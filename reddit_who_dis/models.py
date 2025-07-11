"""Data models for Reddit Who Dis."""

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


class Comment(BaseModel):
    """Pydantic model for a Reddit comment."""

    id: str
    type: Literal["comment"]
    subreddit: str
    created_utc: float
    body: str
    link_title: str
    ups: int
    downs: int
    parent_author: Optional[str] = None
    parent_context: Optional[str] = None


class Post(BaseModel):
    """Pydantic model for a Reddit post."""

    id: str
    type: Literal["post"]
    subreddit: str
    created_utc: float
    title: str
    selftext: str
    ups: int
    downs: int


class SubredditContext(BaseModel):
    """Pydantic model for subreddit context."""

    name: str
    description: str


class RedditAnalysisRequest(BaseModel):
    """Pydantic model for the entire Reddit analysis request payload."""

    subreddit_contexts: List[SubredditContext] = Field(
        ..., description="Contextual descriptions of relevant subreddits."
    )
    activities: List[Union[Comment, Post]] = Field(..., description="A list of the user's recent posts and comments.")


class RedditSummaryRequest(BaseModel):
    """Pydantic model for the summary request."""

    full_analysis: str = Field(..., description="The full, detailed analysis to be summarized.")
