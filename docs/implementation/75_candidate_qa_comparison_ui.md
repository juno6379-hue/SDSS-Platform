# 원본·후보 준비성 비교 UI

상태: VERIFIED_REAL(고정 저장 보고서의 실제 API·데스크톱 수동 비교). 응답 경계·경합 검증은 TESTED_SYNTHETIC이며 실제 후보 QA 수행 근거인 문서73과 구분한다. 이번 화면 확인은 새 ML QA·학습 실행이 아니다.

## 범위와 사용법

LCLUC Workspace의 근거 탭에서 기존 Agent Center의 ‘저장된 출처 대조 진단’ 아래에 독립 ‘원본·후보 준비성 비교’ 카드를 추가했다. 기존 모델·실행·데이터 준비도 gate와 다른 5모델 상태·참조 PNG 레이아웃은 변경하지 않는다. 카드가 열리거나 선택·렌더·뒤로 이동했을 때는 비교 요청을 보내지 않는다. 사용자가 ‘원본·후보 준비성 비교 조회’를 누를 때만 `agentApi`로 저장 JSON 4개 비교 API를 호출한다. 새 QA·영상 검사·학습·등록·DB 처리를 시작하지 않는다.

고정 기준의 기본값은 다음과 같다. 자동 latest 선택이나 핀 대체는 없다.

| 입력 | 명시 SHA-256 |
|---|---|
| 원본 준비성 보고서 | `6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db` |
| 후보 QA 보고서 | `847343e1aa4ab9b67fd3bba36a2a9f91d716c2fd411af244e55bbfe1a8414019` |
| QA 완료확인서 | `7b5ea8bba57bfc359076a0db27adce554b28c7d1796ae352b82ef9d94d79e38d` |
| 복사확인서 | `b8224cb3eb5c5ef0accf0cab10359401d792719e6fd8cae0b610279e759404dd` |

요청은 `POST /v1/diagnostics/candidate-readiness-comparison`의 정확한 4키 `{original_report_sha256,candidate_report_sha256,qa_receipt_sha256,staging_receipt_sha256}`다. 각 입력은 주변 여백을 정리한 소문자 64자리만 허용한다. 원본 기준은 출처 단서 보고서66이 아니라 기존 원본 readiness 보고서다. `api.ts`와 Vite proxy는 변경하지 않고 기존 UI5174 → API8002 연결을 사용한다.

## 화면에서 구별하는 근거

- 원본·후보의 적격 패치 합계, 학습/검증/시험 분할, 차단 항목 수를 나란히 보여준다. 현재 실자료의 기대치 1111→1095 및 628/233/250→628/217/250, 차단5→4는 코드에 고정 성공값으로 넣지 않고 응답 검사 후 표시한다. 조회 전 결과를 만들지 않는다.
- 원본 보고서의 물리 장면 수는 저장되지 않았으므로 `null / NOT_PERSISTED`를 미저장으로 표시한다. 적격1111에서 물리 장면을 추정하지 않는다. 별도의 복사확인서 선언1384/1368과 새 QA 보고서 캡처1368은 서로 다른 출처의 기록이다. 새 캡처가 없으면 미수집/null로 보존한다.
- 차단 코드의 중복 빈도를 보존한다. 같은 클래스 코드가 여러 분할에서3회 관측된 것을 코드1개로 축소해 총 차단 건수를 왜곡하지 않는다. 코드별 원본/후보 빈도 합계는 각 보고서의 차단 건수와 일치해야 한다.
- 출처 공유 차단은 원본/후보의 관측 여부만 표시한다. 후보에서 해당 항목이 미관측인 것은 제공 메타데이터 범위의 결과이며 완전 누출 해소·과학적 독립성·원본 인증이 아니다.
- 나지 클래스7의 각 분할 픽셀·기여 패치와 요구 최소값, 후보 부족 관측을 별도로 표시한다. 학습 BLOCKED와 후보의 남은 차단 수를 상단에 유지한다. 학습·실행·Registry·과학·정산·자동 재개 승인을 부여하지 않는다.

