# 다음 세션 시작용 플랫폼 인계서

작성·확인: 2026-10-16, Asia/Seoul. 이 문서는 마스터 프롬프트 v1.0의 Gate와 인수조건을 현재 코드·검증·증거에 대조한 재개 지침이다. **다음 세션은 이 문서를 먼저 읽고, 아래의 변동 상태를 다시 확인한 뒤 병렬 작업을 이어간다.** 수치와 PID는 스냅샷이므로 재개 시 현재 manifest·프로세스와 대조한다.

## 다음 세션의 첫 순서

1. 이 문서 → GreenBlue_CODEX_Master_Prompt_GMAIS_Integrated_Platform_v1.0.md → docs/implementation/progress.md → docs/implementation/workstream_ownership.md 순으로 읽는다.
2. 작업 전에 docs/implementation/07_api_and_agent_compatibility.md, 08_model_type_validation_sops.md, 22_ui_sdss_geollm_evidence.md, docs/18_MLOps_SDSS_연계검증.md, docs/20_대량수집_학습_통합실행.md도 확인한다.
3. Get-CimInstance Win32_Process로 collect_training_parallel.py와 monitor_collection_progress.py, 전역 ledger lock, run-result.json, 최신 감사 JSON을 읽는다. 기존 collector가 살아 있거나 실행 lock이 있으면 새 collector를 시작하지 않는다. 단발성 읽기 전용 감사를 장기 감시와 중복 실행하지 않는다.
4. 수집기·전역 원장·합산 manifest·원본·모델·체크포인트를 문서 작업을 위해 수정하지 않는다. 공통 계약·API·DB 변경은 root/integration이 먼저 조정한다.
5. data_pipeline, ml_pipeline, web_ui는 소유 경로 안에서 병렬로 이어가고 root/integration은 공통 계약·통합시험·인수 문서를 맡는다. 다음 빈 슬롯에 orchestration/geollm/devops/agent_sdk 작업을 나눌 수 있다.

## 상태 판정 기준

- **완료:** 해당 범위의 코드와 시험 증거가 있다. 전체 사업 또는 과학·운영 인수를 뜻하지 않는다.
- **부분 완료:** 구현이 존재하지만 마스터의 인수 조건 일부가 미충족이다.
- **보류/BLOCKED:** 안전 gate가 다음 단계를 의도적으로 막고 있다.
- **미완료/미착수:** 구현 또는 인수 증거가 없다. 템플릿/문서/HTTP 응답 모양만으로 완료 처리하지 않는다.

## 최신 확인 스냅샷

최신 읽기 전용 데이터 감사는 **2026-10-16 16:54:26 KST**, [evidence/integration/data-g0-g1-20261016T075426219437Z.json](../../evidence/integration/data-g0-g1-20261016T075426219437Z.json)이다. 원본 manifest SHA-256은 `925785265fc8a829b2d9e3e5ef41663255ec2b714375200baba84def87089413`이며 감사 도중 파일을 쓰거나 네트워크 요청을 보내지 않았다. 1,336개 물리 패치 중 1,071개 manifest 품질 적격, 265개 부적격이다. 6개 주×2020~2025년 36/36 셀 모두 적격 자료가 있고 train/validation/test는 588/233/250이다. 적격 총량은 1,000을 넘지만 이를 학습 승인이나 정확도 증거로 보지 않는다.

최신 셀별 적격 수는 남술라웨시 37/32/29/36/36/30, 고론탈로 46/23/14/30/25/8, 남동술라웨시 25/18/26/18/1/23, 동자바 23/16/34/28/16/14, 반텐 53/58/51/32/23/16, 서자바 57/41/56/32/32/32 순이며 연도 순서는 2020~2025다. 계획 바닥인 셀당 28개를 모든 셀에서 만족하지 않는다. 특히 고론탈로 2025(8), 남동술라웨시 2021(18)·2023(18)·2024(1), 동자바 2020(23)·2021(16)·2024(16)·2025(14) 등 저수량 셀을 다음 수집 우선순위에서 확인한다. 이 분포는 수량만 나타내며 클래스 균형·공간 대표성을 보장하지 않는다.

