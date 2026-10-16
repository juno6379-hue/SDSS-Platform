# GMAIS v0.2 API·Agent 호환성 구현 기록

작성: 2026-10-16. 기준 문서는 워크스페이스의 `GreenBlue_GMAIS_v0.2/GreenBlue_GMAIS_v0.2_실행형_표준패키지/`이다. **내부 검토용 제안본**이며 컨소시엄/BIG의 승인 계약이나 운영 승인으로 간주하지 않는다. 계약 기준 파일은 수정하지 않고 `contracts/upstream/GMAIS-v0.2/`에 복사해 사용한다.

## 구현된 로컬 vertical slice

`backend/app/gmais_api.py`가 제안 `/v1` 경로를 제공하고 `backend/app/main.py`가 기존 `/api`와 별도로 router를 연결한다. 현재 여섯 모델 슬롯을 Agent manifest로 노출한다. 실제 구현 상태는 LCLUC만 `BLOCKED`; 다른 다섯 개는 `NOT_IMPLEMENTED`이다. 상위 manifest는 원문 schema의 필드만 사용하고 runtime·dataset·science·deployment·contract 세부축은 별도 `/readiness` companion 응답으로 둔다.

Job 요청은 vendored `job-request.schema.json` Draft 2020-12 validator로 검사하고 `Idempotency-Key`로 중복 제출을 통제한다. 현재 학습자료 준비도, 독립 과학평가, 승인·배포 모델 gate를 통과하지 못하므로 Job은 저장된 `BLOCKED` 상태로 응답한다. 표준 `job_id`·`trace_id`를 조회할 수 있지만 이 상태에서 `Result`·지도·보고서를 만들지 않는다. 같은 키/같은 본문은 동일 Job을 가리키고, 같은 키/다른 본문은 `SCHEMA_MISMATCH`로 거절한다. `/healthz`·`/readyz`는 인증 없이 런타임 상태만 제공하며 과학 준비도를 암시하지 않는다. 브라우저 CORS 요청은 `Idempotency-Key`를 허용한다.

## 경로별 상태

| 경로 | 로컬 상태 | 참고 |
|---|---|---|
| `GET /healthz`, `GET /readyz` | 구현 | 런타임 liveness/readiness만 확인 |
| `GET /v1/agents` 및 `/{agent_id}` | 구현 | 6개 manifest, 원문 Agent schema와 계약 시험 |
| `GET /v1/agents/{agent_id}/capabilities` | 구현 | Agent별 등록 capability |
| `GET /v1/agents/{agent_id}/readiness` | 구현 | proposal companion; 다섯 readiness 축을 manifest 확장 속성으로 위장하지 않음 |
| `POST /v1/agents/{agent_id}/jobs` | 부분 구현 | Idempotency·원문 요청 schema 검사·audit 가능한 BLOCKED Job. 실행 가능한 scientific executor가 없음 |
| `GET /v1/jobs/{job_id}` | 구현 | 표준 status/trace 조회 |
| `GET /v1/jobs/{job_id}/results`·`GET /v1/results/{result_id}` | 차단/조회 | 결과가 없으면 409, 임의 result를 만들지 않음 |
| `POST /v1/jobs/{job_id}/cancel` | 제한 | BLOCKED 상태는 종결 상태로 취소 거부 |
| `POST /v1/workflows/plan` | 로컬 RFC 확장·계획 전용 | upstream workflow schema·DAG를 검사하지만 upstream v0.2 OpenAPI path가 아니다. 입력 Registry/Agent 실행 미연결로 항상 BLOCKED, Job/Result는 생성하지 않음 |
| `POST /v1/models/{model_id}/update-tickets` | 미구현 | schema/OpenAPI만 확인; 실제 approval·ticket store·운영 책임 미확정 |

## 남은 호환·거버넌스 gap

- API route의 contract response와 에러 status/body를 원문 OpenAPI 모든 사례로 확대 검증한다.
- workflow plan은 GMAIS v0.2의 존재하는 schema를 쓰되 `/v1/workflows/plan` 별도 extension으로 버전·소유·승인 상태를 명시한다.
- Update Ticket, Model Registry, artifact/result publication, 권한별 RBAC, 감사 주체 및 기관별 external API/OCI adapter는 미구현이다.
- 현재 `/api` 모델 lifecycle과 표준 Agent approval enum은 서로 다른 저장 계약이다. 기존 기록을 임의 변환하지 않고, 버전·체크포인트 SHA·데이터 lineage를 대조하는 명시적 projection이 필요하다.
- 현재 계약 응답은 내부 검토본의 호환 구현이며 BIG/컨소시엄 승인, 독립 정확도, 실제 여섯 모델 실행, 운영 보안/배포 검증이 아니다.

## 계약 검증

`tests/test_gmais_api.py`는 upstream JSON Schema로 여섯 manifest와 Job/error/status 응답을 검사하고, BLOCKED Job의 trace/멱등성/결과 부재/외부 Agent 차단을 확인한다. `tests/test_gmais_workflow_extension.py`는 plan-only RFC, schema·DAG·차단·비실행을 검사한다. 두 파일은 각각 **8개와 7개 PASS**였고 2026-10-16 전체 회귀시험 **175개 PASS**다. 실제 로컬 HTTP smoke는 [증거](../../evidence/integration/gmais-live-http-contract-only-20261016.json)에 기록했다. 이는 계약·차단 통합시험이며 위성자료의 과학적 정확도 증거가 아니다.
