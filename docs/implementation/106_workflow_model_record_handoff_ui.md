# 106. Workflow 완성 Job과 사용자 모델 레코드의 별도 수동 대조 UI

상태: **TESTED_SYNTHETIC** — 새 UI adapter와 비동기 mock, 실제 Python104 helper 교차 결과를 시험했다. 실제 브라우저·실행 서버 연결은 Root의 별도 근거로 구분한다. 모델 등록·역채움·실제 Job/Workflow 실행·resolver·학습·승인·배포를 수행하는 기능이 아니다.

## 독립 수동 입력과 API 연결

[GeoQuery](../../frontend/src/GeoQuery.tsx)의 기존 완성 Job 검토 다음에 기본 접힌 [별도 component](../../frontend/src/WorkflowModelRecordHandoff.tsx)를 연결했다. 기존 FullJobHandoff와 RFC1/RFC2 adapter는 수정하지 않았다. 새 ‘모델 레코드 초안 대조’에는 빈 선택 노드 ID·빈 완성 Job 원문·빈 선택 모델 레코드 원문을 둔다. 기존 패널의 입력이나 모델 목록에서 자동 추출·채움·선택하지 않는다. 열기·편집·Workflow 변경으로 자동 요청하지 않으며 전용 버튼만 새 `POST /v1/workflows/full-job-model-record-handoff`를 호출한다.

기존 네 문자열 필드에 선택 `model_record_json` 문자열을 더한다. 레코드 입력이 정확히 빈 문자열이면 키를 생략한다. 공백 문자열은 그대로 보내 서버 JSON 오류로 처리하고, `null` 원문도 문자열로 보내 Python None 관측을 받는다. JSON transport null로 바꾸지 않는다. None은 사용자가 레코드를 제공하지 않았다는 뜻이며 Registry/DB에서 모델을 찾지 못했다는 뜻이 아니다.

병합된 전체 body UTF-8 1MiB 한도를 먼저 검사하고 Workflow/Job/record 각 원문 512KiB 한도를 적용한다. Workflow는 기존 정수 canonical pin 계약을 재사용한다. Job·레코드의 소수·지수·음수 0 원문은 그대로 전송한다. JS의 전체 Job/record canonical hash를 서버 Python 관측 SHA와 비교하지 않는다. 중복 키·소수·underflow·깊이 등 엄격 JSON 검사는 서버의 책임이며 UI에 다시 구현하지 않는다. JSON.parse 결과는 문자 필드 관계와 응답 검증의 보조 자료일 뿐 원문 전송값을 대체하지 않는다.

## 응답 결합과 3단계 검증

[새 adapter](../../frontend/src/workflowModelRecordHandoffAdapter.ts)는 다음 순서로 결과를 검증한다.

1. 새 RFC1 exact5 wrapper의 extension·INTERNAL_REVIEW·upstream false·**새 요청 전체 RAW SHA**를 확인한다. 새 extension은 `greenblue.workflow-full-job-model-record-handoff.rfc1`이다.
2. nested89를 기존 `fullJobHandoffView`로 검사한다. 이 재포장에는 **기존 네 필드 body의 별도 SHA**를 사용한다. 새 요청 전체 SHA와 같은 값이라고 가장하지 않는다. 기존24false·7I/O0·schema_files_read null·metadata 결합 검사는 원 adapter대로 유지한다.
3. 104의 exact12/3흐름·5false와 103의 exact12/6상태·3binding·exact3 issue·호출 수·nested100의 exact10 정합을 검사한다. 100은 기존 `parseModelProvenance`를 재사용한다. 정상 검증된 identity projection 뒤에는 103의 REFERENCE_INVALID가 자연 도달할 수 없으므로 outer OBSERVED 결과에서 거부한다.

| outer 상태 | 화면 의미 | projection / 103 호출 |
|---|---|---|
| HANDOFF_BLOCKED | 완성 Job 입력 전달 차단 | false / 0, nested 모델 결과 null |
| MODEL_REFERENCE_ABSENT | 모델 참조 없음 · 대조 미실행 | false / 0, nested 모델 결과 null |
| MODEL_REFERENCE_OBSERVED | 모델 참조 대조 수행 · 결과 별도 확인 | true / 1, nested103 검사 |

