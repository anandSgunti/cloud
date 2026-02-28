# ZeroCorp Image Pipeline – Demo Implementation Document

## 1. Overview
This document demonstrates the end-to-end setup of the ZeroCorp Face-Image Quarantine & Approval Pipeline using Microsoft Azure services and Python.

The solution ensures:
- Face images are detected and routed to quarantine
- Hard deletion requirements for PII are enforced
- Approved images retain EXIF metadata
- Full audit trail is maintained

---

# 2. Required Tools & Access

## Required Tools
- Azure Account (active subscription)
- Python 3.9+
- Git (optional)
- VS Code (recommended)

## Required Access
- Azure Portal access: https://portal.azure.com
- Permission to create resources
- Permission to create Cognitive Services resources

---

# 3. Azure Resource Setup

## Step 1: Create Resource Group
Purpose: Logical container for all resources

Configuration:
- Resource Group Name: zerocorp-image-pipeline
- Region: UK South

Expected Result:
Resource group created successfully.

📸 Screenshot 1: Resource Group Overview


![Screenshot 2 – Storage Account Properties](/Screenshots/Picture1.png)

---

## Step 2: Create Storage Account
Purpose: Host blob containers and table storage

Configuration:
- Name: zerocorpstorage[random]
- Region: UK South
- Performance: Standard
- Redundancy: LRS

CRITICAL PII SETTINGS:
- Soft delete for blobs: DISABLED
- Soft delete for containers: DISABLED
- Blob versioning: DISABLED
- Point-in-time restore: DISABLED

Expected Result:
Storage account deployed successfully.

📸 Screenshot 2: Storage Account – Data Protection Settings

![Screenshot 2 – Storage Account Properties](/Screenshots/Picture2.png)

---

## Step 3: Create Blob Containers
Containers Created:
- quarantine (Private)
- approved (Private)

Expected Result:
Both containers visible under Data Storage → Containers.

📸 Screenshot 3: Blob Containers List

![Screenshot 3 – Blob Containers](/Screenshots/Picture3.png)

---

## Step 4: Create Table Storage
Table Name: imagemetadata
Purpose:
- Store EXIF metadata
- Store audit logs

Expected Result:
Table visible in Tables section.

📸 Screenshot 4: Table Storage View

![Screenshot 4 – Table Storage](/Screenshots/Picture4.png)

---

## Step 5: Configure Lifecycle Policy
Rule Name: DeleteOldQuarantineBlobs
Scope: quarantine/ prefix
Action: Delete blobs after 2 days (48 hours)

Purpose:
Acts as failsafe in case application deletion job fails.

Expected Result:
Lifecycle rule visible under Data Management → Lifecycle Management.

📸 Screenshot 5: Lifecycle Policy Rule

![Screenshot 5 – Lifecycle Management Rule](/Screenshots/Picture5.png)

---

## Step 6: Create Azure Face API Resource
Configuration:
- Name: zerocorp-face-api
- Region: West Europe
- Pricing Tier: Free F0

Purpose:
Detect human faces before images enter Transfer Bridge.

Expected Result:
Face API deployed successfully.

📸 Screenshot 6: Face API Resource Overview

![Screenshot 6 – Face API Overview](/Screenshots/Picture6.png)

---

# 4. Architecture Overview

Flow:
1. Image uploaded
2. Face detection via Azure Face API
3. If face detected → Quarantine container
4. If no face → Approved container
5. Metadata stored in Table Storage
6. Scheduled job deletes quarantine images < 24 hours
7. Lifecycle rule deletes > 48h (failsafe)

📊 Diagram:
(Insert architecture diagram screenshot here)

![Screenshot 6 – Face API Overview](/zerocorp_flow.png)

---

# 5. Compliance Controls Implemented

## PII Enforcement
- No face images enter production pipeline
- Quarantine container has no soft delete
- Versioning disabled
- No retention backups

## Hard Delete Strategy
- Application-level hourly deletion job
- Storage lifecycle failsafe (48h)
- Audit log maintained in Table Storage

---

# 6. Application Execution & Output Demonstration

This section demonstrates the live backend execution and observable outputs of the ZeroCorp image pipeline.

---

## 6.1 Backend Execution

The Python backend performs the following steps:

1. **Load images** from `sample_images/` folder (Images Folder / staging)
2. **Extract EXIF** metadata (GPS, timestamp, camera) from original image
3. **Save EXIF to Table Storage** (status: `exif_saved`)
4. **Call Azure Face API** on original image
5. **Evaluate response** — face detected / no face / unknown (fail-closed → quarantine)
6. **Route image** to quarantine or approved path:
   - **Face / unknown** → quarantine container (skip Bridge, will be deleted)
   - **No face** → Transfer Bridge → ML Model (query Table for metadata) → approved container
