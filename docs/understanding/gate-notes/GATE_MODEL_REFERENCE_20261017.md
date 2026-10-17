# Gate Model Reference 20261017 — 고정 모델 문자 선언의 지원 범위 일치

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/model_reference_contract.py`; `backend/app/gmais_api.py`; `backend/app/workflow_job_request_handoff.py`; `tests/test_model_reference_contract.py`; `docs/implementation/96_model_reference_contract.md`; `evidence/integration/model-ref-related-20261017.log`; `evidence/integration/model-ref-source-runtime-20261017.json`; `evidence/integration/model-ref-independent-20261017.log`; `evidence/integration/model-ref-full-tests-20261017.log`; `evidence/integration/model-ref-live-integrity-20261017.json`; `evidence/integration/model-ref-next-review-20261017.json`; `evidence/integration/model-ref-original-gmais-20261017.py`; `evidence/integration/model-ref-original-handoff-20261017.py` |
| confidence | 완료 코드·원문핀 대조·격리 합성시험; 실제 모델 버전 resolver와 운영 제출 미검증 |
| status | TESTED_SYNTHETIC; GMAIS 허용 입력 축소; 실제 model resolver BLOCKED |

## 쉬운 설명

모델을 주문할 때 “최신 것” 대신 어느 버전인지 적게 한다. 기존 초안 창구는 이를 막았지만 공통 접수 창구에는 빠진 검사가 있었다. 같은 문자 검사 규칙을 두 곳이 쓰도록 했다. 이름과 버전 표기가 맞아도 그 모델이 실제 보관함에 있고 그 버전의 파일이 맞는지는 아직 확인한 것이 아니다.

## 이론적 배경

고정 id/version/SHA를 요구한다는 안내와 달리 GMAIS 공통 검사는 공백·latest/current 등을 받았다.89는 이미 거부했다.96은89의 문자 지원 규칙을 공통 pure helper로 묶고 GMAIS의 schema/SHA 검사 뒤에 적용한다. GMAIS 허용 입력을 줄이는 명시적 동작 변경이며 동등 refactor가 아니다.89의 기존 지원 범위·결과는 보존한다.

정상 고정 선언과 선언 부재의 동작 보존, 새 거부 대상의 변경을 나누어 검증한다. 실제 모델 version의 권위 필드와 불변 등록 정책은 없으므로 모델 Registry/checkpoint resolver를 연결하지 않는다. dataset_version을 model version으로 바꾸어 쓰거나 과거 값을 채우지 않는다.

## 코드와 오류 순서

`model_reference_issue(ref)`는 id/version과 선택role을exact문자열1..256자·비공백·제어문자/surrogate없음으로확인한다. 문자조건이먼저이며실패하면MODEL_REFERENCE_INVALID다. 통과후version의strip/lower가latest/current이면MODEL_VERSION_NOT_PINNED다. 비교를위해별칭을식별할뿐입력을정규화하거나덮어쓰지않는다. “ v1 ”같은비별칭패딩은기존89처럼보존한다.

helper는SHA·URI·허용키·원schema정책을소유하지않는다. 두caller의원schema는id/version/sha256를필수로요구한다. helperNone은검사할선언없음중립이지명시null의schema허용이아니다. 요청키생략은이전처럼허용하고명시null은schema에서거부한다. SHA누락/오류·타입·URI·추가키같은기존schema오류와GMAIS수동SHA검사가새문자검사보다우선한다.

GMAIS는새거부대상을등록관계/Store factory전에기존400INVALID_REQUEST envelope로막는다.89는schema→bbox→model→context→metadata순서와기존model코드를유지해정상진단200BLOCKED다. 원schema·90/94safevalidator·RFC1/2·24false·schemaIO null은그대로다. Workflow계획은변경하지않는다.

## 시험과 source 관측

신규11개를포함한관련112 PASS/21.832초다.256/257문자·공백/제어문자/surrogate·role·별칭대소문자/패딩·비별칭원형·None/명시null·SHA/URI/type우선순위를검증했다. 핀된변경전gmais/89모듈과정상/부재/패딩/경계의응답·headers·임시Job/멱등기록·Store접근순서,89/RFC1/2전체결과를대조했다. 새거부대상은변경사례이며정상동등성과혼동하지않는다.

freshsource9사례는정상3/새거부6의기대값과같았다. 원공통validator가과거문자를수용했다는사실은모든옛전체route가저장·실행성공했다는증거가아니다. 운영route/Store/JobPOST·모델Registry/checkpoint읽기는0이었다. 신규helper의IO0은전체handler/schema/임시Store시험IO0이아니다. 독립41 PASS/4.101초와 최종 전체977건/976 PASS/기존1 SKIP/348.393초·종료0,보존근거를확인했다.

## UI와 실제 적용 한계

기존AgentCenter400안내와fullJobmodel코드/RFC2NOT_RUN표시가이미지원해직접frontend/build/브라우저재시험은없다. 이전95실제화면근거를96에서재실행했다고말하지않는다. nonreload8000/8001적용과공통제출의실제서버행동은미검증이다.8002reload/PID만으로검증을대신하지않는다.

선언이정상이어도실제모델존재·버전파일동일성·readiness·기관ACL·과학·실행승인은아니다. model_verifiedfalse·등록축3false/기존24false를유지한다. 원본5차단·후보1095/4차단·예약136314880B·환불0과학습BLOCKED는변하지않는다. 운영JobPOST·수집·QA·정식학습·배포는없다.

## 1분 발표

“모델 버전을 고정해서 적으라는 규칙과 실제 접수 검사의 차이를 보완했습니다. 공백이나 최신 버전 별칭을 공통 접수에서도 거부하고 기존 초안 검사와 같은 문자 규칙을 사용합니다. 이는 받는 입력을 줄이는 변경이며 단순 리팩터가 아닙니다. 정상 고정 선언의 응답과 기록은 그대로인지 비교했습니다. 다만 이름과 버전 문자가 맞아도 실제 모델 파일과 버전은 아직 조회하지 않습니다. 권위 있는 모델 버전 계약이 없어 resolver는 차단 상태이고 학습·실행 승인은 별도입니다.”

## 5분 발표 순서

1. **0~1분:** “최신 것” 대신 고정 버전을 적는 주문 비유를 말한다.
2. **1~2분:** 허용 입력 축소와 정상 동작 보존을 나눈다.
3. **2~3분:** 문자·별칭·schema/SHA 우선순서와 생략/null을 설명한다.
4. **3~4분:** 원문핀 동등성·새 거부·source9사례·전체시험을 구분한다.
5. **4~5분:** 실제 model resolver 부재·UI 재시험 없음·승인 한계를 말한다.

10분 설명에서는비별칭패딩원형·24false·schemaIO범위·dataset_version대체금지와운영서버적용미확인을추가한다.

## Q&A

**최신 별칭을 막으면 실제 불변 모델인가?** 아니다. 문자 선언만 확인한다. 실제 버전 권위와 파일 검증은 별도다.

**이번은 동작이 같은 리팩터인가?** GMAIS는 허용 입력을 줄였다. 정상 보존과 새 거부를 구분해야 한다.

**model_ref=null도 생략과 같은가?** helper의None중립과 요청schema는 다르다. 명시null은schema가 거부한다.

**dataset_version으로 모델 버전을 대신하나?** 하지 않는다. 권위 model version 계약이 없어 실제 resolver는BLOCKED다.

**새 화면 검증을 했나?** 기존 오류 표시가 지원해 직접프론트·브라우저재시험은없다. 이전95근거와구분한다.

## 이후 갱신

독립·전체·보존 근거를 읽고 INDEX·변경 이력·계약·Orchestrator·구조·용어·발표·FAQ·시연을 함께 갱신했다. 다음은 PLANNED다. 미래 내부 register_experiment에 선택적 caller model_version 선언을 붙일 후보를 읽기 검토했다. 생략은 기존 record와 같고 명시값은 checkpoint/report SHA와 연결하되 caller 선언을 기관권위나승인으로부르지않는다. 중복id거부·legacy역채움금지·dataset_version대체금지를유지하고report필드충돌규칙을먼저확정해야한다. 기존Store두쓰기의비트랜잭션/전역불변성한계도그대로이며현재구현은없다. 전체개발과10분보고는계속된다.


## 최종 회귀와 보존

최종 backend 전체 **977건 중976 PASS·기존 Windows symlink 권한 제약1 SKIP**,348.393초·종료0이다. deterministic 경계시험은 통과했다. 신규11개는전체에포함되고관련112/21.832초·독립41/4.101초·source9사례를추가합산하지않는다.

보호141참조·기존코어/원schema66개·catalog14·Job2본문·이전증거599파일은같았다. 기존추적수정은gmais_api.py와89helper의허용2파일뿐이다. 지정한보호범위이며전체workspace/독립옛runtime/원자snapshot인증은아니다. 운영JobPOST·역채움·executor·프로젝트실자료QA·정식학습은0이다. 전체회귀의합성fixture와운영QA를구분한다.

원schema·90/94safevalidator·RFC1/2·UI코드는보존했다. 직접프론트/build/browser재시험은없고직전95근거를이번재검증으로부르지않는다. source허용범위보완과실제공통제출서버적용은별도이며modelresolver/승인·학습BLOCKED는유지한다.
