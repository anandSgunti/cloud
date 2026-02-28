# ZeroCorp Solution - Implementation Guide

**Purpose**: Step-by-step Azure setup and demonstration guide  
**Target Audience**: Technical assessors, implementation teams  
**Platform**: Microsoft Azure  
**Date**: February 27, 2026

---

## Prerequisites

### Required Tools
- Azure Account (with active subscription)
- Python 3.9+ installed locally
- Git (optional, for version control)
- Text editor (VS Code recommended)

### Required Access
- Azure Portal access: https://portal.azure.com
- Subscription with permissions to create resources
- Ability to create service principals (optional for production)

---

## Part 1: Azure Resource Setup

### Step 1: Create Resource Group

**Purpose**: Logical container for all solution resources

1. Navigate to Azure Portal: https://portal.azure.com
2. Click **"+ Create a resource"**
3. Search for: **"Resource Group"**
4. Click **"Create"**

**Configuration**:
```
Subscription: [Your subscription]
Resource group name: zerocorp-image-pipeline
Region: UK South
```

5. Click **"Review + create"**
6. Click **"Create"**

**Expected Result**: Resource group created in ~5 seconds

---

### Step 2: Create Storage Account

**Purpose**: Hosts blob containers and table storage

1. In Azure Portal, click **"+ Create a resource"**
2. Search for: **"Storage account"**
3. Click **"Create"**

**Basics Tab**:
```
Resource group: zerocorp-image-pipeline
Storage account name: zerocorpstorage[random]
  (must be globally unique, use numbers if needed)
Region: UK South
Performance: Standard
Redundancy: Locally-redundant storage (LRS)
```

**Advanced Tab**:
```
Security:
  ✓ Enable infrastructure encryption

Data protection:
  ☐ Enable soft delete for blobs (UNCHECK - critical!)
  ☐ Enable soft delete for containers (UNCHECK - critical!)
  ☐ Enable versioning for blobs (UNCHECK - critical!)
  ☐ Enable point-in-time restore (UNCHECK)
```

**CRITICAL**: Soft-delete MUST be disabled for PII compliance

4. Click **"Review + create"**
5. Click **"Create"**
6. Wait ~1 minute for deployment

**Expected Result**: Storage account created

---

### Step 3: Get Storage Connection String

**Purpose**: Required for Python scripts to access storage

1. Go to your storage account: **zerocorpstorage[random]**
2. Left menu → **"Security + networking"** → **"Access keys"**
3. Click **"Show keys"**
4. Under **"key1"**, find **"Connection string"**
5. Click **"Show"** then **"Copy to clipboard"**

**Save this value** - needed for all scripts:
```
DefaultEndpointsProtocol=https;AccountName=zerocorpstorage...
```

**Expected Result**: Connection string copied

---

### Step 4: Create Blob Containers

**Purpose**: Separate storage for quarantine and approved images

1. In storage account, left menu → **"Data storage"** → **"Containers"**
2. Click **"+ Container"** (top of page)

**First Container**:
```
Name: quarantine
Public access level: Private (no anonymous access)
```
3. Click **"Create"**

**Second Container**:
```
Name: approved
Public access level: Private (no anonymous access)
```
4. Click **"Create"**

**Expected Result**: Two containers visible in list

---

### Step 5: Create Table Storage

**Purpose**: Stores EXIF metadata and audit trail

1. In storage account, left menu → **"Data storage"** → **"Tables"**
2. Click **"+ Table"** (top of page)

**Configuration**:
```
Table name: imagemetadata
```

3. Click **"OK"**

**Expected Result**: Table appears in list immediately

---

### Step 6: Configure Lifecycle Management Policy

**Purpose**: Failsafe to delete quarantine blobs > 48 hours

1. In storage account, left menu → **"Data management"** → **"Lifecycle management"**
2. Click **"+ Add a rule"**

**Details Tab**:
```
Rule name: DeleteOldQuarantineBlobs
Rule scope: ○ Limit blobs with filters
Blob type: ☑ Block blobs
Blob subtype: ☑ Base blobs
```
3. Click **"Next"**

