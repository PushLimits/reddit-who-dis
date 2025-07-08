"""Data models for Reddit Who Dis."""

import html
from dataclasses import dataclass
from typing import Optional


@dataclass
class RedditActivity:
    """Base class for Reddit activities (comments and posts)."""

    id: str
    subreddit: str
    created_utc: float
    type: str

    def to_xml(self, include_post_bodies: bool = False, max_post_body_length: int = 150) -> str:
        """
        Serialize the activity as an XML string for LLM prompts.
        All user/dynamic data is sanitized to prevent invalid XML.
        Subclasses must override this method to provide their own XML structure.
        """
        # Default implementation, should be overridden by subclasses
        raise NotImplementedError("Subclasses must implement to_xml.")


@dataclass
class Comment(RedditActivity):
    """Represents a Reddit comment."""

    body: str
    link_title: str
    parent_context: Optional[str] = None

    def __post_init__(self):
        self.type = "comment"

    def to_xml(self, include_post_bodies: bool = False, max_post_body_length: int = 150) -> str:
        """
        Serialize the comment as an XML string for LLM prompts.
        All user/dynamic data is sanitized to prevent invalid XML.
        Includes <Body> and optional <ParentContext> fields.
        """
        parent_context_xml = (
            f"<ParentContext>{html.escape(self.parent_context)}</ParentContext>\n" if self.parent_context else ""
        )

        return (
            '<Activity type="comment"'
            f' subreddit="{html.escape(self.subreddit)}"'
            f' created_utc="{html.escape(str(self.created_utc))}">\n'
            "  <Content>\n"
            f"   <Body>{html.escape(self.body)}</Body>\n"
            f"   {parent_context_xml}"
            "  </Content>\n"
            "</Activity>"
        )


@dataclass
class Post(RedditActivity):
    """Represents a Reddit post."""

    title: str
    selftext: str

    def __post_init__(self):
        self.type = "post"

    def to_xml(self, include_post_bodies: bool = False, max_post_body_length: int = 150) -> str:
        """
        Serialize the post as an XML string for LLM prompts.
        All user/dynamic data is sanitized to prevent invalid XML.
        Includes <Title> and optional <Body> fields.
        """
        body_xml = ""
        if include_post_bodies and self.selftext:
            truncated_body = self.selftext[:max_post_body_length]
            body_xml = f"<Body>{html.escape(truncated_body)}</Body>\n"
        return (
            f'<Activity type="post"'
            f' subreddit="{html.escape(self.subreddit)}" created_utc="{html.escape(str(self.created_utc))}">'
            "  <Content>\n"
            f"    <Title>{html.escape(self.title)}</Title>\n"
            f"    {body_xml}"
            "  </Content>\n"
            "</Activity>"
        )


def subreddit_contexts_to_xml(subreddit_descriptions: Optional[dict]) -> str:
    """
    Serialize subreddit descriptions to XML for LLM prompts.
    All user/dynamic data is sanitized to prevent invalid XML.
    """
    if not subreddit_descriptions:
        return ""
    xml = "  <SubredditContexts>"
    for sub, desc in subreddit_descriptions.items():
        xml += f'<Subreddit name="{html.escape(str(sub))}">{html.escape(str(desc))}</Subreddit>'
    xml += "</SubredditContexts>"
    return xml
