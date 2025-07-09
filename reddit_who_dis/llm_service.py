"""LLM service for analyzing Reddit activity."""

import html
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
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={api_key}"
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
            "<Instructions>\n"
            "  The following data is provided in XML format, with subreddit contexts, instructions, and user "
            "activities clearly separated into distinct tags.\n"
            "    1. Each ACTIVITY element contains attributes for type (post/comment), subreddit, upvotes, downvotes, "
            "and created_date.\n"
            "    2. Each ACTIVITY includes CONTENT elements with both BODY and PARENTCONTEXT child elements.\n"
            "    3. The PARENTCONTEXT element contains an author attribute to understand trends in user interaction "
            "patterns.\n"
            "    4. The SUBREDDITCONTEXTS element contains descriptions of relevant subreddits in SUBREDDIT "
            "child elements.\n\n"
            
            "  Use all of the information in SUBREDDITCONTEXTS and ACTIVITIES to infer the following:\n"
            "    1. The user's likely personality traits.\n"
            "    2. Their general interests.\n"
            "    3. Any recurring themes or patterns in their discussions.\n"
            "    4. How to best engage with this user in future interactions.\n"
            "    5. Any notable events or changes in their activity over time.\n"
            "    6. Any potential biases or perspectives that may influence their opinions.\n"
            "    7. Any significant relationships or interactions with other users.\n"
            "    8. Any potential areas of expertise or knowledge they may have.\n"
            "    9. Any potential areas of concern or red flags based on their activity.\n"
            "    10. Any other relevant insights that can be drawn from their activity.\n\n"

            "  Use the following guidelines for the analysis:\n"
            "    1. The analysis MUST use the subreddit descriptions to provide context for the user's activities.\n"
            "    2. The analysis MUST use activity upvotes and downvotes to gauge the reception and relevance of "
            "the post or comment.\n"
            "    3. The analysis MUST be comprehensive, covering all aspects of the user's activity.\n"
            "    4. The output MUST be in a professional tone, suitable for a report or summary.\n"
            "    5. The output MUST be in a markdown format.\n"
            "    6. The output MUST be structured with clear sections for each analysis point.\n"
            "    7. The output MUST be concise, insightful, and well-organized.\n"
            "    8. The output MUST NOT include any personal opinions or biases.\n"
            "    9. The output MUST NOT include any irrelevant information or tangents.\n"
            "</Instructions>\n"
        )

        # Format activities as XML
        activities_xml = "  <Activities>\n"
        for activity in activities_for_llm:
            activities_xml += activity.to_xml(include_post_bodies, max_post_body_length) + "\n"
        activities_xml += "  </Activities>\n"

        # Combine XML prompt
        prompt = (
            "<RedditAnalysisRequest>\n"
            f"  {instructions_xml}"
            f"  {subreddit_context_xml}"
            f"  {activities_xml}"
            "</RedditAnalysisRequest>"
        )

        chat_history = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {"contents": chat_history}

        logging.info(f"Sending {len(activities_for_llm)} combined activities to LLM for analysis.")
        logging.info(f"LLM Prompt (XML):\n{prompt}...\n")

        try:
            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json=payload,
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
                return f"LLM response structure unexpected: {json.dumps(result, indent=2)}"

        except requests.exceptions.RequestException as e:
            logging.error(f"An error occurred during LLM API call: {e}")
            return f"An error occurred during LLM API call: {e}"
        except Exception as e:
            logging.error(f"An unexpected error occurred during LLM analysis: {e}")
            return f"An unexpected error occurred during LLM analysis: {e}"

    def summarize_analysis(self, full_analysis: str, max_length: int = 350) -> str:
        """Generate a conversational, concise summary of the analysis for TTS, using an XML prompt structure."""
        # XML instructions for summary
        instructions_xml = (
            "<Instructions>\n"
            "  1. Summarize the following Reddit user analysis in a conversational, professional tone.\n"
            "  2. Avoid section headers, markdown, or lists. Make it sound like you're giving a quick spoken "
            "overview to a professional colleague.\n"
            f"  3. Limit the summary to {max_length} words or less.\n"
            "</Instructions>\n"
        )

        # Wrap the full analysis in XML
        analysis_xml = f"<Analysis>\n  {html.escape(full_analysis)}\n</Analysis>\n"

        prompt = f"<RedditSummaryRequest>\n  {instructions_xml}  {analysis_xml}</RedditSummaryRequest>"

        logging.debug(f"LLM Summary Prompt (XML):\n{prompt}")

        chat_history = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {"contents": chat_history}

        try:
            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json=payload,
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
                return f"LLM response structure unexpected: {json.dumps(result, indent=2)}"
        except requests.exceptions.RequestException as e:
            logging.error(f"An error occurred during LLM API call: {e}")
            return f"An error occurred during LLM API call: {e}"
        except Exception as e:
            logging.error(f"An unexpected error occurred during LLM summary: {e}")
            return f"An unexpected error occurred during LLM summary: {e}"
