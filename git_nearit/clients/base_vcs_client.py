from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urlparse

from git import Repo

from git_nearit.models import GitRepository, Review, ReviewListItem, ReviewDetail


class BaseVCSClient(ABC):
    def _parse_remote_url(self, repo: Repo) -> dict[str, str]:
        try:
            remote_url = repo.remote("origin").url
        except Exception as e:
            raise ValueError("Could not get origin remote URL") from e

        # Handle SSH and HTTPS URLs
        # SSH: git@host.com:owner/repo.git or git@host.com:group/subgroup/repo.git
        # SSH with scheme: ssh://git@host.com:port/owner/repo.git
        # HTTPS: https://host.com/owner/repo.git or https://host.com/group/subgroup/repo.git

        if remote_url.startswith("git@"):
            parts = remote_url.replace("git@", "").replace(".git", "").split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid SSH remote URL: {remote_url}")

            hostname = parts[0]
            path = parts[1].split("/")
            if len(path) < 2:
                raise ValueError(f"Invalid SSH remote URL: {remote_url}")

            base_url = f"https://{hostname}"
            repo_name = path[-1]
            owner = "/".join(path[:-1])
            full_path = "/".join(path)
        else:
            parsed = urlparse(remote_url)

            # Extract hostname from netloc (strip username and port)
            # netloc might be: "git@host.com:5022" or "host.com:443" or "host.com"
            netloc = parsed.netloc
            if "@" in netloc:
                netloc = netloc.split("@", 1)[1]
            if ":" in netloc:
                hostname = netloc.split(":", 1)[0]
            else:
                hostname = netloc

            if parsed.scheme == "ssh":
                base_url = f"https://{hostname}"
            else:
                base_url = f"{parsed.scheme}://{hostname}"

            path = parsed.path.strip("/").replace(".git", "").split("/")
            if len(path) < 2:
                raise ValueError(f"Invalid remote URL: {remote_url}")

            repo_name = path[-1]
            owner = "/".join(path[:-1])
            full_path = "/".join(path)

        return {
            "base_url": base_url,
            "hostname": hostname,
            "owner": owner,
            "repo": repo_name,
            "full_path": full_path,
        }

    @abstractmethod
    def check_existing_review(self, source_branch: str, target_branch: str) -> Optional[Review]:
        pass

    @abstractmethod
    def create_review(
        self,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str,
        wip: bool = False,
    ) -> Review:
        pass

    @abstractmethod
    def get_review(self, pr_id: int) -> ReviewDetail:
        pass

    @abstractmethod
    def get_repository_info(self) -> GitRepository:
        pass

    @abstractmethod
    def list_reviews(self, base_branch: str, state: str = "open") -> list[ReviewListItem]:
        pass
