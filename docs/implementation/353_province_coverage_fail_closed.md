# Unit 353/354 — 행정경계 커버리지·복구율 fail-closed 교정

상태는 세 층으로 구분한다.

- 운영 inventory 1,779행과 SHA 확인: `VERIFIED_REAL`
- EPSG:6933 이진 mask fixture와 API 계약: `TESTED_SYNTHETIC`
- 운영 36개 주·연도 coverage mask 합집합: `BLOCKED`
- 운영 before/after/boundary 동일-grid 전이 mask: `BLOCKED`

## 문제와 최종 동작

과거 문서의 49.47%→99.23%, 복구율 98.50%, 신규 56,590,468ha는 실제 전후 마스크 차집합에서 나온 값이 아니었다. 이 수치와 `VERIFIED_REAL` 표시는 철회했다. 패치별 유효 비율, 패치 수, 두 시점의 집계 면적 차이는 `after AND NOT before` 화소 집합을 증명하지 못한다.

`province_year_coverage.py`는 다음을 모두 만족해야 면적을 계산한다.

1. source와 boundary JSON, 모든 raster의 SHA-256이 일치한다.
2. source schema는 `province-coverage-source/1.0`, boundary schema는 `province-boundaries/1.0`이다.
3. boundary는 명시된 EPSG:4326이고 정확히 요청 범위를 포함한다. 중복 province와 patch ID는 차단한다.
4. quality mask는 EPSG:6933, 단일 band, north-up, NoData 미설정, 값 `{0,1}`, 의미 `BINARY_OBSERVED_0_1`, 정책 `quality-mask/1.0`이어야 한다.
5. cause mask는 같은 grid에서 값 `{0,1,2,3}`만 허용한다. 1/2/3은 cloud/shadow/nodata이며 관측 화소 또는 경계 밖에 원인 코드를 둘 수 없다.
6. 겹치는 footprint로 이중 계상될 가능성, 면적 불변식 위반, 알려지지 않은 quality status는 즉시 예외로 중단한다.
7. `COVERAGE_COMPLETE`는 outside, cloud, shadow, nodata, not-measured가 모두 허용 오차 이하이고 observed가 경계 전체를 덮을 때만 가능하다.

면적은 경계와 raster 모두 EPSG:6933에서 계산한다. UTM·Web Mercator raster 면적을 EPSG:6933 경계 면적과 섞는 경로는 제거했다. 운영 quality TIFF는 현재 이 명시 계약에 맞춘 행정경계 mosaic가 아니므로 운영 36셀 실측은 아직 수행할 수 없다.

## 복구율 계약

`recovery_rate_engine.py` schema `4.1`은 두 종류 값을 분리한다.

- `aggregate_net_observed_area_change_ha`와 `aggregate_net_coverage_change_pct_point`: 엄격 검증된 before/after coverage 보고서의 집계 순변화다. 새로 복구된 화소가 아니라 별도 집계 상태다.
- `newly_recovered_area_ha`와 `recovery_rate_pct`: 36셀 각각의 pinned before/after/boundary mask가 같은 EPSG:6933 grid일 때만 계산한다.

mask가 없으면 집계 순변화가 있더라도 전체 recovery 상태는 `BLOCKED`, 이유는 `MISSING_SAME_GRID_OBSERVED_MASK_TRANSITIONS`, 복구량과 복구율은 `null`이다. mask가 있으면 `(~before) & after & boundary`로 신규 복구 면적을 계산하고, `(~before) & boundary`를 분모로 사용한다. mask 면적과 coverage 보고서 면적이 일치하지 않으면 중단한다.

## 432셀 inventory 계약

`province_month_coverage_audit.py` schema `4.1`은 운영 source의 SHA, 정책 버전 `guarded-deficit-1024`, 실행 상태, scope, timestamp/year, split, scene/patch ID, quality status, quality SHA 형식을 검증한다. 실제 확인 값은 1,779 patch rows, 107 unique scenes, 품질 적격 1,407, 미흡 372, 활성 주·월 77이다.

이 수치는 inventory 증거다. 432셀의 `valid_coverage_pct`와 `outside_footprint_pct`는 `null`, `measurement_status`는 `BLOCKED_NOT_MEASURED`다. 측정하지 않은 셀을 nominal 또는 degraded로 분류하지 않으며 top과 rollup 모두 nominal=0, degraded=0, unclassified=전체 셀로 일치한다.

## API

`GET /v1/mlops/recovery-rate`는 현재 다음 versioned envelope를 반환한다.

```json
{
  "schema_version": "4.1",
  "status": "blocked",
  "reason_code": "MISSING_EXPLICIT_PINNED_BEFORE_AND_AFTER_COVERAGE_REPORTS",
  "recovery_summary": {
    "evidence_status": "BLOCKED",
    "total_newly_recovered_ha": null,
    "mean_recovery_rate_pct": null
  }
}
```

HTTP 200은 계약 응답 성공만 뜻한다. 과학 지표 성공을 뜻하지 않는다. 실행 중 서버와 브라우저 반영은 Root의 재시작·실브라우저 검증 전까지 별도 상태다.

## 시험 근거와 제한

집중·관련 회귀 41건이 통과했다. 이 시험은 36셀 scope, invalid cause 차단, 완전 관측에서만 `COVERAGE_COMPLETE`, SHA 불일치, 원인 미측정, 비이진 quality mask, NoData 불일치, 중복 patch, unknown quality status, 운영 432 inventory, rollup 분류 일치, aggregate/recovery 분리, 동일-grid 차집합, boundary pin, 셀 불변식, blocked API envelope를 검증한다. G2/G5 CLI도 각각 exit 0으로 null-safe 출력을 확인했다.

결정적 raster 시험은 `TESTED_SYNTHETIC`이다. 실제 운영 before/after 전이 mask, 운영 36셀 coverage, 실제 복구율은 없다. `evidence/integration/unit353-coverage-contract-20261021/real-smoke.json`은 이전 알고리즘이 UTM pixel 면적과 EPSG:6933 경계를 혼합해 만든 기록이다. 원파일은 provenance 보존을 위해 남겼지만 현재 알고리즘으로 재검증하지 않았고 `VERIFIED_REAL` 근거에서 철회했다. 운영 source와 ledger는 읽기만 했고 쓰지 않았다.

## 시험 저장소 격리 사고와 복구

초기 MLOps router 회귀 시험이 workspace의 `data/catalog.sqlite3`를 사용해 2026-10-21 시험 retrain/approval 행을 기록했다. Root는 API PID 42092를 중지하고 사고 시점 파일과 삭제 대상 목록을 먼저 보존한 뒤, kind/id/body가 모두 일치하는 24행만 단일 트랜잭션으로 삭제했다. 레코드는 53행에서 29행으로 돌아왔고 대상 잔여는 0, SQLite `integrity_check`는 `ok`다. 삭제 뒤 raw SHA-256은 `d08418826b858deccad972d5326cfaa2122f56aa13faef0fc1e3628650fdfc45`로, SQLite 파일의 물리 바이트 동일성은 복원되지 않았다. 포렌식 스냅샷과 복구 결과는 `evidence/integration/unit355-catalog-incident-20261021/`에 보존했다.

관련 router 시험은 현재 `TemporaryDirectory` 안의 `Store`와 복사한 source fixture만 사용한다. 최종 41건 회귀는 이 격리 교정 뒤 통과했으며 workspace catalog를 다시 열거나 쓰지 않았다.
