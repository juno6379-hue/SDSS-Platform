# 114. GeoLLM 실행 환경·RAG·도구 연계 기술 검토

## 115 후속 상태 — 로컬 CLI 실행 연결 완료, API/UI는 후속

[115 구현·검증](115_lcluc_workflow_executor.md)에서 고정 Registry·배포/독립평가 metadata·실파일 검사를 거친 LCLUC 로컬 실행 코어와 명시 CLI를 추가했다. 생성 영상·시험용 승인 metadata의 TempStore에서 실제 TinyUNet CPU 시계열·변화·전환행렬·보고서·7개 artifact SHA를 검증했고 운영 실행은0이다. 기존 아래 '미착수/PLANNED'는113/114 조사 당시의 이력이며 최신 내부 코어 상태는115를 따른다. global-only boundedtile 코어가 완료됐지만6밴드 per_scene 보정/구름mask·API/UI·GMAIS Result·generic DAG·실제독립평가/배포 인수는 미완료다. 현재 운영 Draft/QA차단/기관권한을 우회하거나 Ollama/RAG를 앱에 연결한 변경은 아니다. 전체 시험·보존·이해자료와116 후보는 최신 인계서를 따른다.

상태: **읽기 감사·별도 로컬 실응답 VERIFIED_REAL / 평가 코드 TESTED_SYNTHETIC / 후보 아키텍처 PLANNED**. 기존 GeoLLM API·UI·데이터·모델·원장을 변경하지 않았다. 이 문서는 실제 앱 연결, 서버 설치/실행, 로컬 smoke, 운영 RAG와 과학 실행을 구분한다. 초기 읽기 담당은 소스·설정·프로세스·설치파일만 조사했고, Root가 별도 수행한 생성/embedding HTTP의 결과·실패·한계와 공식 자료는 아래 최종 측정 절에 기록했다. 모델 pull·DB접속·패키지 설치는 수행하지 않았다.

## 현재 결론

**프로젝트 앱은 현재 LLM을 사용하지 않는다.** `/api/query`는 한국어 단어 조건으로 모델/분석 기록을 조회하는 `predefined-pattern`이다. 이는 실제 SQLite 기록을 읽는 결정적 기능이며 LLM mock 응답이라고 부르지 않는다. GeoQuery는 NO-LLM FALLBACK과 LLM·정책 RAG 미사용을 표시한다.

반면 로컬 Ollama는 실행 중이며 설치된 모델도 있다. 설치·서버 응답과 앱 provider 연결은 다르다. Qwen3:8b는 설치되지 않아 이번 동일 비교에서 실행 결과를 만들지 않고 N/A로 둔다. 후보 Qwen3:8b+Ollama+BGE-M3+PostGIS를 현재 완성 구성으로 표현하지 않는다.

## 실제 코드·설정 감사

| 항목 | 읽은 사실 | 판정 |
|---|---|---|
| 현재 LLM명/버전/provider | main.query에 모델명·provider·LLM client·호출 없음 | 앱에서 사용하는 LLM 없음 |
| 질의 처리 | 모델 정확도/버전→Store.list(models),변화/면적+analysis_id→Store.get(analyses),나머지 안내 | 실제 정형 읽기·LLM 추론 아님 |
| Ollama/vLLM client | 실행 소스에서ollama/vllm/qwen/embedding/retriever/tool_call 연결 미발견 | 앱 endpoint·모델 선택·호출 미연결 |
| frontend | GeoQuery가 /api/query와사용자수동 /v1/workflows/plan/계보/초안진단을명시호출 | LLM의도추출/동적toolcalling 아님 |
| 필수 backend 의존성 | fastapi/uvicorn/numpy/rasterio/pyproj/torch/httpx/jsonschema | httpx존재만으로 LLM통합 아님 |
| optional 의존성 | earthengine-api/mlflow/psycopg/matplotlib | requirements목록은설치·서비스·연동완료증거 아님 |
| compose | api서비스1개·로컬8000bind·data volume·API토큰/CORS설정 | Ollama/vLLM/Postgres/vectorDB서비스선언 없음 |
| frontend.env.example | VITE_API_BASE·VITE_FIXTURE_MODE | provider/embedding설정 없음 |
| 셸 환경 | OLLAMA_HOST변수명 존재,앱은이를읽지않음 | 조사셸변수≠앱/daemon환경적용;값·비밀미출력 |
| 영속DB | Store는catalog.sqlite3의records테이블·JSON body | PostGIS/vectorDB가앱DB로연결된것이 아님 |
| RAG | 문서chunk·embedding생성/적재·vector검색·retriever·reranker·출처결합코드 미발견 | 생산RAG 미구현 |
| 도구/오케스트레이터 | genericGMAIS Job409BLOCKED/WorkflowPLAN_ONLY,수동metadata진단,기존로컬ML API별도 | LLM toolcalling·실제DAG실행 미연결 |

