# G0 AS-IS Architecture Audit Report (Baseline Frozen)

**Audit Timestamp**: 2026-10-19T14:26:28.767323+00:00  
**Git Commit**: `7a630e7c8e2a4d76994a0f77a0c8b3310e9a786b` (Branch: `main`, Dirty: `True`)  
**Baseline Snapshot ID**: `BASELINE-G0-20261019`  
**Standard**: `GreenBlue_CODEX_LCLUC_PostGIS_Coverage_MLOps_Deployment_Master_v3.0.md`

---

## 1. System Topology & Storage Architecture

```
[ Frontend: React + MapLibre GL + Vite (Port 5174) ]
       │ HTTP / GeoJSON / WMS
       ▼
[ FastAPI Backend (Port 8002) ] ─── [ GeoServer WMS (Port 8088) ]
       │                                     │
       ├─ [ Legacy SQLite: data/catalog.sqlite3 ]  └─ [ Coverages: GeoTIFFs / Styles ]
       └─ [ Raw / Patch Storage: data/ ]
```

- **Frontend**: React 18, TypeScript, MapLibre GL, Vite dev server on port `5174`.
- **Backend API**: FastAPI on port `8002`, asynchronous job dispatcher, in-memory & file-based storage adapters.
- **Relational / Catalog Storage (AS-IS)**:
  - SQLite database at `data/catalog.sqlite3` (155648 bytes).
  - SHA-256: `7c5068be8f430c7cbe10badd9ce7bbf4df94a5045fad788682c96fcb20867b1b`.
  - Tables: records.
- **GIS Map Service**: GeoServer WMS on port `8088` (Status: `ONLINE_HTTP_200`).
- **Data Assets (AS-IS)**: 10303 files, total 6640.1 MB across `data/`.

---

## 2. SQLite Database Inventory (Verified)

| Database File | Size (Bytes) | Integrity | Table Name | Row Count |
|---|---|---|---|---|
| `data/catalog.sqlite3` | 155648 | ok | `records` | 14 |

---

## 3. GeoServer Layer Audit

- **WMS Endpoint**: `http://127.0.0.1:8088/geoserver/wms`
- **Server Status**: `ONLINE_HTTP_200`
- **Registered Layers**: 6 layers detected.

---

## 4. AI & MLOps Baseline State

- **Models Found on Disk**: 0 checkpoints.
- **Store Configuration**: `NOT_FOUND`
- **Baseline Model ID**: `baseline2021_cpu_v1_model`
- **Baseline Metrics (Historic Reported)**:
  - OA: 1.35% (WorldCover reference)
  - mIoU: 0.27% (High Grassland bias)
  - Note: Under CODEX v3.0, historic figures are labeled `LEGACY_REPORTED` and must NOT be mixed with post-improvement evaluations.
