# 100. 로컬 모델 등록 메타데이터의 순수 정합성 관측

상태: **TESTED_SYNTHETIC**. 새 내부 helper와 합성 시험만 추가했다. 기존 API·등록 함수·resolver·UI에는 연결하지 않았다. 운영 등록·역채움·수집·학습·배포는 없다. Root의 실제 catalog 읽기 관측은 별도 증거로 구분한다.

## 무엇을 관측하는가

[inspect_model_registration_provenance(record)](../../backend/app/model_registration_provenance.py)는 이미 메모리에 있는 모델 레코드에서 선언과 부모 필드가 서로 일치하는지만 관측한다. Store·파일·network·resolver를 호출하지 않는다. 경로를 따라가거나 checkpoint/report hash를 재계산하지 않는다. 결과에 레코드 ID·버전·hash 원문·경로를 복사하지 않는다.

97~99의 `model_version_declaration`은 caller 메타데이터다. 레코드 안의 값이 모두 맞아도 실제 파일·원본 인증·명시 API 호출의 진정성을 확인한 것이 아니다. 같은 필드가 복사되거나 위조될 수 있으므로 최고 상태도 **CONSISTENT_UNVERIFIED**다. 이 helper를 등록 권위나 모델 resolver의 승인 근거로 사용하지 않는다.

```python
observation = inspect_model_registration_provenance(model_record)
```

## 입력과 검사 순서

정확한 builtin `dict`만 받는다. `id`는 [96 공통 문자 검사](../../backend/app/model_reference_contract.py)에 `version='v1'`과 함께 전달해 검증한다. 실제 관측 ID는 `record['id']`만 사용하며 `model_id`, `dataset_version`, 승인·상태 필드는 읽지 않는다. ID가 유효하고 선언 키가 없으면 즉시 `ABSENT`이며 부모 hash나 선택적 top-level version을 검사하지 않는다.

선언 키가 있으면 `None`도 부재로 바꾸지 않는다. 정확한 dict·**정확히 5키**인지 길이부터 확인하고 다음을 검사한다.

| 선언 키 | 요구 조건 |
|---|---|
| `schema_version` | 정확한 int `1`; bool·float 제외 |
| `source` | 정확한 str `CALLER_EXPLICIT_REGISTRATION` |
| `version` | 96의 1~256자·공백/제어문자/surrogate 제외·latest/current 차단 |
| `checkpoint_sha256` | 정확한 str, 소문자 16진수 64자 |
| `training_report_sha256` | 정확한 str, 소문자 16진수 64자 |

선언이 유효하면 부모의 `checkpoint_sha256`, `training_report_sha256`, 선택적 `model_version` 순으로 **존재하는 값의 형식을 모두 먼저** 검사한다. 부모 version도 96을 사용한다. 형식이 잘못되면 binding을 비교하지 않고 모두 `NOT_CHECKED`로 반환한다.

형식 검사 후 원형 값의 정확한 일치를 비교한다. trim·정규화·추정은 없다. 따라서 선언 `" v2 "`와 부모 `"v2"`는 충돌이다. 부모 두 hash의 부재는 `MISSING`, top-level version의 부재는 정상 `NOT_RECORDED`다. 충돌이 하나라도 있으면 다른 hash의 부재보다 우선한다. 충돌 우선순위는 checkpoint→training report→version이고, 부재 우선순위는 checkpoint→training report다.

알 수 없는 필드는 순회·복제·직렬화하지 않는다. 큰 값이나 순환 참조가 있어도 선택 필드 외에는 관측하지 않는다. 외부 요청 전체를 검증하는 JSON parser나 임의 객체의 진정성을 확인하는 도구는 아니다.

## 고정 출력 계약

결과는 다음 **exact 10키**다. 각 binding은 `NOT_CHECKED`, `MATCH`, `MISMATCH`, `MISSING`, `NOT_RECORDED` 중 해당 값이다.

