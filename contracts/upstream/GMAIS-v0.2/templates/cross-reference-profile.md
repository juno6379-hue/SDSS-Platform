# Cross-reference 식별·고정 규칙
- 식별자: Dataset ID/Version/Hash, Model ID/Version/Hash, Agent ID/Version, Capability ID, Workflow Run ID, Job ID, Result ID, Layer ID, Report ID, trace_id.
- 불변 참조: 결과가 입력으로 참조한 dataset/model은 **id+version+sha256** 고정. latest 포인터는 사용자 탐색 전용이며 분석재현용으로 사용 금지.
- 참조무결성: 등록되지 않은 id, 존재하지 않는 blob, SHA 불일치, 접근권한 누락 또는 Retired artifact는 거부.
- 사슬: user query → trace_id → workflow_run_id → job_id → agent/model+dataset → result_id → layer/report. immutable audit 이벤트로 연결.
- 데이터 표준: CRS·pixel grid/affine·resolution, 시간(timezone/calendar), 단위/Vertical datum, quality flag, category legend를 함께 비교.
- 데이터 원본/가공 독립 버전, 접근권한·라이선스 상속·사용목적별 제약을 표시.
- lineage event: parent_refs, process_version, parameters_hash, executed_at, actor, result_hash.