OBSERVED는 일치·준비·승인이 아니다. nested103은 사용자 레코드 미제공·형식 오류·참조 충돌·선언 근거로 대조 불가·메타데이터 일치하나 미인증을 분리해 표시한다. ID 불일치는 등록 선언 관측0회, 같은 ID는1회다. version/SHA를 비교하는 단계에서는 nested100이 CONSISTENT_UNVERIFIED이어야 하며 version 충돌을 SHA 충돌보다 먼저 issue로 표시한다. 입력 레코드가 None인지·타입·가능한 ID/version/checkpointSHA 문자 관계도 대조해 다른 정상 형식 결과를 바꿔 끼우지 못하게 한다. 이는 메타데이터 표시 정합성 검사이며 응답 신원 인증이 아니다.

## 화면 상태·실패·한계

입력·Workflow plan·executionRevision 변경은 이전 요청 세대를 폐기하고 결과·오류·busy를 지운다. route/hashchange/popstate·unmount도 같은 경계를 적용한다. async digest 준비 중 편집하면 POST 전에 중단하고, POST 뒤 늦은 응답은 다른 입력에 붙이지 않는다. 동기 pending은 React busy 렌더 전 중복 클릭도 한 요청으로 제한한다. 명시 ‘응답 표시 중단’은 표시 세대만 폐기하며 서버 처리 취소가 아니다. 기존 RFC1/RFC2·계획·계보 패널의 상태를 덮어쓰지 않는다.

응답 오염·상태/flag/호출 수 불일치와 HTTP400/413/503/401/403은 검증된 고정 한국어 안내로만 표시한다. 임의 서버 data·경로·예외를 출력하지 않고 이전 성공 결과를 폐기한다. [scoped CSS](../../frontend/src/workflow-model-record-handoff.css)와 공통 SVG Icon을 쓰며 제목/도움말/버튼 간격을 전역 스타일과 분리했다.

기관 권위·실제 파일 바이트·실행 승인·과학 정확도·모델 인증은 **이 진단에서 항상 미검증**이다. 기존 모델 승인 값을 false로 바꾸는 판정이 아니다. 같은 shape/source·메타데이터/SHA 일치는 원본 인증·실파일 확인·명시 등록 호출의 진정성을 입증하지 못한다. URI 형식은 URI 해결·권위 검증이 아니고 pin은 원본 인증이 아니다. wrapper 추가 I/O0과 89 cold schema 로드 가능성을 구분해 schema 파일 읽기 null을 전체 파일 I/O0으로 표시하지 않는다.

## 시험 근거

[신규 시험](../../frontend/src/workflowModelRecordHandoffAdapter.test.mjs) **19 PASS / 2815.4243ms**. 실제 Python104의 15케이스로 outer3흐름·자연 도달 nested5상태·소수/지수 입력을 JS와 교차했다. 별도103 REFERENCE_INVALID 객체는 parser 형식 시험에만 사용하며 정상 outer 도달 근거가 아니다. exact shape/typed flags/calls·오염·None·문자 관계·충돌 우선순위·수동 중복1회·입력/plan/revision/route/back/unmount·async 준비 중 중단·안전 오류를 검증했다.

최초 18/19의 실패1건은 sibling JSX를 검사하는 시험 정규식 오타였다. 제품 코드를 바꾸지 않고 정확한 JSX 문자열 비교로 수정했다. [최초 실패 로그](../../evidence/integration/workflow-model-record-ui-related-initial-failure-20261017.log)를 보존했다.

- [관련 로그](../../evidence/integration/workflow-model-record-ui-related-20261017.log): 19 PASS.
- [전체 프론트 로그](../../evidence/integration/workflow-model-record-ui-tests-20261017.log): **191 PASS / 8678.6347ms**.
- [빌드 로그](../../evidence/integration/workflow-model-record-ui-build-20261017.log): tsc·Vite 성공(exit 0), **96 modules / 28.34초**. 기존 500kB chunk 경고는 유지한다.

실제 브라우저의 접힘/빈값/수동 흐름·합성 입력의 실제 API 호출·레이아웃·입력 복원·운영 보존 관측은 Root가 별도 근거로 기록한다. mock/합성 성공을 운영 모델 준비나 실제 과학 실행으로 표현하지 않는다.

