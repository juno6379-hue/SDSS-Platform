# 96. model_ref 문자 선언 검사 공통화

## 2026-10-17 — 향후 내부 등록의 명시 모델 버전 선언 (97)

`register_experiment(store, report_path, *, model_version=...)`에서 호출자가 명시한 미래 버전을 선택적으로 보존한다. 옵션 생략은 기존 응답·레코드 바이트와 raw training의 임의 필드 복사를 그대로 유지한다. 명시할 때만 96 문자 검증과 보고서 필드 충돌 검사를 거쳐 모델 레코드의 exact5 `model_version_declaration`에 버전 원문·기존 checkpoint SHA·훈련 report SHA를 연결한다. 잘못된 명시 값은 기존 검사가 끝난 뒤 첫 Store.put 전에 거부한다.

기존 main/API·훈련 producer·UI는 이 옵션을 전달하지 않는다. 따라서 현재 공개 요청·화면의 동작은 그대로다. 명시 선언은 caller metadata이며 기관 권위·원본 인증·과학/모델/실행 승인이 아니다. 같은 모양의 raw 필드도 생략 경로에서 복사될 수 있으므로 키/source만으로 명시 호출이 생성했다고 인증하지 않는다. 기존 model_id 또는 dataset_id 중복 거부·Draft·독립평가 false·쓰기 순서를 유지한다.

기존 기록의 dataset_version을 모델 버전으로 대체하거나 역채움하지 않는다. 두 번 쓰기의 비트랜잭션·동시경쟁/전역 immutable 한계도 해결했다고 표현하지 않는다. 사용법·충돌 규칙·합성 임시 Store 시험·한계는 [문서97](97_model_version_declaration.md)를 따른다.

상태: **TESTED_SYNTHETIC**. 합성 요청과 격리 임시 Store 시험이다. 운영 Job 제출·실제 모델 조회·학습·배포를 수행하지 않았다. 전체 프로젝트 완료나 과학·운영 승인을 뜻하지 않는다.

## 문제와 변경 범위

기존 GMAIS 제출 검사는 `model_ref`의 고정 id/version/sha256를 요구한다는 안내와 달리 공백뿐인 문자나 `latest/current`를 허용했다. 완성 Job 초안 검사(89)는 이를 이미 차단했다. 새 순수 함수 `model_reference_issue(ref)`를 두 호출부가 공유한다. **GMAIS 허용 입력을 축소하는 변경**이며 동작 무변경 리팩터가 아니다. 89의 지원 입력·검사 순서·결과 코드는 그대로다.

- [문자 검사 함수](../../backend/app/model_reference_contract.py): 선언만 검사하고 최초 오류 코드 또는 `None`을 반환한다.
- [GMAIS 제출 검사](../../backend/app/gmais_api.py): 원 schema·기존 shape/SHA 검사 뒤 새 문자 검사를 추가한다. 잘못된 선언은 등록관계/Store factory 전에 기존 HTTP400 `INVALID_REQUEST` 오류 envelope로 거부한다.
- [완성 Job 초안 검사](../../backend/app/workflow_job_request_handoff.py): 원 schema→bbox→model→context→metadata 순서에서 기존 두 model 분기를 공유 함수로 대체한다.
- [회귀 시험](../../tests/test_model_reference_contract.py): 변경 전 원문 모듈의 SHA를 고정해 정상 응답·레코드·접근 순서 및 89/RFC1/RFC2 결과를 대조한다.

새 API·화면 카드·응답 필드를 추가하지 않는다. Workflow 계획의 검사는 변경하지 않는다. 기존 수동 초안 검사 RFC1/RFC2의 safe response validator도 수정하지 않는다.

## 지원 선언과 오류 우선순위

`id`, `version`, 선택적 `role`은 정확한 문자열 타입, 길이 1~256자, 공백뿐인 문자열이 아니어야 한다. U+0000~001F, U+007F~009F 제어문자와 surrogate U+D800~DFFF를 거부한다. 먼저 문자 조건을 검사하고 실패하면 `MODEL_REFERENCE_INVALID`다. 모든 문자 조건을 통과한 뒤 `version.strip().lower()`가 `latest` 또는 `current`면 `MODEL_VERSION_NOT_PINNED`다.

