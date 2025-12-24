from dataclasses import dataclass

from git_nearit.models.base_review import BaseReview


@dataclass
class ReviewSummary(BaseReview):
    author: str
    state: str
    draft: bool
    created_at: str
    updated_at: str
