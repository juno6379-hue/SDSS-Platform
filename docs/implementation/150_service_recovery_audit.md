# 150 — 147 통합 완료 및 사용자 API 복원 사전 감사

관측: 2026-10-18 09:46–10:04 KST. 현재 상태: **VERIFIED_REAL — 기존 localhost 개발 모드 API·프록시·실제 화면 연결 복원 및 catalog 보존 확인**. 09:49까지의 조건부 보류는 아래 과거 이력이며 현재 BLOCKED가 아니다.

## 147 통합 마무리가 뜻하는 것

화면 코드를 작성한 다음, 그 화면이 기존 API와 같은 Workflow ID·모델·연도·보고서 SHA를 연결하는지 시험하고, 실제 브라우저 표시까지 확인한 뒤 문서·설명자료·Git에 함께 고정하는 작업이다. 보고서가 다른 분석에서 섞여 들어오거나 실패를 0으로 표시하지 않도록 검산하는 과정도 포함한다.

147은 커밋 `76949f650123653f30841507feebc7678aaea151`에 반영돼 있다. 이번 담당은 closeout의 UI 소스·시험 6개 raw SHA가 현재 파일과 모두 일치함을 독립 확인했다. 공통 개발 원장과 구현147, 이해 Gate의 최종 검증·API offline 정정도 읽었다. 앞선 미커밋·이해자료 최종 대기라는 보고는 현재 상태와 달라졌다.

기존 근거는 집중9 PASS, 독립7 PASS, 전체 frontend280 PASS, build116 modules, 관련 backend34 PASS다. 이번 감사에서 시험을 재실행한 수치는 아니다. 실제 main Temp8003·Vite5180 브라우저 통과와 기존5174 반영은 이전 관측 이력이다. 합성 영상·미훈련 모델·모의 승인으로 시험했으므로 실자료 과학적 정확도나 기관 승인이 아니다.

## 09:46–09:49 서비스 관측 이력

09:46 프로세스·리스너 확인에서 frontend5174 PID34484와 Ollama11434 PID27860만 확인됐다. API8000·8001·8002·8003과 시험frontend5180 리스너는 없었다. 기존 API 프로세스의 종료 원인은 미확정이며 인증 설정 부재가 그 종료 원인이라는 뜻은 아니다. 현재 서비스와 과거 브라우저 성공을 구분한다.

사용자 Chrome의 기존5174 탭에는 캐시된 ‘로컬 분석 서버 연결됨’ 표시가 있었다. 읽기 전용 ‘서버 상태 새로고침’ 뒤 **‘서버 연결 확인 필요’**로 바뀌었다. 사용자 탭을 새로 열거나 URL·질문·토큰을 변경하지 않았다. 서버 연결 설정의 API 토큰 password field는 값 존재 여부만 읽었고 `false`였다. 새 토큰 입력·발급·적용은 수행하지 않았다.

## API를 바로 켜지 않은 구체적인 이유

`backend/app/main.py`는 import 시 `Store(ROOT, recover_jobs=True)`를 호출한다. Store는 root mkdir, `CREATE TABLE IF NOT EXISTS records`, legacy `jobs`의 queued/running 항목을 failed로 고치는 복구를 수행할 수 있다. 따라서 단순 uvicorn 실행도 읽기 전용 작업은 아니다. 라우터 구성 검색에서는 별도 startup/lifespan/복구·디렉터리 생성 코드가 확인되지 않았으며, POST 실행 함수는 호출하지 않았다.

운영 `data/catalog.sqlite3`를 SQLite URI `mode=ro`로 읽었으며 Store/main은 import하지 않았다. 현재 catalog14행은 datasets6·models1·analyses3·gmais_jobs2·gmais_idempotency2이고 legacy jobs는0이다. 따라서 현재 관측 기준 자동 실패 복구 대상은0이다. GMAIS 두 job을 legacy jobs와 혼동하지 않는다. DB raw SHA는 전후 `7c5068be8f430c7cbe10badd9ce7bbf4df94a5045fad788682c96fcb20867b1b`, canonical14행 SHA는 `72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b`로 147 최종 근거와 같다.

