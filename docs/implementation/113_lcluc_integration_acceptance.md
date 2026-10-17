# 113. LCLUC 우선 통합 수락 조건과 Ollama 연결 현황

## 116·117 후속 상태 — 명시 실행 API·화면 연결 완료

[116 API](116_lcluc_workflow_api.md)와 [117 UI](117_lcluc_workflow_ui.md)에서 115 코어를 수동 제출·상태/보고서 조회·검증 산출물 다운로드에 연결했다. 임시 합성 자료의 실제 CPU 실행과 기존5174/8002 반영은 검증됐으며 운영 실행은0이다. 아래 API/UI 미연결·미착수 표현은 당시 이력이다. 현재도 독립 정확도·공식 GMAIS Result·운영 배포 인수·6밴드 per_scene·선택 변화쌍 지도 연결은 미완료이며, GeoLLM 서비스의 기존 NO-LLM fallback은 그대로다. 최신 시험·보존·후속은 인계서와116·117을 따른다.

## 115 후속 상태 — 로컬 CLI 실행 연결 완료, API/UI는 후속

[115 구현·검증](115_lcluc_workflow_executor.md)에서 고정 Registry·배포/독립평가 metadata·실파일 검사를 거친 LCLUC 로컬 실행 코어와 명시 CLI를 추가했다. 생성 영상·시험용 승인 metadata의 TempStore에서 실제 TinyUNet CPU 시계열·변화·전환행렬·보고서·7개 artifact SHA를 검증했고 운영 실행은0이다. 기존 아래 '미착수/PLANNED'는113/114 조사 당시의 이력이며 최신 내부 코어 상태는115를 따른다. global-only boundedtile 코어가 완료됐지만6밴드 per_scene 보정/구름mask·API/UI·GMAIS Result·generic DAG·실제독립평가/배포 인수는 미완료다. 현재 운영 Draft/QA차단/기관권한을 우회하거나 Ollama/RAG를 앱에 연결한 변경은 아니다. 전체 시험·보존·이해자료와116 후보는 최신 인계서를 따른다.

상태: **읽기 전용 조사 / 내부 실행 연결 PLANNED / 운영·과학 승인 BLOCKED**. 2026-10-18 현재 소스·로컬 프로세스·리스너를 읽었다. 이 조사에서 소스·설정·원본·DB를 수정하거나 endpoint를 호출하지 않았다. Ollama 설치·모델 pull·생성 요청·클러스터 접근·배포·새 QA/학습은 실행하지 않았다. LCLUC 실행 연결은 후속 PLANNED이며 아직 착수하지 않았다. 사용자 우선순위에 따라 GeoLLM 기술 검토를 먼저 수행한다. 이후 완료 여부는 해당 코드·시험·실제 근거로 갱신한다.

## 핵심 판정

LCLUC의 수집·학습·평가·추론·변화/시계열 계산과 로컬 승인 상태 API는 있다. 그러나 현재 모델은 Draft·독립 평가 미완료이며 후보 준비성은4차단이다. GMAIS Job 제출은 항상409 BLOCKED, Workflow는PLAN_ONLY다. 따라서 여섯 화면이 있다는 사실과 LCLUC의 실제 오케스트레이터 연계 완료를 같은 것으로 말할 수 없다.

Ollama 서버 프로세스와11434 리스너는 실제로 있다. 반면 조사한 앱 실행 소스·compose에서 Ollama endpoint 설정·호출은 찾지 못했다. 현재 `/api/query`는 정형 읽기 패턴이고 GeoQuery는 NO-LLM FALLBACK을 명시한다. **서버 실행 중 / 앱 미연결**로 구분한다. 설치 모델 목록·생성 성공·앱의 Ollama 호출 이력은 검증하지 않았다.

사용자가 확인한 외부5개 API/SDK/실행 코드 미제공·미연결과 독립 정확도 검증 라벨 미제공은 외부 차단이다. 기존 약한 라벨 학습 입력은 보존되며 독립 평가 정답과 동등하지 않다. 외부 자료 위치를 반복 질문하지 않고 LCLUC 내부 통합을 우선 진행한다.

## 현재 수준과 코드 근거

