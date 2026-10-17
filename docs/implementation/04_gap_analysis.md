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
