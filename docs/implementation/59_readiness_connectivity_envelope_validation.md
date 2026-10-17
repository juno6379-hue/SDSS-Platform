# 59. 연결 witness의 순수 canonical envelope 계약

## 쉬운 설명과 상태

이 도구는 향후 caller가 공급할 적격 scene 메타데이터와 제한된 연결 witness를 하나의 재현 가능한 JSON bytes 구조로 묶는다. 파일이나 데이터베이스에 저장하지 않는다. source report/manifest/reference SHA를 기재해도 해당 파일의 실제성·적격성은 확인하지 않는다. helper SHA 역시 **caller 선언과 외부 pin 일치만** 확인하며 실행 중인 helper 코드 파일을 몰래 읽지 않는다.

`TESTED_SYNTHETIC` 구현이다. 현재 실제 saved report의 scene witness 부재를 확인한 Root의 None envelope byte 왕복은 별도 증거로 기록한다. 기존 readiness.assess/gate/policy, 적격 scene 추출·과거 원인 복구는 이 기능에 연결하지 않았다. 전체 결과는 BLOCKED, ready/scientific/실행·정산·자동재개 승인 false, 환불 0이다.

## 함수

```python
build_readiness_connectivity_envelope(
    eligible_scenes, province_splits=None, *, provenance,
    helper_sha256, expected_helper_sha256, limits=None,
)
validate_readiness_connectivity_envelope(
    envelope, *, expected_helper_sha256,
    expected_provenance, expected_input_sha256,
)
encode_readiness_connectivity_envelope(envelope, **external_pins)  # -> bytes
decode_readiness_connectivity_envelope(raw, **external_pins)       # -> detached dict
```

build는 caller metadata를 복사하고 58 helper를 한 번 실행한다. validate는 모든 pin·digest·구조를 확인한 다음 같은 입력으로 58 helper를 다시 실행해 witness 전체를 typed exact 비교한다. encode/decode도 validate를 수행하므로 helper 재계산을 포함한다. 동일 dictionary key 순서는 canonical encoding으로 통합하지만 scene 리스트 순서·배열 순서·literal 문자열·int/float/bool은 구별한다. 기존 파일·픽셀·GEOS·네트워크·readiness.assess 호출은 없다.

## 정확한 schema v1

모든 객체의 unknown key는 거부한다. 입력 scene은 58의 필수 5키만 허용한다. witness는 helper 재계산 전체와 일치해야 하므로 추가·누락 필드도 거부된다.

| 필드 | 계약 |
|---|---|
| `schema_version` | int 1, bool 금지 |
| `kind` | READINESS_CONNECTIVITY_WITNESS_ENVELOPE |
| `status` | BLOCKED |
| `canonical_protocol` | PYTHON_JSON_UTF8_SORT_KEYS_COMPACT_V1 |
| `helper_sha256` | caller가 선언한 lowercase 64hex, 외부 expected helper SHA와 일치 |
| `provenance` | 아래 3개 SHA/null 필드의 정확한 객체 |
| `provenance_sha256` | provenance canonical bytes SHA256 |
| `input` | eligible_scenes / province_splits / limits의 정확한 객체 |
| `input_sha256` | input 전체 canonical bytes SHA256, 외부 expected input SHA와 일치 |
| `witness` | 58 helper 전체 반환 객체 |
| `witness_sha256` | witness canonical bytes SHA256 |
| `envelope_sha256` | 이 필드만 제외한 나머지 envelope 전체 canonical bytes SHA256 |

provenance는 정확히 `source_report_sha256`, `source_manifest_sha256`, `eligible_scene_reference_sha256`를 갖는다. 각 값은 lowercase 64hex 또는 null이다. 이름·값을 추측하거나 fallback하지 않는다. scene 입력이 None이어도 nonnull reference SHA를 기재할 수 있으나 **hash 주장은 scene 내용 존재의 증명이 아니며** 결과는 계속 UNKNOWN_NOT_PERSISTED이다. Root의 현재 부재 확인 예시는 report/manifest SHA 명시·eligible_scene_reference_sha256=null을 사용한다.

