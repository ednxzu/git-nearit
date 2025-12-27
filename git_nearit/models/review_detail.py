from dataclasses import dataclass

from git_nearit.models.review import Review


@dataclass
class ReviewDetail(Review):
    source_branch: str
    target_branch: str
