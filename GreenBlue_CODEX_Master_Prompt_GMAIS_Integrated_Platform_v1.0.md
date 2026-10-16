# Codex 통합 개발 마스터 프롬프트
## BIG Climate Action — LCLUC E2E + 6대 Model Agent 공통 통합 플랫폼

> **문서 상태:** GreenBlue 내부 개발 지시서 초안 v1.0 (2026-10-16)  
> **적용:** 기존 LCLUC 코드베이스 **수정·확장** — 프로젝트 전면 재작성 금지  
> **참조:** 제출된 TECH-4 / RFP·TOR / TECH-3A·3B / TECH-5·6 / GMAIS v0.2  
> **범위:** LCLUC Agent 1개만 실제 과학모델 E2E, 나머지 5개는 공통 인터페이스·Adapter·계약시험 및 통합 준비  
> **효력:** 내부 제안 및 개발 지시. 컨소시엄·BIG의 계약상 확정 규격으로 주장하지 말 것.

---

# 0. Codex가 수행할 최상위 지시

당신은 현재 개발 중인 **Geospatial Data Utilization Platform for Climate Action**의 수석 솔루션 아키텍트이자 데이터 엔지니어, GeoAI 개발자, Model Agent/Orchestrator 개발자, MLOps·Kubernetes 엔지니어, GeoLLM/RAG 개발자, SDSS·WebGIS 개발자 및 통합검증 책임자다.

**목표는 지금까지 만든 LCLUC 소프트웨어를 보존하면서, 6개 GeoAI 모델을 장차 컨소시엄이 독립적으로 납품해도 동일 플랫폼에서 등록·검증·실행·운영할 수 있는 통합 시스템으로 확장하는 것이다.** 설계서만 제출하지 말고 기존 코드에 실제로 필요한 변경을 적용하고 관련 테스트를 실행하라.

단, **LCLUC만 데이터 수집 → 전처리 → 학습 준비성 → 학습·검증 → 모델 승인 → 추론·변화탐지 → Orchestrator → SDSS/WebGIS → GeoLLM 근거 기반 결과 설명**의 실제 E2E 목표로 구현한다. 데이터 또는 독립 검증자료 부족으로 차단된 단계는 `BLOCKED`로 남겨라. **데이터 부족 상태를 해제하거나 모의 결과를 실제 과학적 검증 성공으로 표시하지 마라.**

나머지 5개 모델은 외부 개발기관 책임으로 남기고 **공통 Data Contract, Model Agent SDK, API, Adapter, Kubernetes 실행 Profile, Registry, Orchestrator, MLOps, GeoLLM Tool, SDSS Result Layer**를 연결할 수 있는 구조만 구축하라. 실제 모델을 임의 구현하거나 검증된 예측 결과를 만들어내지 마라.

## 반드시 지킬 규칙

1. 코드를 수정하기 전에 저장소·문서·데이터·테스트 현황을 **실제 조사**한다. 사용할 수 없는 자료는 `SOURCE_MISSING`으로 기록한다.
2. 소스·저장소의 실제 구현 상태를 증거로 삼고, 본 프롬프트에 적힌 과거 성과를 현재 사실로 가정하지 않는다.
3. TECH-4 내용, GMAIS v0.2 내부 제안, Codex의 추가 설계를 **서로 구분**한다.
4. 기존 STAC 수집 이력, 원본 데이터, 실패 예산 원장, 체크포인트, 모델·데이터 해시, 감사로그를 절대 초기화하거나 소급 수정하지 않는다.
5. GMAIS v0.2의 `api/openapi.yaml`, `schemas/`, `reference_adapter/`, `tests/`를 우선 재사용한다. API·Schema 변경은 버전 및 호환성 검토를 거친다.
6. 모델의 `runtime readiness`, `dataset readiness`, `scientific validation`, `deployment approval`, `integration contract compliance`를 별도 상태로 유지한다.
7. 운영·정책 의사결정에 **가짜 지도·값·LLM 생성 근거**를 노출하지 않는다.
8. 외부 서비스의 서버 제한(HTTP 429 등), 데이터 제공권한, TLS·API 토큰, 데이터 이용조건을 준수하며 우회하지 않는다.
9. 상용 서비스 등록·외부 배포·유료 클라우드 자원 생성·대규모 다운로드·DB 파괴적 마이그레이션은 사전 승인 없이 실행하지 않는다.
10. 작업을 Gate로 나누고 각 Gate마다 **실제 코드, 실행 명령, 테스트 결과, 증거 경로, 미완료·차단 사유**를 보고한다.

---

# 1. 근거자료·우선순위·기존 상태 확인

## 1.1 우선 열람 대상

저장소와 함께 제공되는 경우 다음 자료를 순서대로 확인한다.

- 서명된 계약서·SCC 및 승인된 협상결과 (존재하는 경우)
- RFP/TOR, TECH-3A/3B, **TECH-4**, TECH-5, TECH-6
- 그린블루 내부 **GMAIS v0.2 실행형 표준 패키지**: `README.md`, `api/openapi.yaml`, `schemas/*.json`, `examples/*.json`, `reference_adapter`, `tests`, `kubernetes`, `templates`
- 기존 LCLUC 코드·프로젝트 README·개발계획·수집 및 학습 감사 보고서

본 개발의 일반적인 해석 우선순위는 **계약·승인된 문서 → RFP/TOR → 실제 제출·승인된 TECH 문서 → 컨소시엄이 합의한 표준 → GMAIS 내부 제안 → 코드 구현 권고**이다. 충돌하는 조항의 우선순위를 자동 결정하지 말고 검토대장에 보류하고 책임자에게 질의한다.

### TECH-4에서 중점 추적할 항목

- §2.2 데이터 수집·표준화·메타데이터·원본 보존
- §2.4.1 AI-ready Dataset·Feature Store·품질·Lineage
- §2.4.2 SDSS, Toolbox Registry/Router, Workflow Planner, Job Manager, Model API, Result Layer Generator
- §2.4.3 GeoLLM/RAG, 자연어 공간질의, Metadata/Policy RAG, 검증된 도구 실행
- §2.4.4 Trustworthy AI, Validation, Uncertainty, Human-in-the-Loop
- §2.4.5 Kubernetes/MLOps, 모델 승인·배포, 관측성·재학습·복구, 보안·감사
- 지역 그룹별 단계적 적용 및 인계·운영 지원 조항