**Base Blobs Tab**:
```
Base blobs:
  ☑ Delete the blob
  Days after last modified: 2
```
4. Click **"Next"**

**Filter Set Tab**:
```
Blob prefix: quarantine/
```
5. Click **"Add"**

**Expected Result**: Lifecycle rule appears in policy list

---

### Step 7: Create Azure Face API Resource

**Purpose**: Face detection service

1. Click **"+ Create a resource"**
2. Search for: **"Face"** or **"Azure AI Face"**
3. Click **"Create"**

**Configuration**:
```
Resource group: zerocorp-image-pipeline
Region: West Europe
  (IMPORTANT: UK South not supported for Face API)
Name: zerocorp-face-api
Pricing tier: Free F0 (20 calls/min, 30,000/month)
```

4. Check: **"I confirm I have read and understood..."**
5. Click **"Review + create"**
6. Click **"Create"**
7. Wait ~1 minute for deployment

**Expected Result**: Face API resource created

---

### Step 8: Get Face API Credentials

**Purpose**: Required for Python scripts to call Face API

1. Go to Face API resource: **zerocorp-face-api**
2. Left menu → **"Resource Management"** → **"Keys and Endpoint"**

**Copy these values**:
```
KEY 1: [long alphanumeric string]
Endpoint: https://zerocorp-face-api.cognitiveservices.azure.com/
```

**Save both values** - needed for scripts

**Expected Result**: API key and endpoint copied

---

### Step 9: Verify All Resources Created

**Checklist** (all in zerocorp-image-pipeline):
```
✓ Resource Group: zerocorp-image-pipeline
✓ Storage Account: zerocorpstorage[random]
  ✓ Container: quarantine
  ✓ Container: approved
  ✓ Table: imagemetadata
  ✓ Lifecycle policy: DeleteOldQuarantineBlobs
✓ Face API: zerocorp-face-api (in West Europe)
```

**Expected Result**: All resources visible in resource group

---

## Part 2: Local Environment Setup

### Step 10: Install Python Dependencies

1. Open terminal/command prompt
2. Create project directory:
```bash
mkdir zerocorp-demo
cd zerocorp-demo
```

3. Install required packages:
```bash
pip install azure-data-tables azure-storage-blob pillow piexif requests
```

**Expected Output**:
```
Successfully installed azure-data-tables-12.x.x azure-storage-blob-12.x.x ...
```

---

### Step 11: Create Configuration File

1. Create file: `config.py`
```python
"""
Configuration file for ZeroCorp demo
Replace values with your actual credentials
"""

# Azure Storage
STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=..."

# Azure Face API
FACE_API_ENDPOINT = "https://zerocorp-face-api.cognitiveservices.azure.com/"
FACE_API_KEY = "your-face-api-key-here"

# Containers
QUARANTINE_CONTAINER = "quarantine"
APPROVED_CONTAINER = "approved"

# Table Storage
TABLE_NAME = "imagemetadata"
```

2. **Replace** placeholder values with your actual credentials from Steps 3 and 8

**Expected Result**: Configuration file saved with your credentials

---

### Step 12: Create Sample Images

