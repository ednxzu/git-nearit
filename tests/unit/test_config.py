import os
import unittest
from unittest.mock import MagicMock, patch

from git_nearit.config import get_git_config, _parse_config_key


class TestParseConfigKey(unittest.TestCase):
    def test_parse_simple_key(self) -> None:
        section, option = _parse_config_key("user.name")
        self.assertEqual(section, "user")
        self.assertEqual(option, "name")

    def test_parse_multipart_key(self) -> None:
        section, option = _parse_config_key("nearit.gitea.example.com.token")
        self.assertEqual(section, 'nearit "gitea.example.com"')
        self.assertEqual(option, "token")

    def test_parse_three_part_key(self) -> None:
        section, option = _parse_config_key("section.subsection.option")
        self.assertEqual(section, 'section "subsection"')
        self.assertEqual(option, "option")

    def test_parse_invalid_key(self) -> None:
        with self.assertRaises(ValueError) as context:
            _parse_config_key("invalidkey")

        self.assertIn("Invalid config key", str(context.exception))


class TestGetGitConfig(unittest.TestCase):
    @patch("git_nearit.config.GitConfigParser")
    def test_get_simple_value(self, mock_parser_class) -> None:
        mock_parser = MagicMock()
        mock_parser.get_value.return_value = "test-value"
        mock_parser_class.return_value = mock_parser

        result = get_git_config("user.name")

        self.assertEqual(result, "test-value")
        mock_parser.get_value.assert_called_once_with("user", "name", default="")

    @patch("git_nearit.config.GitConfigParser")
    def test_get_env_variable(self, mock_parser_class) -> None:
        mock_parser = MagicMock()
        mock_parser.get_value.return_value = "env(TEST_VAR)"
        mock_parser_class.return_value = mock_parser

        with patch.dict(os.environ, {"TEST_VAR": "env-value"}):
            result = get_git_config("nearit.token")

        self.assertEqual(result, "env-value")

    @patch("git_nearit.config.GitConfigParser")
    def test_get_env_variable_not_set(self, mock_parser_class) -> None:
        mock_parser = MagicMock()
        mock_parser.get_value.return_value = "env(MISSING_VAR)"
        mock_parser_class.return_value = mock_parser

        result = get_git_config("nearit.token", default="default-val")

        self.assertEqual(result, "default-val")

    @patch("git_nearit.config.GitConfigParser")
    def test_get_with_exception_returns_default(self, mock_parser_class) -> None:
        mock_parser_class.side_effect = Exception("Config error")

        result = get_git_config("user.name", default="fallback")

        self.assertEqual(result, "fallback")

    @patch("git_nearit.config.GitConfigParser")
    def test_get_non_string_value(self, mock_parser_class) -> None:
        mock_parser = MagicMock()
        mock_parser.get_value.return_value = 123
        mock_parser_class.return_value = mock_parser

        result = get_git_config("some.number")

        self.assertEqual(result, "123")

    def test_get_from_repo_config(self) -> None:
        """Test that when repo is provided, it uses repo.config_reader()"""
        mock_repo = MagicMock()
        mock_config_reader = MagicMock()
        mock_config_reader.get_value.return_value = "repo-token"
        mock_repo.config_reader.return_value = mock_config_reader

        result = get_git_config("nearit.gitea.example.com.token", repo=mock_repo)

        self.assertEqual(result, "repo-token")
        mock_repo.config_reader.assert_called_once()
        mock_config_reader.get_value.assert_called_once_with(
            'nearit "gitea.example.com"', "token", default=""
        )

    @patch("git_nearit.config.GitConfigParser")
    def test_get_without_repo_uses_global_config(self, mock_parser_class) -> None:
        """Test that when repo is None, it uses GitConfigParser (global config)"""
        mock_parser = MagicMock()
        mock_parser.get_value.return_value = "global-token"
        mock_parser_class.return_value = mock_parser

        result = get_git_config("nearit.gitea.example.com.token", repo=None)

        self.assertEqual(result, "global-token")
        mock_parser_class.assert_called_once()
        mock_parser.get_value.assert_called_once_with(
            'nearit "gitea.example.com"', "token", default=""
        )

    def test_repo_config_with_env_variable(self) -> None:
        """Test that env() syntax works with repo config"""
        mock_repo = MagicMock()
        mock_config_reader = MagicMock()
        mock_config_reader.get_value.return_value = "env(REPO_TOKEN)"
        mock_repo.config_reader.return_value = mock_config_reader

        with patch.dict(os.environ, {"REPO_TOKEN": "my-repo-token"}):
            result = get_git_config("nearit.token", repo=mock_repo)

        self.assertEqual(result, "my-repo-token")
