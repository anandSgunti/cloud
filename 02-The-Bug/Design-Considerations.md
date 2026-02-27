# Design Considerations & Decision Rationale (Concise)

**Date:** 2026-02-27  
**Scope:** Key considerations, trade-offs, and risk controls used to arrive at the final architecture that (1) preserves EXIF metadata for ML and (2) enforces 24-hour hard deletion for images with faces, while (3) avoiding changes to the Transfer Bridge.

---

## 1) Requirements We Must Satisfy

### Functional
- **EXIF preservation:** GPS + timestamps must be available to the ML model even if the Bridge strips EXIF.
- **PII enforcement:** Any image with a **human face** must be **hard deleted within 24 hours**.

### Non-functional
- **No Transfer Bridge code changes** (protect $50k investment; avoid regressions and political risk).
- **Scalable + reliable** (batch/stream ingestion, retries, idempotency).
- **Auditability:** Provide evidence of detection decisions and deletion timing.

---

## 2) Constraints & Assumptions

- The Bridge **may strip EXIF** and must remain **unchanged**.
- We need a **stable identifier** (`image_id`) that survives the pipeline (filename or hash).
- “Hard delete” means **irrecoverable deletion**:
  - For PII containers: **soft delete OFF**, **versioning OFF**, and no snapshots (or purge them).
- Face detection is **classification**, not identity verification:
  - Store **boolean/count/confidence**, not embeddings/templates.

---

## 3) Key Engineering Decisions

### A) Decouple metadata from image transport
**Why:** File-based EXIF is fragile through transforms.  
**Decision:** Extract EXIF **before** the Bridge and store it as structured data (Azure Table Storage).

**Result:** ML reads metadata from the table, not from the image file.

---

### B) Classify every image, then route (Approved vs Quarantine)
**Why:** To ensure face images do not propagate downstream.  
**Decision:** Run face detection for every image and route:
- **No face → `approved`**
- **Face detected → `quarantine` + set deletion deadline**

**Result:** The Bridge and ML read from `approved` without PII exposure.

---

### C) Enforce deletion with a scheduler + audit trail
**Why:** Compliance requires a time-bound, provable delete.  
**Decision:** A timer-based deletion job (e.g., every 5 minutes):
- Queries expired face images (`deadline < now`)
- Hard deletes from quarantine
- Writes `pii_deleted_at` and status updates for auditing

**Result:** Guaranteed enforcement with traceable evidence.

---

## 4) Options Considered (and Why We Didn’t Choose Them)

### EXIF options
- **Modify Bridge to preserve EXIF:** technically clean, but violates the “no Bridge changes” constraint.
- **Sidecar JSON / Blob metadata:** workable, but weaker queryability and higher operational risk at scale than a centralized store.

### PII options
- **“Delete everything every 30 minutes” without detection:** only works if *all* images are disposable; it does not support keeping no-face images for ML.
- **Third-party face detection (external APIs):** increases compliance surface area and audit complexity vs Azure-native services.

---

## 5) Threat / Failure Mode Review (What We Designed For)

### Duplicate events / retries
- Expect duplicate triggers; use **idempotent upserts** keyed by `image_id`.

### Detection failures
- **Fail-closed policy:** if detection fails, treat as **face present** → keep in quarantine → schedule deletion.

### Race conditions
- Use a lightweight **status** field (e.g., `scheduled_delete`, `no_face_approved`, `deleted`) so deletion only acts on eligible records.

### Hard delete correctness
- Confirm PII container settings: soft delete/versioning disabled to avoid recoverable deletions.

### Downstream leakage prevention
- Bridge/ML should only read from `approved` (least privilege; optional separate permissions).

---

## 6) Minimal Data Model (PoC + Audit Essentials)

We kept the tracking model small but sufficient for enforcement and audit:

- **Identity:** `PartitionKey`, `RowKey=image_id`
- **EXIF:** `gps_latitude`, `gps_longitude`, `timestamp_original`
- **Face:** `has_human_face`, `face_detection_timestamp`, *(optional)* `face_count`, `confidence`
- **Compliance:** `pii_delete_deadline`, `pii_deleted_at`
- **Routing:** `blob_container` *(and `blob_name` to make delete/move implementable)*
- **Status:** `processing_status`

---

## 7) Why This Meets the “Crisis” Constraints

- **Fixes EXIF loss** without touching the Bridge: EXIF is persisted upstream and queried by ML.
- **Meets 24-hour deletion**: face images are isolated in quarantine and deleted on a strict schedule.
- **Protects the Bridge investment**: the Bridge is unchanged and processes only approved, non-face images.
- **Audit-ready**: deadlines and deletion timestamps are recorded for compliance reporting.

---

## 8) Success Criteria (What “Done” Means)

- **EXIF:** 100% of ML inputs have required GPS/timestamps available via the metadata store.
- **PII:** 0 face images remain beyond 24 hours (target p95 time-to-delete ≤ 24h + scheduler interval).
- **Safety:** no face images are promoted to `approved`.
- **Stability:** Bridge behavior unchanged; no regressions introduced.

---