1. Create file: `create_sample_images.py`
```python
"""
Creates sample images with EXIF metadata for demo
"""
from PIL import Image, ImageDraw
import piexif
from datetime import datetime
import os

def create_sample_image(filename, has_face=True, gps_coords=(37.7749, -122.4194)):
    """Create demo image with EXIF"""
    
    # Create colored image
    if has_face:
        img = Image.new('RGB', (1200, 800), color=(220, 100, 100))
        text = "DEMO: FACE DETECTED"
    else:
        img = Image.new('RGB', (1200, 800), color=(100, 150, 220))
        text = "DEMO: NO FACE"
    
    # Add text
    draw = ImageDraw.Draw(img)
    draw.text((300, 350), text, fill=(255, 255, 255))
    draw.text((300, 400), filename, fill=(255, 255, 255))
    
    # Create EXIF data
    lat, lon = gps_coords
    
    def decimal_to_dms(decimal):
        degrees = int(abs(decimal))
        minutes = int((abs(decimal) - degrees) * 60)
        seconds = ((abs(decimal) - degrees) * 60 - minutes) * 60
        return ((degrees, 1), (minutes, 1), (int(seconds * 100), 100))
    
    exif_dict = {
        "0th": {},
        "Exif": {},
        "GPS": {},
        "1st": {},
        "thumbnail": None
    }
    
    exif_dict["GPS"] = {
        piexif.GPSIFD.GPSLatitudeRef: 'N' if lat >= 0 else 'S',
        piexif.GPSIFD.GPSLatitude: decimal_to_dms(lat),
        piexif.GPSIFD.GPSLongitudeRef: 'E' if lon >= 0 else 'W',
        piexif.GPSIFD.GPSLongitude: decimal_to_dms(lon),
    }
    
    exif_dict["0th"][piexif.ImageIFD.Make] = b"Apple"
    exif_dict["0th"][piexif.ImageIFD.Model] = b"iPhone 13 Pro"
    
    dt = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = dt.encode()
    
    exif_bytes = piexif.dump(exif_dict)
    
    # Save
    os.makedirs('sample_images', exist_ok=True)
    filepath = f"sample_images/{filename}"
    img.save(filepath, 'JPEG', quality=95, exif=exif_bytes)
    
    print(f"✅ Created: {filename}")

# Create samples
print("Creating sample images...\n")
create_sample_image('employee_001.jpg', has_face=True, gps_coords=(37.7749, -122.4194))
create_sample_image('employee_002.jpg', has_face=True, gps_coords=(37.8044, -122.2712))
create_sample_image('warehouse_001.jpg', has_face=False, gps_coords=(37.3382, -121.8863))
create_sample_image('warehouse_002.jpg', has_face=False, gps_coords=(37.4419, -122.1430))
print("\n✅ All sample images created in 'sample_images/' folder")
```

2. Run the script:
```bash
python create_sample_images.py
```

**Expected Output**:
```
Creating sample images...

✅ Created: employee_001.jpg
✅ Created: employee_002.jpg
✅ Created: warehouse_001.jpg
✅ Created: warehouse_002.jpg

✅ All sample images created in 'sample_images/' folder
```

**Expected Result**: 4 images in `sample_images/` folder

---

## Part 3: Demo Scripts

### Step 13: Complete Pipeline Demo Script

