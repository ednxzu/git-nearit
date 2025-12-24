import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, mock_open, patch

from git_nearit.clients.base_vcs_client import Review
from git_nearit.utils import (
    display_reviews_table,
    edit_in_editor,
    format_relative_time,
    get_pr_description,
    get_pr_title,
    get_text_input,
    select_from_menu,
    setup_logging,
)


class TestFormatRelativeTime(unittest.TestCase):
    def test_just_now(self) -> None:
        now = datetime.now(timezone.utc)
        iso_str = now.isoformat()
        result = format_relative_time(iso_str)
        self.assertEqual(result, "just now")

    def test_minutes_ago(self) -> None:
        now = datetime.now(timezone.utc)
        past = now - timedelta(minutes=5)
        iso_str = past.isoformat()
        result = format_relative_time(iso_str)
        self.assertEqual(result, "5m ago")

    def test_hours_ago(self) -> None:
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=3)
        iso_str = past.isoformat()
        result = format_relative_time(iso_str)
        self.assertEqual(result, "3h ago")

    def test_days_ago(self) -> None:
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=5)
        iso_str = past.isoformat()
        result = format_relative_time(iso_str)
        self.assertEqual(result, "5d ago")

    def test_months_ago(self) -> None:
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=60)
        iso_str = past.isoformat()
        result = format_relative_time(iso_str)
        self.assertEqual(result, "2mo ago")

    def test_years_ago(self) -> None:
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=400)
        iso_str = past.isoformat()
        result = format_relative_time(iso_str)
        self.assertEqual(result, "1y ago")

    def test_with_z_suffix(self) -> None:
        iso_str = "2025-12-22T10:00:00Z"
        result = format_relative_time(iso_str)
        self.assertIsNotNone(result)

    def test_invalid_format(self) -> None:
        invalid_str = "not-a-date"
        result = format_relative_time(invalid_str)
        self.assertEqual(result, "not-a-date")


class TestDisplayReviewsTable(unittest.TestCase):
    @patch("git_nearit.utils.console")
    def test_display_empty_reviews(self, mock_console) -> None:
        display_reviews_table([], "main")
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        self.assertIn("No open reviews", call_args)
        self.assertIn("main", call_args)

    @patch("git_nearit.utils.console")
    def test_display_reviews_with_data(self, mock_console) -> None:
        reviews = [
            Review(
                number=1,
                title="feat/test-feature",
                url="https://example.com/pulls/1",
                author="testuser",
                state="open",
                draft=False,
                created_at="2025-12-22T10:00:00Z",
                updated_at="2025-12-22T12:00:00Z",
            ),
            Review(
                number=2,
                title="This is a very long title that should be truncated because it exceeds the maximum length",
                url="https://example.com/pulls/2",
                author="developer",
                state="closed",
                draft=True,
                created_at="2025-12-21T10:00:00Z",
                updated_at="2025-12-22T10:00:00Z",
            ),
        ]

        display_reviews_table(reviews, "develop")

        mock_console.print.assert_called_once()
        table_arg = mock_console.print.call_args[0][0]
        # Basic check that it's a table object
        self.assertEqual(table_arg.__class__.__name__, "Table")

    @patch("git_nearit.utils.console")
    def test_display_reviews_with_missing_fields(self, mock_console) -> None:
        reviews = [
            Review(
                number=1,
                title="minimal-review",
                url="https://example.com/pulls/1",
            )
        ]

        display_reviews_table(reviews, "main")
        mock_console.print.assert_called_once()

    @patch("git_nearit.utils.console")
    def test_display_reviews_with_merged_state(self, mock_console) -> None:
        reviews = [
            Review(
                number=1,
                title="merged-pr",
                url="https://example.com/pulls/1",
                state="merged",
            )
        ]

        display_reviews_table(reviews, "main")
        mock_console.print.assert_called_once()

    @patch("git_nearit.utils.console")
    def test_display_reviews_with_unknown_state(self, mock_console) -> None:
        reviews = [
            Review(
                number=1,
                title="test-pr",
                url="https://example.com/pulls/1",
                state="pending",
            )
        ]

        display_reviews_table(reviews, "main")
        mock_console.print.assert_called_once()


class TestSetupLogging(unittest.TestCase):
    def test_setup_logging_creates_logger(self) -> None:
        logger = setup_logging()
        self.assertEqual(logger.name, "git-nearit")
        self.assertEqual(logger.level, 20)
        self.assertEqual(len(logger.handlers), 1)


