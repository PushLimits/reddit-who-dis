"""Data models for Reddit Who Dis."""

from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class RedditActivity:
    """Base class for Reddit activities (comments and posts)."""
    id: str
    subreddit: str
    created_utc: float
    type: str

    def format_for_llm(self, include_post_bodies: bool = False, max_post_body_length: int = 150) -> str:
        """Format the activity for LLM input."""
        raise NotImplementedError

@dataclass
class Comment(RedditActivity):
    """Represents a Reddit comment."""
    body: str
    link_title: str
    parent_context: Optional[str] = None

    def __post_init__(self):
        self.type = "comment"

    def format_for_llm(self, include_post_bodies: bool = False, max_post_body_length: int = 150) -> str:
        parent_str = f"\nParent Context: {self.parent_context}" if self.parent_context else ""
        return f"Type: Comment\nSubreddit: r/{self.subreddit}\nContent: {self.body}{parent_str}\nCreated: {time.ctime(self.created_utc)}"

@dataclass
class Post(RedditActivity):
    """Represents a Reddit post."""
    title: str
    selftext: str

    def __post_init__(self):
        self.type = "post"

    def format_for_llm(self, include_post_bodies: bool = False, max_post_body_length: int = 150) -> str:
        if include_post_bodies and self.selftext:
            truncated_body = self.selftext[:max_post_body_length]
            return f"Type: Post\nSubreddit: r/{self.subreddit}\nTitle: {self.title}\nContent: {truncated_body}\nCreated: {time.ctime(self.created_utc)}"
        return f"Type: Post\nSubreddit: r/{self.subreddit}\nTitle: {self.title}\nCreated: {time.ctime(self.created_utc)}"
