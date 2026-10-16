# ML·Model Type·MLOps Gap Analysis 초안

root 통합 `04_gap_analysis.md`에 병합할 ML 담당 초안이다. 기준 원문은 `GreenBlue_CODEX_Master_Prompt_GMAIS_Integrated_Platform_v1.0.md`이며 원문이 내부 지시 초안이라는 효력을 유지한다. TECH-4·GMAIS 원문과 추가 설계를 같은 출처로 표시하지 않는다. 상세 SOP/준비도 분리는 `08_model_type_validation_sops.md`, 실제 관측 snapshot과 코드 SHA는 `data/audits/gmais-ml-current-inventory.json`을 참조한다. 소유권은 root 통합 관리 파일에 전달했다.

| requirement_id | source_section | source_type | subsystem | owner_proposed | acceptance_evidence | current_state | gap | decision_required |
|---|---|---|---|---|---|---|---|---|
| ML-01 | §4 | 내부 마스터 | 유형별 Model Pipeline | ml_pipeline/root | model_type별 dispatch·조건부 artifact·오류 fixture | PARTIAL: LCLUC torch train/infer만 구현 | calibrated/statistical/inference-only/external 분기·카드·검증근거 없음 | GMAIS enum 원문 확보·유형별 책임기관 TBD |
| ML-02 | §4.1 | 내부 마스터 | 학습 준비성 | ml_pipeline/data_pipeline | real file hashes·split·class/quality·blocked 시험 | IMPLEMENTED gate / DATA BLOCKED | 마지막 실제 ML감사77patch,수집기중간664는미재검증;전체1000/train600·대표성 미달 | stable collection snapshot 시각/버전 선정 |
| ML-03 | §4.1 | 내부 마스터 | LCLUC 독립 평가 | ml_pipeline/분야전문가 TBD | independent expert 참조·라벨서명·중복/공간검사·OA/mIoU/분해 평가 | PARTIAL / BLOCKED | 실제 독립 자료 없음;자기진술 검증만으로 출처독립성 공인 불가;지역/연도별 평가 미구현 | 제공기관·평가기준·최소 성능·reviewer 승인 권한 확정 |
| ML-04 | §4.1 | 내부 마스터 | 학습 재현/비교 | ml_pipeline | actual config/checkpoint/optimizer/RNG·중단/재개 동일성·baseline 비교 | PARTIAL | 새학습 설정/재개 구현;과거checkpoint설정소급복원금지;신규실학습·기존모델비교 없음 | 충분자료 통과 후 비교프로토콜 동결 |
| ML-05 | §4.2 | 내부 마스터 | Recalibration | 외부기관 TBD/ml_pipeline adapter | parameter/forcing/initial&boundary버전·보정/독립기간 분리·민감도/물리성 시험 | NOT_IMPLEMENTED | 실제 물리모델/관측·parameter run 없음 | 보정 모델·전문가·유형별 metric 계약 필요;OA/mIoU 강제 금지 |
| ML-06 | §4.3 | 내부 마스터/확인된v0.2내부제안 | Update Ticket | root/ml_pipeline | schema·proposal-only생성·승인/감사·자동실행금지 시험 | SOURCE_FOUND / NOT_IMPLEMENTED | 원문update-ticket.schema/OpenAPI존재;참조server와현행플랫폼endpoint미구현 | route/store ownership·실제enum/policy결합·RFC |
| AG-01 | §5.1 | 내부 마스터 | 6-Agent 경계 | root/외부5기관 TBD | 등록·capability/준비도 조회,외부5 결과미생성 | LOCAL_PROPOSAL_IMPLEMENTED | 6개manifest·상세/기능조회구현;LCLUC BLOCKED/DRAFT,외부5 NOT_IMPLEMENTED;동적기관등록/실제외부실행기없음 | 기관R&R/납품승인은미확정TBD유지 |
| AG-02 | §5.2 | 내부 마스터/확인된v0.2내부제안 | Agent API/Schema | root | 제공원문OpenAPI·JSONSchema·호환 fixture | LOCAL_PROPOSAL_IMPLEMENTED / NOT_APPROVED | gmais_api.py+main router연결,strictschema시험8PASS;전체성공실행/기관승인미완료 | 버전별확장RFC·컨소시엄승인별도 |
| AG-03 | §5.2 | 내부 마스터 | Job API | root | 202+Location·Idempotency-Key·401/403/409·cancel/timeout시험 | PARTIAL: 영속BLOCKED Job/멱등성/trace/조회구현 | 409+Location+표준status,같은키재생/다른본문충돌,무결과확인;승인된202성공실행/DAG실행/timeout/retry확장남음 | 실행/취소·기관인증정책협의 |
| AG-06 | 관련 §6 | 내부 마스터/로컬RFC | Workflow Plan | root | upstream Workflow Plan Schema·노드/의존성/순환·위상순서·무실행 시험 | LOCAL_PLAN_ONLY_EXTENSION / 7TESTS_PASS | /v1/workflows/plan 구현;항상BLOCKED/실행false/Job·Result미생성. 실제DAG실행·스케줄링·timeout/retry/cancel·과학결과발행미완료 | upstream OpenAPI에없는내부RFC;기관승인/실행계약별도 |
| AG-04 | §5.2 | 내부 마스터 | Readiness 분리 | root/ml_pipeline | runtime/dataset/scientific/deployment/integration 각각출력·차단 | LOCAL_PROPOSAL_IMPLEMENTED | companion axes runtime/dataset/science/deployment/contract구현;contract PROPOSED,과학·배포차단유지 | Agent READY != Model APPROVED;기관·운영적합성별도 |
| AG-05 | §5.3 | 내부 마스터 | Delivery Package | 외부기관 TBD/root | 실제manifest/I/O/runtime/security/validation/operations자료·contract pack | NOT_IMPLEMENTED | 공통납품구조·유형별필수/예외없음 | 외부API/수치형조건부필드협의 |
| OP-01 | §7.1 | 내부 마스터 | Registry 분리 | root | Dataset/Run/Model/Agent/Deployment/Result 고정id/version/hash상호참조 | PARTIAL: 기존SQLite+6 Agent manifests+gmais_jobs/idempotency | 유형별run/calibration/service image/deployment registry·과학결과발행/workflow전체crossref미완료 | 비파괴schema migration·기존TitleCase mapping |
| OP-02 | §7.1 | 내부 마스터 | Approval | root/검토기관 TBD | Draft차단·실제전문가증거/역할/서명·checkpoint변조거부 | PARTIAL / APPROVAL BLOCKED | Draft게이트·해시·평가경합시험구현;역할/RBAC/서명·운영UAT없음 | 승인권한/기관별역할·최소평가기준필요 |
| OP-03 | §7.2 | 내부 마스터 | Monitoring/Drift | root/devops | 지연/에러/CPU/GPU/저장/분포·drift→검토ticket만생성 | NOT_IMPLEMENTED 운영통합 | 로컬job/실험분포는있으나통합계측·drift/ticket없음 | 운영환경/관측도구·경보정책확정 |
| OP-04 | §7.3 | 내부 마스터 | Rollback | root/devops | 승인된이전artifact/config/DB호환·staging복구smoke | PARTIAL: local배포이력 | 인프라실배포·호환migration·실rollback시험없음 | staging/production환경·접근권한·검수주체TBD |

