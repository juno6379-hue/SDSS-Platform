# 288 — 로컬 STAC 파일 보호 어댑터 공유 적용

상태: IMPLEMENTED_UNVERIFIED(운영 SURVEY 연결), TESTED_SYNTHETIC(실제 프로젝트 회귀). 2026-10-18 21:07 KST.

## 변경과 이유

281 격리 구현과 287 독립 정적 검토를 거쳐 `backend/app/data/bare_survey_stac_file.py`와 `tests/test_bare_survey_stac_file281.py` 두 파일만 새로 추가했다. 기존 8개 기반 파일은 덮어쓰지 않았다. 작은 STAC 원문 파일의 바이트와 신원을 확인한 뒤 기존 246 순수 binding 검사를 호출하는 내부 어댑터다.

`read_pinned_survey_stac(root, request, selected_asset, maximum_read_bytes)`는 최대 1MiB, 단일 파일 descriptor, 실제 읽은 바이트 계측, SHA, 파일·부모 identity, hardlink/reparse 검사를 적용한다. 고정 오류 코드를 반환하고 원 ID·원문 시각을 자동 변환하지 않는다. 기존 226/246 계약과 v1 동작은 그대로다. 다른 자산 참조 파일까지 열어 검증하지 않으며, 이 결과는 실행 허가 토큰이 아니다.

## 실제 적용·시험 근거

- Root 실행: `python -X utf8 evidence/integration/survey288-apply-root-20261018.py --audit-sha256 194affdac6f8838875251bdb8c6cb2807cc3492015b3b655ba71ae040ba8c455`.
- 결과: `evidence/integration/survey288-application-root-20261018.json`, `ADDITIVE_TWO_FILES_APPLIED_PROJECT61_VERIFIED`, exit 0, 전체 1.968초.
- 실제 프로젝트의 세 모듈 회귀: 61 PASS / 0.922초. 격리판의 같은 61개와 합쳐 122개 독립 시험으로 표현하지 않는다.
- 로그: `evidence/integration/survey288-project-regression-root-20261018.log`, SHA `73b47b637619cd9bb6169efd16bfdf1fa9e5f11db8ace390ea7913f0d9ee715c`.
- 제품 SHA `542c418f2fb7ed47c4e03a9fa9fad73bc2c4effcc5f95aaac27209792dac468c`; 시험 SHA `57eb43e36dc44d0bebc2f64040bef28daedf3ffe3179bd023407d379bf60e31d`.
- 수집 코어 39핀, 새 2핀, 운영 source/원장/후보/나지검토/profile 5핀 보존. 운영 원본·원장 변경, HTTP, 수집, 학습 시작은 0.

## 계약·사용법·한계

호출자는 기존 strict typed request와 고정 파일 SHA를 제공한다. 읽기 allowance는 한 호출의 로컬 자원 한도이며 공유 원격 수집 예산을 대신하지 않는다. 실제 Windows junction 전체와 공격자의 모든 원자적 교체 가능성을 검증했다고 주장하지 않는다. 합성 parent 교체 시험과 실제 운영 검증을 구별한다.

SURVEY runner, registry, 공유 예약·2초 간격·429 정지 및 support 소비 연결은 아직 없다. 따라서 나지 확보량·수집 승인·독립 정답 확보를 의미하지 않는다. API·UI가 이 모듈을 아직 소비하지 않아 화면 변경과 서버 재시작은 필요하지 않다. 289 시각 v2 제안은 별도 PLANNED 문서이며 이 적용에 포함되지 않는다.

## 인계

285 신규 자료의 독립 감사 완료 이후 원본을 고정한 상태에서 적용했다. 다음 ML 290은 새 고정 후보 QA 준비 단위이며 Root GO 전 실행하지 않는다. 별도 understanding_agent에 281/287/288 완료 코드와 시험, 285 실제 확보량을 전달해 설명·대본·FAQ·INDEX·변경 이력을 갱신한다.
