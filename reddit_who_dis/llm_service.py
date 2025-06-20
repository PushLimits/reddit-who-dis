"""LLM service for analyzing Reddit activity."""

import json
import logging
from typing import Dict, List, Optional

import requests

from .models import Comment, Post


class LLMService:
    """Service for analyzing Reddit activity using a language model."""

    def __init__(self, api_key: str):
        """Initialize the LLM service with API key."""
        self.api_key = api_key
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    def analyze_reddit_activity(
        self,
        comments: List[Comment],
        posts: List[Post],
        subreddit_descriptions: Optional[Dict[str, str]] = None,
        include_post_bodies: bool = False,
        max_activities: int = 50,
        max_post_body_length: int = 150,
    ) -> str:
        """Analyze Reddit activity using the LLM."""
        if not comments and not posts:
            logging.warning("No comments or posts to analyze.")
            return "No comments or posts to analyze."

        # Combine and sort activities
        all_activities = []
        seen_ids = set()

        for comment in comments:
            if comment.id not in seen_ids:
                all_activities.append(comment)
                seen_ids.add(comment.id)

        for post in posts:
            if post.id not in seen_ids:
                all_activities.append(post)
                seen_ids.add(post.id)

        # Sort by creation time (most recent first) and truncate
        all_activities.sort(key=lambda x: x.created_utc, reverse=True)
        activities_for_llm = all_activities[:max_activities]

        # Format activities
        formatted_activities = []
        for activity in activities_for_llm:
            formatted_activities.append(
                activity.format_for_llm(include_post_bodies, max_post_body_length)
            )
        combined_activities_string = "\n---\n".join(formatted_activities)

        # Build subreddit context
        subreddit_context = ""
        if subreddit_descriptions:
            subreddit_context = "Subreddit Contexts:\n"
            for sub, desc in subreddit_descriptions.items():
                subreddit_context += f"- r/{sub}: {desc}\n"
            subreddit_context += "\n"

        # Create prompt
        prompt = (
            subreddit_context + "Analyze the following Reddit activities for the user. "
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

        logging.info(
            f"\nSending {len(activities_for_llm)} combined activities to LLM for analysis "
            "(this might take a moment)..."
        )

        try:
            response = requests.post(
                self.api_url, headers={"Content-Type": "application/json"}, json=payload
            )
            response.raise_for_status()
            result = response.json()

            if (
                result.get("candidates")
                and result["candidates"][0].get("content")
                and result["candidates"][0]["content"].get("parts")
                and result["candidates"][0]["content"]["parts"][0].get("text")
            ):
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return (
                    f"LLM response structure unexpected: {json.dumps(result, indent=2)}"
                )

        except requests.exceptions.RequestException as e:
            logging.error(f"An error occurred during LLM API call: {e}")
            return f"An error occurred during LLM API call: {e}"
        except Exception as e:
            logging.error(f"An unexpected error occurred during LLM analysis: {e}")
            return f"An unexpected error occurred during LLM analysis: {e}"