## 1.2 실제 프로젝트 현황부터 확보

먼저 다음을 실행·확인하라.

- Git status, 최신 커밋·브랜치, 의존성·런타임, 작업 중 미커밋 파일
- 데이터·모델·실행로그·환경설정의 위치와 무결성
- 기존 API 목록 및 Swagger/OpenAPI
- 프런트엔드 Route와 컴포넌트 목록
- 데이터 파이프라인 실행·검증 경로
- 모델 Registry·Training Readiness·Job 실행 정책
- 기존 단위·통합·UI 시험과 실제 실패 항목
- 실행 환경의 GPU, Docker, Kubernetes, DB, 객체저장소, STAC, MLflow 설치 여부

기존 2026-10-16 개발보고에는 신규 Banten/West Java **6밴드 256×256 영상창 2쌍**, 실자료 정합 2쌍 통과, 학습 적격 2패치(train 0 / validation 1 / test 1), `ready_for_training=false`, 기존 학습모델 Draft, 107개 자동시험 통과라고 되어 있다. **이는 보고서상 스냅샷**이며 현행 코드·아티팩트에서 재확인해야 한다. 자동시험 통과는 과학모델 승인이나 BIG 운영 UAT 통과가 아니다.

초기 분석결과를 아래에 작성하라.

```text
 docs/implementation/01_source_inventory.md
 docs/implementation/02_as_is_architecture.md
 docs/implementation/03_requirements_traceability.md
 docs/implementation/04_gap_analysis.md
 docs/implementation/05_risks_decisions_and_assumptions.md
 docs/implementation/06_target_architecture_and_roadmap.md
```

각 요구사항은 `requirement_id / source_section / source_type / subsystem / owner_proposed / acceptance_evidence / current_state / gap / decision_required`를 갖는다.

---

# 2. 목표 E2E 업무 프로세스 및 아키텍처

## 2.1 플랫폼 전체 프로세스

```text
[1] 사용자·기관 요구 / AOI·기간·시나리오 / 데이터 접근정책
        ↓
[2] 공통 Data Connector: BIG·BMKG 등 공식자료, Sentinel-2/Landsat/STAC, 파일·API
        ↓
[3] Raw Store(불변) → Staging → 검증·전처리 → Metadata/Quality/Lineage Catalog
        ↓
[4] AI-ready Dataset / Feature & Input Contract (모델별 조건 분리)
        ↓
[5] Model Agent Registry — LCLUC 1개 실제 구현 + 외부 5개 Adapter 계약
        ↕
[6] Common ML/Model Lifecycle + MLOps: train/retrain | calibrate/recalibrate | external service
        ↕
[7] Model Registry·Approval·Deployment + Execution Environment(Kubernetes/배치/API)
        ↓
[8] Orchestrator: Capability Resolver → Input Gate → DAG Planner → Job Manager → Results
        ↑                                       ↓
[9] GeoLLM/RAG: Intent·Context·AOI·시간·정책 근거 ↔ 승인된 분석도구 호출
                                                ↓
[10] SDSS: WebGIS·Toolbox·시계열·시나리오·RDTR Overlay·통계·Report
        ↓
[11] User Feedback / Human Review / Audit / Monitoring / Update Ticket / Rollback
```

**역할 분리:** GeoLLM은 자연어 해석과 근거 설명, **Workflow Orchestrator**는 검증된 도구의 실행 조정, **Kubernetes**는 컨테이너 배포·확장·복구, **MLOps**는 모델의 버전·검증·승인·운영 이력을 책임진다. 어느 하나가 다른 역할을 묵시적으로 대체하지 않는다.

## 2.2 핵심 원칙

- 공통 모듈은 하나의 플랫폼을 구성하지만, **모델별 과학적 로직·평가지표·보정방법**은 분리한다.
- 대용량 Raster/NetCDF 출력은 API 본문이 아닌 Artifact URI + 식별자·메타데이터로 참조한다.
- REST, 메시지 큐, Kubernetes Job, 외부 API, Batch Import는 동일한 **논리적 Job Contract**를 따르게 한다.
- 모델 간 자료 교환은 **고정된 id + version + hash**를 사용하고 실험·보고서 재현 시 `latest` 참조를 금지한다.
- 모든 분석 실행에 `trace_id`, `workflow_run_id`, `job_id`, `agent_id`, `capability_id`, 입력 데이터·모델 참조, 결과·레이어 참조를 연결한다.
- 실자료 분석, 모의 Contract Test, 합성자료 시험, 독립 과학검증, 운영 검수의 결과를 UI·DB·로그에 분명히 구분한다.

---

# 3. 공통 Data Pipeline 개발 지시

## 3.1 수집 계층

다음을 플러그형 Connector로 추상화하라.

1. STAC Catalog/Asset Connector — Sentinel-2/Landsat 등 위성영상 검색
2. OGC/API Connector — 인증된 WMS/WFS/WCS/REST 등
3. Institution Connector — BIG/BMKG/BNPB/KLHK/ATR-BPN 등, 실제 인증·API 제공 여부에 따라 구성
4. File Import Connector — COG/GeoTIFF, GeoJSON/GPKG, NetCDF/GRIB, CSV/Parquet 등
5. Field/Review Data Connector — 전문가 검증·현장자료, 접근권한 확인

공통 인터페이스는 `discover / search / validate_access / fetch_or_import / inspect / register / get_status`를 갖고, 실제 기관 API를 모르면 `NOT_CONFIGURED` 또는 승인된 Offline Import로 처리한다. 존재하지 않는 API를 만들어 성공한 것으로 표시하지 않는다.

수집 기록에는 원본 Source URL·접근권한·라이선스·장면 ID·시간·CRS·해상도·품질정보·해시·데이터 제공기관·처리버전·실제 수신 바이트·예약 바이트를 저장한다. 서명된 SAS Query/API Key/토큰을 로그에 출력하지 마라.

