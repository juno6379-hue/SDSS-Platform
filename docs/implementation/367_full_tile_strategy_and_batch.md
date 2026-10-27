# Unit 366–367 — Sentinel-2 SCL 전체 타일 전략 pilot와 2건 확대 batch

## 1. 결과

2048×2048 부분 창을 반복하는 방식과 Sentinel-2 MGRS SCL 전체 타일(5490×5490, 20m)을 실제 비용·관측 증가량으로 비교했다. East Java 2021 전체 타일 1건을 Unit366 pilot으로 실행한 뒤, 검증 결과를 근거로 East Java 2023·2024 두 건만 추가 허용해 Unit367 batch로 순차 실행했다.

세 건 모두 다운로드, SCL QA, 원장 정산, execution lock 해제, 36셀 EPSG:6933·1km observed/cause mosaic 재생성, 독립 validator까지 성공했다. 학습·모델 승격·배포는 실행하지 않았다.

최종 상태는 `FULL_TILE_PILOT_AND_BATCH2_COMPLETED_MORE_GAPS_REMAIN`이다. 전체 누락 수집 완료가 아니다.

## 2. 구현

- `backend/app/data/service.py`
  - `read_cog_full_tile()`을 추가했다.
  - 단일 band·CRS·최대 8192×8192·전송량 상한을 검증한다.
  - 기존 `HTTPRangeReader`의 실제 Range 본문 계측과 HTTP 429/오류 원인 보존을 그대로 사용한다.
- `backend/app/ml/province_year_full_tile_collector.py`
  - 사용자 결정, BIG 임시 경계 SHA, 최신 mosaic SHA, 기존 검증 window report SHA와 scene ID를 모두 고정한다.
  - preflight → 64MiB 예약 → 전체 SCL 읽기 → QA → 원장 정산 → mosaic → validator 순서로 실행한다.
  - 실패 시 예약 전액 보수 정산, 첫 실패 중지, 학습·배포 false를 강제한다.
- `scripts/run_provisional_full_tile_pilot.py`
  - 모든 입력 pin을 명시하는 one-shot CLI다.
- `tests/test_data_service.py`, `tests/test_province_year_full_tile_collector.py`
  - 전송 오류 계측 보존, 정책값·pin drift·batch 증가·학습/배포 승인 경계를 검사한다.

## 3. 실제 수집 결과

| 연도 | scene/tile | 전체 타일 clear | Range 본문 | 원장 charge | observed 증가 |
|---:|---|---:|---:|---:|---:|
| 2021 | `S2B...T49MFM...163939` | 72.5252% | 3,399,268B | 3,399,668B | +7,033 |
| 2023 | `S2A...T49MEM...145247` | 99.5867% | 2,886,467B | 2,886,869B | +8,211 |
| 2024 | `S2B...T49MFM...062840` | 77.0732% | 2,431,938B | 2,432,340B | +7,511 |

2021·2024 전체 타일의 clear 비율에는 위성 swath 밖 NoData 5,985,608 / 6,057,587 pixel이 포함된다. 이를 저품질 cloud로 바꾸지 않고 NODATA 원인으로 보존했다. 따라서 전체 타일 clear 비율과 기존 256 학습 patch의 최종 유효 80% 기준은 같은 지표가 아니다.

전체 타일 세 건의 합계는 Range 8,717,673B, 원장 charge 8,718,877B, observed +22,755다. 대응하는 기존 2048 창 세 건은 Range 2,555,904B, observed +4,891이었다. 전체 타일은 전송량 3.410798배로 observed 4.652423배를 확보해, 이 표본에서는 바이트당 관측 증가 효율이 1.364028배였다.

다만 세 표본이 모두 East Java이므로 다른 주에서도 같은 효율이라고 확정하지 않는다.

## 4. mosaic와 장부

- observed: 14,948 → 37,703, `+22,755`
- observed 비율: 1.330393% → 3.355619%
- `OUTSIDE_FOOTPRINT`: 1,107,605 → 1,079,260, `-28,345`
- 최종 gap: 1,085,875
- 원인: CLOUD 1,377 / SHADOW 901 / NODATA 4,337 / OUTSIDE 1,079,260
- source assets: 124 → 127 unique SCL
- 최종 manifest SHA: `8285cffc8e151ee6bc79abde1ab50ad1eeebedb3aac6977f0bbfb0cdef789a11`
- 원장 잔액: 1,704,005,367B
- 원장 SHA: `97f04bbba9e1e8c6e8ed2e6a58592a8c7e1ddefe6775bc2b770a8da7e1da8448`
- 기존 pending Banten/West Java 2023 두 건: 변경 없음
- active collector 0 / execution lock 없음 / rate-limit false

## 5. 검증

- 실제 원격 Sentinel-2 SCL 전체 타일: 3건 `VERIFIED_REAL`
- 독립 validator: 36셀, 127 unique asset, pin/grid/EPSG:6933/domain/경계 밖 0/gap 전수 원인 PASS
- 관련 회귀: 45 PASS / 88 warnings / 11 subtests PASS / 55.23초
- 서비스: API 8002, UI 5174, WMS 8088 HTTP 200
- training/deployment run: 0/0

이번 기능은 내부 수집 CLI와 evidence 계약이다. API/UI 상태·오류 계약을 바꾸지 않았으므로 web UI 변경은 필요하지 않다. HTTP 200은 신규 mosaic가 화면에 게시됐다는 증거가 아니다.

## 6. 다음 batch 결정

다음 확대 상한은 **전체 타일 6건**으로 권고한다. 그러나 아직 실행 승인 산출물이 아니라 `PLANNED_REQUIRES_PINNED_CANDIDATE_SELECTION_AND_PREFLIGHT`다.

실행 전 조건:

1. 최신 manifest에서 서로 다른 고공백 province-year 셀을 우선 선정한다.
2. 각 셀의 기존 로컬 STAC item·scene·source window SHA를 고정한다.
3. 이미 전체 타일로 확장한 scene/tile/year를 중복 제외한다.
4. 최대 384MiB를 사전 예약할 수 있어야 한다.
5. 첫 실패·HTTP429에서 전체 batch를 중지한다.
6. batch 종료 후 한 번만 mosaic를 재생성하고 독립 검증한다.
7. 재학습·승격·배포는 계속 사람 승인형으로 둔다.

현재 관측률 3.355619%는 권고 수집 목표 95%와 큰 차이가 있다. 95%는 아직 발주처·BIG 승인 인수기준이 아니라 운영 권고 목표이며, 승인 전 BIG 1km inventory 수치를 공식 관측률로 발표하지 않는다.

## 7. 증거

- Unit366: `evidence/integration/unit366-full-tile-strategy-pilot-20261027/`
- Unit367 item 1: `evidence/integration/unit367-full-tile-batch-item1-20261027/`
- Unit367 item 2: `evidence/integration/unit367-full-tile-batch-item2-20261027/`
- 합산: `evidence/integration/unit367-full-tile-batch-summary-20261027.json`
