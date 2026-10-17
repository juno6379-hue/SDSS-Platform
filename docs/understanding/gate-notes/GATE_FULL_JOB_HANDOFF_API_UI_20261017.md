# Gate Full Job Handoff API UI 20261017 — 전체 초안의 수동 검사 통로

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | d474d5bce6c2a6c4bd8ba141c9256d15f6004631 (108까지 구현 검토 기준; 이 메타데이터 정리는 후속 문서 커밋) |
| evidence_paths | `backend/app/workflow_job_request_handoff_api.py`; `tests/test_workflow_job_request_handoff_api.py`; `docs/implementation/90_full_job_handoff_api.md`; `evidence/integration/full-job-handoff-api-related-20261017.log`; `evidence/integration/full-job-handoff-api-independent-20261017.log`; `docs/implementation/91_full_job_handoff_ui.md`; `frontend/src/FullJobHandoff.tsx`; `frontend/src/fullJobHandoffAdapter.ts`; `frontend/src/fullJobHandoffAdapter.test.mjs`; `frontend/src/full-job-handoff.css`; `frontend/src/GeoQuery.tsx`; `evidence/integration/full-job-handoff-api-live-api-20261017.json`; `evidence/integration/full-job-handoff-api-live-ui-20261017.json`; `evidence/integration/full-job-handoff-api-full-tests-20261017.log`; `evidence/integration/full-job-handoff-api-live-integrity-20261017.json`; `evidence/integration/full-job-handoff-ui-adapter-20261017.log`; `evidence/integration/full-job-handoff-ui-tests-20261017.log`; `evidence/integration/full-job-handoff-ui-independent-20261017.log`; `evidence/integration/full-job-handoff-ui-build-20261017.log`; `evidence/integration/full-job-handoff-ui-desktop-20261017.jpg` |
| confidence | 완료 API와 합성 HTTP 시험; 운영 full Job 전달·실행 미검증 |
| status | TESTED_SYNTHETIC: fullJob 초안; 실제 API·UI 전송/표시 확인; 운영 제출·실행 미검증 |

## 쉬운 설명

앞서 만든 전체 주문서 검사기에 수동 접수 창구를 붙인다. 사용자가 작성한 주문서를 그대로 보내고 형식과 입력 목록을 확인한다. 좌표에는 소수가 필요하므로 재료 목록만 비교하던 창구와 숫자 규칙을 나눈다. 양식이 맞아도 실제 주문을 접수하거나 실행하지 않는다.

## 이론적 배경

89의 내부 helper를 별도 API에 연결했다. 원 Workflow와 사용자 full Job 초안의 JSON 원문을 보존한다. Workflow는87의 정수 중심 canonical pin을 쓰지만 full Job은 소수·지수와 finite 숫자를 지원한다. 전체 초안의 Python canonical hash는 관측값으로 표시할 대상이지 JavaScript float 직렬화와 같다고 검증할 값이 아니다.

실제 보낸 outer 요청 raw bytes의 SHA로 요청과 응답을 묶는다. 이것은 full Job 외부 pin이나 출처 인증이 아니다. AOI/output/context/model을 자동 채우거나 Job을 생성하지 않는다.89의 전용 날짜 보완은 재사용하지만 기존 공통 API의 date-time 공백은 그대로 별도 대기열이다.

## 코드와 HTTP 동작

`POST /v1/workflows/full-job-input-handoff`는 workflow_request_json/pinned_workflow_request_sha256/selected_node_id/full_job_request_json의 정확 네 키를 받는다. `parse_full_job_handoff_request`는 Workflow를87 규약으로, full Job은 별도 strict decimal parser로 해석한다. 실제 stream body1MiB, 원문 각각512KiB다.

full Job은 depth24/atoms16384/string4096/key256, 정수±(2^53−1), 숫자 lexeme128자와 finite 소수·지수를 지원한다. 비영값의 underflow-to-zero와 overflow·거대 exponent 오류는 거부한다. 진짜0과 표현 가능한 subnormal은 허용한다. 문자열 숫자와 bool을 좌표로 강제 변환하지 않는다. duplicate·UTF8·surrogate·비유한은 거부한다. 이 예산은 전체 프로세스 RAM·시간 hard cap이 아니다.