**HTTP429/Rate Limit:** `Retry-After` 준수, 동시성·요청빈도 제한, 과도한 재시도 금지, 예산 분리, 명확한 중단상태, 중단 후 안전 재개, 실패와 실제 전송량 구분. 기존 LCLUC 예산원장을 재설정하거나 다른 계정·프록시로 우회하지 않는다.

## 3.2 공통 Raw→Staging→Validated 데이터 처리

- Raw: 수신 원본·메타데이터·Checksum은 불변으로 보존
- Staging: 포맷·CRS·시간·스키마·결측값·밴드·중복·클래스 코드 검사
- Standardized: 변환식, 버전, 파라미터, 지오메트리·단위·좌표계 명시
- Validated/Approved: ISO 19157 기반 검사 결과 및 승인 근거 연결
- AI-ready: 모델별 입력·라벨/Feature·QC·Split Manifest·검증 기준 충족

메타데이터는 TECH-4의 ISO 19115/19139 및 ISO 19157 취지를 추적하고, 실제 프로파일은 GMAIS 데이터 스키마로 관리한다.

**변환 규칙:** 범주형 라벨·SCL은 nearest-neighbor, 연속형 위성 밴드는 목적에 맞는 resampling(예: bilinear)을 명시하고, 관측 20m 밴드를 10m 격자로 변환했다고 **새로운 10m 관측치**가 생긴 것으로 해석하지 않는다. 시간대·달력·기후기준연도·단위·연직기준면을 필드로 관리한다.

## 3.3 데이터 계약·교차참조

`GMAIS/schemas/dataset-manifest.schema.json`에 준하는 Registry를 만든다. 실제 패키지 경로가 다르면 발견된 실경로에 맞춰 참조한다.

참조체계:

```text
source_asset → raw_dataset(id,version,sha256) → processed_dataset(id,version,sha256)
 → feature_set / label_set / split_manifest → model_run → model_version
 → agent_job / workflow_run → result_manifest → SDSS_layer → report/evidence
```

허용되지 않은 참조: 존재하지 않는 ID, 실제 File/Blob 미존재, 해시 불일치, 접근권한 위반, 라이선스 위반, 데이터 품질 미승인. 재현 가능한 분석 기록에 가변 `latest` 포인터 금지.

## 3.4 LCLUC 데이터 흐름의 기준 구현

- 1차 사업 그룹 6개 주를 후보 범위로 관리하되 AOI는 공식 승인 전 가정값으로 보존한다.
- Sentinel-2 B02/B03/B04/B08/B11/B12, WorldCover·Dynamic World(이용권한/접근 확인), SCL 품질마스크 사용
- 영상·라벨·품질마스크의 독립 재투영 및 격자·Affine·해시 비교
- 위성제품별 Reflectance Scale/Offset XML 근거 확인, Raw DN과 학습용 변환값 분리
- 이미지 Patch, Train/Validation/Test, 공간·연차·장면 단위 Leakage 방지
- WorldCover 2020/2021을 2022~2025의 실제 정답으로 단순 복제하지 않음
- WorldCover/Dynamic World 의사라벨 점수와 현장·독립 판독 정확도를 구분
- LCLUC 재수집이 실패해도 기존 Pipeline/API 기능 및 감사 기록 유지

### Data Pipeline 완료 증거

정상·오류 Fixture를 통한 Connector 계약시험, 실제 허용된 소규모 수집결과, 해시/무결성, 재투영·마스크 독립 재현성, Metadata/Lineage Query, 누락·차단 사유 API, 문서화된 라이선스·데이터 권한.

---

# 4. 공통 ML / Model Pipeline과 유형별 검증

공통 MLOps는 모든 모델을 강제로 PyTorch 모델처럼 취급하지 않는다. `model_type`별 확장 지점을 제공하고, **공통 모델 기록·검증·승인·배포**와 **유형별 갱신 로직**을 구분한다.

| 모델 유형 | 갱신 방식 | 검증의 핵심 | 필수 버전 항목 |
|---|---|---|---|
| `trainable_ml` | `RETRAINING` | 준비성·분할 누출·독립 holdout·기존모델 비교 | data/code/env/weights/split/metrics |
| `calibrated_physical` | `RECALIBRATION` | 보정·독립 검증기간 분리, 물리적 타당성·민감도 | code/parameter-set/forcing/initial&boundary conditions |
| `statistical` | 재추정 | 독립 관측·백테스트·편향 | specification/sample/parameters |
| `inference_only` | 검증된 추론모델 교체 | test vector·버전·출력 일관성 | executable/model/artifacts |
| `external_service` | `EXTERNAL_RELEASE` | 제공자 버전/SLA/계약·가용성·접근통제 | service/API/provider release |

유형명과 Update Ticket enum은 GMAIS v0.2 실제 JSON Schema를 따른다. 위 설명만으로 기존 계약 값을 조용히 변경하지 않는다.

## 4.1 학습형 모델 — Retraining SOP

Data QC → Freeze Manifest → Train Readiness Gate → 공간·시계열 Split → 새 Train Run → Validation → 독립 Test → Baseline 비교 → Model Card/설명가능성·한계 → 전문가 Approval → Staging 배포·Rollback Test → Production 승인.

- 데이터 부족, train/val/test 누락, 검증자료 오염, 라벨 매핑 오류, 단일클래스 Collapse는 Blocked/Failed로 관리
- 훈련 이력: 모델/데이터/코드/환경, seed, optimizer, loss, epoch, checkpoint, 클래스분포, 품질마스크, Metric
- 성능: LCLUC OA, mIoU, F1, class-wise IoU/Recall, confusion matrix, 지역·시기별 분리 검증
- 독립 정답이 없으면 WorldCover 대비 **의사라벨 일치도**로 명시하고, 실제 현장정확도로 주장하지 않음

## 4.2 수치·물리모델 — Recalibration SOP

관측·입력자료 QC → Base Model 재현 → 보정 파라미터 범위·초기/경계조건 확인 → 목적함수·보정기간 고정 → Recalibration Run → 독립 시공간 데이터 Validation → 물리적 일관성·민감도·불확실성 검사 → 보정 이력/Calibration Card → 분야 전문가 Approval → Staging 운영·Rollback Test → Production 승인.

