# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Tuple, Any

from rapidfuzz import fuzz

from services.cache_manager import TTLCache
from utils.text import normalize_text, extract_search_tokens
from utils.logging import get_logger

logger = get_logger("search_engine")

@dataclass(slots=True)
class IndexedFile:
    id: str
    caption: str
    file_type: str
    file_name: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    master_file_id: Optional[str]
    delivery_file_id: Optional[str]
    source_chat_id: Optional[int]
    source_message_id: Optional[int]
    created_at: Optional[str]
    normalized_caption: str

class SearchEngine:

    def __init__(
        self,
        cache_size: int = 1000,
        strict_and: bool = True,
        fuzzy_enabled: bool = True,
        fuzzy_threshold: int = 75,
    ):
        self.strict_and = strict_and
        self.fuzzy_enabled = fuzzy_enabled
        self.fuzzy_threshold = fuzzy_threshold

        self._files: Dict[str, IndexedFile] = {}
        self._token_to_file_ids: Dict[str, Set[str]] = {}
        self._version: int = 0

        self._query_cache: TTLCache[List[str]] = TTLCache(maxsize=cache_size, default_ttl=300.0)

    @property
    def total_files(self) -> int:
        return len(self._files)

    @property
    def total_tokens(self) -> int:
        return len(self._token_to_file_ids)

    @property
    def version(self) -> int:
        return self._version

    def build_index(self, raw_files: List[Dict[str, Any]], version: int = 1) -> None:
        start_time = time.perf_counter()
        new_files: Dict[str, IndexedFile] = {}
        new_token_index: Dict[str, Set[str]] = {}

        for item in raw_files:
            file_id = str(item.get("id", ""))
            if not file_id:
                continue

            caption = item.get("caption") or ""
            norm_caption = normalize_text(caption)

            indexed_file = IndexedFile(
                id=file_id,
                caption=caption,
                file_type=item.get("file_type", "document"),
                file_name=item.get("file_name"),
                file_size=item.get("file_size"),
                mime_type=item.get("mime_type"),
                master_file_id=item.get("master_file_id"),
                delivery_file_id=item.get("delivery_file_id"),
                source_chat_id=item.get("source_chat_id"),
                source_message_id=item.get("source_message_id"),
                created_at=item.get("created_at"),
                normalized_caption=norm_caption,
            )
            new_files[file_id] = indexed_file

            tokens = extract_search_tokens(caption)

            if indexed_file.file_name:
                tokens.extend(extract_search_tokens(indexed_file.file_name))

            for tok in set(tokens):
                if tok not in new_token_index:
                    new_token_index[tok] = set()
                new_token_index[tok].add(file_id)

        self._files = new_files
        self._token_to_file_ids = new_token_index
        self._version = version
        self._query_cache.clear()

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Search index built: %d files, %d unique tokens (took %.2f ms, version=%d)",
            len(self._files),
            len(self._token_to_file_ids),
            elapsed_ms,
            version,
        )

    def get_file(self, file_id: str) -> Optional[IndexedFile]:
        return self._files.get(file_id)

    def search(
        self,
        query: str,
        limit: int = 100,
        enable_fuzzy: Optional[bool] = None,
    ) -> List[IndexedFile]:
        norm_query = normalize_text(query)
        if not norm_query:
            return []

        cache_key = f"q:{norm_query}:{limit}"
        cached_ids = self._query_cache.get(cache_key)
        if cached_ids is not None:
            results = [self._files[fid] for fid in cached_ids if fid in self._files]
            return results

        tokens = extract_search_tokens(norm_query)
        if not tokens:
            return []

        candidate_ids = self._find_candidates(tokens)

        use_fuzzy = self.fuzzy_enabled if enable_fuzzy is None else enable_fuzzy
        if not candidate_ids and use_fuzzy and len(norm_query) >= 3:
            candidate_ids = self._fuzzy_search_candidates(norm_query, tokens)

        if not candidate_ids:
            self._query_cache.set(cache_key, [])
            return []

        scored_results = self._rank_candidates(candidate_ids, norm_query, tokens)

        top_files = [res[0] for res in scored_results[:limit]]
        top_ids = [f.id for f in top_files]

        self._query_cache.set(cache_key, top_ids)
        return top_files

    def _find_candidates(self, tokens: List[str]) -> Set[str]:
        if not tokens:
            return set()

        if self.strict_and:

            token_sets: List[Set[str]] = []
            for tok in tokens:
                s = self._token_to_file_ids.get(tok)
                if not s:

                    return set()
                token_sets.append(s)

            token_sets.sort(key=len)
            candidates = set(token_sets[0])
            for s in token_sets[1:]:
                candidates.intersection_update(s)
                if not candidates:
                    break
            return candidates
        else:
            candidates: Set[str] = set()
            for tok in tokens:
                s = self._token_to_file_ids.get(tok)
                if s:
                    candidates.update(s)
            return candidates

    def _fuzzy_search_candidates(self, norm_query: str, tokens: List[str], max_candidates: int = 200) -> Set[str]:
        fuzzy_matched_file_ids: Set[str] = set()

        for query_tok in tokens:
            if len(query_tok) < 3:
                continue
            for indexed_tok, file_ids in self._token_to_file_ids.items():
                if abs(len(indexed_tok) - len(query_tok)) > 2:
                    continue
                score = fuzz.ratio(query_tok, indexed_tok)
                if score >= self.fuzzy_threshold:
                    fuzzy_matched_file_ids.update(file_ids)
                    if len(fuzzy_matched_file_ids) >= max_candidates:
                        break
            if len(fuzzy_matched_file_ids) >= max_candidates:
                break

        return fuzzy_matched_file_ids

    def _rank_candidates(
        self,
        candidate_ids: Set[str],
        norm_query: str,
        tokens: List[str],
    ) -> List[Tuple[IndexedFile, float]]:
        scored: List[Tuple[IndexedFile, float]] = []
        token_set = set(tokens)

        for fid in candidate_ids:
            f = self._files.get(fid)
            if not f:
                continue

            caption_norm = f.normalized_caption
            score = 0.0

            if caption_norm == norm_query:
                score += 1000.0

            if norm_query in caption_norm:
                score += 500.0
                if caption_norm.startswith(norm_query):
                    score += 200.0

            matched_count = 0
            for t in token_set:
                if t in caption_norm:
                    matched_count += 1
                if f"#{t}" in f.caption.lower():
                    score += 100.0

            coverage = (matched_count / len(tokens)) if tokens else 0.0
            score += coverage * 100.0

            if len(candidate_ids) <= 1000:
                rf_score = fuzz.partial_ratio(norm_query, caption_norm)
                score += rf_score * 0.5

            scored.append((f, score))

        scored.sort(
            key=lambda x: (x[1], x[0].created_at or "", x[0].id),
            reverse=True,
        )
        return scored


    def remove_file(self, file_id: str) -> bool:
        f = self._files.pop(file_id, None)
        if not f:
            return False
        self._query_cache.clear()
        for tok_set in self._token_to_file_ids.values():
            tok_set.discard(file_id)
        logger.info("Removed inaccessible file from search engine: %s", file_id)
        return True

    def get_all_files(self, file_type: Optional[str] = None) -> List[IndexedFile]:
        files = list(self._files.values())
        if file_type:
            ft = file_type.lower()
            files = [f for f in files if (f.file_type or "").lower() == ft]
        files.sort(key=lambda x: x.created_at or "", reverse=True)
        return files

    def get_random_files(self, count: int = 5, file_type: Optional[str] = None) -> List[IndexedFile]:
        import random
        files = self.get_all_files(file_type)
        if not files:
            return []
        sample_size = min(max(1, count), len(files))
        return random.sample(files, sample_size)

    def count_by_file_type(self, candidate_ids: Optional[Set[str]] = None) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        target_ids = candidate_ids if candidate_ids is not None else set(self._files.keys())
        for fid in target_ids:
            f = self._files.get(fid)
            if f:
                ft = (f.file_type or "document").lower()
                counts[ft] = counts.get(ft, 0) + 1
        return counts
