import praw
import os
import time
import requests
import json
import argparse # Import the argparse module
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check required environment variables at startup
REQUIRED_ENV_VARS = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "GOOGLE_API_KEY"]
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    print(f"ERROR: The following environment variables are required but not set: {', '.join(missing_vars)}")
    print("Please set them in your .env file or environment before running this script.")
    exit(1)

def get_reddit_user_comments(reddit_instance, username, limit=None):
    """
    Fetches the comment history for a given Reddit username.

    Args:
        reddit_instance (praw.Reddit): An authenticated PRAW Reddit instance.
        username (str): The Reddit username whose comments you want to fetch.
        limit (int, optional): The maximum number of comments to retrieve.
                               If None, retrieves all available comments.
                               Defaults to None.

    Returns:
        list: A list of dictionaries, where each dictionary represents a comment
              with 'id', 'subreddit', 'link_title', 'body', and 'created_utc' fields.
              Returns an empty list if the user is not found or has no comments.
    """
    try:
        redditor = reddit_instance.redditor(username)
        print(f"Fetching comments for user: {username}...")
        comments_data = []
        for i, comment in enumerate(redditor.comments.new(limit=limit)):
            comments_data.append({
                "id": comment.id,
                "type": "comment",
                "subreddit": comment.subreddit.display_name,
                "link_title": comment.submission.title,
                "body": comment.body,
                "created_utc": comment.created_utc  # Store as float for sorting
            })
            if (i + 1) % 100 == 0:
                print(f"  Fetched {i + 1} comments so far...")
        print(f"Successfully fetched {len(comments_data)} comments for {username}.")
        return comments_data
    except Exception as e:
        print(f"An error occurred during Reddit comment fetching: {e}")
        return []

