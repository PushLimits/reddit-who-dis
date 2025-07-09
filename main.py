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

logging.basicConfig(level=loglevel_value, format="[%(levelname)s] %(message)s")


def main():
    """Main entry point for the Reddit Who Dis application."""

    logging.info("Starting Reddit Who Dis...")
    logging.info(f"Using log level: {loglevel}")

    # Set up argument parser and get configuration
    parser = Config.setup_arg_parser()
    args = parser.parse_args()

    try:
        config = Config.from_env_and_args(args)
    except ValueError as e:
        logging.error(str(e))
        exit(1)

    # Log all possible config values passed in from the command line (excluding env vars)
    logging.debug("Config values from params or default:")
    for key in vars(args):
        logging.debug(f"  {key}: {getattr(args, key)}")

    # Initialize cache manager
    cache_manager = CacheManager(cache_days=config.cache_days)

    # Check cache if enabled
    if config.use_cache and not config.force_refresh:
        cached_result = cache_manager.get_cached_result(config.username, config.__dict__)
        if cached_result:
            result = cached_result["result"]
            print_analysis_results(config, result["user_info"], result["full_analysis"])

            if config.use_tts:
                tts_summary = result.get("tts_summary") or result["full_analysis"]
                print_tts_summary(tts_summary)
                speak_analysis(tts_summary)

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
        full_analysis = llm_service.analyze_reddit_activity(
            user_comments,
            user_posts,
            subreddit_descriptions=subreddit_descriptions,
            include_post_bodies=config.include_post_bodies,
            max_activities=config.llm_activities_limit,
            max_post_body_length=config.max_post_body_length,
        )

        # Prepare payload for caching
        analysis_payload = {
            "user_info": user_info,
            "full_analysis": full_analysis,
        }

        # Generate conversational summary for TTS
        tts_summary = llm_service.summarize_analysis(full_analysis, max_length=350)
        analysis_payload["tts_summary"] = tts_summary

        # Save to cache if enabled
        if config.use_cache:
            logging.info("Saving analysis result to cache...")
        cache_manager.save_result(config.username, config.__dict__, analysis_payload)

        logging.info("Analysis completed successfully.")

        # Print results
        print_analysis_results(config, user_info, full_analysis)
        print_tts_summary(tts_summary)

        if config.use_tts:
            speak_analysis(tts_summary)
    else:
        logging.warning(
            f"No comments or posts found for user '{config.username}' "
            "or errors occurred during fetching. Skipping LLM analysis."
        )


def print_analysis_results(config, user_info, full_analysis):
    """Prints or saves the analysis results."""
    username = config.username
    output_content = (
        f"### Reddit User: {username}\n"
        f"> **Created:** {user_info['creation_date']} | "
        f"**Comment Karma:** {user_info['comment_karma']} | "
        f"**Post Karma:** {user_info['post_karma']}\n"
        f"\n{full_analysis}\n"
    )

    if config.output_to_file:
        output_dir = "output"
        output_file_path = os.path.join(output_dir, f"{username}.md")
        try:
            os.makedirs(output_dir, exist_ok=True)
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(output_content)
            logging.info(f"Analysis results saved to {output_file_path}")
        except IOError as e:
            logging.error(f"Error writing to file {output_file_path}: {e}")
    else:
        print(output_content)


def print_tts_summary(summary_text):
    print("\n## Summary for Text-to-Speech (TTS)\n")
    print(summary_text + "\n")


def speak_analysis(summary_text):
    """Helper to synthesize speech from analysis text using TTSService."""
    import reddit_who_dis.tts_service as tts_service

    default_voice = "am_adam(1)+af_heart(3)"
    logging.info(f"Synthesising speech using voice {default_voice}...")

    tts = tts_service.TTSService(default_voice=default_voice)

    try:
        tts.synthesize_speech(summary_text, stream=True)
        logging.info("Audio synthesis completed successfully.")
    except Exception as e:
        logging.error(f"Error during TTS synthesis: {e}")


if __name__ == "__main__":
    main()