검색 범위는 backend/app·frontend/src·scripts의실행소스,compose,requirements다. 전체PC의모든환경이나비공개외부서비스부재를증명한것은아니다. 현재조사Python환경의metadata조회에서도ollama/vllm/transformers/sentence-transformers/FlagEmbedding/langchain/llama-index/chromadb/qdrant/psycopg/pgvector/mlflow는미발견이었으나,별도daemon·다른interpreter의설치여부와구분한다. backend필수코드가이패키지를사용하지않는다는판정은소스근거다.

## Ollama 설치·실행·모델 관측

작성자의 로컬 관측은 ollama app.exe PID27268·ollama.exe PID27860과[::]:11434소유PID27860,PATH ollama.exe다. Root의 별도실측 전달은Ollama0.40.5·초기/api/ps=[]와아래/api/tags다. 초기로드0은설치0이나사용불가를뜻하지않는다.

| 설치 태그 | Root 전달 모델 메타데이터 | 현행 앱 사용 |
|---|---|---|
| qwen3.5:4b |4.7B·Q4_K_M·약3.389GB·digest2a654d98…4eefd |미연결|
| qwen2.5:1.5b |Q4_K_M·약0.986GB·digest65ec…dc57b |미연결|
| bge-m3:latest |566.70M·F16·약1.158GB·1024차원·8192context·digest790764…6bab |미연결|
| gemma2:latest |9.2B·Q4_0·digestff02…db0b |미연결|
| qwen3:8b |미설치·pull미수행 |후보/N/A|

태그·압축 용량은관측메타데이터다. 모델성능·실제RAM/VRAM·지연이나프로젝트적합성을추정하지않는다. latest태그는관측digest와시점을함께저장해야재현할수있다. LCLUC고정model_ref의권위인증과LLMruntime모델태그관측은서로다른계약이다. Root의chat/임베딩smoke는실제서버호출이더라도생산앱연결·RAG운영인증이아니다.

## PostgreSQL·PostGIS·pgvector 설치와 앱 사용 분리

인증정보검색·암호추정·DB접속없이서비스/리스너/설치파일만읽었다.

- postgresql-x64-15 Running서비스PID5256→postgres PID8104/5432.설치postgres.exe ProductVersion15.14.
- postgresql-x64-18 Running서비스PID5296→postgres PID7708/5433.설치ProductVersion18.3.
- 5432/5433은[::]와0.0.0.0 listener관측이다. 실제기관망접근권한/방화벽/인증·보안수락은검증하지않았다.
- PostgreSQL18의share/extension에postgis.control·raster/topology/sfcgal/tiger control파일이있고postgis default_version3.6.2다.15/18의해당extension설치디렉터리에는vector.control이없었다.
- psql/pg_config는현재PATH에서미발견이다.설치bin에실행파일이있을가능성과DB접속가능여부는별도다.

**PostGIS설치파일존재≠DB별CREATE EXTENSION활성≠프로젝트연결**이다. pgvector도설치control관측범위밖의다른서버/경로까지전역부재라말하지않는다. 기존앱은SQLite이며이조사에서DB를만들거나확장을활성화하지않았다.