def get_reddit_user_posts(reddit_instance, username, limit=None):
    """
    Fetches the post history (submissions) for a given Reddit username.

    Args:
        reddit_instance (praw.Reddit): An authenticated PRAW Reddit instance.
        username (str): The Reddit username whose posts you want to fetch.
        limit (int, optional): The maximum number of posts to retrieve.
                               If None, retrieves all available posts.
                               Defaults to None.

    Returns:
        list: A list of dictionaries, where each dictionary represents a post
              with 'id', 'subreddit', 'title', 'selftext', and 'created_utc' fields.
              Returns an empty list if the user is not found or has no posts.
    """
    try:
        redditor = reddit_instance.redditor(username)
        print(f"Fetching posts for user: {username}...")
        posts_data = []
        # Use redditor.submissions.new() to get submissions (posts)
        for i, submission in enumerate(redditor.submissions.new(limit=limit)):
            posts_data.append({
                "id": submission.id,
                "type": "post",
                "subreddit": submission.subreddit.display_name,
                "title": submission.title,
                "selftext": submission.selftext,
                "created_utc": submission.created_utc  # Store as float for sorting
            })
            if (i + 1) % 100 == 0:
                print(f"  Fetched {i + 1} posts so far...")
        print(f"Successfully fetched {len(posts_data)} posts for {username}.")
        return posts_data
    except Exception as e:
        print(f"An error occurred during Reddit post fetching: {e}")
        return []

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
            except Exception as e:
                subreddit_descriptions[sub] = "(Could not fetch description)"
                cache[sub] = {"desc": "(Could not fetch description)", "timestamp": now}
                updated = True
    # Save updated cache
    if updated:
        try:
            with open(cache_file, "w") as f:
                json.dump(cache, f)
        except Exception:
            pass  # Ignore cache write errors
    return subreddit_descriptions

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
        return "ERROR: GOOGLE_API_KEY environment variable not set. Please set it before running."

    if not comments_data and not posts_data:
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

    # When formatting activities for LLM, optionally include human-readable date if desired
    formatted_activities_for_llm = []
    for activity in activities_for_llm:
        if activity["type"] == "comment":
            formatted_activities_for_llm.append(
                f"Type: Comment\nSubreddit: r/{activity['subreddit']}\nContent: {activity['body']}\nCreated: {time.ctime(activity['created_utc'])}"
            )
        elif activity["type"] == "post":
            if include_post_bodies and activity["selftext"]:
                truncated_body = activity["selftext"][:max_post_body_length]
                formatted_activities_for_llm.append(
                    f"Type: Post\nSubreddit: r/{activity['subreddit']}\nTitle: {activity['title']}\nContent: {truncated_body}\nCreated: {time.ctime(activity['created_utc'])}"
                )
            else:
                formatted_activities_for_llm.append(
                    f"Type: Post (Title Only)\nSubreddit: r/{activity['subreddit']}\nTitle: {activity['title']}\nCreated: {time.ctime(activity['created_utc'])}"
                )
        # Add a clear separator between activities
        formatted_activities_for_llm.append("---")

    # Remove the last "---" if it exists
    if formatted_activities_for_llm and formatted_activities_for_llm[-1] == "---":
        formatted_activities_for_llm.pop()

    combined_activities_string = "\n\n".join(formatted_activities_for_llm)

    # Build subreddit context string if provided
    subreddit_context = ""
    if subreddit_descriptions:
        subreddit_context = "Subreddit Contexts:\n"
        for sub, desc in subreddit_descriptions.items():
            subreddit_context += f"- r/{sub}: {desc}\n"
        subreddit_context += "\n"

    prompt = (
        subreddit_context +
        "Based on the following Reddit activities (comments and posts), each explicitly labeled with its type and subreddit, "
        "provide an overview of the user's likely personality, their general interests, "
        "and any discernible history or common themes in their discussions. "
        "Pay close attention to the subreddit context and content type (comment vs. post, and whether post body is included) "
        "when inferring interests and personality traits. "
        "Keep the summary concise and insightful.\n\n"
        "Reddit Activities:\n"
        f"{combined_activities_string}"
    )

    chat_history = [{"role": "user", "parts": [{"text": prompt}]}]
    payload = {"contents": chat_history}
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"

    print(f"\nSending {len(activities_for_llm)} combined activities to LLM for analysis (this might take a moment)...")

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
        return f"An error occurred during LLM API call: {e}"
    except Exception as e:
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

    args = parser.parse_args()

    # --- Configuration from Command-Line Arguments ---
    target_username = args.username
    num_comments_to_fetch = args.comments_limit
    num_posts_to_fetch = args.posts_limit
    analyze_post_bodies = args.include_post_bodies
    max_activities_for_llm_input = args.llm_activities_limit
    max_post_body_length = args.max_post_body_length
    # -------------------------------------------------

    # --- Reddit API Credentials (still from Environment Variables or hardcoded) ---
    CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    USER_AGENT = os.getenv("REDDIT_USER_AGENT", "script:MyRedditActivityAnalyzer:v1.0 (by /u/JoMa4)") # Replace with your Reddit username
    # -----------------------------------------------------------------------------

    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: Please set the REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables.")
        exit()

    try:
        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            user_agent=USER_AGENT
        )
    except Exception as e:
        print(f"Failed to initialize PRAW: {e}. Check your Reddit API credentials.")
        exit()

    user_comments = get_reddit_user_comments(reddit, target_username, limit=num_comments_to_fetch)
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
        print(f"Could not fetch user info: {e}")
        account_creation_date = "N/A"
        comment_karma = "N/A"
        post_karma = "N/A"

    if user_comments or user_posts:
        print("\n--- Latest Reddit Activities ---")
        # Display a few comments
        for i, comment in enumerate(user_comments[:3]):
            print(f"\nComment {i+1} (ID: {comment['id']}) in r/{comment['subreddit']}:")
            print(f"  Body: {comment['body'][:150]}...")
            print(f"  Created: {time.ctime(comment['created_utc'])}")
        # Display a few posts
        for i, post in enumerate(user_posts[:3]):
            print(f"\nPost {i+1} (ID: {post['id']}) in r/{post['subreddit']}:")
            print(f"  Title: {post['title']}")
            if post['selftext'] and analyze_post_bodies:
                print(f"  Body: {post['selftext'][:150]}...")
            elif not analyze_post_bodies:
                print(f"  Body: (Excluded from display and LLM analysis based on setting)")
            print(f"  Created: {time.ctime(post['created_utc'])}")

        if len(user_comments) + len(user_posts) > 6:
            print(f"\n... and more activities (fetched up to {num_comments_to_fetch} comments and {num_posts_to_fetch} posts).")

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
        print(f"No comments or posts found for user '{target_username}' or errors occurred during fetching. Skipping LLM analysis.")
