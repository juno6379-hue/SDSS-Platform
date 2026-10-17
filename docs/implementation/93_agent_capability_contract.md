# 93 — Agent·capability 등록관계 공통 계약 추출

## 2026-10-17 — 선택형 완성 Job 로컬 등록관계 API·UI(94/95)

기존 수동 `/v1/workflows/full-job-input-handoff`에서 `contract_version`이 없는 정확4키 요청은 기존RFC1로유지한다. 사용자가기존details의기본off ‘로컬 등록관계도 확인 (RFC2)’를선택하고수동버튼을누를때만정확5키/정수2의RFC2를요청한다. RFC2는89의원결과를그대로보존하고innerMATCH때만Job제출과같은로컬staticmanifest firstmatch+93membership관계를관측한다. innerBLOCKED면등록관계는NOT_RUN이다.

등록됨도실제capability지원·모델/readiness·기관ACL·과학/실행승인이아니며inner24false/7IO0/schema읽기null과outer3false를유지한다. 생산·안전재검증의인메모리manifest관측2회와네트워크/Store0을구분하고관측변동·오염은503으로닫는다. UI는전체요청SHA와버전포함identity/편집·route/back세대폐기를적용하고outerBLOCKED와innermetadataMATCH를분리해표시한다.

실제8002진단HTTP15경우와5174브라우저합성초안으로정상·차단·오류·선택전환/뒤로가기를확인했고원Workflow초안을복원했다. 이는운영Job제출/Workflow실행승인이아니다. 요청/응답·지원범위·원문한도·시험/화면근거는 [API94](94_full_job_registration_api.md)·[UI95](95_full_job_registration_ui.md)를참조한다. 기존89/90/91 및93의정의는각단위이력으로보존한다.

상태: **TESTED_SYNTHETIC**. 기존 로컬 manifest와 합성 요청·임시 Store로 원 핸들러와 변경 핸들러를 대조했다. 운영 Job 제출이나 실제 Workflow 실행·과학적 capability 검증은 아니다.

## 목적과 구현

기존 `backend/app/gmais_api.py`의 Job 제출과 Workflow 계획은 선택된 manifest가 있는지와 그 manifest의 capability 목록에 요청 값이 포함되는지를 각각 검사했다. 새 `backend/app/agent_capability_contract.py`의 `agent_capability_issue(agent, capability_id)`가 이 관계 검사만 공통으로 수행한다.

반환값은 선택된 manifest가 `None`이면 `AGENT_NOT_IMPLEMENTED`, 기존 Python list membership에서 요청 capability를 찾지 못하면 `INVALID_REQUEST`, 찾으면 `None`이다. 함수는 I/O·Registry 조회·정규화·준비도/승인 검사·새 오류 정책을 추가하지 않는다. malformed 내부 manifest의 기존 KeyError/TypeError도 삼키거나 새 응답으로 바꾸지 않는다.

## 보존한 동작

- Job 제출은 기존 `next`로 manifest 목록의 **첫** 일치를 선택한다. schema/경로 Agent 검사 후 등록관계를 검사하며, Agent 부재는 기존 `409 AGENT_NOT_IMPLEMENTED`, capability 불일치는 기존 `400 INVALID_REQUEST`다. 두 거부는 Store factory 호출 이전이다.
- Workflow 계획은 기존 dict comprehension으로 동일 Agent ID의 **마지막** manifest를 선택한다. 이 선택 차이를 새 모호성 거부나 통일 정책으로 바꾸지 않았다. 현재 기본 6개 manifest ID는 서로 다르며 중복 동작은 합성 fixture로만 검증했다.
- Workflow의 원 schema/DAG 검사, Store factory 접근, 각 node의 등록관계·readiness·입력 진단 및 blocker 순서를 유지한다. 등록관계 불일치가 있어도 기존 입력 진단을 계속하는 동작을 보존한다.
- 준비도 BLOCKED/NOT_IMPLEMENTED·모델 gate와 정상 제출의 409 BLOCKED Job/멱등 기록, 재요청 동작을 유지한다. 합성 manifest를 READY로 바꿔도 기존 실행 미연결 gate가 실행을 시작하지 않는다.
- 기존 오류 code/message/status, trace/retryable/Location/header, 전체 Workflow 응답과 임시 저장 레코드·접근 순서를 보존한다. 기존 원 schema·89/90/91·24개 false·`agent_capability_verified=false` 의미를 변경하지 않는다.

