"""Configuration handling for Reddit Who Dis."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv
import logging
import argparse

@dataclass
class Config:
    """Configuration settings for the application."""
    username: str
    comments_limit: int
    posts_limit: int
    include_post_bodies: bool
    llm_activities_limit: int
    max_post_body_length: int
    include_parent_context: bool
    max_parent_context_length: int
    max_comment_length: int
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    google_api_key: str
    cache_days: int
    force_refresh: bool
    use_cache: bool

    @classmethod
    def from_env_and_args(cls, args: argparse.Namespace) -> 'Config':
        """Create a Config instance from environment variables and command line arguments."""
        load_dotenv()
        
        # Check required environment variables
        required_env_vars = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "GOOGLE_API_KEY"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logging.error(error_msg)
            raise ValueError(error_msg)

        return cls(
            username=args.username,
            comments_limit=args.comments_limit,
            posts_limit=args.posts_limit,
            include_post_bodies=args.include_post_bodies,
            llm_activities_limit=args.llm_activities_limit,
            max_post_body_length=args.max_post_body_length,
            include_parent_context=args.include_parent_context,
            max_parent_context_length=args.max_parent_context_length,
            max_comment_length=args.max_comment_length,
            reddit_client_id=os.getenv("REDDIT_CLIENT_ID"),
            reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "script:reddit-who-dis:v1.0"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            cache_days=args.cache_days,
            force_refresh=args.force_refresh,
            use_cache=args.use_cache
        )

    @staticmethod
    def setup_arg_parser() -> argparse.ArgumentParser:
        """Create and return the argument parser for command line arguments."""
        parser = argparse.ArgumentParser(description="Analyze a Reddit user's comment and post history using an LLM.")
        parser.add_argument("username", type=str, help="The Reddit username to analyze.")
        parser.add_argument("--comments-limit", type=int, default=50,
                          help="Maximum number of comments to fetch from Reddit API (default: 50).")
        parser.add_argument("--posts-limit", type=int, default=50,
                          help="Maximum number of posts to fetch from Reddit API (default: 50).")
        parser.add_argument("--include-post-bodies", action="store_true",
                          help="Include full post bodies in LLM analysis (default: False, only titles).")
        parser.add_argument("--llm-activities-limit", type=int, default=100,
                          help="Total combined activities (comments + posts) to send to LLM (default: 100).")
        parser.add_argument("--max-post-body-length", type=int, default=150,
                          help="Maximum length of post bodies to include in LLM analysis (default: 150).")
        parser.add_argument("--include-parent-context", action="store_true",
                          help="Include parent comment context in user comments (default: False).")
        parser.add_argument("--max-parent-context-length", type=int, default=200,
                          help="Maximum length of parent comment context to include (default: 200).")
        parser.add_argument("--max-comment-length", type=int, default=500,
                          help="Maximum length of user comment bodies to include (default: 500).")
        parser.add_argument("--cache-days", type=int, default=7,
                          help="Number of days to cache analysis results (default: 7).")
        parser.add_argument("--force-refresh", action="store_true",
                          help="Force refresh of cached results (default: False).")
        parser.add_argument("--no-cache", action="store_false", dest="use_cache", default=True,
                          help="Disable caching of results (default: False).")
        return parser
