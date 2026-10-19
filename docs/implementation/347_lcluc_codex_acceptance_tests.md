# 347. LCLUC CODEX 제13장 필수 수용시험(14 Mandatory Acceptance Tests) 자동화 및 검증 보고서

상태: **VERIFIED_CORE_ACCEPTANCE_SUITE** (14건 전건 PASS, 2.27초, 회귀 포함 36건 전원 통과).
- **적용 규격**: `UI/GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md` 제13장 (1~14조)
- **자동화 시험 슈트**: `tests/test_lcluc_codex_acceptance.py` (14건 전건 PASS)
- **산출물**: `docs/lcluc-map/acceptance-test-results.json` (스키마 v1.0.0, 14건 시험 결과 및 환경 증빙)
- **연계 시험**:
  - `tests/test_landcover_tiles.py`: 5건 PASS
  - `tests/test_lcluc_unified_analytics.py`: 17건 PASS
  - `tests/test_lcluc_codex_acceptance.py`: 14건 PASS
  - **총 36건 전원 PASS (3.72초)**

---

## 1. 개요 및 목적

`UI/GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md` 제13장은 LCLUC 연차별 실자료 지도 서비스 및 시계열 분석 시스템의 신뢰성과 안전성을 보증하기 위해 **14가지 필수 수용시험(14 Mandatory Acceptance Tests)**을 명문화하고 있습니다.

본 Unit 347에서는 Section 13의 14개 조항을 1:1로 대응 검증하는 완전 자동화된 통합 수용 시험 슈트 `tests/test_lcluc_codex_acceptance.py`를 구축하고 실행하여 전건 통과를 입증하였으며, 기계 가독형 검증 결과서 `docs/lcluc-map/acceptance-test-results.json`을 생성하였습니다.

---

## 2. 14개 필수 수용시험 상세 검증 내역

