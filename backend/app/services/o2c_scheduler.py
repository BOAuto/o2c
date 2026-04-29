"""Start and signal the O2C Temporal ingestion scheduler."""

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from app.core.config import settings
from app.temporal.client import connect_temporal_client
from app.temporal.workflows.o2c_ingestion import O2CIngestionSchedulerWorkflow


async def ensure_o2c_scheduler_started(client: Client, *, period_minutes: int) -> None:
    try:
        await client.start_workflow(
            O2CIngestionSchedulerWorkflow.run,
            args=[max(1, period_minutes)],
            id=settings.TEMPORAL_O2C_SCHEDULER_WORKFLOW_ID,
            task_queue=settings.TEMPORAL_TASK_QUEUE,
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
        )
    except WorkflowAlreadyStartedError:
        pass


async def signal_o2c_poll_now() -> None:
    client = await connect_temporal_client()
    handle = client.get_workflow_handle(settings.TEMPORAL_O2C_SCHEDULER_WORKFLOW_ID)
    await handle.signal(O2CIngestionSchedulerWorkflow.poll_now_requested)


async def signal_o2c_retrieval_period_minutes(minutes: int) -> None:
    client = await connect_temporal_client()
    handle = client.get_workflow_handle(settings.TEMPORAL_O2C_SCHEDULER_WORKFLOW_ID)
    await handle.signal(
        O2CIngestionSchedulerWorkflow.retrieval_period_updated,
        max(1, int(minutes)),
    )


async def ensure_and_sync_o2c_scheduler(period_minutes: int) -> None:
    client = await connect_temporal_client()
    await ensure_o2c_scheduler_started(client, period_minutes=period_minutes)
    await signal_o2c_retrieval_period_minutes(period_minutes)
