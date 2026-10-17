# Job 제출 시점 입력 기록 조회 UI

기준일: 2026-10-17, Asia/Seoul. 상태: **지속 개발 진행 중**. 이 작업은 기존 Job의 저장 진단을 읽는 UI 연결이며 실제 Job 실행·과학/운영 승인을 뜻하지 않는다.

## 구현·사용법

- `frontend/src/AgentCenter.tsx`의 표준 Job 조회가 상태 API와 새 `GET /v1/jobs/{job_id}/input-resolution`을 동시에 조회한다. 두 응답을 따로 판단하므로 상태 조회 성공이 기록 조회 성공으로 바뀌지 않는다.
- `Job·Trace·입력 기록 실제 조회` 버튼에 실제 발급된 Job ID를 입력한다. 조회 가능한 기록이 있으면 기존 InputDiagnostics에 고정 ID/version/SHA, 무결성·품질·권한 차단, 검사 시각·scope를 표시한다.
- `RECORDED`: 같은 Job·Trace의 제출 당시 저장 기록이다. **현재 파일을 재검사한 결과가 아니며 실행·과학 승인을 부여하지 않는다**는 문구를 함께 표시한다.
- `LEGACY`: 이전 Job에는 제출 시점 입력 기록이 저장되지 않았다. 현재 자료에서 진단을 재생성하거나 통과로 추정하지 않는다.
- `INVALID`: 서버가 SNAPSHOT_INVALID를 보고하거나 응답 계약이 다르면 저장 입력을 표시하지 않는다.
- `IDENTITY_MISMATCH`: 요청 Job ID 또는 상태의 Trace와 snapshot wrapper가 다르면 표시를 차단한다.
- `NOT_FOUND`: 입력 기록 endpoint의 HTTP404. Job 상태 성공과 별개로 기록 부재·API 미지원 여부를 확인하도록 표시한다.
- `ERROR`: 그 외 기록 조회 실패. 상태 조회 성공을 입력 무결성 통과로 해석하지 않는다.

## 계약과 경합 보호

- `inputDiagnosticsAdapter.ts`의 jobSnapshotView는 extension, Job/Trace, available/reason/snapshot 관계와 `current_files_revalidated:false`, `execution_authorized:false`, `scientific_approval:false`를 확인한다.
- Job ID를 편집하거나 Agent를 바꾸면 이전 Job·입력 기록·Result·게시 판정을 즉시 지운다. 요청 세대와 응답 Job ID를 함께 확인하므로 이전 조회 응답이 뒤늦게 도착해도 다시 표시하지 않는다.
- 조회 중 Agent 변경, 같은 ID의 재조회, 화면 이탈에 대해서도 세대를 무효화한다. 폴링·취소·Result 조회의 늦은 응답이 새로운 Job 화면에 섞이지 않도록 같은 guard를 사용한다.
- 원본 JSON 접기 영역은 기존 민감정보 필터를 사용하여 제한 경로·URI·자격정보를 숨긴다.
- READY 제출 gate와 실제 실행·Result 상태 조건은 유지했다. 신규 Job·운영 Dataset·과학모델 결과를 등록하지 않았다. 6개 모델 PNG 기반 레이아웃, Vite proxy 설정, backend 코드는 변경하지 않았다.

## 검증·문서

- 기존 입력/정책 adapter5시험에 새 snapshot3시험을 추가했다: Job·Trace일치/불일치, legacy·invalid·불완전 계약과 승인값 거부, ID/Agent 변경 및 이전 요청 세대 거부.
- Result adapter5시험을 함께 수행해 **UI adapter13/13 PASS, 561.2336ms**를 확인했다. 시험 fixture 상태는 **TESTED_SYNTHETIC**이며 실제 과학모델 결과가 아니다.
- production build **PASS: 52 modules, 15.97초, 종료0**. 생성된 production JS에 API8002/api가 포함되고 이전8001/api가 없는 것을 확인했다. MapLibre 포함 chunk 크기 경고는 남는다.
- production build 및 adapter 증거: `evidence/integration/job-snapshot-ui-build-20261017.log`.
- 관련 API/서버 계약은 root/data 담당 문서31을 참고한다. 본 문서32는 UI 사용법·진단 해석·경합 방지를 담당한다. 이해자료 갱신은 root가 완료 코드·최종 증거를 understanding_agent에 전달한다.

## 현재 개발 실행 경로

- 현재 UI 주소는 **http://127.0.0.1:5174**를 유지한다. 브라우저는 동일 출처 `/api`·`/v1`을 호출한다.
- root가 새 API를 **http://127.0.0.1:8002**, `--reload --reload-dir backend`로 실행했다. 코드 변경 시 worker PID는 바뀔 수 있다. 이전8000/8001 API 프로세스는 보존한다.
- root가 `frontend/.env.local`의 VITE_API_BASE를 `http://127.0.0.1:8002/api`, VITE_API_PROXY_TARGET을 `http://127.0.0.1:8002`로 갱신했다. UI 담당은 이 두 설정만 읽어 확인하고 최종 build를 검증한다.
- 개발 UI5174의 동일 출처 proxy가 API8002로 전달한다. backend CORS·인증을 완화하지 않는다. 최종 실제 브라우저 요청·새 endpoint 확인은 root/integration 담당이며 서버 시작·build 통과만으로 live 검증 완료라고 표시하지 않는다.

## Root 실제 브라우저 검증

UI5174→동일출처 proxy→API8002에서 기존 Job의 BLOCKED 상태와 LEGACY 기록 부재를 확인했다. Job ID 변경 즉시 이전 상태/진단을 지웠고, 없는 ID는 JOB_NOT_FOUND HTTP404를 표시했다. 증거는 evidence/integration/job-snapshot-live-ui-20261017.json 및 evidence/ui-20261017/job-input-snapshot-legacy-live.png·job-input-snapshot-not-found-live.png다. Catalog·원장·manifest SHA 전후 동일, 신규 Job/Result/Trace0. snapshot이 실제 저장된 성공 조회는 임시 fixture 시험이며 live에서는 두 legacy Job의 읽기만 확인했다.
