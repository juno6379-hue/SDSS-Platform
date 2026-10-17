# 103. 명시 모델 identity와 제공된 레코드의 순수 대조

상태: **TESTED_SYNTHETIC**. 새 순수 helper·시험·문서만 추가했다. 기존 제품 소스·API·UI·원 schema·등록/승인 gate는 변경하지 않았다. 운영 등록·조회·실행이나 실제 파일 검증을 수행하는 기능이 아니다. Root의 실제 읽기 관측은 별도 근거로 구분한다.

## 목적과 입력의 구분

[compare_model_reference_record(reference_identity, model_record=None)](../../backend/app/model_reference_record_comparison.py)는 호출자가 **명시적으로 추출한 identity**와 호출자가 제공한 레코드를 대조한다. identity는 exact 3키 `id/version/sha256`다. 원 GMAIS `model_ref`는 이 세 키 외에 선택적 `uri/role`을 허용하므로, full `model_ref`를 이 함수에 그대로 넣는 계약이 아니다. 함수가 Job에서 필드를 자동 추출하거나 optional model_ref 부재를 해석하지 않는다.

```python
identity = {'id': declared_id, 'version': declared_version, 'sha256': declared_sha256}
comparison = compare_model_reference_record(identity, supplied_model_record)
```

`reference_identity=None`은 `REFERENCE_INVALID`다. 반대로 candidate 인자 생략 또는 `None`은 `RECORD_NOT_PROVIDED`이며 **DB를 조회했으나 없다는 뜻이 아니다**. 이 함수는 조회를 수행하지 않는다. resolver·고정 모델 버전의 권위 등록·whole Job 검증·파일/Store/network 호출은 없다. dataset_version을 읽거나 모델 버전으로 대체하지 않는다.

## 검사와 대조 순서

1. identity가 정확한 builtin dict·정확히 3키인지 길이부터 검사한다. [96 공통 문자 계약](96_model_reference_contract.md)으로 id/version을 검사한 뒤 SHA가 정확한 str·소문자 hex64인지 검사한다. 참조가 잘못되면 candidate는 관측하지 않는다.
2. candidate가 None이면 미제공, 비dict면 `RECORD_INVALID`다. candidate의 `id`만 96으로 검사한다. 유효 id끼리 원형 값이 다르면 `REFERENCE_CONFLICT`이며 100 관측을 호출하지 않는다.
3. id가 같을 때만 [100 관측](100_model_registration_provenance_observation.md)을 **정확히 1회** 호출해 결과를 그대로 embed한다. intrinsic 상태가 `CONSISTENT_UNVERIFIED`가 아니면 `REFERENCE_NOT_COMPARABLE`이며 version/SHA는 비교하지 않는다. embedded 100의 ABSENT/INVALID/RECORD_CONFLICT/PARENT_BINDING_UNKNOWN으로 이유를 구분한다.
4. intrinsic이 `CONSISTENT_UNVERIFIED`일 때만 identity version과 선언 version, identity sha256와 선언 checkpoint_sha256를 비교한다. 두 binding을 모두 계산하고, 불일치 issue는 version→SHA 순으로 하나 반환한다. 모두 같으면 `MATCH_UNVERIFIED`다.

모든 비교는 원문까지 정확히 같아야 한다. trim·정규화·dataset version 추정이 없다. 예를 들어 `" v2 "`와 `"v2"`는 다른 선언이다. 100 예외는 조용히 상태로 바꾸지 않고 전파한다. 후속 API가 있다면 안전 오류 경계는 그 API가 책임져야 한다.

## exact 12키 출력

```json
{
  "schema_version": 1,
  "scope": "DECLARED_MODEL_IDENTITY_TO_SUPPLIED_RECORD_ONLY",
  "status": "MATCH_UNVERIFIED",
  "bindings": {"id": "MATCH", "version": "MATCH", "sha256": "MATCH"},
  "record_provenance": {
    "schema_version": 1,
    "scope": "LOCAL_MODEL_REGISTRATION_METADATA_OBSERVATION_ONLY",
    "status": "CONSISTENT_UNVERIFIED",
    "declaration_present": true,
    "bindings": {"checkpoint_sha256": "MATCH", "training_report_sha256": "MATCH", "model_version": "NOT_RECORDED"},
    "issue": null,
    "authority_verified": false,
    "artifact_bytes_verified": false,
    "execution_authorized": false,
    "scientific_accuracy_validated": false
  },
  "issue": null,
  "inspection_calls": 1,
  "authority_verified": false,
  "artifact_bytes_verified": false,
  "execution_authorized": false,
  "scientific_accuracy_validated": false,
  "model_verified": false
}
```