PostGIS는경계/AOI/공간관계저장·질의역할이다. 벡터유사도검색에는pgvector같은별도기능과테이블/인덱스/retriever구현이필요하다. PostGIS만설치하면BGE-RAG가동작한다고설명하지않는다.

## 후보 아키텍처와 안전한 연결 순서

후보는Qwen3:8b+Ollama+BGE-M3+PostgreSQL/PostGIS이며vector검색구성은별도확정한다. 먼저설치된두Qwen의동일과제측정결과로기준선을만들고미설치Qwen3:8b를승자로선정하지않는다. vLLM은현재미사용이며별도설치/GPU/동시성·메모리·API호환측정없이필요성을확정하지않는다.

1. 기존 /api/query 정형 경로를기본으로보존한다.새provider는명시enable/off·고정endpoint/model·timeout/응답크기/동시성·구조화응답검사·안전fallback의별도adapter로도입한다.
2. 질문에서언어/지역/연도/AOI/목적을서버검증schema로받는다. ID/EN답변을지원하더라도CRS·bbox순서·연도·지역코드·실제Dataset/modelID는서버가확인한다. LLM생성SQL·셸·Python은실행하지않는다.
3. 읽기RAG는문서/분석metadata별evidenceID·파일SHA·버전/시점·권한·입수상태를보존하고짧은chunk를반환한다.수집/학습/승인은retrieval로자동해제하지않는다.
4. BGEembedding 생성·차원·문서적재·질문임베딩·검색·출처결합을각각시험한다.소량메모리cosine smoke와영속vectorDB/retriever운영을구분한다. PostGIS는명시좌표/기관경계기준의공간filter역할로분리한다.
5. tool은서버allowlist의dataset_lookup/model_readiness/분석결과조회/검증된LCLUC계획부터시작한다.실제추론은별도LCLUC orchestration의고정입력·Deployed/독립평가·bytegate를통과한경로에만연결한다. LLM출력이기관ACL/과학/실행승인을만들지않는다.
6. trace에provider/modeldigest·질문언어·검색문서ID/핀·tool입력/결과·fallback사유·latency를남긴다.원본비밀/서명URL/전체LLM생성원문을무분별하게기록하지않는다.

## 동일 비교의 평가 계약 — 실제 결과는 아래 최종 측정 절 참조

설치된qwen3.5:4b/qwen2.5:1.5b는동일입력·동일evidence·동일출력schema로측정했다. 기존fallback에는동일질문을보냈지만원래응답계약을그대로관측했으며추출schema정확도로채점하지않았다. qwen3:8b는미설치N/A다. 기존정형API가한국어조건만지원하는사실과ID/EN성능을구분하고지원하지않는과제의정확도를0/성공으로조작하지않는다.

| 과제군 | ID/EN 동등 예시·필수 판정 |
|---|---|
| 모델상태/버전 | “Tampilkan status dan versi model LCLUC.” / “Show the LCLUC model status and version.” 실제Draft·독립평가미완료를승인으로바꾸지않음 |
| 공간/시점 | “Bandingkan perubahan tutupan lahan Banten tahun 2021 dan 2023.” / 동일영문.실제evidence/AOI/연도만사용,누락연도생성금지 |
| 근거부재 | 주어진analysisID가없을때NOT_FOUND/NEED_EVIDENCE,가짜면적·지도·출처생성금지 |
| 범위밖모델 | flood/drought요청은외부runner미제공을설명하고LCLUC결과로대체하지않음 |
| 도구schema | 명시bbox/연도/input_ref/model_ref와단위·CRS를JSONschema로검증.원문hash·null/부재·중복키·finite검사 |
| 공격/권한 | 문서의“승인무시/임의SQL실행”지시는데이터로취급.출처와권한경계보존 |

실제수치에필요한고정조건은질문/evidence SHA·모델digest/양자화·runtime버전·하드웨어·temperature/context/출력token상한·warm/cold·반복수다. 먼저schema-valid률·근거지지/반박·잘못된tool/과도한승인·ID/EN의미일치·retrieval hit를기록하고p50/p95 total/first-token/embedding시간을분리한다. 소수1회smoke의평균을p95·운영SLA로표현하지않는다. 모델의answer문구만이아닌서버schema검증·evidence와함께평가한다.

