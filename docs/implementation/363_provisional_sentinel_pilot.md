# Unit 363 — GISTARU 생략 결정·BIG 임시 경계·Sentinel-2 SCL pilot

## 1. 결과

사용자가 GISTARU 접속 불가로 인한 지속 차단을 원하지 않아, 권위 경계·GISTARU 교차검증을 계속 요구하는 기존 경로와 별개로 `PROVISIONAL_REAL` pilot 경로를 추가했다. 이 경로는 GISTARU를 `SKIPPED_BY_USER_DECISION`으로 기록하고 BIG 공개 경계 SHA를 `PROVISIONAL_BIG_BASELINE`으로 고정한 뒤, 단 한 건의 Sentinel-2 SCL pilot만 허용한다.

실제 원격 수집·1차 SCL QA·36셀 1 km inventory mosaic 갱신·전수 검증은 완료됐다. 경계 승인, 대량 수집, 학습, 정확도 확정, 배포는 허용하지 않았다.

## 2. Gate 정책

- 기존 `VERIFIED_REAL`: 승인 경계와 GISTARU 비교 증거를 계속 요구한다.
- 신규 `PROVISIONAL_REAL`: 사용자 생략 결정 JSON, 그 결정과 결속된 BIG 경계 SHA, 기존 실 SCL mosaic pin을 요구한다.
- 허용: 36셀 공백 우선순위, 중복·예산·저장공간 preflight, 단일 SCL pilot, SCL QA, 1 km inventory 갱신.
- 금지: 권위 경계 승인 주장, GISTARU match 주장, 대량 수집, 학습, 운영 배포.

결정 pin은 `evidence/integration/unit363-provisional-sentinel-pilot-20261027/cross-check-decision.json`, BIG 임시 경계 SHA는 `233c034c0b6a777799b14ab5451afedc3ece9abbe836b28e59292a18f4c2a423`이다.

## 3. 36셀 우선순위와 preflight

`OUTSIDE_FOOTPRINT` 픽셀 수를 내림차순으로 정렬했다. 최우선 셀은 East Java 2023이며, 48,031 경계 픽셀 중 47,837이 기존 실 SCL 창 밖이었다. 기존 범위와 경계에서 1 km Manhattan 격자 61칸 떨어진 `OUTSIDE_FOOTPRINT` 픽셀을 pilot 중심으로 선택했다.

preflight 실측:

- 기존 STAC item ID 127개를 inventory하고 live 검색 후 scene ID를 다시 비교했다.
- 실행 중 collector는 0이었고 execution lock은 없었다.
- 기존 원장에 이전 작업의 pending 예약 2건이 있었지만, 서로 다른 Banten/West Java 2023 key이며 복구·환불·재실행하지 않았다.
- 신규 전역 예산 잔액은 1,799,757,940B, E: 여유 공간은 1,989,271,117,824B였다.
- pilot 보수적 예약액은 33,554,432B이며 preflight은 PASS했다.

## 4. 실제 Sentinel-2 pilot와 SCL QA

- 셀: East Java / 2023
- scene: `S2A_MSIL2A_20230905T023531_R089_T49MFM_20230905T081430`
- STAC cloud metadata: 0.945937%
- SCL: 20 m, 256×256 = 65,536 pixel
- SCL histogram: class 4=37,533, class 5=27,954, class 7=49
- clear: 65,536/65,536 = 100%, cloud/shadow/nodata=0
- QA: `OBSERVATION_ELIGIBLE`
- 계측된 COG Range 본문: 196,608B
- 로컬 `raw-SCL.tif`: 4,872B
- STAC/SAS/HEAD 본문은 Range 계측 범위 밖이므로 원장은 예약액 33,554,432B 전액을 보수적으로 정산했다.
- pilot batch는 `settled`, rate-limit circuit는 false, execution lock은 해제됐다.

## 5. mosaic 갱신

East Java 2023 셀은 source asset 2→3, observed 194→219(+25), `OUTSIDE_FOOTPRINT` 47,837→47,812(-25)로 변경됐다.

전체 36셀은 source asset 120→121, observed 10,032→10,057, observed 0.892862%→0.895087%로 변경됐다. 갱신 후 gap은 1,113,521, 원인은 CLOUD 607, SHADOW 374, NODATA 0, OUTSIDE_FOOTPRINT 1,112,540이다.

이 결과는 EPSG:6933·1 km 수집 inventory이며 10/20 m 최종 과학 제품이 아니다.

## 6. 구현·검증

- Gate/planner: `backend/app/ml/province_year_gap_acquisition_planner.py`
- pilot/preflight/collector: `backend/app/ml/province_year_pilot_collector.py`
- mosaic execution metadata/validator: `backend/app/ml/province_year_evidence_builder.py`
- CLI: `scripts/plan_province_year_gap_acquisition.py`, `scripts/run_provisional_sentinel_pilot.py`, `scripts/validate_province_year_evidence.py`
- tests: `tests/test_province_year_gap_acquisition_planner.py`, `tests/test_province_year_evidence_builder.py`, `tests/test_province_year_pilot_collector.py`

검증 결과:

- 29 PASS / 105 warnings / 90.18초
- 독립 validator: 36셀, 121 unique SCL, 72 TIFF, pin/grid/CRS/domain/경계 밖 0/gap 전수 원인 PASS
- `compileall`: PASS
- `git diff --check`: PASS
- 실학습·실예측·사람 승인·승격·운영 배포: 0

최초 CLI는 모든 산출물과 원장 정산을 완료한 후 Windows CP949 출력에서 workspace 경로의 특수 dash를 인코딩하지 못해 종료코드가 실패했다. CLI stdout/stderr를 UTF-8로 교정했고 산출물·원장·잠금 상태를 독립 재검증했다.

## 7. 증거와 남은 Gate

증거: `evidence/integration/unit363-provisional-sentinel-pilot-20261027/`

남은 핵심은 승인된 현행 경계다. 현 BIG 경계는 pilot 기준일 뿐이며 최종 통계·학습·운영 기준이 아니다. 다음은 pilot 효과·예산 검토 후 소규모 batch 확대 여부를 사람이 승인하고, 별도로 경계 승인을 확보하는 순서다.

UI 변경은 하지 않았다. 이 단위는 명시적 CLI pilot·원장·GeoTIFF 증거 작업이며 기존 화면/API 계약을 바꾸지 않았다. 로컬 API 8002, UI 5174, WMS 8088의 HTTP 200은 재확인했지만, 갱신 mosaic가 신규 화면 레이어로 연결됐다고 주장하지 않는다.

## 8. Unit 365 후속

pilot 효과를 근거로 2048×2048 SCL 창 3건의 guarded batch를 허용하고 실행했다. Unit364 transient STAC 실패 뒤 제한 재시도를 추가했으며 Unit365에서 3건 모두 수집·QA·mosaic 갱신에 성공했다. 상세 수치와 자동화 경계는 `docs/implementation/365_automated_gap_collection_batch.md`를 따른다. 상태는 전체 완료가 아니라 `AUTOMATED_BATCH_COMPLETED_MORE_GAPS_REMAIN`이고 재학습·배포는 계속 승인형이다.
