# 274 — 273 완료 후 후보 승계의 정적 검토 계약

## 범위와 결론

상태는 **STATIC_REVIEW_COMPLETED / 승계 실행 전 계약 정리**다. 기존 `priority227-promote-root-20261018.py`, `candidate_quality` reader와 profile·candidate 생성/receipt 코드를 읽었다. 273의 실제 summary·receipt·candidate·pointer·원본·원장을 읽지 않았고 native·HTTP·승계 실행·운영 파일 쓰기도 0회다. 이 문서만 새로 작성했다. 273은 별도 담당의 단1회 QA가 진행 중이며 완료 수치·예상 후보 수를 확정하지 않는다.

기존227 script를 경로와 숫자만 바꿔 재사용하면 안 된다. 273은 명시128MiB profile을 사용하므로 bounded reader/hash와 **하나의 operation-local 16GiB ContextVar** 안에서 검증해야 한다. 핵심 호환 공백은 마지막 reader hash callback의 keyword 지원이다.

## 기존227 코드의 재사용 주의

227 script는 source/후보 규모가 당시 legacy 범위였고 `read_text`·`read_bytes`·일반 SHA 함수를 사용한다. 현재 큰 source를 같은 방식으로 읽으면128/depth32/node4M/누적16GiB 계약을 검증한 것이 아니다. 현재 제품의 명시 profile reader/hash·role별 cap을 사용해야 한다. 단순히 old helper 상한을 늘리거나 재시도로 context를 새로 만들어 통과시키지 않는다.

또한227의 마지막 호출은 다음과 같다.

```python
candidate_quality(D, current_pin, lambda p, h: sha(p) == h)
```

active profile에서 reader는 `same_hash(path, sha, json_role=role)`를 전달한다. 위 lambda는 keyword를 받지 못해 TypeError가 발생하고 reader는 `available=false`로 닫힌다. **기존227은 이미 pointer를 os.replace한 뒤 이 검사를 하므로, 새 pointer가 게시된 후 검증 실패로 끝날 수 있다.** 실제273에서 이 실패를 재현한 것이 아니라 소스 제어 흐름에 따른 정적 판단이다.

새 승계는 같은 profile scope 안에서 아래 형태의 명시 role callback을 사용해야 한다.

```python
def same_hash(path, expected, *, json_role):
    return bounded_json_digest(path, json_role) == expected
```

이 호출은 `scope('bounded128m-3000-v1')`가 이미 활성인 **동일 작업 context 안**에서 수행한다. hash를 raw read로 바꾸거나 profile 밖에서 reader만 확인하는 우회는 금지다. 위 코드는 계약 설명이며 본 문서에서 실행하지 않았다.

## 완료 근거를 먼저 검증할 목록

Root만 실제273 종료와 원본 고정 상태를 확인하고 다음 값을 읽어 확정한다. 이전227의 하드코딩 숫자·SHA·경로는 사용하지 않는다.

1. 실제 프로세스 종료·exit0·최종 summary와 handoff의 존재/지문, 완료 상태 `PINNED_CANDIDATE_QA_COMPLETED`를 확인한다. 중간 SOURCE_QA_COMPLETE나 stage 파일 생성만으로 승계하지 않는다.
2. 현재 원본 SHA =273 입력 source SHA =273 snapshot 실제 SHA를 대조한다. 현재 원장 SHA·원 pending 원형·잠금 없음·Root 수집 hold도 별도 보존 기준으로 고정한다.
3. profile marker가 정확한 `bounded128m-3000-v1` 및 고정 descriptor SHA인지 확인한다. legacy64로 성공한 것처럼 처리하거나 profile을 자동 선택하지 않는다. source/candidate 각128MiB·합계행3000·depth32·node4M·누적JSON I/O16GiB와 role별 작은 cap을 유지한다.
4. summary가 지목한 모든 생성 output의 실제 SHA/byte수를 같은 scope의 역할별 bounded 읽기/해시로 확인한다. 경로는 허용 root에 confined된 일반 파일이어야 하며 링크/alias·입출력 재사용을 허용하지 않는다. 파일명 확장자만 보고 JSON 계측을 생략하지 않는다.
5. source QA와 candidate QA의 완료/정확 source 결속·보존 지문을 확인한다. `file_sha_mismatches==0`, `remaining_source_identity_conflicts==0`, 최종 blockers·split별 적격 수가 summary/QA에서 같아야 한다. 이 값은273의 완료 근거이며 Root가 새 native QA를 중복 실행한다는 뜻은 아니다.
6. `training_executed`, registry 호출·자동 실행·과학 정확도 승인 등의 금지 상태를 유지한다. readiness가 blockers를 가진 채 완료돼도 게시할 수 있지만, 그 게시를 학습 승인으로 바꾸지 않는다. 실제273 값을 확인하기 전 후보 적격 수를 추정해 pointer에 쓰지 않는다.