독립 검토가 같은 신규19개를 별도 실행해 **19 PASS / 2988.2351ms / exit0**, 추가 결함0을 확인했다. [독립 UI 로그](../../evidence/integration/workflow-model-record-ui-independent-20261017.log). 기존 관련/전체 수치에 중복 합산하지 않는다.

## Workflow 모델 레코드 대조 API·UI 검증 완료 (105/106)

별도 수동 진단 POST와 실행계획 검토 화면의 ‘모델 레코드 초안 대조’를 연결했다. API 담당은 strict parsing·크기 한도·원문 SHA·nested exact typed 재검증을, UI 담당은 공통 SVG·명시 클릭·오래된 응답 폐기·안전 오류를 구현했다. 기존 RFC1/RFC2 결과와 승인 gate를 보존한다. producer의 103 호출 1회와 독립 validator의 추가 1회를 구분하며, record 원문 파싱은 89 gate보다 먼저다.

관련 API 101 PASS·독립 15 PASS, 프론트 관련/독립 각19 PASS·전체191 PASS, 빌드96 modules/28.34초다. Root 최종 전체 backend는 1060건/1059 PASS/기존 Windows symlink 1 SKIP/364.175초/exit0다. 첫 전체 실행은 기존101 AST 보존 시험의 새 router 허용목록 부재로 실패1건이었다. 정확한 두 연결만 허용하는 시험 호환 수정 후 전체를 재실행했고, 최초 실패 로그도 보존했다. 제품 동작 오류와 시험 호환 수정은 구분한다.

Root는 합성 원문으로 실제 HTTP 10건(200×6/400×3/413×1)과 브라우저 11개 확인·수동 진단 POST4회를 수행했다. 미제공·일치 미검증·공백400·null 미제공, 입력/Workflow 편집의 결과 폐기와 화면 이동/뒤로가기를 확인했다. 원래 Workflow 원문은 정확히 복원하고 새 node/job/record 필드는 비웠다. desktop 제목 겹침·가로넘침0/제목·버튼 SVG 정상, 시험 이후 수집된 최근20 warn/error 중 새 항목0이다. 지연·동시성 방어는 격리 시험 근거이며 실제 back 확인은 완료 응답 이후다. 표시 중단은 서버 취소가 아니다.

보호141·이전 증거736·catalog14·기존 Job 본문을 보존했다. 계약기준73개 중72개는 byte 불변이며 나머지 GeoQuery1개는 허용된 import/sibling 두 조각만 제거하면 원문 byte와 정확히 같다. 기존제품의 허용 변경은 main router import/include와 GeoQuery sibling 배치이며 추가 기존 시험1개 호환 수정은 별도 사전 byte 근거를 남겼다. 운영 등록/Job 생성·Workflow 제출·수집/새 운영 QA/정식 학습/배포0, 원본/원장/lock/예약136314880B/분할/모델 보존·QA차단4/학습BLOCKED 유지다. 이 진단은 metadata 관계만 관측하며 기관 권위·실바이트·과학 정확도·실행 승인·모델 인증을 입증하지 않는다. 성공 화면 PNG도 합성 입력 진단 예시다.

완료 코드·시험·실제 화면 근거를 이해 에이전트에 전달해 쉬운 설명·발표 대본·FAQ·INDEX·변경 이력을 함께 갱신했다. 다음은 Workflow 입력 연결 대기열 검토(PLANNED)이며 전체 개발은 미완료다. geoai-2 예약 ACTIVE와 실제 worker 실행은 다르다. 최종 로컬 프로세스 관측의 수집/학습 후보는0이며 원격/숨은 worker까지 보장하지 않는다. 8002는 실제 진단 요청으로 새 경로를 확인했고8000/8001은 유지·새 코드 로딩 미확인이다. 지속 개발과10분 담당별 보고를 유지한다.

근거: `evidence/integration/workflow-model-record-api-live-integrity-20261017.json`, `evidence/integration/workflow-model-record-api-live-api-20261017.json`, `evidence/integration/workflow-model-record-api-live-ui-20261017.json`, `evidence/integration/workflow-model-record-api-runtime-final-20261017.json`. 최종 문서 감사와 rawSHA snapshot은 `evidence/integration/workflow-model-record-api-closeout-20261017.json`을 따른다.