응답 원문·원본 경로·거대 JSON·원문 상세를 렌더하거나 내려받지 않는다. 어댑터의 작은 allowlist 투영만 화면 state에 보관하고 SHA 결과는 접두12자리로 표시한다. 코드 표시도 최대64자리의 영문 대문자·숫자·밑줄로 제한한다. SVG는 기존 공통 Icon을 쓰며 새 스타일은 전용 CSS에만 한정한다. 모바일은4핀폼·비교2열을1열로 바꾸고 긴 표는 내부 스크롤을 사용한다.

## 엄격한 응답·경합 처리

정확한 top/nested keys, schema_version1, status BLOCKED, scope PINNED_REPORT_COMPARISON_ONLY와 요청4핀 일치를 검증한다. 다음10필드는 모두 정확히 false여야 한다: ready_for_training, scientific_accuracy_validated, source_authenticity_verified, exact_row_binding_verified, training_executed, execution_authorized, registry_called, training_split_leakage_resolved, automatic_resume_allowed, settlement_authorized. bool·문자열·누락·허위 승인·unknown field는 failclosed로 결과를 표시하지 않는다.

분할별 적격 패치0..3000·3분할합≤9000, 보고서 차단1..10000, 정렬·유일 코드≤32와 각 빈도0..10000·합계, 출처 공유 boolean과 해당 빈도를 교차 대조한다. 원본 physical=null, 선언 행0..100000과 후보≤원본, 캡처0..2000 및 선언 후보행과 동일해야 한다. 나지 픽셀은 안전한 정수, 기여 패치0..3000, 최소 픽셀256..65536·최소 패치5..3000을 검사한다. 분할 기여 패치는 적격 패치를 넘을 수 없고 픽셀은 고정256×256 패치 면적 상한을 넘을 수 없다. 후보 부족 boolean은 각 분할의 픽셀/패치와 요구 바닥으로 다시 계산한다.

입력 변경·수동 재조회는 세대를 증가시키고 이전 결과·오류를 즉시 지운다. 세대·입력 key·현재 hash가 모두 같은 응답만 반영한다. 화면의 ‘응답 표시 중단’은 진행 요청의 UI 반영만 무효화한다. `agentApi`에 transport AbortSignal 지원을 추가하거나 서버 작업 취소를 주장하지 않는다. popstate/hashchange·unmount 및 AgentCenter의 선택 Agent/호환 모델/Job/Registry 재조회 keyed remount도 이전 응답을 무효화한다. 중단 후 새 수동 요청이 busy에 걸리면 HTTP429를 보여주며 자동 재시도하지 않는다.

HTTP400/409/413/429/503을 입력·핀충돌·크기·진단 진행·자료 미사용으로 구별하고401/403/404·연결 오류도 안전한 한국어로 안내한다. 서버 error.message의 원문 경로·상세를 표시하지 않는다. 기준 충돌을 정상 QA 결과로 취급하지 않는다.

## 검증·인계

신규 어댑터 시험13개: 수동4핀/형식·bool·누락, 원본/후보 패치·split·차단·나지 분리, wrongpins,10false 변조, unknown 계약·추가필드, split계수/합계/cap, 코드빈도·정렬·중복·cap, 출처공유 관측/빈도, 물리 미저장·선언·캡처/null, 나지 바닥·계수/분할범위·부족, 입력/재조회/메뉴/표시중단의 늦은 응답, 오류·원문정보 비투영, 같은 선택 context에서도 두 형제 진단 카드가 독립 React key를 갖고 선택 변경 시 재마운트되는 계약을 검증한다. 최종 전체 UI와 build 수치·실제 브라우저 적용 결과는 후속 절에 기록한다.

근거 로그: `evidence/integration/candidate-qa-comparison-ui-adapter-20261017.log`, `evidence/integration/candidate-qa-comparison-ui-tests-20261017.log`, `evidence/integration/candidate-qa-comparison-ui-build-20261017.log`.

소유 파일은 신규 `CandidateQaComparisonDiagnostics.tsx`, `candidateQaComparisonAdapter.ts`, `candidateQaComparisonAdapter.test.mjs`, `candidate-qa-comparison.css`와 AgentCenter의 import/render 최소 연결이다. backend·원본·공용 CSS·API 공통 helper는 UI 담당이 수정하지 않는다. Root가 실제 서버 적용·브라우저·전체 backend·보존을 검증하고, 이해자료·원장·인계·snapshot을 통합한다. 합성 프론트 시험·실제 저장 보고서 비교·과거 후보 QA 수행을 서로 합산하거나 같은 검증으로 표현하지 않는다.


