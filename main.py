import praw
import os
import time
import requests
import json
import argparse # Import the argparse module
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Check required environment variables at startup
REQUIRED_ENV_VARS = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "GOOGLE_API_KEY"]
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    logging.error(f"The following environment variables are required but not set: {', '.join(missing_vars)}")
    logging.error("Please set them in your .env file or environment before running this script.")
    exit(1)

def fetch_redditor(reddit_instance, username):
    try:
        return reddit_instance.redditor(username)
    except Exception as e:
        logging.error(f"Failed to fetch redditor object for {username}: {e}")
        return None

def fetch_comments(redditor, limit=None, include_parent_context=False, max_parent_context_length=200, max_comment_length=500):
    comments_data = []
    try:
        for i, comment in enumerate(redditor.comments.new(limit=limit)):
            # Truncate user comment body
            body = comment.body[:max_comment_length]
            comment_dict = {
                "id": comment.id,
                "type": "comment",
                "subreddit": comment.subreddit.display_name,
                "link_title": comment.submission.title,
                "body": body,
                "created_utc": comment.created_utc
            }
            if include_parent_context:
                parent_context = None
                try:
                    parent = comment.parent()
                    # Only include parent if it's a comment (not a submission)
                    if hasattr(parent, 'body'):
                        parent_context = parent.body[:max_parent_context_length]
                except Exception as e:
                    logging.warning(f"Could not fetch parent context for comment {comment.id}: {e}")
                if parent_context:
                    comment_dict["parent_context"] = parent_context
            comments_data.append(comment_dict)
            if (i + 1) % 100 == 0:
                logging.info(f"  Fetched {i + 1} comments so far...")
        logging.info(f"Successfully fetched {len(comments_data)} comments.")
    except Exception as e:
        logging.error(f"An error occurred during Reddit comment fetching: {e}")
    return comments_data

def fetch_posts(redditor, limit=None):
    posts_data = []
    try:
        for i, submission in enumerate(redditor.submissions.new(limit=limit)):
            posts_data.append({
                "id": submission.id,
                "type": "post",
                "subreddit": submission.subreddit.display_name,
                "title": submission.title,
                "selftext": submission.selftext,
                "created_utc": submission.created_utc
            })
            if (i + 1) % 100 == 0:
                logging.info(f"  Fetched {i + 1} posts so far...")
        logging.info(f"Successfully fetched {len(posts_data)} posts.")
    except Exception as e:
        logging.error(f"An error occurred during Reddit post fetching: {e}")
    return posts_data

def get_reddit_user_comments(reddit_instance, username, limit=None, include_parent_context=False, max_parent_context_length=200, max_comment_length=500):
    redditor = fetch_redditor(reddit_instance, username)
    if not redditor:
        return []
    return fetch_comments(redditor, limit, include_parent_context, max_parent_context_length, max_comment_length)

def get_reddit_user_posts(reddit_instance, username, limit=None):
    redditor = fetch_redditor(reddit_instance, username)
    if not redditor:
        return []
    return fetch_posts(redditor, limit)

def get_subreddit_descriptions(reddit_instance, comments_data, posts_data, cache_file=".cache/subreddit_descriptions_cache.json"):
    """
    Fetches the public descriptions for all unique subreddits found in the user's comments and posts.
    Uses a local cache file to avoid repeated API calls. Cache entries older than 30 days are refreshed.

    Args:
        reddit_instance (praw.Reddit): An authenticated PRAW Reddit instance.
        comments_data (list): List of comment dictionaries.
        posts_data (list): List of post dictionaries.
        cache_file (str): Path to the cache file (default: "subreddit_descriptions_cache.json").

    Returns:
        dict: Mapping of subreddit name to its public description.
    """
    import json
    import os
    import time
    from datetime import datetime, timedelta

    unique_subreddits = set()
    for activity in comments_data + posts_data:
        unique_subreddits.add(activity['subreddit'])

    # Ensure cache directory exists
    cache_dir = os.path.dirname(cache_file)
    if cache_dir and not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)

    # Load cache if it exists
    cache = {}
    try:
        with open(cache_file, "r") as f:
            cache = json.load(f)
    except Exception:
        logging.info("No cache found or failed to load cache file for subreddit descriptions.")
        pass  # No cache or failed to load

    now = time.time()
    THIRTY_DAYS = 30 * 24 * 60 * 60
    subreddit_descriptions = {}
    updated = False
    for sub in unique_subreddits:
        cache_entry = cache.get(sub)
        needs_refresh = True
        if cache_entry and isinstance(cache_entry, dict):
            desc = cache_entry.get("desc")
            ts = cache_entry.get("timestamp", 0)
            if desc is not None and (now - ts) < THIRTY_DAYS:
                subreddit_descriptions[sub] = desc
                needs_refresh = False
        if needs_refresh:
            try:
                subreddit = reddit_instance.subreddit(sub)
                desc = subreddit.public_description or subreddit.description or "(No description available)"
                desc_clean = desc.strip().replace("\n", " ")
                subreddit_descriptions[sub] = desc_clean
                cache[sub] = {"desc": desc_clean, "timestamp": now}
                updated = True
                logging.info(f"Fetched description for r/{sub}.")
            except Exception as e:
                subreddit_descriptions[sub] = "(Could not fetch description)"
                cache[sub] = {"desc": "(Could not fetch description)", "timestamp": now}
                updated = True
                logging.warning(f"Could not fetch description for r/{sub}: {e}")
    # Save updated cache
    if updated:
        try:
            with open(cache_file, "w") as f:
                json.dump(cache, f)
            logging.info("Updated subreddit description cache.")
        except Exception:
            logging.warning("Failed to write subreddit description cache.")
    return subreddit_descriptions

