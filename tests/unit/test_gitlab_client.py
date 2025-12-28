import unittest
from unittest.mock import MagicMock, patch

from git import Repo

from git_nearit.models import Review, ReviewDetail
from git_nearit.clients.gitlab_client import GitLabClient, GitlabAPIError
from git_nearit.models.git_repository import GitRepository
from tests.base import GitRepoTestCase


class TestGitLabClientInit(GitRepoTestCase):
    def test_init_with_token(self):
        client = GitLabClient(Repo(self.repo_path), token="test-token")

        self.assertEqual(client.hostname, "example.com")
        self.assertEqual(client.base_url, "https://example.com")
        self.assertEqual(client.owner, "test")
        self.assertEqual(client.repo_name, "repo")
        self.assertEqual(client.full_path, "test/repo")
        self.assertEqual(client.project_id, "test%2Frepo")
        self.assertEqual(client.token, "test-token")
        self.assertEqual(client.api_url, "https://example.com/api/v4")

    def test_init_without_token_raises_error(self):
        with self.assertRaises(ValueError) as context:
            GitLabClient(Repo(self.repo_path))

        self.assertIn("No gitlab token found", str(context.exception))

    def test_init_with_custom_url(self):
        client = GitLabClient(
            Repo(self.repo_path),
            token="test-token",
            base_url="https://custom.gitlab.com:8443",
        )

        self.assertEqual(client.base_url, "https://custom.gitlab.com:8443")
        self.assertEqual(client.api_url, "https://custom.gitlab.com:8443/api/v4")


