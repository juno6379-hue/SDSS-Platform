# 95 — 완성 Job 초안의 선택적 로컬 등록관계 관측 UI

## 2026-10-17 — model_ref 고정 문자 선언 검사 통일 (96)

`model_reference_contract.model_reference_issue()`를 GMAIS 제출 검사와 89 초안 검사에서 공유한다. id/version 및 제공한 role은 기존 89와 같은 1..256자 지원 범위로 확인하며, 공백만 있는 문자열·제어문자·단독 surrogate와 latest/current 버전 별칭을 거부한다. 정상 고정 문자열을 trim하거나 바꾸지는 않는다. 기존에 지원하던 패딩된 고정 v1과 256자 경계도 유지한다.

GMAIS는 기존 schema·SHA 검사를 먼저 하고, 새 문자 거부를 Store 접근 전 기존 `400 INVALID_REQUEST` 형식으로 반환한다. 이는 공통 제출 API의 허용 입력을 좁히는 변경이다. 89의 기존 모델 차단 코드와 순서, RFC1/RFC2 결과, 24개 false 플래그는 보존한다. 원 schema에서 SHA는 양쪽 모두 필수이며 helper가 SHA/URI/키 정책을 대신하거나 완화하지 않는다. model_ref 부재는 그대로이고 명시 null은 기존 schema 오류다.

이 검사는 문자 선언의 지원 범위만 확인한다. 실제 등록 모델·checkpoint·권위 있는 model version·기관 ACL·과학·실행 승인을 조회하지 않으며 `model_verified=false`를 유지한다. 기존 UI 오류 표시로 처리할 수 있어 직접 프론트 수정·build·브라우저 재시험은 없다. 지원 범위, 새 오류와 격리시험 근거는 [문서96](96_model_reference_contract.md)를 참조한다.

상태: **TESTED_SYNTHETIC** — 신규 adapter 시험과 Python94 producer 교차 검산, 기존 프론트 회귀 및 production build를 검증했다. 실행 중 서버와 실제 브라우저 반영 여부는 Root의 별도 증거를 따른다. 운영 Job 제출이나 실행 승인이 아니다.

## 사용자 흐름과 이전 동작 보존

기존 `완성 Job 초안 검토` 안에 기본 선택 해제된 `로컬 등록관계도 확인 (RFC2)` 체크박스를 추가했다. 선택 해제 시 기존 RFC1의 정확한 네 키 요청·adapter·오류·결과 표시를 사용한다. 기존 RFC1 adapter와 시험 파일은 수정하지 않았다. 선택한 경우 같은 수동 검사 버튼과 endpoint에 `contract_version: 2`를 추가한 정확한 다섯 키 요청을 보낸다.

체크박스 선택, 펼치기, 편집, 기존 계획·계보·노드 조회는 새 RFC2 검사를 자동으로 발생시키지 않는다. 기존 진단 버튼 자체의 수동 POST는 그대로 유지한다. 원 Workflow·선택 노드·완성 Job 원문을 보존하며 자동 채움·Job 생성·Workflow 실행이 없다. 사용자 입력은 빈 상태로 시작한다. 버전 선택도 요청 identity에 포함하므로 버전·원문·노드·Workflow·revision 편집, popstate/hashchange, 표시 중단, unmount는 이전 응답 표시를 무효화한다. 표시 무효화는 서버 처리 취소가 아니다.

## 응답 계약과 상태 구분

새 `fullJobRegistrationAdapter.ts`는 기존 prepare의 canonical Workflow pin과 metadata preview를 재사용하고, 버전이 포함된 전체 RAW body UTF-8 SHA를 새로 계산한다. 완성 Job 소수·지수 원문과 Python 관측 SHA의 기존 처리도 그대로다. RFC2 exact wrapper는 extension `greenblue.workflow-full-job-input-handoff.rfc2`, INTERNAL_REVIEW, upstream false, 전체 요청 SHA, result 다섯 키다.

result는 정확한 여덟 키다: schema_version 2, 고정 scope, status, full_job_comparison, local_manifest_registration, actual_capability_supported false, institution_acl_verified false, execution_authorized false. 등록축은 정확한 세 키 source/status/checked이며 source는 LOCAL_STATIC_AGENT_MANIFESTS다. full_job_comparison은 기존 RFC1 안전 view로 다시 확인한다. 기존 24 false, 명시한 7개 typed I/O 0, schema 파일 읽기 null, metadata hash와 phase 안전 검사를 통과해야 한다.

