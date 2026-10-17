# Workflow·Job 입력 및 정책 진단 UI

기준일: 2026-10-17, Asia/Seoul. 개발 상태: **지속 개발 진행 중**. 이 단위는 진단의 UI 연결이며 전체 Orchestrator·운영 인수를 뜻하지 않는다.

## 구현 범위

- `frontend/src/InputDiagnostics.tsx`: 공통 입력 진단과 Workflow 정책·노드 진단 컴포넌트.
- `frontend/src/inputDiagnosticsAdapter.ts`: 진단 projection, 누락 응답 처리, 민감 경로·URI·자격정보를 숨기는 출력 adapter.
- `frontend/src/input-diagnostics.css`: 진단 카드·표의 한국어 표시와 모바일 줄바꿈. 6개 PNG 기반 모델 Workspace 레이아웃은 변경하지 않았다.
- `frontend/src/GeoQuery.tsx`: `/v1/workflows/plan` 응답을 노드별로 표시. 원본 JSON은 민감 경로를 제외한 접기 영역으로 유지한다.
- `frontend/src/AgentCenter.tsx`: Job 제출의 HTTP409 `error.details.input_resolution`을 보존하여 표시한다. 진단이 없는 기존 Job 상태 응답을 통과로 표시하지 않는다.
- `frontend/src/App.tsx`: GeoLLM의 `실행계획 검토` 메뉴는 execution, `근거·출처 확인` 메뉴는 evidence 질의 유형으로 연다. 메뉴 왕복 시 계획 JSON·질문·선택 분석 ID 초안은 탭 세션에 보존한다.

## 화면과 계약 매핑

| 서버 필드 | 화면 표시 | 해석 제한 |
|---|---|---|
| input_resolution.evaluated_at / evaluation_scope / scope | 검사 시각·검사 범위 | 제출/계획 시점 snapshot이며 현재 실행 승인 아님 |
| resolved[].id / version / sha256 | 고정 입력 ID·버전·SHA-256 | 임의 경로 또는 최신 버전으로 치환하지 않음 |
| integrity_verified | 입력 무결성 일치/미확인·불일치 | 품질·권한·과학적 승인과 별도 |
| quality_status / access_class | 품질·접근 분류 | PUBLIC을 기관 권한 검증 완료로 간주하지 않음 |
| authorization_verified / blocker_codes | 권한 검증 기록·차단 조건 | false는 권한 검증 안 됨으로 표시 |
| policy_resolution.on_blocked | STOP_DEPENDENTS / FAIL_ALL 설명 | 실행·취소 정책을 실제 적용한 결과 아님 |
| policy_resolution.topological_order / local_blocking_node_ids | 검사 순서·직접 차단 노드 | 실제 스케줄링·실행 이력 아님 |
| node.dependency_resolution.local_blockers | 이 노드의 직접 차단 | 원본 detail_code/code 보존 |
| upstream_blocked_by | 선행 노드로부터 전파된 차단 | 의존성 경로에 따른 원인 |
| policy_blocked_by | 전체 중단 정책으로 전파된 차단 | 실제 upstream과 별도 표시 |
| blocking_cause_node_ids / diagnostic_status | 최초 원인 노드·진단 상태 | NO_BLOCKING_CAUSE_IDENTIFIED는 READY가 아님 |

## 사용자 확인 경로

1. `GeoLLM Assistant → 실행계획 검토`를 선택한다. 준비도 검토 유형이 처음부터 표시된다.
2. 실제 Registry의 Agent·Capability와 고정 입력 ID·버전·해시를 JSON 초안에 입력한다.
3. `실제 실행계획·차단 근거 조회 (RFC)`를 누른다. 서버의 Workflow ID·Trace·정책·노드별 입력 및 차단 원인을 확인한다.
4. 원본 JSON을 펼쳐 같은 응답을 확인한다. 민감 경로·URI 필드는 숨긴다.
5. Agent Center의 제출은 READY gate를 유지한다. 제출 오류에 실제 Job ID·입력 진단이 포함되면 해당 snapshot을 표시한다. 자동 Job 실행 버튼은 비활성 상태다.

## 검증·증거

- `inputDiagnosticsAdapter.test.mjs` 5개 시험: 무결성과 권한 승인 구별, 품질/ACL blocker 보존, 직접·의존·정책 원인 분리, 실행 권한 생성 금지, 제한 경로·URI·자격정보 비노출, 누락 응답 처리.
- 기존 Result adapter 5개 시험과 합계 **10/10 PASS**, 최종 522.8507ms.
- production build **PASS**: 52 modules, 18.95초, 종료0 (개발 proxy 코드 보완 후 마지막 build 재실행). MapLibre 포함 JS chunk 크기 경고는 남는다.
- production build 및 두 adapter 시험 통합 로그: `evidence/integration/workflow-policy-ui-build-20261017.log`.
- 시험 상태: **TESTED_SYNTHETIC**. 브라우저의 실제 API 연결·전달값 확인은 root/integration의 별도 검증 범위다.

## 남은 제한

아래 UI 담당의 단위 검증에 이어 root가 실제 Workflow 브라우저 표시를 확인했다. 최종 근거는 이 문서 마지막 절을 따른다. Job409 표시는 코드·합성 어댑터 시험 범위이며 READY gate를 우회한 실제 제출은 수행하지 않았다.

