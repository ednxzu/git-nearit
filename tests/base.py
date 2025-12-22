import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from git import Repo


class GitRepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
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
        self.temp_dir.cleanup()
