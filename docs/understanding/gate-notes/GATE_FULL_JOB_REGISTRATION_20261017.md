# Gate Full Job Registration 20261017 — 선택형 로컬 등록관계 관측

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/workflow_job_registration_handoff.py`; `backend/app/workflow_job_request_handoff_api.py`; `docs/implementation/94_full_job_registration_api.md`; `docs/implementation/95_full_job_registration_ui.md`; `evidence/integration/full-job-registration-api-related-20261017.log`; `evidence/integration/full-job-registration-api-independent-20261017.log`; `evidence/integration/full-job-registration-api-live-api-20261017.json`; `tests/test_workflow_job_registration_handoff.py`; `tests/test_workflow_job_registration_handoff_api.py`; `frontend/src/FullJobHandoff.tsx`; `frontend/src/fullJobRegistrationAdapter.ts`; `frontend/src/fullJobRegistrationAdapter.test.mjs`; `frontend/src/full-job-handoff.css`; `evidence/integration/full-job-registration-api-live-ui-20261017.json`; `evidence/integration/full-job-registration-api-full-tests-20261017.log`; `evidence/integration/full-job-registration-api-live-integrity-20261017.json`; `evidence/integration/full-job-registration-api-original-20261017.py`; `evidence/integration/full-job-registration-ui-related-20261017.log`; `evidence/integration/full-job-registration-ui-tests-20261017.log`; `evidence/integration/full-job-registration-ui-independent-20261017.log`; `evidence/integration/full-job-registration-ui-build-20261017.log`; `evidence/integration/full-job-registration-ui-desktop-20261017.png`; `evidence/integration/full-job-registration-ui-blocked-20261017.png`; `evidence/integration/full-job-registration-api-next-review-20261017.json` |
| confidence | 완료 코드·합성 초안/로컬 manifest 대조·실제 HTTP; 운영 capability 지원 미검증 |
| status | TESTED_SYNTHETIC: 합성 초안/로컬 manifest·실제 API/UI 확인; 운영 capability/실행 미검증 |

## 쉬운 설명

전체 주문서가 원 작업과 맞는지 본 뒤, 사용자가 원하면 담당자와 업무 이름이 로컬 명부에 함께 있는지도 확인한다. 명부에 없으면 주문서 목록이 같아도 별도 차단으로 보여준다. 명부에 있다고 실제 업무 능력이나 출고 승인을 확인한 것은 아니다. 기본 화면은 이전 검사이며 사용자가 선택해야 새 관측을 요청한다.

## 이론적 배경

기존 RFC1은 전체 초안의 schema·bbox 수치·metadata 대조다. RFC2는 이를 그대로 안에 보존하고 로컬 등록관계만 별도 축으로 붙인다.89~91의 agent_capability_verified=false를 true로 바꾸지 않는다. 로컬 static manifest의 이름 관계와 실제 capability 지원·readiness·기관 ACL·과학·실행 승인은 다른 사실이다.

버전도 명시적이다. contract_version이 없는 정확4키는기존RFC1이고,정확한정수2가추가된정확5키만RFC2다. bool·2.0·문자2·null·명시1은400이며묵시승격하지않는다. outerwrapper는5키를유지하되extension이rfc2로바뀐다. 요청전체rawSHA도버전선택을포함한다.

## 코드와 상태 흐름

`compare_workflow_job_registration_handoff`가89를한번호출한다. innerMATCH일때만Job과같은첫manifest선택과93의membership를관측한다. 안전응답검증에서동일등록관계를다시대조하므로staticmanifest인메모리관측은총2회다. innerBLOCKED는0회이며기존86comparator를다시실행하지않는다.

RFC2의exact8result는schema_version/scope/status/full_job_comparison/local_manifest_registration과actual_capability_supported·institution_acl_verified·execution_authorized false다. 등록축은source=LOCAL_STATIC_AGENT_MANIFESTS,status,checked의exact3키다. 관측사이변동·오염·manifest형식실패는safe503이다.

| inner89 | 등록축 | checked | outerRFC2 |
|---|---|---|---|
| BLOCKED | NOT_RUN | false | BLOCKED |
| MATCH | REGISTERED | true | MATCH |
| MATCH | AGENT_UNKNOWN | true | BLOCKED |
| MATCH | CAPABILITY_UNREGISTERED | true | BLOCKED |

checked는관측완료다. Agent가없거나업무가없어도true일수있으며실지원검증이아니다. inner24false·7IO0·schema파일읽기null은그대로다. 인메모리관측을DB/원격Registry조회로설명하지않고schema coldIO를포함한전체IO0도주장하지않는다.

## API·UI 계약

같은fullJob endpoint에RFC2 opt-in을추가했다. 기존RFC1은정확한요청·wrapper·원89결과·오류를유지하고핀된수정전API router와격리응답byte/header/status를대조했다. transport400·예산413·resource/오염503·정상진단200BLOCKED와no-store/auth는그대로다. fullJob decimal·raw원문·Python관측hash표시범위도같다.

UI는기본off선택란을두고같은수동버튼에서만RFC2를요청한다. 선택자체로POST하지않는다. 별도adapter가버전extension·rawSHA·inner/outer·등록축·비승인false를검사한다. 버전선택도identity에포함해편집/route/back/unmount/표시중단이이전결과를폐기한다. outerBLOCKED와innerMATCH를구분해표시한다. 표시중단은서버취소가아니다. 최종 UI독립·실제브라우저근거를 확인했고 최종 전체966건/965 PASS/기존1 SKIP/350.995초·종료0과 보존 근거를 확인했다.

## 검증 증거

API관련69 PASS/8.515초·독립18 PASS/1.433초다. 신규core8/API10과기존89/90/93/92를검증했다. four상태·inmemory2/0·inner1회·위조등록관계·privacy·버전경계·RFC1전후동등을확인했다. 실제API8002의15합성초안case도RFC1unknownMATCH/RFC2unknownBLOCKED·LCLUC/외부등록/noapproval·오류version·NOT_RUN을확인했다. 운영Job제출이나실제capability실행은아니다.

UI관련24 PASS/24406.859ms는신규10+기존14이며Pythonproducer의등록4상태교차를포함한다. 전체137 PASS/11405.9891ms·build88modules/19.48초PASS다. 반복/교차사례를전체시험에합산하지않는다. UI독립24 PASS/4215.2776ms와 실제 합성 시연을 확인했다. backend전체966건/965 PASS/기존1 SKIP/350.995초와 최종 보존을 확인했다.

## 한계와 기존 상태

REGISTERED도실제기능구현·모델준비도·과학적AOI/output·기관ACL·배포·실행승인이아니다. 원본인증·전체Jobpin·DAG·TOCTOU·현재파일·전이계보미검증은같다. LCLUC BLOCKED·외부5 NOT_IMPLEMENTED·원본5차단·후보1095/4차단·예약136314880B·환불0을유지한다.

기존nonreload8000/8001적용은미확인이다.8002실제진단은합성초안의관측이며운영JobPOST·수집·QA·정식학습·executor연결은없다. RFC2화면완료와전체프로젝트완료를구분한다.

## 1분 발표

“전체 초안 검사에 선택형 로컬 등록관계 관측을 붙였습니다. 기본은 이전 검사이며 사용자가 선택하면 담당 Agent와 업무 이름이 로컬 명부에 함께 있는지 따로 봅니다. 원 초안이 같아도 명부에 없으면 바깥 결과는 차단으로 표시합니다. 등록됐다는 결과도 실제 기능 지원이나 모델·기관·과학·실행 승인은 아닙니다. 이전 결과와 비승인 값은 그대로 보존하고 명시 버전으로 구분합니다. 실제 진단도 합성 초안을 사용했으며 Job을 제출하거나 실행하지 않습니다.”

## 5분 발표 순서

1. **0~1분:** 주문서 검사 뒤 선택형 명부 확인의 비유를 말한다.
2. **1~2분:** RFC1 보존과 명시 RFC2 선택을 설명한다.
3. **2~3분:** inner 목록 일치와 outer 등록 차단의 차이를 설명한다.
4. **3~4분:** 격리 동등성·HTTP·UI·전체 회귀 근거를 나눈다.
5. **4~5분:** 등록과 실능력·준비도·기관·실행 승인의 차이를 말한다.

10분 설명에서는static관측2/0·firstmatch·typedversion·위조응답재대조·schemaIO null·버전stale계약을추가한다.

## Q&A

**REGISTERED면 기능이 실제 지원되나?** 로컬 명부의 이름 관계다. 실제 지원은 false로 남는다.

**왜 안쪽 MATCH와 바깥 BLOCKED가 같이 나오나?** 입력 목록은 같아도 Agent나 업무가 로컬 명부에 없을 수 있기 때문이다.

**기본 검사가 자동 변경되나?** 아니다. 기본off이며 선택하지 않으면 기존RFC1을 쓴다.

**checked=true면 성공인가?** 관측을 마쳤다는 뜻이다. 미등록 결과에도 true일 수 있다.

**기존24false가 true로 바뀌나?** 아니다. 로컬 관측은 별도 축이고 이전 비승인은 그대로다.

## 이후 갱신

최종 UI독립/브라우저·전체·보존 근거를 읽고 INDEX·변경 이력·계약·Orchestrator·구조·06·용어·발표·FAQ·시연을 함께 갱신했다. 다음은 읽기 선정만 한 PLANNED다. GMAIS의 고정 model_ref 설명과 달리 latest/current·공백을 수용하는 경로를89의 지원 범위와 맞추는 순수 문자 선언 검사를 검토한다. 허용 입력을 줄이는 변경이므로 동작 불변 refactor로 부르지 않는다. 기존400/Store이전거부·정상pin의BLOCKED·원schema/RFC1/2를 유지할 계획이다. 권위 있는 model version 필드와 불변 등록 정책이 없어 실제 model resolver는 BLOCKED이며 dataset_version 대체나 과거 역채움은 금지한다. 현재 구현·API실행은 없다. 전체개발과10분보고는계속된다.


## 실제 UI95 관측의 범위

실제 UI5174의1449×1087에서13check가모두통과했다. RFC1미등록MATCH에서RFC2미등록BLOCKED/innerMATCH로전환,잘못된capability·등록관계/3false·schema차단NOT_RUN·중복JSON400을확인했다. 선택해제는RFC1으로돌아가고기존88결과와독립이며접기펼치기는결과/선택을보존했다. node편집과뒤로이동후복귀는결과를지우고빈입력/defaultoff/disabled로돌아갔다.

fullJob수동클릭9회와기존88클릭1회는조작기록이며네트워크계측수는아니다. 기존계획·계보·노드수동진단은자기POST를계속사용하고새RFC2를자동발생시키지않는다. 전체POST0으로설명하지않는다. 문서와두패널overflow0/console오류없음을확인했고원Workflow초안을정확복원해합성입력/결과를지웠다.

모바일·강제지연/취소응답·브라우저503/auth·5173적용·이번단위forward는미검증이다. 화면에실제합성초안을표시한근거이며운영Job/Workflow제출·실능력/과학승인·executor검증은아니다.


## 최종 회귀와 보존

최종 backend 전체 **966건 중965 PASS·기존 Windows symlink 권한 제약1 SKIP**,350.995초·종료0이다. deterministic 경계시험은 통과했다. 신규core8/API10은전체에포함되고API관련69·독립18·UI관련/독립24와교차사례를전체에더하지않는다. UI신규10포함전체137 PASS·build88modules/19.48초PASS다.

시험 후 보호141참조·기존코어/원schema62개·catalog14·Job2본문·이전증거576파일이같았다. 기존추적수정은workflow_job_request_handoff_api.py·FullJobHandoff.tsx·scopedCSS의허용3파일뿐이다. 지정한보호범위이며전체workspace/과거runtime/원자snapshot인증은아니다. 기존RFC1adapter/14시험·89core·93helper·원schema는보존했다.

실제8002/5174의합성진단은확인했으나nonreload8000/8001적용은미검증이다. 운영JobPOST·역채움·executor·프로젝트실자료QA·정식학습은0이다. 전체회귀의합성fixture는운영QA와구분한다. 실제등록관계가관측돼도기존24false와새3false·학습BLOCKED는유지한다.