def format_activity_for_llm(activity, include_post_bodies, max_post_body_length):
    if activity["type"] == "comment":
        parent_str = ""
        if activity.get("parent_context"):
            parent_str = f"\nParent Context: {activity['parent_context']}"
        return f"Type: Comment\nSubreddit: r/{activity['subreddit']}\nContent: {activity['body']}{parent_str}\nCreated: {time.ctime(activity['created_utc'])}"
    elif activity["type"] == "post":
        if include_post_bodies and activity["selftext"]:
            truncated_body = activity["selftext"][:max_post_body_length]
            return f"Type: Post\nSubreddit: r/{activity['subreddit']}\nTitle: {activity['title']}\nContent: {truncated_body}\nCreated: {time.ctime(activity['created_utc'])}"
        else:
            return f"Type: Post\nSubreddit: r/{activity['subreddit']}\nTitle: {activity['title']}\nCreated: {time.ctime(activity['created_utc'])}"
    return ""

def format_activities_for_llm(activities, include_post_bodies, max_post_body_length):
    formatted = [format_activity_for_llm(a, include_post_bodies, max_post_body_length) for a in activities]
    # Add separator
    return "\n---\n".join(formatted)

def analyze_reddit_activity_with_llm(
    comments_data,
    posts_data,
    subreddit_descriptions=None,
    include_post_bodies=False,
    max_activities_for_llm=50,
    max_post_body_length=150
):
    """
    Analyzes a user's Reddit comments and posts using a large language model.

    Args:
        comments_data (list): A list of comment dictionaries.
        posts_data (list): A list of post dictionaries.
        subreddit_descriptions (dict, optional): Mapping of subreddit name to description.
        include_post_bodies (bool): If True, includes the full selftext of posts in the analysis.
        max_activities_for_llm (int): Maximum number of combined activities (comments + posts)
                                      to send to the LLM to manage token limits.
        max_post_body_length (int): Maximum length of post bodies to include in the analysis.

    Returns:
        str: An overview of the user's likely personality and general history,
             or an error message if the analysis fails.
    """
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        logging.error("GOOGLE_API_KEY environment variable not set. Please set it before running.")
        return "ERROR: GOOGLE_API_KEY environment variable not set. Please set it before running."

    if not comments_data and not posts_data:
        logging.warning("No comments or posts to analyze.")
        return "No comments or posts to analyze."

    # Combine and deduplicate activities, prioritizing recent ones if limiting
    all_activities = []
    seen_ids = set()

    # Add comments
    for comment in comments_data:
        if comment['id'] not in seen_ids:
            all_activities.append(comment)
            seen_ids.add(comment['id'])

    # Add posts
    for post in posts_data:
        if post['id'] not in seen_ids: # Ensure unique posts
            all_activities.append(post)
            seen_ids.add(post['id'])

    # Sort by creation time (most recent first) and then truncate for LLM
    all_activities.sort(key=lambda x: x['created_utc'], reverse=True)
    activities_for_llm = all_activities[:max_activities_for_llm]

    combined_activities_string = format_activities_for_llm(activities_for_llm, include_post_bodies, max_post_body_length)

    # Build subreddit context string if provided
    subreddit_context = ""
    if subreddit_descriptions:
        subreddit_context = "Subreddit Contexts:\n"
        for sub, desc in subreddit_descriptions.items():
            subreddit_context += f"- r/{sub}: {desc}\n"
        subreddit_context += "\n"

    prompt = (
        subreddit_context +
        "Analyze the following Reddit activities for the user. " 
        "Each activity is labeled with its type and subreddit. "
        "For comments, a 'Parent Context' field (representing the parent comment) may be included to clarify the user's intent or conversational style. "
        "User comment bodies and parent contexts may be truncated to a maximum length for efficiency. "
        "Use the subreddit context, the activity type, the content, and any parent context to infer:\n"
        "- The user's likely personality traits\n"
        "- Their general interests\n"
        "- Any recurring themes or patterns in their discussions\n"
        "Be concise, insightful, and reference the context provided.\n\n"
        "Reddit Activities:\n"
        f"{combined_activities_string}"
    )

    chat_history = [{"role": "user", "parts": [{"text": prompt}]}]
    payload = {"contents": chat_history}
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"

    logging.info(f"\nSending {len(activities_for_llm)} combined activities to LLM for analysis (this might take a moment)...")

    try:
        response = requests.post(api_url, headers={'Content-Type': 'application/json'}, json=payload)
        response.raise_for_status()
        result = response.json()

        if result.get("candidates") and result["candidates"][0].get("content") and \
           result["candidates"][0]["content"].get("parts") and \
           result["candidates"][0]["content"]["parts"][0].get("text"):
            analysis_text = result["candidates"][0]["content"]["parts"][0]["text"]
            return analysis_text
        else:
            return f"LLM response structure unexpected: {json.dumps(result, indent=2)}"

    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred during LLM API call: {e}")
        return f"An error occurred during LLM API call: {e}"
    except Exception as e:
        logging.error(f"An unexpected error occurred during LLM analysis: {e}")
        return f"An unexpected error occurred during LLM analysis: {e}"

