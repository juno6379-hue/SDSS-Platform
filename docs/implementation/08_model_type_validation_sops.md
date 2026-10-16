# Model Type별 검증 SOP와 준비도 대조

검토일 2026-10-16. 작업자 `ml_pipeline`; 소유권과 공동 파일 변경 규칙은 `workstream_ownership.md`를 따른다. 본 문서는 새 마스터 §4/§5/§7을 현행 구현과 대조한 G0/G2 초안이다. API·DB·공통 Schema를 수정하거나 과학적 승인 상태를 생성하지 않았다. `backend/app/main.py`는 root와 협의하기 전까지 읽기 전용이다.

## 1. 출처 및 확인 범위

| 자료 | 발견 결과 | 적용 한계 |
|---|---|---|
| `GreenBlue_CODEX_Master_Prompt_GMAIS_Integrated_Platform_v1.0.md` | 실제 파일 열람: §4/5/7 및 관련 §0/6/12/13/14 | GreenBlue 내부 개발 지시 초안; 계약 확정 규격이나 TECH 원문 증거와 구분 |
| GMAIS v0.2 실행 패키지 | **FOUND_INTERNAL_PROPOSAL_NOT_APPROVED** | root가 공유 드라이브에서 확인하여 `contracts/upstream/GMAIS-v0.2/`에 vendoring. 실제 agent/result/update-ticket Schema·model-type-profiles·policy/adapter 열람. 컨소시엄·BIG 승인 규격 아님 |
| 현행 LCLUC ML/Readiness | `backend/app/ml/{dataset,raster,normalization,readiness,service,network}.py`, `scripts/run_experiment.py` | 실제 구현 확인; 다른 5개 과학모델 구현 증거가 아님 |
| 현행 Registry/API | `backend/app/{store,lifecycle,main,experiment_registry,gmais_api}.py` | 기존 SQLite/스레드 큐를 보존하고 GMAIS 내부 제안의 제한적 로컬 어댑터 연결. 실제 Kubernetes 운영 검증 아님 |
| 실자료·등록 모델 현황 | `data/audits/gmais-ml-current-inventory.json` | 2026-10-16 06:17:35 UTC 고정 관측. 수집 중 보고서의 후속 변경은 이 snapshot에 소급 반영하지 않음 |

초기 backend-only 검색에서는 SOURCE_MISSING이었으나 root가 실제 패키지를 발견·반입하여 그 판단을 정정했다. 초기 관측 JSON은 삭제하지 않고 후속 `data/audits/gmais-ml-contract-review.json`으로 출처 발견 상태를 갱신한다. 원문 Schema의 enum/필드는 확인됐지만 현행 플랫폼 호환 완료나 컨소시엄 승인으로 간주하지 않는다. `package_manifest.json`의 34개 SHA를 재검증했으며, 정확한 model-type-profiles 경로는 `templates/model-type-profiles.md`다.

## 2. 현행 상태를 분리해서 해석

| 상태 축 | 현재 증거 | 현재 해석/차단 |
|---|---|---|
| runtime readiness | `runtime_status()`의 torch/CPU/CUDA 탐지; CPU 학습 및 checkpoint 재개 시험 | 로컬 CPU 실행 가능. 실제 Kubernetes/GPU/기관 인프라 검증과 별개 |
| dataset readiness | `readiness.assess()`와 `validate_prepared_training()` | 1,000~3,000 실제 패치, fixed 4/1/1, 600/100/100 이상, 6주·기간·밴드·제품 보정·클래스·누출 gate. 현재 BLOCKED |
| scientific validation | `evaluate_model()`의 전문가 참조/검토자/분류체계 서명/중복·공간 검사 | 독립성은 사용자 출처 진술+중복 검사이며 공인 인증이 아님. 실제 독립 전문가 자료 미확보 |
| deployment approval | `lifecycle.transition/deploy`, API checkpoint/evaluation hash 검증 | 기존 실제 모델 Draft/독립 평가 false. Production 실행 불가 |
| integration compliance | 기존 `/api/*`와 `gmais_api.py`의 `/v1/agents/*`·차단 Job 어댑터, strict Schema 시험 8개 | 로컬 제안 계약 세로 경로 구현. companion contract 축은 PROPOSED이며 기관 승인·전체 workflow·Production 적합성을 뜻하지 않음 |

