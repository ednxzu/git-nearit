from dataclasses import dataclass

@dataclass
class BaseReview:
    title: str
    url: str
    number: int