transport 구문·숫자 오류는400, byte/depth/문자/atoms 등 예산 초과는413이다. 원 schema의 INVALID나 bbox/model/metadata 차이는200 BLOCKED다. core의 schema resource 상태와 응답 검증 실패는503으로 안전하게 바꾸며 원문 예외는 내보내지 않는다. 자체 응답은no-store, 인증은 기존 main을 계승한다.

89를 threadpool에서 한 번 호출하고 `validate_full_job_handoff_response`로 exact 단계·24false·7정수IO0·schema_files_read=null·comparator0/1·typed nullable hash를 확인한다. fullJob 관측hash·추출metadata·inner86의현재요청pin/count/index/false를대조한다. schema coldread가가능하므로sourceasset0을전체IO0으로확대하지않는다.

## 검증과 적용 범위

API 관련15 PASS/1.275초·독립15 PASS/1.075초다. 소수/지수/−0/subnormal/underflow·거대exponent·중복·UTF8·예산·양식INVALID200·resource503·단계/hash/flags오염·인증·기존87응답불변을합성검증했다. 반복실행을전체시험에더하지않는다.

UI91의 완료 코드·프론트 시험·build·실제 합성 초안 HTTP/브라우저를 확인했다. 최종 전체927건/926 PASS/기존1 SKIP/370.179초·종료0과 보존 근거를 확인했다. 화면 연결과 Job 생성·실행은 다른 상태다.

## 한계

전체 초안 schema와 bbox 수치 순서가 맞아도 실제 AOI/output·Agent capability·모델·기관 ACL·과학·준비성·실행을 승인하지 않는다. full Job hash는 서버 관측값이며 외부 fullpin 검증false다. 현재파일/Registry/전이계보/TOCTOU·실제executor도미검증이다.

schema_files_read=null은 미계측이다. 자산·DB·Registry·resolver·executor 호출0과 구분한다. 기존 원본5차단·후보1095패치/4차단과예약136314880B·환불0을유지한다. 표시중단은서버처리취소가아니며API의순수진단을실제Workflow실행으로표현하지않는다.

## 1분 발표

“전체 Job 초안을 검사하는 수동 API를 추가했습니다. 원 Workflow와 사용자가 작성한 초안을 그대로 보내며 좌표에 필요한 소수도 지원합니다. 전체 요청 지문으로 응답을 묶고 서버가 계산한 초안 지문은 관측값으로 구분합니다. 양식과 입력 목록이 맞아도 실제 AOI·모델·권한을 승인하지 않습니다. 주문서를 대신 채우거나 Job을 만들지 않으며 학습과 실행은 시작하지 않습니다. schema를 읽을 수 있으므로 전체가 IO0인 기능도 아닙니다.”

## 5분 발표 순서

1. **0~1분:** 전체 주문서 검사의 수동 접수 창구를 설명한다.
2. **1~2분:** Workflow 정수 규약과 full Job 소수 지원을 나눈다.
3. **2~3분:** raw 요청 결속과 서버 초안 관측 hash를 구분한다.
4. **3~4분:** 합성 API·UI·실제 통신·전체 회귀의 근거를 나눈다.
5. **4~5분:** schema IO·원본 인증·실행과 과학 승인의 한계를 말한다.

10분 설명에서는 underflow·signed zero·schema resource503·typed단계교차와UI독립/stale계약을추가한다.

## Q&A

**기존 metadata API를 그대로 쓰나?** 별도 API다. full Job의 소수 좌표를 위해 숫자 규약도 나눈다.

**200이면 초안이 통과한 것인가?** 정상 진단의 BLOCKED도200이다. schema resource 오류는503으로 구분한다.

**서버 초안 hash와 브라우저 hash를 비교하나?** full Job Python float canonical은 표시할 관측값이다. 실제 outer 전송 지문으로 응답을 결속한다.

**schema 읽기null은0인가?** 아니다. 미계측이며 로컬 schema cold read가 가능하다.

**실행과 학습을 시작하나?** 아니다. 진단 통로이며 Job생성·제출·학습·executor연결은없다.