직전 **실제 ML 재감사**는 초기 6배치 물리80/적격77, train45/val16/test16, 5/36조합, blockers16이다. `training-readiness.json`의 입력 manifest는 이후 수집으로 변경되어 현행 API는 stale로 취급해야 한다. 06:17:35 UTC 수집기 중간 집계는 물리832/적격664, train353/val151/test160이며 **정식 ML 재검증 수치가 아니다**. 수집기 자체 `candidate_target_met=false`이다. train600/전체1000 미달, bare 클래스 비율·포함 패치 부족, 일부 주 공간 대표성 미달이 남아 있다.

실제 registry를 읽기 전용 SQL로 확인한 기존 모델은 `baseline2021_cpu_v1_model`, Draft, independent_evaluation=false, checkpoint SHA `ad74f5cf5ab4bfd42bffd94b2fa399bf28f3527bc8e9f424d6a9d5339b12cd6c` 하나다. 과거 실제 RGB 3패치·3epoch 기능시험이며 산림/도시 6년 모델 성능으로 주장하지 않는다. checkpoint와 원장·원본을 변경하지 않았다.

## 3. 유형별 SOP와 실제 구현 범위

| model_type 후보 | 갱신 구분 후보 | 필수 검증 SOP | 현행 구현/한계 |
|---|---|---|---|
| trainable_ml | RETRAINING | QC→고정 입력/코드/환경/분할→준비도→train→validation 선택→독립 test/기존모델 비교→model card→전문가 승인→staging/rollback→production | LCLUC dataset/train/infer/변화분석과 Draft gate 구현. 데이터 부족으로 신규 실학습 BLOCKED. 독립 관측/전문가 승인/staging rollback/지역·연도별 분해 평가 미완료 |
| calibrated_physical | RECALIBRATION | 관측/forcing QC→기준모델 재현→보정 파라미터·목적함수·보정기간 고정→재보정→별도 시공간 독립 검증→물리 일관성·민감도·불확실성→calibration card/전문가 승인 | NOT_IMPLEMENTED. 파라미터/forcing/초기·경계조건 Registry와 보정 실행기 없음. ML OA/mIoU로 일괄 승인 금지 |
| statistical | RETRAINING 또는 CONFIG_UPDATE | specification/sample freeze→재추정→독립 관측·백테스트·편향→파라미터 버전/전문가 검토 | NOT_IMPLEMENTED. 실제 `reference_adapter/policies.py` 허용값 확인; 모델별 기준/관측/담당기관 TBD |
| inference_only | 검증된 아티팩트 교체 | 실행파일·가중치/런타임 고정→유효/오류 test vectors→출력 버전·단위·일관성→독립 근거/승인→rollback | NOT_IMPLEMENTED 공통 유형. 기존 LCLUC infer 함수 존재와 공통 delivery 지원은 다름 |
| external_service | EXTERNAL_RELEASE | 제공자 릴리스/SLA/라이선스/접근권한→TLS/auth/timeout/가용성→실서비스 계약시험→승인된 버전 승격 | NOT_CONFIGURED/NOT_IMPLEMENTED. 실제 기관 API·서비스·자격증명 제공 필요 |

보정(calibration) 자료와 독립 검증 자료는 분리해야 한다. 제품 XML의 위성 DN 반사도 보정 검사는 물리 수치모델 재보정 SOP의 구현 증거가 아니다. 모델별 역할 기관은 TBD이며 내부 업무 분장을 계약상 R&R로 확정하지 않는다.

### LCLUC 세부 SOP

