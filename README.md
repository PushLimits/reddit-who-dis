# Reddit Who Dis 🔍

## Purpose

**Reddit Who Dis** analyzes a Reddit user's public activity using Large Language Models (currently Google Gemini). It provides insights into:
- Personality traits and interests
- Activity patterns and engagement
- Subreddit participation context
- Historical behavior analysis

## Prompt Format (as of v1.1.0)

The LLM prompt is structured as XML for robust parsing and context separation. All user and subreddit data is sanitized to prevent invalid XML. Example structure:

```
<RedditAnalysisRequest>
  <SubredditContexts>
    <Subreddit name="sub1">Description</Subreddit>
    ...
  </SubredditContexts>
  <Instructions>
    ...
  </Instructions>
  <Activities>
    <Activity type="comment" subreddit="sub1" created_utc="...">
      <Content>
        <Body>...</Body>
        <ParentContext>...</ParentContext>
      </Content>
    </Activity>
    <Activity type="post" subreddit="sub2" created_utc="...">
      <Content>
        <Title>...</Title>
        <Body>...</Body>
      </Content>
    </Activity>
    ...
  </Activities>
</RedditAnalysisRequest>
```

- All dynamic fields are escaped for XML safety using Python's `html.escape`.
- The `to_xml` method is implemented on all activity models for robust serialization.
- Subreddit context is serialized using `subreddit_contexts_to_xml`.
- No fallback string parsing is used; all serialization is model-driven.

## Quick Start 🚀

1. **Setup:**
   ```sh
   git clone https://github.com/yourusername/reddit-who-dis.git
   cd reddit-who-dis
   uv pip install -r requirements.txt
   cp .env.example .env
   ```

2. **Configure API Keys:**
   Edit your `.env` file:
   ```env
   REDDIT_CLIENT_ID=your_client_id        # From reddit.com/prefs/apps
   REDDIT_CLIENT_SECRET=your_secret       # From reddit.com/prefs/apps
   GOOGLE_API_KEY=your_gemini_key         # Your Google Gemini API key
   REDDIT_USER_AGENT=reddit-who-dis:v1.1  # Custom user agent
   ```

3. **Run Analysis:**
   ```sh
   uv run python main.py <username> [options]
   ```

## Features ✨

- **Smart Caching:** Subreddit descriptions cached for 30 days
- **Configurable Depth:** Control how much history to analyze
- **Context Aware:** Includes subreddit descriptions for better analysis
- **Privacy Focused:** Only processes public data
- **Rate Limit Friendly:** Respects API limitations
- **Robust XML Prompt:** All data is sanitized and structured for LLMs

## Usage Options 🛠️

```sh
python main.py <username> [options]

Options:
  --comments-limit N            Max comments to analyze (default: 100)
  --posts-limit N               Max posts to analyze (default: 50)
  --include-post-bodies         Include full post bodies in LLM analysis instead of just titles (default: True)
  --llm-activities-limit N      Total combined activities (comments + posts) to send to LLM (default: 200)
  --max-post-body-length N      Maximum length of post bodies to include in LLM analysis (default: 500)
  --include-parent-context      Include parent comment context in user comments (default: True)
  --max-parent-context-length N Maximum length of parent comment context to include (default: 500)
  --max-comment-length N        Maximum length of user comment bodies to include (default: 500)
  --cache-days N                Number of days to cache analysis results (default: 7)
  --force-refresh               Force refresh of cached results (default: False)
  --no-cache                    Disable caching of results (default: False)
```

**Example:**
```sh
python main.py spez --comments-limit 100 --include-post-bodies --max-post-body-length 300 --no-cache --force-refresh
```

## Important Notes ⚠️

- **Rate Limits:** Respect Reddit and Google API limits
- **Privacy:** Only analyzes public data; do not use for harassment
- **Accuracy:** LLM analyses are interpretations, not facts
- **Token Limits:** Large histories are analyzed partially
- **Security:** Never commit API credentials
- **Cache:** `.cache/` directory stores subreddit data

## Contributing 🤝

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a Pull Request

## License

[MIT License](LICENSE)

---

*For support or questions, please [open an issue](https://github.com/yourusername/reddit-who-dis/issues).*