관측된 pending batch는 South Sulawesi 2020 (`parallel-v2-grid-esri_io-south_sulawesi-2020-g03`)와 Gorontalo 2021 (`parallel-v2-grid-esri_io-gorontalo-2021-g03`)다. 실행 lock은 있었지만 프로세스 health는 감사에서 검증하지 않았다. 신규 예산 예약/계측은 1,875,687,296B이며 pending 예약 136,314,880B를 포함한다. 신규 4GiB 상한 잔여는 2,419,280,000B다. 원장 내부합계 일치, HTTP429 회로 비활성. 예약액은 실제 수신량이 아니다. 재접속 시 프로세스·lock·batch·SHA·수치를 다시 확인한다.

ML 담당의 직전 독립 재계수는 **manifest SHA `57c9b672…`인 1,026 적격 snapshot** 기준 train 572<600, East Java 고유 위치 28<32, split별 bare 클래스 비율 0.5% 미달 및 기여 패치 0/5, 원본 scene split 충돌 1건(Banten val 16 / West Java test 9)을 보고했다. 이 증거는 최신 1,071 snapshot의 검증으로 간주하지 않는다. 최신 manifest에 대해 class·공간·scene 누출 gate를 다시 계산해야 하며 그 전까지 학습은 BLOCKED다. ML 검사에서 별도 발견한 Esri 2024/2025 연간 URL 날짜 형식과 `readiness.py` 허용 패턴 간 호환 차이는 실제 실행 참조가 잘못됐다는 증거가 아니라 구현 호환 gap이다. 수정/회귀시험 및 최신 행 검증이 남아 있다. `data/first-group/training-readiness.json`은 77패치·31/36 셀을 담은 **오래된 readiness 결과**이므로 현재 manifest 상태로 인용하지 않는다.

## 마스터 프롬프트 Gate별 구축 판정

