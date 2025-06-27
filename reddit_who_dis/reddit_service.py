"""Reddit API service for interacting with Reddit."""

import logging
import time
from typing import Any, Dict, List, Optional

import praw

from .cache_manager import CacheManager
from .models import Comment, Post


class RedditService:
    """Service for interacting with Reddit API."""

    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        """Initialize the Reddit service with API credentials."""
        self.reddit = praw.Reddit(
            client_id=client_id, client_secret=client_secret, user_agent=user_agent
        )

    def fetch_redditor(self, username: str) -> Optional[praw.models.Redditor]:
        """Fetch a Reddit user by username."""
        try:
            return self.reddit.redditor(username)
        except Exception as e:
            logging.error(f"Failed to fetch redditor object for {username}: {e}")
            return None

    def get_user_info(self, username: str) -> Dict:
        """Get basic information about a Reddit user."""
        try:
            redditor = self.reddit.redditor(username)
            return {
                "creation_date": time.ctime(redditor.created_utc),
                "comment_karma": redditor.comment_karma,
                "post_karma": redditor.link_karma,
            }
        except Exception as e:
            logging.warning(f"Could not fetch user info: {e}")
            return {"creation_date": "N/A", "comment_karma": "N/A", "post_karma": "N/A"}

    def fetch_comments(
        self,
        redditor: praw.models.Redditor,
        limit: Optional[int] = None,
        include_parent_context: bool = True,
        max_parent_context_length: int = 500,
        max_comment_length: int = 500,
    ) -> List[Comment]:
        """Fetch comments for a given Reddit user."""
        comments = []
        try:
            for i, comment in enumerate(redditor.comments.new(limit=limit)):
                body = comment.body[:max_comment_length]

                parent_context = None
                if include_parent_context:
                    try:
                        parent = comment.parent()
                        # If parent is a comment, get its body
                        if hasattr(parent, "body"):
                            parent_context = parent.body[:max_parent_context_length]
                        # If parent is a submission (the post itself), get its title and selftext
                        elif hasattr(parent, "title") and hasattr(parent, "selftext"):
                            # Combine title and selftext for context, truncate if needed
                            combined = f"{parent.title}\n{parent.selftext}"
                            parent_context = combined[:max_parent_context_length]
                    except Exception as e:
                        logging.warning(
                            f"Could not fetch parent context for comment {comment.id}: {e}"
                        )

                comments.append(
                    Comment(
                        id=comment.id,
                        subreddit=comment.subreddit.display_name,
                        created_utc=comment.created_utc,
                        body=body,
                        link_title=comment.submission.title,
                        parent_context=parent_context,
                        type="comment",  # Adding required type parameter
                    )
                )

                if (i + 1) % 100 == 0:
                    logging.info(f"Fetched {i + 1} comments so far...")

            logging.info(f"Successfully fetched {len(comments)} comments.")
        except Exception as e:
            logging.error(f"An error occurred during Reddit comment fetching: {e}")

        return comments

    def fetch_posts(
        self, redditor: praw.models.Redditor, limit: Optional[int] = None
    ) -> List[Post]:
        """Fetch posts for a given Reddit user."""
        posts = []
        try:
            for i, submission in enumerate(redditor.submissions.new(limit=limit)):
                posts.append(
                    Post(
                        id=submission.id,
                        subreddit=submission.subreddit.display_name,
                        created_utc=submission.created_utc,
                        title=submission.title,
                        selftext=submission.selftext,
                        type="post",  # Adding required type parameter
                    )
                )

                if (i + 1) % 100 == 0:
                    logging.info(f"  Fetched {i + 1} posts so far...")

            logging.info(f"Successfully fetched {len(posts)} posts.")
        except Exception as e:
            logging.error(f"An error occurred during Reddit post fetching: {e}")

        return posts

    def get_subreddit_descriptions(
        self,
        comments: List[Comment],
        posts: List[Post],
        cache_manager: Optional["CacheManager"] = None,
        force_refresh: bool = False,
    ) -> Dict[str, str]:
        """Fetch descriptions for subreddits, using cache if available.

        Args:
            comments: List of Comment objects
            posts: List of Post objects
            cache_manager: Optional CacheManager instance for caching
            force_refresh: Whether to force refresh cached descriptions

        Returns:
            Dictionary mapping subreddit names to their descriptions
        """
        unique_subreddits = {comment.subreddit for comment in comments}.union(
            {post.subreddit for post in posts}
        )

        # If no cache manager, return descriptions without caching
        if not cache_manager:
            return self._fetch_subreddit_descriptions(unique_subreddits)

        return cache_manager.get_subreddit_descriptions(
            self.reddit, unique_subreddits, force_refresh=force_refresh
        )

    def _fetch_subreddit_descriptions(self, subreddits: set[str]) -> Dict[str, str]:
        """Fetch descriptions for subreddits without caching.

        Args:
            subreddits: Set of subreddit names to fetch descriptions for

        Returns:
            Dictionary mapping subreddit names to their descriptions
        """
        descriptions = {}
        for sub in subreddits:
            try:
                subreddit = self.reddit.subreddit(sub)
                desc = (
                    subreddit.public_description
                    or subreddit.description
                    or "(No description available)"
                )
                desc_clean = desc.strip().replace("\n", " ")
                descriptions[sub] = desc_clean
                logging.info(f"Fetched description for r/{sub}: {desc_clean[:100]}...")
            except Exception as e:
                descriptions[sub] = "(Could not fetch description)"
                logging.warning(f"Could not fetch description for r/{sub}: {e}")
        return descriptions
