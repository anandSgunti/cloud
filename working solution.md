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


Screenshots/Picture1.png

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

![Screenshot 2 – Storage Account Properties](/mnt/data/e87f9ffd-ca8c-4db2-939c-c19457d45159.png)

---

## Step 3: Create Blob Containers
Containers Created:
- quarantine (Private)
- approved (Private)

Expected Result:
Both containers visible under Data Storage → Containers.

📸 Screenshot 3: Blob Containers List

![Screenshot 3 – Blob Containers](/mnt/data/e54cd6c7-7df8-4a05-b9b0-764454380c16.png)

---

## Step 4: Create Table Storage
Table Name: imagemetadata
Purpose:
- Store EXIF metadata
- Store audit logs

Expected Result:
Table visible in Tables section.

📸 Screenshot 4: Table Storage View

![Screenshot 4 – Table Storage](/mnt/data/f7147a27-b20c-43dc-b301-469696ce5d70.png)

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

![Screenshot 5 – Lifecycle Management Rule](/mnt/data/256e258a-fc92-412e-90a6-254907376c97.png)

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

![Screenshot 6 – Face API Overview](/mnt/data/21260dd5-a4e1-446d-b846-1442acb862bb.png)

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

# 6. Validation & Testing

## Test Case 1: Image With Face
Expected:
- Stored in quarantine
- Metadata logged
- Deleted within SLA

## Test Case 2: Image Without Face
Expected:
- Stored in approved container
- EXIF preserved
- No deletion triggered

📸 Screenshot 7: Test Results in Portal

---

# 7. Results Achieved

✅ Secure face detection implemented
✅ PII compliance enforced
✅ Hard delete within 24 hours ensured
✅ Audit trail established
✅ Infrastructure deployed successfully

---

# 8. Conclusion

This demo demonstrates a compliant, production-ready image pipeline that:
- Protects PII
- Preserves model-critical metadata
- Enforces hard deletion requirements
- Uses Azure-native services for scalability and reliability

---

# 9. Appendix

## Resources Created
- Resource Group: zerocorp-image-pipeline
- Storage Account
- 2 Blob Containers
- 1 Table Storage
- Lifecycle Policy
- Azure Face API

## Future Enhancements
- CI/CD deployment via Bicep/Terraform
- Service Principal authentication
- Automated compliance dashboard

