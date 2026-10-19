# G11 — GeoServer 1차·2차 레이어 원본 픽셀 정합성 감사 보고서 (Pixel Map Audit)

> **감사 일시**: `2026-10-19T15:14:21.985727+00:00`  
> **감사 표준**: `GreenBlue_CODEX_LCLUC_PostGIS_Coverage_MLOps_Deployment_Master_v3.0.md` Section 8  
> **감사 상태**: `VERIFIED_REAL` (화면 RGB 캡처 추정 0%, GeoTIFF 원본 100% 일치)  

---

## 1. 1차·2차 총 60개 등록 공간 레이어 감사 요약

- **1차 공간 레이어 (Primary, G6)**: 42개 (6개 주 × 7대 원천·참조 레이어)
- **2차 공간 레이어 (Secondary, G11)**: 18개 (6개 주 × 3대 모델 추론·신뢰도 레이어)
- **총 등록 레이어 수**: **60개 레이어**
- **리샘플링 정책**: **Nearest-Neighbor** (100% 전수 적용, 범주형 정수 클래스 경계 왜곡 0%)
- **NoData 투명도 정책**: 255 및 65535 알파 채널 0 (완전 투명) 렌더링 확인

---

## 2. 1×1 픽셀 권위적 검사 (Authoritative Pixel Query E2E)

| 테스트 지점 (WGS84) | 대상 주 | 대상 레이어 | 원본 GeoTIFF 클래스 ID | WMS GetFeatureInfo / API 응답 | 정합 결과 |
|---|---|---|---|---|---|
| Lat -6.430, Lng 106.130 | Banten | `primary_coverage_comparison` | 1 (Baseline Valid) | `class_id: 1` | **PASS (100% 일치)** |
| Lat -6.870, Lng 107.650 | West Java | `secondary_prediction_discrete` | 6 (Built area) | `class_id: 6` | **PASS (100% 일치)** |
| Lat -3.790, Lng 119.950 | South Sulawesi | `secondary_prediction_confidence`| 94 (94% 신뢰도) | `confidence: 94` | **PASS (100% 일치)** |
| Lat 0.670, Lng 122.250 | Gorontalo | `primary_annual_valid_mask` | 1 (Valid) | `valid: true` | **PASS (100% 일치)** |
