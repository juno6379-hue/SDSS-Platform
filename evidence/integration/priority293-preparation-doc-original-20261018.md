# 293 — 290 완료 후 후보 게시 준비

상태: **PREPARED / COMPILE_ONLY / NOT_EXECUTED**.290 QA가 활성인 동안 게시·pointer 교체·부분 결과 읽기·운영 source/ledger/model 읽기·HTTP·실QA/수집0을 유지한다. Root만 실제 게시를 실행한다. 후보 수를 미리 확정하지 않는다.

## 원판과 최소 변경

검증된 `evidence/integration/priority275-promote-root-20261018.py` 원판 SHA `d5ba83bf030a97c85e5570aba9b7b87a6ccda743672254e88ae561c4536f61a8`를 확인하고 새 `priority293-before275-20261018.py`에 원바이트 보존했다. 원275 파일은 편집하지 않았다. 번호 검색에서 기존293 작업 충돌이 없음을 확인했다.

새 코드는 `evidence/integration/priority293-promote-root-20261018.py` SHA `08f58cf98db254c73679f27d1fd6ef4b99be96e90f94c49aed1c271d2fbfd789`다. 최소 diff는 `priority293-minimal-diff-20261018.patch` SHA `1c3015d269883aa71a9d295349012692db59de5b682b88744fee552b2a5a12b9`에 기록했다.

변경 범위는 입력 run273→290, terminal290, GO kind POST290, 출력/오류명275→293, 이전 게시 split의 train816→822, post285/1747 scope, 새 source/ledger/oldpointer를 GO와 exact tuple로 고정하는 한 검사뿐이다. 기존275의 검산·교체 알고리즘은 보존한다. 제품 backend/scripts/UI는 수정하지 않았다.

## 준비에 고정한 운영 핀과 읽기 범위

| 역할 | 고정 값 |
|---|---|
| current source | `9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7`,68,220,381B·Root 인계1747행 |
| current ledger | `4a4f4a47b522b9497b944ac00b29d2368a977c1a4eb6dfe972a34959fcc68722` |
| 이전 게시 pointer | `1aee2e01583a024c508d6fdac0d3c4fac2260bbd449ea12269d5e033c1dcc7b4` |
| 이전 게시 split | train822 / val276 / test250, 합계1348 |
| 새 receipt scope | `FROZEN_POST285_1747_ROW_SOURCE_NOT_LATER_COLLECTION` |

source/ledger는 Root가 준 현재 값이다. pointer 전체 SHA와 split은 완료275 publication evidence/완료 문서에서 확인했으며 **운영 pointer 파일은 읽지 않았다.** 이 값들이 현재 운영에 실제 유지됐는지는 실행 전 Root가 다시 검산해야 한다. 자동으로 바뀐 운영 핀을 따라가지 않으며 tuple이 다르면 차단한다.

290의 summary·handoff·terminal은 아직 최종 지문을 받지 않았고 열지 않았다. 새 후보 수·새 split 수·blocker를 성공값으로 hardcode하지 않는다. 이후 실제 완료 summary/QA/counts로만 결정한다. current source1747은 고정 입력 범위이며 향후 다른 수집 자료를 포함한다고 표시하지 않는다.

## Root GO 계약과 입력 경로

기존275와 같은 **정확8개 키**만 허용하며 kind만 `ROOT_POST290_PUBLICATION`이다. 아래는 스키마 설명용이다. placeholder를 유효한 실제 GO라고 취급하지 않는다.

```json
{
  "kind": "ROOT_POST290_PUBLICATION",
  "approved": true,
  "summary_sha256": "<Root final290 summary SHA>",
  "handoff_sha256": "<Root final290 handoff SHA>",
  "terminal_sha256": "<Root final290 terminal SHA>",
  "source_sha256": "9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7",
  "ledger_sha256": "4a4f4a47b522b9497b944ac00b29d2368a977c1a4eb6dfe972a34959fcc68722",
  "previous_pointer_sha256": "1aee2e01583a024c508d6fdac0d3c4fac2260bbd449ea12269d5e033c1dcc7b4"
}
```

실제 GO는 Root가290 완료/최종 검산 뒤 새 지문으로 별도 작성한다. runner는 evidence 아래 절대 approval 경로를 요구한다. 사용 명령은 승인 뒤 `python -X utf8 evidence/integration/priority293-promote-root-20261018.py --approval <absolute Root293 GO path>`이며 이번 준비에서 실행하지 않았다. 원275 GO나 미완료 summary를 재사용하지 않는다.

