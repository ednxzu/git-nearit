from git_nearit.clients.git_client import GitClient
from tests.base import GitRepoTestCase


class TestCLIWorkflow(GitRepoTestCase):
    """Test CLI workflow scenarios."""

    def test_workflow_fails_with_uncommitted_changes(self) -> None:
        """Test that workflow exits early with uncommitted changes to tracked files."""
        git_client = GitClient(self.repo_path)

        readme = self.repo_path / "README.md"
        readme.write_text("# Modified content\n")

        self.assertTrue(git_client.has_uncommitted_changes())

    def test_workflow_allows_untracked_files(self) -> None:
        """Test that workflow allows untracked files to proceed."""
        git_client = GitClient(self.repo_path)

        test_file = self.repo_path / "untracked.txt"
        test_file.write_text("untracked content")

        self.assertFalse(git_client.has_uncommitted_changes())

        branch_name = git_client.create_change_branch()
        self.assertTrue(branch_name.startswith("change/"))

    def test_workflow_succeeds_with_clean_working_tree(self) -> None:
        """Test that workflow can proceed with clean working tree."""
        git_client = GitClient(self.repo_path)

        self.assertFalse(git_client.has_uncommitted_changes())

        branch_name = git_client.create_change_branch()
        self.assertTrue(branch_name.startswith("change/"))
        self.assertEqual(git_client.get_current_branch(), branch_name)

    def test_workflow_on_existing_change_branch(self) -> None:
        """Test workflow when already on a change branch."""
        git_client = GitClient(self.repo_path)

        change_branch = "change/20250101120000"
        git_client.repo.git.checkout("-b", change_branch)

        self.assertEqual(git_client.get_current_branch(), change_branch)
        self.assertTrue(git_client.get_current_branch().startswith("change/"))

        self.assertFalse(git_client.is_on_main_branch())