class TestGitLabClientURLParsing(unittest.TestCase):
    def test_parse_ssh_url(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "git@gitlab.com:owner/repo.git"

        client = GitLabClient(mock_repo, token="test-token")

        self.assertEqual(client.hostname, "gitlab.com")
        self.assertEqual(client.base_url, "https://gitlab.com")
        self.assertEqual(client.owner, "owner")
        self.assertEqual(client.repo_name, "repo")
        self.assertEqual(client.full_path, "owner/repo")

    def test_parse_https_url(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "https://gitlab.com/owner/repo.git"

        client = GitLabClient(mock_repo, token="test-token")

        self.assertEqual(client.hostname, "gitlab.com")
        self.assertEqual(client.base_url, "https://gitlab.com")
        self.assertEqual(client.owner, "owner")
        self.assertEqual(client.repo_name, "repo")
        self.assertEqual(client.full_path, "owner/repo")

    def test_parse_ssh_url_with_groups(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "git@gitlab.com:group/subgroup/repo.git"

        client = GitLabClient(mock_repo, token="test-token")

        self.assertEqual(client.hostname, "gitlab.com")
        self.assertEqual(client.base_url, "https://gitlab.com")
        self.assertEqual(client.owner, "group/subgroup")
        self.assertEqual(client.repo_name, "repo")
        self.assertEqual(client.full_path, "group/subgroup/repo")
        self.assertEqual(client.project_id, "group%2Fsubgroup%2Frepo")

    def test_parse_ssh_scheme_url_with_port(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "ssh://git@gitlab.example.com:5022/owner/repo.git"

        client = GitLabClient(mock_repo, token="test-token")

        self.assertEqual(client.hostname, "gitlab.example.com")
        self.assertEqual(client.base_url, "https://gitlab.example.com")
        self.assertEqual(client.owner, "owner")
        self.assertEqual(client.repo_name, "repo")

    def test_parse_invalid_ssh_url_no_colon(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "git@invalid-url"

        with self.assertRaises(ValueError) as context:
            GitLabClient(mock_repo, token="test-token")

        self.assertIn("Invalid SSH remote URL", str(context.exception))

    def test_parse_invalid_ssh_url_bad_path(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "git@gitlab.com:owner"

        with self.assertRaises(ValueError) as context:
            GitLabClient(mock_repo, token="test-token")

        self.assertIn("Invalid SSH remote URL", str(context.exception))

    def test_parse_invalid_https_url_bad_path(self):
        mock_repo = MagicMock()
        mock_repo.remote.return_value.url = "https://gitlab.com/owner"

        with self.assertRaises(ValueError) as context:
            GitLabClient(mock_repo, token="test-token")

        self.assertIn("Invalid remote URL", str(context.exception))

    def test_parse_no_origin_remote(self):
        mock_repo = MagicMock()
        mock_repo.remote.side_effect = Exception("No origin")

        with self.assertRaises(ValueError) as context:
            GitLabClient(mock_repo, token="test-token")

        self.assertIn("Could not get origin remote URL", str(context.exception))


class TestGitLabClientAPI(GitRepoTestCase):
    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_check_existing_review_found(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = [
            {
                "title": "feat/test-feature",
                "web_url": "https://gitlab.com/test/repo/-/merge_requests/1",
                "iid": 1,
            }
        ]
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")
        review = client.check_existing_review("feat/test-branch", "main")

        # Type narrowing for type checker, rather than self.assertIsNotNone(review)
        assert review is not None
        self.assertEqual(review.title, "feat/test-feature")
        self.assertEqual(review.url, "https://gitlab.com/test/repo/-/merge_requests/1")
        self.assertEqual(review.number, 1)

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_check_existing_review_not_found(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")
        review = client.check_existing_review("feat/test-branch", "main")

        self.assertIsNone(review)

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_create_review(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = True
        mock_response.json.return_value = {
            "title": "feat/new-feature",
            "web_url": "https://gitlab.com/test/repo/-/merge_requests/2",
            "iid": 2,
        }
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")
        review = client.create_review("feat/new-feature", "Description here", "feat/branch", "main")

        # Type narrowing for type checker, rather than self.assertIsInstance(review, Review)
        assert isinstance(review, Review)
        self.assertEqual(review.title, "feat/new-feature")
        self.assertEqual(review.url, "https://gitlab.com/test/repo/-/merge_requests/2")
        self.assertEqual(review.number, 2)

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_create_review_with_wip(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = True
        mock_response.json.return_value = {
            "title": "[Draft] feat/new-feature",
            "web_url": "https://gitlab.com/test/repo/-/merge_requests/3",
            "iid": 3,
        }
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")
        review = client.create_review(
            "feat/new-feature", "Description here", "feat/branch", "main", wip=True
        )

        # Type narrowing for type checker, rather than self.assertIsInstance(review, Review)
        assert isinstance(review, Review)
        self.assertEqual(review.title, "[Draft] feat/new-feature")
        self.assertEqual(review.url, "https://gitlab.com/test/repo/-/merge_requests/3")
        self.assertEqual(review.number, 3)

        # Verify the API was called with the Draft prefix
        call_args = mock_request.call_args
        json_data = call_args[1]["json"]
        self.assertEqual(json_data["title"], "[Draft] feat/new-feature")

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_api_error_handling(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")

        from requests.exceptions import HTTPError

        http_error = HTTPError()
        http_error.response = mock_response
        mock_request.side_effect = http_error

        client = GitLabClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GitlabAPIError) as context:
            client.create_review("title", "desc", "branch", "main")

        self.assertIn("HTTP 404", str(context.exception))

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_get_review(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = {
            "title": "feat/test-feature",
            "web_url": "https://gitlab.com/test/repo/-/merge_requests/42",
            "iid": 42,
            "source_branch": "change/20231215120000",
            "target_branch": "main",
        }
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")
        pr = client.get_review(42)

        # Type narrowing for type checker
        assert isinstance(pr, ReviewDetail)
        self.assertEqual(pr.title, "feat/test-feature")
        self.assertEqual(pr.number, 42)
        self.assertEqual(pr.source_branch, "change/20231215120000")
        self.assertEqual(pr.target_branch, "main")

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_get_review_not_found(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Merge request not found"
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")

        from requests.exceptions import HTTPError

        http_error = HTTPError()
        http_error.response = mock_response
        mock_request.side_effect = http_error

        client = GitLabClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GitlabAPIError) as context:
            client.get_review(999)

        self.assertIn("HTTP 404", str(context.exception))

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_list_reviews(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = [
            {
                "iid": 1,
                "title": "feat/test-feature",
                "web_url": "https://gitlab.com/test/repo/-/merge_requests/1",
                "state": "opened",
                "draft": False,
                "author": {"name": "Test User"},
                "created_at": "2025-12-20T10:00:00Z",
                "updated_at": "2025-12-22T10:00:00Z",
            },
            {
                "iid": 2,
                "title": "fix/bug-fix",
                "web_url": "https://gitlab.com/test/repo/-/merge_requests/2",
                "state": "opened",
                "draft": True,
                "author": {"name": "Developer"},
                "created_at": "2025-12-21T10:00:00Z",
                "updated_at": "2025-12-22T12:00:00Z",
            },
        ]
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")
        reviews = client.list_reviews("main")

        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0].number, 1)
        self.assertEqual(reviews[0].title, "feat/test-feature")
        self.assertEqual(reviews[0].author, "Test User")
        self.assertEqual(reviews[1].number, 2)
        self.assertEqual(reviews[1].draft, True)

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_list_reviews_empty(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")
        reviews = client.list_reviews("develop")

        self.assertEqual(len(reviews), 0)

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_list_reviews_with_state(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = [
            {
                "iid": 3,
                "title": "merged-mr",
                "web_url": "https://gitlab.com/test/repo/-/merge_requests/3",
                "state": "merged",
                "draft": False,
                "author": {"name": "Test User"},
                "created_at": "2025-12-20T10:00:00Z",
                "updated_at": "2025-12-22T10:00:00Z",
            }
        ]
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")
        reviews = client.list_reviews("main", state="merged")

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0].state, "merged")

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_list_reviews_uses_server_side_filtering(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = [
            {
                "iid": 2,
                "title": "MR targeting develop",
                "web_url": "https://gitlab.com/test/repo/-/merge_requests/2",
                "state": "opened",
                "draft": False,
                "author": {"name": "Test User"},
                "created_at": "2025-12-20T10:00:00Z",
                "updated_at": "2025-12-22T10:00:00Z",
            },
        ]
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")
        reviews = client.list_reviews("develop")

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        self.assertIn("params", call_kwargs)
        self.assertEqual(call_kwargs["params"]["target_branch"], "develop")
        self.assertEqual(call_kwargs["params"]["state"], "opened")

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0].number, 2)
        self.assertEqual(reviews[0].title, "MR targeting develop")

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_request_exception_handling(self, mock_request):
        from requests.exceptions import RequestException

        mock_request.side_effect = RequestException("Network error")

        client = GitLabClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GitlabAPIError) as context:
            client.check_existing_review("feat/test", "main")

        self.assertIn("Request failed", str(context.exception))

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_check_existing_review_generic_exception(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GitlabAPIError) as context:
            client.check_existing_review("feat/test", "main")

        self.assertIn("Failed to check existing reviews", str(context.exception))

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_create_review_generic_exception(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = True
        mock_response.json.side_effect = KeyError("missing key")
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GitlabAPIError) as context:
            client.create_review("title", "desc", "branch", "main")

        self.assertIn("Failed to create review", str(context.exception))

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_get_review_generic_exception(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.side_effect = KeyError("missing key")
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GitlabAPIError) as context:
            client.get_review(42)

        self.assertIn("Failed to get merge request", str(context.exception))

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_list_reviews_generic_exception(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.side_effect = ValueError("Invalid data")
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")

        with self.assertRaises(GitlabAPIError) as context:
            client.list_reviews("main")

        self.assertIn("Failed to list reviews", str(context.exception))

    def test_get_repository_info(self):
        client = GitLabClient(Repo(self.repo_path), token="test-token")
        info = client.get_repository_info()

        self.assertIsInstance(info, GitRepository)
        self.assertEqual(info.platform, "gitlab")
        self.assertEqual(info.base_url, "https://example.com")
        self.assertEqual(info.hostname, "example.com")
        self.assertEqual(info.owner, "test")
        self.assertEqual(info.repo, "repo")

    @patch("git_nearit.clients.gitlab_client.requests.request")
    def test_make_request_returns_none_on_204(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.content = False
        mock_request.return_value = mock_response

        client = GitLabClient(Repo(self.repo_path), token="test-token")
        result = client._make_request("DELETE", "/test")

        self.assertIsNone(result)
