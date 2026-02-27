sequenceDiagram
    autonumber
    participant Bridge as Transfer Bridge
    participant Quarantine as Quarantine<br/>Container
    participant EventGrid as Event Grid
    participant FaceFunc as Face Detector<br/>Function
    participant Vision as Azure AI<br/>Vision
    participant DB as Azure SQL<br/>Database
    participant KeyVault as Key Vault
    participant Approved as Approved<br/>Container
    participant Scheduler as Deletion<br/>Scheduler
    
    Bridge->>Quarantine: Upload image
    Quarantine->>EventGrid: BlobCreated event
    EventGrid->>FaceFunc: Trigger function
    
    FaceFunc->>Quarantine: Download image
    FaceFunc->>Vision: Detect faces
    Vision-->>FaceFunc: Result: Face found
    
    FaceFunc->>KeyVault: Get encryption key
    KeyVault-->>FaceFunc: Return key
    
    FaceFunc->>DB: Encrypt & store result
    Note over DB: has_human_face = ENCRYPTED(TRUE)<br/>deadline = now + 24h<br/>status = scheduled_delete
    
    alt No Face
        FaceFunc->>Approved: Move blob
        FaceFunc->>DB: Update: approved
    else Face Detected
        Note over Quarantine: Image stays in quarantine
    end
    
    Note over Scheduler: 24 hours later...
    
    Scheduler->>DB: Query expired images
    DB-->>Scheduler: Return expired list
    
    Scheduler->>KeyVault: Get decryption key
    KeyVault-->>Scheduler: Return key
    
    Scheduler->>Quarantine: Hard delete blob
    Note over Quarantine: Permanently removed
    
    Scheduler->>DB: Update: pii_deleted_at = NOW()
    Scheduler->>DB: Write audit log
```

---

## Database Schema Design

### Compliance Tracking Table
```
TABLE: image_metadata

┌─────────────────────────────────────────────────────┐
│ EXIF Metadata (from previous solution)              │
├─────────────────────────────────────────────────────┤
│ • image_id (Primary Key)                            │
│ • gps_latitude, gps_longitude                       │
│ • timestamp_original                                │
│ • camera_make, camera_model                         │
├─────────────────────────────────────────────────────┤
│ PII Compliance Fields (NEW)                         │
├─────────────────────────────────────────────────────┤
│ • has_human_face (ENCRYPTED 🔒)                     │
│ • face_count                                        │
│ • face_detection_confidence (0.0 - 1.0)            │
│ • face_detection_timestamp                          │
│                                                     │
│ • pii_delete_required (TRUE/FALSE)                  │
│ • pii_delete_deadline (timestamp + 24h)            │
│ • pii_deleted_at (when actually deleted)           │
│ • deletion_verified (TRUE/FALSE)                    │
├─────────────────────────────────────────────────────┤
│ Processing Status                                   │
├─────────────────────────────────────────────────────┤
│ • processing_status:                                │
│   - 'uploaded' (just uploaded)                      │
│   - 'face_detection_pending' (analyzing)            │
│   - 'no_face_approved' (moved to approved)          │
│   - 'scheduled_delete' (awaiting deletion)          │
│   - 'deleted' (permanently removed)                 │
├─────────────────────────────────────────────────────┤
│ Blob Location Tracking                              │
├─────────────────────────────────────────────────────┤
│ • blob_container ('quarantine' or 'approved')       │
│ • blob_url (full path to blob)                      │
├─────────────────────────────────────────────────────┤
│ Audit Trail                                         │
├─────────────────────────────────────────────────────┤
│ • created_at (upload timestamp)                     │
│ • updated_at (last modification)                    │
└─────────────────────────────────────────────────────┘
```

### Database Indexes (for Performance)
```
Performance Indexes:
├─ PRIMARY KEY on image_id (fast lookups)
├─ INDEX on pii_delete_deadline (deletion queries)
├─ INDEX on processing_status (status filtering)
└─ INDEX on blob_container (routing queries)
```

---

## Encryption Strategy: Always Encrypted

### What is Always Encrypted?
```
┌─────────────────────────────────────────────────┐
│ Regular Database Encryption                     │
├─────────────────────────────────────────────────┤
│ ├─ Data encrypted on disk                      │
│ ├─ Data DECRYPTED in database memory           │
│ ├─ DBAs can see decrypted data                 │
│ └─ Risk: Memory dumps, admin access            │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Always Encrypted (Our Choice) 🔒               │
├─────────────────────────────────────────────────┤
│ ├─ Data encrypted on disk AND in memory        │
│ ├─ Database NEVER sees decrypted data          │
│ ├─ Only authorized apps can decrypt            │
│ ├─ DBAs see only encrypted bytes               │
│ └─ Keys stored in Azure Key Vault              │
└─────────────────────────────────────────────────┘
```

### Encryption Setup
```
Step 1: Create Column Master Key
├─ Stored in: Azure Key Vault
├─ Key Type: RSA 2048-bit
└─ Access: Managed Identity only