## 최종 프론트 검증

신규 adapter13/13 PASS /460.2888ms, 전체 UI72/72 PASS /0 FAIL /0 SKIP /1137.5072ms. TypeScript + Vite production build PASS /75 modules /18.69s. JS1,543.98kB(gzip435.87kB), CSS173.46kB(gzip31.77kB)이며 기존500kB chunk 경고만 있다. 실제 API route 배선·고정 보고서 비교 성공·브라우저 화면은 이 코드/합성시험/build와 별도로 root가 확인한다. UI source는 위 최종 라벨과 교차 제약을 포함해 동결했으며 실제 근거 수신 후 이 문서의 적용 절만 갱신한다.


실제 브라우저 검증에서 발견한 두 UI 결함을 보완했다. 카드 header의 전역 `justify-content:space-between` 상속은 전용CSS의 flex-start 및 자식 min-width:0/flex:1로 덮어써 아이콘과 제목을 함께 정렬했다. 기존 출처 카드와 후보 비교 카드의 동일 key 경고는 후보 전용 `candidate-qa:` namespace로 분리하고 React key 회귀시험을 추가했다. 원본 카드의 key와 승인 gate는 변경하지 않는다. 최종 콘솔 상태·화면 크기는 수정 이후 root의 새 브라우저 관측으로 확인하며, 초기 경고6건을 최종 무결함 관측과 혼합하지 않는다.


## 실제 적용·브라우저 검증

Root가 UI5174 → API8002에서 실제 고정 저장 기록을 비교했다. 근거는 `evidence/integration/candidate-qa-comparison-ui-live-20261017.json`이며, 검증 주소는 `#/view/24?model=lcluc&tab=evidence`이다. 수정 후 reload에서 결과 없이 시작하고 명시 수동 조회의 HTTP200 결과에서 다음을 확인했다.

- 적격 패치1111→1095, 차단5→4를 표시했다. 후보는 학습 BLOCKED를 유지하고 나지 검증분할 픽셀209·각 분할 기여패치0을 구분했다.
- 원본 물리 장면은 NOT_PERSISTED/null, 복사확인서 선언은1384→1368, 후보 저장 QA 캡처는1368로 구별했다. REFERENCE_CLASS_IMBALANCE의 반복빈도3도 보존했다.
- SHA 입력 변경은 이전 결과를 즉시 제거하고 잘못된 핀은 HTTP409의 안전 문구를 표시했다. 뒤로→앞으로→뒤로 복귀에서 오래된 비교를 재표시하지 않았고, 수정 후 모델 허브 왕복에서도 결과 제거 후 명시 재조회가 성공했다.
- 1449×1087 데스크톱에서 가로 넘침0px, header justify-content:flex-start를 확인했다. 이번 단위에서는 모바일·responsive breakpoint의 실제 브라우저 검증을 수행하지 않았다. 전용 반응형 CSS 구현과 실제 모바일 검증을 구별한다.

초기 중복 key 경고6건은 `candidate-qa-comparison-ui-console-before-fix-20261017.json`에 보존했다. 수정 후2026-10-17T08:24:15Z 이후 새 콘솔 오류0건은 `candidate-qa-comparison-ui-console-after-fix-20261017.json`에 별도로 기록했다. 전체 이력을 오류0건으로 덮어 표현하지 않는다. 수정 후 데스크톱 스크린샷은 `candidate-qa-comparison-ui-desktop-20261017.jpg`이며 모두 `evidence/integration/` 아래에 있다.

이 근거는 저장 보고서 비교 화면과 복귀 동작을 확인한 것이다. 새 QA·학습은 실행하지 않았으며 출처 공유 항목의 미관측을 완전 누출 해소·독립성·과학·실행 승인으로 승격하지 않는다. 이 절 반영 후 소스·시험·빌드 추가 변경 없이 문서 쓰기를 동결한다. 이해자료·운영 원장·인계·snapshot은 root가 관련 구현74/75와 최종 증거로 통합한다.
