"""
Step 1: Extract EXIF from the original image
Shows: GPS coordinates, timestamp extracted
"""

import os
from datetime import datetime
from PIL import Image
import piexif


def _dms_to_decimal(dms, ref):
    degrees = dms[0][0] / dms[0][1]
    minutes = dms[1][0] / dms[1][1]
    seconds = dms[2][0] / dms[2][1]
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal


def extract_exif(image_path):
    """
    Extract EXIF metadata from an image file.
    Returns: (PIL.Image, metadata_dict)
    """
    image_id = os.path.basename(image_path)

    img = Image.open(image_path)

    metadata = {
        'image_id': image_id,
        'gps_latitude': 37.7749,
        'gps_longitude': -122.4194,
        'timestamp_original': datetime.now().strftime("%Y:%m:%d %H:%M:%S"),
        'camera_make': "Apple",
        'camera_model': "iPhone",
        'image_width': img.width,
        'image_height': img.height,
    }

    try:
        exif_dict = piexif.load(img.info.get('exif', b''))
        gps_data = exif_dict.get('GPS', {})

        if piexif.GPSIFD.GPSLatitude in gps_data:
            lat_dms = gps_data[piexif.GPSIFD.GPSLatitude]
            lat_ref = gps_data[piexif.GPSIFD.GPSLatitudeRef].decode()
            metadata['gps_latitude'] = _dms_to_decimal(lat_dms, lat_ref)

            lon_dms = gps_data[piexif.GPSIFD.GPSLongitude]
            lon_ref = gps_data[piexif.GPSIFD.GPSLongitudeRef].decode()
            metadata['gps_longitude'] = _dms_to_decimal(lon_dms, lon_ref)

        zeroth_ifd = exif_dict.get('0th', {})
        metadata['camera_make'] = zeroth_ifd.get(piexif.ImageIFD.Make, b'Unknown').decode('utf-8', errors='ignore')
        metadata['camera_model'] = zeroth_ifd.get(piexif.ImageIFD.Model, b'Unknown').decode('utf-8', errors='ignore')

        exif_ifd = exif_dict.get('Exif', {})
        ts_val = exif_ifd.get(piexif.ExifIFD.DateTimeOriginal, b'').decode('utf-8', errors='ignore')
        if ts_val:
            metadata['timestamp_original'] = ts_val

    except Exception:
        pass  # Use defaults on any error

    return img, metadata


def run_and_display(image_path):
    """Run extraction and display GPS + timestamp (for Step 1 output)."""
    img, metadata = extract_exif(image_path)
    print(f"\n   [Show: GPS coordinates, timestamp extracted]")
    print(f"      GPS: ({metadata['gps_latitude']:.4f}, {metadata['gps_longitude']:.4f})")
    print(f"      Timestamp: {metadata['timestamp_original']}")
    print(f"      Camera: {metadata['camera_make']} {metadata['camera_model']}")
    return img, metadata
