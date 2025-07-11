"""LLM service for analyzing Reddit activity."""

import logging
from typing import Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import Comment, Post, RedditAnalysisRequest, RedditSummaryRequest, SubredditContext


class LLMService:
    """Service for analyzing Reddit activity using a language model."""

    def __init__(self, api_key: str):
        """Initialize the LLM service with API key."""
        self.api_key = api_key
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=api_key)

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

        # Transform data into Pydantic models
        pydantic_activities = []
        for activity in activities_for_llm:
            if isinstance(activity, Comment):
                pydantic_activities.append(activity)
            elif isinstance(activity, Post):
                # For posts, we might need to truncate the body if include_post_bodies is True
                # and the selftext exceeds max_post_body_length.
                # The Pydantic Post model now has an optional 'body' field.
                if include_post_bodies and activity.selftext:
                    activity.selftext = activity.selftext[:max_post_body_length]
                else:
                    activity.selftext = None  # Ensure selftext is None if not included

                pydantic_activities.append(activity)

        subreddit_contexts = (
            [SubredditContext(name=sub, description=desc) for sub, desc in subreddit_descriptions.items()]
            if subreddit_descriptions
            else []
        )

        analysis_request = RedditAnalysisRequest(subreddit_contexts=subreddit_contexts, activities=pydantic_activities)

        # Define the prompt template to accept a JSON blob
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert analyst. The user will provide you with a JSON object "
                    "containing a user's Reddit activity. Your task is to perform a detailed "
                    "analysis based on the provided data and instructions.",
                ),
                (
                    "human",
                    "Please analyze the following Reddit user data and provide a comprehensive "
                    "report. The data is structured in JSON format and includes subreddit "
                    "descriptions for context and a list of the user's recent activities "
                    "(posts and comments).\n\n"
                    "Use all of the information in `subreddit_contexts` and `activities` to "
                    "infer the following:\n"
                    "1. The user's likely personality traits.\n"
                    "2. Their general interests.\n"
                    "3. Any recurring themes or patterns in their discussions.\n"
                    "4. How to best engage with this user in future interactions.\n"
                    "5. Any notable events or changes in their activity over time.\n"
                    "6. Any potential biases or perspectives that may influence their opinions.\n"
                    "7. Any significant relationships or interactions with other users.\n"
                    "8. Any potential areas of expertise or knowledge they may have.\n"
                    "9. Any potential areas of concern or red flags based on their activity.\n"
                    "10. Any other relevant insights that can be drawn from their activity.\n\n"
                    "Use the following guidelines for the analysis:\n"
                    "1. The analysis MUST use the subreddit descriptions to provide context for "
                    "the user's activities.\n"
                    "2. The analysis MUST use activity upvotes and downvotes to gauge the "
                    "reception and relevance of the post or comment.\n"
                    "3. The analysis MUST be comprehensive, covering all aspects of the user's "
                    "activity.\n"
                    "4. The output MUST be in a professional tone, suitable for a report or "
                    "summary.\n"
                    "5. The output MUST be in a markdown format.\n"
                    "6. The output MUST be structured with clear sections for each analysis point.\n"
                    "7. The output MUST be concise, insightful, and well-organized.\n"
                    "8. The output MUST NOT include any personal opinions or biases.\n"
                    "9. The output MUST NOT include any irrelevant information or tangents.\n\n"
                    "Here is the data:\n"
                    "```json\n"
                    "{analysis_request}\n"
                    "```",
                ),
            ]
        )

        chain = prompt_template | self.llm
        logging.info(f"Sending {len(pydantic_activities)} combined activities to LLM for analysis.")

        try:
            response = chain.invoke({"analysis_request": analysis_request.model_dump_json(indent=2)})
            return response.content
        except Exception as e:
            logging.error(f"An unexpected error occurred during LLM analysis: {e}")
            return f"An unexpected error occurred during LLM analysis: {e}"

    def summarize_analysis(self, full_analysis: str, max_length: int = 350) -> str:
        """Generate a conversational, concise summary of the analysis for TTS."""
        summary_request = RedditSummaryRequest(full_analysis=full_analysis)

        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert summarizer. The user will provide you with a JSON object "
                    "containing a detailed analysis of a Reddit user. Your task is to create a "
                    "concise, conversational summary suitable for a text-to-speech (TTS) system.",
                ),
                (
                    "human",
                    "Please summarize the following Reddit user analysis in a conversational, "
                    "professional tone. Avoid section headers, markdown, or lists. Make it sound "
                    "like you're giving a quick spoken overview to a professional colleague. "
                    "Limit the summary to {max_length} words or less.\n\n"
                    "Here is the analysis to summarize:\n"
                    "```json\n"
                    "{summary_request}\n"
                    "```",
                ),
            ]
        )

        chain = prompt_template | self.llm
        logging.debug("Generating LLM summary...")

        try:
            response = chain.invoke(
                {
                    "max_length": max_length,
                    "summary_request": summary_request.model_dump_json(indent=2),
                }
            )
            return response.content
        except Exception as e:
            logging.error(f"An unexpected error occurred during LLM summary: {e}")
            return f"An unexpected error occurred during LLM summary: {e}"
