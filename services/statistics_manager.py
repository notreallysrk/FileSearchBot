# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from __future__ import annotations

import asyncio
from typing import Optional, Dict
from database.statistics import StatisticsRepository
from utils.logging import get_logger

logger = get_logger("statistics_manager")

class StatisticsManager:

    def __init__(
        self,
        stats_repo: StatisticsRepository,
        max_queue_size: int = 5000,
        flush_interval: float = 2.0,
    ):
        self.stats_repo = stats_repo
        self.max_queue_size = max_queue_size
        self.flush_interval = flush_interval

        self._queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task: Optional[asyncio.Task] = None
        self._running: bool = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._flush_worker(), name="stats_flush_worker")
        logger.info("Statistics background manager started")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            await self.flush()
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info("Statistics background manager stopped")

    def record_event(self, field: str, amount: int = 1) -> None:
        try:
            self._queue.put_nowait((field, amount))
        except asyncio.QueueFull:
            logger.warning("Statistics queue is full. Dropping non-critical event for %s", field)

    def record_search(self) -> None:
        self.record_event("searches_performed", 1)

    def record_delivery_success(self) -> None:
        self.record_event("successful_deliveries", 1)

    def record_delivery_failure(self) -> None:
        self.record_event("failed_deliveries", 1)

    async def flush(self) -> None:
        if self._queue.empty():
            return

        batch: Dict[str, int] = {}
        while not self._queue.empty():
            try:
                field, amount = self._queue.get_nowait()
                batch[field] = batch.get(field, 0) + amount
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break

        for field, total in batch.items():
            try:
                await self.stats_repo.increment_counter(field, total)
            except Exception as exc:
                logger.error("Failed to flush stats counter %s: %s", field, exc)

    async def _flush_worker(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Error in statistics background worker: %s", exc)
