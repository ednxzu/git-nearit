import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import click
from click.testing import CliRunner

from git_nearit.main import handle_review, lab_review, tea_review

SUBMIT_DEFAULTS = {"title": None, "description": None, "no_edit": False, "json_output": False}


class TestHandleReview(unittest.TestCase):
    @patch("git_nearit.main.run_review")
    def test_handle_review_submit_mode(self, mock_run_review):
        handle_review(
            "gitea", target_branch=None, download=None, list=False, wip=False, ready=False
        )
        mock_run_review.assert_called_once_with("gitea", None, False, False, **SUBMIT_DEFAULTS)

    @patch("git_nearit.main.run_review")
    def test_handle_review_submit_mode_with_branch(self, mock_run_review):
        handle_review(
            "gitea", target_branch="develop", download=None, list=False, wip=False, ready=False
        )
        mock_run_review.assert_called_once_with("gitea", "develop", False, False, **SUBMIT_DEFAULTS)

    @patch("git_nearit.main.run_review")
    def test_handle_review_submit_mode_with_wip(self, mock_run_review):
        handle_review("gitea", target_branch=None, download=None, list=False, wip=True, ready=False)
        mock_run_review.assert_called_once_with("gitea", None, True, False, **SUBMIT_DEFAULTS)

    @patch("git_nearit.main.download_review")
    def test_handle_review_download_mode(self, mock_download_review):
        handle_review("gitea", target_branch=None, download=42, list=False, wip=False, ready=False)
        mock_download_review.assert_called_once_with("gitea", 42)

    @patch("git_nearit.main.list_reviews")
    def test_handle_review_list_mode(self, mock_list_reviews):
        handle_review("gitea", target_branch=None, download=None, list=True, wip=False, ready=False)
        mock_list_reviews.assert_called_once_with("gitea", None, json_output=False)

    @patch("git_nearit.main.list_reviews")
    def test_handle_review_list_mode_with_branch(self, mock_list_reviews):
        handle_review(
            "gitea", target_branch="develop", download=None, list=True, wip=False, ready=False
        )
        mock_list_reviews.assert_called_once_with("gitea", "develop", json_output=False)

    def test_handle_review_rejects_download_with_branch(self):
        with self.assertRaises(Exception) as cm:
            handle_review(
                "gitea", target_branch="develop", download=42, list=False, wip=False, ready=False
            )
        self.assertIn("download cannot be used with TARGET_BRANCH", str(cm.exception))

    def test_handle_review_rejects_wip_in_download_mode(self):
        with self.assertRaises(Exception) as cm:
            handle_review(
                "gitea", target_branch=None, download=42, list=False, wip=True, ready=False
            )
        self.assertIn("wip can only be used in submit mode", str(cm.exception))

    def test_handle_review_rejects_wip_in_list_mode(self):
        with self.assertRaises(Exception) as cm:
            handle_review(
                "gitea", target_branch=None, download=None, list=True, wip=True, ready=False
            )
        self.assertIn("wip can only be used in submit mode", str(cm.exception))

    @patch("git_nearit.main.download_review")
    @patch("git_nearit.main.list_reviews")
    def test_handle_review_rejects_multiple_modes(self, mock_list, mock_download):
        # This should be caught by the sum check
        with self.assertRaises(click.UsageError):
            handle_review(
                "gitea", target_branch=None, download=42, list=True, wip=False, ready=False
            )


