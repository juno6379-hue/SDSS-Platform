# Workflow 입력의 현재 전이 계보 읽기 UI

## 2026-10-17 — Workflow 입력 전달 수동 API·UI 연결 (87/88)

순수86을 독립 내부 RFC `POST /v1/workflows/node-input-handoff`와 GeoQuery 실행계획 검토의 ‘Workflow 노드 입력 전달 선언 검사’에 연결했다. API는 원 Workflow/제안metadata JSON 문자열2개·caller canonical pin·명시 node_id의 정확4키를 받는다. 엄격UTF8·중복키/nonfinite/float·int32·원문별512KiB/전체1MiB·깊이/atom 한도 검사 후86을1회 호출한다. wrapper 전체 수신 rawbody SHA와 내부 canonical pin은 범위가 다르다. 고정400/413/503·no-store/기존인증을 유지하고 raw본문/URI/ID/예외를 응답하지 않는다.

UI는 원 planJson을 보존하며 node/제안metadata를 직접 입력하고 버튼을 눌러야만 검사한다. 기존 계획·현재 계보와 별도 상태이며 편집/node/proposal/revision/route/back/unmount가 이전 응답을 폐기한다. 전체요청 SHA·canonical pin·안전형식/indices/count/20false7IO0를 검증하고, Python/JS Unicode canonical fixture로 프로토콜을 대조했다. 기존 반환 plan.nodes 요약에서 원문을 재구성하지 않는다.

실제 로컬 HTTP와 브라우저에서 합성 caller선언의 MATCH/변조BLOCKED·미확인계수·원문검사·기존조회독립/뒤로가기를 확인했다. 이는 운영 Workflow/Job 전달의 검증이 아니다. MATCH는 완성Job/AOI/output/선행Result/DAG/원본인증/기관ACL/과학/학습/실제executor 승인을 부여하지 않는다. 신규 비교의 I/O0와 기존 plan/lineage의 Registry진단은 별도 범위다. 사용법·계약·시험/한계는 [API87](87_workflow_node_handoff_api.md)·[UI88](88_workflow_node_handoff_ui.md)를 따른다. 실제 Job 생성·실행·capture역채움은 없다.

기준일: 2026-10-17, Asia/Seoul. 상태: 지속 개발 중. 내부 RFC의 요청 시점 읽기 진단이며 기존 실행계획·정책·단독 입력 진단이나 제출 snapshot을 대체하지 않는다. 실제 DAG/Job 실행·등록·기관 권한·과학 승인 없음.

## 변경 파일과 사용법

- `frontend/src/GeoQuery.tsx`: 기존 계획 JSON/버튼/정책 진단을 보존하고 독립 현재 계보 컴포넌트를 연결했다. 기존 inspectPlan의 늦은 응답도 JSON 본문 key·요청 세대·Workflow ID/Trace로 방어한다.
- `WorkflowLineageDiagnostics.tsx`, `workflow-lineage-diagnostics.css`: `Workflow 입력의 현재 계보 읽기 검증` 명시 버튼·별도 현재 검사 카드·노드/입력/공유 진단·예산·차단 표시.
- `workflowLineageAdapter.ts`, `.test.mjs`: POST 바이트 해시·신원/계약·binding 일치·계획 차단 유지·노드/한도/현재 집계·경합 검사.
- GeoLLM Assistant → 실행계획 검토에서 실제 Workflow JSON 초안을 입력하고 기존 계획 검토 또는 현재 계보 버튼을 각각 누른다. 현재 계보 버튼은 JSON 형식·Workflow ID·Trace·노드가 없으면 비활성이다.
- 현재 검사만 `POST /v1/workflows/lineage-validation`을 호출한다. 화면 진입·JSON 수정·상태 polling에서 자동 해시/조회/Job 실행을 추가하지 않는다.
- JSON·질의 메뉴·초기 메뉴 context 변경 시 계획·현재 계보·오류/busy를 초기화하고 요청 세대를 무효화한다. JSON 초안의 session 보존은 유지한다. 같은 JSON으로 되돌아가도 이전 요청 세대는 거부한다.
- 기존6개 모델 PNG·대시보드·카탈로그 배치와 Job/snapshot UI/backend/원문계약/실자료는 변경하지 않는다.

## 정확한 요청 신원

브라우저의 agentApi는 `JSON.stringify(parsedPayload)`를 실제 요청 body로 보낸다. UI는 **같은 문자열을 TextEncoder UTF-8 바이트로 바꾸고 WebCrypto SHA-256**을 계산하여 응답 request_sha256과 비교한다. 키를 정렬하는 canonical hash나 원본 textarea의 들여쓰기/공백이 포함된 문자열 hash가 아니다.

Workflow ID·Trace·실제 POST body SHA가 모두 일치해야 표시한다. JSON을 편집하는 동안 hash 계산/HTTP가 늦게 끝나도 요청 세대와 현재 본문 key가 다르면 요청 진행 또는 결과 표시를 거부한다. 기존 plan endpoint에는 server request_sha256 필드를 새로 넣지 않고,해당 응답의 Workflow ID/Trace와 로컬 요청 key·세대만 검사한다.