검사는 값을 정규화하거나 덮어쓰지 않는다. 기존 89와 같이 `" v1 "`, `" model "`, `" role "`은 허용하고 원문 그대로 유지한다. `" Current "`는 거부한다. 별칭 2개를 배제했다고 모든 실제 모델 버전의 불변성이 입증되는 것은 아니다.

공유 함수는 SHA-256·URI·허용 키·필수 키 정책을 소유하지 않는다. 호출자의 원 GMAIS schema가 여전히 id/version/sha256를 필수로 요구하며 URI는 원문 문자열 정책을 따른다. SHA/URI 내용에서 모델을 추측하거나 조회하지 않는다. helper의 `None`은 검사할 선언 부재를 의미할 뿐이다. 실제 요청에서 `model_ref`를 생략하면 이전처럼 허용하고, 명시적 `null`은 두 호출부 모두 원 schema 오류로 거부한다. SHA 누락·잘못된 SHA·비문자 값·추가 키 등 기존 schema 오류가 새 문자 오류보다 우선한다. 기존 GMAIS 수동 SHA 분기도 문자 검사보다 앞에 유지했다.

89에서는 schema 위반은 `FULL_JOB_SCHEMA_INVALID`, 이후 문자/별칭 오류는 기존 model 코드 그대로 HTTP200 `BLOCKED`다. bbox 오류가 model 오류보다 우선하며 schema 통과 여부와 모델 선언 검토 결과를 구별한다. `24 false`와 IO 0 계측, comparator 0/1, schema 읽기 미계측 `null`을 변경하지 않는다. 선언 검사 통과는 모델·실행 승인이나 Registry/checkpoint 실재 검증이 아니다.

## 시험과 증거

다음 명령은 `.runtime;backend;tests`를 PYTHONPATH로 두고 프로젝트 루트에서 실행했다.

```powershell
python -m unittest test_model_reference_contract -v
python -m unittest test_model_reference_contract test_gmais_api test_gmais_workflow_extension test_schema_formats test_agent_capability_contract test_workflow_job_request_handoff test_workflow_job_request_handoff_api test_workflow_job_registration_handoff test_workflow_job_registration_handoff_api -v
```

- 신규 11개 시험: **11 PASS / 4.132초**. [초기 결과](../../evidence/integration/model-ref-initial-tests-20261017.log).
- 관련 묶음 최종 결과: **112 PASS / 21.832초**. [관련 시험 로그](../../evidence/integration/model-ref-related-20261017.log). 전체 회귀·독립 검토·보존 결과는 Root 인계/closeout 근거에 기록한다.
- 문자 길이 256/257, 공백·제어문자·surrogate·int/bool/null, 선택적 role, alias 대소문자/패딩, 비alias 패딩 유지를 검증했다. 비어 있거나 비문자 값은 원 schema가 먼저 거부한다.
- 새 거부 대상은 격리 router에서 기존 400 envelope와 Store factory 0을 확인했다. 정상 고정 선언·부재·패딩·256경계 요청은 변경 전/후 HTTP409 `MODEL_NOT_READY`, 전체 응답/헤더, 임시 Job/멱등 레코드와 접근 순서가 같다. 모델 Store 조회와 결과 생성은 0이다.
- Workflow 계획, 89의 전체 결과, RFC1/RFC2의 전체 body/headers를 변경 전 원 helper와 대조했다. `null`/SHA/type/URI 오류 우선순위와 수동 SHA 분기도 확인했다.
- 원문 비교 근거: [GMAIS 원문](../../evidence/integration/model-ref-original-gmais-20261017.py), [89 원문](../../evidence/integration/model-ref-original-handoff-20261017.py). 시험은 각각 SHA `78a39d0298113f6da4e67cb8bd2902b563f90276f938b19ed64e17be585bd802`, `3ab99c8b90f0aea185d2ff4d6339407ef646fdd859d27f432f3cc1b0f9f352e8`를 확인하고 로드한다.

## UI 인계와 실행 한계