class TestSelectFromMenu(unittest.TestCase):
    @patch("git_nearit.utils.questionary.select")
    def test_select_from_menu_success(self, mock_select) -> None:
        mock_select.return_value.ask.return_value = "option1"
        result = select_from_menu("Choose:", ["option1", "option2"])
        self.assertEqual(result, "option1")

    @patch("git_nearit.utils.questionary.select")
    @patch("git_nearit.utils.console")
    def test_select_from_menu_cancelled(self, mock_console, mock_select) -> None:
        mock_select.return_value.ask.return_value = None
        with self.assertRaises(SystemExit) as cm:
            select_from_menu("Choose:", ["option1", "option2"])
        self.assertEqual(cm.exception.code, 1)
        mock_console.print.assert_called_once()


class TestGetTextInput(unittest.TestCase):
    @patch("git_nearit.utils.questionary.text")
    def test_get_text_input_success(self, mock_text) -> None:
        mock_text.return_value.ask.return_value = "user input"
        result = get_text_input("Enter text:")
        self.assertEqual(result, "user input")

    @patch("git_nearit.utils.questionary.text")
    @patch("git_nearit.utils.console")
    def test_get_text_input_cancelled(self, mock_console, mock_text) -> None:
        mock_text.return_value.ask.return_value = None
        with self.assertRaises(SystemExit) as cm:
            get_text_input("Enter text:")
        self.assertEqual(cm.exception.code, 1)
        mock_console.print.assert_called_once()


class TestEditInEditor(unittest.TestCase):
    @patch("git_nearit.utils.subprocess.run")
    @patch("git_nearit.utils.tempfile.NamedTemporaryFile")
    @patch("git_nearit.utils.Path")
    def test_edit_in_editor_basic(self, mock_path_class, mock_temp, mock_run) -> None:
        mock_file = MagicMock()
        mock_temp.return_value.__enter__.return_value = mock_file
        mock_file.name = "/tmp/test.txt"

        mock_path = MagicMock()
        mock_path_class.return_value = mock_path
        mock_path.read_text.return_value = (
            "# ---- EDIT BELOW THIS LINE ----\n\nEdited content\n\n# ---- EDIT ABOVE THIS LINE ----"
        )

        result = edit_in_editor("initial content")

        self.assertEqual(result, "Edited content")
        mock_run.assert_called_once()
        mock_path.unlink.assert_called_once()

    @patch("git_nearit.utils.subprocess.run")
    @patch("git_nearit.utils.tempfile.NamedTemporaryFile")
    @patch("git_nearit.utils.Path")
    def test_edit_in_editor_missing_markers(self, mock_path_class, mock_temp, mock_run) -> None:
        mock_file = MagicMock()
        mock_temp.return_value.__enter__.return_value = mock_file
        mock_file.name = "/tmp/test.txt"

        mock_path = MagicMock()
        mock_path_class.return_value = mock_path
        mock_path.read_text.return_value = "Content without markers"

        result = edit_in_editor("initial")

        self.assertEqual(result, "Content without markers")


class TestGetPrTitle(unittest.TestCase):
    @patch("git_nearit.utils.get_text_input")
    @patch("git_nearit.utils.select_from_menu")
    def test_get_pr_title(self, mock_select, mock_input) -> None:
        mock_select.return_value = "feat"
        mock_input.return_value = "new-feature"

        result = get_pr_title()

        self.assertEqual(result, "feat/new-feature")


class TestGetPrDescription(unittest.TestCase):
    @patch("git_nearit.utils.edit_in_editor")
    def test_get_pr_description_success(self, mock_edit) -> None:
        mock_edit.return_value = "PR description"

        result = get_pr_description("commit subject", "commit body")

        self.assertEqual(result, "PR description")
        mock_edit.assert_called_once_with("commit subject\n\ncommit body")

    @patch("git_nearit.utils.edit_in_editor")
    @patch("git_nearit.utils.console")
    def test_get_pr_description_empty(self, mock_console, mock_edit) -> None:
        mock_edit.return_value = ""

        with self.assertRaises(SystemExit) as cm:
            get_pr_description("subject", "body")

        self.assertEqual(cm.exception.code, 1)
        mock_console.print.assert_called_once()
