# Reddit Who Dis

## Overview

Reddit Who Dis is a technical tool for analyzing a Reddit user's public activity using Large Language Models (LLMs), currently supporting Google Gemini. The tool provides structured insights into user behavior, personality, subreddit participation, and historical activity. It is designed for research, moderation, and data analysis purposes, and emphasizes robust, model-driven XML prompt construction for LLMs.

## Features

- Structured XML prompt generation for LLMs
- Smart caching of subreddit descriptions and analysis results
- Configurable analysis depth and limits
- Context-aware: includes subreddit descriptions and parent comment context
- Privacy-focused: only processes public Reddit data
- Rate limit friendly: respects Reddit and Google API limitations
- Modular codebase for easy extension and testing
- Text-to-speech (TTS) synthesis of LLM summaries

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) for dependency management and execution
- [Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI) must be installed and available in your environment (for TTS services)

## Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/PushLimits/reddit-who-dis.git
   cd reddit-who-dis
   ```

2. **Install dependencies using uv:**
   ```sh
   uv pip install -r requirements.txt
   ```
   If you are developing, you may also want to install dev dependencies:
   ```sh
   uv pip install -r requirements-dev.txt
   ```

3. **Install Kokoro-FastAPI:**
   Reddit Who Dis assumes [Kokoro-FastAPI](https://github.com/joelewis101/kokoro-fastapi) is installed and running. Please follow the instructions in the Kokoro-FastAPI repository to set up the required services.

4. **Configure API Keys:**
   Copy the example environment file and edit it with your credentials:
   ```sh
   cp .env.example .env
   ```
   Edit `.env`:
   ```env
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_secret
   GOOGLE_API_KEY=your_gemini_key
   REDDIT_USER_AGENT=reddit-who-dis:v1.1
   ```

## Usage

Run the analysis tool from the command line:

```sh
uv run python main.py <reddit_username> [options]
```

### Options

- `--comments-limit N`            Max comments to analyze (default: 100)
- `--posts-limit N`               Max posts to analyze (default: 50)
- `--include-post-bodies`         Include full post bodies in LLM analysis (default: True)
- `--llm-activities-limit N`      Total combined activities (comments + posts) to send to LLM (default: 200)
- `--max-post-body-length N`      Maximum length of post bodies to include in LLM analysis (default: 500)
- `--include-parent-context`      Include parent comment context in user comments (default: True)
- `--max-parent-context-length N` Maximum length of parent comment context to include (default: 500)
- `--max-comment-length N`        Maximum length of user comment bodies to include (default: 500)
- `--cache-days N`                Number of days to cache analysis results (default: 7)
- `--force-refresh`               Force refresh of cached results (disabled by default)
- `--no-cache`                    Disable caching of results (enabled by default)
- `--no-tts`                      Disable text-to-speech synthesis of the summary (enabled by default)

#### Example

```sh
python main.py spez --comments-limit 100 --include-post-bodies --max-post-body-length 300 --no-cache --force-refresh --no-tts
```

## How It Works

1. **Argument Parsing and Configuration:**
   The tool parses command-line arguments and environment variables to configure analysis parameters and API credentials.

2. **Caching:**
   Results are cached for a configurable number of days. Cached results are used unless `--force-refresh` is specified.

3. **Data Fetching:**
   The tool fetches user info, comments, posts, and subreddit descriptions using the Reddit API. Parent comment context and post bodies are included as configured.

4. **LLM Analysis:**
   Activities and context are serialized to XML and sent to the LLM for analysis. The analysis and a conversational summary are generated.

5. **Text-to-Speech (TTS):**
   The summary is synthesized to audio using the TTS service (via Kokoro-FastAPI).

6. **Output:**
   Results are printed to the console and optionally played as audio.

## Notes and Best Practices

- **Kokoro-FastAPI:** This project assumes Kokoro-FastAPI is installed and running. See: https://github.com/joelewis101/kokoro-fastapi
- **API Limits:** Be aware of Reddit and Google API rate limits. Excessive requests may result in temporary bans or throttling.
- **Privacy:** Only public Reddit data is analyzed. Do not use this tool for harassment or privacy violations.
- **Security:** Never commit API credentials or sensitive data to version control.
- **Cache:** Cached data is stored in the `.cache/` directory by default. You may clear this directory to reset cached results.
- **Token/Prompt Limits:** Large user histories may be truncated to fit LLM token limits. Adjust limits as needed for your use case.

## Contributing

Contributions are welcome. Please fork the repository, create a feature branch, and submit a pull request. Ensure your code is well-documented and tested.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Support

For questions or issues, please open an issue on the GitHub repository.