# Unit 365 — Sentinel-2 누락 수집 자동 batch와 승인형 MLOps 경계

## 1. 쉬운 결과

Sentinel-2 Scene Classification Layer(SCL) 누락 구간을 **한 건씩 수동 처리하지 않고**, 공백 감시 → 우선순위 계획 → 중복·예산·저장공간 점검 → 수집 → SCL 품질검사 → 36셀 observed/cause mosaic 재생성·검증까지 한 번에 수행하는 guarded batch를 구현하고 실제 실행했다.

pilot 결과를 바로 대량 수집으로 확대하지 않고 **2048×2048 SCL 창 3건**을 첫 허용 batch로 결정했다. 첫 Unit 364 실행은 STAC 연결이 끊겨 0건으로 안전 중지됐고, 새 batch ID와 최대 3회 transient retry 정책을 적용한 Unit 365에서 3건 모두 성공했다. 재학습·모델 승격·배포는 자동화 범위에 포함하지 않았으며 계속 사람 승인형이다.

현재 상태는 `AUTOMATED_BATCH_COMPLETED_MORE_GAPS_REMAIN`이다. 자동화가 동작했다는 뜻이지 누락 수집 전체 완료를 뜻하지 않는다.

## 2. batch 규모 결정

- pilot: SCL 256×256 한 건, observed +25 pixel.
- 최초 확대: 면적 64배인 2048×2048 창 3건.
- 보수적 상한 예약: 건당 48 MiB, batch 최대 144 MiB(150,994,944B).
- 중지 조건: 첫 asset/QA 실패, HTTP 429, 3번째 STAC 실패, 예산·디스크 부족, lock 충돌, mosaic 검증 실패.
- 대상 정책: 같은 batch에서 서로 다른 province-year 셀 3개. 실제 최상위가 모두 East Java였지만 2021·2023·2024로 서로 다른 셀이다.

3건을 택한 이유는 pilot 한 건만으로 전송 안정성과 실제 공간 이득을 대량 외삽하지 않기 위해서다. 성공 후에도 다음 batch 상한을 자동으로 키우지 않는다. 현재 1 km inventory의 남은 규모가 매우 크므로 반복 2048 창보다 MGRS full-tile 또는 체계적 타일링 전략을 먼저 비교해야 한다.

## 3. 자동화 범위와 안전장치

`backend/app/ml/province_year_collection_orchestrator.py`의 `run_automated_collection_batch()`가 다음을 순서대로 수행한다.

1. 사용자 결정, BIG 임시 경계 SHA, 시작 mosaic SHA, GISTARU 생략 결정 pin 검증
2. `OUTSIDE_FOOTPRINT` 기준 36셀 감시·우선순위 재계산
3. 중복 scene, 활성 collector, 전역 execution lock, rate-limit circuit, 원장 잔액, 디스크 검사
4. 전역 lock 아래 Sentinel-2 SCL 3건 순차 수집
5. 각 SCL histogram·clear/cloud/shadow/nodata QA
6. 36셀 EPSG:6933·1 km observed/cause mosaic 재생성
7. pin, 동일 격자, CRS, value domain, 경계 밖 0, 모든 gap 원인 분류 검증
8. completion과 원장 정산 기록

STAC 검색은 transient 오류에 한해 최대 3회 재시도하고 HTTP 429는 즉시 shared circuit를 연다. batch는 첫 실패에서 멈춘다. 요청 간격·회로 설정은 예외가 발생해도 `finally`에서 원상 복구된다.

이 구현은 **한 번 호출되는 guarded batch 자동화**다. 무기한 무인 스케줄러를 켜거나 다음 batch를 자동 승인하지 않는다. 다음 batch는 최신 mosaic를 시작 pin으로 삼는 별도 명시 결정이 필요하다.

## 4. 실제 실패와 재시도

Unit 364 결정 SHA는 `ab7559b77687a3bbef98ae3e9799a3212aac9a25b0bb12b86a29fff12144e8ea`다. 첫 STAC search에서 `RemoteDisconnected`가 발생해 download 0, 후속 2건 미시작, lock 해제로 종료했다. 측정하지 못한 외부 요청 비용을 축소해 보이지 않도록 48 MiB 예약액 50,331,648B는 전액 정산했다.

Unit 365 재시도 결정 SHA는 `ea42c7fb09221086bc082f5c1be4140cedf1b69b83bda6540273f8598f22533d`다. 새 batch run ID `unit365-auto-retry1`을 써서 이전 실패 key를 재사용하지 않았다.

## 5. 실제 수집·QA 결과