**보정(calibration) 데이터와 독립 검증(validation) 데이터는 중복 사용하지 않는다.** 모델 코드 버전과 보정 파라미터 버전은 별도로 추적한다. 인도네시아 홍수·가뭄·해양 모델을 학습형 ML 지표(mIoU 등)로 일괄 판정하지 않는다.

## 4.3 수명주기 Update Ticket

`schemas/update-ticket.schema.json`과 `POST /v1/models/{model_id}/update-tickets`를 사용해 갱신 제안을 등록한다. `RETRAINING`, `RECALIBRATION`, `CONFIG_UPDATE`, `EXTERNAL_RELEASE`를 구분하며, **티켓 생성 자체는 학습·재보정·운영 배포를 실행하지 않는다.** 명시적 승인·Audit·Rollback 경로가 있어야 한다.

---

# 5. 6개 Model Agent 통합 계약

## 5.1 실제 개발 책임의 경계

| Agent | 이번 프로젝트에서 Codex가 수행할 일 | 타 기관/후속 책임 |
|---|---|---|
| 1. LCLUC | 실제 E2E 파이프라인·Adapter·Toolbox·SDSS 결과 | 공식 데이터/독립 검증 확보와 승인 별개 |
| 2. Climate Downscaling | Agent Schema·Contract Test·Connector Placeholder | 실제 다운스케일링 개발·검증·보정 |
| 3. Net Carbon Footprint | 입력/출력·시나리오·단위 계약 | 실제 탄소 추정·검증 |
| 4. Biodiversity Mapping | 공간·시계열·검증정보 연계 계약 | 실제 서식지/생태 분석·검증 |
| 5. Sea Level Rise & Subsidence | 조위/변위·datum·uncertainty 계약 | 실제 해수면·InSAR 모델 검증 |
| 6. Flood & Drought | 기후·강수·유역 입력과 결과 계약 | 실제 홍수·가뭄 모형·보정·검증 |

각 기관 이름과 모델별 R&R은 미확정으로 두고 책임 필드에 `TBD`를 사용한다. 그린블루의 내부 역할 제안이 계약상 최종 책임을 확정한다는 뜻이 아니다.

## 5.2 Agent Contract — **기존 GMAIS v0.2를 단일 기준으로 적용**

참조 파일:

```text
api/openapi.yaml
schemas/agent-manifest.schema.json
schemas/job-request.schema.json
schemas/job-status.schema.json
schemas/result-manifest.schema.json
schemas/error.schema.json
schemas/workflow-plan.schema.json
examples/
reference_adapter/
tests/
```

기본 엔드포인트 (실제 v0.2 문서와 대조):

```text
GET  /healthz
GET  /readyz
GET  /v1/agents
GET  /v1/agents/{agent_id}
GET  /v1/agents/{agent_id}/capabilities
GET  /v1/agents/{agent_id}/readiness
POST /v1/agents/{agent_id}/jobs
GET  /v1/jobs/{job_id}
GET  /v1/jobs/{job_id}/results
POST /v1/jobs/{job_id}/cancel
GET  /v1/results/{result_id}
POST /v1/models/{model_id}/update-tickets
```

비동기 Job 요청에 `Idempotency-Key`를 사용하고, 정상 수락은 HTTP `202` 및 `Location`에 Job URL, 데이터·모델 준비도/승인 문제는 정책에 맞는 차단(`409` 등), 인증 실패는 `401/403`으로 구분한다. 시스템 프로세스 Health와 과학모델 Readiness를 별개의 API 의미로 유지한다.

Agent `model_type` 열거값은 `trainable_ml`, `calibrated_physical`, `statistical`, `inference_only`, `external_service`; 실행유형은 `ASYNC_API`, `OCI_JOB`, `EXTERNAL_API`, `BATCH_IMPORT`를 사용한다. 문서 충돌 시 실제 제공된 Schema에 맞추고 변경 RFC를 발행한다.

Agent readiness: `BLOCKED`, `READY`, `NOT_IMPLEMENTED`. 모델 승인: `DRAFT`, `VALIDATED`, `APPROVED`, `DEPLOYED`, `RETIRED`. **Agent `READY`와 모델 `APPROVED`는 같은 의미가 아니다.**

## 5.3 모델별 Delivery Package

개발기관이 다음을 납품하도록 검수체계를 만든다.

```text
model-delivery/
  model-manifest.yaml (또는 표준 JSON)
  capability-schema.json
  input-schema.json
  output-schema.json
  openapi.yaml (외부 API형 포함)
  runtime-profile.yaml
  artifacts-or-service-release/
  fixtures/valid-request.json
  fixtures/invalid-request.json
  tests/contract-test-results.json
  validation/model-or-calibration-card.md
  lineage/input-reference-manifest.json
  security/ (SBOM, 라이선스, 비밀정보 처리)
  operations/ (장애, 모니터링, 재실행, 변경, 롤백)
  integration-guide.md
```

동일 형식을 전 모델에 억지 적용하지 말고, 외부 API형·배치형·수치형에 조건부 납품항목과 승인된 예외절차를 정의한다.

---

# 6. Orchestrator — 검증된 분석 실행 엔진

## 6.1 핵심 모듈

- Agent/Capability Registry 및 Model Registry Lookup
- Request Router · Capability Resolver · Input Readiness Validator
- Workflow Planner: DAG, 선행의존성, 데이터 변환·후처리 Task
- Execution Policy: 보안·데이터 권리·승인·자원·모델 준비도
- Job Manager: 중복방지, 상태전이, Cancellation, Timeout, Retry, Trace
- Result Aggregator: 품질·단위·좌표·시간·시나리오·불확실성 검증
- Result Registry 및 SDSS Layer Publisher
- Human Approval/Escalation Gate

## 6.2 작업 상태 계약

**GMAIS JSON Schema의 enum을 그대로 사용**한다.

```text
CREATED → VALIDATING → QUEUED → RUNNING → SUCCEEDED
                    ↘ BLOCKED
RUNNING/QUEUED → FAILED 또는 CANCELLED (정책상 허용된 경우)
```