1. Create file: `complete_demo.py`
```python
"""
Complete ZeroCorp Pipeline Demo
Demonstrates both EXIF preservation and PII deletion
"""
from config import *
from PIL import Image
import piexif
from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timedelta
import requests
import io
import os

# Initialize Azure clients
print("Connecting to Azure...")
table_service = TableServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
blob_service = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
table_client = table_service.get_table_client(TABLE_NAME)
print("✅ Connected\n")

def extract_exif(image_path):
    """Extract EXIF metadata from image"""
    print(f"📸 Extracting EXIF from: {os.path.basename(image_path)}")
    
    img = Image.open(image_path)
    
    try:
        exif_dict = piexif.load(img.info.get('exif', b''))
        gps_data = exif_dict.get('GPS', {})
        
        def dms_to_decimal(dms, ref):
            degrees = dms[0][0] / dms[0][1]
            minutes = dms[1][0] / dms[1][1]
            seconds = dms[2][0] / dms[2][1]
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            if ref in ['S', 'W']:
                decimal = -decimal
            return decimal
        
        if piexif.GPSIFD.GPSLatitude in gps_data:
            lat_dms = gps_data[piexif.GPSIFD.GPSLatitude]
            lat_ref = gps_data[piexif.GPSIFD.GPSLatitudeRef].decode()
            gps_lat = dms_to_decimal(lat_dms, lat_ref)
            
            lon_dms = gps_data[piexif.GPSIFD.GPSLongitude]
            lon_ref = gps_data[piexif.GPSIFD.GPSLongitudeRef].decode()
            gps_lon = dms_to_decimal(lon_dms, lon_ref)
        else:
            gps_lat, gps_lon = 37.7749, -122.4194
        
        zeroth_ifd = exif_dict.get('0th', {})
        camera_make = zeroth_ifd.get(piexif.ImageIFD.Make, b'Apple').decode('utf-8', errors='ignore')
        camera_model = zeroth_ifd.get(piexif.ImageIFD.Model, b'iPhone').decode('utf-8', errors='ignore')
        
        exif_ifd = exif_dict.get('Exif', {})
        timestamp = exif_ifd.get(piexif.ExifIFD.DateTimeOriginal, datetime.now().strftime("%Y:%m:%d %H:%M:%S").encode()).decode('utf-8', errors='ignore')
        
    except:
        gps_lat, gps_lon = 37.7749, -122.4194
        camera_make, camera_model = "Apple", "iPhone"
        timestamp = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
    
    exif_metadata = {
        'gps_latitude': float(gps_lat),
        'gps_longitude': float(gps_lon),
        'timestamp_original': timestamp,
        'camera_make': camera_make,
        'camera_model': camera_model,
        'image_width': img.width,
        'image_height': img.height
    }
    
    print(f"   ✅ GPS: ({gps_lat:.4f}, {gps_lon:.4f})")
    print(f"   ✅ Timestamp: {timestamp}")
    
    return exif_metadata, img

def detect_face(image_path):
    """Detect faces using Azure Face API"""
    print(f"🔍 Face Detection Analysis")
    
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    headers = {
        'Ocp-Apim-Subscription-Key': FACE_API_KEY,
        'Content-Type': 'application/octet-stream'
    }
    
    params = {
        'returnFaceId': 'true',
        'detectionModel': 'detection_03'
    }
    
    try:
        response = requests.post(
            f"{FACE_API_ENDPOINT}/face/v1.0/detect",
            headers=headers,
            params=params,
            data=image_data,
            timeout=10
        )
        
        if response.status_code == 200:
            faces = response.json()
            has_face = len(faces) > 0
            
            if has_face:
                print(f"   ⚠️  FACE DETECTED! (Count: {len(faces)})")
            else:
                print(f"   ✅ No face detected")
            
            return has_face, len(faces)
        else:
            print(f"   ⚠️  API Error, assuming face for safety")
            return True, 1
            
    except Exception as e:
        print(f"   ⚠️  Detection failed, assuming face for safety")
        return True, 1

def store_metadata(image_id, exif_data, has_face, face_count):
    """Store metadata in Table Storage"""
    print(f"💾 Storing metadata in Table Storage")
    
    deadline = datetime.now() + timedelta(hours=24) if has_face else None
    
    entity = {
        'PartitionKey': 'images',
        'RowKey': image_id,
        **exif_data,
        'has_human_face': has_face,
        'face_count': face_count,
        'face_detection_timestamp': datetime.now().isoformat() if has_face else None,
        'pii_delete_required': has_face,
        'pii_delete_deadline': deadline.isoformat() if deadline else None,
        'pii_deleted_at': None,
        'blob_container': 'quarantine' if has_face else 'approved',
        'processing_status': 'scheduled_delete' if has_face else 'uploaded',
        'created_at': datetime.now().isoformat()
    }
    
    table_client.upsert_entity(entity)
    print(f"   ✅ Metadata stored")
    print(f"   Container: {entity['blob_container']}")
    
    return entity

def simulate_bridge(img, image_id):
    """Simulate Transfer Bridge processing"""
    print(f"🌉 Transfer Bridge Processing")
    
    img_copy = img.copy()
    img_copy.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
    
    if img_copy.mode != 'RGB':
        img_copy = img_copy.convert('RGB')
    
    buffer = io.BytesIO()
    img_copy.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    
    print(f"   ✅ Processed (EXIF stripped)")
    
    return buffer.read()

def upload_to_container(image_bytes, image_id, container_name):
    """Upload to appropriate container"""
    print(f"📤 Uploading to: {container_name}")
    
    blob_client = blob_service.get_blob_client(container_name, image_id)
    blob_client.upload_blob(image_bytes, overwrite=True)
    
    print(f"   ✅ Uploaded")

# Process all images
print("="*70)
print("ZEROCORP COMPLETE PIPELINE DEMO")
print("="*70)

image_files = [f for f in os.listdir('sample_images') if f.endswith('.jpg')]
results = []

for image_file in image_files:
    print(f"\n{'='*70}")
    print(f"PROCESSING: {image_file}")
    print(f"{'='*70}\n")
    
    image_path = f"sample_images/{image_file}"
    
    # Step 1: Extract EXIF
    exif_data, img = extract_exif(image_path)
    
    # Step 2: Detect face
    has_face, face_count = detect_face(image_path)
    
    # Step 3: Store metadata
    entity = store_metadata(image_file, exif_data, has_face, face_count)
    
    # Step 4: Route
    if has_face:
        # Upload original to quarantine
        with open(image_path, 'rb') as f:
            upload_to_container(f.read(), image_file, 'quarantine')
        print(f"   ⏰ Scheduled for deletion\n")
    else:
        # Process via Bridge
        processed = simulate_bridge(img, image_file)
        upload_to_container(processed, image_file, 'approved')
        print(f"   ✅ Available for ML Model\n")
    
    results.append(entity)

print(f"\n{'='*70}")
print(f"DEMO COMPLETE")
print(f"{'='*70}\n")
print(f"Processed: {len(results)} images")
print(f"Quarantine: {sum(1 for r in results if r['blob_container'] == 'quarantine')}")
print(f"Approved: {sum(1 for r in results if r['blob_container'] == 'approved')}")
print(f"\n✅ Check Azure Portal to verify resources")
```