| 셀 | Sentinel scene | clear | 전송 본문 | 로컬 SCL | 원장 charge | observed 증가 |
|---|---|---:|---:|---:|---:|---:|
| East Java 2021 | `S2B_MSIL2A_20210811T023549_R089_T49MFM_20210811T163939` | 97.4523% | 851,968B | 446,308B | 978,712B | +1,606 |
| East Java 2023 | `S2A_MSIL2A_20230905T023531_R089_T49MEM_20240916T145247` | 99.5910% | 917,504B | 421,689B | 1,226,601B | +1,640 |
| East Java 2024 | `S2B_MSIL2A_20240726T023529_R089_T49MFM_20240726T062840` | 99.9855% | 786,432B | 435,375B | 942,303B | +1,645 |

세 건 모두 `OBSERVATION_ELIGIBLE`이다. batch 실제 원장 charge는 3,147,616B이며 예약 상한 150,994,944B 안이다. Unit 364 실패 charge까지 반영한 현재 추가 예산 잔액은 1,712,724,244B, 원장 SHA는 `2b98eadb6cff1d586fe136db2b151787ad6b8a0fa59389bf6a3d981a98065862`다. 기존 pending Banten/West Java 2023 두 건은 건드리지 않았다.

## 6. mosaic 갱신과 남은 규모

- source asset: 121 → 124 unique SCL
- observed: 10,057 → 14,948, `+4,891`
- observed 비율: 0.895087% → 1.330393%
- `OUTSIDE_FOOTPRINT`: 1,112,540 → 1,107,605, `-4,935`
- 전체 gap: 1,108,630
- 기타 원인: CLOUD 613, SHADOW 412, NODATA 0
- 갱신 manifest SHA: `9259b3d0d6c5da47f616b3b6ec9b45b0c8cfccf56e0095beb0a23ad1f6b93ae3`

단순히 창당 약 1,600개의 1 km pixel을 회복한다고 놓으면 초기 공백 전체에는 약 696개, 현재 잔여에는 약 693개 2048 창이 필요하다. 이 값은 해안선, MGRS 경계, 구름, 중복을 무시한 거친 계획치이며 과학적 완전성 증거가 아니다. 따라서 “누락본 수집 완료” 상태로 올리지 않는다.

## 7. 검증 증거와 상태

- `VERIFIED_REAL`: Sentinel-2 SCL 원격 수집 3건, SCL QA, 원장 정산, lock 해제, 36셀 mosaic 재생성.
- `VERIFIED_REAL`: 독립 validator가 36셀, 124 unique asset, pin/grid/EPSG:6933/domain/경계 밖 0/gap 전수 원인을 통과했다.
- `TESTED_SYNTHETIC`: 관련 회귀 33 PASS / 105 warnings / 87.82초.
- `BLOCKED`: BIG 임시 경계의 관할 기관·통계 사용 승인.
- `BLOCKED`: 전체 native-resolution 수집 완전성.
- `BLOCKED_REQUIRES_HUMAN_APPROVAL`: 재학습, 모델 승격, 배포.

API 8002, UI 5174, WMS 8088은 각각 HTTP 200이다. 이번 단위는 내부 CLI·evidence 계약이며 새 UI/API 계약을 만들지 않았으므로 web UI 변경은 필요하지 않다. 실행 중 화면에 신규 mosaic 레이어가 자동 연결됐다고 주장하지 않는다.

## 8. 파일과 다음 Gate

- orchestration: `backend/app/ml/province_year_collection_orchestrator.py`
- collector: `backend/app/ml/province_year_pilot_collector.py`
- CLI: `scripts/run_provisional_collection_batch.py`
- tests: `tests/test_province_year_collection_orchestrator.py`, `tests/test_province_year_pilot_collector.py`
- 실패 증거: `evidence/integration/unit364-automated-collection-batch-20261027/`
- 성공 증거: `evidence/integration/unit365-automated-collection-retry-20261027/`

다음 Gate는 최신 mosaic pin으로 full-tile 대 반복-window 효율을 비교하고, 새 batch 상한을 명시적으로 결정한 뒤 같은 예산·중복·429·QA·mosaic 검증을 적용하는 것이다. 경계 승인이 확보되면 승인 SHA로 36셀 inventory를 다시 만들어야 한다.

## 9. Unit 366–367 후속

동일하게 고정된 East Java 2021/2023/2024 장면을 5490×5490 전체 SCL 타일로 확장해 세 건을 실제 수집했다. observed는 추가로 +22,755, 전체 비율은 3.355619%가 됐으며, 대응 2048 창보다 Range 바이트당 관측 증가 효율이 이 세 표본에서 약 36.4% 높았다. 상세는 `docs/implementation/367_full_tile_strategy_and_batch.md`를 따른다. 전체 완료·타 주 일반화·자동학습·자동배포는 주장하지 않는다.