## 세 receipt의 v2 연결

273의 명시 profile 경로에서는 다음 세 제품 receipt가 **schema_version=2 + 정확 manifest_profile marker**여야 한다.

- materialization: `candidate-package/receipt.json`의 `EVIDENCE_SPLIT_CANDIDATE_RECEIPT`
- staging: `stage/staging-receipt.json`의 `DATA_CANDIDATE_STAGING_RECEIPT`
- QA: `qa/qa-receipt.json`의 `STAGED_CANDIDATE_READINESS_QA_RECEIPT`

`manifest_resource_profile.receipt()`는 active scope에서 정확 v2/marker를 확인한 뒤 내부 v1 검증용 사본으로 변환한다. 따라서 저장 원판을 v1로 내려쓰거나 marker를 삭제해서 legacy reader를 통과시키면 안 된다. receipt가 없거나 부분·변조·입력/output 지문 불일치이면 승계를 보류한다.

각 receipt의 입력 source/policy/readiness/plan 지문·package 출력과 stage 후보 지문·QA readiness 지문이 서로 이어져야 한다. materialization의 행수 관계, staging의 staged_candidate reference, QA의 실제 저장 report SHA/bytes·완료 상태·blockers·counts를 점검한다. 실제 제품 코드의 false 승인·환불0·exactly_once UNKNOWN 같은 한계를 유지한다.

이 “세 receipt v2”와 UI의 `latest-candidate.json` pointer schema는 다른 계약이다. 현재 `candidate_quality`는 pointer의 schema_version/manifest_profile을 세 제품 receipt처럼 `profile_receipt()`로 검증하지 않는다. pointer에는 reader가 요구하는 정확한3 files·counts·blockers·source 지문을 넣고, 새 profile 표기를 추가할 경우 실제 지원 계약을 명시해야 한다. 단순히 pointer에 v2라고 쓰는 것으로 세 receipt 검증을 대체하지 않는다.

## 정확한 retained partition

plan의 retained/excluded index를 단순 개수로만 확인하지 않는다.

- 두 목록이 list이고 각 index는 bool을 제외한 int·정상 범위여야 한다.
- 둘의 합집합은 source의 모든 행 index이며 중복·교집합·누락이 없어야 한다.
- candidate scene 목록이 retained 순서대로 고른 source scene 원문과 **exact equality**여야 한다. 집계 counts만 같아도 다른 행이 섞이면 실패다.
- source 행수 =candidate 행수+제외 행수, receipt/summary/plan의 해당 값과 split별 counts·QA blockers가 같아야 한다.
- source manifest 원판은 고치지 않고 후보에서만 제외한다. 기존 공유 장면에 대한 제외/남은 conflict 결과는273의 실제 plan·QA에 따라 판단하며 과거16이라는 숫자를 새 결과의 증명으로 대체하지 않는다.

## pointer 원바이트 보존과 안전한 교체

검증을 모두 끝내기 전에는 current pointer를 쓰지 않는다. Root는 현재 pointer bytes와 SHA를 읽어 승계 전 기준으로 고정하고 새 exclusive archive에 **원바이트 그대로** 보존한다. archive의 SHA가 원 pointer SHA와 같은지도 확인한다. 과거227 script에 들어 있는1339 pointer 지문은 현재1342 pointer의 검증값이 아니다.

새 receipt는 고정 source·stage candidate·최종 readiness의3개 경로/SHA와 실제 QA counts/blocker 수, source 지문·시각·승인 아님/범위·이전 pointer 지문을 기록한다. 같은 디렉터리의 새 exclusive temp 파일에 쓰고 flush+`os.fsync`한 뒤, 교체 직전 pointer 원바이트·source·원장 지문과 작업 hold를 다시 확인한다. 그 다음에만 `os.replace`한다.

