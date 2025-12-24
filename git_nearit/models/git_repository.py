from dataclasses import dataclass


@dataclass
class GitRepository:
    platform: str
    base_url: str
    hostname: str
    owner: str
    repo: str
