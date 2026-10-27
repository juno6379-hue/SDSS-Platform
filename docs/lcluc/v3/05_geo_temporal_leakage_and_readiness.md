# G7 — AI-Ready 데이터셋 분할 및 지리적 홀드아웃·학습 준비성 게이트 보고서

> **표준 규격**: `GreenBlue_CODEX_LCLUC_PostGIS_Coverage_MLOps_Deployment_Master_v3.0.md` Section 7.1
> **생성 시점**: `2026-10-21T02:55:28.672634+00:00`
> **게이트 상태**: `BLOCKED_FAIL_CLOSED` (`ready_for_training=False`)
> **데이터셋 이전/이후 개선율**: `BLOCKED_BASELINE_NOT_PINNED` — 같은 정의·분모·시점의 과거 baseline이 권위 증거로 고정되지 않았다.

---

## 1. 데이터셋 이전(Baseline) vs 이후(New) 1차 KPI 비교

| 핵심 지표 (KPI) | 이전 (Baseline) | 이후 (New Expanded) | 개선량 / 성과 | 상태 |
|---|---|---|---|---|
| **6밴드+라벨·마스크 적격 패치** | `NOT_PINNED` | **1,407개** | 같은 정의의 과거 baseline 부재로 개선량 미산출 | `BLOCKED_BASELINE_NOT_PINNED` |
| **학습 후보 패치 (Train)** | `NOT_PINNED` | **865개** | **패치 수량만으로 학습할 수 없음 (SCENE_SPLIT_LEAKAGE, LEDGER_LEARNING_READY_FALSE, COVERAGE_LEARNING_READY_FALSE, CLASS_COVERAGE_POLICY_FAILED)** | `BLOCKED_BY_READINESS_GATE` |
| **검증 후보 홀드아웃 (Val - Banten)** | `NOT_PINNED` | **292개** | 현재 권위 재고만 검증 | `VERIFIED_REAL_CURRENT_INVENTORY` |
| **시험 후보 홀드아웃 (Test - West Java)** | `NOT_PINNED` | **250개** | 현재 권위 재고만 검증 | `VERIFIED_REAL_CURRENT_INVENTORY` |
| **후보 raster grid 화소 (256×256)** | `NOT_PINNED` | **92,209,152 화소** | 유효 학습 화소·실행 학습량으로 해석 금지 | `VERIFIED_REAL_CURRENT_INVENTORY` |
| **`ready_for_training` 게이트** | `False` (차단) | **`False` (BLOCKED_FAIL_CLOSED)** | **SCENE_SPLIT_LEAKAGE, LEDGER_LEARNING_READY_FALSE, COVERAGE_LEARNING_READY_FALSE, CLASS_COVERAGE_POLICY_FAILED** | `BLOCKED` |

---

## 2. 지리적 홀드아웃(Geographic Holdout) 및 공간 누출 차단 검증

권위 원장의 province-split 정책, `scene_id`의 split 간 교차, 실제 raster footprint의 면적 교차를 각각 독립적으로 검사한다.

1. **Train (학습 파티션 - 865개 패치)**:
   - **배정 주**: east_java, gorontalo, south_sulawesi, southeast_sulawesi
2. **Validation (검증 파티션 - 292개 패치)**:
   - **배정 주**: banten
3. **Test (시험 독립 파티션 - 250개 패치)**:
   - **배정 주**: west_java

- **교차 split scene_id**: S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431
- **교차 split raster footprint 쌍**: 없음
- **class 기여 정책 실패**: test:8:fraction_below_0.5pct, test:8:contributors_below_5, train:8:fraction_below_0.5pct, train:8:contributors_below_5, val:8:fraction_below_0.5pct, val:8:contributors_below_5
- **현재 차단 사유**: SCENE_SPLIT_LEAKAGE, LEDGER_LEARNING_READY_FALSE, COVERAGE_LEARNING_READY_FALSE, CLASS_COVERAGE_POLICY_FAILED
- **권위 보고서 실행 플래그**: `True` — 수집/감사 보고서 생성 여부이며 모델 학습 실행을 뜻하지 않는다.
- **실제 모델 학습 실행**: `False`

---

## 3. 6개 밴드 및 라벨 무결성 계약 (Quality Contract)

- **위성 영상**: Sentinel-2 Level-2A Surface Reflectance (BOA) 6개 물리 반사도 밴드 (B02 Blue, B03 Green, B04 Red, B08 NIR, B11 SWIR-1, B12 SWIR-2), `float32`, 형상 `(6, 256, 256)`.
- **참조 라벨**: Esri 10m LULC 및 ESA WorldCover 교차 검증 9대 표준 분류 (`uint8`, 형상 `(256, 256)`).
- **품질 마스크**: SCL 기반 유효 화소 마스크 (`uint8`, 형상 `(256, 256)`).