input의 eligible_scenes는 null 또는 list이며 각 행은 `scene_index`, `province`, `source_group`, `scene_id`, `bounds_wgs84`만 갖는다. province_splits는 58이 지원하는 caller 고정 mapping 또는 None 입력시 null이다. limits는 `max_scenes`, `max_bbox_pairs`, `max_witness_edges`만 가진다. 기본값은 2000/1000000/10000이다. helper의 scene/province/string/좌표/identity/순서/typed limit 계약을 그대로 적용한다. 순서를 바꾸면 last token owner가 달라질 수 있으므로 scene list를 정렬하지 않는다. literal bbox의 `12`와 `12.0`도 input digest가 다르다.

추가 공통 필드는 다음 값으로 고정된다.

- provenance_claim=CALLER_ASSERTED_HASHES_NOT_FILE_VERIFIED, helper_binding_claim=CALLER_DECLARED_PIN_NOT_EXECUTING_CODE_VERIFIED.
- provenance_verified / executing_helper_code_verified / eligibility_verified / historical_readiness_cause_reconstructed / ready_for_training / scientific_accuracy_validated / training_executed / training_split_leakage_resolved / settlement_authorized / execution_authorized / automatic_resume_allowed = 모두 bool false.
- proposed_refund_bytes / source_files_read / source_files_written / network_requests = 모두 int 0.
- exactly_once_applied=UNKNOWN.

이 공통 필드까지 schema 전체에 포함된다. 숫자 0을 false로 바꾸거나 반대로 바꾸면 typed mismatch로 거부한다.

## 외부 pin과 신뢰 경계

validate/encode/decode의 expected_helper_sha256·expected_provenance·expected_input_sha256는 caller의 **독립적인 외부 신뢰 기준**이어야 한다. 동일 envelope에서 이 값을 꺼내 그대로 expected로 재사용하면 전체 입력·lineage를 재작성한 공격에 대한 보호가 사라진다. build 직후 caller가 원래 전달한 input의 digest를 별도로 계산·보관하거나 신뢰한 채널로 전달하는 연결은 caller 책임이다. 내부 envelope hash는 자체 무결성에 쓰이며 출처 인증 서명이 아니다.

공격자가 witness를 바꾸고 witness/envelope SHA를 모두 재계산해도 helper 재실행 결과와 다르면 거부된다. source report/manifest/reference를 바꾸고 self digest를 재계산해도 외부 provenance pin이 다르면 거부된다. scene index/순서/token/bbox/policy/limits를 바꾸고 digest를 다시 만들면 외부 input pin과 달라져 거부된다. helper 선언 SHA 일치는 실제 코드 파일의 동일성 검증이 아니므로 executing_helper_code_verified는 항상 false이다.

None과 빈 list는 다른 input digest와 다른 witness 상태를 가진다. None은 UNKNOWN_NOT_PERSISTED / union_complete=false이고, 빈 list는 NO_SUPPLIED_ELIGIBLE_SCENES다. 저장 witness 한도 0 또는 truncation 역시 원래 입력 limits와 전체 helper 반환값에 포함된다. 저장 edge 일부가 없더라도 전체 prescribed union 완료가 가능하다는 58의 구분을 유지하며 불완전 edge 목록으로 전체 연결 경로를 복원한다고 주장하지 않는다.

## canonical bytes와 보수적 parser 한도

canonical protocol은 Python `json.dumps(ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')`로 정의한다. **RFC8785 보장이나 다른 언어 JSON serializer 간 동일 digest 보장은 아니다.** canonical byte 입력만 decode한다. whitespace/newline, 다른 key 순서·Unicode escape 등 의미가 같아도 bytes가 다르면 거부한다.

