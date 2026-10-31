import re
import time
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

class CacheStats(BaseModel):
    total_entries: int = 0
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    cache_saved_cost: float = 0.0
    cache_saved_tokens: int = 0

class CachedResponse(BaseModel):
    prompt_hash: str
    normalized_prompt: str
    response: str
    model: str
    tier: str
    quality: float
    cost: float
    input_tokens: int
    output_tokens: int
    created_at: float

class SemanticCache:
    """
    Lightweight Semantic & Exact Hash Cache.
    Normalizes text, computes deterministic hash, and prevents duplicate LLM invocations.
    Tracks saved tokens, saved costs, and hit rates.
    """

    STOPWORDS = {
        "can", "you", "in", "terms", "the", "a", "an", "please", "me", "of", "to",
        "is", "are", "for", "on", "it", "this", "that", "with", "what", "how", "tell",
        "describe", "give"
    }

    def __init__(self, similarity_threshold: float = 0.70):
        self.similarity_threshold = similarity_threshold
        self._cache: Dict[str, CachedResponse] = {}
        self.stats = CacheStats()

    @staticmethod
    def normalize_prompt(text: str) -> str:
        """
        Normalizes prompt by stripping whitespace, lowercasing,
        and standardizing punctuation spacing.
        """
        if not text:
            return ""
        cleaned = text.lower().strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"[^\w\s]", "", cleaned)  # Remove punctuation for fuzzy match
        return cleaned

    @classmethod
    def extract_semantic_tokens(cls, text: str) -> set:
        """
        Extracts stemmed semantic keywords with common stopwords filtered out.
        Enables cross-phrasing semantic similarity matching.
        """
        clean = cls.normalize_prompt(text)
        words = clean.split()
        return {w[:5] for w in words if w not in cls.STOPWORDS and len(w) > 2}

    @classmethod
    def compute_hash(cls, normalized_text: str) -> str:
        return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    def get(self, prompt: str) -> Optional[CachedResponse]:
        """
        Lookup cache: First checks exact SHA-256 hash of normalized text.
        Then checks stemmed token similarity for semantic match.
        """
        self.stats.total_requests += 1
        norm = self.normalize_prompt(prompt)
        p_hash = self.compute_hash(norm)

        # 1. Exact Hash Match
        if p_hash in self._cache:
            entry = self._cache[p_hash]
            self.stats.cache_hits += 1
            self.stats.cache_saved_cost = round(self.stats.cache_saved_cost + entry.cost, 4)
            self.stats.cache_saved_tokens += (entry.input_tokens + entry.output_tokens)
            self._update_hit_rate()
            return entry

        # 2. Semantic Similarity Match (stemmed keywords + stopword filter)
        prompt_tokens = self.extract_semantic_tokens(prompt)
        if len(prompt_tokens) >= 2:
            for entry in self._cache.values():
                entry_tokens = self.extract_semantic_tokens(entry.normalized_prompt)
                intersection = prompt_tokens.intersection(entry_tokens)
                union = prompt_tokens.union(entry_tokens)
                similarity = len(intersection) / len(union) if union else 0.0

                if similarity >= self.similarity_threshold:
                    self.stats.cache_hits += 1
                    self.stats.cache_saved_cost = round(self.stats.cache_saved_cost + entry.cost, 4)
                    self.stats.cache_saved_tokens += (entry.input_tokens + entry.output_tokens)
                    self._update_hit_rate()
                    return entry

        # Cache Miss
        self.stats.cache_misses += 1
        self._update_hit_rate()
        return None

    def set(
        self,
        prompt: str,
        response: str,
        model: str,
        tier: str,
        quality: float,
        cost: float,
        input_tokens: int,
        output_tokens: int
    ) -> CachedResponse:
        norm = self.normalize_prompt(prompt)
        p_hash = self.compute_hash(norm)

        entry = CachedResponse(
            prompt_hash=p_hash,
            normalized_prompt=norm,
            response=response,
            model=model,
            tier=tier,
            quality=quality,
            cost=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            created_at=time.time()
        )
        self._cache[p_hash] = entry
        return entry

    def get_stats(self) -> CacheStats:
        self.stats.total_entries = len(self._cache)
        return self.stats

    def clear(self) -> None:
        self._cache.clear()
        self.stats = CacheStats()

    def _update_hit_rate(self) -> None:
        if self.stats.total_requests > 0:
            rate = (self.stats.cache_hits / self.stats.total_requests) * 100.0
            self.stats.cache_hit_rate = round(rate, 2)
        else:
            self.stats.cache_hit_rate = 0.0

# Singleton global cache instance for the application
global_cache = SemanticCache()
