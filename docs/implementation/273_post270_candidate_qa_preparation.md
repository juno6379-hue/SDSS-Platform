# 273 — 270 후속 고정 후보 QA 준비

현재 상태: **VERIFIED_REAL / PINNED_CANDIDATE_QA_COMPLETED**. Root 명시 GO 뒤 단1회 실행·metadata 인계 검산을 마쳤다. **학습 준비 false / 나지 차단3 / 게시·API/UI는 별도 Root 후속**이다. 아래 준비 계약은 당시 기록이며 실제 결과는 마지막 절에 추가했다. 준비 원문은 `evidence/integration/priority273-preparation-doc-before-result-20261018.md`에 SHA `518d32784453dbdd3abf3f4556207074548e44f3f2e9dd43b88f540a51e496cd`로 원바이트 보존했다. 기존238 준비도 그대로다.

준비 당시 상태는 PREPARED / EXECUTION_NOT_STARTED / ROOT_GO_REQUIRED였다. CLI/native QA/학습/게시의 실행 완료 주장이 아니었다. 기존 `priority238-preparation-20261018.json`과238 계획은 보존하고 새 run-id **guarded273-20261018**로 분리했다. 준비 중 운영 source/정책/원장/모델 읽기·수정 없이 코드와 문서·경로 미존재를 확인했다. 실행 GO 이후 허용된 source/정책·고정 cohort를 읽어 QA했고 운영 source·원장·split·라벨·모델·pointer를 쓰지 않았다.

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

## 실제 실행과 최종 인계 — 2026-10-18

Root가 runner 전체·16코드핀·profile/CLI 경로를 검토하고 `priority273-go-root-20261018.json` SHA `d240680837818ea21d6191cb5d14fce40f4ae2a2622b0af62216054367d01a5f`를 발급했다. source/policy/native 지문·collector/lock 부재를 Root가 확인했고 QA 동안 원본을 고정했다. 동결 runner `fe3d74262d8d6a9eb9f8b291dd39de640b5152bdf64602fee4195eb8d7485cc1`와 GO 지문을 재확인한 뒤 승인 명령을 **한 번만** 실행했다. 실제 PID37520/exec session53854, exit0다. 자동 재시도·상한 증가·추가 동일 native 감사는0이다.

snapshot은20:06:05.451 KST에1731행/source0f436으로 고정됐고 summary는20:31:53.167, terminal은20:31:54.445에 기록됐다. 전체 wrapper wall1574.593초(약26분15초), CLI+후검 구간1572.015초, source QA308.390초, candidate QA 함수324.656초다. 함수 시간은 입력 proof 검산도 포함하며 순수 래스터 처리만의 시간으로 쓰지 않는다. 두 QA 시간을 전체 시간에 더하지 않는다. 나머지 구간은 계획/materialize/staging/엄격 JSON 왕복·hash·부수처리로 구분하며 개별 병목 시간을 측정한 주장은 아니다.

| 구분 | 전체 행 | 적격 train/val/test | 적격 합계 | 차단 |
|---|---:|---|---:|---|
| 고정 원본 | 1731 | 822/292/250 | 1364 | sameScene 충돌1+나지3 |
| 새 고정 후보 | 1715 | 822/276/250 | **1348** | 나지3 |

새 후보는 이전1342보다 적격6개 늘었지만 **나지 확보 성공은 아니다**. 원본은 그대로다. Banten과 West Java에 같은 장면 `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`이 포함돼, 고정 test 우선 정책으로 test를 보존하고 val의 원본 index288–303(16행)을 새 후보에서만 제외했다. source/candidate의 exact retained rows와 lineage·retained/excluded의 전체 partition을 인계 검산에서 다시 확인했다. 남은 source identity 충돌은0이다. 운영 원본의16행을 삭제하거나 split을 옮긴 것이 아니다.

최종 참조라벨 나지 통계는 다음과 같다. 기여 패치는 기존 기준(유효 나지256픽셀 이상)을 사용하는 값이다.

| split | 나지 픽셀 / 유효 참조라벨 픽셀 | 비율 | 기여 패치 |
|---|---|---:|---:|
| train | 2562 / 52383086 | 0.00489089169% | 1 |
| val | 2998 / 17776457 | 0.01686500296% | 2 |
| test | 1025 / 16252940 | 0.00630655131% | 0 |