frontend `.env.local`의 proxy 대상은 `http://127.0.0.1:8002`다. `scripts/start-api.ps1` 기본은8000이므로 기본 명령만 실행하면 화면의 연결은 복원되지 않는다. 데이터 root 기본은 저장소 `data`이지만 복원 시에는 실제 절대 root를 명시해야 한다.

이번 실행 환경·사용자·시스템 환경의 `GEOAI_API_TOKEN`은 모두 미설정이었다. 알려진 프로젝트 `.env*`, frontend `.env*`, scripts의 PowerShell 실행 파일 총5개에서도 기존 토큰 설정을 찾지 못했고 사용자 화면의 저장된 입력도 비어 있었다. 이 범위 밖의 비밀 저장소나 과거 프로세스의 secret 존재 여부는 확인하지 않았다. 과거 토큰 값을 추정하거나 로그에서 추출하지 않았다.

Root는 처음 기존 인증 설정을 안전 재사용하는 조건으로 복원을 허용했지만 그 설정을 찾지 못했다. 당시 Root 지시에 따라 신규 secret·사용자 브라우저 인증 변경 없이 복원을 보류했다. 이 초기 감사 구간은 **API 시작0·운영 POST0·새 토큰0·인증 우회0**이다. 토큰 부재를 앱 자체의 필수 실행 차단 요건으로 정한 것은 아니며 아래 후속 소스 재검토로 복원 판단을 정정했다. 이 경계는 수집기 중단 원인이나 수집 재개 조건과 별개다.

## 09:58 이후 — 기존 localhost 개발 모드 복원

Root가 `main.py`의 `authorized`와 `/api/health`를 재검토하여 token 미설정은 기존 지원 localhost 개발 모드임을 확인했다. token이 설정됐을 때의 Bearer 비교 코드를 제거하거나 우회하지 않았다. 기존 token 없음·명시 DATA_ROOT·API/Vite 모두127.0.0.1 bind·복구대상 jobs0을 유지한 채 Root가09:58:53에 API8002를 hidden detached/no-reload PID33956으로 시작했다. web_ui 담당은 별도 재시작하지 않았다.

10:01:35에 API8002 `/healthz`, `/readyz`, `/api/health`와 frontend5174 `/api/health` proxy의 실제 GET이 모두200이었다. health 응답은 `local-development`, `localhost-only; configure GEOAI_API_TOKEN for shared access`이며 ready 응답은 runtime-only/scientific_readiness not-implied다. API8002 PID33956과 Vite5174 PID34484의 리스너는 모두127.0.0.1이다. token 미설정 localhost 모드는 Bearer 인증으로 보호된 공유 운영 서비스와 다르다. 새 secret·토큰·인증코드·브라우저 인증 설정 변경은0이다. 일부 인증 필수 v1 endpoint의 사용 가능성을 일반 health200으로 확대하지 않는다.

기존 사용자 Chrome127.0.0.1:5174 탭에서 서버 새로고침 뒤 ‘로컬 분석 서버 연결됨’을 확인했다. 기존 모델 화면·URL·초안·토큰은 보존했다. 별도 검증탭850118890을 열 때 navigation/초기조회 timeout이 있었으나 한 번 상태를 복구한 뒤 실제 GeoLLM 화면으로 이동해147 패널을 열었다. Local workflow ID 빈 값과 ‘기록·보고서 읽기’ 비활성을 DOM 값·isEnabled로 확인했다. Workflow GET·POST·새 분석은 수행하지 않았으며 임시 탭은 닫았다. 현재 성공 보고서를 만들기 위한 운영 실행이나 임시 fixture 주입도0이다.

