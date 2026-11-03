import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from git_nearit.cli import download_review, list_reviews, run_review
from git_nearit.models import Review, ReviewDetail, ReviewListItem


class TestRunReview(unittest.TestCase):
    @patch("git_nearit.cli.is_interactive", return_value=True)
    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.get_pr_description")
    @patch("git_nearit.cli.get_pr_title")
    @patch("git_nearit.cli.GiteaClient")
    @patch("git_nearit.cli.GitClient")
    def test_run_review_creates_branch_on_main(
        self, mock_git_client, mock_gitea_client, mock_get_title, mock_get_desc, mock_logging, _
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

    @patch("git_nearit.cli.is_interactive", return_value=True)
    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.get_pr_description")
    @patch("git_nearit.cli.get_pr_title")
    @patch("git_nearit.cli.GitLabClient")
    @patch("git_nearit.cli.GitClient")
    def test_run_review_gitlab_platform(
        self, mock_git_client, mock_gitlab_client, mock_get_title, mock_get_desc, mock_logging, _
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

        # Should call update_review with draft=True
        mock_vcs.update_review.assert_called_once_with(
            review=existing_review, title=None, description=None, draft=True
        )
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

        # Should call update_review with draft=False
        mock_vcs.update_review.assert_called_once_with(
            review=existing_review, title=None, description=None, draft=False
        )
        mock_vcs.create_review.assert_not_called()


def _fake_vcs(prefix: str) -> MagicMock:
    """VCS client mock with real draft-prefix helpers, as the JSON output relies on them."""
    vcs = MagicMock()
    vcs.is_draft_title.side_effect = lambda title: title.startswith(prefix)
    vcs.strip_draft_prefix.side_effect = lambda title: title.removeprefix(prefix)
    return vcs


def _fake_git(current_branch: str = "change/test") -> MagicMock:
    git = MagicMock()
    git.has_uncommitted_changes.return_value = False
    git.get_main_branch.return_value = "main"
    git.get_current_branch.return_value = current_branch
    git.is_on_main_branch.return_value = False
    git.get_last_commit_message.return_value = ("feat: subject", "commit body")
    return git


@patch("git_nearit.cli.setup_logging")
@patch("git_nearit.utils.edit_in_editor")
@patch("git_nearit.cli.get_pr_description")
@patch("git_nearit.cli.get_pr_title")
@patch("git_nearit.cli.GitLabClient")
@patch("git_nearit.cli.GitClient")
class TestRunReviewNonInteractive(unittest.TestCase):
    def _setup(self, mock_git_client, mock_gitlab_client, existing=None):
        git = _fake_git()
        mock_git_client.return_value = git
        vcs = _fake_vcs("[Draft] ")
        vcs.check_existing_review.return_value = existing
        vcs.create_review.side_effect = lambda title, description, source_branch, **kw: Review(
            title=f"[Draft] {title}" if kw.get("draft") else title,
            url="https://gitlab.example.com/mr/42",
            number=42,
        )
        mock_gitlab_client.return_value = vcs
        return git, vcs

    def test_create_with_title_and_message_never_prompts(
        self, mock_git_client, mock_gitlab, mock_title, mock_desc, mock_editor, mock_logging
    ):
        _, vcs = self._setup(mock_git_client, mock_gitlab)

        run_review("gitlab", title="feat/add-cli-desc", description="Body")

        mock_title.assert_not_called()
        mock_desc.assert_not_called()
        mock_editor.assert_not_called()
        vcs.create_review.assert_called_once_with(
            title="feat/add-cli-desc",
            description="Body",
            source_branch="change/test",
            target_branch="main",
            draft=False,
        )

    def test_create_with_no_edit_uses_commit_message(
        self, mock_git_client, mock_gitlab, mock_title, mock_desc, mock_editor, mock_logging
    ):
        _, vcs = self._setup(mock_git_client, mock_gitlab)

        run_review("gitlab", title="feat/x", no_edit=True)

        mock_desc.assert_not_called()
        self.assertEqual(
            vcs.create_review.call_args.kwargs["description"], "feat: subject\n\ncommit body"
        )

    @patch("git_nearit.utils.sys.stdin")
    def test_no_tty_missing_title_exits(
        self,
        mock_stdin,
        mock_git_client,
        mock_gitlab,
        mock_title,
        mock_desc,
        mock_editor,
        mock_logging,
    ):
        mock_stdin.isatty.return_value = False
        _, vcs = self._setup(mock_git_client, mock_gitlab)

        with self.assertRaises(SystemExit) as cm:
            run_review("gitlab", description="Body")

        self.assertEqual(cm.exception.code, 1)
        mock_logging.return_value.error.assert_called_once_with(
            "missing --title; required when not running interactively"
        )
        mock_title.assert_not_called()
        vcs.create_review.assert_not_called()

    @patch("git_nearit.utils.sys.stdin")
    def test_no_tty_missing_description_exits(
        self,
        mock_stdin,
        mock_git_client,
        mock_gitlab,
        mock_title,
        mock_desc,
        mock_editor,
        mock_logging,
    ):
        mock_stdin.isatty.return_value = False
        _, vcs = self._setup(mock_git_client, mock_gitlab)

        with self.assertRaises(SystemExit) as cm:
            run_review("gitlab", title="feat/x")

        self.assertEqual(cm.exception.code, 1)
        mock_logging.return_value.error.assert_called_once_with(
            "missing --message, --message-file or --no-edit; "
            "required when not running interactively"
        )
        mock_desc.assert_not_called()
        vcs.create_review.assert_not_called()

    @patch("git_nearit.utils.sys.stdin")
    def test_no_tty_missing_title_on_main_fails_before_git_mutation(
        self,
        mock_stdin,
        mock_git_client,
        mock_gitlab,
        mock_title,
        mock_desc,
        mock_editor,
        mock_logging,
    ):
        mock_stdin.isatty.return_value = False
        git, vcs = self._setup(mock_git_client, mock_gitlab)
        git.get_current_branch.return_value = "main"
        git.is_on_main_branch.return_value = True

        with self.assertRaises(SystemExit) as cm:
            run_review("gitlab", no_edit=True)

        self.assertEqual(cm.exception.code, 1)
        mock_logging.return_value.error.assert_called_once_with(
            "missing --title; required when not running interactively"
        )
        git.create_change_branch.assert_not_called()
        git.repo.git.checkout.assert_not_called()
        git.repo.git.reset.assert_not_called()
        git.push_branch.assert_not_called()
        vcs.check_existing_review.assert_not_called()
        vcs.create_review.assert_not_called()

    @patch("git_nearit.utils.sys.stdin")
    def test_no_tty_missing_title_on_target_branch_fails_before_git_mutation(
        self,
        mock_stdin,
        mock_git_client,
        mock_gitlab,
        mock_title,
        mock_desc,
        mock_editor,
        mock_logging,
    ):
        mock_stdin.isatty.return_value = False
        git, _ = self._setup(mock_git_client, mock_gitlab)
        git.get_current_branch.return_value = "develop"

        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            run_review("gitlab", "develop", description="Body", json_output=True)

        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(
            json.loads(out.getvalue()),
            {"error": "missing --title; required when not running interactively"},
        )
        git.create_change_branch.assert_not_called()
        git.repo.git.reset.assert_not_called()
        git.push_branch.assert_not_called()

    @patch("git_nearit.utils.sys.stdin")
    def test_no_tty_missing_title_on_change_branch_fails_before_push(
        self,
        mock_stdin,
        mock_git_client,
        mock_gitlab,
        mock_title,
        mock_desc,
        mock_editor,
        mock_logging,
    ):
        mock_stdin.isatty.return_value = False
        git, vcs = self._setup(mock_git_client, mock_gitlab)

        with self.assertRaises(SystemExit) as cm:
            run_review("gitlab", no_edit=True)

        self.assertEqual(cm.exception.code, 1)
        vcs.check_existing_review.assert_called_once_with("change/test", "main")
        git.create_change_branch.assert_not_called()
        git.push_branch.assert_not_called()
        vcs.create_review.assert_not_called()

    @patch("git_nearit.utils.sys.stdin")
    def test_no_tty_existing_review_needs_no_title_and_checks_before_push(
        self,
        mock_stdin,
        mock_git_client,
        mock_gitlab,
        mock_title,
        mock_desc,
        mock_editor,
        mock_logging,
    ):
        mock_stdin.isatty.return_value = False
        existing = Review(title="feat/old", url="https://gitlab.example.com/mr/7", number=7)
        git, vcs = self._setup(mock_git_client, mock_gitlab, existing=existing)
        git.push_branch.side_effect = lambda branch: vcs.check_existing_review.assert_called_once()

        run_review("gitlab", wip=True)

        git.push_branch.assert_called_once_with("change/test")
        vcs.check_existing_review.assert_called_once_with("change/test", "main")
        vcs.update_review.assert_called_once_with(
            review=existing, title=None, description=None, draft=True
        )

    def test_on_main_pushes_then_checks_for_review(
        self, mock_git_client, mock_gitlab, mock_title, mock_desc, mock_editor, mock_logging
    ):
        git, vcs = self._setup(mock_git_client, mock_gitlab)
        git.get_current_branch.return_value = "main"
        git.is_on_main_branch.return_value = True
        git.create_change_branch.return_value = "change/20261103120000"

        run_review("gitlab", title="feat/x", description="Body")

        git.create_change_branch.assert_called_once()
        git.push_branch.assert_called_once_with("change/20261103120000")
        vcs.check_existing_review.assert_called_once_with("change/20261103120000", "main")
        vcs.create_review.assert_called_once()

    @patch("git_nearit.utils.sys.stdin")
    def test_tty_still_prompts(
        self,
        mock_stdin,
        mock_git_client,
        mock_gitlab,
        mock_title,
        mock_desc,
        mock_editor,
        mock_logging,
    ):
        mock_stdin.isatty.return_value = True
        mock_title.return_value = "feat/prompted"
        mock_desc.return_value = "Edited"
        _, vcs = self._setup(mock_git_client, mock_gitlab)

        run_review("gitlab")

        mock_title.assert_called_once()
        mock_desc.assert_called_once_with("feat: subject", "commit body")
        self.assertEqual(vcs.create_review.call_args.kwargs["title"], "feat/prompted")

    @patch("git_nearit.utils.sys.stdin")
    def test_json_never_prompts_even_on_tty(
        self,
        mock_stdin,
        mock_git_client,
        mock_gitlab,
        mock_title,
        mock_desc,
        mock_editor,
        mock_logging,
    ):
        mock_stdin.isatty.return_value = True
        self._setup(mock_git_client, mock_gitlab)

        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            run_review("gitlab", description="Body", json_output=True)

        self.assertEqual(cm.exception.code, 1)
        mock_title.assert_not_called()
        self.assertEqual(
            json.loads(out.getvalue()),
            {"error": "missing --title; required when not running interactively"},
        )

    def test_existing_review_with_title_keeps_draft_state(
        self, mock_git_client, mock_gitlab, mock_title, mock_desc, mock_editor, mock_logging
    ):
        existing = Review(title="[Draft] feat/old", url="https://gitlab.example.com/mr/7", number=7)
        _, vcs = self._setup(mock_git_client, mock_gitlab, existing=existing)

        run_review("gitlab", title="fix/new-name")

        # draft=None: the client re-applies the current draft prefix
        vcs.update_review.assert_called_once_with(
            review=existing, title="fix/new-name", description=None, draft=None
        )
        mock_title.assert_not_called()
        mock_desc.assert_not_called()

    def test_existing_review_with_no_edit_replaces_description(
        self, mock_git_client, mock_gitlab, mock_title, mock_desc, mock_editor, mock_logging
    ):
        existing = Review(title="feat/old", url="https://gitlab.example.com/mr/7", number=7)
        _, vcs = self._setup(mock_git_client, mock_gitlab, existing=existing)

        run_review("gitlab", no_edit=True, ready=True)

        vcs.update_review.assert_called_once_with(
            review=existing,
            title=None,
            description="feat: subject\n\ncommit body",
            draft=False,
        )
        mock_logging.return_value.info.assert_any_call("Description replaced")

    def test_existing_review_without_flags_makes_no_update(
        self, mock_git_client, mock_gitlab, mock_title, mock_desc, mock_editor, mock_logging
    ):
        existing = Review(title="feat/old", url="https://gitlab.example.com/mr/7", number=7)
        git, vcs = self._setup(mock_git_client, mock_gitlab, existing=existing)

        run_review("gitlab")

        vcs.update_review.assert_not_called()
        vcs.create_review.assert_not_called()
        mock_title.assert_not_called()
        mock_desc.assert_not_called()
        git.get_last_commit_message.assert_not_called()

    def test_json_create_outputs_single_document(
        self, mock_git_client, mock_gitlab, mock_title, mock_desc, mock_editor, mock_logging
    ):
        self._setup(mock_git_client, mock_gitlab)

        out = io.StringIO()
        with redirect_stdout(out):
            run_review(
                "gitlab", wip=True, title="feat/add-cli-desc", description="Body", json_output=True
            )

        mock_logging.assert_called_once_with(json_output=True)
        self.assertEqual(
            json.loads(out.getvalue()),
            {
                "action": "created",
                "number": 42,
                "url": "https://gitlab.example.com/mr/42",
                "title": "feat/add-cli-desc",
                "draft": True,
                "source_branch": "change/test",
                "target_branch": "main",
            },
        )

    def test_json_existing_review_actions(
        self, mock_git_client, mock_gitlab, mock_title, mock_desc, mock_editor, mock_logging
    ):
        existing = Review(title="feat/old", url="https://gitlab.example.com/mr/7", number=7)
        _, vcs = self._setup(mock_git_client, mock_gitlab, existing=existing)
        updated = Review(title="fix/new", url="https://gitlab.example.com/mr/7", number=7)

        cases = (
            ({}, None, "unchanged", "feat/old"),
            ({"title": "fix/new"}, updated, "updated", "fix/new"),
            ({"title": "feat/old"}, existing, "unchanged", "feat/old"),
        )
        for kwargs, returned, action, title in cases:
            with self.subTest(kwargs=kwargs):
                vcs.update_review.return_value = returned
                out = io.StringIO()
                with redirect_stdout(out):
                    run_review("gitlab", json_output=True, **kwargs)
                result = json.loads(out.getvalue())
                self.assertEqual(result["action"], action)
                self.assertEqual(result["title"], title)
                self.assertEqual(result["number"], 7)

    def test_json_unexpected_error_outputs_error_document(
        self, mock_git_client, mock_gitlab, mock_title, mock_desc, mock_editor, mock_logging
    ):
        _, vcs = self._setup(mock_git_client, mock_gitlab)
        vcs.check_existing_review.side_effect = RuntimeError("boom")

        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            run_review("gitlab", title="feat/x", description="Body", json_output=True)

        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(json.loads(out.getvalue()), {"error": "Unexpected error: boom"})


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

    @patch("git_nearit.cli.display_reviews_table")
    @patch("git_nearit.cli.setup_logging")
    @patch("git_nearit.cli.GitLabClient")
    @patch("git_nearit.cli.GitClient")
    def test_list_reviews_json(
        self, mock_git_client, mock_gitlab_client, mock_logging, mock_display
    ):
        mock_git = MagicMock()
        mock_git_client.return_value = mock_git

        item = ReviewListItem(
            title="feat/x",
            url="https://gitlab.example.com/mr/1",
            number=1,
            author="Jane",
            state="opened",
            draft=False,
            created_at="2026-11-01T00:00:00Z",
            updated_at="2026-11-02T00:00:00Z",
        )
        mock_vcs = MagicMock()
        mock_vcs.list_reviews.return_value = [item]
        mock_gitlab_client.return_value = mock_vcs

        out = io.StringIO()
        with redirect_stdout(out):
            list_reviews("gitlab", "main", json_output=True)

        mock_display.assert_not_called()
        mock_logging.assert_called_once_with(json_output=True)
        self.assertEqual(
            json.loads(out.getvalue()),
            [
                {
                    "title": "feat/x",
                    "url": "https://gitlab.example.com/mr/1",
                    "number": 1,
                    "author": "Jane",
                    "state": "opened",
                    "draft": False,
                    "created_at": "2026-11-01T00:00:00Z",
                    "updated_at": "2026-11-02T00:00:00Z",
                }
            ],
        )