등록관계 일치는 요청 capability가 내부 manifest에 기재되어 있다는 뜻이다. 실제 Agent 구현·모델 존재/버전·입출력 적합성·과학적 성능·기관 ACL·배포/실행 승인을 확인했다는 뜻이 아니다. 별도 API/화면이나 진단 축은 추가하지 않는다.

## 원 핸들러 대조 근거

Root가 수정 전에 원 `gmais_api.py` 바이트를 `evidence/integration/agent-capability-original-gmais-20261017.py`로 보관했다. SHA-256은 `3f6db80820360086ea3b52ecf4282e0d953a62b9aea3e159775aea624c7481b6`이다. 신규 시험은 이 고정 SHA를 확인하고 원 모듈의 router를 격리 FastAPI에서 실제로 실행한다. 원문 fixture는 이후 생산 코드 변화에 맞춰 덮어쓰지 않는다.

두 router에 동일한 합성 manifest·본문·고정 UUID/시각을 주고 각각 별도 TemporaryDirectory의 Store를 사용한다. 전체 응답 status/headers/JSON과 `get_store/list/get/put` 접근 순서, Job/멱등/Result 레코드를 정확히 대조한다. main/운영 앱을 import하지 않으며 운영 catalog에 접촉하지 않는다.

## 시험과 한계

`tests/test_agent_capability_contract.py`: 신규 **11 PASS**. 순수함수 입력불변/I/O 없음·기존 membership 유형 의미·malformed manifest 예외, 미등록 Agent·잘못된 capability의 저장 전 거부, schema 오류 선행, 정상/재요청/external BLOCKED, submit 첫 중복/Workflow 마지막 중복, Workflow unknown/wrong/readiness, READY여도 실행 미개시를 검증한다. 반복 fixture나 두 구현 대조를 별도 신규 시험 수에 합산하지 않는다.

개발 단독 로그 `evidence/integration/agent-capability-development-20261017.log`: **11 PASS / 4.813초**. 관련 회귀 `evidence/integration/agent-capability-related-20261017.log`: **78 PASS / 8.925초**(신규11+92·기존 GMAIS·89/90·87 API). 독립 검토·전체 회귀·실제 catalog 보존·최종 이해자료와 인계는 Root closeout을 따른다.

이번 변경은 기존 정책의 내부 중복 추출이다. 직접 프론트 수정·새 API/화면 연결은 필요하지 않다. web_ui 영향 검토와 실행 중 서버 적용 여부는 Root 인계에 구분한다. 이 합성 router 시험을 실제 브라우저/운영 서버 적용 확인이나 운영 Job 성공으로 표시하지 않는다.

## 관련 문서

- [API 및 Agent 호환성](07_api_and_agent_compatibility.md)
- [89 완성 Job 초안 내부 검사](89_workflow_job_request_handoff.md)
- [90 완성 Job 초안 수동 API](90_full_job_handoff_api.md)
- [92 공통 날짜 검사](92_common_datetime_validation.md)

## Root 최종 검증·인계

독립 21 PASS/5.512초, backend전체948개/947 PASS/기존1 SKIP/381.129초/exit0. 보호141·불변core+schema59 변경0·catalog14/기존Job본문동일을확인했다. 기존tracked소스변경은gmais_api.py1개뿐이며원schema·날짜92·89/90/91/프론트는보존했다. 반복/경계사례를신규11시험수에합산하지않는다.

운영JobPOST/역채움·Workflow/executor·새QA/수집/학습/배포는0이다. 실제서버적용은source/격리시험과구분하며nonreload8000/8001새코드적용미검증,8002reload/PID만으로동작검증을확정하지않는다. UI읽기영향검토결과현재응답계약불변으로직접frontend/build/브라우저재시험없음.

관련설계/사용법·시험근거·운영원장·인계서와이해자료/발표대본/FAQ·INDEX/변경이력을같은단위로갱신한다. 최종문서감사와증거SHA목록은 `evidence/integration/agent-capability-closeout-20261017.json`을따른다. 전체개발은미완료이며후속fullJob등록관계표시는설계검토PLANNED다.