1. 실제 원본/라벨/외부 품질/공식 보정 XML을 해시로 연결한다. 20m→10m bilinear는 새로운 10m 관측 생성으로 표현하지 않는다. 정합 stack은 원본 DN 기반 float32이며 최종 reflectance 적용과 구분한다.
2. 6개 주와 원본 scene/동일 공간의 전연차를 고정 분할한다. 같은 공간·같은 연도 반복 샘플, 다른 분할의 중첩/동일 scene/해시를 차단한다.
3. 충분성 1,000~3,000, train600/val100/test100 이상과 주요 클래스별 비율0.5%/포함패치5개/단일클래스90% 이하 등 명시적 개발 대표성 정책을 검사한다. 이는 정확도 인수 기준이 아니다.
4. train-only 가중치와 실제 optimizer/loss/lr/batch/seed/환경·입력서명을 저장한다. CPU 최대20epoch/호출1800초, 마지막 완료 epoch의 optimizer/RNG를 원자 저장해 재개한다. 미완성 epoch/test는 완료 성과로 게시하지 않는다.
5. validation으로 best 선택 후 실제 test 혼동행렬과 OA/mIoU/F1/IoU/recall/support/예측비율을 계산한다. 단일클래스 붕괴·과도한 지배율은 실험 결과 거부 상태로 기록한다.
6. Esri rangeland 분류명/서명을 보존하고 과거 WC grass와 혼동하지 않는다. 독립 현장자료 없이 생성한 값은 참조제품 **일치도**다. 현장 정확도라고 부르지 않는다.
7. 완료 report/weights/dataset 해시를 검증해 새 모델은 Draft로 등록한다. 실제 독립 참조·분류체계·기간/지역 분리·검토 근거가 없으면 Validated/Approved/Deployed 전이를 차단한다.

## 4. 현행 API와 공통 계약의 차이

| 현재 구현 | 마스터의 공통 계약 후보 | 결론 |
|---|---|---|
| GET `/api/health` + `/healthz`, `/readyz` | Health/runtime readiness | 로컬 UP/runtime-only와 scientific readiness를 분리. UP를 과학모델 준비·운영 승인으로 표시하지 않음 |
| GET `/api/models/{id}/readiness`, `/api/data/collection-status` + `/v1/agents/{id}/readiness` | 5축 readiness companion | runtime/dataset/science/deployment/contract 축을 manifest 밖에서 출력. LCLUC dataset/science/deployment BLOCKED, contract PROPOSED; 외부5개 NOT_IMPLEMENTED |
| 기존 학습·추론 API + POST `/v1/agents/{id}/jobs`, GET `/v1/jobs/{id}`, `/results` | governed Job contract | 현재 GMAIS 요청은 차단 작업을 SQLite에 저장하고 409+Location+trace/표준 status 반환. 동일 Idempotency-Key 재생/다른 본문 충돌 검증. 승인된 성공 실행·DAG 실행/timeout/재시도·실결과 발행 확장은 남음 |
| POST `/v1/workflows/plan` | 로컬 `greenblue.workflow-plan.rfc1` 확장 | upstream Workflow Plan Schema와 노드·의존성·순환·Agent/Capability를 검사하고 안정적인 위상 순서를 제공. 항상 PLAN_ONLY/BLOCKED, execution_started=false이며 Job/Result를 생성하지 않음. upstream OpenAPI에 없는 내부 검토 RFC |
| `/api/models/{id}/transition`, `/evaluate`, `/deploy` | 유형별 Model Registry + Approval + Deployment Registry | 기존 TitleCase 상태를 보존하고 공통 uppercase 변환은 버전 adapter 후보. 역할별 승인·서명·실제 배포 registry 미구현 |
| `/api/models/register-experiment` | 공통 Training/Calibration Run Registry | 실제 완료 학습만 Draft 등록. 물리 보정/외부 서비스에 checkpoint.pt를 강제하지 않는 분기 필요 |
| 없음 | POST `/v1/models/{id}/update-tickets` | 실제 원문 Schema 확보; 플랫폼에서는 미구현. proposal-only 티켓부터 연결하며 생성 자체가 학습/재보정/배포를 실행하면 안 됨 |

공통 API/enum/DB 변경 전 root와 경로·버전·이행안을 협의한다. 현재 로컬 endpoint와 레코드를 삭제·이름 변경하지 않는다. 원문 반입만으로 플랫폼 명세 준수나 기관 승인을 표기하지 않는다.

### 실제 v0.2 원문에서 확인한 필드와 구현 주의점