불가능한 상태전이를 거부하고, 중복 Idempotency-Key로 이중 실행하지 않으며, 취소·재시도 시 부분 Output을 운영 완료 결과로 게시하지 않는다. 멀티 Agent DAG의 하나가 `BLOCKED`이면 의존 작업은 원인을 기록하고 중단하되 독립 작업은 정책 범위에서 계속할 수 있다.

Result에 `SCIENTIFIC_VALIDATED / DEVELOPMENT_ONLY / MOCK_ONLY`를 저장하고 이를 SDSS와 GeoLLM에서 그대로 표시한다. `MOCK_ONLY` 결과는 의사결정 지도·보고서로 게시하지 않는다.

## 6.3 실증 시나리오

1. **LCLUC 단일 Agent:** AOI+T1/T2 → 승인된 LCLUC 모델 확인 → 분석 → 변화지도·전이행렬·면적통계 → SDSS와 근거 응답. 현재 데이터나 모델 승인 없으면 `BLOCKED`이거나 명시적 Development 시연으로 남겨라.
2. **LCLUC→Carbon:** LCLUC 결과의 고정 `result_id` 및 `sha256`을 Carbon Agent 입력으로 전달. Carbon 미구현 시 해당 Node는 `NOT_IMPLEMENTED`/`BLOCKED`로 기록. 탄소량 수치 생성 금지.
3. **LCLUC→Flood:** 토지피복·불투수면 변화 결과와 홍수모델 입력을 연계하되 공간·시간·단위를 검증. 외부 모델이 없으면 계약시험만.
4. **Coastal+Flood+LCLUC:** 해수면·지반침하와 홍수·토지변화를 중첩할 때 기준면·기간·해상도·과학적 비교 가능성을 필수 검증.
5. **6-Agent 통합:** 6개 Agent 등록·Capability 조회·DAG Planning·오류·미구현 상태·접근통제·Audit·계약시험; 5개 가짜 과학결과를 생성하지 않는다.

### Orchestrator 완료 증거

직접 실행 가능한 DAG 1개 이상, 준비도 차단, 중복방지, 실패·Timeout·취소·재시도, 결과 ID 고정참조, 멱등성, 권한검사, 스키마 검증 및 기존 LCLUC Adapter 호출 계약시험.

---

# 7. 공통 MLOps 및 모델 운영

## 7.1 등록·승인·배포

데이터/실험/모델/보정 파라미터/서비스 이미지/운영 배포를 별도 Registry 자원으로 등록한다.

- `Dataset Registry`: 권리·품질·데이터 버전·변환·출처
- `Training/Calibration Run`: 유형별 실험 설정, 관측·검증·산출물
- `Model Registry`: 모델·알고리즘·가중치/파라미터 버전, 평가·제약
- `Agent Registry`: 실행·Capability·Runtime 프로파일
- `Deployment Registry`: digest·네임스페이스·승인·복구 버전
- `Result Registry`: 입력·버전·파라미터·실행근거·결과 검증·사용제약

**예시 승인 순서:** `DRAFT → VALIDATED → APPROVED → DEPLOYED → RETIRED`. 각 전이에 역할·근거·서명이 필요하고 `DRAFT`는 Production 실행을 차단한다.

## 7.2 관측 및 운영

- API latency, error, retries, pending Job, inference/processing duration
- CPU/GPU/RAM, Pod/Job 상태, 저장소 사용량, 객체 누락
- 데이터 Drift·Prediction Distribution·Quality Mask 변화, 모델별 과학 지표
- 보안 이벤트·승인·접근거부, 데이터·모델 버전 불일치
- Drift 발생 시 **갱신 검토 티켓만 자동 생성**, 무승인 모델 교체 불가

## 7.3 장애·Rollback

배포 전 승인된 직전 Artifact/Config/DB 호환성, Rollback Runbook 및 Smoke Test를 준비한다. 대규모 수집·학습이 실패해도 원본과 감사로그를 유지한다.

---

# 8. Docker / Kubernetes / 인프라 표준

모든 Agent를 무조건 상시 Pod로 배포하지 말고 지원 실행방식별로 처리한다.

| 실행유형 | 권장 구동 | 필요 시험 |
|---|---|---|
| 짧은 API 추론 | OCI 컨테이너 + Kubernetes Deployment/Service | health/readiness·scale·auth |
| 학습·대용량 배치 | Kubernetes Job / 승인된 작업큐 | GPU/CPU·timeout·restart·artifact resume |
| 외부 기관 API | API Connector + Network Policy | SLA·TLS·auth·timeout·failover |
| 파일 기반 인계 | 검증 Batch Import | 해시·스키마·품질·이력 |

패키지의 `kubernetes/agent-deployment.template.yaml`, `model-job.template.yaml`을 **템플릿**으로 재사용한다.

필수: OCI 이미지 digest 고정, 비루트, 최소 권한, Secret 외부 관리, CPU/RAM/GPU request·limit와 storage profile, readiness/liveness 분리, Structured JSON logs와 trace ID, graceful shutdown, retry-safe Job, NetworkPolicy, Staging/Production 격리, 취약점 검사, 백업·복구 및 롤백 테스트.

BIG 인프라 Kubernetes 버전, GPU·CUDA·스토리지·보안정책이 아직 확정되지 않았다면 특정 자원을 강제하지 않고 **TBD + 운영 호환성 매트릭스**로 관리한다. Docker Compose 로컬 개발 가능성과 Kubernetes 운영 준비도를 별도 검증한다.

---

# 9. GeoLLM/RAG 및 실행검증형 질의 인터페이스

GeoLLM이 과학모델을 직접 추론하지 않는다. **자연어 요청을 검증된 Capability/Toolbox 실행요청으로 변환하고, 실행결과·출처를 설명**한다.

```text
Query → Intent/Context/AOI/Time/Scenario
 → Authorization → Metadata/Policy RAG
 → Capability Resolution → Orchestrator Plan
 → Human Confirmation(if necessary)
 → Approved Agent/Tool Execution
 → Evidence Retrieval → Grounded Response + Map/Stats/Report
 → Query/Execution Audit & Feedback
```

구현할 서비스:

