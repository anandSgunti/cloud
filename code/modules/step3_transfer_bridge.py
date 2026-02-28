"""
Step 3: Transfer Bridge processes the image
Shows: EXIF gets stripped - the bug occurs
"""

import io
from PIL import Image


def simulate_transfer_bridge(img, image_id):
    """
    Simulate what Transfer Bridge does:
    - Resizes image
    - Converts to RGB
    - Compresses
    - STRIPS EXIF (the bug)
    Returns: bytes (image with no EXIF)
    """
    img_copy = img.copy()
    img_copy.thumbnail((1920, 1080), Image.Resampling.LANCZOS)

    if img_copy.mode != 'RGB':
        img_copy = img_copy.convert('RGB')

    # Save without EXIF - THIS IS THE BUG
    buffer = io.BytesIO()
    img_copy.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    return buffer.getvalue()


def run_and_display(img, image_id):
    """Run bridge and display that EXIF was stripped (for Step 3 output)."""
    processed_bytes = simulate_transfer_bridge(img, image_id)
    print(f"\n   [Show: EXIF gets stripped - the bug occurs]")
    print(f"      Resized, converted to RGB, compressed")
    print(f"      No exif parameter in save() = EXIF stripped")
    print(f"      Output: {len(processed_bytes)} bytes (no metadata)")
    return processed_bytes