입력은 `data/priority164-guarded290-20261018/`, `evidence/integration/priority164-guarded290-20261018/`, `evidence/integration/priority290-terminal-20261018.json`으로 고정한다.290 완료 상태/exit0·manifest marker·파일SHA불일치0·잔여 identity충돌0·training/registry/networkfalse를 확인해야만 진행한다.

## 그대로 유지한 검산과 게시 보호

전체 작업은 동일 `scope(NAME)` 하나에서 수행한다. 명시 `bounded128m-3000-v1`의 역할별 read_metadata/bounded_json_digest/write 계측과 누적 JSON IO16GiB 한도를 유지한다. source/candidate128을 모든 JSON에 적용하지 않으며 saved_plan/readiness/receipt/policy/pointer/status_report 등 기존 semantic role과 개별 cap을 그대로 쓴다.

summary의 outputs는 기존 정확11경로와 집합이 같아야 한다. 모든 바이트 크기/SHA를 재확인하고 세 receipt(candidate package/staging/QA)는 schema2와 정확 manifest_profile marker여야 한다. source/후보 행은 summary·QA·split-plan과 결속한다.

retained/excluded는 bool을 제외한 int 인덱스의 완전 분할이며 중복/누락/범위밖을 거부한다. 후보 scenes는 source에서 retained 순서대로 뽑은 원행과 exact 같아야 한다. source_row_count/candidate_row_count/excluded_source_rows와 QA split count/blockers를 실제 summary 값으로 비교한다. training-ready는 false를 유지한다. 예상 새 후보 총량이나 train 증가량을 성공 조건으로 발명하지 않는다.

old pointer는 exact SHA와822/276/250을 확인한다. 다음 신규 파일을 독점 생성한다.

- `data/first-group-training-priority/candidate-pointer-before293-20261018.json`: old pointer 원바이트 archive와 SHA 확인.
- 같은 디렉터리 `candidate-receipt293-20261018.json`: 검증된290 세 참조와 실제 split/blockers.
- 같은 디렉터리 `latest-candidate293.tmp`: exclusive 작성·계측·flush/fsync.
- `evidence/integration/priority293-publication-root-20261018.json`: 실제 교체와 후검 결과.

원pointer 교체 직전에 oldpointer/current source/ledger SHA·execution lock 부재·세 게시 참조를 다시 확인한 뒤 `os.replace`한다. 같은 누적 scope의 role-aware callback으로 `candidate_quality`를 호출해 현재 source 일치·실제 summary count/split/blockers·false training을 확인한다. 최종 source/ledger도 재검산한다. profile config 재결속·실API·브라우저는 이 스크립트가 수행하지 않는다.

기존 path가 있거나 한도가 넘거나 핀이 달라지면 자동 overwrite/retry/rollback하지 않는다. 실패 시 partial archive/receipt/tmp 또는 이미 교체된 pointer가 남을 수 있다. 따라서 실패를 일괄 “게시되지 않음”으로 간주하지 말고 Root가 실제 교체 여부를 확인해야 한다. 이 준비 단위에서 복구 동작을 새로 발명하지 않았다.

## 검증과 실행 전 남은 일

검증은 원275 SHA/동일 archive SHA·최소 diff·메모리 `compile()` 문법 검사만 수행했다. 새 script를 import하지 않았고 pycache를 만들지 않았다. 운영 파일·290 부분 결과·실QA·게시/API/브라우저 실행을 시험한 것이 아니다. 다른 단위의 과거 시험을293 실성공으로 승계하지 않는다.

Root 실행 전 조건은290 실제 종료/잠금/프로세스 상태와 최종11output/3receipt/summary·handoff·terminal pin 확인, oldpointer와 source/ledger의 현재 exact 검산, 신규 archive/receipt/tmp/result 경로 미존재, 이번 동결 runner/최소diff 독립 검토, 새 GO다. 이후 게시 후검과 profile 재결속/API·실브라우저·이해자료를 별도 실제 근거로 마감한다.

현재는 화면/API/보유량을 바꾸지 않는 준비 코드이므로 UI 변경은 필요 없다. 실제 게시 완료 뒤 Root가 UI/이해 담당에 새 source·실제 후보 count·오류 계약·실행 증거를 인계해야 한다. 나지 gate·독립정답·학습 승인은 이 준비나 후보 게시로 해제하지 않는다.
