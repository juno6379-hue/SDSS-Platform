# Gate Full Job Handoff 20261017 — 전체 초안 schema 검사와 입력 선언 대조

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/workflow_job_request_handoff.py`; `tests/test_workflow_job_request_handoff.py`; `docs/implementation/89_workflow_job_request_handoff.md`; `evidence/integration/full-job-handoff-related-20261017.log`; `evidence/integration/full-job-handoff-independent-20261017.log`; `evidence/integration/full-job-handoff-initial-format-gap-20261017.log`; `evidence/integration/full-job-handoff-full-tests-20261017.log`; `evidence/integration/full-job-handoff-live-integrity-20261017.json`; `evidence/integration/full-job-handoff-catalog-observation-20261017.json`; `evidence/integration/full-job-handoff-runtime-start-20261017.json` |
| confidence | 완료 코드·격리 합성 시험; 운영 full Job 제출·실행 미검증 |
| status | TESTED_SYNTHETIC; 공개 API·UI 미연결; 전체 개발 진행 중 |

## 쉬운 설명

사용자가 채운 주문서 전체가 정해진 양식에 맞는지 먼저 본다. 그 다음 담당자와 재료 목록만 꺼내 원 작업 지시서와 비교한다. 주소와 결과물 요청을 대신 채우지는 않는다. 양식에 맞고 재료 목록이 같아도 주소가 사업 목적에 맞는지, 재료가 실제로 존재하는지, 주문을 실행해도 되는지는 별도다.

## 이론적 배경

87/88은 네 필드 metadata를 사용자가 직접 작성했다. 89는 사용자가 작성한 full Job request를 원 schema로 검사하고 agent/capability/trace/input_refs만 추출해86을 한 번 호출한다. 전체 초안의 schema 적합성과 선택 입력의 선언 동등성은 서로 다른 질문이다. AOI/output/model/context를 추정하거나 Job을 생성하지 않는다.

전체 초안 관측 hash와 추출 metadata hash도 다르다. AOI·output·parameters·purpose가 바뀌어도 추출 입력은 같아 MATCH일 수 있다. 전체 초안 hash는 달라지므로 caller가 이후 초안 변경을 확인하는 데 쓸 수 있지만, 이 함수에는 full Job expected pin 인자가 없다. full_job_pin_verified=false이고 원본 인증도 아니다.

## 코드와 데이터 동작

`compare_workflow_job_request_handoff(workflow_request, pinned_workflow_request_sha256, selected_node_id, full_job_request)`는 먼저 두 객체의 bounded JSON 형태를 검사한다. exact builtin JSON·finite float와2^53−1 이내 int를 지원한다. depth24/atoms16384/string4096/key256/각 canonical UTF8 512KiB를 제한하고 cycle·surrogate·임의객체·비문자key를 거부한다. 일부 byte 계수는 보수적이라 경계 요청을 더 일찍 거부할 수 있다. 이미 객체로 잃은 중복 JSON 키를 복원하는 parser는 아니다.

기존 `_job_request_validator()`의 vendored 원 schema를 재사용한다. required·unknown·context·ref·CRS 등 양식을 확인한다. 전용 detached FormatChecker와 evolve를 사용해 기존 cached checker를 바꾸지 않는다. 날짜는 timezone·달력·offset 범위를 확인하며 leap second는 지원하지 않는다. 기간의 사업상 의미나 시작/종료 순서를 평가하지 않는다.

bbox는 finite int/float4개와 west<east/south<north를 확인한다. bool은 숫자로 받지 않는다. 소수 AOI는 정상 지원하지만 CRS 의미·기하 적합성·기대 AOI 일치는 별도다. model_ref가 있으면 비공백 고정 version 등을 확인하되 실제 모델 존재나 지원 capability는 검사하지 않는다. optional workflow_run_id가 있으면 원 Workflow와 같아야 하며 없으면 채우지 않는다.

검사를 통과하면 agent_id/capability_id/execution_context.trace_id/ordered input_refs만 추출해86을 정확히 한 번 호출한다. 앞 단계 차단은 comparator0회다. full_job_schema_validated와 bbox_numeric_order_validated는 각각 양식과 수치 순서 범위이며 complete_job_validated·aoi_verified·requested_outputs_verified·model/capability/과학/실행 flag는 false다.

## 시험 증거와 보완

최종 관련15 PASS/0.172초·독립15 PASS/0.220초다. decimal bbox·필수양식·날짜·추가키·context·범위·cycle·거대정수·metadata drift·model pin·전체hash와metadatahash 차이·privacy·원문불변·comparator1회를 확인했다. 실제 factory의 schema 미발견을 안전 자원 상태로 바꾸고 복귀하는 회귀도 있다.

초기 환경의 cached FormatChecker에 date-time 선택 dependency가 없어 잘못된 날짜가 통과했다. 전용 checker로 보완했고 offset +00:60을 정상화하는 동작도 범위를 먼저 제한해 막았다. cached checker 불변을 시험했다. 보완은89 전용 checker에만 적용했다. 기존 공통 validator의 환경상 date-time 미등록 공백은 그대로이며 전체 기존 API의 날짜 문제를 해결한 것은 아니다. 최초 실패 원로그는 덮어써져 남아 있지 않다. initial-format-gap은 현상을 다시 재현한 로그이며 최초 원본 로그로 부르지 않는다.

schema loader의 알려진 missing-schema RuntimeError만 RESOURCE_UNAVAILABLE로 바꾼다. 다른 프로그래밍 RuntimeError·AssertionError·종료 신호는 전파한다. 원문 예외는 반환하지 않는다. 독립 반복을 전체 시험에 더하지 않으며 최종 전체912건 중911 PASS·기존 Windows symlink권한1 SKIP/359.738초·종료0을 확인했다.

## IO와 실제 적용 한계

schema factory의 cold path는 로컬 schema를 읽을 수 있다. schema_files_read=null은 실제 파일 횟수를 계측하지 않았다는 뜻이며0이 아니다. source_files_read0은 자산 읽기 범위다. 전체 단위를 IO0으로 부르지 않는다. DB·Registry·resolver·자산·executor·Job제출은 호출하지 않는다.

Python canonical의 float 표현을 사용한다. JavaScript JSON.stringify와 소수·지수·1.0 등 표현이 같다는 교차언어 검증은 아직 없다.87의 int-only parser를 full Job에 그대로 적용하면 정상 AOI 소수를 거부할 수 있다. 전체 초안 양식 적합성은 실제 Agent capability·모델·기관 ACL·지리적합·라벨·과학·실행 인증이 아니다.

이번은 내부 helper다. 공개 API·UI·87/88 화면·원 schema·86 core를 바꾸지 않아 직접 UI 수정·프론트 재시험·브라우저 검사는 없다. 현재 metadata 화면을 full Job 검사 완료로 설명하지 않는다. 원본5차단·후보4차단과 Workflow PLAN_ONLY는 유지한다.

## 1분 발표

“사용자가 작성한 Job 초안 전체를 원 양식으로 검사한 뒤 담당자와 입력 목록만 골라 Workflow와 비교하는 기능을 추가했습니다. 소수 좌표와 날짜 형식도 지원 범위에서 확인합니다. 주소나 결과물·모델을 대신 채우지 않으며 실제 Job을 만들지 않습니다. 양식이 맞고 목록이 같아도 AOI의 사업 적합성이나 실제 파일·모델·권한은 별도입니다. 전체 초안의 관측 지문도 남기지만 원본 인증이나 고정 pin 검증은 아닙니다. 아직 내부 함수이며 기존 화면은 metadata 비교만 제공합니다.”

## 5분 발표 순서

1. **0~1분:** 전체 주문서 양식과 재료 목록 추출의 비유를 말한다.
2. **1~2분:** schema·bbox 수치 순서와 실제 적합성을 나눈다.
3. **2~3분:** 전체 초안 관측 hash와 metadata hash의 차이를 설명한다.
4. **3~4분:** 날짜 보완·합성15개와 원로그/재현 로그의 차이를 설명한다.
5. **4~5분:** schema IO·UI 미연결·모델/권한/실행 미검증을 말한다.

10분 설명에서는 JSON 객체 예산, detached checker·cache 불변, missing-schema 자원 오류 경계와 future decimal 교차언어 계약을 추가한다.

## Q&A

**schema가 맞으면 완성 Job으로 승인되나?** 아니다. 정해진 양식과 일부 수치 범위만 확인한다. 실행에 필요한 모든 조건은 아니다.

**AOI가 바뀌어도 MATCH일 수 있나?** 입력 metadata가 같으면 가능하다. 전체 초안 관측 hash는 달라진다.

**전체 초안 hash는 고정 pin인가?** 이번 내용의 관측 지문이다. 비교할 외부 full Job pin은 받지 않으며 출처 인증도 아니다.

**전체가 IO0인가?** 아니다. schema cold read가 가능하다. 자산·DB·Registry·실행기 호출0과 구분한다.

**기존 화면도 full Job을 검사하나?** 아니다.87/88은 metadata 화면이다. 새 full Job helper는 아직 API·UI에 연결하지 않았다.

## 이후 갱신

최종 전체·보존 근거를 읽고 INDEX·변경이력·계약·Orchestrator·구조·용어·발표·FAQ·시연을 함께 갱신했다. 다음은 PLANNED다. 별도 full Job 수동 API와88 아래 접는 독립 child를 연결할 계획이다. raw 전체 body SHA로 응답을 묶고 Python 전체 초안 관측 hash는 표시하되 JavaScript float canonical과 같다고 검증하지 않는다. Workflow pin은87 규약을 쓰며 full Job은 strict decimal/finite/int53 parser를 따로 검토한다. nullable schema IO·독립 stale 상태를 보존하고 Job은 생성하지 않는다. 기존 공통 validator의 날짜 일관성 개선도 별도 대기열이다. 아직 이 API/UI와 공통 날짜 보완의 구현·실제 검증은 없다. 전체 개발과10분 보고는 계속된다.


## 실제 환경 관측의 범위

읽기 전용 카탈로그14기록과 시작 canonical SHA는 같고 저장 Workflow는0건·기존 Job은2건이었다. 이는 환경과 보존의 관측이지 새 full Job helper의 운영 성공이 아니다. 새 helper의 근거는 TESTED_SYNTHETIC이며 Job POST·QA·학습은 없다.


## 최종 전체와 보존

최종 backend 전체 **912건 중911 PASS·기존 Windows symlink 권한 제약1 SKIP**,359.738초·종료0이다. 기존 deterministic 경계시험은 통과했다. 관련15/.172초·독립15/.220초는 반복이며 전체에 합산하지 않는다.

시험 후 보호141참조·기존 코어와 원 schema57개·catalog14·기존Job2본문이 같았다. 이전 추적 코드·데이터·시험·프론트 변경도 없었다. 지정한 보존 범위이며 전체 워크스페이스나 원자 snapshot 보장은 아니다. 새 helper의 근거는 TESTED_SYNTHETIC이고 운영 API·JobPOST·역채움·executor·새QA·학습은0이다.

기존86~88과 화면/API를 보존했다. 원본 원장·lock·예약136314880B와 원본5차단·후보1095패치/4차단을 유지한다. 전체 초안의 schema 적합성이나 선언 MATCH로 학습 BLOCKED를 해제하지 않는다.