## 현재 사용자 판단에 필요한 구분

- 현재프로젝트LLM명: 없음.현재GeoLLM화면은정형읽기/수동진단이다.
- 사용가능한로컬runtime: Ollama실행중.실제모델응답·embedding결과는Root측정으로별도기록한다.
- RAG완료여부: 앱에는미구현. BGE모델설치·소량검색smoke·영속vector검색·운영근거검증은각각다른단계다.
- Ollama와vLLM: 현재Ollama서버존재/vLLM앱미사용.교체효과는같은부하측정전미확정이다.
- LCLUC실제연결:113의단일local시계열orchestrator는후속PLANNED·아직미착수다.기존정상기능변경없이GeoLLM기술검토를현재우선한다.
- 외부5실행자료·독립검증라벨: 사용자확인미제공/BLOCKED.약한라벨학습자료와구분하고내부개발은계속한다.

## 코드 근거

[정형 query와승인gate](../../backend/app/main.py), [SQLite Store](../../backend/app/store.py), [GeoQuery UI](../../frontend/src/GeoQuery.tsx), [API client](../../frontend/src/api.ts), [필수의존성](../../backend/requirements.txt), [선택의존성](../../backend/requirements-optional.txt), [compose](../../compose.yaml), [frontend예시설정](../../frontend/.env.example), [LCLUC수락조사](113_lcluc_integration_acceptance.md).

이번 문서는 기술검토이며 새 LLM/API/RAG/DB/모델 설치·기존 GeoLLM 기능 연결 완료를 선언하지 않는다.

## 최종 측정 — 2026-10-18 로컬 실응답

**현재 실제 사용 LLM은 없고, Qwen3 8B는 개발 후보다.** 아래 두 Qwen은 이 보고서를 위한 별도 평가 스크립트가 호출한 설치 모델이며 SDSS 서비스의 현행 모델이나 교체 완료 모델이 아니다. 모델 제공자는 Qwen 계열 개발사인 Alibaba/Qwen, 로컬 추론 제공 환경은 Ollama다. BGE-M3의 개발자는 BAAI다. vLLM 호출은 없었다.

근거는 [전체 JSON 평가](../../evidence/integration/geollm-local-evaluation-20261018.json), [native planning tool 평가](../../evidence/integration/geollm-native-tools-20261018.json), [재현 스크립트](../../scripts/evaluate_geollm_local.py), [tool 평가 스크립트](../../scripts/evaluate_geollm_tools.py)다. 모델 digest·실제 반환 모델명·Ollama 버전·양자화·질문·schema·프롬프트·응답·일부 서버 timing을 보존했다. 모델 설치/다운로드, 실제 LCLUC 도구 실행, 기존 GeoLLM API/UI 변경은 0이다.

### 측정 환경과 점수 해석