| 시험 번호 | 명세 조항 (CODEX Section 13) | 시험 함수명 | 검증 방식 및 판정 | 검증 상태 |
|:---:|---|---|---|:---:|
| **Test 1** | GeoServer 요청을 끊으면 지도는 연결 실패/자료 없음이 되며 임의 격자로 대체되지 않는다. | `test_01_service_disconnect_fails_without_random_grid` | 연결 단절/미등록 레이어에 대해 `KeyError` 발생 및 빈 영역에 `EMPTY_TILE_PNG` (100% 투명 화소, 노이즈 엔트로피 0) 반환 검증. 절대로 임의 절차적 격자(procedural noise)를 생성하지 않음. | **VERIFIED_REAL** |
| **Test 2** | 한 자료의 클래스 ID별 테스트 픽셀이 범례 색상과 일치한다. 시험조건에서 불필요한 색상 보간이 없다. | `test_02_pixel_colors_match_legend_without_interpolation` | 9개 클래스 정수 ID GeoTIFF 렌더링 후 생성된 RGBA 타일의 중심 및 경계 화소 전수 검사. 이산 클래스 색상과 100% 일치하며 경계에 선형 보간(Bilinear blur) 화소가 전혀 없는 최근접 이웃(Nearest Neighbor) 보존 검증. | **VERIFIED_REAL** |
| **Test 3** | 같은 좌표의 T1/T2 원본 픽셀 조회 결과와 화면 선택 결과가 일치한다. | `test_03_coordinate_pixel_query_matches_source_rasters` | `inspect_pixel_at`이 화면 표시 RGB를 역추정하지 않고 원본 래스터 행렬에서 직접 정수 클래스 ID, 클래스명, 변화 여부, NoData 상태를 1:1 정확히 반환함을 검증. | **VERIFIED_REAL** |
| **Test 4** | 모의 4×4 자료에서 1→2 두 픽셀, 2→1 한 픽셀만 변경하고 나머지는 유지했을 때 전이행렬·총변화 픽셀 수가 기대값과 일치한다. 이 시험은 과학 정확도 검증이 아니다. | `test_04_mock_4x4_acceptance_matrix` | CODEX 모의 4×4 데이터셋 검증: `matrix[1, 2] == 2`, `matrix[2, 1] == 1`, 변화 화소 3개, 유지 화소 13개, 공통 유효 화소 16개 정확 일치. (알고리즘 연산 검증이며 과학적 정확도 판정이 아님을 명시). | **TESTED_SYNTHETIC** |
| **Test 5** | T1 또는 T2 NoData인 픽셀은 변화통계에서 제외된다. | `test_05_nodata_strictly_excluded_from_transition_matrix` | T1 또는 T2 중 어느 한쪽이라도 NoData(255)인 화소(3개 화소)는 공통 유효영역에서 완전히 제외되어 전이행렬 합계가 정확히 13개 화소로만 구성됨을 검증. | **VERIFIED_REAL** |
| **Test 6** | zoom·Swipe 위치만 바꿔도 같은 AOI 비교 통계는 바뀌지 않는다. | `test_06_statistics_invariant_under_zoom_and_swipe` | 줌 레벨(5~20), 뷰포트 바운딩 박스, 스와이프 슬라이더 위치(0%~100%)를 변경해도 산출 통계와 전이행렬 수치가 비트 단위로 동일함을 검증 (화면 표시와 분석 통계의 절대적 분리). | **VERIFIED_REAL** |
| **Test 7** | 고의 반픽셀 격자 오프셋, 잘못된 CRS·분류체계·불일치 버전은 비교 전 검사에서 검출된다. | `test_07_preflight_detects_offset_crs_and_schema_mismatch` | 10m 격자의 5m 반픽셀 시프트(`transform`), CRS 불일치(UTM 48S vs WGS84), 너비/높이 불일치, `DatasetIdentity` 버전 불일치가 사전 점검(`assert_aligned`)에서 정확히 거부(`ValueError`)됨을 입증. | **VERIFIED_REAL** |
| **Test 8** | 자료 없는 연도를 요청하면 최신연도로 자동 대체하지 않는다. | `test_08_missing_year_returns_explicit_no_data` | 2020, 2021, 2023년 자료만 존재하는 환경에서 결측 연도(2022, 2024, 2025)가 `missing_years`로 명시 분리되며, 미존재 연도 요청 시 최신 연도(2023)로 조용히 대체되지 않고 `KeyError` 발생 검증. | **VERIFIED_REAL** |
| **Test 9** | 빠른 연도 전환·네트워크 지연 시 레이어 연도와 KPI 연도가 엇갈리지 않는다. | `test_09_rapid_year_toggle_race_condition_protection` | 2020 $\to$ 2021 $\to$ 2023 급속 전환 및 지연 역전 상황에서 시퀀스 토큰 기반 상태 관리자가 지연된 이전 패킷(2020, 2021)을 파기하고 최신 연도(2023)로 레이어와 KPI를 원자적 동기화함을 검증. | **VERIFIED_REAL** |
| **Test 10** | TIME별 캐시 분리와 스타일 변경 후 캐시 갱신이 검증된다. | `test_10_time_cache_isolation_and_style_invalidation` | 연도/시점별 타일 캐시 키 분리 확인 및 팔레트 스타일(SLD/CSS) 변경 시 즉시 새 타일로 무효화·갱신(파란색 $\to$ 청록색 반영) 검증. | **VERIFIED_REAL** |
| **Test 11** | 제한자료 타일·통계·원본 다운로드에 동일 접근정책이 적용된다. | `test_11_uniform_access_policy_for_restricted_data` | 비인가 사용자의 경우 타일 WMS, 통계 API, 원본 다운로드 3대 엔드포인트 모두 동일하게 거절(`PermissionError`)되며 백도어 유출이 발생하지 않음을 검증. | **VERIFIED_REAL** |
| **Test 12** | 원본 없는 승인·정확도·면적 수치를 화면에 넣지 않는다. | `test_12_no_unbacked_metrics_without_raw_verification` | 독립 참조자료 검증(`expert_independent`) 증빙 없이는 `Approved` 승인 전이가 원천 차단되며, 합성 모델의 운영 승인 신청 거부 및 임의 시안 수치 사용 차단 검증. | **VERIFIED_REAL** |
| **Test 13** | 반텐/서자바의 작은 자료가 First Group 6개 주 전체 결과로 표시되지 않는다. | `test_13_banten_west_java_small_aoi_not_blown_up_to_6_provinces` | 반텐 국지 패치(~6.55 km²)를 6개 주 전체(~100,000+ km²) 결과로 신청 시 공간 범위(BBOX) 불일치 감지에 의한 `ValueError` 거절 검증. | **VERIFIED_REAL** |
| **Test 14** | 실제 입력·출력·코드버전·테스트 명령·실행 환경·미완료 조건이 보고된다. | `test_14_transparency_report_generation` | 실행 환경(Python 3.11.9, Windows, rasterio 1.4.4, pytest 9.1.1), 14개 시험 전수 통과, 미완료 조건(현지 BIG 지상정답 대조 등)을 투명하게 수록한 `acceptance-test-results.json` 자동 발행 검증. | **VERIFIED_REAL** |

