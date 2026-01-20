"""
Specification downloader for A2A TCK.
Downloads the latest specification files from GitHub.
"""

import requests
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class SpecDownloader:
    """Downloads A2A specification files from GitHub."""

    DEFAULT_PROTO_URL = "https://raw.githubusercontent.com/a2aproject/A2A/main/specification/grpc/a2a.proto"
    DEFAULT_MD_URL = "https://raw.githubusercontent.com/a2aproject/A2A/main/docs/specification.md"

    def __init__(self, cache_dir: Path = None):
        """Initialize downloader with optional cache directory."""
        self.cache_dir = cache_dir or Path("spec_tracker/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download_spec(self, proto_url: str = None, md_url: str = None) -> Tuple[str, str]:
        """
        Download specification files with retry logic.

        Args:
            proto_url: URL for proto file (uses default if None)
            md_url: URL for Markdown spec (uses default if None)

        Returns:
            Tuple of (proto_content, markdown_content)
        """
        proto_url = proto_url or self.DEFAULT_PROTO_URL
        md_url = md_url or self.DEFAULT_MD_URL

        try:
            # Download with retry logic
            proto_content = self._download_with_retry(proto_url, "Proto file", is_json=False)
            md_content = self._download_with_retry(md_url, "Markdown spec", is_json=False)

            # Cache the downloads
            self._cache_specs(proto_content, md_content)

            return proto_content, md_content

        except Exception as e:
            logger.error(f"Failed to download specs after retries: {e}")
            # Try to load from cache as fallback
            cached_data = self._load_from_cache()
            if cached_data:
                logger.info("Using cached specifications as fallback")
                return cached_data
            else:
                logger.error("No cached specifications available")
                raise

    def _download_with_retry(self, url: str, description: str, is_json: bool = True, max_retries: int = 3):
        """Download with exponential backoff retry logic."""
        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading {description} from {url} (attempt {attempt + 1}/{max_retries})")
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                if is_json:
                    return response.json()
                else:
                    return response.text

            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to download {description} after {max_retries} attempts: {e}")
                    raise
                else:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2**attempt
                    logger.warning(f"Download attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)

    def _cache_specs(self, proto_content: str, md_content: str):
        """Save downloaded specs to cache with timestamps."""
        try:
            timestamp = datetime.now().isoformat()

            # Cache Proto spec
            proto_cache_file = self.cache_dir / "a2a_spec.proto"
            cache_proto = {"timestamp": timestamp, "content": proto_content}
            with open(proto_cache_file, "w") as f:
                json.dump(cache_proto, f, indent=2)

            # Cache Markdown spec
            md_cache_file = self.cache_dir / "a2a_spec.md"
            cache_md = {"timestamp": timestamp, "content": md_content}
            with open(md_cache_file, "w") as f:
                json.dump(cache_md, f, indent=2)

            logger.info(f"Cached specifications with timestamp {timestamp}")

        except Exception as e:
            logger.warning(f"Failed to cache specifications: {e}")
            # Don't fail the entire operation if caching fails

    def _load_from_cache(self) -> Optional[Tuple[str, str]]:
        """Load specifications from cache if available."""
        try:
            proto_cache_file = self.cache_dir / "a2a_spec.proto"
            md_cache_file = self.cache_dir / "a2a_spec.md"

            if not (proto_cache_file.exists() and md_cache_file.exists()):
                logger.info("No cached specifications found")
                return None

            # Load Proto cache
            with open(proto_cache_file, "r") as f:
                proto_cache = json.load(f)

            # Load Markdown cache
            with open(md_cache_file, "r") as f:
                md_cache = json.load(f)

            logger.info(f"Loaded cached specifications from {proto_cache['timestamp']}")
            return proto_cache["content"], md_cache["content"]

        except Exception as e:
            logger.warning(f"Failed to load cached specifications: {e}")
            return None