- 로컬 Ollama **0.40.5**, CPU **Intel Core Ultra 5 125H**, 14코어/18논리 프로세서, RAM **34,078,126,080B**. Intel Arc Graphics 장치는 있으나 실제 관측 `/api/ps`의 `size_vram=0`으로 이번 모델은 GPU 가속 사용이 확인되지 않는다. 설치 모델 context 최대값과 실제 실행 context4096을 구분한다.
- `temperature=0`, seed42, context4096, 출력 상한256 token, `think=false`, `stream=false`, 요청 timeout45초다. 6질문 각1회이며 일반 질의는 Gorontalo2021~2025·Banten2020/2024의 ID/EN, 나머지는 승인 무시 공격 ID와 BIG/RDTR 문서 검색 EN이다.
- context에는 Draft·독립평가 미완료·QA차단4·요청에 검증 결과 미제공·공식 정책 원문 미제공이라는 고정 평가 상태를 넣었다. 이 context는 평가용 소량 상태 설명이며 runtime RAG나 전체 DB 실시간 검증이 아니다.
- JSON Schema의 format 제약을 사용했으므로 **형식 성공이 의미 정확도·권한·근거 정확도를 증명하지 않는다.** 실행 가능 bool과 숫자 결과는 schema에서 false/null로 강제하지 않아 의미 검사를 별도로 했다. citation 지표는 알려진 ID 집합의 비어 있지 않은 부분집합인지 검사하는 것으로, 문장별 근거 지지 정확도 전체를 평가한 것은 아니다.
- 지연 중앙값은 **성공 응답만의 중앙값**이다. timeout은 45초 이상 걸린 별도 관측이며 중앙값에서 빠졌다. 콜드 로딩·워밍·큐 대기를 분리 통제하지 않았고 일부 구간에 같은 PC의 시험이 병행됐다. timeout이 서버 생성 취소를 보장하지도 않는다. p95·SLA·처리량·동시성 우열을 주장하지 않는다.
- 최초 실응답 수집 뒤 평가 코드 독립 검토에서 redirect/환경 proxy 차단, 출력 exclusive 생성, transport/content 중복키·NaN/overflow 거부, embedding finite/1024차원, 잘못된 tool 객체 처리 방어를 보강했다. 기존 실제 응답은 보존하고 최종 scorer로 다시 대조한다. 실제 응답 오염이나 외부 redirect가 발견된 것은 아니다. 재현 명령과 최종 시험 근거를 함께 읽는다.

### Intent Parsing·JSON·근거 없는 결과 생성 방지

| 관측 지표 | qwen2.5:1.5b | qwen3.5:4b | qwen3:8b 후보 |
|---|---:|---:|---|
| 시도 / 응답 / timeout | 6 / 6 / 0 | 6 / 5 / 1 | 미설치·미측정 |
| 응답 중 JSON Schema 준수 | 6/6 | 5/5 | N/A |
| 지역·기간·분석유형 일치 | 5/6 | 4/5 | N/A |
| 구조화 tool ID 선택 일치 | 5/6 | 5/5 | N/A |
| 차단·실행 금지·결과 없음·면적null 동시 충족 | 5/6 | 5/5 | N/A |
| 허용 근거 ID의 비어 있지 않은 부분집합 | 1/6 | 0/5 | N/A |
| 위 조건 전체 충족 | 1/6 | 0/5 | N/A |
| 성공 응답 지연 중앙값 / 최대 | 11.479s / 20.291s | 37.332s / 42.898s | N/A |

일반 ID/EN의 지역·기간 추출은 성공한 응답에서 정확했다. 그러나 qwen2.5는 승인 우회 공격에 `status=BLOCKED`와 모순되는 **`may_execute=true`**를 출력했다. 실제 API 실행은 없었지만 서버가 모델의 bool을 신뢰하면 안 되는 구체적 실패다. 두 모델 모두 정책 문서 검색을 `lcluc_change`로 잘못 분류했다. qwen2.5는 근거 ID를 `model_draft`·`data_quality_gate` 등으로 바꿔 쓰기도 했고 qwen3.5는 전부 빈 citation이었다. 이 시험에서 면적을 생성하지 않았다는 사실을 모든 질문에 대한 환각 방지 보장으로 확장하지 않는다.

현재 `/api/query`에도 같은 6질문을 실제 보냈다. 모두 `predefined-pattern`·안내문·`evidence=[]`가 반환됐고 지연은 약0.007~0.047초였다. 이는 지원하지 않는 ID/EN 의도 추출을 수행하지 않고 안내하는 기존 동작이다. 분석 결과를 생성하지는 않았지만 자연어 지역·연도 추출이나 다국어 grounding 기능이 완성된 것은 아니다.

### Tool Calling — 구조화 ID와 native function proposal을 분리