파일 단위 replace는 source/원장/receipt 전체의 원자 transaction이 아니며 Windows에서 전체 디렉터리 전원 장애 내구성을 증명하지도 않는다. archive/temp/부분 결과는 실패 시 보존한다. post-reader 검사가 실패했다고 원 pointer를 무단 복구하거나 재승계를 자동 반복하지 않는다. 이미 교체됐는지를 실제로 기록하고 Root가 후속을 결정한다.

교체 후에는 같은 명시 profile scope·role keyword를 받는 bounded callback으로 `candidate_quality`를 호출해 available, 현재 source 일치, 최종 실제 counts/blocker 수, ready_for_training false를 확인한다. 원본·원장 지문이 승계 전후 같고 실행/학습/registry가 시작되지 않았음을 마지막으로 확인한다. 새 publication receipt를 exclusive로 저장한다.

## reader·API·화면의 별도 경계

`candidate_quality`는 명시 pointer의3파일 지문과 QA counts/blocker 수·source SHA·빈 scene_split_conflicts를 확인한다. 원문 retained partition, 세 제품 receipt 전체 의미·model 품질을 대신 검증하지 않는다. stale pointer도 pinned cohort로 available할 수 있으며 `source_matches_current_manifest`로 현재 원본과의 일치를 별도로 표시한다.

직접 reader 성공은 API 성공을 뜻하지 않는다. `collection_source_profile`이 선택한 source SHA가 실제 현재 원본과 다르면 source 읽기가 `SOURCE_PROFILE_PIN_MISMATCH`로 차단되고 configured status/budget은 UNCONFIRMED로 닫힌다. Root가 old profile 원바이트를 보존하고 같은 descriptor에서 현재 source SHA를 명시 재결속하기 전에는 API 성공을 보장하지 않는다. pointer 승계가 profile 파일을 자동 수정해서도 안 된다.

Root의 실제 API 응답과 이후 단1회 브라우저 새 조회에서 새 후보 수·현재 source 일치/남은 stale 범위·blockers·예산·승인 아님·콘솔/레이아웃을 별도 검증해야 한다. 273 최종 완료 전이나 profile 재결속 전에는 미래 화면 수치·준비 성공을 확정하지 않는다.

## 인계

Root에 keyword callback 공백과 위 필수 검사를 전달했다. 이 문서는 승계 코드 자체의 구현·실행·정상 게시 근거가 아니다. 새 promotion 파일·pointer/archive·publication JSON·profile 쓰기는 Root만 소유한다. 273 담당의 실제 최종 지문/결과를 받은 뒤 Root가 구체 승인·승계를 수행하고, 실제 UI/공통 이해자료·INDEX·변경 이력에 그 완료 근거를 반영한다.

## 275 준비 코드 독립 검토와 고정핀 재읽기 보완

Root의 새 `priority275-promote-root-20261018.py`를 코드만 읽었다. 최초 읽기에서는11개 output을 먼저 해시한 뒤 candidate/plan/QA·세 receipt를 다시 읽을 때 기대 SHA를 넘기지 않고, pointer3참조 SHA도 나중에 새로 계산하는 공백을 전달했다. 그 사이 출력이 바뀌면 summary가 고정한 버전과 실제 판정/게시하는 버전이 달라질 수 있기 때문이다. 이는 실제 파일 변조를 관측한 것이 아니라 정적 경쟁 경로 검토다.

Root 수정판 SHA는 **`d5ba83bf030a97c85e5570aba9b7b87a6ccda743672254e88ae561c4536f61a8`**다. 수정판 전체를 다시 읽어 다음을 확인했다.