- Agent Schema는 `schema_version=0.2.0`, agent_id/version/provider/model_type/execution_mode/capabilities/readiness/deployment_profile을 필수로 요구하고 top-level additionalProperties=false다. `model_approval_status`는 별도 optional enum이다. 5축 세부 readiness를 manifest top-level에 임의 추가하면 원문 Schema 위반이므로 readiness API·버전 있는 companion evidence에서 연결해야 한다.
- Result Schema는 status `SCIENTIFIC_VALIDATED/DEVELOPMENT_ONLY/MOCK_ONLY`와 validation_level `CONTRACT_ONLY/PSEUDO_LABEL_AGREEMENT/INDEPENDENT_SCIENTIFIC`를 각각 구분한다. job_id/agent_id/input_refs/output_assets/spatial/validation/provenance가 필수이며 provenance에는 trace_id/processing_version이 필요하다. model_ref는 Schema상 optional이나 실제 모델 결과에는 고정 id/version/sha256을 연결해야 한다.
- Update Ticket은 ticket_id/model_ref/update_type/trigger/proposed_inputs/validation_plan/approval_state가 필수다. trigger는 DRIFT/NEW_DATA/BUG/SCIENTIFIC_REVIEW/PERFORMANCE_DEGRADATION, approval_state는 PROPOSED/DATA_READY/VALIDATED/APPROVED/REJECTED/DEPLOYED다. validation_plan의 independent_test_ref/metrics/acceptance_threshold_ref는 필수이며 빈 가짜 참조로 통과시키지 않는다.
- 실제 update 허용 조합은 trainable_ml·statistical=RETRAINING/CONFIG_UPDATE, calibrated_physical=RECALIBRATION/CONFIG_UPDATE, inference_only·external_service=EXTERNAL_RELEASE/CONFIG_UPDATE다. 일반 티켓 Schema 자체에 유형별 if/then 제약이 없으므로 policy 검사도 필요하다.
- `model-type-profiles.md`에는 inference_only 개별 SOP가 빠져 있으나 Agent Schema와 policies에는 존재한다. 공통 과학 인수 기준의 확정된 누락이 아니라 내부 제안 문서 보완/RFC 항목으로 남긴다.
- reference_adapter는 MOCK/contract only이며 `/readyz`의 UP는 과학모델 준비 상태가 아니다. update-ticket endpoint는 OpenAPI에 있으나 참조 server에 구현되지 않았다. 참조 server의 취소는 409 반환이고 job 저장은 메모리다. 그대로 운영 플랫폼 구현 완료로 재사용하면 안 된다.

## 5. MLOps 증거와 미구현 사항

현재 SQLite는 datasets/models/jobs/analyses와 로컬 제안 어댑터의 gmais_jobs/gmais_idempotency를 공통 key-value records 테이블에 저장한다. 여섯 manifest 조회 중 LCLUC만 실제 구현 경로와 연결되며 현재 BLOCKED/DRAFT이고, 외부 다섯 개는 NOT_IMPLEMENTED다. 차단 요청에도 고정 job_id·trace·요청 근거를 영속화한다. 결과 endpoint는 차단 작업에 409를 반환하며 가짜 result manifest를 생성하지 않는다. 동일 멱등키 재생은 같은 Job/Location을 반환하고 변경된 본문은 SCHEMA_MISMATCH로 거부한다.

실험 Registry는 report/학습보고서/manifest/checkpoint hash 일치와 완료 여부를 검사하고 Draft를 강제한다. 기존 API는 queued 실행 직전 Deployed와 checkpoint를 재검사하고, 평가 중 상태 전이/중복 평가를 차단한다. 평가 완료 시 모델·checkpoint가 바뀌면 증거 반영을 거부한다. 서버 재시작 시 미완료 작업을 성공으로 복구하지 않는다.

남은 gap: 동적 기관 Agent 등록·납품 검수, 유형별 Training/Calibration Run, parameter-set/forcing Registry, OCI digest/namespace Deployment Registry, 실제 과학 Result 발행과 workflow 전체 trace/cross-reference, 역할 분리·서명, 운영 관측·drift/update-ticket, 실제 staging/rollback smoke test. 현행 여섯 manifest 목록·차단 Job·결과 조회 경로는 이 항목들의 전체 구현을 대신하지 않는다. 과거 배포를 Approved로 되돌리는 로컬 이력은 인프라·DB 호환성 rollback 시험의 증거가 아니다. 선택적 단일 Bearer token은 기관별 RBAC 구현 증거가 아니다.

