# 104. 완성 Job 초안과 제공 모델 레코드의 별도 관측 wrapper

상태: **TESTED_SYNTHETIC**. 신규 내부 wrapper·시험·문서만 추가했다. 원 89/94/103, API·UI·등록/실행 회로는 변경하지 않았다. 운영 Job 제출·모델 등록·학습·배포·resolver 연결은 없다.

## 목적과 호출

[compare_workflow_job_model_record_handoff](../../backend/app/workflow_job_model_record_handoff.py)는 기존 완성 Job 초안 전달 검사 [89](89_workflow_job_request_handoff.md)를 **같은 네 인자로 정확히 1회** 호출한다. 그 원 반환 객체를 수정·재구성하지 않고 보존한 뒤, 허용된 단계에서만 model identity와 caller 제공 레코드를 [103](103_model_reference_record_comparison.md)으로 대조한다.

```python
observation = compare_workflow_job_model_record_handoff(
    workflow_request, pinned_workflow_request_sha256, selected_node_id,
    full_job_request, model_record=None)
```

이 wrapper는 별도 내부 함수이며 기존 RFC1/RFC2 endpoint에 연결하지 않는다. [94의 Agent/capability 로컬 등록관계](94_full_job_registration_api.md)를 변경하거나 그 승인 상태에 모델 관측을 섞지 않는다.

## 단계와 exact 12키 출력

| 단계 | status | projection / 103 호출 |
|---|---|---|
| 89가 BLOCKED | `HANDOFF_BLOCKED` | false / 0 |
| 89 MATCH·model_ref 키 없음 | `MODEL_REFERENCE_ABSENT` | false / 0 |
| 89 MATCH·model_ref 키 있음 | `MODEL_REFERENCE_OBSERVED` | true / 1 |

89가 차단되면 wrapper는 **추가로** model_ref나 candidate를 접근하지 않는다. 89 자체가 수행하는 원 schema/model 검사와 이 후속 접근 중단을 구별한다. model_ref가 없을 때도 candidate를 읽지 않는다. 키가 있으면 `id/version/sha256`만 새 exact3 dict로 명시 projection하고 caller `model_record`를 원형 그대로 103에 전달한다.

`model_record=None`이어도 `MODEL_REFERENCE_OBSERVED`와 nested `RECORD_NOT_PROVIDED`다. DB를 조회해 모델이 없음을 확인한 것이 아니다. outer OBSERVED는 **대조 함수를 실행했다는 뜻**이며 nested conflict/invalid/not-comparable/match를 성공·승인 하나로 바꾸지 않는다.

반환은 다음 exact12 키다. 원문 ID·버전·SHA·URI·경로나 candidate를 직접 응답에 추가하지 않는다.

| 키 | 값과 의미 |
|---|---|
| `schema_version` | 정확한 int 1 |
| `scope` | `WORKFLOW_FULL_JOB_MODEL_RECORD_OBSERVATION_ONLY` |
| `status` | 위 세 outer 상태 |
| `full_job_comparison` | 원 89 반환 객체 그대로 |
| `model_reference_comparison` | 103 exact12 또는 null |
| `identity_projection_performed` | 정확한 bool, 103 호출 때만 true |
| `model_comparison_calls` | 정확한 int 0/1, 103 호출 수 |
| `authority_verified` | 항상 bool false |
| `artifact_bytes_verified` | 항상 bool false |
| `execution_authorized` | 항상 bool false |
| `scientific_accuracy_validated` | 항상 bool false |
| `model_verified` | 항상 bool false |

별도 outer issue나 presence 필드는 없다. 단계의 원인은 nested 원 결과에서 확인한다. 89의 기존 24 false와 metadata 비교·schema·bbox·hash 결과를 수정하지 않는다. 다섯 outer false는 이 관측의 미검증 범위이며 기존 모델 레코드의 과학·승인 값을 false로 바꾸는 것이 아니다.

카운터도 구별한다. 원 89의 `comparator_calls`는 내부 metadata comparator 86의 호출 수다. 새 `model_comparison_calls`는 103 호출 수이고, 103의 `inspection_calls`는 100 내부 관측 호출 수다. 어느 것도 DB·파일 조회 수나 실제 모델 resolver 실행을 뜻하지 않는다. 89·103 예외는 이 순수 wrapper에서 전파하며, 후속 API의 안전 오류 정책을 새로 만들지 않는다.

## role·URI·원형 보존

projection은 full GMAIS model_ref를 새 계약으로 검증하는 동작이 아니다. 원 89가 먼저 원 schema·bbox·model 문자·metadata 전달 등을 검사하고 MATCH한 선언만 exact3로 추출한다. explicit null은 원 schema에서 차단되므로 optional 부재로 바꾸지 않는다.

선택적 role은 기존 96 문자 검사를 거친다. URI는 원 schema의 문자열 조건과 전체 JSON 한도만 확인하며 **URI 정체·로컬/원격 정책·실재 파일·접근 권한을 검증하지 않는다**. role/URI는 103 identity에서 제외하고 해결·조회하지 않는다. id/version/sha256도 trim·보정 없이 원형으로 전달한다. dataset_version으로 모델 버전을 추정하거나 기존 레코드를 역채움하지 않는다.

## I/O와 신뢰 한계

wrapper가 추가하는 Store·artifact·network·resolver·등록·실행 I/O는 0이다. 단, 원 89의 cached schema factory는 cold path에서 vendored `job-request.schema.json`을 읽을 수 있다. 이를 wrapper 전체가 언제나 파일 읽기0인 것으로 보고하지 않는다.