- 전체 envelope 최대 16 MiB. build·validate·encode는 JSON-tree prewalk로 정확한 serialized 크기를 먼저 합산한 뒤 큰 dumps/helper 재실행을 수행한다. build의 helper 입력도 먼저 검사하고 결과 및 최종 digest 필드 추가 이후 전체 envelope도 다시 제한한다. bounded helper의 계산/반환 메모리 자체를 16 MiB peak로 보장하는 것은 아니다.
- tree 최대 깊이 32·전체 node 300000, 문자열 4096 code point, number lexeme 64자. bool을 수치로 취급하지 않는다. cycle/subclass/비JSON 객체·surrogate/비유한/거대 정수를 거부한다. 별칭은 JSON으로 표현되는 반복 값으로 처리하며 caller 객체를 변경하지 않는다.
- decode는 exact bytes 타입·16MiB를 **UTF8 decode/JSON parse 전에** 확인한다. strict UTF8/no BOM/no raw NUL을 적용하고 문자열/escape를 고려한 lexical scan으로 깊이32·token300000·number64·encoded string24576자를 json.loads 전에 제한한다. UTF16/32 escaped quote로 깊이 검사를 우회할 수 없다.
- decode 후 decoded 문자열/tree 한도와 canonical byte 동일성을 다시 검사한다. duplicate key, NaN/Infinity·overflow float, unknown schema·key·잘못된 pin은 ValueError이다. 입력 list 길이·typed helper limits·전체 bbox pair 계획은 row key 순회보다 먼저 확인한다.

## 시험 증거·한계·연결

관련 합성 시험은 `tests/test_readiness_connectivity_envelope.py`, 로그 `evidence/integration/readiness-connectivity-envelope-related-20261017.log`다. 현재 **18 PASS / 0.224초**. UTF8 canonical byte 왕복, caller 입력 불변·file-open trap, None/empty/순서·literal bbox identity, 외부 세 pin, rehashed output tamper, provenance retarget, zero/partial truncation, typed policy/limits·unknown keys, UTF16/32 깊이·escaped quote·huge number parser 전 거부, byte/tree/string limit 및 cycle/alias, final-envelope 한도, CP949 ASCII 요약/UTF8 bytes를 확인했다. 독립 재실행과 전체 회귀는 같은 시험을 중복 합산하지 않는다.

이 단위는 in-memory bytes까지만 생성한다. 영속저장 경로/overwrite/DB/서명 관리·caller eligibility/hash 실제 검증·기존 saved readiness 통합은 후속 PLANNED 범위다. 공개 CLI/API/UI 계약이 없으므로 UI 변경은 필요 없다. 기존20계약·helper58·gate/policy/분할·원본/원장/lock/예약/모델은 수정하지 않는다. Root의 실제 부재 확인 byte 왕복도 적격 scene 연결·원본 영상 파일 검증·과거 차단 원인 복구가 아니다.


## Root 실제 저장된 결측 상태 왕복

**VERIFIED_REAL은 저장 보고서의 결측 상태를 직렬화하고 다시 읽은 범위에 한정한다.** Root는 saved readiness bytes SHA와 기존 helper 파일 bytes SHA를 사전 pin과 대조하고, caller 입력을 `eligible_scenes=None / province_splits=None / 기본 limits`로 독립 구성했다. 예상 input digest는 수신 envelope에서 추출하지 않고 이 원래 입력에서 계산했다. provenance에는 사전 SHA를 확인한 report/manifest를 선언하고 eligible_scene_reference_sha256=null로 남겼다. 기존 저장 보고서의 prepared_payload=null을 장면 목록으로 대체하지 않았다.

[canonical envelope](../../evidence/integration/readiness-connectivity-envelope-live-absence-20261017.json)는 **3385 bytes**, encode→decode→재encode bytes가 완전히 일치했다. [실제 검사 기록](../../evidence/integration/readiness-connectivity-envelope-live-validation-20261017.json)과 [실행 로그](../../evidence/integration/readiness-connectivity-envelope-live-20261017.log)에 외부 input pin·provenance·원래 blocker5·eligible628/233/250을 기록했다. witness는 UNKNOWN_NOT_PERSISTED/union_complete=false이며 실제 적격 장면 입력·과거 연결 원인 복원·readiness.assess 재평가·원본 영상 읽기는 없었다. Root가 새 evidence 파일을 기록한 것이며 모듈에 영속 저장 API가 구현된 것은 아니다. 모듈의 provenance_verified/executing_helper_code_verified/eligibility_verified는 모두 false를 유지한다.

