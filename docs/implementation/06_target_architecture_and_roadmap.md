# 목표 아키텍처·실행 순서

확인: 2026-10-17 KST. 기존 구현을 확장한다.

1. 중단 batch의 실제 전송·terminal 증거를 보존해 coordinator 복구를 시험한다. lock 제거만으로 재개하지 않는다.
2. 고정 manifest의 hash·정합·공간/시간/scene 분할·클래스 gate를 통과한다. 독립 참조를 확보해 평가한다.
3. 검증된 모델을 검토·승인·배포한 뒤 실제 LCLUC Job이 표준 Result를 생성하도록 실행기를 연결한다.
4. 고정 ID/version/SHA·Trace를 유지하며 Result→SDSS projection→GeoJSON/COG 지도→보고서로 이어간다. 현재 구현은 로컬 projection 및 GeoJSON 표시/자산 다운로드까지다.
5. Dataset Registry projection과 RFC를 확정한 후 DAG 스케줄링·retry/timeout/cancel을 구현한다.
6. 외부5 Agent SDK/납품계약, ACL 근거검색, 기관 RBAC, staging/K8s/CI·보안·복구/UAT를 통합한다.

공통 흐름: Connector → 불변 Raw/Registry → Readiness → Model lifecycle → Agent/Job → 검증 Result → SDSS/Report. GeoLLM은 근거 조회/계획·설명, Orchestrator는 실행 조정, MLOps는 검증·승인·배포 책임을 맡는다.

이번 병렬 소유: data_pipeline=data/recovery·collection status, ml_pipeline=ML readiness, web_ui=frontend, root=공통 API·Result adapter·통합 문서/시험. 다음 담당자는 [인계서](00_next_session_handoff.md)의 최신 갱신을 먼저 읽는다.