- 입력 무결성 검사·차단 전파 진단은 실제 executor, 기관 ACL, 독립 과학평가, 모델·배포 승인과 다르다. 실행 버튼 gate를 해제하지 않았다.
- 현재 GET `/v1/jobs/{job_id}`의 원본 Job Status에는 입력 snapshot 확장이 없다. 조회만으로 snapshot을 가져온다고 표시하지 않는다. 제출409 응답에서 제공된 진단을 표시한다.
- 운영 서버가 이전 코드를 계속 실행 중이면 backend 재기동/재배포가 필요하다. 프런트 코드 반영만으로 API 기능이 적용됐다고 판단하지 않는다.
- UI 단위 완료를 전체 개발 완료로 보고하거나 보고 예약을 중지하지 않는다. 이해자료·발표·FAQ 갱신은 root가 완료 소스·최종 검증 근거를 understanding_agent에 전달하여 수행한다.


## 현재 실행 연결과 환경 반영

- root가 새 읽기·계획 진단 API를 `http://127.0.0.1:8001`에 실행했다. 기존8000 프로세스 중지 명령이 자동 승인 검토에서 차단되어 기존 API8000을 보존하고 루프백8001을 사용했다. 같은 Catalog를 사용하며 실행 gate는 유지한다.
- `frontend/.env.local`의 `VITE_API_BASE=http://127.0.0.1:8001/api`를 root가 갱신했고, UI 담당이 해당 설정만 읽어 확인한 뒤 마지막 production build를 재실행했다. 동일 로그 끝에 해당 환경 build52modules/19.93초/종료0을 추가했으며, 아래 proxy 보완 후 마지막 build52modules/18.95초/종료0을 다시 추가했다. 이미 통과한 UI adapter10시험은 코드 변경이 없으므로 반복하지 않았다.
- 기존Vite5173은 reload 후에도 API8000을 계속 가리켰다는 root의 실제 확인에 따라 보존했다. root가 API_BASE를 명시한 새 UI를 **`http://127.0.0.1:5174` → `http://127.0.0.1:8001/api`**로 실행했다. 실제 사용자 브라우저는 이 새 UI 주소에서 확인한다.
- 이는 현재 개발 실행 연결이다. 코드의 일반 기본값과 env example8000 설정은 유지한다. 새 환경 설정만으로 기존 Vite5173 프로세스가 변경됐다고 보고하지 않는다.


## 개발 동일 출처 proxy 보완

- 신규 UI5174에서 API8001로 브라우저 직접 요청할 때 기존 API의 CORS가5173만 허용하여 차단되는 것을 root가 확인했다. API의 CORS·인증 설정과 기존 프로세스를 바꾸지 않고 개발 Vite proxy를 추가했다.
- `frontend/vite.config.ts`가 설정 파일 위치의 env를 읽고 `VITE_API_PROXY_TARGET`이 있을 때만 `/api`, `/v1`, `/healthz`, `/readyz`, `/docs`, `/openapi.json`을 해당 target으로 전달한다. 실제 로더 검사에서 여섯 경로 모두 `http://127.0.0.1:8001`로 설정됨을 확인했다.
- `frontend/src/api.ts`는 `DEV && VITE_API_PROXY_TARGET`인 경우에만 API_BASE를 `/api`로 선택한다. 브라우저 요청 경로는 **UI5174의 동일 출처 `/api`·`/v1` → 개발 proxy → API8001**이다. 표준 Agent 요청과 인증 다운로드도 같은 UI origin을 사용하고 기존 토큰 헤더를 유지한다.
- proxy 설정이 없는 일반 개발 설정과 production은 기존 VITE_API_BASE/default8000 분기를 유지한다. production build 자체가 Vite 개발 proxy를 제공하는 것은 아니며 실제 운영에서는 지정 API의 CORS 또는 운영 reverse proxy가 별도로 필요하다.
- 이 변경은 개발 연결 경로에 한정한다. 실행 READY gate·기관 권한·과학/모델/배포 승인을 해제하지 않았다. 6개 모델 레이아웃은 변경하지 않았다.

## Root의 실제 브라우저 검증

`http://127.0.0.1:5174/`에서 GeoLLM Assistant→실행계획 검토를 열고 source→dependent 및 independent의 3노드 계획을 조회했다. 입력 참조는 모두 빈 배열이며 실제 과학 데이터/모델 실행이 아니다. 메뉴가 execution 유형을 자동 선택하고 새 API의 입력/정책 진단을 카드로 표시했다. STOP_DEPENDENTS에서 dependent의 선행 원인은 source, 독립 분기의 정책 원인은 없었다. FAIL_ALL에서는 독립 분기 원인이 정책 원인으로 추가됐다. 두 경우 모두 BLOCKED·PLAN_ONLY, 자동 실행 비활성 상태였다.

- 실제 서버 및 원본 보존 증거: `evidence/integration/workflow-policy-live-ui-20261017.json`.
- 화면: `evidence/ui-20261017/workflow-stop-dependents-live.png`, `workflow-fail-all-live.png`, `workflow-diagnostics-live.png`.
- 실제 Catalog·전역 원장·합산 manifest의 전후 SHA가 모두 같다. 신규 Job/Result/Trace는 만들지 않았다. Catalog에 원래 있던 gmais_jobs 2건은 그대로 보존됐다.
- UI 적용 여부는 확인했지만 실제 학습·과학적 정확도·운영 배포 승인으로 확대하지 않는다. 기존5173의 새 API 적용은 별도로 확인하지 않았다.