## 충돌·보존 원칙

- 현행 모델 상태는 `Draft/Validated/Approved/Deployed/Retired`; 실제 v0.2 Agent Schema의 uppercase enum과 버전 adapter로 매핑해야 한다. 내부제안 Schema의 존재가 컨소시엄승인은 아니며 기존 DB를 소급 변경하지 않는다.
- 현행 `deploy()`는 로컬 추론용 checkpoint 전제다. 물리모델 파라미터·외부 API 릴리스에 이를 그대로 적용하지 않는다.
- 실제 모델 하나는 Draft/independent=false이며 마지막 실제77patch MLgate도 blocked다. 수집기 664 중간 계수를 정식 gate 통과로 취급하지 않는다.
- 학습 중단 상태는 완료 모델 등록 대상이 아니다. 시험 PASS는 독립 과학검증·운영승인의 대체 증거가 아니다.
- main/API/DB/공통스키마는 root 협의 전 수정하지 않는다. 새로운 5개 모델의 과학결과·수치·레이어를 생성하지 않는다.

## G0 조사 명령·관측 증거

`rg --files` 파일명 검색, 마스터 §4/5/7 열람, `lifecycle.py`, `main.py`, `store.py`, `experiment_registry.py` 및 ML 코드를 읽었다. 실제 카탈로그는 SQLite `mode=ro`로 조회했고 원본·수집 원장·checkpoint를 변경하지 않았다. 2026-10-16 06:17:35 UTC snapshot에 master/구현코드 SHA와 현재 registry/수집기 중간집계/이전readiness stale 상태를 저장했다. 이 Gate에는 코드 변경이 없으며 기존 구현 계약 시험 결과는 문서08과 root 통합 시험 문서로 연결한다.