| 앞선 완성 Job 비교 | 등록축 | checked | 최상위 표시 |
| --- | --- | --- | --- |
| BLOCKED | NOT_RUN | false | BLOCKED |
| MATCH | REGISTERED | true | MATCH |
| MATCH | AGENT_UNKNOWN | true | BLOCKED |
| MATCH | CAPABILITY_UNREGISTERED | true | BLOCKED |

등록 미확인은 앞선 metadata MATCH와 분리해서 표시한다. REGISTERED는 로컬 정적 manifest의 Agent·capability 이름 등록관계 관측이다. 실제 capability 지원·모델 준비도·과학적 검증·기관 ACL·실행 승인을 의미하지 않는다. 이 세 비승인 false를 화면에서 명시한다. 서버가 수행하는 in-memory manifest 관측을 UI가 다시 조회하지 않으며 원 schema cold load는 미계측 null이어서 전체 I/O 0이라고 주장하지 않는다.

기존 400/413/503/401/403 고정 오류 안내를 유지한다. 응답 extension·hash·exact key·등록축 phase·outer/inner 상태·승인 false가 어긋나면 결과 사용을 차단한다. RFC2가 자동으로 RFC1 응답을 수용하거나 그 반대로 승격하지 않는다.

## 화면과 검증 근거

기존 전문 SVG Icon을 등록관계 제목에 재사용했다. checkbox 전용 scoped CSS가 기존 text input의 전체 너비 규칙을 덮어쓰며 등록관계와 이전 비교를 두 열로 표시한다. 좁은 폭은 한 열로 전환한다. 실제 1449px 브라우저 overflow·뒤로 이동·서버 반영 근거는 Root가 기록한다. 모바일 실기기 검증은 수행하지 않았다.

- 관련 시험: `evidence/integration/full-job-registration-ui-related-20261017.log`, **24 PASS / 24406.859ms** — 신규10 + 기존14. 새 시험의 마지막 한 개는 Python94 실제 producer의 REGISTERED/AGENT_UNKNOWN/CAPABILITY_UNREGISTERED/NOT_RUN 네 합성 상태를 JS view와 교차 검산한다. 네 경우를 별도 시험 수에 합산하지 않는다.
- 전체 프론트: `evidence/integration/full-job-registration-ui-tests-20261017.log` — **137 PASS / 11405.9891ms**, 기존127개를 보존했다.
- production: `evidence/integration/full-job-registration-ui-build-20261017.log`, **88 modules / 19.48초 / PASS**. 기존 500kB chunk 경고가 남아 있다.
- 독립 검토·실제 서버/브라우저 증거는 Root가 같은 단위로 연결한다. 이 문서만으로 운영 서버 반영 완료나 운영 Job 성공을 주장하지 않는다.

## 관련 자료

- [기존 수동 초안 UI](91_full_job_handoff_ui.md)
- [Agent·capability 공통 계약](93_agent_capability_contract.md)
- [현재 인계서](00_next_session_handoff.md)
- [최신 이해자료](../understanding/INDEX.md)

이번 단위에 실제 Job POST·실행·수집·QA·학습·배포는 없다. 전체 개발은 미완료다.

## Root 최종 통합 확인

전체backend966개/965 PASS/기존1 SKIP/350.995초/exit0. 보호141·불변core+schema62·catalog14/기존Job본문·이전증거576파일을보존했다. 관련API69/독립18·프론트137/build88modules19.48초는각시험종류별근거이며반복사례를신규시험수에더하지않는다.

`full-job-registration-api-live-api-20261017.json`은8002합성진단HTTP15경우, `full-job-registration-api-live-ui-20261017.json`은5174실제브라우저13check를기록한다. RFC1보존·로컬등록/차단/NOT_RUN·중복400·버전전환/old88독립·접기펼치기/편집clear·뒤로가기초기화와원Workflow정확복원을확인했다. 9회fullJob수동클릭+1회old88클릭은네트워크계측치가아니다.1449×1087 overflow0/console[]·SVG정렬과정상/차단PNG를확인했다. 모바일·강제지연/취소·브라우저503/auth·5173·이번forward는미검증이다.

8002진단/5174화면의합성초안확인과운영Job제출/Workflow실행·기관ACL/과학/승인은구분한다. nonreload8000/8001적용미검증·운영Job생성/수집/정식학습/배포0. 관련문서·인계서와이해자료/대본/FAQ·INDEX/변경이력을같은단위로갱신하며최종감사는 `evidence/integration/full-job-registration-api-closeout-20261017.json`을따른다.
