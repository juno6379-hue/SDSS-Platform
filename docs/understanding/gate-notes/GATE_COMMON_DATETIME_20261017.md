# Gate Common Datetime 20261017 — 공통 날짜 검사의 환경 일관성

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | d474d5bce6c2a6c4bd8ba141c9256d15f6004631 (108까지 구현 검토 기준; 이 메타데이터 정리는 후속 문서 커밋) |
| evidence_paths | `backend/app/schema_formats.py`; `backend/app/gmais_api.py`; `backend/app/workflow_job_request_handoff.py`; `tests/test_schema_formats.py`; `docs/implementation/92_common_datetime_validation.md`; `evidence/integration/common-datetime-related-20261017.log`; `evidence/integration/common-datetime-independent-20261017.log`; `evidence/integration/common-datetime-source-runtime-20261017.json`; `evidence/integration/common-datetime-catalog-observation-20261017.json`; `evidence/integration/common-datetime-next-review-20261017.json`; `evidence/integration/common-datetime-full-tests-20261017.log`; `evidence/integration/common-datetime-live-integrity-20261017.json` |
| confidence | 원 schema·격리 시험·새 Python 프로세스의 합성 날짜 검산; 운영 서버 날짜 적용 미검증 |
| status | TESTED_SYNTHETIC; source 검증 완료·운영 서버 동작은 별도; 전체 개발 진행 중 |

## 쉬운 설명

검사 창구마다 쓰던 달력 검사기를 같은 제작법으로 만든다. 어떤 컴퓨터에 선택 부품이 없어도 날짜 검사가 빠지지 않도록 한다. 새 검사기는 새로 만들 때 연결하며 이미 쓰고 있는 창구의 도구를 몰래 바꾸지 않는다. 날짜 모양이 맞아도 사업 기간이 적절하거나 자료가 준비됐다는 뜻은 아니다.

## 이론적 배경

로컬 jsonschema 기본 FormatChecker에는 선택 dependency 부재로 date-time 등록이 없었다.89는 전용 checker로만 보완했다.92는 `schema_formats.create_format_checker()`를 공통 factory로 추출해 공통 Job validator와 Workflow validator의 생성 시점,89 호환 wrapper가 재사용하도록 했다. 원 schema와 class registry·이전 checker는 바꾸지 않는다.

코드 수정과 실행 프로세스 적용은 다르다. 이전 모듈과 cached validator가 남아 있는 프로세스는 소스만 바뀌어도 그 객체가 바뀌지 않는다. 새 소스로 만든 검사기의 동작을 확인했고 기존 서버의 실제 날짜 동작은 별도 근거가 필요하다.8002의 reload나 PID 존재만으로 동작 검증을 대신하지 않는다.

## 코드와 데이터 동작

`create_format_checker()`는 매번 새 FormatChecker 인스턴스를 만들고 date-time 지원 subset을 등록한다. gmais_api의 `_job_request_validator()`·`_workflow_plan_validator()`가 생성할 때 사용한다. 기존 LRU cache 재사용은 유지한다.89의 `_draft_format_checker()`는 이름을 남긴 호환 wrapper로 같은 factory를 호출한다.

4자리 연도와 실제 달력, T/t·시분초·선택 소수초·Z/z 또는 명시 timezone을 지원한다. offset 시간00..23/분00..59를 먼저 검사해 +00:60 정규화를 막는다. timezone 없음·잘못된 날짜·24시·leap second·연도0000은 거부한다. 모든 RFC3339 표현을 지원하는 것은 아니다. non-string의 type 거부는 schema가 담당하며 format checker는 중립이다.

기간 start/end의 순서·timezone 변환·과학 기간 정책은 검사하지 않는다. 현재 Workflow 원 schema에는 format 필드가 없어 checker 생성만 통일하고 plan 응답은 그대로다. Job의 잘못된 날짜는 기존400 INVALID_REQUEST와 schema 메시지를 유지하며 Store 접근 전에 거부한다. 정상 제출의 기존409 MODEL_NOT_READY/BLOCKED 기록은 임시 Store에서 동등성을 확인했다. 실제 운영 Job을 제출한 것이 아니다.

90 fullJob 수동 검사의 잘못된 날짜는 여전히 정상 진단200 BLOCKED다. 기존 제출의400과 구분한다. 새 화면·상태·필드·오류 계약을 추가하지 않아 직접 프론트 수정·build·브라우저 재시험은 없다.

## 시험과 실제 source 관측

신규10시험을 포함한 관련67 PASS/6.190초, 독립40 PASS/2.972초다. 정상 날짜6·거부 날짜13과start/end26경계, checker 독립·class/cache 불변, 잘못된 제출 Store0/400, 정상 제출 임시기록/409동등, Workflow응답동등을 확인했다. 세부 사례와 반복 수를 전체 unittest에 추가 합산하지 않는다.

새 Python 프로세스와 실제 vendored schema로 기본date-time등록false·shared등록true를 확인했다. 정상6개는수락·잘못된13개는거부했으며 운영앱import·HTTP제출·Store호출은없었다. 이는실제소스를쓴합성초안검증이고운영서버적용이나자료과학성능의증거가아니다. 최종 전체937건/936 PASS/기존1 SKIP/345.696초·종료0과 보존 근거를 확인했다.