if __name__ == "__main__":
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

    args = parser.parse_args()

    # --- Configuration from Command-Line Arguments ---
    target_username = args.username
    num_comments_to_fetch = args.comments_limit
    num_posts_to_fetch = args.posts_limit
    analyze_post_bodies = args.include_post_bodies
    max_activities_for_llm_input = args.llm_activities_limit
    max_post_body_length = args.max_post_body_length
    include_parent_context = args.include_parent_context
    max_parent_context_length = args.max_parent_context_length
    max_comment_length = args.max_comment_length
    # -------------------------------------------------

    # --- Reddit API Credentials ---
    CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    USER_AGENT = os.getenv("REDDIT_USER_AGENT", "script:reddit-who-dis:v1.0")
    # -----------------------------------------------------------------------------

    if not CLIENT_ID or not CLIENT_SECRET:
        logging.error("Please set the REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables.")
        exit()
    try:
        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            user_agent=USER_AGENT
        )
    except Exception as e:
        logging.error(f"Failed to initialize PRAW: {e}. Check your Reddit API credentials.")
        exit()

    user_comments = get_reddit_user_comments(
        reddit,
        target_username,
        limit=num_comments_to_fetch,
        include_parent_context=include_parent_context,
        max_parent_context_length=max_parent_context_length,
        max_comment_length=max_comment_length
    )
    user_posts = get_reddit_user_posts(reddit, target_username, limit=num_posts_to_fetch)

    # Fetch subreddit descriptions for context
    subreddit_descriptions = get_subreddit_descriptions(reddit, user_comments, user_posts)

    # When displaying account creation date, convert to string
    try:
        redditor = reddit.redditor(target_username)
        account_creation_date = time.ctime(redditor.created_utc)
        comment_karma = redditor.comment_karma
        post_karma = redditor.link_karma
    except Exception as e:
        logging.warning(f"Could not fetch user info: {e}")
        account_creation_date = "N/A"
        comment_karma = "N/A"
        post_karma = "N/A"

    if user_comments or user_posts:
        # Analyze comments and posts with LLM, passing subreddit_descriptions
        llm_analysis = analyze_reddit_activity_with_llm(
            user_comments,
            user_posts,
            subreddit_descriptions=subreddit_descriptions,
            include_post_bodies=analyze_post_bodies,
            max_activities_for_llm=max_activities_for_llm_input,
            max_post_body_length=max_post_body_length
        )

        print("\n--- Analysis of User's Personality and History ---")
        print("\n# Reddit User Analysis: u/" + target_username + "\n")
        print("## General Information\n")
        print(f"- Account Creation Date: {account_creation_date}")
        print(f"- Comment Karma: {comment_karma}")
        print(f"- Post Karma: {post_karma}\n")
        print("## Analysis of User's Personality and History\n")
        print(llm_analysis)

    else:
        logging.warning(f"No comments or posts found for user '{target_username}' or errors occurred during fetching. Skipping LLM analysis.")
