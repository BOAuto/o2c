from temporalio.client import Client

from app.core.config import settings


async def connect_temporal_client() -> Client:
    return await Client.connect(
        settings.TEMPORAL_ADDRESS, namespace=settings.TEMPORAL_NAMESPACE
    )