```json
{
  "schema_version": 1,
  "scope": "LOCAL_MODEL_REGISTRATION_METADATA_OBSERVATION_ONLY",
  "status": "CONSISTENT_UNVERIFIED",
  "declaration_present": true,
  "bindings": {
    "checkpoint_sha256": "MATCH",
    "training_report_sha256": "MATCH",
    "model_version": "NOT_RECORDED"
  },
  "issue": null,
  "authority_verified": false,
  "artifact_bytes_verified": false,
  "execution_authorized": false,
  "scientific_accuracy_validated": false
}
```

`declaration_present`는 정확한 dict에서 키 존재 여부이며, 입력이 dict가 아니면 `null`이다. bad ID라도 dict에서 관측한 키 존재 여부는 표시한다. `issue`는 `null` 또는 exact `{code, field}`의 고정 문자열이며 입력 값을 노출하지 않는다. 네 승인/검증 flag는 모든 상태에서 항상 bool `false`다.

| 상태 | 의미 | binding/issue |
|---|---|---|
| `ABSENT` | 유효 ID, 선언 키 없음 | 모두 NOT_CHECKED, issue null |
| `INVALID` | record/ID/선언/존재하는 부모 값의 형식 오류 | 모두 NOT_CHECKED, 첫 오류 |
| `RECORD_CONFLICT` | 유효한 필드끼리 원형 값 불일치 | 모든 binding 계산, 첫 충돌 |
| `PARENT_BINDING_UNKNOWN` | 충돌은 없으나 부모 hash가 빠짐 | 모든 binding 계산, 첫 누락 |
| `CONSISTENT_UNVERIFIED` | 두 부모 hash 일치, 선택적 version도 있으면 일치 | issue null, 인증·실파일 미검증 |

고정 issue 코드는 다음과 같다.

| 코드 | field |
|---|---|
| `RECORD_INVALID` | `record` |
| `MODEL_REFERENCE_INVALID` | `id`, `model_version_declaration.version`, `model_version` 중 검사 대상 |
| `MODEL_VERSION_NOT_PINNED` | `model_version_declaration.version` 또는 `model_version` |
| `DECLARATION_SCHEMA_INVALID` | `model_version_declaration`, `.schema_version`, `.source` |
| `SHA256_INVALID` | 선언의 `.checkpoint_sha256`/`.training_report_sha256`, 또는 부모 동명 필드 |
| `RECORD_BINDING_CONFLICT` | `checkpoint_sha256`, `training_report_sha256`, `model_version` |
| `PARENT_BINDING_MISSING` | `checkpoint_sha256`, `training_report_sha256` |

## 시험과 보존 범위

[신규 시험](../../tests/test_model_registration_provenance.py)은 잘못된 타입/null/bool·문자/별칭·선언 추가 키·hash·부모 부재·충돌과 부재의 우선순위·위조 정합 레코드·입력 불변·IO 차단을 확인한다. unknown 순환 참조와 큰 값에 대해 deepcopy/JSON 직렬화를 금지해도 동작한다. 97의 tiny checkpoint/TempStore 명시 등록 결과를 연결한 뒤 실제 checkpoint 파일을 바꿔도 관측 결과는 같음을 확인했다. 이는 실파일 재검증이 없다는 한계의 시험이며 변경된 모델을 승인한 것이 아니다.

```powershell
# 프로젝트 루트, PYTHONPATH=.runtime;backend;tests
python -m unittest test_model_registration_provenance -v
python -m unittest test_model_registration_provenance test_model_version_declaration test_model_reference_contract test_model_version_registration_api test_experiment_registry -v
```

