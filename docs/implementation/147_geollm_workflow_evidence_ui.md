# 147 — GeoLLM 근거 화면에서 local LCLUC workflow 보고서 검토

상태: **TESTED_SYNTHETIC — 신규 프론트 집중·독립 API·전체 프론트/build·실제 main Temp 브라우저 검증 완료.** 운영 모델의 승인·독립 라벨 확보·정책 RAG·LLM 연결 완료가 아니다.

## 실제 연결한 공백과 사용법

기존 GeoQuery 근거 질의는 `/api/query`와 legacy `analyses` ID를 사용한다. 새 local LCLUC workflow는 별도 namespace이며 기존 `LclucWorkflowPanel`에서만 보고서를 조회할 수 있었다. `GeoQuery`의 근거 분기에 새 `GeoWorkflowEvidence` child를 연결해 사용자가 명시한 64자리 소문자 hex workflow ID의 저장 기록과 보고서를 읽는다. 기존 question·analysis 선택·`onReviewResult(analysisId)` 경로는 보존하며 workflow ID를 legacy 분석 ID로 전달하지 않는다.

GeoLLM 화면의 **결과·모델 출처 설명 · 정형 읽기**에서 **Local LCLUC workflow 근거 조회**를 연다. 빈 ID 칸에 실제 고정 ID를 입력하고 **기록·보고서 읽기**를 누른다. 자동 ID 추정·드래프트 전달·자동 조회·POST·polling·재시도는 없다. 보고서가 검증된 뒤 **동일 workflow 지도·행렬 검토**를 수동으로 열고 변화쌍을 선택한다. 기존 `LclucWorkflowChangeMap`이 같은 receipt/raw report로 `LclucTransitionSummary`를 포함해 보여주며 지도 자산 GET은 기존의 별도 버튼에서만 발생한다.

## 읽기·결합 계약

새 client는 `API_BASE`와 현재 페이지에서 얻은 API origin의 `/v1/lcluc/workflows/{id}`와 `/report` 두 경로만 GET한다. 기존 `sessionStorage.geoai_token`의 Bearer 인증, `cache:no-store`, `redirect:error`, AbortSignal을 사용한다. status가 200인 경우에만 bounded body를 파싱한다. HTTP 실패의 원문 메시지·detail·경로는 표시하지 않고 고정 한국어 안내로 바꾼다.

각 응답은 declared Content-Length와 누적 stream bytes를 모두 **8MiB**로 제한한다. 한도 초과나 오래된 응답은 reader를 cancel하고 lock을 해제한다. strict UTF-8 decode 후 중복 JSON key(escaped key 포함), 비유한 수, 정밀도를 잃는 정수, 잘못된 surrogate, 깊이32·node262144·문자열1MiB 초과를 거부한다. 이 한도는 브라우저 전체 CPU/RSS/시간 SLA나 서버 파일 접근 sandbox 보장이 아니다.

기존 `workflowResponse(...,{readOnly:true})`를 재사용하여 요청 ID와 동일한 exact receipt·명시 `replayed:true`·과학/표준 false를 확인한다. **RUNNING/FAILED는 status만 표시하고 report GET을 하지 않는다.** SUCCEEDED에서만 normalized report_path와 일치하는 유일 artifact SHA를 선택한다. Windows 역슬래시 경로는 비교 시에만 정규화하고 원문 report_path의 기존 parser 계약은 유지한다.

보고서 raw bytes의 SHA-256을 그 artifact pin과 대조한 뒤 기존 `parseWorkflowReport`로 모델 checkpoint SHA·보고서 경로·연도를 결합한다. 모든 변화쌍에 기존 `workflowTransitionStats`의 클래스/9×9 행렬/개수/면적/순변화 검산을 적용한 뒤 하나의 receipt+report+rawReport+SHA 묶음으로만 화면에 게시한다. SHA/형식/집계 실패는 이전 결과를 비우며 숫자·도형을 보충 생성하지 않는다. 값이 0인 실제 변화쌍은 측정된 0으로 유지하고 누락·실패를 0으로 바꾸지 않는다.

## 상태·이동·표시 범위

`WorkflowEvidenceFlight`의 동기 pending gate가 연속 클릭의 중복 전송을 막는다. ID 편집·새 읽기·명시 표시 중단·hash/popstate·unmount는 receipt/요약/지도/오류를 비우고 세대를 무효화하며 전송을 abort한다. parse/SHA 이후에도 live 상태를 다시 확인한다. 예전 success/error/finally가 새 화면에 붙거나 새 요청의 busy를 내리지 않는다. 표시 중단은 서버 실행 취소·rollback 명령이 아니다.

