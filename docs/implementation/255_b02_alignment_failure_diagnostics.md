# 255 — 선택 B02 정렬 실패의 안전한 수치 진단

상태: **IMPLEMENTED / TESTED_SYNTHETIC**. 실제 실행에서 새 진단을 관측한 상태는 **IMPLEMENTED_UNVERIFIED**다. 실제 수집 승인·재시도·가드 완화는 포함하지 않는다.

## 문제와 보완

Root 인계에 따르면 249는 SCL 후보의 품질 조건을 통과한 뒤 선택 B02의 `CENTER_B02_ALIGNMENT_SHORTFALL`에서 차단되었다. 당시 보고에 실제 B02 window transform/bounds가 없어 어느 변이 얼마나 벗어났는지는 확정할 수 없다. 이번 작업은 그 값을 복원하거나 추정하지 않는다. **다음 실행부터 같은 실패가 발생하면 계획 창과 실제 창의 차이를 설명할 수 있게** 관측만 보완했다. SCL 유효율과 목표 B02 창 정렬은 독립 조건이다.

수정 파일은 `backend/app/data/deficit_candidate_guard.py`, `scripts/collect_deficit_guarded.py`, 두 파일의 기존 시험, 이 신규 문서 5개다. 수정 전 기존 4개 원바이트와 SHA는 `evidence/integration/alignment255-20261018/original/` 및 `baseline.json`에 보존했다. 신규 문서는 수정 전 존재하지 않았다. 최소 diff·최종 지문·시험 로그도 같은 evidence 폴더에 남긴다.

## 판정과 출력 계약

기존 `DeficitCandidateLiveGuard.on_window()`의 순서를 유지한다. 선택 B02 URL 식별 후 고정 binding/AOI, metre CRS, 유효 grid bounds, 동일 CRS/요청 side 1024/실제 1024×1024/10m transform을 먼저 검사하고, 기존 식 `all(abs(actual-planned) <= 10.000001)`로 정렬을 판정한다. 그 식이 `CENTER_B02_ALIGNMENT_SHORTFALL`을 발생시켰을 때만 진단을 보관하고 **원래 예외를 그대로 다시 발생**시킨다. 성공 시의 window claim과 `b02_checked=True` 위치는 변하지 않았다.

부모 256 guard·service geometry 생성·scene/split/window support·SCL 품질·원격 예산·속도/429·물리 상한·원장 정산 코드는 수정하지 않았다. 이 경로의 service hook은 `window_geometry_guard` 단계이며 `src.read()` 전이다. 이미 전송된 header bytes는 기존 방식대로 정산된다. 진단은 픽셀 읽기를 허용하거나 이미 실패한 guard를 성공으로 바꾸지 않는다.

`guard.alignment_diagnostic()`는 매번 deepcopy를 반환한다. 원 geometry나 URL은 보관하지 않는다. **매 on_window 진입 때 이전 진단을 지우므로**, 성공·미관측·다른 asset·선행 grid/binding 오류는 진단이 없다. 마지막 callback만 설명하며 과거 실패 전체의 누적 이력은 아니다.

coordinator의 worker `finally`는 진단이 있을 때만 기존 `worker-result.json`에 `b02_alignment_diagnostic` 필드를 추가한다. 성공/미관측에서는 필드가 없으며 기존 worker 필드·배치 summary·run-result·aggregate 계약은 그대로다. 진단을 최상위 UI나 API에 연결하지 않았다.

## 진단 스키마

정상적으로 수치 진단을 만들 수 있으면 다음 고정 필드만 나온다.

| 필드 | 의미 |
|---|---|
| schema_version | 1 |
| code / stage | `CENTER_B02_ALIGNMENT_SHORTFALL` / `window_geometry_guard` |
| available | true |
| crs | 정규화한 `EPSG:<정수>` 또는 고정 문자열 `PROJECTED_METRE_CRS_UNIDENTIFIED` |
| tolerance_m | 기존 기준 10.000001 |
| planned_bounds_m / actual_bounds_m | `[left,bottom,right,top]`, metre CRS의 각 4개 숫자 |
| delta_actual_minus_planned_m | 실제−계획의 각 변 차이, 부호 보존 |
| abs_delta_m | 각 차이의 절댓값 |
| excess_over_tolerance_m | `max(0, abs(delta)-10.000001)` |
| requested_side / window_width / window_height | 앞선 검사에서 확인된 1024 |
| window_transform | 앞선 검사를 통과한 Affine 6개 숫자의 분리 사본 |

음의 left 차이는 왼쪽으로 이동했다는 뜻이며, 음의 bottom 차이는 아래쪽 이동이다. bounds의 초과량은 네 변의 차이이며 원격 COG 전체 bbox와 비교한 값이 아니다. `window_transform`과 실제 bounds는 이미 전달받은 geometry에서 계산한다. 원격 파일을 진단을 위해 다시 열지 않는다.

