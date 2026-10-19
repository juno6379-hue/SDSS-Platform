# 290 — 285 후속 고정 후보 QA 실행 준비

상태: **PREPARED / ROOT_GO_REQUIRED / 실제 QA 미시작**. 기존273 runner/prep/freeze/완료 근거·문서는 수정하지 않았다. 운영 제품·원본·원장·모델·split·게시 pointer 쓰기0, HTTP/collector/native/학습0이다. 이번 준비에서는 Root가 지정한 source·ledger·policy의 metadata SHA와 크기를 실제 읽어 검산했다. 이미지·라벨·모델은 읽지 않았다.

## 직접 확인과 미확정값

Python QA/collector 명령을 실제 OS에서 조회하여 prepare_priority_candidate164/priority273·290 runner/collect_deficit_guarded에 해당하는 실행 프로세스0, execution lock 부재를 확인했다. 조회 셸 자신은 실행 QA로 세지 않았다. Root GO 시 다시 확인해야 하며 과거 관측을 미래 실행 허가로 사용하지 않는다.

| 입력 | bytes | 실제 확인 SHA256 |
|---|---:|---|
| current source | 68220381 | `9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7` |
| current ledger | 67545 | `4a4f4a47b522b9497b944ac00b29d2368a977c1a4eb6dfe972a34959fcc68722` |
| 고정 policy | 1306 | `01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7` |
| 285 단일 감사 | 준비 JSON에 크기 기록 | `194affdac6f8838875251bdb8c6cb2807cc3492015b3b655ba71ae040ba8c455` |

source는 **64MiB67108864B보다1111517B 크다**. 파일 크기로 자동 상향하지 않으며 정확한 명시128 profile을 Root가 승인해야 한다. 단일 native 감사 status는 `COMPLETED_BOUNDED_NATIVE_AND_TRACE_CHECKED`다. 감사 자체를 재실행하지 않았다.

Root의 원본 보고값은1747행/적격1376(train834/val292/test250)이다. 준비는 이를 전체 source QA로 다시 계산한 작업이 아니다. **새 후보 수·제외량·최종 blocker·나지·준비도는 미확정**이며 prep에 candidate_count=null을 남겼다. source의 scenes+history 합계3000 검사는 실제164의 profile reader에서 수행한다. 준비 중 원본 전체를 JSON parse하거나 history 수를 발명하지 않았다.

현재1348 게시 pointer와 `candidate-receipt275-20261018.json`의 SHA는 둘 다 `1aee2e01583a024c508d6fdac0d3c4fac2260bbd449ea12269d5e033c1dcc7b4`다. 새 runner가 시작 전 이 expected 지문과 일치하는지 확인하고 끝난 뒤에도 보존을 검산한다. 게시나 receipt 갱신은 수행하지 않는다.

## 273과 같은 실제 실행 계약

새 파일은 `evidence/integration/priority290-{preparation,runner}-20261018.{json,py}`이며 실제 이름은 각각 preparation JSON과 runner PY다. `priority290-runner-vs273-20261018.diff`에 검증된273 runner 대비 차이를 남겼다.

차이는 새290/run-id·준비 SHA·285 native/source/protected receipt 맥락, 그리고 `protected == plan['protected_expected']` 시작 전 확인이다. 기존164 CLI `main(argv)` 호출 지점은1개이며 코드16개 지문은273 당시와 실제 일치한다. 공유 제품을 바꾼 것이 아니다. AST parse/compile만 수행했고 runner/CLI를 실행해 시험하지 않았다.

명시 profile은 `bounded128m-3000-v1`, descriptor SHA `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`다. source/candidate128MiB, scenes+history3000행, depth32/node4000000, 누적 JSON I/O17179869184B(16GiB), 역할별 policy1MiB/receipt64KiB/readiness16MiB/saved_plan4MiB를 유지한다. node 검사는 decode 후이며128MiB가 최대 RAM/RSS·실행시간을 보증하지 않는다.

runner의 한 ContextVar scope에서 준비 JSON2회 읽기·Root GO·감사 SHA·보호 pointer 전후·launch/log/terminal·source snapshot→source QA→split 계획/검산→package/stage→candidate QA→실 verified_files SHA→summary가 같은 budget을 사용한다. 중첩 @profile_entry는 기존 budget을 재사용한다. app/backend alias의 공용 state와 세 v2 receipt/정확 marker 후검산도 그대로다. source/policy는164가 출력 전·QA 뒤·최종에 다시 직접 검산한다.

