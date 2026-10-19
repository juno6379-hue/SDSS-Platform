# G0 Baseline Provenance Gaps Audit

**Standard**: CODEX v3.0 Section 2.2  
**Baseline Snapshot ID**: `BASELINE-G0-20261019`

## 1. Provenance Gaps Identified

1. **6-Province Full Coverage Gap**:
   - Historical collection consists of small 256×256 sample windows across selected provinces, NOT full province boundaries.
   - Status: `TESTED_SYNTHETIC` / `SMALL_SAMPLE_WINDOW`. Full provincial coverage is `BLOCKED` pending incremental multi-temporal collection (G2-G3).

2. **Esri Land Cover vs. WorldCover Crosswalk**:
   - Historical reliance on WorldCover 2020 v100 and 2021 v200.
   - WorldCover 2021 cannot be cloned as ground truth for 2022-2025.
   - Multi-temporal Esri 10m Land Cover (2020-2025) must be incorporated with strict crosswalk mapping (`10=Clouds`, `0=NoData` excluded).

3. **Database Migration Gap (SQLite -> PostgreSQL/PostGIS)**:
   - `data/catalog.sqlite3` contains 14 total records.
   - Requires formal schema normalization, foreign key enforcement, and PostGIS geometry types (`MultiPolygon`, `GiST` indexes).

4. **Multi-temporal Cloud Gap**:
   - Tropical cloud cover in Indonesia requires SCL-based annual median compositing across all 36 province-year cells (2020-2025).

---
*Verified and frozen as an immutable baseline on 2026-10-19T14:26:28.767323+00:00.*