## 한계와 기존 상태

공통 source의 날짜 검사는 보완했지만 실행 중8000/8001의 이전 모듈 적용은 미확인이다.8002 reload/PID만으로 날짜 동작을 주장하지 않는다. class 전역이나 이미 생성된 cache를 후행 변조하지 않았다. 원 schema·API 응답 필드·준비성·학습 gate는 바꾸지 않았다.

날짜형식이정상이어도데이터존재·정확라벨·Agent/모델·기관ACL·과학·실행승인은아니다. 원본5차단·후보1095패치/4차단·예약136314880B·환불0·Workflow PLAN_ONLY를유지한다. 새JobPOST·수집·QA·학습·배포는없다.

## 1분 발표

“날짜 검사가 컴퓨터의 선택 부품에 따라 빠지지 않도록 공통 검사기를 만들었습니다. 새로 생성하는 공통 validator와 초안 검사기가 같은 규칙을 사용합니다. 존재하지 않는 날짜와 잘못된 시간대는 거부하지만 기간의 사업상 적합성까지 승인하지는 않습니다. 기존 도구나 cache를 몰래 바꾸지 않고 API의 오류 형식도 유지했습니다. 새 Python 프로세스와 격리 시험으로 확인했으며 기존 실행 서버가 새 날짜 규칙을 쓰는지는 별도입니다. 자료 준비도나 학습 승인은 그대로 차단 상태입니다.”

## 5분 발표 순서

1. **0~1분:** 창구별 달력 검사기의 공통 제작법을 설명한다.
2. **1~2분:** 선택 dependency 공백과 공통 factory 생성 시점을 나눈다.
3. **2~3분:** 날짜 지원 subset·기간 순서와 과학 정책 미검사를 설명한다.
4. **3~4분:** 합성 시험·fresh source 관측·운영 서버 적용의 차이를 말한다.
5. **4~5분:** 기존400/200BLOCKED·UI 불변·준비성 차단을 설명한다.

10분 설명에서는 non-string/type 책임·전역/cache 독립·임시 정상제출동등·Workflow schema의format부재를추가한다.

## Q&A

**모든 날짜 표준을 지원하나?** 지원 subset이다. leap second와 연도0000은 거부한다.

**start보다 end가 빠르면 막나?** 이번 변경은 형식만 본다. 기간 순서와 정책은 별도다.

**이미 켜진 서버도 바로 바뀌나?** 기존 프로세스와 cache에 따라 다르다. 소스 확인과 서버 동작 확인을 나눈다.

**새 화면이 필요한가?** 오류·상태 계약이 같아 기존 표시를 사용한다. 이번 직접 UI 재시험은 없다.

**날짜가 맞으면 학습 가능한가?** 아니다. 데이터·모델·권한·과학·학습 준비도는 별도다.

## 이후 갱신

최종 전체·보존 근거를 읽고 INDEX·변경 이력·계약·Orchestrator·구조·용어·발표·FAQ·시연을 함께 갱신했다. 다음은 PLANNED다. 기존 Job 제출과 Workflow의 Agent-capability 등록 관계 판정을 순수 공통 계약으로 추출할 후보를 읽기 검토했다. 기존 오류와 Store 접근 순서를 유지하고 별도 진단 wrapper나89~91의 새 검증 축을 자동 추가하지 않을 계획이다. 아직 구현·시험·운영 API 실행은 없다. 전체개발과10분보고는계속된다.


## 기존 카탈로그 관측

읽기 전용 snapshot의14기록과 기존Job2 본문SHA는 같았다. Job은BLOCKED·capture부재를 유지했고 저장Workflow는0건이었다. 새 운영Job은0이다. 이는 환경 보존 관측이며 날짜 검사의 실제 운영 제출이나 모델·과학 승인 근거가 아니다.


## 최종 회귀와 보존

최종 backend 전체 **937건 중936 PASS·기존 Windows symlink 권한 제약1 SKIP**,345.696초·종료0이다. 기존 deterministic 경계시험은 통과했다. 신규10개는 전체에 포함되며 관련67/6.190초·독립40/2.972초·세부 날짜 사례를 추가 합산하지 않는다.

시험 종료 후 보호141참조·기존 코어/원schema57개·catalog14·기존Job2본문이 같았다. 기존 추적 수정은 허용한gmais_api.py와workflow_job_request_handoff.py 두 파일뿐이다. 지정한 보호 범위이며 전체 workspace나 원자 snapshot 보장은 아니다. 새 운영Job제출·역채움·executor·QA·학습은0이다.

새 공통 source와 freshprocess의 합성 날짜 검증은 완료했다. 실행 중 non-reload8000/8001과8002의 실제 날짜 동작을 운영HTTP로 확인한 것은 아니다. PID/reload 관측을 날짜 적용 성공으로 확대하지 않는다. 기존 오류/화면 계약을 유지하므로 직접 frontend/build/브라우저 재시험은 없다.
