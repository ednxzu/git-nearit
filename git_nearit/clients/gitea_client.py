from typing import Optional

import requests
from git import Repo

from git_nearit.clients.base_vcs_client import BaseVCSClient
from git_nearit.config import get_git_config
from git_nearit.models import Review, GitRepository, ReviewListItem, ReviewDetail


class GiteaAPIError(Exception):
    pass


class GiteaClient(BaseVCSClient):
    def __init__(self, repo: Repo, token: Optional[str] = None, base_url: Optional[str] = None):
        self.repo = repo

        repo_info = self._parse_remote_url(repo)
        self.hostname = repo_info["hostname"]
        self.owner = repo_info["owner"]
        self.repo_name = repo_info["repo"]

        if base_url:
            self.base_url = base_url
        else:
            url_config_key = f"nearit.gitea.{self.hostname}.url"
            custom_url = get_git_config(url_config_key)
            self.base_url = custom_url if custom_url else repo_info["base_url"]

        if token:
            self.token = token
        else:
            config_key = f"nearit.gitea.{self.hostname}.token"
            self.token = get_git_config(config_key)

            if not self.token:
                raise ValueError(
                    f"No Gitea token found for {self.hostname}.\n"
                    f"Please configure it with:\n"
                    f"  git config {config_key} YOUR_TOKEN\n"
                    f"or use an environment variable:\n"
                    f"  git config {config_key} env(GITEA_TOKEN)"
                )

        self.api_url = f"{self.base_url}/api/v1"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
        }
        self.draft_prefix = "WIP: "

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
                raise GiteaAPIError(f"{error_msg}: {error_detail}") from e
            except Exception:
                raise GiteaAPIError(f"{error_msg}: {e.response.text}") from e

        except requests.exceptions.RequestException as e:
            raise GiteaAPIError(f"Request failed on {route}: {e}") from e

    def check_existing_review(self, source_branch: str, target_branch: str) -> Optional[Review]:
        route = f"/repos/{self.owner}/{self.repo_name}/pulls"
        params = {"state": "open"}

        try:
            pulls = self._make_request("GET", route, params=params)

            for pr in pulls:
                if pr.get("head", {}).get("ref") == source_branch:
                    return Review(
                        title=pr["title"],
                        url=pr["html_url"],
                        number=pr["number"],
                    )

            return None
        except GiteaAPIError:
            raise
        except Exception as e:
            raise GiteaAPIError(f"Failed to check existing reviews: {e}") from e

    def create_review(
        self,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str,
        draft: bool = False,
    ) -> Review:
        route = f"/repos/{self.owner}/{self.repo_name}/pulls"

        if draft:
            title = self._add_prefix(text=title, prefix=self.draft_prefix)

        data = {
            "title": title,
            "body": description,
            "head": source_branch,
            "base": target_branch,
        }

        try:
            result = self._make_request("POST", route, json_data=data)
            return Review(
                title=result["title"],
                url=result["html_url"],
                number=result["number"],
            )
        except GiteaAPIError:
            raise
        except Exception as e:
            raise GiteaAPIError(f"Failed to create review: {e}") from e

    def update_review_status(self, review: Review, draft: bool) -> Review:
        route = f"/repos/{self.owner}/{self.repo_name}/pulls/{review.number}"

        try:
            current_title = review.title
            current_draft = current_title.startswith("WIP: ")

            if draft == current_draft:
                return review

            new_title = current_title

            if draft:
                new_title = self._add_prefix(text=new_title, prefix=self.draft_prefix)
            else:
                new_title = self._remove_prefix(text=new_title, prefix=self.draft_prefix)

            update_data = {"title": new_title}
            result = self._make_request("PATCH", route, json_data=update_data)
            return Review(
                title=result["title"],
                url=result["html_url"],
                number=result["number"],
            )
        except GiteaAPIError:
            raise
        except Exception as e:
            raise GiteaAPIError(f"Failed to update pull request {review.number}: {e}") from e

    def get_review(self, pr_id: int) -> ReviewDetail:
        route = f"/repos/{self.owner}/{self.repo_name}/pulls/{pr_id}"

        try:
            result = self._make_request("GET", route)
            return ReviewDetail(
                title=result["title"],
                url=result["html_url"],
                number=result["number"],
                source_branch=result["head"]["ref"],
                target_branch=result["base"]["ref"],
            )
        except GiteaAPIError:
            raise
        except Exception as e:
            raise GiteaAPIError(f"Failed to get pull request {pr_id}: {e}") from e

    def get_repository_info(self) -> GitRepository:
        return GitRepository(
            platform="gitea",
            base_url=self.base_url,
            hostname=self.hostname,
            owner=self.owner,
            repo=self.repo_name,
        )

    def list_reviews(self, base_branch: str, state: str = "open") -> list[ReviewListItem]:
        route = f"/repos/{self.owner}/{self.repo_name}/pulls"

        try:
            pulls = self._make_request(
                "GET", route, params={"state": state, "base_branch": base_branch}
            )
            if not pulls:
                return []

            reviews = []
            for pr in pulls:
                review = ReviewListItem(
                    title=pr.get("title", ""),
                    url=pr.get("html_url", ""),
                    number=pr.get("number", 0),
                    author=pr.get("user", {}).get("login"),
                    state=pr.get("state"),
                    draft=pr.get("draft", False),
                    created_at=pr.get("created_at"),
                    updated_at=pr.get("updated_at"),
                )
                reviews.append(review)
            return reviews
        except GiteaAPIError:
            raise
        except Exception as e:
            raise GiteaAPIError(f"Failed to list reviews for branch {base_branch}: {e}") from e
