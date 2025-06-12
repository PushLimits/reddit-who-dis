"""Cache manager for Reddit Who Dis results."""

import os
import json
import time
import hashlib
import logging
from typing import Optional, Dict, Any

class CacheManager:
    """Manages caching of Reddit analysis results."""

    def __init__(self, cache_days: int = 7, cache_dir: str = ".cache"):
        """Initialize the cache manager.
        
        Args:
            cache_days: Number of days to keep cached results.
            cache_dir: Directory to store cache files.
        """
        self.cache_days = cache_days
        self.cache_dir = cache_dir
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Ensure the cache directory exists."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def _generate_cache_key(self, username: str, config_hash: str) -> str:
        """Generate a unique cache key based on username and configuration.
        
        Args:
            username: Reddit username being analyzed.
            config_hash: Hash of configuration parameters.
            
        Returns:
            A unique cache key string.
        """
        combined = f"{username}:{config_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _generate_config_hash(self, config_dict: Dict) -> str:
        """Generate a hash of configuration parameters.
        
        Args:
            config_dict: Dictionary of configuration parameters.
            
        Returns:
            A hash string representing the configuration.
        """
        # Remove cache-related keys and sort to ensure consistent hash
        analysis_config = {k: v for k, v in config_dict.items() 
                         if k not in ['cache_days', 'force_refresh', 'use_cache']}
        config_str = json.dumps(analysis_config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def get_cache_path(self, username: str, config_dict: Dict) -> str:
        """Get the cache file path for a given username and configuration.
        
        Args:
            username: Reddit username being analyzed.
            config_dict: Configuration dictionary.
            
        Returns:
            Absolute path to the cache file.
        """
        config_hash = self._generate_config_hash(config_dict)
        cache_key = self._generate_cache_key(username, config_hash)
        return os.path.join(self.cache_dir, f"analysis_{cache_key}.json")

    def get_cached_result(self, username: str, config_dict: Dict) -> Optional[Dict]:
        """Get cached analysis result if it exists and is not expired.
        
        Args:
            username: Reddit username being analyzed.
            config_dict: Configuration dictionary.
            
        Returns:
            Cached result dictionary or None if not found or expired.
        """
        cache_path = self.get_cache_path(username, config_dict)
        
        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)

            # Check if cache is expired
            cache_age = time.time() - cache_data.get('timestamp', 0)
            if cache_age > (self.cache_days * 24 * 60 * 60):
                logging.info(f"Cache for user {username} has expired ({cache_age/86400:.1f} days old)")
                return None

            logging.info(f"Using cached analysis for user {username} ({cache_age/86400:.1f} days old)")
            return cache_data

        except Exception as e:
            logging.warning(f"Error reading cache for user {username}: {e}")
            return None

    def save_result(self, username: str, config_dict: Dict, analysis_result: Dict):
        """Save analysis result to cache.
        
        Args:
            username: Reddit username being analyzed.
            config_dict: Configuration dictionary.
            analysis_result: Analysis result to cache.
        """
        cache_path = self.get_cache_path(username, config_dict)
        cache_data = {
            'username': username,
            'timestamp': time.time(),
            'config_hash': self._generate_config_hash(config_dict),
            'result': analysis_result
        }

        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
            logging.info(f"Saved analysis cache for user {username}")
        except Exception as e:
            logging.error(f"Failed to save cache for user {username}: {e}")

    def get_subreddit_description_cache_path(self) -> str:
        """Get the cache file path for subreddit descriptions.
        
        Returns:
            Absolute path to the subreddit descriptions cache file.
        """
        return os.path.join(self.cache_dir, "subreddit_descriptions_cache.json")

    def get_cached_subreddit_descriptions(self) -> Dict[str, Dict[str, str]]:
        """Get cached subreddit descriptions if they exist.
        
        Returns:
            Dictionary mapping subreddit names to their descriptions and timestamps.
        """
        cache_path = self.get_subreddit_description_cache_path()
        
        if not os.path.exists(cache_path):
            return {}

        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Error reading subreddit description cache: {e}")
            return {}

    def save_subreddit_descriptions(self, descriptions: Dict[str, Dict[str, str]]):
        """Save subreddit descriptions to cache.
        
        Args:
            descriptions: Dictionary mapping subreddit names to dictionaries containing
                        description and timestamp information.
        """
        cache_path = self.get_subreddit_description_cache_path()
        try:
            with open(cache_path, 'w') as f:
                json.dump(descriptions, f)
            logging.info("Updated subreddit description cache")
        except Exception as e:
            logging.error(f"Failed to save subreddit description cache: {e}")

    def get_subreddit_descriptions(
        self,
        reddit_instance: Any,
        subreddits: set[str],
        force_refresh: bool = False
    ) -> Dict[str, str]:
        """Fetch descriptions for subreddits, using a local cache.
        
        Args:
            reddit_instance: PRAW Reddit instance to fetch descriptions with.
            subreddits: Set of subreddit names to get descriptions for.
            force_refresh: Whether to force refresh all descriptions.
            
        Returns:
            Dictionary mapping subreddit names to their descriptions.
        """
        logging.info(f"Found {len(subreddits)} unique subreddits to fetch descriptions for")

        # Load cache
        cache = self.get_cached_subreddit_descriptions()
        now = time.time()
        subreddit_descriptions = {}
        updated = False

        for sub in subreddits:
            cache_entry = cache.get(sub)
            needs_refresh = True

            if not force_refresh and cache_entry and isinstance(cache_entry, dict):
                desc = cache_entry.get("desc")
                ts = cache_entry.get("timestamp", 0)
                if desc is not None and (now - ts) < (self.cache_days * 24 * 60 * 60):
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
                    logging.info(f"Fetched description for r/{sub}: {desc_clean[:100]}...")
                except Exception as e:
                    subreddit_descriptions[sub] = "(Could not fetch description)"
                    cache[sub] = {"desc": "(Could not fetch description)", "timestamp": now}
                    updated = True
                    logging.warning(f"Could not fetch description for r/{sub}: {e}")

        # Save updated cache
        if updated:
            self.save_subreddit_descriptions(cache)

        return subreddit_descriptions
