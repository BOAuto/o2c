import asyncio
import concurrent.futures
import logging

from temporalio.worker import Worker

from app.core.config import settings
from app.temporal.activities import ingestion_activities as ingestion_activities_module
from app.temporal.client import connect_temporal_client
from app.temporal.workflows.o2c_ingestion import (
    O2CIngestionSchedulerWorkflow,
    O2CMessageIngestionWorkflow,
)

logger = logging.getLogger(__name__)

_INGESTION_ACTIVITIES = [
    ingestion_activities_module.load_scheduler_config_activity,
    ingestion_activities_module.poll_central_unread_activity,
    ingestion_activities_module.ensure_mailbox_pool_activity,
    ingestion_activities_module.classify_central_sender_activity,
    ingestion_activities_module.record_rejected_central_sender_activity,
    ingestion_activities_module.record_internal_unmapped_sender_activity,
    ingestion_activities_module.save_order_user_anchor_activity,
    ingestion_activities_module.save_order_user_html_eml_from_hop_activity,
    ingestion_activities_module.resolve_in_reply_to_hop_activity,
    ingestion_activities_module.classify_hop_sender_activity,
    ingestion_activities_module.persist_external_correspondent_activity,
    ingestion_activities_module.save_po_html_if_needed_activity,
    ingestion_activities_module.finalize_ingestion_activity,
    ingestion_activities_module.mark_central_message_seen_activity,
]


async def run_worker() -> None:
    client = await connect_temporal_client()
    workflows: list[object] = [
        O2CIngestionSchedulerWorkflow,
        O2CMessageIngestionWorkflow,
    ]
    activities: list[object] = list(_INGESTION_ACTIVITIES)
    if not workflows and not activities:
        logger.warning(
            "Temporal worker started with no registered workflows or activities; idling until implementations are added",
            extra={
                "namespace": settings.TEMPORAL_NAMESPACE,
                "task_queue": settings.TEMPORAL_TASK_QUEUE,
            },
        )
        await asyncio.Event().wait()
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as activity_executor:
        worker = Worker(
            client,
            task_queue=settings.TEMPORAL_TASK_QUEUE,
            workflows=workflows,
            activities=activities,
            activity_executor=activity_executor,
            max_cached_workflows=settings.TEMPORAL_WORKER_MAX_CACHED_WORKFLOWS,
        )
        logger.info(
            "Temporal worker started",
            extra={
                "namespace": settings.TEMPORAL_NAMESPACE,
                "task_queue": settings.TEMPORAL_TASK_QUEUE,
                "max_cached_workflows": settings.TEMPORAL_WORKER_MAX_CACHED_WORKFLOWS,
            },
        )
        await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
