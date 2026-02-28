# ZeroCorp Solution — EXIF Preservation + PII (Face) 24‑Hour Deletion

This document defines the **end-to-end solution** using the provided flow (Steps 1–8). fileciteturn4file0L10-L74

---

## 1) Mermaid Flow Diagram

```mermaid
flowchart TD
    %% ZEROCORP TRANSFER BRIDGE SOLUTION (Mermaid rendition)

    A[Original Image<br/>(with EXIF)] -->|Step 1: Extract EXIF| B[Extracted Metadata<br/>(GPS, timestamp, camera)]
    B -->|Step 2: Save metadata| T[(Azure Table<br/>imagemetadata)]

    A -->|Step 3: Face detection on original| F[Azure Face API]
    F -->|Update has_face + blob_container| T

    F --> D{Step 4: has_face?}

    %% Fail-closed note (recommended): treat unknown as face/PII
    D -->|Yes (face) or Unknown| Q[quarantine container<br/>(PII)]
    D -->|No (approved path only)| BR[Step 5: Transfer Bridge<br/>resize / RGB / compress<br/>(strips EXIF)]

    BR -->|Step 6: ML receives image bytes<br/>(no EXIF)| M[ML Model<br/>query + process]
    M -->|Query EXIF by image_id| T

    M -->|Step 7: Upload processed image| AP[approved container<br/>(retain)]

    %% Scheduled deletion job
    Q -->|Step 8: Scheduled purge (e.g., hourly)<br/>Delete ALL quarantine blobs| HD[Hard Delete<br/>(quarantine only)]
```

**Notes (matching the provided diagram):**
- Only **no-face** images go through the **Transfer Bridge** and into the ML pipeline. fileciteturn4file0L39-L66  
- Images with faces go to **quarantine** and are **hard deleted** via a scheduled purge. fileciteturn4file0L41-L74  
- The ML model retrieves EXIF from the **Azure Table** since EXIF is stripped by the bridge. fileciteturn4file0L49-L58  

---

## 2) Step-by-Step Summary (Mapped to Modules)

| Step | Module | Action | Output |
|------|--------|--------|--------|
| 1 | `step1_extract_exif` | Extract EXIF (GPS, timestamp, camera) from original image | `metadata_dict` + image object |
| 2 | `step2_save_to_table` | Save EXIF metadata to Azure Table (`imagemetadata`) | Table entity created/updated |
| 3 | `face_detection` | Run Face API on original; update table with `has_face` | Table entity updated |
| 4 | `blob_router` | Route: Face → quarantine; No face → continue to Bridge | Blob stored, pointer recorded |
| 5 | `step3_transfer_bridge` | Bridge processes image (approved only); EXIF stripped | processed image bytes |
| 6 | `step4_ml_model` | ML receives bytes; queries Table for EXIF by `image_id`; processes | inference output + metadata |
| 7 | `blob_router` | Upload processed image to approved container | Approved blob stored + URI |
| 8 | Scheduled job | Delete all blobs in quarantine container (hourly) | Compliance satisfied |

(These step names and behaviors are taken directly from the provided flow doc.) fileciteturn4file1L31-L42

---

## 3) Key Design Decisions

### A) EXIF Preservation (Bridge-safe)
- Extract EXIF **before** Transfer Bridge (bridge strips EXIF). fileciteturn4file0L49-L56  
- Persist EXIF in Azure Table for reliable, queryable lookups by `image_id`.
- ML model always uses the table values, not embedded EXIF in the transformed image.

### B) PII Handling + 24h Hard Delete
- Face detection runs on the **original** image before any further processing. fileciteturn4file0L23-L35  
- **Routing:**
  - Face → **quarantine** (PII)
  - No face → Bridge → ML → approved  
  fileciteturn4file1L46-L63  
- A scheduled purge job **deletes all quarantine blobs** on a tight cadence (e.g., hourly) to guarantee hard deletion within 24h. fileciteturn4file0L67-L74  

> Recommended safety hardening: treat *unknown / Face API failure* as **quarantine** (“fail closed”).

---

## 4) Data Linkage: `image_id`

The shared join key is `image_id` (filename or preferably a UUID/hash).

- **Face path:** Original → Table → quarantine blob → (deleted) fileciteturn4file1L67-L74  
- **Approved path:** Original → Table → Bridge → ML query → approved blob fileciteturn4file1L67-L74  

---

## 5) Compliance Mapping

| Requirement | How the solution satisfies it |
|-------------|-------------------------------|
| Metadata loss (EXIF stripped by Bridge) | Extract EXIF before Bridge → store in Table → ML queries Table |
| 24-hour PII deletion | Face images routed to quarantine → scheduled purge deletes quarantine blobs |

(Compliance summary mirrors the provided flow doc.) fileciteturn4file1L78-L83

---

## 6) Operational Notes (Minimal but Practical)

- **Observability:** Track quarantine blob count + oldest quarantine blob age; alert if any blob approaches 24 hours.
- **Idempotency:** Use stable `image_id` (ideally UUID/hash) to make Table upserts and blob writes retry-safe.
- **Security:** Restrict quarantine container access (least privilege); treat metadata table as sensitive (GPS/timestamp).