| 범위 | 현재 구현 | 미완료·수락 조건 |
|---|---|---|
| 모델·데이터 준비 | 고정 Dataset Registry·입력/계보·후보 생성/stage/실제QA·class부족 산술 | 후보1095패치/4차단을 해결한 새 적격자료와 QA, 독립 검증 라벨 필요 |
| 로컬 ML 실행 | `ml/service.py` prepare_dataset/train_model/infer_raster/analyze_change/analyze_timeseries/evaluate_model | 현재 자료·모델의 운영 실행 승인은 없음. helper 구현과 실자료 과학 성능을 구분 |
| 로컬 모델 승인 | `lifecycle.py`, main의readiness/transition/evaluate/deploy. 현재체크포인트와독립평가해시확인 | 독립평가와검토근거없는전이거부. deploy는로컬레코드포인터전환이지K8s rollout아님 |
| 기존 로컬 분석 API | `/api/inference`,`/api/timeseries`가Deployed를요구하고worker시점재확인. `/api/change`는기존로컬자산분석 | GMAIS고정입력/trace/멱등Workflow와실행worker사이에별도연계필요 |
| GMAIS·Workflow | gmais_api.submit_job409·입력snapshot/capture,plan_workflow의PLAN_ONLY/BLOCKED와실행false | genericDAG executor/승인실행/동적선행Result연결없음. 새localLCLUC scope로연결분리 |
| SDSS 결과 | `/api/analyses/{id}/map-data`,report, `sdss_results.project_result`의검증투영 | 기존map_data는top-levelGeoJSON만취급. 시계열의changes[pair]선택투영필요; standardResult인증자동생성금지 |
| 모니터링 | 로컬jobs상태·execution근거·health/ready·수집진행조회 | Prometheus/Grafana·드리프트·MLflow운영연계와알림/UAT증거없음. dashboard도후속대상명시 |
| API 보안 | main전역optionalBearer·localhostcomposebind·입력/경로/SHA/자원진단검사 | 기관RBAC/자료ACL·공유배포정책·보안검증/UAT 별도. PUBLIC진단≠기관권한인증 |
| Docker/Kubernetes | Dockerfile·composeAPI1개와원규격K8s Deployment/Job templates | templates의REPLACE_WITH_REAL_DIGEST·namespace/RBAC/GPU/storage/networkpolicy확정필요. 도구설치≠staging배포 |
| GeoLLM/Ollama | 앱질의는정형읽기,로컬Ollama실행관측 | endpoint설정/모델선택/응답JSON제약·timeout/fallback·실제연결시험미구현. 임의도구실행허가금지 |

## 가장 작은 실제 연결 — Root의 LCLUC 전용 실행 방향

기존 genericDAG를 한 번에 실행 가능하게 바꾸기보다 **고정 모델·연차 입력을 받는 로컬 LCLUC 시계열 Workflow 한 경로**를 연결한다. 후속 후보 `/v1/lcluc/workflows`와 서비스는 PLANNED·아직 미착수이며 아래는 수락 기준이다. GeoLLM 기술 검토가 현재 우선이다. 새 진단만 추가하는 범위가 아니라 gate를 만족한 임시 fixture에서 기존 `analyze_timeseries`를 실제 호출하는 연결이어야 한다.

1. LCLUC capability·고정model_ref·정렬된연차별input_ref·trace·idempotency를검증한다. 원문caller경로를실행payload로직접쓰지않고Registry가검증한manifest의로컬자산만선택한다.
2. 입력은현재resolve로id/version/assetSHA·manifestSHA를확인하고품질VALIDATED·PUBLIC조건을구분한다. 외부모델요청·부족근거는실행전차단하고runner호출0을시험한다.
3. 모델은고정ID/버전선언/checkpointSHA·Deployed·현재해시에결합된독립평가를재확인한다. caller model_version_declaration을기관권위/immutable모델resolver인증으로승격하지않는다. dataset_version대체/역채움도없다.
4. 같은요청의단일실행claim을DB트랜잭션·고유키로확보한뒤파일부작용을시작한다. 기존 Store.put은INSERT OR REPLACE이므로get→put만으로동시멱등을보장하지못한다. 같은key다른요청충돌·실행중중복·실패자동재시도없음·재시작미완료상태를명시한다.
5. 실제runner는기존analyze_timeseries를재사용한다. 함수는모든연차grid를선검사한뒤실제추론·변화지도·timeseries.json을쓴다. 실패부분파일은보존하고성공으로복원하지않는다. 모델배포/파일변경의재확인은가능한한실행직전에하며TOCTOU/원자snapshot무보장을명시한다.
6. 로컬Workflow/analysis/trace/출력파일SHA를연결해상태조회·선택변화쌍지도·보고서를같은실행근거로읽는다. timeseries상위report에는top-levelgeojson_path가없으므로changes[pair]선택을별도투영한다. 표준GMAISResult/전이계보/기관인증전체완료로과장하지않는다.
7. UI에는LCLUC만연결하고수동입력/실행·차단/대기/실행중/실패/완료·이동세대·같은trace/result탐색을반영한다. 원자료/현재Draft모델로실제운영실행하지않고격리TempStore의합성래스터/명시mock평가경계로시험한다.