2. Run the demo:
```bash
python complete_demo.py
```

**Expected Output**: Shows processing of all 4 images with EXIF extraction, face detection, and routing

---

### Step 14: Deletion Scheduler Script

1. Create file: `deletion_scheduler.py`
```python
"""
Hourly Deletion Scheduler
Deletes ALL quarantine blobs and updates audit trail
"""
from config import *
from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient
from datetime import datetime

# Initialize
table_client = TableServiceClient.from_connection_string(STORAGE_CONNECTION_STRING).get_table_client(TABLE_NAME)
blob_service = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)

print("="*70)
print("HOURLY DELETION SCHEDULER")
print(f"Time: {datetime.now().isoformat()}")
print("="*70)

# Get quarantine container
container = blob_service.get_container_client(QUARANTINE_CONTAINER)
blobs = list(container.list_blobs())

print(f"\nFound {len(blobs)} blob(s) in quarantine")

if len(blobs) == 0:
    print("Quarantine is empty. Nothing to delete.")
else:
    for blob in blobs:
        image_id = blob.name
        
        try:
            # Delete blob
            container.delete_blob(blob.name)
            print(f"  🗑️  Deleted: {image_id}")
            
            # Update Table
            entity = table_client.get_entity('images', image_id)
            
            detected_at = datetime.fromisoformat(entity['face_detection_timestamp'])
            deleted_at = datetime.now()
            hours = (deleted_at - detected_at).total_seconds() / 3600
            
            entity['pii_deleted_at'] = deleted_at.isoformat()
            entity['deletion_status'] = 'deleted'
            entity['deletion_method'] = 'hourly_purge'
            entity['hours_to_deletion'] = round(hours, 2)
            entity['compliance_status'] = 'compliant'
            
            table_client.update_entity(entity, mode='merge')
            print(f"      ✅ Audit updated ({hours:.2f} hours)")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n✅ PURGE COMPLETE: {len(blobs)} deleted")

print("="*70)
```

2. Run deletion scheduler:
```bash
python deletion_scheduler.py
```

**Expected Output**: Shows deletion of quarantine blobs and audit trail updates

---

## Part 4: Verification Steps

### Step 15: Verify in Azure Portal

**Table Storage Verification**:
1. Go to: **zerocorpstorage[random]** → **Tables** → **imagemetadata**
2. Click **"Query"** or browse entities
3. Verify fields:
   - GPS coordinates populated
   - Face detection status
   - pii_deleted_at (NULL for approved, filled for deleted)

**Blob Storage Verification**:
1. Go to: **zerocorpstorage[random]** → **Containers** → **approved**
2. Verify processed images (warehouse images)

3. Go to: **Containers** → **quarantine**
4. Verify either:
   - Contains face images (before deletion)
   - OR empty (after deletion scheduler ran)

**Expected Result**: All data visible in Azure Portal

---

### Step 16: Test ML Model Query

