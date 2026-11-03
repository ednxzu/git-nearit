import io
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from git_nearit.models import ReviewListItem
from git_nearit.utils import (
    PR_TITLE_PATTERN,
    PR_TYPES,
    commit_description,
    display_reviews_table,
    edit_in_editor,
    emit_json,
    format_relative_time,
    get_pr_description,
    get_pr_title,
    get_text_input,
    is_interactive,
    read_message_file,
    select_from_menu,
    setup_logging,
    validate_pr_title,
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
            ReviewListItem(
                number=1,
                title="feat/test-feature",
                url="https://example.com/pulls/1",
                author="testuser",
                state="open",
                draft=False,
                created_at="2025-12-22T10:00:00Z",
                updated_at="2025-12-22T12:00:00Z",
            ),
            ReviewListItem(
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
            ReviewListItem(
                number=1,
                title="minimal-review",
                url="https://example.com/pulls/1",
                author="",
                state="",
                draft=False,
                created_at="",
                updated_at="",
            )
        ]

        display_reviews_table(reviews, "main")
        mock_console.print.assert_called_once()

    @patch("git_nearit.utils.console")
    def test_display_reviews_with_merged_state(self, mock_console) -> None:
        reviews = [
            ReviewListItem(
                number=1,
                title="merged-pr",
                url="https://example.com/pulls/1",
                author="testuser",
                state="merged",
                draft=False,
                created_at="2025-12-22T10:00:00Z",
                updated_at="2025-12-22T10:00:00Z",
            )
        ]

        display_reviews_table(reviews, "main")
        mock_console.print.assert_called_once()

    @patch("git_nearit.utils.console")
    def test_display_reviews_with_unknown_state(self, mock_console) -> None:
        reviews = [
            ReviewListItem(
                number=1,
                title="test-pr",
                url="https://example.com/pulls/1",
                author="testuser",
                state="pending",
                draft=False,
                created_at="2025-12-22T10:00:00Z",
                updated_at="2025-12-22T10:00:00Z",
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

    def test_setup_logging_json_logs_to_stderr(self) -> None:
        logger = setup_logging(json_output=True)
        self.assertTrue(logger.handlers[0].console.stderr)

    def test_setup_logging_default_logs_to_stdout(self) -> None:
        logger = setup_logging()
        self.assertFalse(logger.handlers[0].console.stderr)


class TestSelectFromMenu(unittest.TestCase):
    @patch("git_nearit.utils.questionary.select")
    @patch("git_nearit.utils.logging.getLogger")
    def test_select_from_menu_success(self, mock_get_logger, mock_select) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_select.return_value.ask.return_value = "option1"
        result = select_from_menu("Choose:", ["option1", "option2"])
        self.assertEqual(result, "option1")
        # Verify logging calls
        mock_logger.info.assert_any_call("Choose:")
        mock_logger.info.assert_any_call("Selected: option1")

    @patch("git_nearit.utils.questionary.select")
    @patch("git_nearit.utils.logging.getLogger")
    def test_select_from_menu_cancelled(self, mock_get_logger, mock_select) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_select.return_value.ask.return_value = None
        with self.assertRaises(SystemExit) as cm:
            select_from_menu("Choose:", ["option1", "option2"])
        self.assertEqual(cm.exception.code, 1)
        mock_logger.error.assert_called_once_with("Selection cancelled")


class TestGetTextInput(unittest.TestCase):
    @patch("git_nearit.utils.questionary.text")
    @patch("git_nearit.utils.logging.getLogger")
    def test_get_text_input_success(self, mock_get_logger, mock_text) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_text.return_value.ask.return_value = "user input"
        result = get_text_input("Enter text:")
        self.assertEqual(result, "user input")
        mock_logger.info.assert_called_with("Enter text:")

    @patch("git_nearit.utils.questionary.text")
    @patch("git_nearit.utils.logging.getLogger")
    def test_get_text_input_cancelled(self, mock_get_logger, mock_text) -> None:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_text.return_value.ask.return_value = None
        with self.assertRaises(SystemExit) as cm:
            get_text_input("Enter text:")
        self.assertEqual(cm.exception.code, 1)
        mock_logger.error.assert_called_once_with("Input cancelled")


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

    @patch("git_nearit.utils.get_text_input")
    @patch("git_nearit.utils.select_from_menu")
    def test_get_pr_title_prompt_uses_shared_validation(self, mock_select, mock_input) -> None:
        mock_select.return_value = "fix"
        mock_input.return_value = "x"

        get_pr_title()

        mock_select.assert_called_once_with("Select PR/MR type:", PR_TYPES)
        validate = mock_input.call_args.kwargs["validate"]
        self.assertIs(validate("good-desc"), True)
        self.assertIsInstance(validate("Bad_Desc"), str)
        self.assertIsInstance(validate("a" * 31), str)


class TestValidatePrTitle(unittest.TestCase):
    def test_valid_titles(self) -> None:
        for title in ("feat/add-cli-desc", "fix/a", "ci/x1-2", "test/" + "a" * 30):
            with self.subTest(title=title):
                self.assertIsNone(validate_pr_title(title))
                self.assertTrue(PR_TITLE_PATTERN.fullmatch(title))

    def test_invalid_titles(self) -> None:
        for title in (
            "feature/add-cli-desc",  # bad type
            "feat/Add-Cli",  # uppercase
            "feat/" + "a" * 31,  # too long
            "[Draft] feat/x",  # draft prefix included
            "WIP: feat/x",  # draft prefix included
            "feat/",  # empty description
            "feat/a_b",  # underscore
            "feat",  # no separator
            "",
        ):
            with self.subTest(title=title):
                self.assertIsInstance(validate_pr_title(title), str)
                self.assertIsNone(PR_TITLE_PATTERN.fullmatch(title))


class TestNonInteractiveHelpers(unittest.TestCase):
    @patch("git_nearit.utils.sys.stdin")
    def test_is_interactive(self, mock_stdin) -> None:
        mock_stdin.isatty.return_value = True
        self.assertTrue(is_interactive())
        self.assertFalse(is_interactive(json_output=True))
        mock_stdin.isatty.return_value = False
        self.assertFalse(is_interactive())

    def test_commit_description(self) -> None:
        self.assertEqual(commit_description("subject", "body"), "subject\n\nbody")
        self.assertEqual(commit_description("subject", ""), "subject")
        self.assertEqual(commit_description("", ""), "")

    @patch("git_nearit.utils.sys.stdin", new_callable=lambda: io.StringIO("from stdin"))
    def test_read_message_file_stdin(self, _) -> None:
        self.assertEqual(read_message_file("-"), "from stdin")

    def test_read_message_file_path(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "desc.md"
            path.write_text("from file")
            self.assertEqual(read_message_file(str(path)), "from file")

    @patch("git_nearit.utils.sys.stdout", new_callable=io.StringIO)
    def test_emit_json(self, mock_stdout) -> None:
        emit_json({"a": 1})
        self.assertEqual(mock_stdout.getvalue(), '{"a": 1}\n')


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
