from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from reddit_who_dis import CacheManager, LLMService, RedditService
import os

app = FastAPI(title="Reddit Who Dis API")


class AnalysisRequest(BaseModel):
    username: str
    comments_limit: int = 100
    posts_limit: int = 50
    include_post_bodies: bool = True
    llm_activities_limit: int = 200
    max_post_body_length: int = 500
    include_parent_context: bool = True
    max_parent_context_length: int = 500
    max_comment_length: int = 500
    force_refresh: bool = False
    use_cache: bool = True


@app.post("/analyze")
def analyze_user(req: AnalysisRequest):
    # Build config dict
    config_dict = req.model_dump()
    config_dict.update(
        {
            "reddit_client_id": os.getenv("REDDIT_CLIENT_ID"),
            "reddit_client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
            "reddit_user_agent": os.getenv("REDDIT_USER_AGENT", "script:reddit-who-dis:v1.0"),
            "google_api_key": os.getenv("GOOGLE_API_KEY"),
            "cache_days": int(os.getenv("CACHE_DAYS", 7)),
        }
    )

    # Validate required env vars
    for var in ["reddit_client_id", "reddit_client_secret", "google_api_key"]:
        if not config_dict.get(var):
            raise HTTPException(status_code=500, detail=f"Missing env var: {var}")

    cache_manager = CacheManager(cache_days=config_dict["cache_days"])
    if req.use_cache and not req.force_refresh:
        cached = cache_manager.get_cached_result(req.username, config_dict)
        if cached:
            return cached["result"]

    reddit_service = RedditService(
        client_id=config_dict["reddit_client_id"],
        client_secret=config_dict["reddit_client_secret"],
        user_agent=config_dict["reddit_user_agent"],
    )
    llm_service = LLMService(api_key=config_dict["google_api_key"])

    redditor = reddit_service.fetch_redditor(req.username)
    if not redditor:
        raise HTTPException(status_code=404, detail="User not found")

    user_info = reddit_service.get_user_info(req.username)
    user_comments = reddit_service.fetch_comments(
        redditor,
        limit=req.comments_limit,
        include_parent_context=req.include_parent_context,
        max_parent_context_length=req.max_parent_context_length,
        max_comment_length=req.max_comment_length,
    )
    user_posts = reddit_service.fetch_posts(redditor, limit=req.posts_limit)
    subreddit_descriptions = reddit_service.get_subreddit_descriptions(
        user_comments,
        user_posts,
        cache_manager=cache_manager,
        force_refresh=req.force_refresh,
    )

    if not (user_comments or user_posts):
        raise HTTPException(status_code=404, detail="No comments or posts found")

    llm_analysis = llm_service.analyze_reddit_activity(
        user_comments,
        user_posts,
        subreddit_descriptions=subreddit_descriptions,
        include_post_bodies=req.include_post_bodies,
        max_activities=req.llm_activities_limit,
        max_post_body_length=req.max_post_body_length,
    )
    result = {"user_info": user_info, "llm_analysis": llm_analysis}
    if req.use_cache:
        cache_manager.save_result(req.username, config_dict, result)
    return result
