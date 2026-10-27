# G2 — 432개 주·월 inventory 감사

## 상태

- source inventory: `VERIFIED_REAL`
- province coverage: `BLOCKED_NOT_MEASURED`
- schema: `4.1`
- source SHA-256: `0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658`

운영 `annual-window-report.json`을 읽기 전용으로 검증한 결과는 6개 주 × 6년 × 12개월 = 432셀, patch row 1,779개, 고유 scene 107개, 품질 적격 1,407개, 품질 미흡 372개, patch가 존재하는 주·월 77개다. 이 값은 파일에 기록된 inventory의 수와 상태를 뜻한다.

## coverage 해석

패치별 `valid_pixel_ratio`의 평균은 행정경계 전체 커버리지가 아니다. 각 패치는 서로 겹칠 수 있고 주 경계 전체를 덮지 않을 수 있다. 따라서 CSV의 `valid_coverage_pct`와 `outside_footprint_pct`는 모두 `null`이며 `measurement_status=BLOCKED_NOT_MEASURED`다.

측정하지 않은 셀을 정상 또는 품질 저하로 분류하지 않는다.

| 구분 | top-level | 주별 rollup 합계 | 연도별 rollup 합계 |
|---|---:|---:|---:|
| nominal | 0 | 0 | 0 |
| degraded | 0 | 0 | 0 |
| unclassified | 432 | 432 | 432 |

전체 432셀 행은 `02_432_province_month_availability_audit.csv`에 있다. 행정경계 coverage를 만들려면 SHA가 고정된 EPSG:6933 이진 province mask mosaic와 경계가 필요하다. 현재 운영 TIFF inventory만으로는 이 계약을 만족하지 않는다.

## 철회한 표현

기존 문서의 22개 nominal/14개 degraded, 주별 평균 유효 coverage, 우기 288셀이 구름 80~90% 때문에 정책상 모두 제외되었다는 설명은 현재 source에서 검증되지 않아 철회했다. 건기/우기 표시는 월 분류 정책일 뿐, 개별 셀의 과학적 배제 사유를 증명하지 않는다.
