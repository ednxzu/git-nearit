import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from git_nearit.clients.base_vcs_client import Review
from git_nearit.utils import display_reviews_table, format_relative_time


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