Workflow ID·Trace·고정 모델 ID/버전/checkpoint SHA·관측 연도·보고서 원바이트 SHA·실제 변화 요약을 표시한다. `LOCAL_LCLUC_WORKFLOW_ONLY`, 과학 정확도 인증 false, 표준 GMAIS Result false를 함께 보여준다. 저장된 성공 이력을 읽는 것은 현재 모델 배포/기관 권한을 재심사한 결과가 아니다. LLM 응답 생성, 정책 RAG/RDTR, 임의 코드·SQL, 실행 승인이나 새 분석을 추가하지 않는다.

## 변경 범위와 검증

새 UI/adapter/client/scoped CSS/집중 시험을 추가했다. 기존 `GeoQuery.tsx`는 import와 evidence 조건부 mount 두 조각만 추가하고 CRLF를 유지했다. backend/main/API와 기존 workflow adapter/client/map/transition 구현은 수정하지 않았다. 지도 스타일은 별도 wrapper에서 기존 scoped CSS를 그대로 재사용하고 신규 패널의 focus·표·모바일 overflow 스타일만 추가했다.

집중 `node --test src/geollmWorkflowEvidenceAdapter.test.mjs`: **9 PASS / 0 FAIL / 0 SKIP / 588.3648ms / exit0**. 원로그는 `evidence/integration/geollm-workflow-evidence-ui-focused-20261018.log`다. redirect 제한 보강 전 첫9 PASS/435.8917ms 로그는 `...-focused-initial-20261018.log`로 원바이트를 보존했다. 새9건과 초기9건은 중복이므로 합산하지 않는다.

검증에는 저장된 과거 합성 CPU fixture의 receipt/report를 복사하여 report bytes SHA를 고정한 adapter 시험, 명시 mocked fetch/Bearer/GET 경로, RUNNING/FAILED 1GET, HTTP 실패 원문 비누출, stream 한도/cancel, 세대·route·unmount·old finally, 중복 키/Unicode/수치·모델/연도/행렬 오염을 포함한다. 이는 이번 단위에서 운영 추론을 실행한 것이 아니다. 실제 authenticated HTTP·화면·전체 프론트/build는 아래 별도 근거와 구분한다. 운영 collector/Registry/원장·예약·학습/모델 변경은 없다.

독립 `geollm-workflow-evidence-independent-20261018.py/json/log`는 **7 PASS / 0 SKIP / 5.5723868초 / exit0**다. 새 실제 Temp 3년 GTiff와 hand-set untrained TinyUNet의 CPU 추론3회로 만든 workflow1건, 명시 모의 승인 metadata를 사용했다. RUNNING/FAILED 행은 별도로 구성한 과거상태 metadata이고 실제 장기 작업 실행이 아니다. 기존 main auth AST와116 router의 인증·raw report SHA·Trace/model/연도/3변화쌍·401/404/409·파일변조503을 대조하고 GET 중 dispatch/put0·DB/files 불변을 확인했다. 이는 actual main 서버를 켠 브라우저 시험과 별도이며 운영 추론·학습·기관 승인·LLM/RAG 호출은0이다. 독립 담당의 UI6파일 SHA 대조와 읽기 교차검토에서 추가 차단 지적은 없었다.

Root 전체 프론트 `geollm-workflow-evidence-root-frontend-20261018.log`는 **280 PASS / 0 SKIP / 25.2827483초**이며 `geollm-workflow-evidence-build-20261018.log`는 TypeScript 검사와 **116 modules / 23.55초** 빌드 완료를 기록한다. 기존 큰 bundle 경고는 남아 있고 성능/SLA 개선을 인증하지 않는다. Root의 기존 backend 관련 회귀는 `test_lcluc_workflow`와 `test_lcluc_workflow_api`의 **34 PASS / 20.542초 / exit0**다. backend source 변경0이므로 이번 전체 backend는 재실행하지 않았으며145의 전체1431 PASS/1 SKIP는 이전 이력이다. 집중/독립/전체 묶음은 겹치므로 합산하지 않는다.

## 실제 브라우저와 실행 중 서버 적용