| Gate | 판정 | 실제 구축·검증된 것 | 남은 작업/수락 조건 |
|---|---|---|---|
| G0 현행 조사 | **부분 완료** | TECH-4/5, LCLUC 코드, GMAIS v0.2 실행형 패키지 확인. 패키지와 공유 사본 34개 파일 SHA-256 일치. 워크스페이스에는 `.git`이 없고 GitHub `juno6379-hue/SDSS-Platform` 원격 `main`은 README만 있는 것을 확인. | 통합 inventory/as-is/gap/roadmap 문서 일부 미작성. 서명계약, 공식 기관 데이터 권한·endpoint, 기관 R&R 미확정. |
| G1 Data Contract/Registry/Connector | **부분 완료** | LCLUC Sentinel-2 STAC/COG, 6밴드·SCL·라벨 처리, 출처·해시·연차 manifest, 동년 참조, 공유 예산·2 worker·요청 간격·429 전역중지 구현. | 범용 OGC/기관/현장 Connector, 7-method 공통 interface, GeoTIFF 외 파일 import, 불변 version Dataset Registry, upstream Dataset Manifest projection, 완전 lineage/ISO 프로파일 미완료. 기존 데이터 row를 upstream schema에 덮어쓰지 않는다. |
| G2 Model Lifecycle | **부분, LCLUC 학습 보류** | PyTorch 학습·추론·평가와 readiness, SHA/split/class/정합 gate, Draft 등록 및 승인/배포 차단 구현. 제품 XML의 반사도 scale/offset 근거 확인. | 최신 안정 manifest readiness, class balance·공간 대표성·scene 누출 해결. 독립 현장 라벨/OA/mIoU 실제 정확도 미확보. 다른 model_type의 calibration/statistical/external lifecycle 미구현. |
| G3 6개 Agent | **부분 완료** | v0.2 기반 6 manifest, capability/readiness, LCLUC BLOCKED/DRAFT, 외부5 NOT_IMPLEMENTED. Schema 검사, 멱등 key, 영속 BLOCKED Job/Trace 구현·시험. | 동적 기관 등록, 외부5 실행·납품검수, 승인된 성공 Job/실 Result 없음. GMAIS는 내부 제안이며 BIG/컨소시엄 승인본이 아님. |
| G4 Orchestrator | **계획만 부분 완료** | 내부 /v1/workflows/plan 확장이 Workflow Plan schema·DAG·중복/순환/Capability를 검사. PLAN_ONLY/BLOCKED, execution_started=false. | upstream OpenAPI에 없는 RFC 확장. 실제 DAG 스케줄링/실행, 상태전파, retry/timeout/cancel, Result 집계 미완료. |
| G5 MLOps/Kubernetes | **부분 완료** | 모델 전이, 실험 Draft 등록, checkpoint/data/report hash 검사, 독립평가·배포 gate. Dockerfile과 upstream K8s 템플릿 존재. | 유형별 calibration/external release, Update Ticket endpoint, 기관 RBAC/서명, OCI 배포 registry, 실제 K8s/staging/rollback/monitoring 미완료·미검증. 템플릿은 배포 성공이 아님. |
| G6 실제 LCLUC E2E | **BLOCKED** | 데이터→readiness→model review→분석→지도/보고서 기반 연결. 합성 raster E2E contract 시험에서 분석·변화지도·보고서 응답 검증. | 최신 manifest readiness와 balance/leakage gate 미통과. 합성 시험은 과학 성능 증거가 아님. 독립 검증·모델 승인·운영 배포 필요. |
| G7 GeoLLM/RAG | **부분 완료** | GeoQuery 정형 조회·근거 표시, plan-only 연결, LLM 없는 fallback. | intent/spatial/temporal parser, Metadata/Policy RAG, ACL 근거 검색, grounded 응답, Orchestrator 통한 실제 도구실행 미완료. |
| G8 SDSS/WebGIS | **부분 완료** | 기존 분석지도·GeoJSON/통계·보고서/내보내기, Animate/Swipe, Agent Center/Job 조회. Registry/Job/Trace/plan-only를 브라우저에서 검증. | GMAIS Result assets→Layer/Report Adapter, UI Job 제출·DAG polling/retry/cancel, RDTR/시나리오·기관 ACL·Human feedback 미완료. raw Result URL 직접 브라우저 이동은 미검증. |
| G9 외부 Agent 인수 | **미완료** | upstream templates/schemas, NOT_IMPLEMENTED 상태표시. | 외부5 실행형 Adapter/SDK sample/delivery package와 기관명/R&R/모델 미확정. |
| G10 통합 QA/운영 | **부분 완료** | 전체 회귀시험 기록상 175 PASS, GMAIS API 8·workflow 7, UI adapter 4, 프런트 build 42 modules/exit 0, localhost 계약·브라우저 증거. SDSS 5시험은 합성 fixture 범위. | 시험을 현 시점에 재실행한 것은 아님. Security/SBOM/CI-CD, staging/UAT·성능·K8s 복구, BIG/기관 인수 미완료. |

## 다음 세션 실행 순서와 병렬 담당

**P0 — 데이터 수집 상태 보존:** 프로세스·lock·run-result·ledger를 먼저 확인한다. 활성 collector가 있으면 기다리고 중복 실행하지 않는다. 현재 확인했던 두 pending batch, 잔여예산·429·적격수를 갱신한다. 종료가 확인된 경우에만 동일 부모 coordinator/전역 원장으로 재개를 검토한다.

**P1 — 새로 고정된 manifest로 ML readiness 재검증:** 과거 training-readiness.json을 재사용하지 않는다. 수집 안정 후 전체 file/hash·band·normalization·mask/alignment·split·class·공간 대표성을 재검사한다. 16:45 train=572<600, East Java 고유 공간 최소32, split별 bare 비율≥0.5% 및 기여 패치≥5, scene split 충돌 0건이 알려진 gate다. 결과가 ready_for_training=true가 아니면 학습 금지.

계획 QA는 data-root 아래 별도 readiness 출력 경로를 지정한다. 기본 data/first-group/training-readiness.json을 덮지 않으며 --execute 없이 사용한다.

~~~powershell
python scripts/run_experiment.py --manifest data/first-group-training-esri-v1/annual-window-report.json --plan data/first-group/experiment-esri-v003-2020-2025.json --readiness-output first-group/readiness-handoff.json
~~~

