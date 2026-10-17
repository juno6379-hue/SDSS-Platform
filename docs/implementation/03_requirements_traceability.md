# 통합 요구사항 추적

확인: 2026-10-17 KST. source_type은 마스터가 인용한 TECH-4 요구와 내부 GMAIS 제안을 구분한다. 서명계약/기관 승인 원본은 확인되지 않았다.

| requirement_id | source_section | source_type | subsystem | owner_proposed | acceptance_evidence | current_state | gap | decision_required |
|---|---|---|---|---|---|---|---|---|
| DATA-01 | TECH-4 §2.2/2.4.1 | 제출문서 인용 | Data | data_pipeline | 데이터 감사 JSON·recovery 시험 | 부분 | 기관 Connector·불변 Registry | 기관 endpoint/권한 |
| ML-01 | 마스터 §4 | 내부 개발 지시 | ML | ml_pipeline | readiness 재검사·ML tests | BLOCKED | class/scene 누출·독립 평가 | 현장 라벨·합격선 |
| AGENT-01 | GMAIS v0.2 | 내부 제안 | Agent | integration | test_gmais_api.py | 부분 | 외부5 실행기 | 납품 기관 R&R |
| FLOW-01 | TECH-4 §2.4.2 | 제출문서 인용 | Orchestrator | integration | test_gmais_workflow_extension.py | PLAN_ONLY | 실제 DAG/retry/cancel | RFC 승인 |
| UI-01 | UI UX v2 §2–5 | 내부 UI 제안 | Web | web_ui | 브라우저 screenshot·build | 구현 | 기관 UAT·다국어 번역 | 공식 IA 승인 |
| RESULT-01 | 마스터 P2 | 내부 개발 지시 | Result/SDSS | integration | test_sdss_results.py | 로컬 계약 구현 | 운영 Result·COG tile/외부 자산 | 독립 검증/배포 |
| OPS-01 | TECH-4 §2.4.5 | 제출문서 인용 | MLOps | integration | model lifecycle 시험 | 부분 | staging/RBAC/rollback | 운영 인프라 |
| LLM-01 | TECH-4 §2.4.3 | 제출문서 인용 | GeoLLM | integration | GeoQuery plan-only | 부분 | ACL Metadata/Policy RAG | 근거자료/권한 |

세부 데이터 원문 추적: [03_traceability_data.md](03_traceability_data.md). UI reference는 구현 상태/수량의 증거로 사용하지 않는다.
