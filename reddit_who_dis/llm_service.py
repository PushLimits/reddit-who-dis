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
        self.api_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        )

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

        # Build XML subreddit context
        subreddit_context_xml = ""
        if subreddit_descriptions:
            subreddit_context_xml = "  <SubredditContexts>\n"
            for sub, desc in subreddit_descriptions.items():
                subreddit_context_xml += f'    <Subreddit name="{sub}">{desc}</Subreddit>\n'
            subreddit_context_xml += "  </SubredditContexts>\n"

        # XML instructions
        instructions_xml = (
            "  <Instructions>\n"
            "    The following data is provided in XML format, with subreddit contexts, instructions, and user activities clearly separated into distinct tags. "
            "Each <Activity> element contains attributes for type, subreddit, and creation time, and may include <Content> and <ParentContext> child elements. "
            "Use the information in <SubredditContexts>, <Instructions>, and <Activities> to infer: "
            "- The user's likely personality traits "
            "- Their general interests "
            "- Any recurring themes or patterns in their discussions "
            "Reference the XML structure for context and be concise and insightful in your analysis.\n"
            "  </Instructions>\n"
        )

        # Format activities as XML
        activities_xml = "  <Activities>\n"
        for activity in activities_for_llm:
            activities_xml += activity.to_xml(include_post_bodies, max_post_body_length) + "\n"
        activities_xml += "  </Activities>\n"

        # Combine XML prompt
        prompt = (
            "<RedditAnalysisRequest>\n"
            f"{subreddit_context_xml}"
            f"{instructions_xml}"
            f"{activities_xml}"
            "</RedditAnalysisRequest>"
        )

        chat_history = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {"contents": chat_history}

        logging.info(
            f"Sending {len(activities_for_llm)} combined activities to LLM for analysis (this might take a moment)..."
        )
        logging.info(f"LLM Prompt (XML):\n{prompt}...\n")

        try:
            response = requests.post(self.api_url, headers={"Content-Type": "application/json"}, json=payload)
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
                return f"LLM response structure unexpected: {json.dumps(result, indent=2)}"

        except requests.exceptions.RequestException as e:
            logging.error(f"An error occurred during LLM API call: {e}")
            return f"An error occurred during LLM API call: {e}"
        except Exception as e:
            logging.error(f"An unexpected error occurred during LLM analysis: {e}")
            return f"An unexpected error occurred during LLM analysis: {e}"