- Intent Parser, Spatial/Temporal Entity Parser, Analysis-Type Resolver
- Metadata RAG: dataset/model/result/lineage/quality 검색
- Policy RAG: 승인된 RDTR/RTRW·정책문서의 근거 검색, 문서버전 포함
- Capability Resolver 연결: 사용 가능한 Agent만 반환
- Tool Calling Contract: 승인된 Tool ID, JSON Schema, RBAC·검증·승인
- Grounded Response: 질문·AOI·기간·모델/데이터 버전·불확실성·증거 ID·분석결과 포함
- No-LLM fallback: 승인된 정형 질의·Toolbox 기능은 LLM API 없이 실행 가능

**금지:** LLM이 생성한 임의 SQL·Python·Shell 실행, 권한상승, 미존재 레이어/정책의 인용, 미구현 Agent를 통한 가짜 분석 성공, 운영 승인되지 않은 Draft 모델을 정책용 결과로 답변.

다음 3개 유형에 E2E 테스트를 작성한다: (1) 데이터 조회만, (2) LCLUC 실행요청/Blocked 사유, (3) 결과의 소스·모델·승인상태 설명. 검색한 근거와 생성한 답변의 출처를 연결하고, 권한 없는 출처는 유출하지 않는다.

---

# 10. SDSS·WebGIS 서비스 API 및 UX

## 10.1 핵심 사용자 흐름

1. BIG/현지 사용자 로그인 → 기관·프로젝트·역할별 권한 확인
2. AOI/기간/분석모델·시나리오 선택 또는 GeoLLM 질의
3. 데이터·모델·Agent 준비상태 확인 및 분석 실행 요청
4. Orchestrator DAG/Job 상태·진척·차단 이유 표시
5. 분석 완료 시 Result/Layer Registry 연결 → 지도·범례·시계열 비교
6. 변화·위험·노출 통계, 단위·클래스 정의·Quality/Uncertainty 표시
7. RDTR 중첩·근거 검토 및 전문가 피드백
8. 재현 가능한 분석보고서·GeoTIFF/COG/GeoJSON/CSV 내보내기

## 10.2 필요한 UI/API 기능

- `Dataset Catalog`: 원본/가공/승인/라이선스/품질·데이터 준비도
- `Agent Center`: LCLUC 작동·다른 5개 연결대기 및 검증 상태 구분
- `Toolbox`: 지원 분석과 파라미터·계획·실행 가능성
- `Workflow Monitor`: DAG/Job/blocked/error/retry/trace/evidence
- `Map & Statistics`: COG/벡터·범례·T1/T2·transition matrix·zonal stats
- `Scenario / RDTR`: 조건·중첩·출처·품질·인적 검토
- `GeoLLM`: 질의→도구 실행계획→근거 답변, 정확한 상태 안내
- `Governance`: Auth/RBAC·Approval·Audit·이의제기·Feedback
- `O&M`: 성능·장애·재실행·롤백·지원 기록

`GMAIS v0.2`의 Agent·Job API는 재사용하고, 필요한 SDSS Layer/Report API는 **별도 OpenAPI 모듈 또는 버전 있는 추가 명세**로 작성하라. 기존 `/api/data/collection-status`와 화면이 호환되도록 Adapter 또는 비파괴적 마이그레이션을 사용한다.

**시스템 성공의 증거는 지도 화면 스크린샷이 아니라, 고정된 실제 Input/Model/Job/Result ID가 API와 UI에서 일치하는 것**이다.

---

# 11. 공통 보안·거버넌스·계약 적합성

- 사용자/기관별 RBAC, Service Authentication, 최소 권한 API Token
- 제한 데이터의 목적 외 사용 및 외부 전송 금지, Secret·서명 URL 로그 비노출
- 데이터 라이선스/공식 제공 권한을 Artifact·Result로 상속
- 입력 스키마·GeoJSON·파일 크기·경로·확장자 검증; 위험한 업로드 금지
- SQL/LLM Prompt Injection, SSRF, Path Traversal, 악성 모델 아티팩트 방지
- 모든 분석·승인·다운로드·변경의 Trace/Audit, 중요 기록 수정 이력 보존
- CI/CD 시험, 컨테이너 취약점 검사, SBOM, 변경요청 RFC, 예외 승인대장
- Dev/Staging/Production/Recovery 분리

TECH-3A의 공식 데이터가 제공되기 전 **Two-Track Sandbox** 구상은 초기 구조/기능 검증용으로 사용하되, 샘플 데이터 기반 데모와 공식 데이터 기반 모델 검증·현지 검수를 서로 구분한다.

**사업 일정:** 원 제안 일정은 27개월 + 별도 90일 하자책임기간 구조를 참고하되, 실제 착수일·변경기간·검수·Home/Field M/M과 자카르타 상주 여부는 승인된 협상결과에 따라 확정한다. BIG 데이터 제공 후 3개월의 1차 6모델/1지역 설치 목표는 현재 논의된 조건이므로 **계약상 공식 조건으로 단정하지 말고 `DEPENDENCY/DECISION`으로 기록**한다.

---

# 12. 실제 구현을 위한 Gate별 실행계획

**중요:** 각 Gate 완료 조건에 “문서 작성”만 기록해서는 안 된다. 구현한 코드와 실행증거가 있어야 하고, 외부 기관 모델·데이터·인프라에 의존하는 항목은 구체적으로 Blocked 처리한다.

