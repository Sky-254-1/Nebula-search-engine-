"""Scheduler for automated indexing tasks."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Coroutine, Optional


logger = logging.getLogger("nebula.indexing.scheduler")


class ScheduleType(str, Enum):
    """Scheduler types."""
    MANUAL = "manual"
    INTERVAL = "interval"
    CRON = "cron"


@dataclass
class SchedulerConfig:
    """Scheduler configuration."""
    name: str
    schedule_type: ScheduleType
    interval_seconds: Optional[int] = None
    cron_expression: Optional[str] = None
    is_active: bool = True
    last_run: Optional[float] = None
    next_run: Optional[float] = None


class IndexingScheduler:
    """Manages scheduled indexing tasks."""
    
    def __init__(self) -> None:
        self._scheduled_tasks: dict[str, SchedulerConfig] = {}
        self._running = False
        self._loop_task: Optional[Coroutine] = None
        self._callbacks: dict[str, Callable] = {}
    
    def register_task(
        self,
        name: str,
        schedule_type: ScheduleType,
        interval_seconds: Optional[int] = None,
        cron_expression: Optional[str] = None,
        callback: Optional[Callable] = None,
    ) -> SchedulerConfig:
        """
        Register a scheduled task.
        
        Args:
            name: Task name
            schedule_type: Type of schedule
            interval_seconds: Interval in seconds (for interval type)
            cron_expression: Cron expression (for cron type)
            callback: Async function to call
            
        Returns:
            SchedulerConfig
        """
        config = SchedulerConfig(
            name=name,
            schedule_type=schedule_type,
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
        )
        
        self._scheduled_tasks[name] = config
        if callback:
            self._callbacks[name] = callback
        
        # Calculate next run
        if schedule_type == ScheduleType.INTERVAL and interval_seconds:
            config.next_run = time.time() + interval_seconds
        elif schedule_type == ScheduleType.CRON and cron_expression:
            config.next_run = self._calculate_next_cron(cron_expression)
        
        logger.info("Registered scheduled task: %s (type=%s)", name, schedule_type)
        return config
    
    def _calculate_next_cron(self, cron_expression: str) -> float:
        """
        Calculate next run time from cron expression (simplified).
        
        Args:
            cron_expression: Cron expression (e.g., "0 2 * * *" for 2 AM daily)
            
        Returns:
            Next run timestamp
        """
        # Simplified cron parsing - supports daily at hour:minute
        # Format: "minute hour * * *"
        try:
            parts = cron_expression.split()
            if len(parts) >= 2:
                hour = int(parts[0])
                minute = int(parts[1])
                
                now = datetime.now()
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                return next_run.timestamp()
        except Exception as exc:
            logger.debug("Schedule calculation failed: %s", exc)
        
        # Default: run in 1 hour
        return time.time() + 3600
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        self._loop_task = asyncio.create_task(self._schedule_loop())
        logger.info("Scheduler started with %d tasks", len(self._scheduled_tasks))
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Scheduler stopped")
    
    async def _schedule_loop(self) -> None:
        """Main scheduling loop."""
        while self._running:
            now = time.time()
            
            for name, config in self._scheduled_tasks.items():
                if not config.is_active:
                    continue
                
                if config.next_run and now >= config.next_run:
                    # Execute task
                    await self._execute_task(name, config)
                    
                    # Schedule next run
                    if config.schedule_type == ScheduleType.INTERVAL and config.interval_seconds:
                        config.next_run = now + config.interval_seconds
                    elif config.schedule_type == ScheduleType.CRON and config.cron_expression:
                        config.next_run = self._calculate_next_cron(config.cron_expression)
                    
                    config.last_run = now
            
            # Check every minute
            await asyncio.sleep(60)
    
    async def _execute_task(self, name: str, config: SchedulerConfig) -> None:
        """
        Execute a scheduled task.
        
        Args:
            name: Task name
            config: Scheduler config
        """
        logger.info("Executing scheduled task: %s", name)
        
        if name not in self._callbacks:
            logger.warning("No callback for task: %s", name)
            return
        
        try:
            callback = self._callbacks[name]
            if asyncio.iscoroutinefunction(callback):
                await callback()
            else:
                callback()
            
            logger.info("Scheduled task completed: %s", name)
        except Exception as exc:
            logger.error("Scheduled task failed: %s - %s", name, exc)
    
    async def run_task_now(self, name: str) -> bool:
        """
        Manually trigger a task.
        
        Args:
            name: Task name
            
        Returns:
            True if executed
        """
        if name not in self._scheduled_tasks:
            logger.warning("Task not found: %s", name)
            return False
        
        config = self._scheduled_tasks[name]
        await self._execute_task(name, config)
        return True
    
    def get_task_status(self, name: str) -> Optional[dict]:
        """
        Get task status.
        
        Args:
            name: Task name
            
        Returns:
            Task status dict or None
        """
        config = self._scheduled_tasks.get(name)
        if not config:
            return None
        
        return {
            "name": config.name,
            "schedule_type": config.schedule_type.value,
            "is_active": config.is_active,
            "last_run": datetime.fromtimestamp(config.last_run).isoformat() if config.last_run else None,
            "next_run": datetime.fromtimestamp(config.next_run).isoformat() if config.next_run else None,
        }
    
    def get_all_tasks(self) -> list[dict]:
        """Get all scheduled tasks."""
        return [
            {
                "name": config.name,
                "schedule_type": config.schedule_type.value,
                "is_active": config.is_active,
                "last_run": datetime.fromtimestamp(config.last_run).isoformat() if config.last_run else None,
                "next_run": datetime.fromtimestamp(config.next_run).isoformat() if config.next_run else None,
            }
            for config in self._scheduled_tasks.values()
        ]
    
    async def trigger_nightly_reindex(self) -> None:
        """Trigger nightly reindex of all documents."""
        logger.info("Triggering nightly reindex")
        # This would be implemented to reindex all documents
        pass
    
    async def trigger_weekly_optimization(self) -> None:
        """Trigger weekly optimization."""
        logger.info("Triggering weekly optimization")
        # This would be implemented to optimize indexes
        pass
    
    async def scan_missing_documents(self) -> None:
        """Scan for documents missing from index."""
        logger.info("Scanning for missing documents")
        # This would scan documents table and check if they're indexed
        pass


import asyncio


# Global scheduler instance
scheduler = IndexingScheduler()


def get_scheduler() -> IndexingScheduler:
    """Get global scheduler instance."""
    return scheduler