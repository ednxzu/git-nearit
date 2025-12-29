import unittest
from unittest.mock import MagicMock, patch

from git_nearit.cli import download_review, list_reviews, run_review
from git_nearit.models import Review, ReviewDetail


class TestRunReview(unittest.TestCase):
    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.get_pr_description")
    @patch("git_nearit.cli.get_pr_title")
    @patch("git_nearit.cli.GiteaClient")
    @patch("git_nearit.cli.GitClient")
    def test_run_review_creates_branch_on_main(
        self, mock_git_client, mock_gitea_client, mock_get_title, mock_get_desc, mock_logging
    ):
        # Setup mocks
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git.has_uncommitted_changes.return_value = False
        mock_git.get_main_branch.return_value = "main"
        mock_git.get_current_branch.return_value = "main"
        mock_git.is_on_main_branch.return_value = True
        mock_git.create_change_branch.return_value = "change/20250101120000"
        mock_git.get_last_commit_message.return_value = ("feat: test", "test body")
        mock_git_client.return_value = mock_git

        mock_vcs = MagicMock()
        mock_vcs.check_existing_review.return_value = None
        mock_review = MagicMock()
        mock_review.url = "https://example.com/pulls/1"
        mock_vcs.create_review.return_value = mock_review
        mock_gitea_client.return_value = mock_vcs

        mock_get_title.return_value = "feat/test-feature"
        mock_get_desc.return_value = "Test description"

        run_review("gitea", None)

        mock_git.create_change_branch.assert_called_once()
        mock_git.push_branch.assert_called_once_with("change/20250101120000")
        mock_vcs.create_review.assert_called_once()

    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.get_pr_description")
    @patch("git_nearit.cli.get_pr_title")
    @patch("git_nearit.cli.GitLabClient")
    @patch("git_nearit.cli.GitClient")
    def test_run_review_gitlab_platform(
        self, mock_git_client, mock_gitlab_client, mock_get_title, mock_get_desc, mock_logging
    ):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git.has_uncommitted_changes.return_value = False
        mock_git.get_main_branch.return_value = "main"
        mock_git.get_current_branch.return_value = "change/test"
        mock_git.is_on_main_branch.return_value = False
        mock_git.get_last_commit_message.return_value = ("feat: test", "")
        mock_git_client.return_value = mock_git

        mock_vcs = MagicMock()
        mock_vcs.check_existing_review.return_value = None
        mock_review = MagicMock()
        mock_review.url = "https://gitlab.com/mrs/1"
        mock_vcs.create_review.return_value = mock_review
        mock_gitlab_client.return_value = mock_vcs

        mock_get_title.return_value = "feat/test"
        mock_get_desc.return_value = "desc"

        run_review("gitlab", None)

        mock_gitlab_client.assert_called_once()
        mock_vcs.create_review.assert_called_once()

    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.GitClient")
    def test_run_review_exits_on_uncommitted_changes(self, mock_git_client, mock_logging):
        """Test run_review exits when there are uncommitted changes."""
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git.has_uncommitted_changes.return_value = True
        mock_git_client.return_value = mock_git

        with self.assertRaises(SystemExit) as cm:
            run_review("gitea", None)

        self.assertEqual(cm.exception.code, 1)
        mock_logger.error.assert_called()

    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.GiteaClient")
    @patch("git_nearit.cli.GitClient")
    def test_run_review_returns_if_existing_review(
        self, mock_git_client, mock_gitea_client, mock_logging
    ):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git.has_uncommitted_changes.return_value = False
        mock_git.get_main_branch.return_value = "main"
        mock_git.get_current_branch.return_value = "change/test"
        mock_git.is_on_main_branch.return_value = False
        mock_git_client.return_value = mock_git

        mock_vcs = MagicMock()
        existing_review = MagicMock()
        existing_review.title = "Existing PR"
        existing_review.url = "https://example.com/pulls/1"
        mock_vcs.check_existing_review.return_value = existing_review
        mock_gitea_client.return_value = mock_vcs

        run_review("gitea", None)

        mock_vcs.create_review.assert_not_called()

    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.GiteaClient")
    @patch("git_nearit.cli.GitClient")
    def test_run_review_updates_existing_review_to_draft(
        self, mock_git_client, mock_gitea_client, mock_logging
    ):
        """Test that --wip flag updates existing review to draft."""
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git.has_uncommitted_changes.return_value = False
        mock_git.get_main_branch.return_value = "main"
        mock_git.get_current_branch.return_value = "change/test"
        mock_git.is_on_main_branch.return_value = False
        mock_git_client.return_value = mock_git

        mock_vcs = MagicMock()
        existing_review = Review(
            title="Existing PR",
            url="https://example.com/pulls/1",
            number=1,
        )
        mock_vcs.check_existing_review.return_value = existing_review
        mock_gitea_client.return_value = mock_vcs

        run_review("gitea", None, wip=True, ready=False)

        # Should call update_review_status with draft=True
        mock_vcs.update_review_status.assert_called_once_with(review=existing_review, draft=True)
        mock_vcs.create_review.assert_not_called()

    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.GiteaClient")
    @patch("git_nearit.cli.GitClient")
    def test_run_review_updates_existing_review_to_ready(
        self, mock_git_client, mock_gitea_client, mock_logging
    ):
        """Test that --ready flag updates existing review to ready."""
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git.has_uncommitted_changes.return_value = False
        mock_git.get_main_branch.return_value = "main"
        mock_git.get_current_branch.return_value = "change/test"
        mock_git.is_on_main_branch.return_value = False
        mock_git_client.return_value = mock_git

        mock_vcs = MagicMock()
        existing_review = Review(
            title="WIP: Existing PR",
            url="https://example.com/pulls/1",
            number=1,
        )
        mock_vcs.check_existing_review.return_value = existing_review
        mock_gitea_client.return_value = mock_vcs

        run_review("gitea", None, wip=False, ready=True)

        # Should call update_review_status with draft=False
        mock_vcs.update_review_status.assert_called_once_with(review=existing_review, draft=False)
        mock_vcs.create_review.assert_not_called()


