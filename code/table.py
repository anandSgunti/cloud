"""
Table utilities - schema-aligned with imagemetadata.
Uses UTC, fail-closed routing, status + schema_version.
"""

from azure.data.tables import TableServiceClient
from datetime import timedelta

from config import (
    CONNECTION_STRING,
    TABLE_NAME,
    PARTITION_KEY,
    utc_now,
    SCHEMA_VERSION,
    STATUS_FACE_SCANNED,
    ROUTING_QUARANTINE,
    ROUTING_ELIGIBLE,
)


def get_table_client():
    table_service = TableServiceClient.from_connection_string(CONNECTION_STRING)
    return table_service.get_table_client(TABLE_NAME)


def store_image_metadata(
    table_client,
    image_rk: str,
    gps_lat: float,
    gps_lon: float,
    ts_original: str,
    has_face: bool | None,
):
    """
    Store/upsert image metadata with fail-closed routing.
    has_face=True -> quarantine; has_face=False -> eligible; has_face=None -> quarantine.
    """
    now = utc_now()
    if has_face is True:
        routing = ROUTING_QUARANTINE
    elif has_face is False:
        routing = ROUTING_ELIGIBLE
    else:
        routing = ROUTING_QUARANTINE  # fail-closed

    entity = {
        "PartitionKey": PARTITION_KEY,
        "RowKey": image_rk,
        "gps_latitude": gps_lat,
        "gps_longitude": gps_lon,
        "timestamp_original": ts_original,
        "face_detection_timestamp": now,
        "routing_state": routing,
        "status": STATUS_FACE_SCANNED,
        "status_updated_at": now,
        "schema_version": SCHEMA_VERSION,
    }
    if has_face is not None:
        entity["has_human_face"] = has_face
    if has_face is True:
        entity["pii_delete_deadline"] = now + timedelta(hours=24)

    table_client.upsert_entity(entity)
    return entity


def get_image_metadata(table_client, image_id: str):
    return table_client.get_entity(
        partition_key=PARTITION_KEY,
        row_key=image_id,
    )
