import httpx
import logging
import difflib
import time
from typing import List, Optional, Dict

logger = logging.getLogger("router.ollama_client")

class OllamaClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self._cached_models: List[str] = []
        self._last_fetch_time = 0
        self._cache_ttl = 60  # seconds

    async def get_models(self) -> List[str]:
        """Fetch available model tags from Ollama."""
        now = time.time()
        if self._cached_models and (now - self._last_fetch_time < self._cache_ttl):
            return self._cached_models

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    self._cached_models = models
                    self._last_fetch_time = now
                    return models
                else:
                    logger.warning(f"Ollama tags returned status {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to fetch models from Ollama: {e}")
        
        return self._cached_models or []

    async def find_best_model(self, requested_model: str) -> str:
        """Find the best matching model tag for a requested name."""
        available_models = await self.get_models()
        if not available_models:
            return requested_model

        if requested_model in available_models:
            return requested_model

        # Handle common version mismatches (e.g., qwen -> qwen:latest or qwen2.5)
        # 1. Try case-insensitive exact match
        for model in available_models:
            if model.lower() == requested_model.lower():
                return model

        # 2. Try adding :latest if not present
        if ":" not in requested_model:
            latest_version = f"{requested_model}:latest"
            if latest_version in available_models:
                return latest_version

        # 3. Fuzzy matching using difflib
        matches = difflib.get_close_matches(requested_model, available_models, n=1, cutoff=0.6)
        if matches:
            logger.info(f"Fuzzy matched model '{requested_model}' -> '{matches[0]}'")
            return matches[0]

        return requested_model

    async def probe_model(self, model_name: str) -> bool:
        """Verify if a model is ready/pulled."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/show", json={"name": model_name})
                return resp.status_code == 200
        except Exception:
            return False
