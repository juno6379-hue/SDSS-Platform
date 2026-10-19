# 273 — 270 후속 고정 후보 QA 준비

상태: **PREPARED / EXECUTION_NOT_STARTED / ROOT_GO_REQUIRED**. CLI/native QA/학습/게시를 실행한 완료 문서가 아니다. 기존 `priority238-preparation-20261018.json`과238 계획은 원판 그대로 보존하고 새 run-id **guarded273-20261018**로 분리했다. 이 담당은 준비 중 운영 source/정책/원장/모델을 읽거나 수정하지 않았다. 코드 및 과거 문서 읽기·경로 존재 확인·새 준비 파일 생성만 수행했다.

## 현재 근거와 실행 필요성

Root는270 terminal/collector 종료·잠금 해제·정산 완료와 단일 bounded native 감사의 완료를 확인했다. 전달된 감사 근거는 `evidence/integration/deficit270-native-root-20261018.json`, SHA `8b745ee8eeda31584942afbe399f93a0c2e1d4f7253fefbdbc849204193cdb4a`, 상태 `COMPLETED_BOUNDED_NATIVE_AND_TRACE_CHECKED`다. 신규16/적격6/실나지0/기여0과 source·ledger 불변은 Root의 독립 감사 인계다. 이 담당이 native 감사를 반복한 결과가 아니다. runner는 GO 뒤 이 근거 파일의 SHA만 계측하여 대조한다.

Root 보고 source는 `0f436db2c320ca6a3b54ae265470d7c26e1e9d64fc657d35aa12619c3bb73b2b`, **67518599바이트**, 등록1731행이다. **64MiB=67108864바이트보다409735바이트 크다.** default64 경로로 실행할 수 없으며 명시128 경로를 Root가 승인해야 한다. 아직 이 담당의 실제 source SHA·행/history 검산은 수행하지 않았다. 정책 expected pin은 `01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7`이다. 실제 source/정책 지문은 기존164가 출력 생성 전, 각 QA 뒤, 최종 단계에서 직접 검산한다.

기존 게시1342/3나지 차단은 과거 후보의 상태다. 새 후보 개수·split별 적격·blocker·동일 장면 제외량은 실제 QA 전 **미확정**이며 예상1348 등을 확정값으로 기록하지 않는다. 나지 확보·독립 정답·학습 준비도 개선을 미리 주장하지 않는다.

## 명시 profile의 전체 전파와 상한

정확한 선택은 `bounded128m-3000-v1`이다. descriptor는 manifest_bytes134217728/max_rows3000/max_depth32/max_nodes4000000/max_json_io_bytes17179869184이며 canonical SHA는 `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`다. source/candidate 각각128MiB, source의 scenes+historical_noneligible_patches 합계3000행, 깊이32/방문노드4M/누적 metadata JSON I/O16GiB를 유지한다. 정책1MiB·receipt64KiB·saved plan4MiB·readiness16MiB 등의 역할별 작은 한도는 넓히지 않는다. 원격 budget과 raster byte 검사는 이 JSON 예산과 구분한다.

runner는 `profile.scope(NAME)`를 하나 열고 기존164의 **`main(argv)`를 정확히 한 번** 호출한다. argparse의 `--manifest-profile`은 `@profile_entry prepare`에 전달되고 중첩 scope는 같은 ContextVar budget을 재사용한다. `app.ml`/`backend.app.ml`은 기존 공용 state 모듈을 통해 같은 ContextVar를 사용한다. 같은 호출 안의 snapshot/copy→source assess→split plan/validation→materialization→staging→candidate QA/verified_files SHA→summary까지 활성 scope가 이어진다. 코드16개 지문을 준비 시 고정하고 실행 전후 대조한다.

wrapper의 준비 JSON 실제2회 읽기, 승인 JSON·native 근거 hash·보호 pointer 전후 hash·launch/log/terminal 쓰기·QA summary/세 receipt 확인도 **같은 누적 I/O budget**에 계측한다. plain Python 코드 SHA 검산은 JSON metadata가 아니다. source를 wrapper에서 별도로 파싱하거나 native를 추가하지 않는다. 기존164가 source/hash/row/history 검사를 계측하는 경로를 그대로 사용한다. 로그는4MiB 상한이며 준비/GO/launch/terminal은 local_plan2MiB 역할을 유지한다.

노드 검사는 JSON decode 후다.128MiB가 모든 메모리 할당·실제 RSS·풍부한 metadata의 실행시간을 보증하지 않는다. 상한·지문·strict schema 오류가 나면 부분 결과를 보존하고 종료하며 profile/cap 증가·자동 재시도·default로 fallback하지 않는다. 이번은64MiB 초과 원본에 대한 최초 명시128 실제 운영 QA를 준비하는 단계이며 성공을 미리 보증하지 않는다.

## 실행 계약과 새 경로

준비 JSON: `evidence/integration/priority273-preparation-20261018.json`.

runner: `evidence/integration/priority273-runner-20261018.py`.