기본 data-root는 data다. 명령은 readiness JSON을 쓰지만 학습은 시작하지 않는다. 안정된 manifest 확인 뒤 실행하며, Esri 참조를 사용한 첫 실험은 약한 라벨 일치도일 뿐 독립 정확도/운영 승인과 다르다.

**P2 — Result→SDSS vertical slice:** 실제 고정 ID/version/SHA/Trace를 갖는 표준 Result에서 Layer/Report adapter를 연결한다. MOCK_ONLY, job/result 불일치, hash 오류는 게시를 차단하는 계약·브라우저 시험으로 확인한다. 이어 Agent Center의 조건부 Job submit/poll/status/cancel과 evidence 표시를 연결한다.

**P3 — 공통 계약과 Gate 문서:** Workflow endpoint RFC, Dataset manifest projection, BBOX CRS 해석, quality와 approval 구분, metadata 확장 위치, immutable lineage 방안을 root가 조정한다. upstream v0.2 파일은 승인 없이 수정하지 않는다.

**병렬 역할:** data_pipeline은 수집·연차라벨·QC·data docs, ml_pipeline은 readiness/lifecycle/학습 gate, web_ui는 Result/Layer/Report 및 Job/GeoQuery, root/integration은 공통 API/schema/RFC/테스트 및 handoff를 맡는다. orchestration/geollm/devops/agent_sdk는 필요 시 별도 owner를 둔다. 공통 schema/DB 변경을 병렬로 겹치지 않는다. 세부 파일 소유는 docs/implementation/workstream_ownership.md 우선.

## 외부 의존성·문서 gap

- GMAIS v0.2는 checksum 검증된 **GreenBlue 내부 제안**이다. 정식 BIG/컨소시엄 표준이라 표현하지 않는다.
- 공식 기관 endpoint·인증/라이선스·제공 책임, 공식 AOI 승인, 외부5 기관명/R&R, 독립 현장 검증라벨·성능 합격선, 운영 Kubernetes·보안·RBAC·배포 담당은 미확정이다.
- 마스터 §15의 통합 산출물 가운데 02_as_is_architecture.md, 03_requirements_traceability.md, 04_gap_analysis.md, 05_risks_decisions_and_assumptions.md, 06_target_architecture_and_roadmap.md, 09_integration_test_and_evidence.md는 단일 통합본으로 아직 갖춰지지 않았다. 데이터/ML/UI 분할 문서는 있으므로 이 handoff에서 연결하고 중복 없이 보완한다.
- 현재 작업 워크스페이스 자체는 Git repo가 아니다. GitHub `main`은 별도 clone에서 동기화하며, 커밋 전 staged diff를 검토한다. 공개 저장소에 데이터·토큰·비밀정보를 넣지 않는다.

## 핵심 근거 색인

- 기준: GreenBlue_CODEX_Master_Prompt_GMAIS_Integrated_Platform_v1.0.md
- 진행: docs/implementation/progress.md, docs/implementation/progress_data.md
- 데이터: docs/implementation/01_source_inventory_data.md, 03_traceability_data.md, docs/16_충분학습자료_단계별수집계획.md, docs/20_대량수집_학습_통합실행.md, evidence/integration/data-g0-g1-20261016T075426219437Z.json
- API/Agent: docs/implementation/07_api_and_agent_compatibility.md, backend/app/gmais_api.py, contracts/upstream/GMAIS-v0.2/
- ML: docs/implementation/08_model_type_validation_sops.md, docs/implementation/04_gap_analysis_ml_draft.md, backend/app/ml/readiness.py, data/first-group/training-readiness.json (old 77-patch snapshot)
- UI: docs/implementation/22_ui_sdss_geollm_evidence.md, frontend/evidence/gmais-live/, frontend/src/
- MLOps/SDSS: docs/18_MLOps_SDSS_연계검증.md, tests/test_mlops_sdss_flow.py
- Animate/Swipe: docs/21_Animate_Swipe_개발기록.md, frontend/src/TemporalCompare.tsx
- tests are under tests/; previous PASS is historical evidence, not a new run.

