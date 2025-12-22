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
        main_branch = self.client.get_main_branch()
        self.assertEqual(main_branch, "master")

    def test_get_main_branch_with_origin_head(self) -> None:
        self.client.repo.git.symbolic_ref("refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        main_branch = self.client.get_main_branch()
        self.assertEqual(main_branch, "main")

    def test_get_current_branch(self) -> None:
        current_branch = self.client.get_current_branch()
        self.assertEqual(current_branch, "main")

    def test_is_on_main_branch(self) -> None:
        # Current branch is "main", but get_main_branch() returns "master"
        self.assertFalse(self.client.is_on_main_branch())

    def test_create_change_branch(self) -> None:
        branch_name = self.client.create_change_branch()

        self.assertTrue(branch_name.startswith("change/"))
        self.assertGreater(len(branch_name), len("change/"))
        self.assertEqual(self.client.get_current_branch(), branch_name)


class TestGitClientStash(GitRepoTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = GitClient(self.repo_path)

    def test_stash_and_pop(self) -> None:
        readme = self.repo_path / "README.md"
        original_content = readme.read_text()
        readme.write_text("# Modified content\n")

        self.assertTrue(self.client.stash_changes())
        self.assertEqual(readme.read_text(), original_content)
        self.assertTrue(self.client.pop_stash())
        self.assertEqual(readme.read_text(), "# Modified content\n")

    def test_stash_when_nothing_to_stash(self) -> None:
        self.assertFalse(self.client.stash_changes())

    def test_pop_stash_when_no_matching_stash(self) -> None:
        readme = self.repo_path / "README.md"
        readme.write_text("# Modified\n")

        self.client.stash_changes("different-message")

        result = self.client.pop_stash("non-existent-message")
        self.assertFalse(result)


class TestGitClientChanges(GitRepoTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = GitClient(self.repo_path)

    def test_has_uncommitted_changes_false(self) -> None:
        self.assertFalse(self.client.has_uncommitted_changes())

    def test_untracked_files_not_detected(self) -> None:
        test_file = self.repo_path / "new_untracked_file.txt"
        test_file.write_text("untracked content")

        self.assertFalse(self.client.has_uncommitted_changes())

    def test_modified_tracked_files_detected(self) -> None:
        readme = self.repo_path / "README.md"
        readme.write_text("# Modified content\n")

        self.assertTrue(self.client.has_uncommitted_changes())

    def test_staged_changes_detected(self) -> None:
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

    def test_get_last_commit_message_with_body(self) -> None:
        test_file = self.repo_path / "test.txt"
        test_file.write_text("test content")
        self.client.repo.index.add(["test.txt"])
        self.client.repo.index.commit("Test subject\n\nTest body line 1\nTest body line 2")

        subject, body = self.client.get_last_commit_message()

        self.assertEqual(subject, "Test subject")
        self.assertEqual(body, "Test body line 1\nTest body line 2")


class TestGitClientPush(GitRepoTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = GitClient(self.repo_path)

    def test_push_branch_without_force_with_lease(self) -> None:
        test_branch = "test/no-force"
        self.client.repo.git.checkout("-b", test_branch)

        mock_git = MagicMock()
        mock_git.push = MagicMock()

        with patch.object(self.client.repo, "git", mock_git):
            self.client.push_branch(test_branch, force_with_lease=False)

        mock_git.push.assert_called_once_with("-u", "origin", test_branch, "--quiet")

    def test_push_branch_without_set_upstream(self) -> None:
        test_branch = "test/no-upstream"
        self.client.repo.git.checkout("-b", test_branch)

        mock_git = MagicMock()
        mock_git.push = MagicMock()

        with patch.object(self.client.repo, "git", mock_git):
            self.client.push_branch(test_branch, set_upstream=False)

        mock_git.push.assert_called_once_with(
            "origin", test_branch, "--quiet", "--force-with-lease"
        )


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