`record_provenance`는 100의 exact10 객체 또는 `null`이다. 출력에 참조/레코드 ID·버전·SHA 원문·경로를 넣지 않는다. `inspection_calls`는 정확한 int 0/1이며 **100 함수 호출 수**다. DB·파일 조사 횟수나 실제 모델 검증의 증거가 아니다.

| status | bindings와 embedded 관측 |
|---|---|
| `REFERENCE_INVALID` | 모두 NOT_CHECKED, provenance null, calls0 |
| `RECORD_NOT_PROVIDED` | 모두 NOT_CHECKED, provenance null, calls0 |
| `RECORD_INVALID` | 모두 NOT_CHECKED, provenance null, calls0 |
| `REFERENCE_CONFLICT` | id가 다르면 id MISMATCH/나머지 NOT_CHECKED·calls0; same id이면 모두 비교·100 embed·calls1 |
| `REFERENCE_NOT_COMPARABLE` | id MATCH·나머지 NOT_CHECKED, 100 embed·calls1 |
| `MATCH_UNVERIFIED` | 세 binding MATCH, 100 embed·calls1 |

`issue`는 null 또는 exact `{code, field, side}`의 고정 문자열이다. 입력 값을 echo하지 않는다.

| 오류 | code | field / side |
|---|---|---|
| identity shape | `REFERENCE_IDENTITY_INVALID` | `reference_identity` / REFERENCE |
| identity 문자/별칭 | `MODEL_REFERENCE_INVALID` 또는 `MODEL_VERSION_NOT_PINNED` | `reference_identity` / REFERENCE |
| identity SHA | `SHA256_INVALID` | `sha256` / REFERENCE |
| candidate None | `RECORD_NOT_PROVIDED` | `model_record` / RECORD |
| candidate 타입 | `RECORD_INVALID` | `model_record` / RECORD |
| candidate ID 문자 | `MODEL_REFERENCE_INVALID` | `id` / RECORD |
| ID 불일치 | `ID_MISMATCH` | `id` / COMPARISON |
| intrinsic 100이 정합 미검증 상태가 아님 | `REGISTRATION_NOT_COMPARABLE` | `model_version_declaration` / RECORD |
| version 불일치 | `VERSION_MISMATCH` | `version` / COMPARISON |
| checkpoint SHA 불일치 | `CHECKPOINT_SHA256_MISMATCH` | `sha256` / COMPARISON |

## 미검증과 승인 경계

다섯 flag는 모든 상태에서 항상 정확한 bool false다. 이는 이 진단이 권위·artifact 바이트·실행·과학·모델 검증을 하지 않았다는 뜻이다. 기존 모델의 승인 필드를 false로 변경하거나 독립 평가를 무효화하는 것이 아니다.

위조·복사된 레코드와 참조도 메타데이터끼리 일치하면 `MATCH_UNVERIFIED`일 수 있다. 실제 파일을 바꾼 뒤에도 제공한 레코드/identity가 그대로면 결과는 같다. 따라서 MATCH를 실제 모델 존재·권위 버전·원본 인증·정합 checkpoint·사용 허가나 실행 준비로 해석하지 않는다. raw 선언 shape/source나 SHA 값의 동등성만으로 인증할 수 없다는 97~100의 한계도 유지한다.

관련 없는 레코드 필드는 순회·복제·직렬화하지 않는다. 거대한 unknown 값과 순환 참조도 읽지 않으며 `model_id`, dataset_version, status/approval 등의 값을 근거로 사용하지 않는다. 함수를 외부 전체 요청 parser나 모델 resolver로 부르지 않는다.

## 시험과 증거