Root는 별도 브라우저 탭의 Vite5180에서 실제 main을 실행한 Temp8003에 연결해 인증401, 성공3변화쌍, 수동 지도1 polygon과9×9 전이행렬, ID편집 시 이전 표시 제거, RUNNING/FAILED, 없는ID404, 표시 중단·비우기, 메뉴 이동/뒤로 가기와 기존 질의 초안 보존을 확인했다. 근거는 `geollm-workflow-evidence-browser-dom-20261018.txt`, `geollm-workflow-evidence-browser-20261018.png`, `geollm-workflow-evidence-map-browser-20261018.png`다. 정상 자료는 실제 Temp의 합성 래스터·미훈련 hand-set 모델·모의 승인 metadata이므로 실제 운영 분석이나 과학적 정확도 인증이 아니다.

실제 브라우저의 표시 중단/뒤로 가기 검사는 응답이 완료된 뒤 수행했다. 전송 지연을 강제로 주입한 success/error/finally 경쟁, oversized/SHA/집계 오염은 집중 시험 근거이며 브라우저에서 모두 재현한 것으로 표현하지 않는다. 모바일 화면·장치별 WebGL/접근성·동시부하/SLA는 이번 실제 화면 검증에 포함하지 않았다.

기존 실행 중5174는 처음 stale module을 반환했다. Root가 정확히 식별한 해당 Vite PID15608만 재시작한 뒤 GeoQuery 모듈 SHA가5180과 동일하고 새 child가 반영됐음을 확인했다. `geollm-workflow-evidence-applied-dom-20261018.txt`와 `geollm-workflow-evidence-applied-browser-20261018.png`는5174의 빈ID·읽기 disabled를 확인한 적용 근거다. 이 기존 운영 화면에서는 workflow GET을 수행하지 않았다. 소스/시험 반영, 실행 중 서버 적용, Temp 실제 요청은 서로 다른 검증 범위다.

Root 최종 보존 감사에서는 보호141개, 기존 tracked source434개 중 허용 GeoQuery1개 외433개 불변, 이전 evidence1439개 불변, catalog14행 및 예약136314880바이트 보존을 확인했다. 운영 수집·원장·lock·분할·모델·예약·Registry 변경은 없었다. 전체 개발은 계속 미완료이며 공식 RAG/기관 ACL·승인 모델·독립 라벨·운영 수집 및 실행 검증은 별도 후속이다.

### 09:39 KST 재확인 — 과거 브라우저 통과와 현재 API 미실행 구분

위 실제 브라우저 PASS와5174 적용은 앞선08시대 관측 이력이다. 후속 heartbeat의09:38~09:39 재확인에서는 기존 API8000/8001/8002·Temp8003과 front5174/5180이 모두 실행 중이지 않았으며 Ollama 프로세스만 남아 있었다. 종료 원인과 Temp fixture 파일 정리 여부는 확인되지 않았으므로 정상 종료·자동 정리 완료로 추정하지 않는다. Root는 Store 복구 등 시작 부작용을 피하려고 API를 재시작하지 않았다.

`geollm-workflow-evidence-dev-server-after-20261018.json`의09:39:17 관측은 **frontend5174만** detached hidden PID34484로 복원했음을 기록한다. `geollm-workflow-evidence-final-processes-20261018.json`의09:39:48 관측에는 Ollama2개와 해당 Vite만 있으며 API 미실행·운영 수집/학습 프로세스 관측0이다. 따라서 현재 frontend 제공과 이전 API 브라우저 PASS를 현재 API 가용성으로 합치지 않는다. API 미실행 상태의 조회 실패는 이전 검증을 취소하는 근거도, 현재 정상 서비스 제공의 근거도 아니다. 보고 예약 ACTIVE/10분은 수정하지 않았으며 실제 API/수집/학습 프로세스와 구분한다. 이 후속 단락은 상태 기록만 추가하며 UI 소스·시험은 변경하지 않았다.

## 인계

UI source/test 동결 목록과 집중 원로그를 Root·독립 검증 담당에게 전달했다. Root의 실제 main Temp 브라우저·전체 프론트/build·보존 결과를 위 범위로 반영했다. 완료된 코드와 실측 근거를 이해 담당에게 전달하여 쉬운 설명·발표·FAQ·INDEX·변경 이력을 같은 단위로 갱신한다. 이를 전체 프로젝트 완료나 실제 운영 성과로 확대하지 않는다.
