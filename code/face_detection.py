"""
Face Detection Module
Input: image (path, PIL Image, or bytes)
Output: bool | None — True=face, False=no face, None=unknown (fail-closed → quarantine)
Updates Azure Table with routing_state (quarantine|eligible), status, UTC timestamps.
Uses azure-ai-vision-face SDK.
"""

import io
from datetime import timedelta
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.ai.vision.face import FaceClient
from azure.ai.vision.face.models import (
    FaceDetectionModel,
    FaceRecognitionModel,
)

from config import (
    FACE_ENDPOINT,
    FACE_API_KEY,
    PARTITION_KEY,
    utc_now,
    SCHEMA_VERSION,
    STATUS_FACE_SCANNED,
    ROUTING_QUARANTINE,
    ROUTING_ELIGIBLE,
)


def _image_to_bytes(image) -> bytes:
    """Convert image (path, PIL Image, or bytes) to bytes."""
    if isinstance(image, bytes):
        return image
    if isinstance(image, str):
        with open(image, "rb") as f:
            return f.read()
    if hasattr(image, "save"):
        # PIL Image
        buf = io.BytesIO()
        img = image
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return buf.getvalue()
    raise TypeError("image must be path (str), PIL Image, or bytes")


def detect_face(image) -> Optional[bool]:
    """
    Detect if image contains a human face.
    Uses azure-ai-vision-face SDK.

    Returns:
        True if face detected, False if no face, None if unknown (fail-closed → quarantine)
    """
    file_content = _image_to_bytes(image)
    try:
        credential = AzureKeyCredential(FACE_API_KEY)
        with FaceClient(endpoint=FACE_ENDPOINT.rstrip("/"), credential=credential) as face_client:
            faces = face_client.detect(
                file_content,
                detection_model=FaceDetectionModel.DETECTION03,
                recognition_model=FaceRecognitionModel.RECOGNITION04,
                return_face_id=False,
            )
        return len(faces) > 0
    except Exception:
        return None  # unknown → fail-closed → quarantine


def update_table_with_face_result(table_client, image_id: str, has_face: Optional[bool]):
    """
    Update Azure Table with face result. Fail-closed:
    - has_face=True → quarantine
    - has_face=False → eligible (approved only after Bridge+ML success)
    - has_face=None/unknown → quarantine
    """
    now = utc_now()

    if has_face is True:
        routing_state = ROUTING_QUARANTINE
    elif has_face is False:
        routing_state = ROUTING_ELIGIBLE
    else:
        routing_state = ROUTING_QUARANTINE  # fail-closed

    entity = {
        "PartitionKey": PARTITION_KEY,
        "RowKey": image_id,
        "face_detection_timestamp": now,
        "routing_state": routing_state,
        "status": STATUS_FACE_SCANNED,
        "status_updated_at": now,
        "schema_version": SCHEMA_VERSION,
    }
    if has_face is not None:
        entity["has_human_face"] = has_face
    if has_face is True:
        entity["pii_delete_deadline"] = now + timedelta(hours=24)
    table_client.upsert_entity(entity)


def detect_and_update(table_client, image, image_id: str) -> Optional[bool]:
    """
    Detect face in image and update Azure Table.
    Returns: True=face, False=no face, None=unknown (fail-closed).
    """
    has_face = detect_face(image)
    update_table_with_face_result(table_client, image_id, has_face)
    return has_face