## 이후 갱신

UI91·실제HTTP/브라우저·전체 회귀·보존 근거를 읽고 INDEX·변경 이력·계약·구조·06·용어·발표·FAQ를 함께 갱신했다. 다음은 PLANNED다. schema_formats.py의 공통 detached factory를 추출하고 gmais cached validator 생성과89의 호환 wrapper가 재사용해 기존 공통 date-time 환경 공백을 줄일 계획이다. 원 schema·class 전역·이미 생성된 cached 객체의 후행 변조 없이 기존400 오류를 보존하고 leap-second 지원 subset을 문서화한다. 아직 구현·운영 Job POST는 없다. 전체 개발과10분 보고는 계속된다.


## UI91 연결과 실제 관측

GeoQuery의88 metadata 검사 아래 접는 `FullJobHandoff` child를 독립 mount했다. node와 full Job 원문은 빈 값으로 시작하고 펼치기·편집·기존 조회로 자동 요청하지 않는다. 원문을 보존해 전송한다. 브라우저 JSON.parse는 metadata 프리뷰에만 쓰며 full Job 중복키·소수·지수·finite/underflow의 최종 판정은 서버 strict parser가 담당한다. 기존87 정수 parser를 full Job에 적용하지 않는다.

UI는 실제 outer 전송SHA와 exact wrapper,24false·7typed0·schema IO null·단계와inner86을확인한다. full Job Python hash는 관측값으로 표시하고 JSfloat hash와 비교하지 않는다. node/fullJob/Workflow/revision/route 편집과 표시중단이 이전 세대를 폐기한다. 접었다 펼치면 현재 결과는 남고, 기존 plan/lineage/88 metadata와 결과 상태는 독립이다.

최종 신규14 PASS/3122.0076ms·전체127 PASS/5013.0695ms·독립14 PASS/4369.1739ms다. production build87modules/16.14초 PASS이며 기존chunk경고는남는다. Python89→UI8경우 교차검산은신규시험에포함된검증이며별도로합산하지않는다.

실제 API의19새POST는합성fullJob초안이다. decimal/exponent/음0 MATCH,AOI변경으로전체관측SHA만바뀌고metadataSHA가같음,양식/날짜/role/pin/빈선택 차단,중복·UTF8·비유한/overflow/underflow400,byte/depth/token413을확인했다. 기존plan/lineage/88 세진단과기준선3POST는별도이며응답은시각제외같았다.

실제 UI5174/#/view/15의1449×1087에서합성소수·지수·음0 MATCH,날짜+00:60 양식차단·role대조차단·중복fullJob HTTP400·없는node/null을확인했다. 새8POST와기존3조회는별도다. 기존세조회와양방향결과독립,접기펼치기·node/full/Workflow편집clear·backforward폐기·빈기본disabled를확인했다. 문서/패널overflow0·console0·SVG정렬확인후원Workflow초안복원·합성입력을지웠다. 스크린샷은복원전합성시연이다.

모바일·강제지연/취소·브라우저503/인증·5173적용은미검증이다. 실제통신과표시를확인했지만내용은합성초안이고운영Workflow/Job전달·실행은없다. 자산IO0은schema coldIO와기존독립진단을포함하지않는다.


## 최종 회귀와 보존

최종 backend 전체 **927건 중926 PASS·기존 Windows symlink 권한 제약1 SKIP**,370.179초·종료0이다. 기존 deterministic 경계시험은 통과했다. API관련/독립 각15개와UI신규/독립 각14개·교차검산·실제POST횟수는전체에더하지않는다. UI전체127 PASS·build87modules/16.14초PASS다.

시험 후 보호141참조·기존 코어와 원schema56개·catalog14·Job2본문이 같았다. 기존 추적 변경은 main.py와 GeoQuery.tsx의 허용 배선 두 파일뿐이다. 이는 지정한 보호 범위이며 전체 workspace 불변이나 원자 snapshot 보장은 아니다. JobPOST·역채움·executor·새QA·학습은0이다. 실제 통신과 화면을 확인했지만 입력은 합성 초안이고 운영 fullJob 전달·과학/기관/실행 승인은 아니다.