class TestDownloadReview(unittest.TestCase):
    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.GiteaClient")
    @patch("git_nearit.cli.GitClient")
    def test_download_review_fetches_and_checks_out(
        self, mock_git_client, mock_gitea_client, mock_logging
    ):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git.has_uncommitted_changes.return_value = False
        mock_git_client.return_value = mock_git

        mock_vcs = MagicMock()
        mock_vcs.get_review.return_value = ReviewDetail(
            number=42,
            title="Test PR",
            url="https://example.com/pulls/42",
            source_branch="feature/test-branch",
            target_branch="main",
        )
        mock_gitea_client.return_value = mock_vcs

        download_review("gitea", 42)

        mock_vcs.get_review.assert_called_once_with(42)
        mock_git.fetch_and_checkout_branch.assert_called_once_with("feature/test-branch")

    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.GitClient")
    def test_download_review_exits_on_uncommitted_changes(self, mock_git_client, mock_logging):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git.has_uncommitted_changes.return_value = True
        mock_git_client.return_value = mock_git

        with self.assertRaises(SystemExit) as cm:
            download_review("gitea", 42)

        self.assertEqual(cm.exception.code, 1)

    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.GiteaClient")
    @patch("git_nearit.cli.GitClient")
    def test_download_review_exits_on_missing_branch(
        self, mock_git_client, mock_gitea_client, mock_logging
    ):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git.has_uncommitted_changes.return_value = False
        mock_git_client.return_value = mock_git

        mock_vcs = MagicMock()
        mock_vcs.get_review.return_value = ReviewDetail(
            number=42,
            title="Test PR",
            url="https://example.com/pulls/42",
            source_branch="",  # Empty branch name
            target_branch="main",
        )
        mock_gitea_client.return_value = mock_vcs

        with self.assertRaises(SystemExit) as cm:
            download_review("gitea", 42)

        self.assertEqual(cm.exception.code, 1)


class TestListReviews(unittest.TestCase):
    @patch("git_nearit.cli.display_reviews_table")
    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.GiteaClient")
    @patch("git_nearit.cli.GitClient")
    def test_list_reviews_uses_main_branch_by_default(
        self, mock_git_client, mock_gitea_client, mock_logging, mock_display
    ):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git.get_main_branch.return_value = "main"
        mock_git_client.return_value = mock_git

        mock_vcs = MagicMock()
        mock_vcs.list_reviews.return_value = []
        mock_gitea_client.return_value = mock_vcs

        list_reviews("gitea", None)

        mock_git.get_main_branch.assert_called_once()
        mock_vcs.list_reviews.assert_called_once_with("main")
        mock_display.assert_called_once_with([], "main")

    @patch("git_nearit.cli.display_reviews_table")
    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.GiteaClient")
    @patch("git_nearit.cli.GitClient")
    def test_list_reviews_uses_specified_branch(
        self, mock_git_client, mock_gitea_client, mock_logging, mock_display
    ):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git_client.return_value = mock_git

        mock_vcs = MagicMock()
        reviews = [Review(number=1, title="Test", url="https://example.com/pulls/1")]
        mock_vcs.list_reviews.return_value = reviews
        mock_gitea_client.return_value = mock_vcs

        list_reviews("gitea", "develop")

        mock_git.get_main_branch.assert_not_called()
        mock_vcs.list_reviews.assert_called_once_with("develop")
        mock_display.assert_called_once_with(reviews, "develop")

    @patch("git_nearit.cli.display_reviews_table")
    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.GitLabClient")
    @patch("git_nearit.cli.GitClient")
    def test_list_reviews_gitlab_platform(
        self, mock_git_client, mock_gitlab_client, mock_logging, mock_display
    ):
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        mock_git = MagicMock()
        mock_git.get_main_branch.return_value = "main"
        mock_git_client.return_value = mock_git

        mock_vcs = MagicMock()
        mock_vcs.list_reviews.return_value = []
        mock_gitlab_client.return_value = mock_vcs

        list_reviews("gitlab", None)

        mock_gitlab_client.assert_called_once()