시작 전후 catalog는14행/legacy jobs0, raw SHA `7c5068be8f430c7cbe10badd9ce7bbf4df94a5045fad788682c96fcb20867b1b`, canonical SHA `72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b`로 동일하다. 현재 새 API access log의 method는 GET만이며 POST0이다. 이는 이번 복원 프로세스 로그의 관측 범위로, 과거 모든 서버 traffic의 전수 감사가 아니다. 이 복원은 데이터 수집·학습 재개나 과학·운영 승인 완료와 구분한다.

## 재개 가능한 서비스 복원 절차

아래는 초기의 token 설정 재사용을 조건으로 한 복원 검토 절차다. 이번 실제 복원은 위에 기록한 기존 localhost 모드로 수행했다. 향후 token을 설정한 서비스에서는 토큰을 명령줄·로그·문서에 출력하지 않고 자식 프로세스 환경으로만 전달한다.

1. API8002 리스너와 작업 중복 여부, 명시 root 아래 catalog 존재, legacy jobs queued/running0을 다시 확인한다.
2. DB 원바이트·canonical행 SHA, 보호 원본·원장·lock·분할·모델 SHA를 복원 직전 고정한다.
3. `GEOAI_DATA_ROOT`를 저장소 `data` 절대 경로로 설정하고, 기존 인증 설정을 유지한 채 `scripts/start-api.ps1 -Port 8002`에 해당하는 uvicorn을 loopback/no-reload·숨김 detached 방식으로 실행한다. 기존 Store 복구를 monkeypatch하거나 recover gate를 우회하지 않는다.
4. 미인증 `/api/health`401, 인증 GET health200, 공개 `/healthz`·`/readyz`의 runtime 상태를 구분 검증한다. readiness는 학습 준비도나 과학 인증이 아니다.
5. DB·보호 파일 SHA 불변과 운영 POST0을 검산하고, 실제 브라우저에서 현재 연결 및147 빈ID/read disabled를 확인한다. 성공 보고서를 얻기 위해 운영 Workflow를 새로 만들지 않는다.

서비스 가용성과 다른 담당의 수집·학습 준비도 점검은 독립적으로 보고한다. 일반 health200이 실제 Workflow 기록·보고서 조회 성공이나 실자료 확보·학습 준비도 충족을 뜻하지 않는다. 현재 조회의 인증 동작은 main의 기존 설정을 따르며, 이번에는 토큰을 새로 설정한 서비스의401/인증 성공을 재시험하지 않았다.

## 증거와 인계

- [프로세스·리스너·환경 설정 존재 여부](../../evidence/integration/147-closeout-service-audit-20261018-process.json)
- [읽기 전용 catalog·UI raw SHA 검산](../../evidence/integration/147-closeout-service-audit-20261018-catalog.json)
- [기존 인증 설정 재사용 조사](../../evidence/integration/147-closeout-service-audit-20261018-auth.json)
- [Root의 기존 localhost 모드 시작 기록](../../evidence/integration/147-local-service-restore-20261018-start.json)
- [현재 GET·프록시·catalog 보존 검산](../../evidence/integration/147-local-service-restore-20261018-verified.json)
- [후속 실제 브라우저 확인 범위](../../evidence/integration/147-local-service-restore-20261018-browser.json)
- [147 구현과 과거 실제 브라우저 범위](147_geollm_workflow_evidence_ui.md)

이번 단위는 코드·API 계약을 바꾸지 않은 서비스 복원 조사와 Root의 실행에 대한 web_ui 후속 검증이다. 기존147 이해자료의 API offline 표기는 당시 이력이고 최신 localhost 서비스 가용성은150과 후속 증거를 따른다. 새150은 Root와 understanding_agent에 전달한다. 원본·catalog·원장·lock·분할·모델·운영 인증·예약 설정은 변경하지 않았다. 이번 검증은 localhost 서비스 연결 복원 완료이며 전체 프로젝트·수집·학습 완료가 아니다.