Step 2: Create Column Encryption Key
├─ Encrypted by: Column Master Key
├─ Algorithm: RSA_OAEP
└─ Rotation: Automatic every 90 days

Step 3: Encrypt Sensitive Column
├─ Column: has_human_face
├─ Encryption Type: Deterministic (allows WHERE queries)
├─ Algorithm: AEAD_AES_256_CBC_HMAC_SHA_256
└─ Result: DBAs cannot see if image has face
```

### Who Can See What?

| Role | EXIF Data | Face Status (Encrypted) | Face Status (Decrypted) |
|------|-----------|------------------------|------------------------|
| **Database Admin** | ✅ Yes | ✅ Yes (encrypted bytes only) | ❌ No |
| **Azure Function** (with key) | ✅ Yes | ✅ Yes | ✅ Yes (auto-decrypts) |
| **ML Model** | ✅ Yes | ❌ Not needed | ❌ Not needed |
| **Operations Team** | ✅ Yes (dashboard) | ❌ No | ❌ No |
| **Attacker** (if DB breached) | ⚠️ Exposed | ✅ Encrypted (useless) | ❌ No (needs Key Vault) |

---

## Critical Configuration: Storage Containers

### Quarantine Container
```
Container Name: quarantine
Purpose: Temporary staging for ALL uploads

Configuration:
├─ Access Level: Private (no public access)
├─ Soft Delete: DISABLED ❌ (Critical!)
├─ Versioning: DISABLED ❌ (Critical!)
├─ Change Feed: Enabled (audit trail)
└─ Lifecycle Policy: Delete blobs > 48 hours (failsafe)

Why disable soft-delete?
└─ Soft-delete allows recovery for 7-14 days
   This violates 24-hour hard delete requirement
   Must be IRRECOVERABLY deleted for compliance ✅
```

### Approved Container
```
Container Name: approved
Purpose: Storage for verified no-face images

Configuration:
├─ Access Level: Private
├─ Soft Delete: Enabled (7 days) ✅ (OK - no PII)
├─ Versioning: Optional
└─ Lifecycle Policy: Archive after 90 days (cost optimization)
```

---

## Compliance Guarantees

### 24-Hour Deletion Timeline
```
Timeline Breakdown:

Upload Time:           T + 0:00
├─ Image uploaded to quarantine
│
Face Detection:        T + 0:00 to T + 0:01
├─ Event Grid triggers (100-200ms)
├─ Face detection runs (200-500ms)
└─ Database updated with deadline

Deletion Deadline:     T + 24:00
├─ 24 hours from detection timestamp
│
Deletion Scheduler:    Runs every 5 minutes
├─ Checks at: T+24:00, T+24:05, T+24:10...
│
Maximum Deletion Time: T + 24:10
├─ 24 hours (deadline)
├─ + 5 minutes (scheduler interval)
├─ + ~1 minute (processing time)
└─ Total: 24 hours 6 minutes ✅

Failsafe Mechanism:    T + 48:00
└─ Lifecycle policy deletes anything > 48 hours
   Catches any missed deletions
```

### Hard Delete Verification
```
Hard Delete Checklist:

✅ Blob deleted from quarantine container
✅ Soft-delete bypassed (no recovery possible)
✅ All versions purged (if versioning was on)
✅ All snapshots deleted
✅ Database updated: pii_deleted_at = NOW()
✅ Audit log created with timestamp
✅ No way to recover the image

Verification Method:
└─ Attempt to restore deleted blob
   Result: Error "Blob not found" ✅
```

---

## Error Handling Strategy

### Face Detection Failures
```
Scenario: Azure AI Vision API unavailable

Conservative Approach (Safer for Compliance):
├─ Retry 3 times with exponential backoff
├─ If still failing:
│  ├─ ASSUME face exists (conservative)
│  ├─ Mark: pii_delete_required = TRUE
│  ├─ Schedule deletion (24h deadline)
│  └─ Alert operations team
└─ Result: Image gets deleted (safer than risk)

Why conservative?
└─ Better to delete a no-face image than keep a face image
   Prioritizes compliance over convenience
```

### Deletion Scheduler Failures
```
Scenario: Deletion Scheduler function crashes

Mitigation:
├─ Azure Functions auto-restart
├─ Next run catches up (queries all overdue)
├─ Alert if no deletions for > 1 hour
└─ Lifecycle policy failsafe (48h)

Maximum Delay:
└─ 5 minutes (next scheduler run)
   Still within 24-hour window ✅
```

### Database Encryption Key Unavailable
```
Scenario: Key Vault temporarily down

Impact:
├─ Cannot encrypt new face detections
├─ Cannot decrypt for deletion queries

Response:
├─ Queue images for reprocessing
├─ Alert critical error
├─ Do NOT delete without key verification
└─ System pauses until Key Vault recovers

Safety First:
└─ Never compromise encryption integrity
   Wait for Key Vault recovery ✅
```

### Race Condition Prevention
```
Scenario: Deletion scheduler runs while detection in progress

