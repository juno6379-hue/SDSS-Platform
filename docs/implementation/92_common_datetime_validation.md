# 92 — 공통 날짜 형식 검사의 환경 일관성

상태: **TESTED_SYNTHETIC**. 실제 vendored schema와 로컬 Python 검증기를 사용한 합성 초안·격리 FastAPI/임시 Store 시험이다. 운영 Job 제출·실제 Workflow 실행·새 수집·QA·학습·배포 검증은 아니다.

## 변경과 목적

일부 로컬 환경에서는 jsonschema의 선택 RFC3339 의존성이 없어 기본 `FormatChecker()`에 `date-time` 검사가 등록되지 않는다. 따라서 원 Job schema의 `time_range.start/end`가 잘못된 날짜여도 공통 제출 검사에서 통과할 수 있었다. 기존 89의 독립 초안 검사만 이 공백을 보완했다.

새 `backend/app/schema_formats.py`의 `create_format_checker()`가 의존성 없이 검사할 수 있는 날짜 지원 범위를 새 인스턴스에 등록한다. `backend/app/gmais_api.py`의 `_job_request_validator()`와 `_workflow_plan_validator()`는 생성 시 이 factory를 사용한다. `backend/app/workflow_job_request_handoff.py`의 `_draft_format_checker()`는 기존 이름을 유지하는 호환 wrapper로 동일 factory를 재사용한다.

vendored 원 schema와 공개 endpoint/응답 필드는 바꾸지 않는다. `FormatChecker` class registry, 이전에 생성한 checker, 이미 캐시된 validator를 나중에 변경하지 않는다. 각 factory 호출은 독립된 checker를 반환하며 기존 LRU cache 재사용은 유지한다. 배포 중인 기존 프로세스가 이전 모듈/캐시를 유지하면 소스 수정만으로 해당 객체가 바뀌지는 않는다. 실행 중 서버 적용 확인은 Root의 별도 runtime 근거를 따른다.

## 지원 범위와 한계

- 4자리 연도와 실제 달력 날짜, `T/t`, 시·분·초, 선택 소수초, `Z/z` 또는 명시적 timezone offset을 지원한다.
- offset 시간은 00..23, 분은 00..59다. `datetime.fromisoformat`의 offset 분 정규화를 허용하지 않도록 먼저 정규식으로 검사한다.
- timezone 없는 문자열, 잘못된 달력 날짜, 24시, offset 분 60/99, offset 시간 24, leap second 60, 연도 0000은 거부한다. 모든 RFC3339 유효 입력을 지원한다고 주장하지 않는다.
- non-string은 format 단계에서 중립적으로 통과시키고 JSON Schema `type`이 거부한다. 기간의 시작·끝 순서, timezone 변환, 과학적 기간 정책은 검사하지 않는다.
- 정상 형식도 데이터 존재·원본 인증·기관 ACL·모델 준비·과학·실행 승인과 별개다. Job 제출의 기존 준비도 BLOCKED 정책은 유지한다.

## API 및 UI 영향

기존 `POST /v1/agents/{agent_id}/jobs`는 잘못된 `time_range.start/end`를 기존 `400 INVALID_REQUEST` 오류 envelope 및 JSON Schema 메시지 방식으로 거부한다. 이 거부는 `get_store()` 호출보다 앞서므로 Store 조회/저장이나 Job 생성이 없다. 정상 초안은 기존 모델/입력 gate를 거쳐 `409 MODEL_NOT_READY`와 BLOCKED Job을 반환하는 동작을 유지한다. 이 정상 제출 검증은 임시 Store에서만 수행했다.

원 Workflow schema에는 현재 `format` 필드가 없다. checker 생성만 통일하며 기존 계획 응답을 그대로 유지한다. 89 내부 초안 검사와 90의 수동 진단 API는 기존 날짜 차단·상태·해시 계약을 유지한다. 제출 API의 잘못된 형식 400과 90의 정상 JSON/schema 불일치 `200 BLOCKED`를 혼동하지 않는다.

새 화면/필드/상태/오류 계약을 추가하지 않으므로 직접 프론트 수정은 필요하지 않다. 기존 UI 오류 표시와 89/90 날짜 차단 경로를 사용한다. web_ui 담당의 영향 검토 및 실제 서버 적용 여부는 Root 인계서에 기록하며, 이번 backend 시험을 프론트 빌드나 실제 브라우저 재시험으로 표시하지 않는다.

## 시험 증거

`tests/test_schema_formats.py`의 신규 **10 PASS**는 정상 zoned/calendar 사례, 잘못된 날짜/clock/offset/지원 외 형식, non-string/type 분리, factory/class registry/기존 checker 독립성, 선택 date-time 등록 부재, cache 재사용과 89 wrapper 불변을 확인한다.

동일 시험에 원 schema의 start/end 경계와 isolated router의 잘못된 날짜 26경우(13값×2필드) Store factory 미호출/400 오류 계약, 정상 제출의 기존 기본 checker 대비 409 응답·임시 Job/멱등 레코드 정확 동등, 기존 Workflow 계획 응답 동등이 포함된다. 경계 사례를 독립 시험 수에 중복 합산하지 않는다.

관련 회귀 `evidence/integration/common-datetime-related-20261017.log`: **67 PASS / 6.190초**. 신규 10개와 기존 89·90·GMAIS·87 API 시험을 함께 실행했다. 개발 중 단독 신규 시험은 `common-datetime-development-20261017.log`의 **10 PASS / 1.055초**이며 별도 신규 시험으로 합산하지 않는다. 독립 검토·전체 회귀·실제 catalog/보존·최종 이해자료와 인계 근거는 Root closeout을 따른다.

실행 예:

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_schema_formats test_workflow_job_request_handoff test_workflow_job_request_handoff_api test_gmais_api test_workflow_node_input_handoff_api -v
```

## 관련 문서

- [89 완성 Job 초안 내부 검사](89_workflow_job_request_handoff.md)
- [90 완성 Job 초안 수동 API](90_full_job_handoff_api.md)
- [91 완성 Job 초안 UI](91_full_job_handoff_ui.md)
- [API 호환성](07_api_and_agent_compatibility.md)

## Root 최종 검증 및 인계

독립40 PASS/2.972초, 전체 backend 937개/936 PASS/기존 1 SKIP/345.696초/exit0. 보호141·불변core+schema57·catalog14/기존Job본문을보존했다. 원schema/90API/기존frontend변경0이며 이전tracked소스 변경은허용2개뿐이다. 관련·독립·전체의반복시험은신규시험수에더하지않는다.

`common-datetime-source-runtime-20261017.json`은 새Python프로세스의실제vendoredschema/공통검사기로 기본date-time미등록환경에서정상6·오류13을확인한 TESTED_SYNTHETIC 증거다. 운영app/Store/JobPOST를호출하지않았다. `common-datetime-runtime-20261017.json`은기존Vite2/API3·예약설정과실제worker관측범위를분리한다. 8000/8001 nonreload 새코드적용은미검증이며8002reload설정/PID변경만으로공통날짜검사적용을인증하지않는다.

운영Job생성/실행·새QA/수집/학습/배포·승인변경은없다. 이해자료·발표대본/FAQ·INDEX/변경이력을같은단위로갱신하고 최종감사·snapshot은 `evidence/integration/common-datetime-closeout-20261017.json`에기록한다. 전체개발완료가아니며다음등록관계공통계약추출은PLANNED다.