각 split의 기존0.5% 비율·기여5개 조건이 부족하여 `REFERENCE_CLASS_IMBALANCE`가3개 남는다. 새 적격6개가 늘어도 나지 픽셀2562/2998/1025와 기여1/2/0은 이전 후보와 같으므로 대표성 보완은 계속 필요하다. 이 라벨 통계는 독립 현장 정답이나 과학적 정확도 승인과 다르다. `ready_for_training=false`, `scientific_accuracy_validated=false`, training/registry/network0을 유지한다. connectivity witness는 **NOT_CAPTURED_BUDGET**이며 기본 실파일 QA를 생략했다는 뜻은 아니다.

## 실제 profile·실파일·보호 검산 결과

source snapshot67518599B가64MiB를 넘는 상태에서 정확128 marker가 전체 경로에 유지됐다. candidate-package와stage candidate는 모두66897322B/SHA `944e34b5b8f6f8c8da8d39c6ade24353cddf105e804f30dfbb6869e808af2b10`다. 후보 자체가64MiB보다 작더라도 파일 크기로 profile을 자동 변경하지 않았으며 세 receipt는 모두 schema_version2/정확 marker를 유지한다.

| 산출 | SHA256 |
|---|---|
| package receipt | `be0a3d3748cf5dcdb433095096673b1e265eab4781ea3f55377e18a6f6cbdb05` |
| staging receipt | `fcb04a952ee75a61d4a0f959d16c62b9ab54f3ededc777e9a7e98e2abc61f68f` |
| candidate readiness | `4f6a1e1bac5b236de757176ec6d49c56c1ee6c9ec917f2c859e90e9ad0bd2bfb` |
| QA receipt | `fe131b495609681eeac6ecab9bc53c4c8f94159d0f59055ce9df294ccffe661f` |
| handoff-verification | `a8eb96bf444dbadca20e77e683147cb4f83845ee8dd259fe50bea7c5a08b566c` |

기존164가 실제 verified file5376개의 SHA를 최종 대조해 불일치0을 기록했다. 별도 `priority273-handoff-20261018.py`는 native를 호출하지 않고 summary의11출력 실SHA/bytes, 세 v2 receipt, exact rows/partition, 현재 source/정책, old1342 pointer/receipt 보호를 검산했다. 추가 래스터/hash5376 재감사는 반복하지 않았다. 인계 checker는 session51286/exit0이다.

QA wrapper의 terminal 쓰기 전 누적 JSON I/O는4519037065B(읽기4314871515+쓰기204165550), 한도17179869184B보다 작다. 인계 checker는 그 사용량과 terminal 쓰기 비용을 먼저 debit하고 같은16GiB 한도 안에서 검산하여 proof 쓰기 후 누적4926565643B를 기록했다. 운영 QA+인계 계측과 별개인 외부 도구의 로그/OS 모니터링 비용은 이 계측값으로 위장하지 않는다. 전체 프로젝트 I/O나 모든 RAM 할당의 보장이 아니다.

wrapper는 RSS를 측정하지 않아 rss_observed=false다. 별도 OS 표본에서 Windows WorkingSet과 PeakWorkingSet을 읽었으며, 관측한 OS peak의 최대값은1294880768B였다. 이는 실행 종료 시의 최종 peak를 보증하지 않고 Linux RSS나 rich128MiB 최대 사용량 보장으로 확대하지 않는다. 228의 whitespace benchmark와 이번 실제 구조화된 source의26분 실행을 혼합하지 않는다.

20:34:14 KST metadata 인계 검산까지 old1342 pointer와 receipt는 모두 `920ceb52dca0aba32f11389fd2f9c5f2719ca40b47f44e650c3a38b57c3b3d40`로 보존됐다. 원본source0f436·정책01991d도 일치했다. Root에 읽기 검산 종료/안전한 독립 승계 가능 신호를 전달한 뒤 이 담당의 운영 pointer/source 검산은 끝냈다. **그 이후 Root의 의도된 게시·profile 재결속은 별도 후속이며 이 보호 검산 위반으로 해석하지 않는다.** 이 담당은 게시/API/UI/모델을 변경하지 않았다.

준비 원문 archive/과거238·준비freeze와 runner는 보존한다. 최종 결과 지문은 새 completion freeze로 인계한다. Root의 독립 입장 검산·게시275/명시 source 재결속/API276·실 브라우저와 이해자료(쉬운 설명/대본/FAQ/INDEX/이력)는 각각 별도 완료 근거로 확인한다. 이273의 QA 완료를 전체 개발·학습 승인 완료로 보고하지 않는다.
