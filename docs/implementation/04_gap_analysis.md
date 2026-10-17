# 통합 gap

확인: 2026-10-17 KST.

| 우선순위 | 현재 구현 | 남은 gap | 다음 수락 증거 |
|---|---|---|---|
| P0 | 읽기 전용 중단 복구 진단 | pending 2건 terminal/계측 근거 없음 | 원장 보존·중복 없는 coordinator 복구 시험 |
| P1 | 연간 URL 호환·분할 통계 보정 | 클래스 충분성·scene 누출·독립 라벨 | 최신 manifest SHA에 연결된 readiness와 독립평가 |
| P2 | 7개 메뉴·6개 Workspace·표준 Result projection | 실제 승인 Result 없음, COG tile 렌더러 미연결 | 실제 과학 검증 Result→레이어/보고서 E2E |
| P3 | plan-only RFC, BLOCKED Job 영속화 | DAG 실행·상태전파·retry/timeout/cancel | 실행기 계약·통합 실패 복구 시험 |
| 외부 의존 | 외부5 manifest·입력 초안 | 실행 이미지/기관·모델 납품 없음 | 기관 계약시험·검수 |
| 운영 | 로컬 gate/테스트 | 기관 RBAC·CI/CD·SBOM·K8s·UAT | staging 운영/복구·기관 인수 |

상세: [ML gap](04_gap_analysis_ml_draft.md), [인계서](00_next_session_handoff.md). UI 완성은 과학모델/운영 인수 완료와 별개다.

### 2026-10-18 사용자 확인: 외부 실행기·독립 검증 라벨 미확보

다른5개 모델 API/SDK/실행코드는 별도 제공·준비되지 않아 미연결·실행기 미구현 상태로 관리한다. 독립 정확도 검증용 라벨도 미확보다. 기존 약한라벨 학습자료는 보존하지만 이를 독립 검증 자료나 과학 승인으로 대체하지 않는다. 유형별 validation/recalibration 요건은 계속 별도 검토하며, 제공되지 않은 물리모델 관측자료까지 새로 확보됐다고 가정하지 않는다. 근거: `evidence/integration/recovery-commit-contract-external-dependencies-20261017.json`; 영역별 잔여 수락 조건은 [109 감사](109_area_completion_audit.md)를 따른다. 전체 사업·모델 운영 승인 완료가 아니다.

### 2026-10-18 후속: 실제 등록·ML 오류분석·GeoLLM 기술검토

[111](111_data_pipeline_completion.md)은 수집 source report를 RAW/STAGED 문서로 공통 버전에 연결한 명시 CLI이며 운영등록/AI-ready 승인이 아니다. [112](112_lcluc_ml_completion.md)는 기존 TinyUNet RGB 체크포인트를 확인하고 완료best 모델의 val/test 오류분석을 실제 학습 report에 연결했다. class7·QA차단과 독립 검증 라벨 미확보를 해제하지 않는다. [113](113_lcluc_integration_acceptance.md)의 LCLUC전용 새 orchestration은 후속PLANNED다. [114](114_geollm_technical_review.md)는 현재 앱에 LLM/RAG 미연결임을 확인하고 설치된 Ollama 모델의 별도 실응답·실패·임베딩과 Qwen3:8b 후보/N/A를 구분한다. 기존 정상 GeoLLM API/UI·운영 DB/원장은 변경하지 않았다. 최신 전체 시험·보존·이해자료·다음 수락 조건은 인계서의111~114 절을 따른다. 이 변경만으로 Data/ML/운영·기관UAT 전체 완료를 선언하지 않는다.

## 115 후속 상태 — 로컬 CLI 실행 연결 완료, API/UI는 후속

[115 구현·검증](115_lcluc_workflow_executor.md)에서 고정 Registry·배포/독립평가 metadata·실파일 검사를 거친 LCLUC 로컬 실행 코어와 명시 CLI를 추가했다. 생성 영상·시험용 승인 metadata의 TempStore에서 실제 TinyUNet CPU 시계열·변화·전환행렬·보고서·7개 artifact SHA를 검증했고 운영 실행은0이다. 기존 아래 '미착수/PLANNED'는113/114 조사 당시의 이력이며 최신 내부 코어 상태는115를 따른다. global-only boundedtile 코어가 완료됐지만6밴드 per_scene 보정/구름mask·API/UI·GMAIS Result·generic DAG·실제독립평가/배포 인수는 미완료다. 현재 운영 Draft/QA차단/기관권한을 우회하거나 Ollama/RAG를 앱에 연결한 변경은 아니다. 전체 시험·보존·이해자료와116 후보는 최신 인계서를 따른다.