## 계획과 현재 계보의 구분

- 새 wrapper extension은 `greenblue.workflow-lineage-validation.rfc1`,INTERNAL_REVIEW/upstream:false이며 scope는 `CURRENT_WORKFLOW_TRANSITIVE_LINEAGE_PLAN_ONLY`다.
- wrapper의 **mode는 PLAN_ONLY,status는 항상 BLOCKED,execution_started/can_execute는false**다. 개별 Dataset 계보가 INTEGRITY_VERIFIED이거나 lineage_integrity_verified=true여도 Workflow 실행 성공으로 표시하지 않는다.
- 현재 카드에 전체 계획 차단과 별도로 계보 무결성 보고·현재 자산 resolve 시도·기관/실행/과학 승인false를 표시한다. current_assets_revalidated는 시도 여부이며 전체 성공이 아니다.
- 노드별 input_bindings를 실제 요청의 node_id/index/고정id·version·sha와 대조하고,공유 diagnostic_index의 root_ref도 확인한다. 다른 노드의 동일 고정 참조는 재사용으로 표시한다.
- 서로 다른 노드의 같은(id,version)/다른SHA 상충은 서버의 전역 사전 차단 보고를 그대로 표시하며 임의 hash/등록으로 해결하지 않는다. 서로 다른 고정 버전 T1/T2는 상충으로 추정하지 않는다.
- 빈 입력 노드 INPUT_REFS_REQUIRED,상충으로 실제 진단이 비어 있는 정상 보고,checked=false 미검사,부분 총예산 소진을 통과로 채우지 않는다. checked는 수행 여부이며 성공이 아니다.
- 가용=false/CHECK_LIMIT_REACHED의 선행 상한 차단과 가용=true/CHECK_LIMIT_REACHED 부분 결과를 구별한다. 전체 공유 한도는 Workflow노드128,입력64,고유루트32,깊이32,루트당노드64,총노드256이다.
- HTTP400 형식/DAG 오류,503 서비스 불가,404 API 연결,401/403 인증을 구별하며 raw 오류/제한 경로·URI를 노출하지 않는다. 원본 JSON은 기존 안전 details로 유지한다.

## 의미 시험과 증거

- 신규 adapter6시험:UTF-8 실제 body/키순서 hash,Workflow·Trace·body SHA,공유 ref/빈 노드/상충 무해시 진단,계보 일치여도 PLAN_ONLY/BLOCKED·승인false,선행/부분 한도·노드 순서·고정 ref,JSON/메뉴/복귀 경합 guard.
- 기존 UI32시험과 합계38시험을 실행한다. fixture 시험 상태는 TESTED_SYNTHETIC이다.
- build/시험 로그: `evidence/integration/workflow-lineage-ui-build-20261017.log`.
- root가 완료 소스·최종 로그·실제 검증·이 문서41을 understanding_agent에 전달하여 해설·발표·FAQ·INDEX를 갱신한다. UI 단위 완료를 전체 개발 완료로 해석하거나 보고 예약을 중지하지 않는다.

## 실제 API·브라우저 근거

root/integration의 VERIFIED_REAL 범위는 **미등록 참조를 가진 실제 요청의 읽기 차단 진단과 화면 표시**다. 실제 과학모델 성공·기관ACL·운영 승인을 뜻하지 않는다.

- 공유 참조2노드+빈 입력1노드 계획을 명시 조회했다. CURRENT_DIAGNOSTIC/PLAN_ONLY/BLOCKED,본문 SHA 일치,공유 진단1개/검사비용1,종속 입력 reused=true,빈 입력 INPUT_REFS_REQUIRED 표시를 확인했다.
- desktop1440×1000/mobile390×844에서 문서폭375<390을 확인하고 viewport를 복원했다. JSON 변경 시 결과 즉시 제거/잘못된 JSON 버튼 비활성,원래823자 초안의 DOM 정확 복원을 확인했다.
- CLI200/400cycle/400NaN,no-store/raw SHA 일치,보호5SHA 및 기존2Job SHA 불변: `evidence/integration/workflow-lineage-live-20261017.json`.
- 실제 화면: `evidence/ui-20261017/workflow-current-lineage-desktop.png`, `evidence/ui-20261017/workflow-current-lineage-shared-desktop.png`, `evidence/ui-20261017/workflow-current-lineage-mobile.png`.

## 최종 UI 검증 결과

- production build **66 modules / 19.37초 / 종료0 PASS**.
- UI adapter **38/38 PASS / 961.1713ms** (신규 Workflow현재계보6 + 기존32).
- MapLibre 포함 큰 JS chunk 경고는 남는다. 실제 API·브라우저 근거와 합성 adapter 시험의 범위를 구별한다.