최종 독립 합성 시험은 **18 PASS / 0.217초**이며 [독립 로그](../../evidence/integration/readiness-connectivity-envelope-independent-20261017.log)를 따른다. 0.209초는 마지막 입력 길이 선검사 이전 이력이다. 별도 signed-zero 실험에서 -0.0 입력 왕복 보존 및 +0.0으로 바꾼 witness의 self-hash 재계산 변조 거부를 확인했다. 이 별도 실험과 반복 시험을 전체 unittest 건수에 합산하지 않는다.


## Root 전체 회귀·보존과 다음 연결

[전체 회귀](../../evidence/integration/readiness-connectivity-envelope-full-tests-20261017.log)는 **572건/571 PASS/1 SKIP/158.325초/종료0**다. 기존 Windows symlink 생성 권한 조건 1건을 건너뛰었고 deterministic 경계 시험은 통과했다. 관련18건/독립반복18건·별도 signed-zero 실험을 전체 건수에 중복 합산하지 않는다.

[사전 기록](../../evidence/integration/readiness-connectivity-envelope-preflight-20261017.json)과 [최종 보존 증거](../../evidence/integration/readiness-connectivity-envelope-live-integrity-20261017.json)는 보호132참조·기존20계약/저장readiness SHA 불변, 이전 추적 코드/데이터/계약 변경0, 신규 코어·시험 동결 SHA 일치, 기존 blocker5 원형 완전 보존을 기록한다. 이는 원본 영상·기하·현재 내용 SHA나 원자적 snapshot 보장이 아니다. 원본/원장/lock/예약136314880B/분할/모델·terminal 없는2건·BLOCKED/모든 승인false/환불0를 유지했다.

다음 PLANNED 단위는 기존 readiness의 실제 장면 구성·연결 지점 및 provenance 매핑을 읽어, 판정 동등성을 유지하는 최소 선택적 연결 adapter의 범위를 확정하고 합성 검증하는 것이다. 통합·영속저장 API·실제 자료 준비성 재실행·판정/분할 변경은 이번 단위에서 수행하지 않았다. 내부 순수 함수이므로 UI 변경·기존49 UI시험/build·실제 브라우저 재검증 대상은 없다. 향후 화면에 노출할 계약이 생기면 web_ui 담당에 별도로 인계한다.


## 후속 통합 전 계수와 연결 모집단 구분

Root와 독립 검토 담당이 현재 `backend/app/ml/readiness.py` 221~242, 263~281, 295~303행을 읽어 확인했다. patch_count는 0으로 시작하고 조건별 증가하지만, 앞단 예외/continue가 없는 행은 patch_count>0 조건 없이 scenes에 추가된다. 토큰·bbox는 그 scenes 전체에 적용되고 저장 patch_counts_by_split은 각 scene의 eligible_patches 합이다. 따라서 **1111(train628/val233/test250)은 저장 적격 패치 통계이며 연결에 참여한 scene 수를 증명하지 않는다.**

[현재 소스 범위 검토](../../evidence/integration/readiness-connectivity-envelope-integration-scope-review-20261017.json)는 코드 읽기 근거만 남긴다. 과거 보고서 생성 코드의 동일성·실제 union scene 수·0패치 장면의 실재 여부는 UNKNOWN_NOT_PERSISTED로 유지한다. 새 시험이나 실제 assess 재실행을 수행한 것이 아니다. 후속 adapter는 eligible_patches>0 필터나 한도 충족을 위한 scene 목록 자르기를 임의로 추가하면 안 된다. 지원하지 않는 모집단/예산은 판정과 별개 진단 상태로 남기고 기존 gate 동등성을 유지해야 한다.


## 선택적 assess 관측 후속

[60 기본 off adapter](60_readiness_connectivity_adapter_validation.md)에서 assess 내부의 전체 appended scene을 관측하는 선택적 hook을 구현·합성 검증했다. 0patch 장면을 포함하고 기존 gate 본문·default 결과를 유지하며 진단 예외를 분리한다. 실행 중인 assess에는 최종 report SHA가 없으므로 이 문서의 envelope provenance에 가짜 값을 넣어 연결하지 않았다. 영속저장·envelope 통합·CLI 노출·실자료 재평가는 별도 후속이다.