## 6. 검증 명령과 인수 구분

기존 ML 시험에는 실제값을 흉내 내는 합성 fixture가 있으나 실제 패치 목표에 포함하지 않는다. 부모 정상 host에서 pipeline15개 PASS36.984초, 추가 Esri2개 PASS10.207초, 최신 로컬 readiness15개 PASS9.723초는 구현 계약 시험이다. root가 진행하는 전체 회귀 결과는 별도 `09_integration_test_and_evidence.md`에 통합해야 하며 이 문서가 새 전체 PASS를 선언하지 않는다.

```powershell
python -m unittest discover -s tests -p test_ml_readiness.py -v
python -m unittest discover -s tests -p test_ml_pipeline.py -v
python scripts/run_experiment.py --manifest data/first-group-training-esri-v1/annual-window-report.json --plan data/first-group/experiment-esri-v003-2020-2025.json
```

마지막 명령은 stable manifest 이후의 QA이며 `--execute`가 없다. 수집 중 snapshot QA는 별도 output에 쓰고 API의 기존 readiness와 혼동하지 않는다. 독립 과학검증은 실제 라벨 제공과 분야별 기준 승인 후 수행하며 현재 BLOCKED다. 실제 반입 패키지에서 `python -m unittest discover -s tests -p test_policies.py -v`를 실행하여 4개 PASS(보고시간0.000초)를 확인했다. 이는 내부 참조 policy 계약시험이며 실제 과학모델·플랫폼 API·운영 검증과 다르다.

후속 root host 실행에서 `python -m unittest discover -s tests -p test_gmais_api.py -v`의 엄격 Schema/로컬 API 시험 8개 PASS가 확인됐다. 시험은 임시 Store로 실제 카탈로그와 격리한다. 검증 범위는 여섯 manifest·별도 readiness 축·차단 Job의 영속/trace/멱등성·잘못된 입력/키 거부·결과 미생성·외부 Agent 미구현 상태다. 성공 과학 실행이나 운영·기관 승인을 시험한 결과가 아니다. 이 문서 갱신에서는 코드·시험·수집물을 수정하지 않았다.

추가 root host 실행에서 `python -m unittest discover -s tests -p test_gmais_workflow_extension.py -v` 7개 PASS를 확인했다. 로컬 plan-only RFC는 이제 구현됐으며, 유효 계획 차단·Job/Result 미생성, 잘못된 Schema·중복 ID·미지/자기 의존성·순환 거부, 미등록 Agent/Capability 실행 차단과 입력 순서에 무관한 위상 순서를 검증했다. 실제 DAG 실행·스케줄링·timeout/retry/cancel·고정 과학결과 발행은 여전히 gap이며 기관 승인된 공통 계약 구현으로 확대 해석하지 않는다.

## 7. 다음 협의 및 구현 우선순위

1. 반입된 v0.2 내부 제안과 현행 플랫폼의 호환성·참조 구현 누락을 검토하고 표준 수정은 RFC로 기록한다. 컨소시엄·BIG 승인 여부는 별도 결정 사항이다.
2. 구현된 root 소유 로컬 경로/5축 readiness·멱등 차단 Job을 보존하며 update-ticket proposal 저장 및 실행 금지 계약을 추가 협의.
3. model_type별 조건부 delivery/검증근거·approval 입력 계약. 외부5개는 NOT_IMPLEMENTED/owner TBD로 계약시험만 가능하게 한다.
4. 이미 구현한 차단 Job trace/idempotency를 기반으로 실제 승인 실행·workflow·timeout/retry/cancel·고정 결과 참조를 기존 LCLUC 서비스 위에 비파괴적으로 확장한다.
5. 실제 적격 데이터와 분리 검증이 충족된 경우에만 LCLUC 새 실험을 진행한다. 운영 승인·배포는 추가 독립 전문가/인프라 검증이 필요하다.