### 필수 시험

- 승인/독립평가/Deployed·checkpoint불일치·입력SHA/manifest/품질/ACL차단에서runner0,DB/원자료기록의허용범위확인.
- 고정TinyUNet·두개이상작은연차영상의실제시계열runner출력·classifications/changes/report파일·trace연계. 독립평가는fixture의명시mock이며실제정확도승인아님.
- samekey같은요청1회실행/변경요청충돌/동시호출/실패후미재시도·출력경로탈출·부분파일보존·현재gate재확인.
- 기존gmais409/WorkflowPLAN_ONLY/API호환유지,신규로컬scope표시·새화면실제브라우저및모바일검증범위구분.

## Ollama 로컬 관측과 연결 수락 조건

로컬 조회에서 `ollama app.exe` PID27268·`ollama.exe` PID27860, `[::]:11434`의소유PID27860을확인했다. PATH의ollama.exe도확인했다. 그외실행중개발listener는5173/PID30944·5174/PID15608·8000/PID32224·8001/PID26912·8002/PID35032다. 이는조사시점의소켓/프로세스관측이며HTTP생성성공이나앱연결증거아니다.

`backend/app`,`frontend/src`,`scripts`,`compose.yaml`의실행코드에서정확한Ollama명·OLLAMA설정키·localhost/127.0.0.1:11434의명시호출을검색했다. 현재main.query는모델/분석저장기록을읽는predefined-pattern이고GeoQuery문구는LLM·정책RAG미사용을명시한다. 설치모델확인·/api/tags·/api/generate·/api/chat·모델pull은호출하지않았다.

후속연결은명시endpoint와모델설정·개별enable·timeout/응답크기·구조화응답검사·정형fallback·LLM이아닌서버의실행gate를갖춘다. 자연어를임의Python/SQL/셸로실행하거나LLM출력만으로수집·학습·모델승인을허용하지않는다. endpoint연결검사·모델존재·실제질의성공·fallback은각각별도수락근거로남긴다.

## MLOps·운영 인수의 순서

1. 현재LCLUC로컬gate와실행연결을격리시험+UI까지완료한다.
2. class7자료/실제QA·훈련·독립정답평가·검토승인을확보한범위에서실자료E2E를수행한다. 약한라벨평가를독립승인으로대체하지않는다.
3. 권한·비밀관리·오류/감사/경로노출·동시성·장애복구와입력자원한도를인수한다. 현재optionalBearer가기관RBAC완료를뜻하지않는다.
4. 실제image digest·namespace·RBAC·storage·networkpolicy·CPU/GPU정책의K8sstagingmanifest와rollout/rollback·health/로그·metrics를검증한다. 템플릿이나kubectl/docker설치만으로완료하지않는다.
5. PM/분야담당과AOI·연도·분류체계·지도/전환행렬/통계/보고서·대기/실패/취소·버전/trace·모바일/성능·접근권한의UAT수락결과를남긴다. 클러스터/기관책임·계정/망·독립라벨미확보는외부BLOCKED로명시한다.

## 읽은 근거와 조사 한계

소스: `backend/app/main.py`,`gmais_api.py`,`lifecycle.py`,`ml/service.py`,`store.py`,`dataset_registry.py`,`map_data.py`,`sdss_results.py`,`frontend/src/GeoQuery.tsx`,`frontend/src/api.ts`,`compose.yaml`,`backend/Dockerfile`,`contracts/upstream/GMAIS-v0.2/kubernetes/*.template.yaml`.

기존 근거: `docs/implementation/109_area_completion_audit.md`, 사용자 확인 `evidence/integration/recovery-commit-contract-external-dependencies-20261017.json`, `tests/test_mlops_sdss_flow.py`의격리성공과명시mock평가설명. 이번조사에서시험을새로돌리지않았고기존시험코드읽기를새PASS로표현하지않는다. Docker/kubectl의PATH존재는확인했지만클러스터context/daemon/배포/보안/UAT를실행하지않았다. 환경변수비밀이나전체프로세스명령줄은출력하지않았다.
