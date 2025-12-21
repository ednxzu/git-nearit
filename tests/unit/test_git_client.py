import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from git import Repo

from git_nearit.clients.git_client import GitClient


class TestGitClientInit(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.repo_path = self.temp_path / "test_repo"
        self.repo_path.mkdir()

        repo = Repo.init(self.repo_path)

        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        test_file = self.repo_path / "README.md"
        test_file.write_text("# Test Repository\n")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        try:
            repo.git.branch("-M", "main")
        except Exception:
            pass

        try:
            repo.create_remote("origin", "https://example.com/test/repo.git")
        except Exception:
            pass

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

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


class TestGitClientBranches(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.repo_path = self.temp_path / "test_repo"
        self.repo_path.mkdir()

        repo = Repo.init(self.repo_path)

        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        test_file = self.repo_path / "README.md"
        test_file.write_text("# Test Repository\n")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        try:
            repo.git.branch("-M", "main")
        except Exception:
            pass

        try:
            repo.create_remote("origin", "https://example.com/test/repo.git")
        except Exception:
            pass

        self.client = GitClient(self.repo_path)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

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


class TestGitClientStash(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.repo_path = self.temp_path / "test_repo"
        self.repo_path.mkdir()

        repo = Repo.init(self.repo_path)

        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        test_file = self.repo_path / "README.md"
        test_file.write_text("# Test Repository\n")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        try:
            repo.git.branch("-M", "main")
        except Exception:
            pass

        self.client = GitClient(self.repo_path)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

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


class TestGitClientChanges(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.repo_path = self.temp_path / "test_repo"
        self.repo_path.mkdir()

        repo = Repo.init(self.repo_path)

        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        test_file = self.repo_path / "README.md"
        test_file.write_text("# Test Repository\n")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        self.client = GitClient(self.repo_path)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

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


class TestGitClientCommits(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.repo_path = self.temp_path / "test_repo"
        self.repo_path.mkdir()

        repo = Repo.init(self.repo_path)

        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        test_file = self.repo_path / "README.md"
        test_file.write_text("# Test Repository\n")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        self.client = GitClient(self.repo_path)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_get_last_commit_message(self) -> None:
        """Test getting last commit message."""
        subject, body = self.client.get_last_commit_message()
        self.assertEqual(subject, "Initial commit")
        self.assertIsInstance(body, str)
