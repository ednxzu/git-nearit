from dataclasses import dataclass


@dataclass
class Review:
    title: str
    url: str
    number: int