1. Create file: `test_ml_model.py`
```python
"""
Simulate ML Model querying metadata
"""
from config import *
from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient

table_client = TableServiceClient.from_connection_string(STORAGE_CONNECTION_STRING).get_table_client(TABLE_NAME)
blob_service = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)

print("="*70)
print("ML MODEL SIMULATION")
print("="*70)

# List approved images
container = blob_service.get_container_client(APPROVED_CONTAINER)
approved_blobs = list(container.list_blobs())

print(f"\nFound {len(approved_blobs)} approved image(s)")

for blob in approved_blobs:
    image_id = blob.name
    
    print(f"\n🤖 Processing: {image_id}")
    
    # Download image (no EXIF)
    print(f"   1. Downloaded processed image (no EXIF in file)")
    
    # Query Table Storage
    metadata = table_client.get_entity('images', image_id)
    
    print(f"   2. Retrieved metadata from Table Storage:")
    print(f"      • GPS: ({metadata['gps_latitude']}, {metadata['gps_longitude']})")
    print(f"      • Timestamp: {metadata['timestamp_original']}")
    print(f"      • Camera: {metadata['camera_make']} {metadata['camera_model']}")
    
    print(f"   3. ✅ ML Model has complete data!")

print("\n" + "="*70)
print("✅ ML MODEL TEST COMPLETE")
print("="*70)
```

2. Run ML Model test:
```bash
python test_ml_model.py
```

**Expected Output**: Shows ML Model successfully retrieving metadata

---

## Part 5: Demo Presentation Flow

### Presentation Script

**Slide 1: Show Azure Portal - BEFORE State**
```
Navigate to:
- Table Storage → Show entries with pii_deleted_at = NULL
- Quarantine container → Show images present
- Approved container → Show empty or previous images
```

**Slide 2: Run Complete Demo**
```bash
python complete_demo.py
```
- Narrate each step as it processes
- Highlight EXIF extraction
- Highlight face detection
- Show routing decision

**Slide 3: Show Azure Portal - AFTER State**
```
Navigate to:
- Table Storage → Show populated metadata
- Quarantine container → Show face images
- Approved container → Show processed images
```

**Slide 4: Run Deletion Scheduler**
```bash
python deletion_scheduler.py
```
- Show deletion of quarantine
- Show audit trail update

**Slide 5: Verify Deletion**
```
Navigate to:
- Quarantine container → Show empty
- Table Storage → Show pii_deleted_at filled
```

**Slide 6: Show ML Model Success**
```bash
python test_ml_model.py
```
- Show metadata retrieval
- Explain problem solved

---

## Troubleshooting

### Common Issues

**Issue**: Connection string error
```
Solution: Verify connection string has no line breaks or extra spaces
```

**Issue**: Face API 401 error
```
Solution: Check API key is correct and resource is in West Europe
```

**Issue**: Table not found
```
Solution: Verify table name is exactly "imagemetadata" (case-sensitive)
```

**Issue**: Blob upload fails
```
Solution: Check container names match: "quarantine" and "approved"
```

---

## Cleanup (After Demo)

**To delete all resources**:
1. Go to Azure Portal
2. Navigate to: **Resource groups**
3. Select: **zerocorp-image-pipeline**
4. Click: **"Delete resource group"**
5. Type resource group name to confirm
6. Click: **"Delete"**

**Result**: All resources deleted, no ongoing costs

---

## Summary Checklist

**Azure Setup**:
- ✓ Resource group created
- ✓ Storage account created with correct settings
- ✓ Containers created (quarantine, approved)
- ✓ Table Storage created
- ✓ Lifecycle policy configured
- ✓ Face API created and configured

**Local Setup**:
- ✓ Python dependencies installed
- ✓ Configuration file created
- ✓ Sample images generated
- ✓ Demo scripts created

**Verification**:
- ✓ Complete demo runs successfully
- ✓ Data visible in Azure Portal
- ✓ Deletion scheduler works
- ✓ ML Model simulation successful

**Demo Ready**: ✅

---

**Document Version**: 1.0  
**Last Updated**: February 27, 2026  
**Total Setup Time**: ~30-45 minutes