- 하나의 `scope(NAME)` 안에서 approval·terminal·summary·handoff, 역할별11개 output map, source/원장을 읽고 해시한다. file set이 정확히11경로인지 검사한다.
- `output_pin()`이 pinned summary의 SHA만 반환하고, 세 receipt·candidate·plan·QA 재읽기에 그 기대핀을 넘긴다. source도 승인 source SHA로 읽는다.
- pointer files는 같은 summary 고정핀을 사용한다. `os.replace` 직전에 source/candidate/readiness3참조가 그 핀과 같은지 다시 검사한다. 위의 읽기/해시 공백은 해소됐다.
- 세 receipt v2/marker, typed index partition·exact retained 행·QA counts/blockers·mismatch0/conflicts0와 false 권한을 확인한다. 실제 값은273 완료 근거를 읽는 Root 실행 단계에서 결정된다.
- 현재 pointer를 기대 SHA로 읽고 원바이트 archive를 재해시한다. exclusive 새 receipt/temp·measured write·fsync 후 원 pointer/source/원장·잠금 부재와3파일을 재확인하고 replace한다.
- 사후 reader callback은 `json_role` keyword를 받고 `bounded_json_digest`를 사용한다. 같은 scope에서 reader 현재source/count/blocker와 원본·원장 지문을 확인한다. API/브라우저·profile 변경 완료로 주장하지 않는다.

이 수정판의 검토 범위에서는 추가 차단사항을 발견하지 못했다. 기존 실행 환경·원본 hold·동일 출처 지문이 유지된다는 전제이며,273 실완료나 실제 게시를 이번 리뷰가 확인한 것은 아니다. 마지막 결과의 `json_io_before_result_write`는 이름대로 결과 파일 쓰기 전 계측값이므로 최종 전체 I/O라고 오인하지 않아야 한다.

## 276 명시 profile 재결속·API 확인 준비 코드 정적 검토

`profile276-post273-root-20261018.py`도 코드만 읽었다. 검토 SHA는 `01cd78fa391a153740b9a29238ec730c5509c9df052051a466190aa46bbde23d`다. 이 단계는 read-only API 호출과 **명시 profile config 쓰기**가 결합된 Root 소유 작업이다. 전체 작업이 읽기 전용이라는 뜻은 아니다. 독립 검토 담당은 이 코드를 실행하거나 운영 config를 읽지 않았다.

준비 코드는275 publication의 기대 SHA·완료 상태를 먼저 요구하고, 현재 source·원장·candidate pointer·bare pointer 지문을 고정한다. old config의 기대 SHA와 기존 source 지문을 확인한 뒤 원바이트 archive를 남긴다. 같은 config 객체에서 `source_manifest_sha256`만 현재 source로 바꾸므로 descriptor 자동상향이나 다른 profile 선택은 하지 않는다.

새 config temp를 exclusive로 쓰고 measured write·flush/fsync 뒤 old config와 운영4핀을 재확인하여 replace한다. 이어 새 config 지문과 명시 재결속 receipt를 남긴다. source/원장·두pointer·모델·후보QA를 이 단계에서 수정하지 않는다.

그 다음 localhost collection-status GET을1회 수행하고 응답을2MiB로 제한해 원문 증거를 보존한다. 코드의 검사는270에서 이미 확인한 원본 수량/셀 부족, publication이 제시하는 **실제 후보 수**와 source일치/blockers·승인 아님, 기존bare50의 stale·예산/oldpending, 운영4핀과 config 보존을 구분한다. 미래 후보 수를 하드코딩하거나 후보QA를 재실행하지 않는다. 단일 응답 시간은 전체 서비스 SLA가 아니며 브라우저 검증도 false로 남긴다.

검토 범위에서 새로운 차단사항을 발견하지 못했다. 다만 API timeout/HTTP오류/응답검사 실패는 **config가 이미 교체된 후** 발생할 수 있다. 이 경우 archive·재결속 receipt가 profile 적용의 실제 증거이고, API/화면은 미확인으로 남겨야 한다. 전체 작업을 실행 전 차단으로 기록하거나 config를 자동 롤백·재시도하지 않는다. Root가 실제 파일과 결과를 보고 후속을 정한다.

275의 새 approval과276의 publication SHA 인자 발급,273 실제완료 검산, 두 준비 코드의 실행·운영 JSON 읽기는 모두 Root 소유다. 이번 후속 리뷰도 새273 산출물·운영JSON·native·HTTP·승계 실행0을 유지했다. 완료 코드 읽기와 실행 결과 확인을 명확히 구분해 공통 이해자료에 반영해야 한다.