새 DATA/evidence 경로는 각각 `data/priority164-guarded273-20261018/`, `evidence/integration/priority164-guarded273-20261018/`다. 로그는 `evidence/integration/priority164-guarded273-20261018.log`, launch/terminal은 `priority273-{launch,terminal}-20261018.json`이다. 준비 시 모두 미존재를 확인했고 runner가 GO 뒤 다시 확인한다. 존재하거나 부분 결과가 있으면 삭제·재사용하지 않는다.

실행 명령은 아래 template이며 **아직 실행하지 않았다**. approval 파일은 Root가 검토 후 생성해야 한다. runner를 승인 없이 호출하면 필수 인자가 없어 실제 QA 경로로 들어가지 않는다.

```powershell
python -X utf8 -u evidence/integration/priority273-runner-20261018.py --approval 'E:/GeoAI–MLOps–SDSS/evidence/integration/<ROOT_GO_FILE>.json'
```

approval은 정확한 key 집합과 다음 값을 요구한다. `approved`, `no_active_collector`, `execution_lock_absent`는 실제 bool true다. 아래는 스키마 설명이며 승인 파일을 대신하지 않는다.

```json
{
  "kind":"PINNED_CANDIDATE_QA_273_GO",
  "approved":true,
  "run_id":"guarded273-20261018",
  "preparation_sha256":"a87623fd2346e5fea4d89b03662ec0e83606ab4da58d6360d08cf442d33043c5",
  "native_audit_sha256":"8b745ee8eeda31584942afbe399f93a0c2e1d4f7253fefbdbc849204193cdb4a",
  "source_sha256":"0f436db2c320ca6a3b54ae265470d7c26e1e9d64fc657d35aa12619c3bb73b2b",
  "source_bytes":67518599,
  "manifest_profile":{"name":"bounded128m-3000-v1","sha256":"db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4"},
  "no_active_collector":true,
  "execution_lock_absent":true
}
```

Root는 collector가 없고 원본 고정이 유지되는지 확인한 뒤에만 승인한다. runner는 execution lock 부재를 다시 확인하지만 OS 전체 collector 탐지를 대체하지 않는다. source SHA/bytes가 변했으면 이 준비를 그대로 실행하지 않고 Root가 원인을 검토해야 한다. ledger는 QA 입력이 아니며 읽거나 고치지 않는다.

기존164 CLI argv는 data-root/source/source-sha256/policy/policy-sha256/run-id에 위 고정값과 `--manifest-profile bounded128m-3000-v1`를 전달한다. 외부 subprocess로 별도 budget을 만들지 않으므로 QA PID는 runner PID와 같다. source/candidate는 서로 다른 cohort의 정상 QA이며 별도 동일 native 감사의 반복이 아니다.

## 보호, 마감, 한계

기존 `latest-candidate.json`과 `candidate-receipt227-20261018.json`의 실제 SHA를 GO 뒤 scope 안에서 전후 확인하며 쓰지 않는다. source·원장·고정 split·라벨·모델을 수정하지 않고 동일 scene 누출은 새 후보에서만 제외한다. 게시·API/UI·Registry·학습·운영 승인은 runner가 수행하지 않는다.

exit0 뒤 summary의 source pin/manifest marker/실파일 SHA 불일치0/훈련false와 package/staging/QA receipt의 schema_version2·정확 marker를 확인한다. gate blocker가 남으면 그대로 유지한다. 실제 sameScene retained/excluded partition·exact row 및 결과 나지 픽셀/분모/기여도·현재 source/정책·output11개 pin은 완료 후 별도 읽기 인계로 검산하며 추가 native QA를 실행하지 않는다.

runner는 전체 wrapper monotonic wall과 CLI+postcheck wall을 구분한다. 실제 RSS/OS peak는 관측하지 않으며 `rss_observed=false`로 남긴다. 필요하면 Root가 실제 PID의 OS 표본을 별도로 기록하고 표본 최대와 peak를 구분한다. 예전 whitespace 시험의 RSS를 이번 수치로 쓰지 않는다.

오류·budget 소진·지문 변경은 부분 결과를 남기고 exit2다. 정상 terminal도 결과 게시 승인과 다르다. JSON budget/보호핀 검산/파일 쓰기 자체가 실패하면 terminal도 없거나 부분일 수 있으며, 이를 완료로 만들기 위해 예산 밖 fallback receipt를 쓰지 않는다. 이 경우 OS 종료코드·기존 log·남은 산출물로 미완료를 인계한다. 자동 재실행하지 않는다.

준비 검증은 runner AST parse/compile(실행0), `cli_main` 호출 지점1개, 코드16개 SHA 일치, 새 경로 미존재 재확인이다. 실제 CLI/QA 시험은 하지 않았다. 준비 파일/runner/문서 지문은 `priority273-preparation-freeze-20261018.json`에 고정하고 Root가 실행 GO 전 직접 검토한다. 새 결과가 나오면 Root 독립 승계 검산→old pointer 원바이트 archive→receipt/pointer 게시→실 API·브라우저 확인→문서/이해자료 갱신 순서를 별도 완료 근거로 남긴다.