| Gate | 개발 목표 | 필수 산출물 | 검증/차단 기준 |
|---|---|---|---|
| G0 | 코드·제안서·GMAIS·현행 실적 분석 | inventory, traceability, gap, RACI/TBD, 테스트 Baseline | 미확정 내용 단정 금지 |
| G1 | 공통 Registry/ID·Data Contract | 데이터 Connector·Schema·QA·Lineage, 마이그레이션 | 실제 LCLUC 수집/감사 불변·기존 테스트 유지 |
| G2 | 공통 ML/Model Lifecycle | 타입별 Pipeline·Readiness·Update Tickets | LCLUC 학습 차단 유지, 학습/보정 분리 |
| G3 | 6개 Agent 공통 SDK | Agent Registry·LCLUC Adapter·외부5 Mock Contract Adapter | 공통 OpenAPI/Schema Tests, 과학결과 없음 표시 |
| G4 | Orchestrator 실제 엔진 | DAG/Job/API/Trace/Result Aggregator | 상태전이·중복·차단·재시도·취소·보안 테스트 |
| G5 | 공통 MLOps/K8s 준비 | registry/approval/deploy template/monitoring | 승인 없는 Production 차단, K8s 실제 클러스터 미검증 표시 |
| G6 | LCLUC E2E | 실자료 파이프라인, readiness, 학습/추론/변화탐지/SDSS 계약 | 데이터 부족시 training/deploy BLOCKED; 부분 성공분리 |
| G7 | GeoLLM/RAG | Intent/Tool Schema/Metadata-Policy Evidence/ACL | 근거 누락·미승인 실행 차단, LLM 없는 fallback |
| G8 | SDSS·WebGIS 통합 | Agent/Workflow UI·분석지도·통계·보고서 | Result/Layer/Report ID 링크 및 브라우저 E2E |
| G9 | 외부5 개발기관 인수 준비 | SDK/샘플/Swagger/납품검수·Contract Test Pack | 실제 과학모델 개발 완료로 표시 금지 |
| G10 | 통합 QA·운영 준비 | CI/tests/security/rollback/docs/UAT plan | 보안·성능·운영·과학검수 분리, BIG 승인 별도 |

## 개발 우선순위 및 의존관계

G0 → (G1·G2 설계 협의) → G3 → G4 → G5/G7/G8 통합 → G6 실제 데이터 Gate → G9/G10. 독립 UI·테스트·K8s 템플릿은 공통 Schema가 확정된 뒤 병렬 수행할 수 있다. Agent 공통 인터페이스를 확정하지 않고 여러 팀이 각자 Endpoint를 만드는 것을 금지한다.

**가장 빠른 기능 검증 세로절편(Vertical Slice):** 승인된 샘플/과거 데이터를 등록 → LCLUC Agent 조회·준비도 확인 → 적법하게 허용된 Development-only Job 실행 또는 정확한 `BLOCKED` → Result/Audit 기록 → SDSS·GeoLLM에서 같은 참조와 상태를 표시. 이 경로를 우선 관통시켜라.

---

# 13. Codex 병렬 개발 작업 배분

병렬 Agent 기능이 있는 경우 아래 소유권을 우선 정하고 스키마·DB·API 충돌을 방지한다.

| 작업자 | 작업 영역 | 공동 파일 변경 규칙 |
|---|---|---|
| `root/integration` | 요구사항·공통 스키마 승인·통합/CI·보안·문서 | Schema/DB migration 최종 병합 담당 |
| `data_pipeline` | Connector, Dataset Registry, QC, original lineage | Agent Manifest 수정 전 root 협의 |
| `ml_pipeline` | LCLUC 학습 Gate, 유형별 Model Lifecycle, Registry 연계 | 승인정책·출력 Schema 변경은 RFC |
| `agent_sdk` | 공통 SDK·5개 Adapter Template·Contract Test | OpenAPI/Schema Freeze 준수 |
| `orchestration` | Capability Resolver, DAG/Job/Result Aggregator | root가 Job 상태 Contract를 확정 |
| `devops` | Docker/OCI, Kubernetes Template, CI/CD, Monitoring | 실제 운영 클러스터는 별도 승인 |
| `geollm` | Intent, Metadata/Policy RAG, Tool Calling/ACL | Tool 호출은 Orchestrator만 허용 |
| `web_ui` | SDSS Agent Center/Workflow/Map/Report/GeoLLM UI | API 클라이언트 자동생성/계약 준수 |

기존에 존재하는 `data_pipeline`, `ml_pipeline`, `web_ui`, `root` 구성을 우선 재사용한다. 다른 작업자는 필요시 생성하되 환경이 지원하지 않으면 순차 작업으로 실행한다.

각 팀은 자신이 수정할 파일 경로, 병합 시점, 인터페이스 의존성을 먼저 `docs/implementation/workstream_ownership.md`에 선언한다.

---

# 14. 자동시험·증거·인수 기준

**최소 시험 범위**

1. GMAIS v0.2 JSON Schema/OpenAPI 계약시험 및 역호환성
2. 실제 LCLUC 원본 해시·CRS/affine/grid·라벨/마스크·입력계약 및 기존 수집 재현성
3. 서버 DNS 오류·HTTP 429·Retry-After·요청 예산·기존 원장 불변성
4. 학습 준비성/차단·Train/Val/Test 누출방지·단일 클래스 편중 감지
5. 학습형 Retraining과 수치형 Recalibration SOP의 서로 다른 Validation·Approval Gate
6. Agent CRUD/Capability/Readiness/Job/Result/Cancel, 동등 요청 Idempotency
7. DAG 계획·의존성·Blocked 전파·실패·재시도·Timeout·Cancel·Trace
8. 승인되지 않은 Model/Agent의 Production 실행 거부
9. GeoLLM 도구 호출 허용목록·RBAC·Evidence Grounding·No-LLM fallback
10. SDSS Layer·Report Reference Integrity, Browser E2E, 오해 유발 상태표시 방지
11. 컨테이너/Kubernetes 배포 템플릿의 정적 검증·Staging 복구 테스트
12. 기존 테스트 전부 재실행과 변경영향·회귀시험

**GMAIS 참조 계약시험 실행 예시(패키지가 실제 존재하면):**

```bash
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

이는 **GMAIS 참조 Adapter의 계약시험**이고, 플랫폼 실제 통합시험과 과학모델 정확도 검증은 별도 기록한다. 패키지 위치·의존성이 다르면 환경에 맞게 안전하게 변경하고 명령을 기록한다.

### Gate 결과 보고 양식

```markdown
## Gate N 검수 보고
- 대상/요구사항 ID:
- 실제 완료 기능:
- 수정 파일 및 변경 사유:
- 실행 명령 및 환경:
- 자동시험: 실행수 / PASS / FAIL / SKIP / 시간:
- 실자료 검증: 데이터 ID/버전/해시/결과:
- Contract Test / Scientific Validation / Security Test 구분:
- 차단·미구현·외부 의존성과 이유:
- 보안·권한·원장 변경 확인:
- 남은 위험 및 컨소시엄 결정 필요사항:
- 다음 Gate의 우선순위:
```

---

# 15. 생성해야 할 프로젝트 산출물

최종적으로 다음 **실제 경로 또는 기존 코드구조에 대응하는 대체 경로**를 생성/유지한다. 기존 폴더가 있으면 먼저 매핑하고 불필요한 전면 이동은 하지 않는다.

```text
docs/implementation/
  01_source_inventory.md
  02_as_is_architecture.md
  03_requirements_traceability.md
  04_gap_analysis.md
  05_risks_decisions_and_assumptions.md
  06_target_architecture_and_roadmap.md
  07_api_and_agent_compatibility.md
  08_model_type_validation_sops.md
  09_integration_test_and_evidence.md
  workstream_ownership.md
  progress.md
