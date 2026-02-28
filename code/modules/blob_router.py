"""
Blob Router Module
Routes images to quarantine or approved container based on face detection.
Face detected = Yes -> quarantine (status=quarantined_written)
Face detected = No  -> approved (status=approved_written, approved_blob_uri set)
"""

from typing import Optional

from azure.storage.blob import BlobServiceClient

from config import (
    CONNECTION_STRING,
    QUARANTINE_CONTAINER,
    APPROVED_CONTAINER,
    PARTITION_KEY,
    ROUTING_APPROVED,
    utc_now,
    SCHEMA_VERSION,
    STATUS_QUARANTINED_WRITTEN,
    STATUS_APPROVED_WRITTEN,
)


def get_blob_service_client():
    """Get configured Blob Service client."""
    return BlobServiceClient.from_connection_string(CONNECTION_STRING)


def _ensure_container_exists(blob_service_client, container_name: str):
    """Create container if it does not exist."""
    container_client = blob_service_client.get_container_client(container_name)
    try:
        container_client.get_container_properties()
    except Exception:
        blob_service_client.create_container(container_name)


def route_to_container(
    image_bytes: bytes,
    image_id: str,
    has_face: bool,
    table_client=None,
) -> str:
    """
    Upload image to quarantine or approved container.
    If table_client provided, updates approved_blob_uri and status after successful upload.

    Returns:
        Container name where image was uploaded.
    """
    blob_service = get_blob_service_client()
    container_name = QUARANTINE_CONTAINER if has_face else APPROVED_CONTAINER

    _ensure_container_exists(blob_service, container_name)

    container_client = blob_service.get_container_client(container_name)
    blob_client = container_client.get_blob_client(image_id)
    blob_client.upload_blob(image_bytes, overwrite=True)

    now = utc_now()
    if table_client:
        if has_face:
            entity = {
                "PartitionKey": PARTITION_KEY,
                "RowKey": image_id,
                "status": STATUS_QUARANTINED_WRITTEN,
                "status_updated_at": now,
                "schema_version": SCHEMA_VERSION,
            }
        else:
            blob_uri = blob_client.url
            entity = {
                "PartitionKey": PARTITION_KEY,
                "RowKey": image_id,
                "approved_blob_uri": blob_uri,
                "routing_state": ROUTING_APPROVED,
                "status": STATUS_APPROVED_WRITTEN,
                "status_updated_at": now,
                "schema_version": SCHEMA_VERSION,
            }
        table_client.upsert_entity(entity)

    return container_name


def run(
    image_bytes: bytes,
    image_id: str,
    has_face: bool,
    table_client=None,
) -> str:
    """Route image to the appropriate container. Updates table if table_client provided."""
    return route_to_container(image_bytes, image_id, has_face, table_client)
