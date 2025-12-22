from unittest.mock import MagicMock, patch

from git import Repo

from git_nearit.clients.git_client import GitClient
from tests.base import GitRepoTestCase


class TestGitClientInit(GitRepoTestCase):
    def test_init_with_valid_repo(self) -> None:
        """Test GitClient initialization with valid repository."""
        client = GitClient(self.repo_path)
        self.assertIsNotNone(client.repo)
        self.assertIsInstance(client.repo, Repo)

    def test_init_with_invalid_path(self) -> None:
        """Test GitClient initialization with invalid path."""
        non_repo_path = self.temp_path / "not_a_repo"
        non_repo_path.mkdir()

        with self.assertRaises(ValueError) as context:
            GitClient(non_repo_path)

        self.assertIn("Not a git repository", str(context.exception))


class TestGitClientBranches(GitRepoTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = GitClient(self.repo_path)

    def test_get_main_branch(self) -> None:
        """Test getting main branch name."""
        main_branch = self.client.get_main_branch()
        self.assertEqual(main_branch, "master")

    def test_get_current_branch(self) -> None:
        """Test getting current branch name."""
        current_branch = self.client.get_current_branch()
        self.assertEqual(current_branch, "main")

    def test_is_on_main_branch(self) -> None:
        """Test checking if on main branch."""
        # Current branch is "main", but get_main_branch() returns "master"
        self.assertFalse(self.client.is_on_main_branch())

    def test_create_change_branch(self) -> None:
        """Test creating a change branch."""
        branch_name = self.client.create_change_branch()

        self.assertTrue(branch_name.startswith("change/"))
        self.assertGreater(len(branch_name), len("change/"))
        self.assertEqual(self.client.get_current_branch(), branch_name)


class TestGitClientStash(GitRepoTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = GitClient(self.repo_path)

    def test_stash_and_pop(self) -> None:
        """Test stashing and popping changes to tracked files."""
        readme = self.repo_path / "README.md"
        original_content = readme.read_text()
        readme.write_text("# Modified content\n")

        self.assertTrue(self.client.stash_changes())
        self.assertEqual(readme.read_text(), original_content)
        self.assertTrue(self.client.pop_stash())
        self.assertEqual(readme.read_text(), "# Modified content\n")

    def test_stash_when_nothing_to_stash(self) -> None:
        """Test stashing when there are no changes."""
        self.assertFalse(self.client.stash_changes())


class TestGitClientChanges(GitRepoTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = GitClient(self.repo_path)

    def test_has_uncommitted_changes_false(self) -> None:
        """Test detecting no uncommitted changes."""
        self.assertFalse(self.client.has_uncommitted_changes())

    def test_untracked_files_not_detected(self) -> None:
        """Test that untracked files are NOT detected as uncommitted changes."""
        test_file = self.repo_path / "new_untracked_file.txt"
        test_file.write_text("untracked content")

        self.assertFalse(self.client.has_uncommitted_changes())

    def test_modified_tracked_files_detected(self) -> None:
        """Test that modified tracked files ARE detected."""
        readme = self.repo_path / "README.md"
        readme.write_text("# Modified content\n")

        self.assertTrue(self.client.has_uncommitted_changes())

    def test_staged_changes_detected(self) -> None:
        """Test that staged changes ARE detected."""
        test_file = self.repo_path / "staged_file.txt"
        test_file.write_text("staged content")
        self.client.repo.index.add(["staged_file.txt"])

        self.assertTrue(self.client.has_uncommitted_changes())


class TestGitClientCommits(GitRepoTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = GitClient(self.repo_path)

    def test_get_last_commit_message(self) -> None:
        subject, body = self.client.get_last_commit_message()
        self.assertEqual(subject, "Initial commit")
        self.assertIsInstance(body, str)


class TestGitClientFetchAndCheckout(GitRepoTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = GitClient(self.repo_path)

    def test_fetch_and_checkout_new_branch(self) -> None:
        test_branch = "feature/new-feature"

        self.client.repo.git.checkout("-b", test_branch)
        test_file = self.repo_path / "feature.txt"
        test_file.write_text("feature content")
        self.client.repo.index.add(["feature.txt"])
        self.client.repo.index.commit("Add feature")

        self.client.repo.create_head(f"origin/{test_branch}", test_branch)

        self.client.repo.git.checkout("main")
        self.client.repo.git.branch("-D", test_branch)

        real_git = self.client.repo.git
        mock_git = MagicMock()
        mock_git.fetch = MagicMock()
        mock_git.checkout = MagicMock(side_effect=real_git.checkout)
        mock_git.reset = MagicMock(side_effect=real_git.reset)

        with patch.object(self.client.repo, "git", mock_git):
            self.client.fetch_and_checkout_branch(test_branch)

        mock_git.fetch.assert_called_once_with("origin", test_branch)
        mock_git.checkout.assert_called_once_with("-b", test_branch, f"origin/{test_branch}")

    def test_fetch_and_checkout_existing_branch(self) -> None:
        test_branch = "feature/existing"

        self.client.repo.git.checkout("-b", test_branch)
        test_file = self.repo_path / "existing.txt"
        test_file.write_text("v1")
        self.client.repo.index.add(["existing.txt"])
        self.client.repo.index.commit("v1")

        test_file.write_text("v2")
        self.client.repo.index.add(["existing.txt"])
        self.client.repo.index.commit("v2")

        self.client.repo.create_head(f"origin/{test_branch}", test_branch)
        self.client.repo.git.checkout("main")

        real_git = self.client.repo.git
        mock_git = MagicMock()
        mock_git.fetch = MagicMock()
        mock_git.checkout = MagicMock(side_effect=real_git.checkout)
        mock_git.reset = MagicMock(side_effect=real_git.reset)

        with patch.object(self.client.repo, "git", mock_git):
            self.client.fetch_and_checkout_branch(test_branch)

        mock_git.fetch.assert_called_once_with("origin", test_branch)
        mock_git.checkout.assert_called_once_with(test_branch)
        mock_git.reset.assert_called_once_with("--hard", f"origin/{test_branch}")

    def test_fetch_and_checkout_fails_with_nonexistent_branch(self) -> None:
        from git.exc import GitCommandError

        mock_git = MagicMock()
        mock_git.fetch.side_effect = GitCommandError("git fetch", 128)

        with patch.object(self.client.repo, "git", mock_git):
            with self.assertRaises(ValueError) as context:
                self.client.fetch_and_checkout_branch("nonexistent/branch")

        self.assertIn("Failed to fetch and checkout branch", str(context.exception))
        mock_git.fetch.assert_called_once_with("origin", "nonexistent/branch")