원장 SHA는 준비/Root native 완료 provenance이며 **QA 입력으로 추가하지 않는다**. Root가 GO 직전 최신 원장/정산을 확인해야 한다. 준비 때의 별도 metadata 지문 읽기를 미래 실행의 profile 측정치로 꾸며 쓰지 않는다. 실행 scope는 실제 호출의 측정값을 남긴다.

## 단1회 실행과 새 경로

run-id는 **guarded290-20261018**다. 다음 새 경로가 모두 미존재임을 준비 시 재확인했다.

```text
data/priority164-guarded290-20261018/
evidence/integration/priority164-guarded290-20261018/
evidence/integration/priority164-guarded290-20261018.log
evidence/integration/priority290-launch-20261018.json
evidence/integration/priority290-terminal-20261018.json
```

GO 뒤 다시 검사하며 기존/부분 파일을 삭제하거나 재사용하지 않는다. 승인 파일이 없으면 필수 argparse 인자가 없어 QA를 실행할 수 없다. Root가 전체 runner/최소 diff/핀을 검토한 뒤 아래 명령을 단1회 승인할 수 있다. **현재 이 명령은 미실행이다.**

```powershell
python -X utf8 -u evidence/integration/priority290-runner-20261018.py --approval 'E:/GeoAI–MLOps–SDSS/evidence/integration/<ROOT_290_GO_FILE>.json'
```

GO는 아래 정확 key 집합/값을 요구한다. 예시 자체는 승인 파일이 아니다. bool3개는 실제 true여야 한다.

```json
{
  "kind":"PINNED_CANDIDATE_QA_290_GO",
  "approved":true,
  "run_id":"guarded290-20261018",
  "preparation_sha256":"e9260f8ee5c81a63a9a8221e24b439f5e7c0b2b5e5955129be6b0cf169ace4ef",
  "native_audit_sha256":"194affdac6f8838875251bdb8c6cb2807cc3492015b3b655ba71ae040ba8c455",
  "source_sha256":"9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7",
  "source_bytes":68220381,
  "manifest_profile":{"name":"bounded128m-3000-v1","sha256":"db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4"},
  "no_active_collector":true,
  "execution_lock_absent":true
}
```

runner는 source bytes·code16핀·native 근거 SHA·lock·새 경로·기존1348 pointer expected를 검사하고 한 프로세스에서 기존 CLI main을 한 번 호출한다. OS 전체 collector 탐지는 Root 확인을 대체하지 않는다. source/pointer/code가 달라졌다면 준비를 자동 수정하거나 재시도하지 않는다.

## 완료 검산과 미완료 경계

실행 후 actual wrapper wall과 CLI+postcheck wall을 구분하고 RSS를 관측하지 못하면 false/null로 남긴다. 느린 strict metadata 단계를 우회하지 않는다. failure/상한 초과는 부분 보존/exit2이며 cap 증가·새 profile·자동 retry0이다. 예산 소진/쓰기 실패이면 terminal도 없거나 부분일 수 있고 예산 밖 fallback 완료 영수증을 쓰지 않는다.

정상 exit라도 source/candidate의 실제 split/eligible·sameScene 제외/partition·파일5376 같은 기록 수는 **이번 결과를 읽어 새로 확정**해야 한다. 이전273 개수를 이번 값으로 고정하지 않는다. 나지3 차단·NOT_CAPTURED_BUDGET도 과거 참고이며 새 gate를 관측대로 기록한다. 수집 증가를 독립 정답이나 학습 승인으로 확대하지 않는다.

새 summary/terminal/세 v2 receipt·actual output SHA·원본/정책·보호 pointer와 exact retained partition을 읽기 검산하고, Root에게 검산 종료 신호를 보낸다. Root의 독립 승계·old1348 archive·게시/명시 source 재결속·실 API/브라우저·이해자료/INDEX/이력은 별도 근거로 마감한다. 이 내부 준비는 화면 변경이나 실제 QA 완료가 아니므로 API/UI를 실행하지 않았다.
