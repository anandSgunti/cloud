"""
ZeroCorp Assessment - Modular Pipeline
Orchestrates the 6-step flow to prove the Transfer Bridge bug is solved.
"""

import io
import os
from config import SAMPLE_IMAGES_DIR
from modules.step1_extract_exif import run_and_display as step1_display
from modules.step2_save_to_table import get_table_client, run_and_display as step2_display
from modules.step3_transfer_bridge import run_and_display as step3_display
from modules.step4_ml_model import run_and_display as step4_display
from face_detection import detect_and_update
from modules.blob_router import route_to_container


def main():
    print("=" * 70)
    print("ZeroCorp Assessment - Modular Bug Solution Pipeline")
    print("=" * 70)
    print("\nConnecting to Azure...")
    table_client = get_table_client()
    print("Connected!\n")

    # Discover images
    image_files = [
        f for f in os.listdir(SAMPLE_IMAGES_DIR)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]

    images_data = {}
    face_results = {}
    processed_images = {}
    ml_results = {}

    # --- Step 1: Extract EXIF ---
    print("=" * 70)
    print("Step 1: Extract EXIF from the original image")
    print("=" * 70)
    for image_file in image_files:
        image_path = os.path.join(SAMPLE_IMAGES_DIR, image_file)
        print(f"\nProcessing: {image_file}")
        img, metadata = step1_display(image_path)
        images_data[image_file] = {'img': img, 'metadata': metadata}
    print(f"\nStep 1 complete: {len(images_data)} images processed")

    # --- Step 2: Save EXIF to Table ---
    print("\n" + "=" * 70)
    print("Step 2: Save EXIF metadata to Azure Table Storage")
    print("=" * 70)
    for image_file, data in images_data.items():
        print(f"\nSaving: {image_file}")
        step2_display(table_client, data['metadata'])
    print(f"\nStep 2 complete: Table has EXIF metadata")

    # --- Step 3: Face detection + Step 4: Blob routing (only approved go to Bridge) ---
    print("\n" + "=" * 70)
    print("Step 3: Face detection (on original image)")
    print("Step 4: Blob routing - face->quarantine, no-face->approved path")
    print("=" * 70)
    for image_file, data in images_data.items():
        image_path = os.path.join(SAMPLE_IMAGES_DIR, image_file)
        print(f"\nProcessing: {image_file}")
        has_face = detect_and_update(table_client, image_path, image_file)
        face_results[image_file] = has_face
        face_label = "Yes" if has_face is True else "No" if has_face is False else "Unknown"
        print(f"   Face detected: {face_label} | Table updated")

        # Blob routing: face or unknown -> quarantine; no face -> approved path
        is_quarantine = has_face is not False  # True or None (fail-closed)
        if is_quarantine:
            buf = io.BytesIO()
            data["img"].save(buf, format="JPEG", quality=90)
            buf.seek(0)
            route_to_container(buf.getvalue(), image_file, has_face=True, table_client=table_client)
            print(f"   -> quarantine container (PII/unknown, will be deleted)")
        else:
            processed = step3_display(data["img"], image_file)
            processed_images[image_file] = processed
            success, metadata = step4_display(table_client, image_file, processed)
            ml_results[image_file] = {"success": success, "metadata": metadata}
            route_to_container(processed, image_file, has_face=False, table_client=table_client)
            print(f"   -> approved container (via Bridge + ML Model)")

    print(f"\nStep 3-4 complete: Face routing done; only no-face images went through Bridge + ML Model")

    # --- Summary ---
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    success_count = sum(1 for r in ml_results.values() if r['success'])
    print(f"\nTotal images: {len(ml_results)}")
    print(f"Successfully processed: {success_count}")
    print(f"Failed: {len(ml_results) - success_count}")
    print("\nBug solved: EXIF extracted before Bridge, stored in Table, ML Model queries Table.")


if __name__ == "__main__":
    main()