7. **Log transaction** in Table Storage (status, routing\_state, approved\_blob\_uri)

### Sample Command (Local Execution)

```
python main.py
```

### Console Output :&#x20;

**EXIF Extracted**

![image.png](/Screenshots/Picture7.png)

**EXIF Metadata Save to Azure Table**

![image.png](/Screenshots/Picture8.png)

![image.png](/Screenshots/pic9.jpg)


**Face Detection and Metadata Insertion  after Tranfer Bridge**

<br>

<br>


![image.png](/Screenshots/Picture10.png)
![image.png](/Screenshots/face.jpg)
<br>

---

## 6.2 Portal Validation (Visual Proof)

### Case 1: Face Image

**Validation Steps:**

- Confirm blob appears in `quarantine` container
- Confirm entry exists in `imagemetadata` table
- Confirm deletion after SLA window (hourly purge job)

![image.png](/Screenshots/pic12.jpg)
![image.png](/Screenshots/quar.jpg)

---

### Case 2: Non-Face Image

**Validation Steps:**

- Confirm blob appears in `approved` container
- Confirm EXIF metadata values stored correctly in table
- Confirm no `pii_delete_deadline` (no deletion scheduled)

![image.png](/Screenshots/pic11.jpg)
![image.png](/Screenshots/approved.jpg)

## 6.3 Table Storage Record Example

Table: `imagemetadata`\
PartitionKey: `images` (all entities use same partition)

### Approved Image (No Face)

| Field                 | Value                                                                     |
| --------------------- | ------------------------------------------------------------------------- |
| PartitionKey          | images                                                                    |
| RowKey                | warehouse\_002.jpg                                                        |
| gps\_latitude         | 37.4419                                                                   |
| gps\_longitude        | -122.143                                                                  |
| timestamp\_original   | 2026:02:27 17:35:20                                                       |
| has\_human\_face      | False                                                                     |
| routing\_state        | approved                                                                  |
| status                | approved\_written                                                         |
| approved\_blob\_uri   | <https://transferimages.blob.core.windows.net/approved/warehouse_002.jpg> |
| pii\_delete\_deadline | *(not set)*                                                               |
| schema\_version       | 1                                                                         |

### Quarantine Image (Face Detected)

| Field                 | Value                            |
| --------------------- | -------------------------------- |
| PartitionKey          | images                           |
| RowKey                | warehouse\_001.jpg               |
| gps\_latitude         | 37.3382                          |
| gps\_longitude        | -121.8863                        |
| timestamp\_original   | 2026:02:27 17:35:19              |
| has\_human\_face      | True                             |
| routing\_state        | quarantine                       |
| status                | quarantined\_written             |
| pii\_delete\_deadline | 2026-02-28T17:35:19Z (UTC + 24h) |
| schema\_version       | 1                                |

---

## 6.4 Deletion Job Demonstration

Hourly deletion job purges **all blobs** in the quarantine container (quarantine = PII zone; everything there is destined for deletion).

**Sample output:**

```
Deletion job started: 2026-02-28 16:00
Scanning quarantine container...
Found 3 blobs in quarantine
Deleting blobs...
   Deleted: warehouse_001.jpg
   Deleted: employee_001.jpg
   Deleted: portrait_002.jpg
Deletion complete
Table updated: status=pii_deleted
Audit log updated
```

**Validation:**

- Blobs removed from quarantine container
- Table row updated with `status=pii_deleted` and deletion timestamp

**Screenshot 11:** Quarantine Container After Deletion *(Insert screenshot)*

---

# 7. Results Achieved

| Requirement                          | Status                             |
| ------------------------------------ | ---------------------------------- |
| Secure face detection implemented    | Done                               |
| PII compliance enforced              | Done                               |
| Hard delete within 24 hours ensured  | Done (quarantine purge)            |
| Audit trail established              | Done (status, timestamps in table) |
| EXIF metadata preserved for ML model | Done                               |
| Infrastructure deployed              | Done                               |

---

# 8. Conclusion

This demo shows a compliant, production-ready image pipeline that:

- **Protects PII** — face images routed to quarantine and hard-deleted
- **Preserves model-critical metadata** — EXIF extracted before Bridge, stored in Table
- **Enforces hard deletion** — quarantine blobs purged on schedule
- **Uses Azure-native services** — Face API, Blob, Table Storage

---

# 9. Appendix

### Resources Used

- Storage Account: `transferimages`
- Blob Containers: `quarantine`, `approved`
- Table: `imagemetadata`
- Azure Face API (East US)

### Future Enhancements

- CI/CD deployment via Bicep/Terraform
- Managed identity / Service Principal authentication
- Lifecycle policy for automated blob purge
- Automated compliance dashboard

<br>
