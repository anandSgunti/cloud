# ZeroCorp Transfer Bridge – Assessment Solution 

---

## Solution Overview

### Approach: Pre-Processing Layer (Non-Invasive)

Instead of changing the Transfer Bridge:

- **EXIF**: Extract and store metadata in Azure Table Storage **before** the Bridge processes images. The ML model then queries the table by `image_id` instead of reading EXIF from the file.
- **PII**: Detect faces before the Bridge using Azure Face API. Route images with faces to a **quarantine** container and run an hourly purge. Route non-face images through the Bridge to the **approved** container.

### Outcomes

- Transfer Bridge is **unchanged**.
- EXIF is preserved in a metadata store and available to the ML model.
- Face images are deleted within about **1 hour** (well within the 24-hour requirement).
- Full audit trail for compliance.

---

## Suggested Sequence

1. **Understand the problem** → `01-root-cause-analysis/RCA.md`
2. **Review solution options** → `02-The-Bug/01_Solutions_Options.md`, `03. The-Privacy/options-Considered.md`
3. **See the full architecture** → `Unified-Solution.md`
4. **Run end-to-end** → `working solution.md`
5. **CEO escalation (Part 2)** → `Email.md`

---

## End-to-End Working Solution

The solution is **implemented and executed end-to-end**. For the complete working guide—Azure setup, resource configuration, execution steps, and validation—see:

| Document | Contents |
|----------|----------|
| **[`working solution.md`](working%20solution.md)** | Full end-to-end guide: Azure resource setup, lifecycle policy, Face API, app execution, console output, portal validation, Table Storage records, deletion job demo, and results achieved |

Use `working solution.md` when you want to run the pipeline yourself or verify the full flow.

---

## Repository Structure

```
cloud/
├── README.md                          # This file
├── Email.md                           # CEO escalation (Part 2) – model quality & delays
├── Unified-Solution.md                # Full unified architecture (both problems)
├── working solution.md                # End-to-end execution guide (setup, run, validate)
│
├── 01-root-cause-analysis/
│   └── RCA.md                         # Root cause: EXIF loss at resize step
│
├── 02-The-Bug/
│   ├── 01_Solutions_Options.md        # EXIF fix options comparison
│   └── 02_Solution_Architecture.md    # EXIF solution on Azure
│
├── 03. The-Privacy/
│   ├── options-Considered.md          # PII deletion options
│   └── Solution architecture.md       # PII solution architecture
│
└── code/                              # Reference implementation
    ├── main.py                        # Orchestrates 6-step pipeline
    ├── config.py                      # Configuration
    ├── face_detection.py              # Face detection (Azure Face API)
    ├── table.py                       # Azure Table client
    ├── requirements.txt               # Dependencies
    ├── .env.example                   # Environment variables
    └── modules/
        ├── step1_extract_exif.py      # Extract EXIF from original
        ├── step2_save_to_table.py     # Save EXIF to Azure Table
        ├── step3_transfer_bridge.py   # Simulate Bridge (resize/compress)
        ├── step4_ml_model.py          # ML model (queries Table for EXIF)
        └── blob_router.py             # Route to quarantine vs approved
```

---

## Design Principles

1. **Extract before Bridge** – Capture EXIF and face status before the Bridge processes images.
2. **Decouple metadata from transport** – Store metadata in Azure Table Storage; images in Blob Storage.
3. **Leave Bridge unchanged** – Treat this as an enhancement layer, not a rewrite.
4. **Fail closed for faces** – If face detection is uncertain, route to quarantine.

---

## Documentation Map

| Topic | Document |
|-------|----------|
| **How to run end-to-end (working guide)** | **`working solution.md`** |
| **CEO escalation – model quality & delays (Part 2)** | **`Email.md`** |
| Why EXIF is lost | `01-root-cause-analysis/RCA.md` |
| EXIF solution options | `02-The-Bug/01_Solutions_Options.md` |
| EXIF solution design | `02-The-Bug/02_Solution_Architecture.md` |
| PII solution options | `03. The-Privacy/options-Considered.md` |
| PII solution design | `03. The-Privacy/Solution architecture.md` |
| Unified architecture | `Unified-Solution.md` |

---

## Running the Code

1. Copy `.env.example` to `.env` and set Azure credentials.
2. Install dependencies: `pip install -r requirements.txt`
3. Ensure sample images exist in the configured directory.
4. Run: `python main.py`

The pipeline demonstrates: EXIF extraction → Table storage → Face detection → Blob routing (quarantine vs approved) → Bridge processing (no-face only) → ML model using Table-backed metadata.

---

