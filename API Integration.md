# API / Integration Notes

Implementation guide for the ZeroCorp solution. Shows endpoints, auth, and how to test.

---

## 1. Services Used

| Service | Purpose |
|---------|---------|
| **Azure Face API** | Face detection; returns faces or empty array |
| **Azure Blob Storage** | Store images in `quarantine` or `approved` containers |
| **Azure Table Storage** | Store metadata (EXIF, routing_state, status); table `imagemetadata` |

---

## 2. Auth Method

| Component | Current | Production Recommendation |
|-----------|---------|---------------------------|
| Face API | `AzureKeyCredential` (API key in config) | **Azure Key Vault** + managed identity; load key at runtime |
| Blob / Table | Connection string (account key) | **Managed identity** for App Service/Function; or Key Vault for connection string |
| Secrets | In `config.py` | **Never commit keys.** Use env vars or Key Vault references |

**Example: Key Vault in production**
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://my-vault.vault.azure.net/", credential=credential)
face_key = client.get_secret("face-api-key").value
```

---

## 3. Endpoints & How to Test

### 3.1 Face API — Detect

**Endpoint:** `POST https://<region>.api.cognitive.microsoft.com/face/v1.0/detect`

**Auth:** `Ocp-Apim-Subscription-Key: <YOUR_KEY>`

**cURL — image from file (binary):**
```bash
curl -X POST "https://eastus.api.cognitive.microsoft.com/face/v1.0/detect?detectionModel=detection_03&returnFaceId=false" \
  -H "Ocp-Apim-Subscription-Key: <YOUR_FACE_API_KEY>" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @sample_images/warehouse_001.jpg
```

**cURL — image from URL:**
```bash
curl -X POST "https://eastus.api.cognitive.microsoft.com/face/v1.0/detect?detectionModel=detection_03&returnFaceId=false" \
  -H "Ocp-Apim-Subscription-Key: <YOUR_FACE_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/image.jpg"}'
```

**Postman:**
- Method: POST
- URL: `https://eastus.api.cognitive.microsoft.com/face/v1.0/detect`
- Headers: `Ocp-Apim-Subscription-Key` = your key
- Body: binary (select file) or raw JSON with `{"url":"..."}`

**Response (face detected):**
```json
[
  {
    "faceId": "abc-123",
    "faceRectangle": { "top": 100, "left": 150, "width": 80, "height": 100 },
    "faceAttributes": { ... }
  }
]
```

**Response (no face):** `[]`

---

### 3.2 Blob Storage — Upload

**Endpoint:** `PUT https://<account>.blob.core.windows.net/<container>/<blob>`

**Auth:** SAS token or account key in header; or connection string via SDK.

**cURL (with SAS):**
```bash
curl -X PUT "https://transferimages.blob.core.windows.net/quarantine/warehouse_001.jpg?<SAS_TOKEN>" \
  -H "x-ms-blob-type: BlockBlob" \
  -H "Content-Type: image/jpeg" \
  --data-binary @sample_images/warehouse_001.jpg
```

**Postman:**
- Method: PUT
- URL: `https://<account>.blob.core.windows.net/<container>/<blob>?<SAS_TOKEN>`
- Headers: `x-ms-blob-type: BlockBlob`, `Content-Type: image/jpeg`
- Body: binary, select image file

---

### 3.3 Table Storage — Insert/Query Entity

**Endpoint:** `https://<account>.table.core.windows.net/<TableName>(PartitionKey='<pk>',RowKey='<rk>')`

**Auth:** Shared key or SAS; typically used via SDK (connection string).

**cURL (REST — requires signing):** Table REST API uses SharedKey auth. Easier to test via SDK or Azure Storage Explorer.

**Postman:** Use Azure Storage REST with `Authorization` header (SharedKey). Prefer **Azure Storage Explorer** or a small Python script for ad‑hoc tests.

**Sample entity (insert/upsert):**
```json
{
  "PartitionKey": "images",
  "RowKey": "warehouse_001.jpg",
  "gps_latitude": 37.3382,
  "gps_longitude": -121.8863,
  "timestamp_original": "2026:02:27 17:35:19",
  "has_human_face": true,
  "routing_state": "quarantine",
  "status": "face_scanned"
}
```

---

## 4. Sample Payloads & Expected Responses

### Face API

| Request | Expected Response |
|---------|-------------------|
| Image with face | `[{ "faceId": "...", "faceRectangle": {...}, ... }]` |
| Image with no face | `[]` |
| Invalid key | `401 Unauthorized` |
| Malformed image | `400 Bad Request` |

### Table (query by RowKey)

**Request:** `GET` entity `PartitionKey=images`, `RowKey=warehouse_001.jpg`

**Response (entity):**
```json
{
  "PartitionKey": "images",
  "RowKey": "warehouse_001.jpg",
  "gps_latitude": 37.3382,
  "gps_longitude": -121.8863,
  "timestamp_original": "2026:02:27 17:35:19",
  "routing_state": "quarantine",
  "status": "quarantined_written",
  "has_human_face": true
}
```

---

## 5. Quick Test Script (Python)

```python
# Test Face API
from azure.ai.vision.face import FaceClient
from azure.ai.vision.face.models import FaceDetectionModel, FaceRecognitionModel
from azure.core.credentials import AzureKeyCredential

client = FaceClient(
    endpoint="https://eastus.api.cognitive.microsoft.com/",
    credential=AzureKeyCredential("<YOUR_KEY>")
)
with open("sample_images/warehouse_001.jpg", "rb") as f:
    faces = client.detect(
        f.read(),
        detection_model=FaceDetectionModel.DETECTION03,
        recognition_model=FaceRecognitionModel.RECOGNITION04,
        return_face_id=False,
    )
print(f"Faces detected: {len(faces)}")
```
