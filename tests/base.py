import contextlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from git import Repo
from git.exc import GitCommandError


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

        with contextlib.suppress(GitCommandError):
            repo.git.branch("-M", "main")

        with contextlib.suppress(GitCommandError):
            repo.create_remote("origin", "https://example.com/test/repo.git")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
