# Unit 349/353/354 — 주·월 inventory와 복구율을 구분하는 법

## 쉬운 설명

파일이 많이 있다는 사실과 한 주 전체를 관측했다는 사실은 다르다. 현재 확인된 실제 값은 1,779개 patch row 중 1,407개가 품질 적격이라는 inventory다. 이 숫자만으로 “주 전체의 99.23%를 관측했다”거나 “결측의 98.50%를 복구했다”고 말할 수 없다.

현재 상태는 다음과 같다.

- 432개 주·월 표와 운영 source inventory: `VERIFIED_REAL`
- 행정경계 coverage: `BLOCKED_NOT_MEASURED`
- 동일-grid mask 차집합 코드와 fixture: `TESTED_SYNTHETIC`
- 운영 신규 복구 면적과 복구율: `BLOCKED`, 값 `null`

## 이론적 배경

집계 면적 증가는 복구 면적과 같지 않다. 전후 관측 면적이 각각 40ha와 60ha이면 순증가는 20ha다. 그러나 전 시점의 10ha가 사라지고 다른 곳 30ha가 새로 보였다면 실제 신규 관측은 30ha다. 위치가 있는 mask를 겹쳐야만 이 차이를 알 수 있다.

행정경계 내부에서 다음처럼 계산한다.

```text
신규 복구 = (전에는 미관측) AND (후에는 관측) AND 경계 내부
초기 결측 = (전에는 미관측) AND 경계 내부
복구율 = 신규 복구 면적 / 초기 결측 면적
```

면적 비교는 한 좌표계에서 해야 한다. 이 구현은 EPSG:6933 equal-area grid만 허용한다. UTM pixel 면적과 EPSG:6933 경계 면적을 섞거나 Web Mercator 면적을 실제 면적으로 취급하면 차단한다.

## 코드와 데이터 동작

`province_month_coverage_audit.py`는 운영 JSON의 SHA, 정책 버전, scope, 시간, split, 중복 patch ID, quality status를 검사한다. 결과는 inventory이며 coverage 필드는 null이다. 측정하지 않은 셀은 nominal이나 degraded가 아니라 unclassified다.

`province_year_coverage.py`는 source/boundary/mask SHA와 schema를 확인한다. quality mask는 `{0,1}`만, cause mask는 `{0,1,2,3}`만 허용한다. outside footprint, cloud, shadow, nodata, not-measured 중 하나라도 남으면 구체적인 `BLOCKED_*` 상태를 반환한다. 모두 0이고 observed가 경계를 완전히 덮을 때만 `COVERAGE_COMPLETE`다.

`recovery_rate_engine.py`는 두 coverage 보고서를 먼저 엄격 검증한다. 보고서만 있으면 집계 순변화는 `aggregate_net_*`에만 기록하며 recovery는 blocked/null이다. 36셀 모두에 동일-grid before/after/boundary mask가 있을 때만 `newly_recovered_area_ha`와 `recovery_rate_pct`를 계산한다.

`GET /v1/mlops/recovery-rate`의 HTTP 응답 자체는 정상적으로 반환되지만, 데이터 상태는 top-level `status=blocked`, `schema_version=4.1`, `reason_code`로 명시한다. 현재 실행 중 서버에 이 코드가 반영됐다는 뜻은 아니며 재시작과 브라우저 확인은 별도다.

## 테스트 증거

집중·관련 회귀는 41건을 통과했고 G2/G5 CLI는 각각 exit 0이었다. 다음 실패 조건을 확인한다.

- SHA, schema, boundary scope, 중복 patch/cell, unknown quality status 오류
- 비이진 quality mask, NoData 설정, 비 equal-area grid
- cause mask 격자와 의미 불일치
- observed+missing 또는 missing cause 합계 불변식 위반
- 동일-grid 전이 mask가 없는 recovery 요청

결정적 2×2 fixture에서는 36셀 전체에 대해 invalid cause가 남을 때 completion을 차단하고, 완전 관측일 때만 completion을 허용했다. 또 동일-grid mask에서 `(~before) & after`를 실제 계산했다. 이 결과는 `TESTED_SYNTHETIC`이며 운영 실측으로 확대하지 않는다.

## 발표 스크립트

> “현재 실제로 확인한 것은 432개 주·월 inventory와 1,779개 patch row입니다. 패치 수와 패치 내부 품질을 행정경계 전체 coverage로 해석하지 않습니다. 기존의 99.23%, 98.50%, 5천6백만 ha 주장은 동일-grid 전후 mask가 없어 철회했습니다. 새 계약은 EPSG:6933 이진 mask, SHA, schema, 경계 mask를 모두 검증하며, 그 증거가 없으면 API도 `BLOCKED/null`을 반환합니다. 차집합 계산 자체는 합성 fixture에서 시험했지만 운영 복구율은 아직 측정하지 않았습니다.”

## Q&A

**Q. 1,407개 적격 patch가 있으니 coverage도 높은 것 아닌가요?**

A. 알 수 없다. patch가 좁은 곳에 겹칠 수 있어 행정경계 전체 합집합 mask가 필요하다.

**Q. 전후 coverage 차이를 복구 면적으로 쓰면 안 되나요?**

A. 안 된다. 사라진 위치와 새로 생긴 위치를 구분하지 못한다. 순변화는 별도 참고 필드이고 복구율은 mask 차집합으로만 계산한다.

**Q. `COVERAGE_COMPLETE`는 언제 가능한가요?**

A. 경계 밖 미피복과 cloud/shadow/nodata/not-measured 면적이 모두 0이고 observed가 경계를 완전히 덮을 때만 가능하다.

**Q. HTTP 200이면 복구율 산출 성공인가요?**

A. 아니다. 현재 envelope는 HTTP 200 안에서도 `status=blocked`와 이유 코드를 반환한다.

**Q. 다음 실제 Gate는 무엇인가요?**

A. 법적·분석적 경계가 고정된 EPSG:6933 grid에서 36셀 before/after/boundary mask를 생성하고 각 파일 SHA를 등록한 뒤 독립 QA를 수행해야 한다.