후속 발견: 초기 backend-only SOURCE_MISSING 판단을 정정한다. root가 공유 드라이브에서 실제 패키지를 발견해 `contracts/upstream/GMAIS-v0.2/`로 반입했다. 원문 Agent/Result/Update Ticket Schema·model-type-profiles·policy/참조server를 읽었고 `package_manifest.json` 34개 SHA를 검증했다. 새 발견 근거는 `data/audits/gmais-ml-contract-review.json`에 기록하며 초기 관측 JSON을 소급 변경하지 않는다. policy 원문 시험 4개 PASS. 실제 플랫폼 공통 API 호환, 독립 과학검증과 BIG 승인 성과는 아니다.

추가 gap: 참조 model-type-profiles에는 inference_only 개별 SOP가 없지만 Schema/policies에는 유형이 존재한다. update-ticket OpenAPI는 있으나 reference server endpoint는 없다. Agent top-level additionalProperties=false이므로 로컬 구현은 5축 readiness 증거를 별도API/companion으로 분리했다. Result validation_level과 status의 의미를 보존하며 원문 Schema에 없는 운영 승인 전이를 스키마 검증만으로 보장하지 않는다.

## 로컬 제안 API 어댑터 구현 후속

root가 `backend/app/gmais_api.py`와 main router 연결을 구현하고 host에서 `tests/test_gmais_api.py` 8개 strict Schema 시험 PASS를 확인했다. 여섯 Agent manifest와 별도 5축 readiness companion, trace를 포함한 영속 BLOCKED Job, 409+Location, 멱등 재생/키 충돌, job/status/results 조회와 가짜 결과 미생성을 검증했다. 원문 reference adapter의 메모리 mock과 달리 로컬 플랫폼 Store에 차단 Job을 남긴다.

이는 내부 검토본 v0.2의 제한적 로컬 호환 구현이다. 실제 workflow 실행, update-ticket, 기관별 RBAC/서명, 실제 성공 과학결과, Production 배포·rollback 및 컨소시엄·BIG 승인은 남은 gap이다. 데이터/독립평가 부족 차단을 해제하지 않았다. 이번 후속은 두 문서만 수정하며 코드·시험·데이터 수집 변경은 없다.

후속 `/v1/workflows/plan`은 로컬 plan-only RFC로 구현됐다. root host에서 `tests/test_gmais_workflow_extension.py` 7개 PASS: upstream Schema 검사, 중복 ID·미지/자기 의존성·cycle 거부, 미등록 Agent/Capability 차단, 안정적 DAG 위상 순서와 Job/Result 미생성을 확인했다. `PLAN_ONLY/BLOCKED`, `execution_started:false`를 유지하며 upstream OpenAPI 미포함·INTERNAL_REVIEW 상태를 명시한다. 계획 검사는 실제 과학 실행이나 운영 승인 증거가 아니다.
