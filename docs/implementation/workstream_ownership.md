# 병렬 작업 파일 소유권

서로의 영역은 협의 없이 수정하지 않는다. 공통 계약/Schema 변경은 root/integration과 먼저 합의한다.

## root/integration — GMAIS API vertical slice

- 소유: `backend/app/gmais_api.py`, `backend/app/main.py` 공통 router/CORS wiring, `backend/requirements.txt`, `backend/Dockerfile`, `docs/implementation/07_api_and_agent_compatibility.md`, `docs/implementation/progress.md`.
- 구현: 제안 v0.2 기반 여섯 Agent registry, LCLUC readiness companion, upstream Job Request JSON Schema 검증, 멱등성·BLOCKED job/trace·result 차단.
- 금지: 내부 검토본을 승인 규격으로 표현하거나, BLOCKED 입력에 scientific Result/지도 생성.
- 분리 시험: `tests/test_gmais_api.py`는 ml_pipeline 소유; 데이터 수집 worker/원장 변경은 data_pipeline 소유; 화면/evidence는 web_ui 소유.

## data_pipeline — 2026-10-16 G0/G1 조사

- 소유: `docs/implementation/01_source_inventory_data.md`, `docs/implementation/03_traceability_data.md`, `docs/16_충분학습자료_단계별수집계획.md`, `docs/20_대량수집_학습_통합실행.md`의 데이터 수집 현황/작업로그.
- 기존 코드 소유: `backend/app/data/`, `scripts/collect*.py`, 수집 설정/데이터 시험. 이번 조사에서는 실행 중 coordinator를 보존하기 위해 수정하지 않는다.
- 증거 출력: `evidence/integration/data-g0-g1-20261016.json` 및 소유 문서. 실수집 원장·수신파일·실행manifest는 읽기만 한다.
- 병합: source inventory/traceability의 데이터 분할문서를 root가 공통 `01_source_inventory.md`/`03_requirements_traceability.md`에 연결한다. 공통 파일을 독자 덮어쓰지 않는다.
- 의존: GMAIS v0.2 실제 패키지 발견/공통ID·Schema 결정은 root 책임. 패키지가 없으면 `SOURCE_MISSING`; 본 명령서로 스키마를 추측해 생성하지 않는다.
- 실행 보호: root session89858의 수집을 중단/중복실행/원장 수정하지 않는다. 최신 계상·적격 집계는 읽은 시각을 붙인 snapshot으로만 기록한다.