- 집중 신규 **12 PASS / 0.302초**: [집중 로그](../../evidence/integration/model-provenance-focused-20261017.log).
- 관련 묶음 **47 PASS / 13.447초**: [관련 로그](../../evidence/integration/model-provenance-related-20261017.log). 신규 12개는 관련 묶음에 포함된다. 독립 검토·실제 읽기 관측·보존은 Root 근거로 구분한다.
- 기존 제품 소스 변경은 0이며 새 helper/test/문서만 추가한다. 이번에는 관련·신규·독립 시험과 기존 바이트 보존으로 검증하며 전체 backend 회귀는 다시 실행하지 않는다. 직전 전체 998건/997 PASS/기존 1 SKIP/366.134초는 **이전 98/99 증거**이며 이번 새 전체 회귀 통과 수치가 아니다.

## UI·다음 연결

현재 API·UI에서 이 함수를 호출하지 않는다. 따라서 화면 계약 변화가 없고 프론트 수정·build·브라우저 재시험이 필요하지 않다. 함수 코드·합성 검증과 실행 중 서버 적용을 구분한다. 기존 등록 UI와 운영 데이터는 그대로 유지한다.

후속 진단 API/UI를 연결한다면 다섯 관측 상태와 항상 false인 권위/실파일/실행/과학 검증을 구별하고, 값이 맞는다는 이유로 원본 인증·모델 사용 승인으로 표현하지 않아야 한다. 실제 resolver·역채움·전역 불변성·트랜잭션 보장은 이번 범위 밖이다.

## Root 최종 통합·실제 읽기 관측

[독립 로그](../../evidence/integration/model-provenance-independent-20261017.log)는12 PASS/0.185초다. [실제 catalog 읽기](../../evidence/integration/model-provenance-catalog-observation-20261017.json)에서 모델1의 선언은ABSENT/NOT_CHECKED이며 catalog14의원문SHA는전후동일했다. 관측의4false는이helper가권위·실바이트·과학·실행을검증하지않았다는뜻이며 기존모델필드의값을수정하거나원래부재/null을false로확정한것이아니다.

[보존 검사](../../evidence/integration/model-provenance-live-integrity-20261017.json)의보호141·core70·기존제품파일·이전증거662는변경0이다. UI담당은새endpoint/화면호출이없어직접UI변경불필요를읽기확인했다. 전체회귀·프론트/build/browser는이번재실행하지않았다. 독립담당은계약검토후대기상태여서Root가실제상태확인후시험실행을followup으로다시배정했고,최종통과수치는실제실행로그만사용한다. 운영등록/Job/수집/정식학습/배포0을유지했다.

## 101/102 읽기 전용 API·화면 후속

[API101](101_model_registration_provenance_api.md)과 [UI102](102_model_registration_provenance_ui.md)는100pure관측을기존선택모델에서수동조회하게연결한다. 5상태200·기존auth/404·고정503,응답상태/binding/issue·4false정합과세대방어를적용했다. 실제API/브라우저는기존모델ABSENT와없는모델404를읽기확인했고등록/실행/승인0이다. 타상태와오염·지연응답은합성시험만이다. [통합시험·보존](../../evidence/integration/model-provenance-api-live-integrity-20261017.json)과 [실제화면](../../evidence/integration/model-provenance-api-live-ui-20261017.json)을따른다. 관측4false는기존모델필드변경이아니며세대방어는응답모델신원인증이아니다. 기존선택시readiness의실파일검증과새metadataendpoint의artifact읽기0은구분한다.

## 103 별도 내부 identity 비교 후속

[명시 identity 대조](103_model_reference_record_comparison.md)는전체GMAIS model_ref가아닌명시추출exact3 id/version/sha256와호출자가제공한레코드만비교한다. 역할/URI·전체Job검증이나record선택/Registry조회는수행하지않는다. 같은id의100관측이일치미검증인때만버전/SHA를비교하고최고상태도MATCH_UNVERIFIED·권위/실바이트/과학/실행/model_verifiedfalse다. None은RECORD_NOT_PROVIDED이며실DBNotFound조회와다르다. 기존Workflow89·94/등록/관측API/UI호출은미연결·기존출력/falseflags불변이다. [합성시험·보존근거](../../evidence/integration/model-reference-record-live-integrity-20261017.json)를따르며이번전체/frontend/build/browser재시험은없다.
