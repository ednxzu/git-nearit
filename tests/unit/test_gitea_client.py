import unittest
from unittest.mock import MagicMock, patch

from git import Repo

from git_nearit.models import Review, ReviewDetail
from git_nearit.clients.gitea_client import GiteaAPIError, GiteaClient
from git_nearit.models.git_repository import GitRepository
from tests.base import GitRepoTestCase


class TestGiteaClientInit(GitRepoTestCase):
    def test_init_with_token(self):
        client = GiteaClient(Repo(self.repo_path), token="test-token")

        self.assertEqual(client.hostname, "example.com")
        self.assertEqual(client.base_url, "https://example.com")
        self.assertEqual(client.owner, "test")
        self.assertEqual(client.repo_name, "repo")
        self.assertEqual(client.token, "test-token")
        self.assertEqual(client.api_url, "https://example.com/api/v1")

    def test_init_without_token_raises_error(self):
        with self.assertRaises(ValueError) as context:
            GiteaClient(Repo(self.repo_path))

        self.assertIn("No Gitea token found", str(context.exception))

    def test_init_with_custom_url(self):
        client = GiteaClient(
            Repo(self.repo_path),
            token="test-token",
            base_url="https://custom.example.com:8443",
        )

        self.assertEqual(client.base_url, "https://custom.example.com:8443")
        self.assertEqual(client.api_url, "https://custom.example.com:8443/api/v1")