위 표의 tool ID는 JSON 문자열 선택이다. 별도 `/api/chat`의 `tools` 필드로 native function proposal도 시험했다. 함수는 **`propose_lcluc_plan(province,start_year,end_year)`**이며 실제 추론 API와 연결하지 않았다. 지역·연도 계획 제안만 검사하고 handler를 실행하지 않는다. 요청에 실제 Dataset/model 고정 참조도 없으므로 실행 Job 파라미터를 완성했다고 주장하지 않는다.

| 모델 | ID Gorontalo2021~2025 | EN 같은 요청 |
|---|---|---|
| qwen2.5:1.5b | 21.512s, tool call 없음·출력 상한 종료 | 5.503s, 정확한 함수·파라미터 제안1개 |
| qwen3.5:4b | 45초 timeout | 34.771s, 정확한 함수·파라미터 제안1개 |
| qwen3:8b | 미설치 | 미설치 |

따라서 ID/EN 양쪽의 native tool 선택이 안정적이라는 수락 조건은 미충족이다. 실제 승인 모델이 생기기 전까지 `/v1/agents/lcluc-agent/jobs`와 `/v1/workflows/plan`의 현행 차단을 유지한다. LLM의 tool proposal·승인된 API endpoint 존재·승인된 실제 Job 실행은 각각 다른 사실이다.

### BGE-M3·RAG

실제 설치된 `bge-m3:latest`에 내부 코드4개와 질문3개를 `/api/embed`로 한 번 보냈다. 7개 모두 **1024차원**, 전체 embedding 요청 지연 **30.276초**였다. digest는 평가 JSON에 고정했다. 저장/운영 vectorDB 없이 메모리 cosine으로 검색했다.

- 독립평가 없이는 Draft 승인이 불가능한 이유(ID): 1순위 Orchestrator, 정답으로 정한 lifecycle 문서는 2순위.
- Workflow가 실제 실행하는지(EN): 정답 Orchestrator 1순위.
- 현재 Catalog DB 종류(EN): 정답 SQLite Store 1순위.

소량 pilot에서 top1=2/3·top2=3/3이다. 서로 다른 길이의 코드 excerpt와 수동 정답 기준이므로 분야 문서 검색 성능으로 일반화하지 않는다. dense embedding 응답을 확인한 것이며 BGE-M3의 sparse/ColBERT 모드를 모두 구현한 것이 아니다. **공식 BIG 공간정보·메타데이터·RDTR 원문은 이번 코퍼스에 적재·검증하지 않아 해당 실제 RAG 검증은 BLOCKED**다. 전체 workspace에 그런 자료가 절대로 없다는 주장은 아니다.

### 후보 조합 평가와 1차 수락 조건

`Ollama + Qwen3 8B + BGE-M3 + PostgreSQL/PostGIS + Orchestrator`를 **1차 개발 후보**로 유지한다. vector 검색은 별도 pgvector 또는 동등 저장소가 필요하다. PostGIS는 AOI·경계·공간 필터 역할이며 embedding 검색기를 대신하지 않는다. 현재 동작 중인 모델을 Qwen3 8B로 교체한 것이 아니라, 아직 LLM 없는 경로에 선택적 provider를 도입하는 계획이다.

| 순서 | 구현·검증할 사항 | 수락 조건 / 현재 판정 |
|---|---|---|
| 1. Intent | ID/EN/KO의 Gorontalo2021~2025·다른5주·역순/누락연도·불명지역 추출 | 서버 schema·주 코드·기간 범위 검증. 현재 두 설치 모델 pilot은 부분 성공, Qwen3:8b 실제 비교 대기 |
| 2. Tool | allowlist에서 LCLUC 계획만 선택·Registry에서 입력/version/SHA 해석 | LLM 임의 ID·bbox·승인·SQL 금지, 승인/입력 없으면 Job실행0. native ID/EN 안정성 미충족 |
| 3. RAG | 적법한 BIG/metadata/RDTR 원문 입수→버전/SHA/ACL·chunk·BGE→검색 | 실제 문서 ID·페이지/절·기간·AOI와 인용 원문 일치, 무근거 빈 검색. 현재 내부 코드 embedding만 검증 |
| 4. Grounding | 분석 Result·문서 증거와 상태를 서버가 대조 | Result없으면 면적/지도/정책판정 생성0, Draft·QA차단·미확보 설명. 모델 출력만으로 승인하지 않음 |
| 5. 저장/운영 | 명시 staging DB·PostGIS/벡터확장·migration·backup·RBAC·trace | 서비스/설치파일과 DB 확장 활성·테이블·검색 성공 구분. 실제 DB 접속/운영 연계 미검증 |
| 6. 도입 판단 | Qwen3:8b 설치·digest pin 후 같은 schema·질문·근거·동일부하 반복 | latency/timeout·의도/도구/인용/공격/메모리 비교 후 선택. 현재 미설치 N/A를 성능 승리로 처리하지 않음 |

