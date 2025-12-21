from datetime import datetime
from pathlib import Path
from typing import Optional

from git import Repo
from git.exc import GitCommandError


class GitClient:
    """Handle local git repository operations."""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        try:
            self.repo = Repo(self.repo_path, search_parent_directories=True)
        except Exception as e:
            raise ValueError(f"Not a git repository: {self.repo_path}") from e

    def get_main_branch(self) -> str:
        try:
            origin_head = self.repo.git.symbolic_ref("refs/remotes/origin/HEAD")
            main_branch = origin_head.replace("refs/remotes/origin/", "")
            return main_branch
        except GitCommandError:
            return "master"

    def get_current_branch(self) -> str:
        return self.repo.active_branch.name

    def is_on_main_branch(self) -> bool:
        return self.get_current_branch() == self.get_main_branch()

    def create_change_branch(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        branch_name = f"change/{timestamp}"

        self.repo.git.checkout("-b", branch_name)

        return branch_name

    def stash_changes(self, message: str = "auto-stash-before-branch-switch") -> bool:
        if not self.has_uncommitted_changes():
            return False

        try:
            # -u includes untracked files
            self.repo.git.stash("push", "-u", "-m", message)
            return True
        except GitCommandError:
            return False

    def pop_stash(self, stash_message: str = "auto-stash-before-branch-switch") -> bool:
        try:
            stash_list = self.repo.git.stash("list")
            if stash_message in stash_list:
                self.repo.git.stash("pop")
                return True
            return False
        except GitCommandError:
            return False

    def reset_main_to_origin(self) -> None:
        main_branch = self.get_main_branch()

        self.repo.git.checkout(main_branch)
        self.repo.git.fetch("origin", main_branch, "--quiet")
        self.repo.git.reset("--hard", f"origin/{main_branch}")

    def push_branch(
        self, branch_name: str, force_with_lease: bool = True, set_upstream: bool = True
    ) -> None:
        args = ["origin", branch_name, "--quiet"]

        if set_upstream:
            args.insert(0, "-u")

        if force_with_lease:
            args.append("--force-with-lease")

        self.repo.git.push(*args)

    def get_last_commit_message(self) -> tuple[str, str]:
        commit = self.repo.head.commit
        subject = commit.summary
        body = commit.message.replace(subject, "", 1).strip()
        return subject, body

    def has_uncommitted_changes(self) -> bool:
        return self.repo.is_dirty(untracked_files=False)
