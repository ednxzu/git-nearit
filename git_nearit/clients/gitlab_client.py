from typing import Optional
from urllib.parse import quote

import requests
from git import Repo

from git_nearit.clients.base_vcs_client import BaseVCSClient, PullRequest, Review
from git_nearit.config import get_git_config
from git_nearit.models.git_repository import GitRepository


class GitlabAPIError(Exception):
    pass


class GitLabClient(BaseVCSClient):
    def __init__(self, repo: Repo, token: Optional[str] = None, base_url: Optional[str] = None):
        self.repo = repo

        repo_info = self._parse_remote_url(repo)
        self.hostname = repo_info["hostname"]
        self.owner = repo_info["owner"]
        self.repo_name = repo_info["repo"]
        self.full_path = repo_info["full_path"]
        self.project_id = quote(self.full_path, safe="")

        if base_url:
            self.base_url = base_url
        else:
            url_config_key = f"nearit.gitlab.{self.hostname}.url"
            custom_url = get_git_config(url_config_key)
            self.base_url = custom_url if custom_url else repo_info["base_url"]

        if token:
            self.token = token
        else:
            config_key = f"nearit.gitlab.{self.hostname}.token"
            self.token = get_git_config(config_key)

            if not self.token:
                raise ValueError(
                    f"No gitlab token found for {self.hostname}.\n"
                    f"Please configure it with:\n"
                    f"  git config {config_key} YOUR_TOKEN\n"
                    f"or use an environment variable:\n"
                    f"  git config {config_key} env(GITLAB_TOKEN)"
                )

        self.api_url = f"{self.base_url}/api/v4"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _make_request(self, method: str, route: str, json_data: Optional[dict] = None, **kwargs):
        url = f"{self.api_url}{route}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=json_data,
                timeout=30,
                **kwargs,
            )
            response.raise_for_status()

            if response.status_code != 204 and response.content:
                return response.json()
            return None

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code} error on {method} {route}"
            try:
                error_detail = e.response.json()
                raise GitlabAPIError(f"{error_msg}: {error_detail}") from e
            except Exception:
                raise GitlabAPIError(f"{error_msg}: {e.response.text}") from e

        except requests.exceptions.RequestException as e:
            raise GitlabAPIError(f"Request failed on {route}: {e}") from e

    def check_existing_review(self, source_branch: str, target_branch: str) -> Optional[Review]:
        route = f"/projects/{self.project_id}/merge_requests"
        params = {"state": "opened", "source_branch": source_branch, "target_branch": target_branch}

        try:
            merges = self._make_request(method="GET", route=route, params=params)

            if len(merges) > 0:
                return Review(
                    title=merges[0]["title"], url=merges[0]["web_url"], number=merges[0]["iid"]
                )

            return None
        except GitlabAPIError:
            raise
        except Exception as e:
            raise GitlabAPIError(f"Failed to check existing reviews: {e}") from e

    def create_review(
        self, title: str, description: str, source_branch: str, target_branch: str
    ) -> Review:
        route = f"/projects/{self.project_id}/merge_requests"
        data = {
            "title": title,
            "description": description,
            "source_branch": source_branch,
            "target_branch": target_branch,
        }

        try:
            result = self._make_request(method="POST", route=route, json_data=data)
            return Review(
                title=result["title"],
                url=result["web_url"],
                number=result["iid"],
            )
        except GitlabAPIError:
            raise
        except Exception as e:
            raise GitlabAPIError(f"Failed to create review: {e}") from e

    def get_pull_request(self, pr_id: int) -> PullRequest:
        route = f"/projects/{self.project_id}/merge_requests/{pr_id}"

        try:
            result = self._make_request(method="GET", route=route)
            return PullRequest(
                number=pr_id,
                title=result["title"],
                source_branch=result["source_branch"],
                target_branch=result["target_branch"],
            )
        except GitlabAPIError:
            raise
        except Exception as e:
            raise GitlabAPIError(f"Failed to get merge request {pr_id}: {e}") from e

    def get_repository_info(self) -> GitRepository:
        return GitRepository(
            platform="gitlab",
            base_url=self.base_url,
            hostname=self.hostname,
            owner=self.owner,
            repo=self.repo_name,
        )

    def list_reviews(self, base_branch: str, state: str = "opened") -> list[Review]:
        route = f"/projects/{self.project_id}/merge_requests"
        params = {"state": state, "target_branch": base_branch}

        try:
            merges = self._make_request(method="GET", route=route, params=params)
            if not merges:
                return []

            reviews = []
            for mr in merges:
                review = Review(
                    title=mr.get("title", ""),
                    url=mr.get("web_url", ""),
                    number=mr.get("iid", 0),
                    author=mr.get("author", {}).get("name"),
                    state=mr.get("state"),
                    draft=mr.get("draft", False),
                    created_at=mr.get("created_at"),
                    updated_at=mr.get("updated_at"),
                )
                reviews.append(review)
            return reviews
        except GitlabAPIError:
            raise
        except Exception as e:
            raise GitlabAPIError(f"Failed to list reviews for branch {base_branch}: {e}") from e