시험에서는 cache를 비운 후 첫 실제 호출의 `Path.read_text`를 계측해 schema 1회를 확인하고 warm 호출에서는 추가 읽기0을 확인했다. 이후 warm 상태에서 Path.open·Store get/list/put·network를 차단한 호출도 같은 결과다. 이 측정은 시험의 cold/warm 근거이며 반환된 원 89의 `schema_files_read=null`을 0이나 1로 바꾸지 않는다. 원 89의 source/DB 등 기존 계측0과 schema 미계측 null도 그대로 유지한다.

같은 shape/source로 위조·복사한 레코드도 metadata가 맞으면 nested `MATCH_UNVERIFIED`일 수 있다. 파일 바이트를 재검증하지 않으며 실제 모델 사용·과학·실행 승인을 부여하지 않는다. outer OBSERVED, inner89 MATCH, nested103 MATCH_UNVERIFIED의 세 의미를 구별해야 한다.

## 시험과 근거

[신규 시험](../../tests/test_workflow_job_model_record_handoff.py)은 다음을 검증한다.

- mock 89의 exact 인자·정확1회·원 반환 객체 동일성, BLOCKED 뒤 poison model_ref/candidate 접근0, MATCH·참조부재 candidate 접근0.
- exact3 projection과 원형 candidate 전달·입력 불변, 실제 89 원 결과/24 false 동등.
- 실제 decimal·URI 문자열 입력과 date/null/role/alias/bbox/schema/resource·pin 차단. URI 허용은 문자열 계약의 증거이며 URI 실체 검증이 아니다.
- 실제로 도달하는 103의 미제공·레코드오류·충돌·비교불가·미검증일치 다섯 상태에도 outer OBSERVED/다섯 false를 유지한다. 103의 `REFERENCE_INVALID`는 89 MATCH 뒤 정상 projection에서는 도달하지 않으므로 **6상태 mock embed 시험**과 실제 다섯 상태 시험을 구별한다.
- cold/warm schema 읽기 계측, wrapper 추가 I/O0, candidate unknown 순환 무복제/무해결, 89/103 예외 전파.

```powershell
# 프로젝트 루트, PYTHONPATH=.runtime;backend;tests
python -m unittest test_workflow_job_model_record_handoff -v
python -m unittest test_workflow_job_model_record_handoff test_workflow_job_request_handoff test_model_reference_record_comparison test_model_registration_provenance test_workflow_job_registration_handoff -v
```

- 집중 신규 **12 PASS / 0.128초**: [집중 로그](../../evidence/integration/workflow-model-record-focused-20261017.log).
- 관련 **61 PASS / 0.887초**: [관련 로그](../../evidence/integration/workflow-model-record-related-20261017.log). 신규12개는 관련 묶음에 포함된다. 독립 시험·원본/바이트 보존은 Root 근거로 구분한다.
- 새 미연결 wrapper이므로 관련·독립 시험과 기존 byte 보존을 검증하고 이번 전체 backend/frontend·build·브라우저는 재실행하지 않는다. 직전 전체1019건/1018 PASS/기존1 SKIP/381.288초는 이전101/102 증거이며 이번 새 전체 회귀 결과가 아니다.

## UI 인계와 다음 범위

기존 API·UI와 연결하지 않았으므로 새 화면 응답·판정 변화가 없다. 직접 프론트 수정·build·브라우저 재시험이 필요하지 않으며 테스트 코드 반영을 실행 서버/UI 적용으로 표시하지 않는다.

후속 명시 선택형 진단을 연결한다면 outer 단계와 embedded89/103의 상태·미검증 flag를 구별하고 candidate 출처·진정성·개체 선택 정책을 별도로 검토해야 한다. 자동 Registry 조회·모델 선택·원형 보정·운영 Job 제출·gate 우회는 이번 범위 밖이다.

## Root 최종 검증·보존

[독립시험](../../evidence/integration/workflow-model-record-independent-20261017.log)은12 PASS/0.182초다. [보존검사](../../evidence/integration/workflow-model-record-live-integrity-20261017.json)는보호141·core72·기존제품·이전증거721·catalog14 변경0을확인했다. [실제catalog관측](../../evidence/integration/workflow-model-record-catalog-observation-20261017.json)은보존만검사했으며새wrapper의운영Workflow입력시험이아니다. 새기능의실행근거는합성시험으로한정한다. 전체backend/frontend/build/browser는이번재실행하지않았다. 기존API/화면/RFC1/2미연결·기존파일byte불변과UI영향읽기근거를유지했다.

다음은기존형식을바꾸지않는별도읽기전용wrapperAPI의계약검토이며endpoint/UI추가·실제Registry조회/모델선택/resolver·신원/기관권위/실행승인은아직구현하지않았다.

### 105/106 후속 연결 및 검증

별도 비변경 진단 API와 수동 UI를 연결했다. 기존 RFC1/RFC2 결과·승인 경계를 유지한다. 새 계약·원문/한도·생산과 검증 호출 수·실제/합성 시험 및 한계는 [API105](105_workflow_job_model_record_handoff_api.md), [UI106](106_workflow_model_record_handoff_ui.md)를 따른다. 최종 전체 회귀·브라우저·보존 근거는 `evidence/integration/workflow-model-record-api-live-integrity-20261017.json`과 `evidence/integration/workflow-model-record-api-live-ui-20261017.json`이다. 이해자료·인계서도 같은 단위로 갱신했다. metadata 일치는 실바이트·권위·과학/실행 승인이 아니며 운영 Job 생성/등록은 없다.
