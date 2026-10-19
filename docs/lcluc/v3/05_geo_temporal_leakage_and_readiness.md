# G7 — AI-Ready 데이터셋 분할 및 지리적 홀드아웃·학습 준비성 게이트 보고서

> **표준 규격**: `GreenBlue_CODEX_LCLUC_PostGIS_Coverage_MLOps_Deployment_Master_v3.0.md` Section 7.1  
> **생성 시점**: `2026-10-19T22:58:22.492194+00:00`  
> **게이트 상태**: `GATE_PASSED_READY_FOR_TRAINING` (`ready_for_training=True`)  
> **데이터셋 확장율**: **+88,900.0%** (과거 적격 2패치 $\to$ 현재 실측 1,780패치)  

---

## 1. 데이터셋 이전(Baseline) vs 이후(New) 1차 KPI 비교

| 핵심 지표 (KPI) | 이전 (Baseline) | 이후 (New Expanded) | 개선량 / 성과 | 상태 |
|---|---|---|---|---|
| **6밴드+라벨·마스크 적격 패치** | **2개** (Banten 1, West Java 1) | **1,780개** | **+1,778개 (+88,900.0%)** | `VERIFIED_REAL` |
| **학습용 패치 (Train)** | **0개** (`BLOCKED`) | **1,179개** | **학습 불능 공백 완전 해소** | `RESOLVED_BOTTLENECK` |
| **검증용 홀드아웃 (Val - Banten)** | 1개 | **337개** | +336개 확장 | `VERIFIED_REAL` |
| **시험용 독립 홀드아웃 (Test - West Java)** | 1개 | **264개** | +263개 확장 | `VERIFIED_REAL` |
| **총 학습 픽셀 수 (256×256)** | 131,072 화소 | **116,654,080 화소** | **890.0배 데이터 확장** | `VERIFIED_REAL` |
| **`ready_for_training` 게이트** | `False` (차단) | **`True` (통과)** | **정식 MLOps 재학습 개시 가능** | `GATE_PASSED` |

---

## 2. 지리적 홀드아웃(Geographic Holdout) 및 공간 누출 차단 검증

본 프로젝트는 모델의 과적합 및 공간적 데이터 누출(Spatial Data Leakage)을 원천 차단하기 위해 **지리적 분할 원칙**을 강제한다:

1. **Train (학습 파티션 - 1,179개 패치)**:
   - **배정 주**: East Java (248개), South Sulawesi (320개), Gorontalo (272개), Southeast Sulawesi (339개)
   - **지리적 특성**: 자바 동부 화산·농경지대 및 술라웨시 열대 우림·산림·관목 지형 대표
2. **Validation (검증 파티션 - 337개 패치)**:
   - **배정 주**: Banten (337개)
   - **지리적 특성**: 자바 서단 해안·구릉 농업 지대 (Train 주와 완벽한 행정구역 및 공간 분리)
3. **Test (시험 독립 파티션 - 264개 패치)**:
   - **배정 주**: West Java (264개)
   - **지리적 특성**: 수도권 인접 도시화·고도 농업 복합 지형
   - **독립성 보장**: Train 및 Val에 전혀 포함되지 않은 완전 독립 지리 표본으로, 모델의 일반화 성능을 정밀 측정

---

## 3. 6개 밴드 및 라벨 무결성 계약 (Quality Contract)

- **위성 영상**: Sentinel-2 Level-2A Surface Reflectance (BOA) 6개 물리 반사도 밴드 (B02 Blue, B03 Green, B04 Red, B08 NIR, B11 SWIR-1, B12 SWIR-2), `float32`, 형상 `(6, 256, 256)`.
- **참조 라벨**: Esri 10m LULC 및 ESA WorldCover 교차 검증 9대 표준 분류 (`uint8`, 형상 `(256, 256)`).
- **품질 마스크**: SCL 기반 유효 화소 마스크 (`uint8`, 형상 `(256, 256)`).
