"""Test branch workflow with commits."""

from git import Repo

from git_nearit.clients.git_client import GitClient
from tests.base import GitRepoTestCase


class TestBranchWorkflowWithCommits(GitRepoTestCase):
    def setUp(self) -> None:
        super().setUp()

        repo = Repo(self.repo_path)
        self.initial_commit_sha = repo.head.commit.hexsha

        test_file = self.repo_path / "README.md"
        test_file.write_text("# Initial commit\n\nNew changes by user\n")
        repo.index.add(["README.md"])
        self.user_commit = repo.index.commit("User's new commit")
        self.user_commit_sha = self.user_commit.hexsha

        self.client = GitClient(self.repo_path)

    def test_commits_transferred_to_change_branch(self) -> None:
        self.assertEqual(self.client.get_current_branch(), "main")
        self.assertEqual(self.client.repo.head.commit.hexsha, self.user_commit_sha)

        branch_name = self.client.create_change_branch()

        self.assertEqual(self.client.get_current_branch(), branch_name)
        self.assertEqual(self.client.repo.head.commit.hexsha, self.user_commit_sha)
        self.assertEqual(self.client.repo.head.commit.message.strip(), "User's new commit")

    def test_main_can_be_reset_after_branch_creation(self) -> None:
        branch_name = self.client.create_change_branch()
        change_branch_commit = self.client.repo.head.commit.hexsha
        self.assertEqual(change_branch_commit, self.user_commit_sha)

        self.client.repo.git.checkout("main")
        self.client.repo.git.reset("--hard", self.initial_commit_sha)

        self.assertEqual(self.client.repo.head.commit.hexsha, self.initial_commit_sha)

        self.client.repo.git.checkout(branch_name)

        self.assertEqual(self.client.repo.head.commit.hexsha, self.user_commit_sha)
        self.assertEqual(self.client.repo.head.commit.message.strip(), "User's new commit")
