# G5 — 구름·결측 복구율 보고서

## 현재 상태

- schema: `4.1`
- recovery: `BLOCKED`
- reason: `MISSING_EXPLICIT_PINNED_BEFORE_AND_AFTER_COVERAGE_REPORTS`
- `newly_recovered_area_ha`: `null`
- `mean_recovery_rate_pct`: `null`

운영 경로에는 SHA가 고정된 before coverage 보고서, after coverage 보고서, 36셀 동일-grid before/after/boundary mask가 없다. 그러므로 실제 신규 복구 면적, 잔여 결측 면적, 복구율을 산출하지 않는다.

## 계산 가능 조건

각 주·연도 셀마다 EPSG:6933, 동일 shape/transform, 단일 band, NoData 미설정, 값 `{0,1}`인 세 mask가 필요하다.

```text
newly_recovered = (~before_observed) & after_observed & boundary
before_missing  = (~before_observed) & boundary
still_missing   = (~after_observed) & boundary
recovery_rate   = area(newly_recovered) / area(before_missing) * 100
```

before/after 집계 coverage 보고서만 제공된 경우에는 순변화(`aggregate_net_*`)를 별도 필드로 표시할 수 있지만, 이것을 신규 복구 면적이나 복구율로 부르지 않는다. 예를 들어 다른 위치에서 관측 화소가 사라지고 생기면 집계 합계는 같아도 실제 전이는 존재한다.

## 철회

이전 보고서의 49.47%→99.23%, +49.76%p, 56,590,468ha, 98.50%, 36/36 품질 합격, `VERIFIED_REAL` 주장은 동일-grid mask 증거 없이 생성되어 모두 철회했다. 실제 학습, 실제 합성 실행, 실제 복구 mask 게시, 과학 검증을 뜻하지 않는다.

동일-grid 결정적 fixture에서 차집합 공식을 시험한 상태는 `TESTED_SYNTHETIC`이다. 운영 실측은 `BLOCKED`다.