모든 기록 수치의 finiteness를 확인한다. 유한 입력의 뺄셈이 overflow하거나 CRS 표시 등 formatting이 실패하면 수치를 싣지 않고 `available=false`, 고정 `reason=ALIGNMENT_DIAGNOSTIC_UNAVAILABLE`만 남긴다. 이때도 schema/code/stage는 고정이다. 진단 helper 자체가 예상 밖 예외를 던지면 진단을 생략하고 원래 정렬 오류를 다시 발생시킨다. 원 geometry·예외 문자열·URL·토큰·scene ID·경로·임의 CRS WKT/이름을 기록하지 않는다. EPSG를 판별할 수 없으면 입력 CRS 문구를 복사하지 않는다. 필드와 배열 크기는 고정이므로 임의 asset 목록이 커져도 진단 크기가 늘지 않는다.

유효 geometry를 가드에서 확인하기 전의 실패에는 이 진단을 만들지 않는다. 진단 부재가 성공의 뜻은 아니다. `live_b02_checked`와 기존 error/정산 상태를 함께 읽어야 한다. 기존 finally 파일 쓰기 자체가 실패하면 기존의 미확정 정산 보호를 유지하며 완료를 꾸며내지 않는다.

## 검증 증거

실행 환경은 프로젝트 코드와 `.runtime`을 PYTHONPATH로 지정하고 bytecode 쓰기를 껐다. 운영 source/ledger/model/실래스터 읽기·HTTP·실 collector·native QA는 실행하지 않았다. 시험의 원장·래스터·출력은 TemporaryDirectory의 합성 자료이며 provider/inventory는 기존 시험 mock을 사용했다.

집중 실행은 신규 5개와 기존 service pixel-read 차단 시험 1개, **6 PASS / 3.640초**다. `focused.log`에 보존했다. 최종 관련 회귀:

```powershell
$env:PYTHONPATH="$PWD;$PWD/.runtime;$PWD/backend;$PWD/scripts;$PWD/tests"
$env:PYTHONDONTWRITEBYTECODE='1'
python -X utf8 -m unittest test_deficit_candidate_guard test_collect_deficit_guarded -q
```

결과 **54 PASS / 17.982초 / exit 0**, `regression.log` 보존. 집중 실행과 겹치는 집합이므로 합산하지 않는다. rasterio의 기존 PendingDeprecationWarning은 있었으며 실패나 skip은 없었다.

검증 내용:

- ±11m 수평 이동의 signed/absolute/excess 값, 원 geometry 및 반환 사본 수정에 대한 alias 분리, 다음 SCL/성공 callback에서 stale 진단 삭제.
- 비교식을 분리한 fake bounds에서 ±10.000001 경계 허용. 실제 큰 좌표의 뺄셈에는 기존 부동소수점 동작을 그대로 유지하며 tolerance를 조정하지 않는다.
- NaN/Infinity 및 유한값 뺄셈 overflow는 원래 차단을 유지하고 수치 없는 고정 unavailable 결과. 진단 formatting 및 helper 자체의 예상 밖 예외도 원래 차단을 가리지 않음.
- 잘못된 grid에는 진단 없음, 기존 부모 256·scene/split/support 보호 회귀 통과.
- fake raster header callback의 정렬 실패 뒤 `dataset.read.assert_not_called()`와 b02_checked=false 확인. 실제 HTTP/실픽셀 읽기 없음.
- 오프라인 worker 정렬 실패 뒤 finally에 진단 저장, materialize 호출 0/신규 패치 0, 기존 source prefix/oldpending 2개 보존, 합성 측정 97바이트 그대로 정산/잠금 해제 확인. URL·token 미포함.
- 성공 fakeworker의 기존 worker 결과에는 새 진단 필드 없음. 기존 정산 실패·finally 실패·2worker·임시 materialization 회귀도 함께 통과.

## 인계와 한계

246 신규 3파일은 편집하지 않고 이전 동결 SHA와 별도 대조한다. 이번 255의 source/test/doc와 원판 archive·diff·logs 지문은 `freeze255.json`으로 고정하여 Root에 인계한다. Root 독립 검토 후 다음 실행 코드핀에 포함할지 결정하며 수집 재개권은 Root에만 있다. 재시도나 과거 249 재실행은 하지 않았다.

실운영 실패 진단 관측, 실제 파일 좌표의 정확한 원인 확정, API/UI 표시, 자동 복구는 미완료다. 이번 변경은 내부 worker 진단이므로 UI 제품 변경·서버 재시작·브라우저 확인을 수행하지 않았다. Root 검토 후 이해 담당이 쉬운 설명·대본·FAQ·INDEX·변경 이력을 갱신하는 후속이 남는다. 수집 성공·나지 확보·모델 학습 준비 완료로 확대해서 설명하지 않는다.
