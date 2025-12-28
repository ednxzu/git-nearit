import unittest
from unittest.mock import patch

from click.testing import CliRunner

from git_nearit.main import handle_review, lab_review, tea_review


class TestHandleReview(unittest.TestCase):
    @patch("git_nearit.main.run_review")
    def test_handle_review_submit_mode(self, mock_run_review):
        handle_review("gitea", target_branch=None, download=None, list=False, wip=False)
        mock_run_review.assert_called_once_with("gitea", None, False)

    @patch("git_nearit.main.run_review")
    def test_handle_review_submit_mode_with_branch(self, mock_run_review):
        handle_review("gitea", target_branch="develop", download=None, list=False, wip=False)
        mock_run_review.assert_called_once_with("gitea", "develop", False)

    @patch("git_nearit.main.run_review")
    def test_handle_review_submit_mode_with_wip(self, mock_run_review):
        handle_review("gitea", target_branch=None, download=None, list=False, wip=True)
        mock_run_review.assert_called_once_with("gitea", None, True)

    @patch("git_nearit.main.download_review")
    def test_handle_review_download_mode(self, mock_download_review):
        handle_review("gitea", target_branch=None, download=42, list=False, wip=False)
        mock_download_review.assert_called_once_with("gitea", 42)

    @patch("git_nearit.main.list_reviews")
    def test_handle_review_list_mode(self, mock_list_reviews):
        handle_review("gitea", target_branch=None, download=None, list=True, wip=False)
        mock_list_reviews.assert_called_once_with("gitea", None)

    @patch("git_nearit.main.list_reviews")
    def test_handle_review_list_mode_with_branch(self, mock_list_reviews):
        handle_review("gitea", target_branch="develop", download=None, list=True, wip=False)
        mock_list_reviews.assert_called_once_with("gitea", "develop")

    def test_handle_review_rejects_download_with_branch(self):
        with self.assertRaises(Exception) as cm:
            handle_review("gitea", target_branch="develop", download=42, list=False, wip=False)
        self.assertIn("download cannot be used with TARGET_BRANCH", str(cm.exception))

    def test_handle_review_rejects_wip_in_download_mode(self):
        with self.assertRaises(Exception) as cm:
            handle_review("gitea", target_branch=None, download=42, list=False, wip=True)
        self.assertIn("wip can only be used in submit mode", str(cm.exception))

    def test_handle_review_rejects_wip_in_list_mode(self):
        with self.assertRaises(Exception) as cm:
            handle_review("gitea", target_branch=None, download=None, list=True, wip=True)
        self.assertIn("wip can only be used in submit mode", str(cm.exception))

    @patch("git_nearit.main.download_review")
    @patch("git_nearit.main.list_reviews")
    def test_handle_review_rejects_multiple_modes(self, mock_list, mock_download):
        # This should be caught by the sum check
        with self.assertRaises(Exception):
            handle_review("gitea", target_branch=None, download=42, list=True, wip=False)


class TestTeaReview(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    @patch("git_nearit.main.run_review")
    def test_tea_review_no_args(self, mock_run_review):
        result = self.runner.invoke(tea_review, [])
        self.assertEqual(result.exit_code, 0)
        mock_run_review.assert_called_once_with("gitea", None, False)

    @patch("git_nearit.main.run_review")
    def test_tea_review_with_branch(self, mock_run_review):
        result = self.runner.invoke(tea_review, ["develop"])
        self.assertEqual(result.exit_code, 0)
        mock_run_review.assert_called_once_with("gitea", "develop", False)

    @patch("git_nearit.main.run_review")
    def test_tea_review_with_wip_flag(self, mock_run_review):
        result = self.runner.invoke(tea_review, ["-w"])
        self.assertEqual(result.exit_code, 0)
        mock_run_review.assert_called_once_with("gitea", None, True)

    @patch("git_nearit.main.download_review")
    def test_tea_review_download_flag(self, mock_download_review):
        result = self.runner.invoke(tea_review, ["-d", "42"])
        self.assertEqual(result.exit_code, 0)
        mock_download_review.assert_called_once_with("gitea", 42)

    @patch("git_nearit.main.list_reviews")
    def test_tea_review_list_flag(self, mock_list_reviews):
        result = self.runner.invoke(tea_review, ["-l"])
        self.assertEqual(result.exit_code, 0)
        mock_list_reviews.assert_called_once_with("gitea", None)

    @patch("git_nearit.main.list_reviews")
    def test_tea_review_list_flag_with_branch(self, mock_list_reviews):
        result = self.runner.invoke(tea_review, ["-l", "develop"])
        self.assertEqual(result.exit_code, 0)
        mock_list_reviews.assert_called_once_with("gitea", "develop")

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
        mock_run_review.assert_called_once_with("gitlab", None, False)

    @patch("git_nearit.main.run_review")
    def test_lab_review_with_branch(self, mock_run_review):
        result = self.runner.invoke(lab_review, ["develop"])
        self.assertEqual(result.exit_code, 0)
        mock_run_review.assert_called_once_with("gitlab", "develop", False)

    @patch("git_nearit.main.run_review")
    def test_lab_review_with_wip_flag(self, mock_run_review):
        result = self.runner.invoke(lab_review, ["-w"])
        self.assertEqual(result.exit_code, 0)
        mock_run_review.assert_called_once_with("gitlab", None, True)

    @patch("git_nearit.main.download_review")
    def test_lab_review_download_flag(self, mock_download_review):
        result = self.runner.invoke(lab_review, ["-d", "42"])
        self.assertEqual(result.exit_code, 0)
        mock_download_review.assert_called_once_with("gitlab", 42)

    @patch("git_nearit.main.list_reviews")
    def test_lab_review_list_flag(self, mock_list_reviews):
        result = self.runner.invoke(lab_review, ["-l"])
        self.assertEqual(result.exit_code, 0)
        mock_list_reviews.assert_called_once_with("gitlab", None)

    @patch("git_nearit.main.list_reviews")
    def test_lab_review_list_flag_with_branch(self, mock_list_reviews):
        result = self.runner.invoke(lab_review, ["-l", "develop"])
        self.assertEqual(result.exit_code, 0)
        mock_list_reviews.assert_called_once_with("gitlab", "develop")

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