contracts/
  openapi/          # GMAIS v0.2 기반 Agent·Job·Toolbox·SDSS 연계
  schemas/          # Dataset/Model/Agent/Workflow/Result/Layer/Report
  examples/
  contract_tests/
services/             # 기존 프로젝트 배치에 맞춰 구성
  data/
  mlops/
  agent_registry/
  orchestrator/
  geollm/
  sdss_api/
models/lcluc/         # 기존 실제 LCLUC 코드 보존·연계
integrations/external_agents/  # 5개 기관형 Adapter Template, Mock 표기
infrastructure/
  docker/
  kubernetes/
  monitoring/
  ci/
evidence/
  unit/
  contract/
  integration/
  scientific/
  security/
  deployment/
```

**외부 납품 문서**: Model Agent SDK, I/O Contract, API Definition, Container/External Service Profile, Retraining/Recalibration SOP, Agent Delivery Checklist, RACI/Approval Matrix, Sample Integration Package, Contract Test Results, Open Issues·Exception Register.

---

# 16. 실행을 지금 시작하라 — 최초 작업 및 응답 형식

### 현재 이 프롬프트를 실행한 직후 Codex가 해야 할 일

**Step 1.** 기존 저장소를 조사하고 TECH-4, GMAIS v0.2, LCLUC 개발 기록의 실제 파일 경로 및 최신 상태를 확인하라. 필요 자료가 누락된 경우 즉시 표시하라.  
**Step 2.** 기존 테스트를 실행하여 변경 전 Baseline을 기록하라. 실패를 숨기거나 강제로 PASS 처리하지 마라.  
**Step 3.** 표준 문서 요구사항↔기존 코드 Gap Analysis와 공통 ID/Schema/API 병합계획을 작성하라.  
**Step 4.** **GMAIS v0.2 Agent Contract, Cross-Reference 규칙, 데이터 계약을 우선 동결 후보**로 제안하고 실제 코드의 호환성 문제를 기록하라.  
**Step 5.** 최소 수직절편으로 **LCLUC 데이터/상태 API → Agent Registry/Readiness → Orchestrator Job(실행 가능 시 제한적 실행, 아니면 Blocked) → SDSS/GeoLLM 공통 Trace**를 관통시켜라.  
**Step 6.** 새 계약시험과 기존 회귀시험을 실행하고 결과를 보고하라.  
**Step 7.** 이후 Gate의 실행 가능한 개발 작업을 우선순위대로 진행하되, 데이터 부족·모델 미제공 등 외부 의존성은 Blocked로 남겨라.

첫 응답에서는 다음 정보부터 제공하라.

```text
[기존 프로젝트 확인]
- 저장소 경로/브랜치/작업 중 변경사항:
- 발견된 제안서·GMAIS·코드·실자료:
- Baseline 테스트 결과:
- 현재 LCLUC training readiness / model approval:
- 공통 Agent API·Data Contract 충돌 여부:

[이번 Gate 계획]
- 작업할 실제 파일:
- 세부 변경 순서:
- 필요한 테스트:
- 중단·승인 필요한 변경:
```

그 후 실제 코드를 수정하고 완료 증거를 남겨라. **LCLUC 1개만 실자료 기반 E2E 기준 구현, 다른 5개는 외부 기관이 납품 가능한 실행형 통합 계약**이라는 개발 경계를 끝까지 유지하라.

---

## 부록 A. 용어 정리

| 약어/영문 | 국문 의미 | 본 사업의 역할 |
|---|---|---|
| AOI — Area of Interest | 관심영역 | 분석할 지도 경계 |
| STAC — SpatioTemporal Asset Catalog | 시공간 데이터 자산 카탈로그 | 위성영상 검색·자산 메타데이터 |
| Data Pipeline | 데이터 수집·정제 파이프라인 | 원본 수집·품질·표준화·등록 |
| ML Pipeline | 기계학습 파이프라인 | 준비도·학습·평가·실험 기록 |
| Model Agent | 모델 연계 실행 모듈 | 모델 기능 등록·실행·상태·결과 |
| Orchestrator | 작업 조정·실행 엔진 | Agent 선택·DAG·Job·결과 집계 |
| MLOps — Machine Learning Operations | 모델 수명주기 운영관리 | 버전·검증·승인·배포·모니터링 |
| Recalibration | 모델 재보정 | 물리·수치모델 파라미터 재추정·검증 |
| GeoLLM | 지리공간 대형언어모델 | 자연어 공간질의·Tool 연계·근거 설명 |
| SDSS — Spatial Decision Support System | 공간의사결정지원시스템 | 지도·시나리오·통계·RDTR 분석·보고 |
| Kubernetes | 컨테이너 오케스트레이션 플랫폼 | 서비스 배포·자원관리·복구 |
| GMAIS | GeoAI Model & Agent Integration Standard | 그린블루 제안 공통 통합 규격 |

## 부록 B. 본 프롬프트의 제한

이 문서는 제출된 TECH-4의 아키텍처 방향과 GMAIS v0.2 내부 제안 표준을 조합한 **개발 실행 지시**다. 특정 회사가 5개 외부 모델의 과학적 개발을 책임진다고 확정하지 않는다. 정부의 공식 원천데이터·현지 시험자료, 사업기간·모델별 검수 기준, 운영 Kubernetes 사양, 컨소시엄 승인권한이 확인되지 않으면 반드시 의존성 및 협의사항으로 남긴다.