새 상태나 오류 envelope가 없고 기존 Agent 제출 화면의 400 안내와 수동 초안 화면의 model 코드/NOT_RUN 표시가 이 결과를 이미 지원한다. web_ui 읽기 영향 검토를 Root가 인계받으며 직접 프론트 수정·build·브라우저 재시험은 이 내부 단위에 필요하지 않다. 이전 94/95 화면 증거를 이번에 새로 실행했다고 표현하지 않는다. 실행 중 non-reload 서버의 새 소스 적용은 시험 코드 통과와 별개이며 미검증이다.

모델 version 권위 필드·immutable 등록 정책·실제 resolver 연결은 **BLOCKED**다. dataset_version을 model version으로 대체하거나 기존 모델 레코드를 역채움하지 않는다. 원 schema·원본 데이터·원장/lock·예약·분할·모델은 변경하지 않는다. 운영 Job POST, 외부 수집, 정식 학습, 배포는 0이다.

## Root 최종 검증과 인계

독립41 PASS/4.101초, 전체backend 977건/976 PASS/기존 1 SKIP/348.393초/exit0. 보호141·불변core+schema66·catalog14/기존Job본문·이전증거599파일을 보존했다. 기존 tracked 소스 수정은 허용 두 파일뿐이며 반복/경계 사례를 신규11 시험 수에 합산하지 않는다.

`model-ref-source-runtime-20261017.json`은 fresh 공통 validator의 정상3/새거부6 합성 검증이다. 옛 validator 수용을 옛 운영 full route 저장 성공으로 확대하지 않는다. 실제 Job POST·Store·Registry/checkpoint 조회는 없고, 기존 서버의 새 공통 제출 동작은 미검증이다. UI 영향 읽기 검토 결과 기존 400·모델 코드/RFC2 NOT_RUN 표시를 유지해 새 frontend/build/브라우저 시험은 없다.

관련 설계/계약·사용법·시험·인계서와 이해자료/대본/FAQ·INDEX/변경이력을 같은 단위로 갱신했다. 최종 감사와 SHA snapshot은 `evidence/integration/model-ref-closeout-20261017.json`을 따른다. 실제 model version 필드/immutable등록 정책이 없어 Registry 연결은 BLOCKED이며 데이터 버전으로 대체하거나 기존 기록을 역채움하지 않는다. 전체 개발은 미완료다.

## 98/99 입력 연결 후속

기존 등록 API·화면의 명시 선택 연결은 [98 API](98_model_version_registration_api.md)·[99 UI](99_model_version_registration_ui.md)를 따른다. 96 문자 검증·97 핵심 등록 검사는 보존했고 caller선언은 권위/승인이 아니다. 최종 통합시험·운영음성 UI·보존과 한계는 [통합 근거](../../evidence/integration/model-version-api-live-integrity-20261017.json)를 따른다.

## 100 내부 관측 후속

[순수등록선언관측](100_model_registration_provenance_observation.md)은 저장된 metadata의 부재·형식·충돌·근거부족·일치미인증을구분한다. API/UI·등록/승인gate에미연결이며 기존출처검증이나등록동작을대체하지않는다. 동일shape/source의raw복사위조도일치할수있으므로기관권위·실제바이트·과학/실행승인으로해석하지않는다. 이전모델필드도수정하지않는다. [관련/독립시험·보존](../../evidence/integration/model-provenance-live-integrity-20261017.json)과 [실제읽기관측](../../evidence/integration/model-provenance-catalog-observation-20261017.json)을참조한다. 전체회귀와프론트/build/브라우저는이번재실행하지않았고이전증거와구분한다.

## 103 별도 내부 identity 비교 후속

[명시 identity 대조](103_model_reference_record_comparison.md)는전체GMAIS model_ref가아닌명시추출exact3 id/version/sha256와호출자가제공한레코드만비교한다. 역할/URI·전체Job검증이나record선택/Registry조회는수행하지않는다. 같은id의100관측이일치미검증인때만버전/SHA를비교하고최고상태도MATCH_UNVERIFIED·권위/실바이트/과학/실행/model_verifiedfalse다. None은RECORD_NOT_PROVIDED이며실DBNotFound조회와다르다. 기존Workflow89·94/등록/관측API/UI호출은미연결·기존출력/falseflags불변이다. [합성시험·보존근거](../../evidence/integration/model-reference-record-live-integrity-20261017.json)를따르며이번전체/frontend/build/browser재시험은없다.