class TestGiteaClientURLParsing(unittest.TestCase):
    def test_parse_ssh_url(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "git@github.com:owner/repo.git"

        client = GiteaClient(mock_repo, token="test-token")

        self.assertEqual(client.hostname, "github.com")
        self.assertEqual(client.base_url, "https://github.com")
        self.assertEqual(client.owner, "owner")
        self.assertEqual(client.repo_name, "repo")

    def test_parse_https_url(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "https://gitlab.com/owner/repo.git"

        client = GiteaClient(mock_repo, token="test-token")

        self.assertEqual(client.hostname, "gitlab.com")
        self.assertEqual(client.base_url, "https://gitlab.com")
        self.assertEqual(client.owner, "owner")
        self.assertEqual(client.repo_name, "repo")

    def test_parse_ssh_scheme_url_with_port(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "ssh://git@git.example.com:5022/owner/repo.git"

        client = GiteaClient(mock_repo, token="test-token")

        self.assertEqual(client.hostname, "git.example.com")
        self.assertEqual(client.base_url, "https://git.example.com")
        self.assertEqual(client.owner, "owner")
        self.assertEqual(client.repo_name, "repo")

    def test_parse_invalid_ssh_url_no_colon(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "git@invalid-url"

        with self.assertRaises(ValueError) as context:
            GiteaClient(mock_repo, token="test-token")

        self.assertIn("Invalid SSH remote URL", str(context.exception))

    def test_parse_invalid_ssh_url_bad_path(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "git@github.com:owner"

        with self.assertRaises(ValueError) as context:
            GiteaClient(mock_repo, token="test-token")

        self.assertIn("Invalid SSH remote URL", str(context.exception))

    def test_parse_invalid_https_url_bad_path(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "https://github.com/owner"

        with self.assertRaises(ValueError) as context:
            GiteaClient(mock_repo, token="test-token")

        self.assertIn("Invalid remote URL", str(context.exception))

    def test_parse_no_origin_remote(self):
        mock_repo = MagicMock()
        mock_repo.remote.side_effect = Exception("No origin")

        with self.assertRaises(ValueError) as context:
            GiteaClient(mock_repo, token="test-token")

        self.assertIn("Could not get origin remote URL", str(context.exception))


class TestGiteaClientAPI(GitRepoTestCase):
    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_check_existing_review_found(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = [
            {
                "title": "feat/test-feature",
                "html_url": "https://example.com/test/repo/pulls/1",
                "number": 1,
                "head": {"ref": "feat/test-branch"},
            }
        ]
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")
        review = client.check_existing_review("feat/test-branch", "main")

        # Type narrowing for type checker, rather than self.assertIsNotNone(review)
        assert review is not None
        self.assertEqual(review.title, "feat/test-feature")
        self.assertEqual(review.url, "https://example.com/test/repo/pulls/1")
        self.assertEqual(review.number, 1)

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_check_existing_review_not_found(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")
        review = client.check_existing_review("feat/test-branch", "main")

        self.assertIsNone(review)

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_create_review(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = True
        mock_response.json.return_value = {
            "title": "feat/new-feature",
            "html_url": "https://example.com/test/repo/pulls/2",
            "number": 2,
        }
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")
        review = client.create_review("feat/new-feature", "Description here", "feat/branch", "main")

        # Type narrowing for type checker, rather than self.assertIsInstance(review, Review)
        assert isinstance(review, Review)
        self.assertEqual(review.title, "feat/new-feature")
        self.assertEqual(review.url, "https://example.com/test/repo/pulls/2")
        self.assertEqual(review.number, 2)

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_api_error_handling(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")

        from requests.exceptions import HTTPError

        http_error = HTTPError()
        http_error.response = mock_response
        mock_request.side_effect = http_error

        client = GiteaClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GiteaAPIError) as context:
            client.create_review("title", "desc", "branch", "main")

        self.assertIn("HTTP 404", str(context.exception))

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_get_review(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = {
            "title": "feat/test-feature",
            "html_url": "https://example.com/test/repo/pulls/42",
            "number": 42,
            "head": {"ref": "change/20231215120000"},
            "base": {"ref": "main"},
        }
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")
        pr = client.get_review(42)

        # Type narrowing for type checker
        assert isinstance(pr, ReviewDetail)
        self.assertEqual(pr.title, "feat/test-feature")
        self.assertEqual(pr.number, 42)
        self.assertEqual(pr.source_branch, "change/20231215120000")
        self.assertEqual(pr.target_branch, "main")

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_get_review_not_found(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Pull request not found"
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")

        from requests.exceptions import HTTPError

        http_error = HTTPError()
        http_error.response = mock_response
        mock_request.side_effect = http_error

        client = GiteaClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GiteaAPIError) as context:
            client.get_review(999)

        self.assertIn("HTTP 404", str(context.exception))

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_list_reviews(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = [
            {
                "number": 1,
                "title": "feat/test-feature",
                "html_url": "https://example.com/test/repo/pulls/1",
                "state": "open",
                "draft": False,
                "user": {"login": "testuser"},
                "created_at": "2025-12-20T10:00:00Z",
                "updated_at": "2025-12-22T10:00:00Z",
                "head": {"ref": "feat/test-branch"},
                "base": {"ref": "main"},
            },
            {
                "number": 2,
                "title": "fix/bug-fix",
                "html_url": "https://example.com/test/repo/pulls/2",
                "state": "open",
                "draft": True,
                "user": {"login": "developer"},
                "created_at": "2025-12-21T10:00:00Z",
                "updated_at": "2025-12-22T12:00:00Z",
                "head": {"ref": "fix/bug-branch"},
                "base": {"ref": "main"},
            },
        ]
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")
        reviews = client.list_reviews("main")

        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0].number, 1)
        self.assertEqual(reviews[0].title, "feat/test-feature")
        self.assertEqual(reviews[0].author, "testuser")
        self.assertEqual(reviews[1].number, 2)
        self.assertEqual(reviews[1].draft, True)

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_list_reviews_empty(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")
        reviews = client.list_reviews("develop")

        self.assertEqual(len(reviews), 0)

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_list_reviews_with_state(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = [
            {
                "number": 3,
                "title": "merged-pr",
                "html_url": "https://example.com/test/repo/pulls/3",
                "state": "closed",
                "draft": False,
                "user": {"login": "testuser"},
                "created_at": "2025-12-20T10:00:00Z",
                "updated_at": "2025-12-22T10:00:00Z",
                "base": {"ref": "main"},
            }
        ]
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")
        reviews = client.list_reviews("main", state="closed")

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0].state, "closed")

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_list_reviews_uses_server_side_filtering(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = [
            {
                "number": 2,
                "title": "PR targeting develop",
                "html_url": "https://example.com/test/repo/pulls/2",
                "state": "open",
                "draft": False,
                "user": {"login": "testuser"},
                "created_at": "2025-12-20T10:00:00Z",
                "updated_at": "2025-12-22T10:00:00Z",
                "base": {"ref": "develop"},
                "head": {"ref": "feature-2"},
            },
        ]
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")
        reviews = client.list_reviews("develop")

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        self.assertIn("params", call_kwargs)
        self.assertEqual(call_kwargs["params"]["base_branch"], "develop")
        self.assertEqual(call_kwargs["params"]["state"], "open")

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0].number, 2)
        self.assertEqual(reviews[0].title, "PR targeting develop")

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_request_exception_handling(self, mock_request):
        from requests.exceptions import RequestException

        mock_request.side_effect = RequestException("Network error")

        client = GiteaClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GiteaAPIError) as context:
            client.check_existing_review("feat/test", "main")

        self.assertIn("Request failed", str(context.exception))

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_check_existing_review_generic_exception(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GiteaAPIError) as context:
            client.check_existing_review("feat/test", "main")

        self.assertIn("Failed to check existing reviews", str(context.exception))

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_create_review_generic_exception(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = True
        mock_response.json.side_effect = KeyError("missing key")
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GiteaAPIError) as context:
            client.create_review("title", "desc", "branch", "main")

        self.assertIn("Failed to create review", str(context.exception))

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_get_review_generic_exception(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.side_effect = KeyError("missing key")
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GiteaAPIError) as context:
            client.get_review(42)

        self.assertIn("Failed to get pull request", str(context.exception))

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_list_reviews_generic_exception(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.side_effect = ValueError("Invalid data")
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GiteaAPIError) as context:
            client.list_reviews("main")

        self.assertIn("Failed to list reviews", str(context.exception))

    def test_get_repository_info(self):
        client = GiteaClient(Repo(self.repo_path), token="test-token")
        info = client.get_repository_info()

        self.assertIsInstance(info, GitRepository)
        self.assertEqual(info.platform, "gitea")
        self.assertEqual(info.base_url, "https://example.com")
        self.assertEqual(info.hostname, "example.com")
        self.assertEqual(info.owner, "test")
        self.assertEqual(info.repo, "repo")

    @patch("git_nearit.clients.gitea_client.requests.request")
    def test_make_request_returns_none_on_204(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.content = False
        mock_request.return_value = mock_response

        client = GiteaClient(Repo(self.repo_path), token="test-token")
        result = client._make_request("DELETE", "/test")

        self.assertIsNone(result)
