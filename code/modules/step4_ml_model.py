"""
Steps 4, 5, 6: ML Model receives image, queries Table, processes successfully
Shows: Image has no metadata -> Gets GPS/timestamp from Table -> Has all required metadata
"""

import io
import piexif # to check if the image has EXIF
from PIL import Image

from config import TABLE_NAME, PARTITION_KEY


def get_metadata_from_table(table_client, image_id):
    """Query Table Storage for metadata by image_id (filename)."""
    return table_client.get_entity(
        partition_key=PARTITION_KEY,
        row_key=image_id
    )


def ml_model_process(table_client, image_id, image_bytes):
    """
    Simulate ML Model processing:
    1. Receives image (no EXIF)
    2. Queries Table Storage for metadata
    3. Gets GPS and timestamp
    Returns: (success: bool, metadata or None)
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Step 4: Check image - no EXIF
    try:
        exif_dict = piexif.load(img.info.get('exif', b''))
        has_exif = bool(exif_dict.get('GPS'))
    except Exception:
        has_exif = False

    # Step 5: Query Table Storage
    try:
        entity = get_metadata_from_table(table_client, image_id)

        # Step 6: Success - has all required metadata
        return True, dict(entity)
    except Exception as e:
        return False, None


def run_and_display(table_client, image_id, image_bytes):
    """Run ML model flow and display each step (for Step 4-6 output)."""
    img = Image.open(io.BytesIO(image_bytes))

    # Step 4
    print(f"\n   [Show: Image has no metadata]")
    try:
        exif_dict = piexif.load(img.info.get('exif', b''))
        if exif_dict.get('GPS'):
            print(f"      EXIF found in image")
        else:
            print(f"      No EXIF in image")
    except Exception:
        print(f"      No EXIF in image")

    # Step 5
    print(f"\n   [Show: Gets GPS, timestamp from Table]")
    try:
        entity = get_metadata_from_table(table_client, image_id)
        print(f"      GPS: ({entity['gps_latitude']}, {entity['gps_longitude']})")
        print(f"      Timestamp: {entity['timestamp_original']}")
        print(f"      Camera: {entity['camera_make']} {entity['camera_model']}")
    except Exception as e:
        print(f"      Failed: {e}")
        return False, None

    # Step 6
    print(f"\n   [Show: Has all required metadata]")
    print(f"      ML Model can process successfully")
    return True, dict(entity)
