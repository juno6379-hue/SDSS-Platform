# 현행 아키텍처

확인: 2026-10-17 KST. 내부 개발 현황이며 운영 인수가 아니다.

- `frontend/src/App.tsx`: React/MapLibre 공통 shell, 7개 전역 메뉴와 로컬 탐색. `PlatformShell.tsx`·`ModelAnalysisWorkspace.tsx`의 모델별 작업화면과 기존 검색·학습·추론·변화분석 화면을 연결한다. `SDSSChrome.tsx`는 PNG 기준 공통 header/sidebar/footer를 제공한다.
- `backend/app/main.py`: FastAPI 기존 `/api`, SQLite Store, 로컬 단일 작업 executor, 모델 승인 gate. `gmais_api.py`는 내부 v0.2 `/v1` 호환 API와 plan-only RFC를 제공한다.
- `backend/app/data/`: STAC/COG·연간 참조·공유 예산 수집. 실제 수신 자료와 전역 원장은 `data/`에 보존한다. 중단 복구 진단은 `data/recovery.py`가 읽기 전용으로 수행한다.
- `backend/app/ml/`: 6밴드 준비도·정합·분할·학습·추론·평가. 과학적 검증과 배포 승인은 별도다.
- `backend/app/sdss_results.py`: 표준 Result의 schema·Job·Trace·고정 입력/모델·자산 SHA 검사와 SDSS projection. 검증한 복사본만 다운로드한다. 실제 승인된 표준 Result는 아직 없다.
- PostGIS, MLflow, 기관 인증, 운영 Kubernetes, 외부 5개 실행기, 실제 DAG 스케줄러는 연결되지 않았다.

근거: [API 호환성](07_api_and_agent_compatibility.md), [UI 구현](23_ui_completion.md), [재개 인계서](00_next_session_handoff.md).