Prevention: processing_status field
├─ 'uploaded' → Not checked yet, don't delete
├─ 'face_detection_pending' → In progress, don't delete
├─ 'scheduled_delete' → Ready for deletion ✅

Scheduler Query:
WHERE processing_status = 'scheduled_delete'
  AND pii_delete_deadline < NOW()
  AND pii_deleted_at IS NULL

Result: No race condition possible ✅
```

---

## Monitoring & Audit Trail

### Real-Time Compliance Dashboard
```
┌─────────────────────────────────────────────────┐
│  PII Compliance Dashboard - Live Status         │
├─────────────────────────────────────────────────┤
│                                                 │
│  📊 Current Status                              │
│  ├─ Images in Quarantine: 23                   │
│  │  ├─ Awaiting Detection: 3                   │
│  │  └─ Awaiting Deletion: 20                   │
│  ├─ Images in Approved: 1,224                  │
│  └─ Total Processed Today: 1,247               │
│                                                 │
│  ⏰ Compliance Metrics                          │
│  ├─ Oldest Pending Deletion: 6h 23min left ✅  │
│  ├─ Deletions Overdue: 0 ✅                    │
│  ├─ Deletions Today: 312                       │
│  └─ Average Time to Delete: 24h 4min ✅        │
│                                                 │
│  🔍 Face Detection                              │
│  ├─ Success Rate: 99.8%                        │
│  ├─ Faces Detected Today: 374 (30%)            │
│  └─ API Errors: 0                              │
│                                                 │
│  🔒 Security Status                             │
│  ├─ Always Encrypted: Active ✅                 │
│  ├─ Key Vault: Healthy ✅                       │
│  └─ Unauthorized Access: 0 ✅                   │
│                                                 │
│  🚨 Active Alerts                               │
│  └─ No violations detected ✅                   │
└─────────────────────────────────────────────────┘
```

### Audit Log Structure
```
Audit Trail Entry (Example):

Audit ID: aud_20260228_103523_001
Timestamp: 2026-02-28 10:35:23 UTC

Image Details:
├─ Image ID: employee_001.jpg
├─ Uploaded: 2026-02-27 10:30:00
├─ Face Detected: 2026-02-27 10:30:19
├─ Face Count: 1
└─ Confidence: 0.98

Deletion Timeline:
├─ Scheduled Deadline: 2026-02-28 10:30:19
├─ Actual Deletion: 2026-02-28 10:35:23
├─ Time from Upload: 24h 5min 23sec
└─ Compliance Status: COMPLIANT ✅

Deletion Verification:
├─ Deleted from: quarantine container
├─ Deletion Method: hard_delete
├─ Soft-delete Bypassed: TRUE
├─ Recovery Possible: FALSE ✅
└─ Database Updated: TRUE

System Actor:
├─ Function: DeletionScheduler
├─ Identity: Managed Identity
└─ Authorization: Key Vault verified
```

### Alert Configuration
```
Critical Alerts (Immediate Action):
├─ Image past 24h deadline not deleted
├─ Deletion scheduler failed
├─ Key Vault unavailable
└─ Action: Page on-call team

Warning Alerts (Email Team):
├─ Face detection failure rate > 10%
├─ Quarantine container > 100 images for > 12h
└─ Database query latency > 100ms
```

---

## Why This Solution Works

### ✅ Compliance Achieved
```
24-Hour Deletion Requirement:
├─ Maximum deletion time: 24h 10min ✅
├─ Hard delete (no recovery) ✅
├─ Complete audit trail ✅
└─ Automated enforcement ✅
```

### ✅ Security Implemented
```
Data Protection:
├─ Always Encrypted for PII data ✅
├─ Keys in Azure Key Vault ✅
├─ Managed Identity (no passwords) ✅
├─ Private network endpoints (optional) ✅
└─ Complete access logging ✅
```

### ✅ Operationally Sound
```
Reliability:
├─ Event-driven architecture (scalable) ✅
├─ Automated deletion (no manual work) ✅
├─ Failsafe mechanisms (lifecycle policy) ✅
├─ Conservative error handling ✅
└─ Real-time monitoring ✅
```

### ✅ Politically Safe
```
Transfer Bridge Impact:
├─ Bridge uploads to quarantine (minor change) ✅
├─ Bridge code unchanged ✅
├─ No criticism of Bridge design ✅
└─ $50k investment preserved ✅
```

---

## Implementation Timeline
```
Week 1: Infrastructure
├─ Create quarantine/approved containers
├─ Setup Azure SQL with Always Encrypted
├─ Configure Azure Key Vault
└─ Deploy Event Grid subscriptions

Week 2: Face Detection
├─ Build Face Detector Function
├─ Integrate Azure AI Vision
├─ Implement database encryption
└─ Test with sample images

Week 3: Deletion Automation
├─ Build Deletion Scheduler
├─ Implement hard delete logic
├─ Configure alerts
└─ End-to-end testing

Week 4: Production
├─ Security review
├─ Deploy to production
├─ Monitor for 48 hours
└─ Document and handoff

Total: 4 weeks to production
