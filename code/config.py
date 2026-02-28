"""
ZeroCorp Assessment - Shared Configuration
Central config so updates don't affect old modules.
Loads secrets from environment variables (see .env.example).
"""

import os
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CONNECTION_STRING = os.getenv("CONNECTION_STRING", "")
FACE_ENDPOINT = os.getenv("FACE_ENDPOINT", "")
FACE_API_KEY = os.getenv("FACE_API_KEY", "")


def utc_now():
    """UTC datetime for Azure systems + compliance deadlines."""
    return datetime.now(timezone.utc)


# Table schema: processing status (avoids races + retries)
SCHEMA_VERSION = 1
STATUS_EXIF_SAVED = "exif_saved"
STATUS_FACE_SCANNED = "face_scanned"
STATUS_ROUTED = "routed"
STATUS_PROCESSED = "processed"
STATUS_APPROVED_WRITTEN = "approved_written"
STATUS_QUARANTINED_WRITTEN = "quarantined_written"
STATUS_PII_DELETED = "pii_deleted"

# Routing state (fail-closed)
ROUTING_QUARANTINE = "quarantine"
ROUTING_ELIGIBLE = "eligible"
ROUTING_APPROVED = "approved"

SAMPLE_IMAGES_DIR = "sample_images"
TABLE_NAME = "imagemetadata"
PARTITION_KEY = "images"

# Blob Storage containers (face-based routing)
QUARANTINE_CONTAINER = "quarantine"
APPROVED_CONTAINER = "approved"

# Azure Face API (for face detection) - loaded from env above
