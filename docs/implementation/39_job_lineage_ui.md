# Job 입력의 현재 전이 계보 읽기 UI

기준일: 2026-10-17, Asia/Seoul. 상태: 지속 개발 중. 이 단위는 이미 저장된 Job의 고정 입력에 대해 요청 시점의 현재 계보를 읽는 내부 RFC UI다. 저장 snapshot·Job 실행·과학 승인·기관 권한을 변경하지 않는다.

## 변경 파일·배치

- `frontend/src/AgentCenter.tsx`: 표준 Job 상태와 저장 snapshot 영역 아래에 독립 현재 계보 컴포넌트만 연결한다.
- `JobLineageDiagnostics.tsx`, `job-lineage-diagnostics.css`: 명시 조회 버튼·현재 검사 카드·입력/진단 매핑·개별 노드/부모→자식 연결·차단·한도 표시.
- `jobLineageAdapter.ts`, `.test.mjs`: Job/Trace,검사 scope,읽기·승인 불변,고정 참조/진단 연결,부분 검사,응답 경합 검사.
- 대시보드·카탈로그·6개 모델 PNG 배치,기존 status/snapshot/READY 실행 gate,backend/API·원문계약·원본 데이터는 변경하지 않는다.

## 사용자 경로와 서버 계약

1. Agent Center에서 실제 Job ID를 `Job·Trace·입력 기록 실제 조회`로 확인한다. 기존 상태·제출 snapshot 조회는 그대로 유지한다.
2. `이 Job 입력의 현재 계보 읽기 검증`을 별도로 누른다. 이때만 `GET /v1/jobs/{job_id}/lineage-validation`을 호출한다. Job 조회·화면 진입·2.5초 상태 polling에 현재 계보 검사를 넣지 않는다.
3. Job·Trace,검사 시작/종료 KST,`CURRENT_TRANSITIVE_LINEAGE_NOT_SUBMISSION_SNAPSHOT` 범위,입력→고유 진단 연결,재사용 여부,개별 계보 노드/연결,차단,검사 한도·수행량을 확인한다.
4. 원본 JSON은 기존 안전한 details로 보존하며 제한 경로·URI·자격정보를 숨긴다.

상세 응답 계약은 data_pipeline의 문서38과 API/core가 기준이다. wrapper는 `greenblue.job-lineage-validation.rfc1`,approval_status INTERNAL_REVIEW,기관/실행/과학 승인false다. 개별 diagnostics는 기존 Dataset 계보 `_project` 결과이며 저장 snapshot을 포함하지 않는다.

## 판정·해석

| 응답 | 표시 의미 |
|---|---|
| available=true, CURRENT_LINEAGE_CHECKED, BLOCKED | 현재 진단 보고서는 있지만 차단 조건이 존재한다 |
| INTEGRITY_VERIFIED | 모든 검사·입력 연결·차단 근거가 일치한 현재 무결성 보고이며 품질/기관/실행/과학 승인은 아니다 |
| LEGACY_REQUEST_NOT_RECORDED | 원래 요청이 없어 현재 계보 확인 불가; 저장 snapshot 부재와 별도로 표시 |
| JOB_REQUEST_INVALID | 저장된 요청이 유효하지 않아 검사 불가; 신원/Trace까지 다르면 응답 신원 불일치로 표시 차단 |
| CHECK_LIMIT_REACHED, available=false | 입력64/고유루트32 상한 등의 선행 제한으로 검사 미시작 |
| CHECK_LIMIT_REACHED, available=true | 현재 총 검사 예산 소진 등 부분 결과; 미검사 binding을 전체 통과로 처리하지 않음 |
| HTTP404 / 503 / 401·403 | Job/API 부재·서비스 불가·인증 문제를 구별; 저장 snapshot 성공으로 대체하지 않음 |

- checked는 해당 참조 진단을 수행했는지이며 검사 성공이 아니다. reused는 같은 고정 ID/version/SHA의 진단 재사용이다.
- current_assets_revalidated=true는 한 번 이상 resolve 시도했다는 뜻이다. 전체 자산 성공으로 표시하지 않는다.
- 같은(id,version)의 다른SHA가 상충하면 available=true라도 diagnostics가 비어 있고 checked=false일 수 있다. 구조 진단 자체는 유효하므로 BLOCKED·차단 원인을 표시한다.
- API의 고정 예산:입력64,고유루트32,깊이32,루트당 최대노드64,전체노드256. 노드/고유루트 수행량은 이 한도와 별도로 표시한다.
- Job·Trace가 요청과 같고 wrapper·개별 diagnostic의 승인false/네트워크·쓰기0,입력 ref와 diagnostic_index의 root_ref 연결이 일치해야 표시한다. 무결성 집계와 개별 노드/차단이 불일치하면 표시를 거부한다.

## 경합·비반복 검사

현재 검사는 기존 stored snapshot state와 분리한 자식 컴포넌트 상태를 사용한다. Job ID·Agent 변경/재조회/화면 이탈 시 기존 Job 세대와 key가 바뀌어 현재 카드가 제거된다. 늦은 응답은 자식 요청 세대·Job/Trace key로 거부한다. 버튼은 검사 중 비활성이며 자동 반복 해시는 없다. 기존 제출 snapshot과 원본 요청을 다시 쓰지 않는다.

## 검증·증거

- 신규 adapter7시험:Job/Trace/scope,legacy/invalid/상한,부분 검사·상충 입력,중복 진단 재사용·고정 ref 연결,무결성/승인 불변,예산·읽기 범위,조회 경합.
- 기존 UI25시험과 합계32시험을 실행한다. 합성 fixture 상태는 TESTED_SYNTHETIC이고 실제 성공 과학계보·운영 승인이 아니다.
- build/시험 로그: `evidence/integration/job-lineage-ui-build-20261017.log`.
- 실제 기존 Job의 legacy·현재 차단 조회,원본 snapshot 불변,desktop/mobile 검증은 root/integration이 담당한다. 새로운 성공 fixture·운영 데이터·Job을 UI 검증용으로 등록하지 않는다.
- root가 완료 소스·최종 로그·문서39를 understanding_agent에 전달하여 해설·발표·FAQ·INDEX를 갱신한다. 이 단위 완료를 전체 프로젝트 완료로 해석하거나 보고 예약을 중지하지 않는다.
## 최종 UI 검증 결과

- production build **63 modules / 24.15초 / 종료0 PASS**.
- UI adapter **32/32 PASS / 1129.7804ms** (새 Job 현재계보7 + 기존25).
- MapLibre 포함 큰 JS chunk 경고는 남는다. 이 기록은 브라우저 실제 연결·성공 과학계보 인수를 대신하지 않는다.


## Root 실제 읽기 UI 확인

UI5174→API8002에서 기존 Job job-00893a5fc1014e4db9eea3d8a7fa238f의 제출기록LEGACY와 현재계보BLOCKED/DATASET_VERSION_NOT_FOUND를 별도로 확인했다. 명시버튼 전에는 현재결과없음, 클릭후범위/KST검사구간·시도≠전체성공·승인없음·입력↔진단연결/차단코드 표시를 확인했다. Job ID변경시이전상태/현재결과가즉시제거되고 다른 기존Job상태조회에도현재검사를자동실행하지않았다. desktop1440×1000/mobile390×844(문서375px<viewport390px)확인후viewport복원. evidence/integration/job-lineage-live-20261017.json와evidence/ui-20261017/job-current-lineage-*.png근거. 보호5SHA·기존2JobSHA불변/신규실행0,실제성공계보/과학모델실행검증아님.