class TestTeaReview(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    @patch("git_nearit.main.run_review")
    def test_tea_review_no_args(self, mock_run_review):
        result = self.runner.invoke(tea_review, [])
        self.assertEqual(result.exit_code, 0)
        mock_run_review.assert_called_once_with("gitea", None, False, False, **SUBMIT_DEFAULTS)

    @patch("git_nearit.main.run_review")
    def test_tea_review_with_branch(self, mock_run_review):
        result = self.runner.invoke(tea_review, ["develop"])
        self.assertEqual(result.exit_code, 0)
        mock_run_review.assert_called_once_with("gitea", "develop", False, False, **SUBMIT_DEFAULTS)

    @patch("git_nearit.main.run_review")
    def test_tea_review_with_wip_flag(self, mock_run_review):
        result = self.runner.invoke(tea_review, ["-w"])
        self.assertEqual(result.exit_code, 0)
        mock_run_review.assert_called_once_with("gitea", None, True, False, **SUBMIT_DEFAULTS)

    @patch("git_nearit.main.download_review")
    def test_tea_review_download_flag(self, mock_download_review):
        result = self.runner.invoke(tea_review, ["-d", "42"])
        self.assertEqual(result.exit_code, 0)
        mock_download_review.assert_called_once_with("gitea", 42)

    @patch("git_nearit.main.list_reviews")
    def test_tea_review_list_flag(self, mock_list_reviews):
        result = self.runner.invoke(tea_review, ["-l"])
        self.assertEqual(result.exit_code, 0)
        mock_list_reviews.assert_called_once_with("gitea", None, json_output=False)

    @patch("git_nearit.main.list_reviews")
    def test_tea_review_list_flag_with_branch(self, mock_list_reviews):
        result = self.runner.invoke(tea_review, ["-l", "develop"])
        self.assertEqual(result.exit_code, 0)
        mock_list_reviews.assert_called_once_with("gitea", "develop", json_output=False)

    def test_tea_review_download_and_list_rejected(self):
        result = self.runner.invoke(tea_review, ["-d", "42", "-l"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("must use exactly one mode", result.output)

    def test_tea_review_download_with_branch_rejected(self):
        result = self.runner.invoke(tea_review, ["-d", "42", "develop"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("download cannot be used with TARGET_BRANCH", result.output)

    def test_tea_review_wip_with_download_rejected(self):
        result = self.runner.invoke(tea_review, ["-w", "-d", "42"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("wip can only be used in submit mode", result.output)

    def test_tea_review_wip_with_list_rejected(self):
        result = self.runner.invoke(tea_review, ["-w", "-l"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("wip can only be used in submit mode", result.output)


class TestLabReview(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    @patch("git_nearit.main.run_review")
    def test_lab_review_no_args(self, mock_run_review):
        result = self.runner.invoke(lab_review, [])
        self.assertEqual(result.exit_code, 0)
        mock_run_review.assert_called_once_with("gitlab", None, False, False, **SUBMIT_DEFAULTS)

    @patch("git_nearit.main.run_review")
    def test_lab_review_with_branch(self, mock_run_review):
        result = self.runner.invoke(lab_review, ["develop"])
        self.assertEqual(result.exit_code, 0)
        mock_run_review.assert_called_once_with(
            "gitlab", "develop", False, False, **SUBMIT_DEFAULTS
        )

    @patch("git_nearit.main.run_review")
    def test_lab_review_with_wip_flag(self, mock_run_review):
        result = self.runner.invoke(lab_review, ["-w"])
        self.assertEqual(result.exit_code, 0)
        mock_run_review.assert_called_once_with("gitlab", None, True, False, **SUBMIT_DEFAULTS)

    @patch("git_nearit.main.download_review")
    def test_lab_review_download_flag(self, mock_download_review):
        result = self.runner.invoke(lab_review, ["-d", "42"])
        self.assertEqual(result.exit_code, 0)
        mock_download_review.assert_called_once_with("gitlab", 42)

    @patch("git_nearit.main.list_reviews")
    def test_lab_review_list_flag(self, mock_list_reviews):
        result = self.runner.invoke(lab_review, ["-l"])
        self.assertEqual(result.exit_code, 0)
        mock_list_reviews.assert_called_once_with("gitlab", None, json_output=False)

    @patch("git_nearit.main.list_reviews")
    def test_lab_review_list_flag_with_branch(self, mock_list_reviews):
        result = self.runner.invoke(lab_review, ["-l", "develop"])
        self.assertEqual(result.exit_code, 0)
        mock_list_reviews.assert_called_once_with("gitlab", "develop", json_output=False)

    def test_lab_review_download_and_list_rejected(self):
        result = self.runner.invoke(lab_review, ["-d", "42", "-l"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("must use exactly one mode", result.output)

    def test_lab_review_download_with_branch_rejected(self):
        result = self.runner.invoke(lab_review, ["-d", "42", "develop"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("download cannot be used with TARGET_BRANCH", result.output)

    def test_lab_review_wip_with_download_rejected(self):
        result = self.runner.invoke(lab_review, ["-w", "-d", "42"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("wip can only be used in submit mode", result.output)

    def test_lab_review_wip_with_list_rejected(self):
        result = self.runner.invoke(lab_review, ["-w", "-l"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("wip can only be used in submit mode", result.output)


class TestNonInteractiveFlags(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    @patch("git_nearit.main.run_review")
    def test_title_and_message_passed_through(self, mock_run_review):
        result = self.runner.invoke(lab_review, ["-t", "feat/add-cli-desc", "-m", "  Body  "])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_run_review.assert_called_once_with(
            "gitlab",
            None,
            False,
            False,
            title="feat/add-cli-desc",
            description="Body",
            no_edit=False,
            json_output=False,
        )

    @patch("git_nearit.main.run_review")
    def test_message_file_from_stdin(self, mock_run_review):
        result = self.runner.invoke(tea_review, ["-F", "-"], input="## Summary\nfrom stdin\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(mock_run_review.call_args.kwargs["description"], "## Summary\nfrom stdin")

    @patch("git_nearit.main.run_review")
    def test_message_file_from_path(self, mock_run_review):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "desc.md"
            path.write_text("from file\n")
            result = self.runner.invoke(lab_review, ["--message-file", str(path)])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(mock_run_review.call_args.kwargs["description"], "from file")

    @patch("git_nearit.main.run_review")
    def test_no_edit_passed_through(self, mock_run_review):
        result = self.runner.invoke(lab_review, ["--no-edit"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(mock_run_review.call_args.kwargs["no_edit"])
        self.assertIsNone(mock_run_review.call_args.kwargs["description"])

    @patch("git_nearit.main.run_review")
    def test_description_sources_mutually_exclusive(self, mock_run_review):
        for args in (
            ["-m", "x", "--no-edit"],
            ["-m", "x", "-F", "-"],
            ["-F", "-", "--no-edit"],
        ):
            with self.subTest(args=args):
                result = self.runner.invoke(lab_review, args, input="x")
                self.assertEqual(result.exit_code, 2)
                self.assertIn("are mutually exclusive flags", result.output)
        mock_run_review.assert_not_called()

    def test_submit_only_flags_rejected_in_other_modes(self):
        for mode in (["-l"], ["-d", "42"]):
            for args in (["-t", "feat/x"], ["-m", "x"], ["-F", "-"], ["--no-edit"]):
                with self.subTest(mode=mode, args=args):
                    result = self.runner.invoke(tea_review, mode + args, input="x")
                    self.assertEqual(result.exit_code, 2)
                    self.assertIn("can only be used in submit mode", result.output)

    @patch("git_nearit.main.run_review")
    def test_missing_message_file_rejected(self, mock_run_review):
        result = self.runner.invoke(lab_review, ["-F", "/nonexistent/desc.md"])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("Could not read --message-file '/nonexistent/desc.md'", result.stderr)
        self.assertEqual(result.stdout, "")
        mock_run_review.assert_not_called()

    @patch("git_nearit.main.run_review")
    def test_missing_message_file_with_json_emits_error(self, mock_run_review):
        result = self.runner.invoke(lab_review, ["--json", "-F", "/nonexistent/desc.md"])
        self.assertEqual(result.exit_code, 2)
        error = json.loads(result.stdout)["error"]
        self.assertIn("Could not read --message-file '/nonexistent/desc.md'", error)
        mock_run_review.assert_not_called()

    def test_invalid_title_rejected(self):
        result = self.runner.invoke(lab_review, ["-t", "Feature/Bad"])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("Invalid --title", result.output)

    def test_empty_message_rejected(self):
        result = self.runner.invoke(lab_review, ["-m", "   "])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("Empty description", result.output)

    def test_empty_message_file_rejected(self):
        result = self.runner.invoke(lab_review, ["-F", "-"], input="\n\n")
        self.assertEqual(result.exit_code, 2)
        self.assertIn("Empty description", result.output)

    @patch("git_nearit.main.list_reviews")
    def test_json_accepted_in_list_mode(self, mock_list_reviews):
        result = self.runner.invoke(lab_review, ["-l", "--json"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_list_reviews.assert_called_once_with("gitlab", None, json_output=True)

    @patch("git_nearit.main.run_review")
    def test_json_accepted_in_submit_mode(self, mock_run_review):
        result = self.runner.invoke(tea_review, ["--json"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(mock_run_review.call_args.kwargs["json_output"])

    @patch("git_nearit.main.download_review")
    def test_json_rejected_with_download(self, mock_download_review):
        result = self.runner.invoke(lab_review, ["-d", "42", "--json"])
        self.assertEqual(result.exit_code, 2)
        mock_download_review.assert_not_called()
        self.assertIn("--json can only be used in submit or list mode", result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {"error": "--json can only be used in submit or list mode"},
        )

    def test_usage_error_without_json_prints_nothing_on_stdout(self):
        result = self.runner.invoke(lab_review, ["-d", "42", "-t", "feat/x"])
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.stdout, "")

    def test_handle_review_rejects_title_in_list_mode(self):
        with self.assertRaises(click.UsageError) as cm:
            handle_review(
                "gitea",
                target_branch=None,
                download=None,
                list=True,
                wip=False,
                ready=False,
                title="feat/x",
            )
        self.assertIn("--title can only be used in submit mode", str(cm.exception))
