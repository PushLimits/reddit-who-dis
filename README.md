# Reddit Who Dis 🔍

## Purpose

**Reddit Who Dis** analyzes a Reddit user's public activity using Large Language Models (currently Google Gemini). It provides insights into:
- Personality traits and interests
- Activity patterns and engagement
- Subreddit participation context
- Historical behavior analysis

## Quick Start 🚀

1. **Setup:**
   ```sh
   # Clone and enter directory
   git clone https://github.com/yourusername/reddit-who-dis.git
   cd reddit-who-dis

   # Install dependencies (using uv or pip)
   uv pip install -r requirements.txt
   
   # Configure environment
   cp .env.example .env
   ```

2. **Configure API Keys:**
   ```env
   REDDIT_CLIENT_ID=your_client_id        # From reddit.com/prefs/apps
   REDDIT_CLIENT_SECRET=your_secret       # From reddit.com/prefs/apps
   GOOGLE_API_KEY=your_gemini_key        # Your Google Gemini API key
   REDDIT_USER_AGENT=reddit-who-dis:v1.0  # Custom user agent
   ```

3. **Run Analysis:**
   ```sh
   python main.py USERNAME [options]
   ```

## Features ✨

- **Smart Caching:** Subreddit descriptions cached for 30 days
- **Configurable Depth:** Control how much history to analyze
- **Context Aware:** Includes subreddit descriptions for better analysis
- **Privacy Focused:** Only processes public data
- **Rate Limit Friendly:** Respects API limitations

## Usage Options 🛠️

```sh
python main.py <username> [options]

Options:
  --comments-limit N        Max comments to analyze (default: 50)
  --posts-limit N          Max posts to analyze (default: 50)
  --include-post-bodies    Include full post content in analysis
  --llm-activities-limit N Max activities for LLM (default: 100)
  --max-post-body-length N Truncate posts to length (default: 150)
```

**Example:**
```sh
python main.py spez --comments-limit 100 --include-post-bodies
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