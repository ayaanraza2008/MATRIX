"""MATRIX Request Deduplication & Single-Flight Idempotency Engine.
Prevents duplicate execution of identical user requests, protects against
rapid double-clicks, duplicate WebSocket/REST submissions, and ensures
exactly-once processing semantics across MATRIX Brain and Multi-Agent Orchestrator.
"""
import asyncio
import hashlib
import time
from typing import Dict, Any, Optional, Tuple, Callable, Awaitable
from config.logging_config import get_logger

logger = get_logger("core.deduplication")


class IdempotencyManager:
    """Guarantees single-flight execution and debounced deduplication for user requests."""

    def __init__(self, ttl_seconds: float = 60.0, debounce_window_seconds: float = 4.0):
        self._ttl_seconds = ttl_seconds
        self._debounce_window = debounce_window_seconds
        # In-flight executions: key -> asyncio.Future
        self._in_flight: Dict[str, asyncio.Future] = {}
        # Completed response cache: key -> (timestamp, response_data)
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    def generate_dedup_key(
        self,
        session_id: str,
        user_prompt: str,
        request_id: Optional[str] = None
    ) -> str:
        """Derive an idempotency key.
        If explicit request_id is supplied, use it directly.
        Otherwise, hash session_id, normalized prompt, and a rolling debounce window.
        """
        if request_id and request_id.strip():
            return f"req:{request_id.strip()}"

        # Clean and normalize prompt
        norm_prompt = " ".join(user_prompt.strip().lower().split())
        # Rolling time window prevents double-click within debounce window
        # while permitting the user to ask the same question again later
        window_bucket = int(time.time() // self._debounce_window)
        raw_sig = f"{session_id}:{norm_prompt}:{window_bucket}"
        sig_hash = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()[:16]
        return f"auto:{sig_hash}"

    async def execute_single_flight(
        self,
        key: str,
        execution_coro_fn: Callable[[], Awaitable[Dict[str, Any]]]
    ) -> Tuple[Dict[str, Any], bool]:
        """Execute a task with strict single-flight and caching semantics.
        
        Returns:
            Tuple of (result_data, is_duplicate)
        """
        now = time.time()

        # 1. Check completed cache under lock
        async with self._lock:
            self._cleanup_expired(now)
            if key in self._cache:
                cached_time, cached_result = self._cache[key]
                logger.info(f"Deduplication hit for key '{key}' (cached {now - cached_time:.2f}s ago). Returning cached response.")
                duplicate_result = dict(cached_result)
                duplicate_result["deduplicated"] = True
                duplicate_result["dedup_source"] = "cache"
                return duplicate_result, True

            # 2. Check if identical request is currently in-flight
            if key in self._in_flight:
                logger.info(f"Single-flight join for key '{key}'. Awaiting active in-flight task.")
                future = self._in_flight[key]
            else:
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                self._in_flight[key] = future
                future = None  # We will be the runner

        # If someone else is running it, await their future
        if future is not None:
            try:
                res = await future
                dup_res = dict(res)
                dup_res["deduplicated"] = True
                dup_res["dedup_source"] = "in_flight"
                return dup_res, True
            except Exception as e:
                logger.warning(f"Awaited in-flight task failed: {e}")
                raise

        # We are the primary runner
        runner_future = self._in_flight[key]
        try:
            result = await execution_coro_fn()
            result["deduplicated"] = False

            # Cache successful result
            async with self._lock:
                self._cache[key] = (time.time(), result)
                if not runner_future.done():
                    runner_future.set_result(result)
            return result, False

        except Exception as ex:
            async with self._lock:
                if not runner_future.done():
                    runner_future.set_exception(ex)
            raise
        finally:
            async with self._lock:
                self._in_flight.pop(key, None)

    def _cleanup_expired(self, current_time: float):
        """Remove entries older than TTL."""
        expired = [
            k for k, (ts, _) in self._cache.items()
            if (current_time - ts) > self._ttl_seconds
        ]
        for k in expired:
            self._cache.pop(k, None)

    def clear(self):
        """Clear cache and reset."""
        self._cache.clear()
        self._in_flight.clear()


# Global Idempotency Manager singleton
idempotency_manager = IdempotencyManager()
