# Reddit Who Dis

## Purpose

**Reddit Who Dis** is a command-line tool that analyzes a Reddit user's public comment and post history using a Large Language Model (LLM, e.g., Google Gemini). It summarizes the user's likely personality, interests, and activity patterns, providing context from the subreddits they participate in.

## Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/reddit-who-dis.git
   cd reddit-who-dis
   ```

2. **Install dependencies:**
   ```sh
   uv pip install -r requirements.txt
   ```
   *(Or use your preferred Python environment manager. [uv](https://github.com/astral-sh/uv) is a fast Python package manager.)*

3. **Set up environment variables:**
   - Copy the provided `.env` file and fill in your credentials:
   ```sh
   cp .env .env.local  # or just edit .env
   # Then edit .env and add your keys
   ```
   - `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`: [Create a Reddit app](https://www.reddit.com/prefs/apps) to get these.
   - `GOOGLE_API_KEY`: Your Google Gemini API key.

   Example `.env` file:
   ```env
   REDDIT_CLIENT_ID=your_id
   REDDIT_CLIENT_SECRET=your_secret
   GOOGLE_API_KEY=your_gemini_key
   REDDIT_USER_AGENT=script:reddit-who-dis:v1.0
   ```

## Usage

```sh
python main.py <reddit_username> [options]
```

**Options:**
- `--comments-limit N` : Max number of comments to fetch (default: 50)
- `--posts-limit N` : Max number of posts to fetch (default: 50)
- `--include-post-bodies` : Include full post bodies in LLM analysis
- `--llm-activities-limit N` : Max combined activities to send to LLM (default: 100)
- `--max-post-body-length N` : Max length of post bodies for LLM (default: 150)

**Example:**
```sh
python main.py spez --comments-limit 100 --posts-limit 100 --include-post-bodies
```

## Caveats

- **API Limits:**  
  Reddit and Google Gemini APIs have rate limits. Heavy use may result in temporary bans or errors.
- **Privacy:**  
  Only public Reddit data is analyzed. Do not use this tool for harassment or privacy violations.
- **Accuracy:**  
  LLM-generated summaries are not always accurate or unbiased.
- **Token Limits:**  
  If a user has a large history, only the most recent activities are analyzed to fit within LLM token limits.
- **Subreddit Descriptions:**  
  Some subreddits may have missing or generic descriptions, which can affect context quality.
- **Security:**  
  Never commit your API keys or secrets to source control.

---

*For questions or contributions, please open an issue or pull request on GitHub.*
