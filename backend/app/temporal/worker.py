import asyncio
import logging

from temporalio.worker import Worker

from app.core.config import settings
from app.temporal.client import connect_temporal_client

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    client = await connect_temporal_client()
    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[],
        activities=[],
    )
    logger.info(
        "Temporal worker started (no workflows registered yet)",
        extra={
            "namespace": settings.TEMPORAL_NAMESPACE,
            "task_queue": settings.TEMPORAL_TASK_QUEUE,
        },
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