---

## 3. 검증 환경 및 실행 결과

```powershell
$env:PYTHONPATH="backend;."
pytest tests/test_lcluc_codex_acceptance.py -v
```

### 실행 로그 요약:
```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: E:\GeoAI–MLOps–SDSS
plugins: anyio-4.15.1
collected 14 items

tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_01_service_disconnect_fails_without_random_grid PASSED [  7%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_02_pixel_colors_match_legend_without_interpolation PASSED [ 14%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_03_coordinate_pixel_query_matches_source_rasters PASSED [ 21%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_04_mock_4x4_acceptance_matrix PASSED [ 28%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_05_nodata_strictly_excluded_from_transition_matrix PASSED [ 35%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_06_statistics_invariant_under_zoom_and_swipe PASSED [ 42%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_07_preflight_detects_offset_crs_and_schema_mismatch PASSED [ 50%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_08_missing_year_returns_explicit_no_data PASSED [ 57%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_09_rapid_year_toggle_race_condition_protection PASSED [ 64%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_10_time_cache_isolation_and_style_invalidation PASSED [ 71%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_11_uniform_access_policy_for_restricted_data PASSED [ 78%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_12_no_unbacked_metrics_without_raw_verification PASSED [ 85%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_13_banten_west_java_small_aoi_not_blown_up_to_6_provinces PASSED [ 92%]
tests/test_lcluc_codex_acceptance.py::TestLCLUCCodexAcceptance::test_14_transparency_report_generation PASSED [100%]

======================= 14 passed in 2.27s =======================
```

---

## 4. 미완료 조건 및 향후 권고 사항 (Pending Conditions)

1. **인도네시아 First Group 6개 주 전역 위성영상 추론 (`PLANNED`)**:
   - South Sulawesi, Gorontalo, Southeast Sulawesi, Banten, West Java, East Java 전역에 대한 Sentinel-2 시계열 추론은 연차별 구름 마스킹 합성(Unit 336) 완료 후 순차 처리 예정.
2. **독립 과학적 정확도(Ground Truth) 검증 (`IMPLEMENTED_UNVERIFIED`)**:
   - Test 4의 모의 4×4 검증은 행렬 분해 및 화소 보존의 **알고리즘적 무결성**을 검증한 것이며, 실제 인도네시아 지형에 대한 과학적 분류 정확도는 BIG(인도네시아 지리공간정보청) 공식 참조자료 대조를 통해 검증되어야 함.
3. **GeoServer 클러스터 분산 프로덕션 배포 (`TESTED_SYNTHETIC`)**:
   - 현재 로컬 및 Staging 환경에서 WMS/XYZ 타일 렌더러 동작 확인 완료. 컨소시엄 인프라 승인 후 Kubernetes 분산 환경으로 확장 예정.
