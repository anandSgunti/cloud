"""
Step 2: Save metadata to Azure Table Storage
Shows: Table has all the metadata
"""

from azure.data.tables import TableServiceClient

from config import (
    CONNECTION_STRING,
    TABLE_NAME,
    PARTITION_KEY,
    utc_now,
    SCHEMA_VERSION,
    STATUS_EXIF_SAVED,
)


def get_table_client():
    """Get configured Table Storage client."""
    table_service = TableServiceClient.from_connection_string(CONNECTION_STRING)
    return table_service.get_table_client(TABLE_NAME)


def save_metadata(table_client, metadata):
    """
    Save metadata entity to Azure Table Storage.
    Links by image_id (filename) as RowKey.
    Uses UTC for timestamps; status + schema_version for versioning.
    """
    now = utc_now()
    entity = {
        "PartitionKey": PARTITION_KEY,
        "RowKey": metadata["image_id"],
        "gps_latitude": float(metadata["gps_latitude"]),
        "gps_longitude": float(metadata["gps_longitude"]),
        "timestamp_original": metadata["timestamp_original"],
        "camera_make": metadata["camera_make"],
        "camera_model": metadata["camera_model"],
        "image_width": metadata["image_width"],
        "image_height": metadata["image_height"],
        "created_at": now,
        "status": STATUS_EXIF_SAVED,
        "status_updated_at": now,
        "schema_version": SCHEMA_VERSION,
    }
    table_client.upsert_entity(entity)
    return entity


def run_and_display(table_client, metadata):
    """Save to table and display confirmation (for Step 2 output)."""
    save_metadata(table_client, metadata)
    print(f"\n   [Show: Table has all the metadata]")
    print(f"      RowKey: {metadata['image_id']}")
    print(f"      Saved: GPS, timestamp, camera info, dimensions")