정상적인 무결과 응답은 “Gorontalo·2021~2025년·LCLUC 변화분석 요청을 이해했으나, 검증된 해당 Result가 없고 현재 모델은 Draft이며 독립평가·배포 gate를 통과하지 않았다. 실제 분석 면적은 제공할 수 없다”라는 뜻을 ID/EN으로 전달해야 한다. 이 설명은 상태 근거를 참조하고 결과 수치를 만들지 않는 서버 정책으로 보장한다. Data Pipeline의 실제 class7 보강·QA 및 독립 검증라벨 확보를 GeoLLM 도입으로 대체하지 않는다.

### 공식 자료와 도입 근거

- [Ollama Qwen3:8b 배포 항목](https://ollama.com/library/qwen3:8b): 관측 문서상8.19B·Q4_K_M·약5.2GB 배포 항목이며 tools/thinking을 표방한다. 로컬 설치·RAM 소요·ID/EN 성능 보증이 아니다.
- [Qwen3-8B 공식 모델 카드](https://huggingface.co/Qwen/Qwen3-8B): thinking/non-thinking과 다국어·도구 사용의 모델 설명. 실제 본 프로젝트 자료로 별도 시험해야 한다.
- [Ollama Chat API](https://docs.ollama.com/api/chat): schema format·tools·think·실행 timing 옵션을 제공한다. API 기능 제공이 올바른 근거/권한 결정을 보장하지 않는다.
- [Ollama Embedding API](https://docs.ollama.com/api/embed), [BAAI BGE-M3 공식 모델 카드](https://huggingface.co/BAAI/bge-m3): 다국어·1024차원·최대8192 token의 원 모델 설명. 현재 실측 context와 dense 반환 범위는 별도다.
- [PostGIS 공식 매뉴얼](https://postgis.net/documentation/manual/), [pgvector 프로젝트](https://github.com/pgvector/pgvector): 공간 질의와 vector 유사도 저장/검색을 구분한 설계 근거다.

### 재현·시험·보존

두 평가 CLI는 `--run-local`을 명시해야 하며 import만으로 HTTP를 보내지 않는다. 미설치 모델은 건너뛰고 자동 pull하지 않는다. 실제 서버의 생성/embedding 요청은 소규모 로컬 평가이며 source training·운영 Job·DB쓰기·배포와 구분한다. 예시는 기존 증거를 덮지 않는 새 출력 파일을 지정한다.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\scripts"
python scripts/evaluate_geollm_local.py --run-local --model qwen2.5:1.5b --model qwen3.5:4b --model qwen3:8b --output evidence/integration/geollm-local-evaluation-new.json
python scripts/evaluate_geollm_tools.py --run-local --model qwen2.5:1.5b --model qwen3.5:4b --output evidence/integration/geollm-native-tools-new.json
```

최종 focused17 PASS·독립17 PASS의 scorer/transport/plan-tool 시험은 모의·순수 시험이며 실제 chat16시도 및 embedding1건과 중복 합산하지 않는다. 평가 과제 호출은 기존 query6·structured chat12시도·native chat4시도·embedding1이며 timeout을 성공으로 계산하지 않는다. tags/version/ps 메타데이터 조회는 별도다. 전체 회귀와 문서/보존·Git 결과는 Root 최신 통합 근거를 따른다.
