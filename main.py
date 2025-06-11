#!/usr/bin/env python3
"""Reddit Who Dis - A tool for analyzing Reddit user activity."""

import logging
from reddit_who_dis import Config
from reddit_who_dis import LLMService
from reddit_who_dis import RedditService

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def main():
    """Main entry point for the Reddit Who Dis application."""
    # Set up argument parser and get configuration
    parser = Config.setup_arg_parser()
    args = parser.parse_args()
    
    try:
        config = Config.from_env_and_args(args)
    except ValueError as e:
        logging.error(str(e))
        exit(1)

    # Initialize services
    reddit_service = RedditService(
        client_id=config.reddit_client_id,
        client_secret=config.reddit_client_secret,
        user_agent=config.reddit_user_agent
    )
    
    llm_service = LLMService(api_key=config.google_api_key)

    # Fetch user data
    redditor = reddit_service.fetch_redditor(config.username)
    if not redditor:
        exit(1)

    # Fetch user information
    user_info = reddit_service.get_user_info(config.username)

    # Fetch comments and posts
    user_comments = reddit_service.fetch_comments(
        redditor,
        limit=config.comments_limit,
        include_parent_context=config.include_parent_context,
        max_parent_context_length=config.max_parent_context_length,
        max_comment_length=config.max_comment_length
    )

    user_posts = reddit_service.fetch_posts(
        redditor,
        limit=config.posts_limit
    )

    # Fetch subreddit descriptions for context
    subreddit_descriptions = reddit_service.get_subreddit_descriptions(
        user_comments,
        user_posts
    )

    if user_comments or user_posts:
        # Analyze comments and posts with LLM
        llm_analysis = llm_service.analyze_reddit_activity(
            user_comments,
            user_posts,
            subreddit_descriptions=subreddit_descriptions,
            include_post_bodies=config.include_post_bodies,
            max_activities=config.llm_activities_limit,
            max_post_body_length=config.max_post_body_length
        )

        # Print results
        print("\n--- Analysis of User's Personality and History ---")
        print("\n# Reddit User Analysis: u/" + config.username + "\n")
        print("## General Information\n")
        print(f"- Account Creation Date: {user_info['creation_date']}")
        print(f"- Comment Karma: {user_info['comment_karma']}")
        print(f"- Post Karma: {user_info['post_karma']}\n")
        print("## Analysis of User's Personality and History\n")
        print(llm_analysis)
    else:
        logging.warning(
            f"No comments or posts found for user '{config.username}' "
            "or errors occurred during fetching. Skipping LLM analysis."
        )


if __name__ == "__main__":
    main()
