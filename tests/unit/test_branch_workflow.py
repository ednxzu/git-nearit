"""Test branch workflow with commits."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from git import Repo

from git_nearit.clients.git_client import GitClient


class TestBranchWorkflowWithCommits(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.repo_path = self.temp_path / "test_repo"
        self.repo_path.mkdir()

        repo = Repo.init(self.repo_path)

        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        test_file = self.repo_path / "README.md"
        test_file.write_text("# Initial commit\n")
        repo.index.add(["README.md"])
        initial_commit = repo.index.commit("Initial commit")

        try:
            repo.git.branch("-M", "main")
        except Exception:
            pass

        try:
            repo.create_remote("origin", "https://example.com/test/repo.git")
        except Exception:
            pass

        self.initial_commit_sha = initial_commit.hexsha

        test_file.write_text("# Initial commit\n\nNew changes by user\n")
        repo.index.add(["README.md"])
        self.user_commit = repo.index.commit("User's new commit")
        self.user_commit_sha = self.user_commit.hexsha

        self.client = GitClient(self.repo_path)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_commits_transferred_to_change_branch(self) -> None:
        """Test that user commits are on the change branch after workflow."""
        self.assertEqual(self.client.get_current_branch(), "main")
        self.assertEqual(self.client.repo.head.commit.hexsha, self.user_commit_sha)

        branch_name = self.client.create_change_branch()

        self.assertEqual(self.client.get_current_branch(), branch_name)
        self.assertEqual(self.client.repo.head.commit.hexsha, self.user_commit_sha)
        self.assertEqual(self.client.repo.head.commit.message.strip(), "User's new commit")

    def test_main_can_be_reset_after_branch_creation(self) -> None:
        """Test that main can be safely reset after creating change branch."""
        branch_name = self.client.create_change_branch()
        change_branch_commit = self.client.repo.head.commit.hexsha
        self.assertEqual(change_branch_commit, self.user_commit_sha)

        self.client.repo.git.checkout("main")
        self.client.repo.git.reset("--hard", self.initial_commit_sha)

        self.assertEqual(self.client.repo.head.commit.hexsha, self.initial_commit_sha)

        self.client.repo.git.checkout(branch_name)

        self.assertEqual(self.client.repo.head.commit.hexsha, self.user_commit_sha)
        self.assertEqual(self.client.repo.head.commit.message.strip(), "User's new commit")
