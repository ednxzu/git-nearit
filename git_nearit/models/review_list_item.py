from dataclasses import dataclass

from git_nearit.models.review import Review


@dataclass
class ReviewListItem(Review):
    author: str
    state: str
    draft: bool
    created_at: str
    updated_at: str