[신규 시험](../../tests/test_model_reference_record_comparison.py)은 exact3·타입/길이/문자/별칭/SHA·None candidate·ID 오류/불일치 미호출·same-id 100 정확1회·4비정합 intrinsic 상태의 embed·version/SHA 모두 계산과 issue 우선순위·원형 패딩·위조 정합·입력 불변/순환 unknown 무순회·I/O 차단·예외 전파를 확인한다.

97의 작은 합성 report/checkpoint·TempStore 등록 결과와도 연결해 MATCH_UNVERIFIED를 확인했다. 이후 파일 변조에도 관측 결과가 같은 것은 실파일 미검증 한계를 확인한 시험이다. 운영 모델을 변조하거나 승인한 것이 아니다.

```powershell
# 프로젝트 루트, PYTHONPATH=.runtime;backend;tests
python -m unittest test_model_reference_record_comparison -v
python -m unittest test_model_reference_record_comparison test_model_registration_provenance test_model_reference_contract test_model_version_declaration test_experiment_registry -v
```

- 집중 신규 **14 PASS / 0.381초**: [집중 로그](../../evidence/integration/model-reference-record-focused-20261017.log).
- 관련 **50 PASS / 16.590초**: [관련 로그](../../evidence/integration/model-reference-record-related-20261017.log). 신규 14개는 관련 묶음 안에 포함된다. 독립 시험·실제 읽기 관측·byte 보존은 Root의 근거로 구분한다.
- 미연결 pure helper 추가이므로 관련·독립 시험과 기존 바이트 보존을 검증하고 이번 전체 backend/frontend·build·브라우저는 재실행하지 않는다. 직전 전체 backend 1019건/1018 PASS/기존1 SKIP/381.288초는 **이전 101/102 근거**이며 이번 새 전체 통과 수치가 아니다.

## UI 인계·다음 범위

기존 API/UI·Workflow/Job 실행 회로에서 이 함수를 호출하지 않는다. 새 화면 상태나 응답 변화가 없어 직접 프론트 수정·build·브라우저 재시험이 필요하지 않다. 제품 연결·실행 서버 적용을 구현했다고 보고하지 않는다.

후속 API/UI를 설계한다면 identity의 명시 추출, candidate 미제공과 실제 조회 부재의 구별, embedded 100 상태, 언제나 false인 다섯 검증 축을 별도로 보여줘야 한다. 실제 resolver·권위 있는 등록 증거·승인·역채움·자동 모델 선택은 이번 범위 밖이다.

## Root 최종 검증·보존

[독립시험](../../evidence/integration/model-reference-record-independent-20261017.log)은14 PASS/0.319초다. [보존검사](../../evidence/integration/model-reference-record-live-integrity-20261017.json)는보호141·core71·기존제품파일·이전증거706·catalog14 변경0을확인했다. [실제catalog관측](../../evidence/integration/model-reference-record-catalog-observation-20261017.json)은모델1/버전선언0의보존관측일뿐새비교함수의운영입력시험이나실Workflow참조시험이아니다. 새비교는합성시험만TESTED_SYNTHETIC이며dataset_version를대신넣거나허구의pin을만들지않았다.

기존API/UI/Workflow89·94/등록·승인경로미연결을UI담당이읽기확인했다. 이번전체backend/front/build/browser재실행없음과이전1019회귀근거를구분한다. 다음은89의정상MATCH검토뒤에만optionalmodel_ref를명시추출해103에전달할별도wrapper계약검토이며아직구현0이다.

## 104 별도 내부 Workflow 모델 대조 연결

[연결함수104](104_workflow_job_model_record_handoff.md)는원89결과를그대로유지하며정상MATCH뒤에모델참조가있을때만exact3 identity를추출해103과호출자제공레코드를대조한다. 89차단후wrapper추가접근/1030,참조부재1030,참조존재1031회다. outerOBSERVED는대조수행관측일뿐일치·승인이아니고nested103과5false로한계를구분한다. 기존89/94/RFC1/2·103/API/UI출력은변경하지않았다. URI해결·Registry/resolver·바이트검증·기관/실행승인0이다. 원89coldschema읽기와wrapper추가IO0은구분한다. [관련·독립시험/보존](../../evidence/integration/workflow-model-record-live-integrity-20261017.json)은합성근거이며운영Workflow참조시험이아니다. 이번전체/frontend/build/browser재시험없음도이전전체근거와구분한다.
