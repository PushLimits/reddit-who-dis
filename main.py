#!/usr/bin/env python3
"""Reddit Who Dis - A tool for analyzing Reddit user activity."""

import logging
import os

from reddit_who_dis import CacheManager, Config, LLMService, RedditService

# Set up dynamic logging level from environment variable
loglevel = os.environ.get("LOG_LEVEL", "INFO").upper()
try:
    loglevel_value = getattr(logging, loglevel)
except AttributeError:
    loglevel_value = logging.INFO
    logging.warning(f"Invalid LOGLEVEL '{loglevel}' specified. Falling back to INFO.")
logging.basicConfig(level=loglevel_value, format='[%(levelname)s] %(message)s')


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

    # Initialize cache manager
    cache_manager = CacheManager(cache_days=config.cache_days)

    # Check cache if enabled
    if config.use_cache and not config.force_refresh:
        cached_result = cache_manager.get_cached_result(
            config.username, config.__dict__
        )
        if cached_result:
            logging.info(f"Using cached result for user '{config.username}'.")
            result = cached_result["result"]
            print_analysis_results(config.username, result['user_info'], result["llm_analysis"])

            import reddit_who_dis.tts_service as tts_service
            tts = tts_service.TTSService(default_voice="am_adam(1)+af_heart(3)")
            tts_text = result.get("llm_analysis_summary") or result["llm_analysis"]
            try:
                tts.synthesize_speech(
                    tts_text,
                    stream=True
                )
                logging.info("LLM analysis audio synthesis completed successfully.")
            except Exception as e:
                logging.error(f"Error during TTS synthesis: {e}")
            return

    # Initialize services
    reddit_service = RedditService(
        client_id=config.reddit_client_id,
        client_secret=config.reddit_client_secret,
        user_agent=config.reddit_user_agent,
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
        max_comment_length=config.max_comment_length,
    )

    user_posts = reddit_service.fetch_posts(redditor, limit=config.posts_limit)

    # Fetch subreddit descriptions for context
    subreddit_descriptions = reddit_service.get_subreddit_descriptions(
        user_comments,
        user_posts,
        cache_manager=cache_manager,
        force_refresh=config.force_refresh,
    )

    if user_comments or user_posts:
        # Analyze comments and posts with LLM
        llm_analysis = llm_service.analyze_reddit_activity(
            user_comments,
            user_posts,
            subreddit_descriptions=subreddit_descriptions,
            include_post_bodies=config.include_post_bodies,
            max_activities=config.llm_activities_limit,
            max_post_body_length=config.max_post_body_length,
        )

        # Prepare result
        analysis_result = {"user_info": user_info, "llm_analysis": llm_analysis}

        # Generate conversational summary for TTS
        conversational_summary = llm_service.summarize_analysis(llm_analysis, max_length=350)
        analysis_result["llm_analysis_summary"] = conversational_summary

        # Save to cache if enabled
        cache_manager.save_result(config.username, config.__dict__, analysis_result)

        print_analysis_results(config.username, user_info, llm_analysis)

        # TTS: Use conversational summary
        import reddit_who_dis.tts_service as tts_service
        tts = tts_service.TTSService(default_voice="am_adam(1)+af_heart(3)")
        try:
            tts.synthesize_speech(
                conversational_summary,
                stream=True
            )
            logging.info("Conversational summary audio synthesis completed successfully.")
        except Exception as e:
            logging.error(f"Error during TTS synthesis: {e}")
            print(f"Error during TTS synthesis: {e}")

    else:
        logging.warning(
            f"No comments or posts found for user '{config.username}' "
            "or errors occurred during fetching. Skipping LLM analysis."
        )


def print_analysis_results(username, user_info, llm_analysis):
    print("\n# Reddit User Analysis: u/" + username + "\n")
    print("## General Information\n")
    print(f"- Account Creation Date: {user_info['creation_date']}")
    print(f"- Comment Karma: {user_info['comment_karma']}")
    print(f"- Post Karma: {user_info['post_karma']}\n")
    print("## Analysis of User's Personality and History\n")
    print("\n" + llm_analysis + "\n")


if __name__ == "__main__":
    main()
