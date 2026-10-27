# G14 — 전체 E2E 시험 증거서 (E2E Test Evidence)

> **Unit352 교정**: 이 문서의 G6 5건·G7 4건·총 67건은 `ARCHIVED_PRE_UNIT352` 실행 이력이다. 현행 G6/G7 fail-closed 계약의 시험 수나 현재 학습 준비 증거로 재사용하지 않는다. Unit352 이후 시험은 최신 구현 문서와 인계서에 별도로 기록한다.
> **수행 일시**: `2026-10-19T15:14:21.990072+00:00`
> **시험 결과 범위**: 아래 코드 시험의 당시 실행 결과. 과학적 정확도·실 GeoServer 전수 게시·운영 승인을 검증하지 않음.

---

## 1. 시험 결과 요약

- **백엔드 단위/통합 시험 (`pytest`)**:
  - `test_province_month_coverage_audit.py`: 7 / 7 PASS
  - `test_recovery_rate_engine.py`: 5 / 5 PASS
  - `test_mlops_router.py`: 5 / 5 PASS
  - `test_geoserver_primary_layers.py`: 5 / 5 PASS
  - `test_ai_dataset_splits.py`: 4 / 4 PASS
  - `test_model_benchmark_evaluator.py`: 4 / 4 PASS
  - `test_api.py`: 13 / 13 PASS
  - `test_lcluc_workflow.py`: 19 / 19 PASS
  - `test_landcover_tiles.py`: 5 / 5 PASS
  - **총 백엔드 시험 합격수**: **67 / 67 PASS (100%)**

- **프론트엔드 단위 시험 (`node --test`)**:
  - `modelMlopsWorkspace.test.mjs` 포함 전체 프론트엔드 스위트: **347 / 347 PASS (100%)**

- **프론트엔드 프로덕션 빌드 (`npm run build`)**:
  - **130개 모듈 변환, 0 에러, 성공 빌드**
