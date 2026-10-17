# Gate Candidate QA Comparison 20261017 — 원본·후보의 저장 QA 명시 비교

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | d474d5bce6c2a6c4bd8ba141c9256d15f6004631 (108까지 구현 검토 기준; 이 메타데이터 정리는 후속 문서 커밋) |
| evidence_paths | `backend/app/ml/candidate_qa_comparison.py`; `backend/app/candidate_qa_comparison_api.py`; `tests/test_candidate_qa_comparison.py`; `frontend/src/CandidateQaComparisonDiagnostics.tsx`; `frontend/src/candidateQaComparisonAdapter.ts`; `docs/implementation/75_candidate_qa_comparison_ui.md`; `backend/app/main.py`; `frontend/src/AgentCenter.tsx`; `frontend/src/candidateQaComparisonAdapter.test.mjs`; `frontend/src/candidate-qa-comparison.css`; `docs/implementation/74_candidate_qa_comparison_api.md`; `evidence/integration/candidate-qa-comparison-related-20261017.log`; `evidence/integration/candidate-qa-comparison-independent-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-adapter-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-tests-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-build-20261017.log`; `evidence/integration/candidate-qa-comparison-ui-independent-20261017.log`; `evidence/integration/candidate-qa-comparison-live-http-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-live-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-console-before-fix-20261017.json`; `evidence/integration/candidate-qa-comparison-ui-console-after-fix-20261017.json`; `evidence/integration/candidate-qa-comparison-full-tests-20261017.log`; `evidence/integration/candidate-qa-comparison-live-integrity-20261017.json` |
| confidence | 코드·전체/독립/프론트로그·실제HTTP/수정후브라우저/보존근거; 과학승인아님 |
| status | TESTED_SYNTHETIC: API/UI·전체회귀; VERIFIED_REAL: 5174/8002 저장비교; 학습 BLOCKED |

## 쉬운 설명

원본과 후보의 검사표 두 장을 확인증과 함께 고정해 나란히 읽는 작은 비교창이다. 검사표를 읽는다고 새 검사를 시작하지 않는다. 적격자료 수와 차단 수가 달라진 점, 여전히 부족한 나지 자료를 함께 보여준다. 원본 검사표에 적히지 않은 장면 수는 다른 숫자로 채워 넣지 않고 ‘미저장’으로 표시한다.

## 이론적 배경

73의 실제 QA는후보4차단을관측했지만기존원본조회카드는원본5차단을읽는다. 별도의명시비교계약으로두기록의시점·범위·pin을구분하면차단수가줄었다는사실을학습준비나완전한누출해소로오해하지않게할수있다. 차단코드중복은분할별빈도로보존하고물리장면수·선언행수·적격패치수를분리한다.

## 코드·고정입력

`compare_candidate_qa`는원본report/후보report/QAreceipt/stagingreceipt 정확히네고정JSON을네외부SHA로읽는다. `project_candidate_qa`는메모리안선택계약을대조하고최소출력만만든다. 실제바이트pin은reader담당이며순수projection이파일을인증하는것은아니다.

report각16MiB/receipt각64KiB·깊이32·strictUTF8/중복키/비유한수·typed상태/계수/15~17false·출처참조/동일policy/signature·receipt의pin/size·원본과후보각manifest역할을확인한다. 마지막에네입력SHA/stat/논리대상을재대조한다. 설정상한은한pass32.125MiB·두pass64.25MiB이며RAM/CPU하드제한과는다르다. 거대source/candidate manifest·영상/라벨·assess/helper/Registry/학습을호출하지않는다. 전후pin은원자snapshot이나과거실행코드신원인증이아니다.

현재지원계약은두저장report가blocked/readyfalse인범위다. 원본physicalscene수는oldreport에없어null/NOT_PERSISTED로반환한다. stagingreceipt의선언source1384/candidate1368과newQA capture1368은출처를분리한다. 패치1111로장면수를추정하거나선언1384를oldreport관측값으로채우지않는다.

## API·사용법·오류

`POST /v1/diagnostics/candidate-readiness-comparison` 요청은정확히 original_report_sha256/candidate_report_sha256/qa_receipt_sha256/staging_receipt_sha256 네소문자64hex다. 본문2KiB·JSON깊이8 제한이며임의경로/latest탐색을받지않는다. 고정report비교범위와pin·두split/총패치/차단요약·코드별빈도·공유차단관측·장면출처·bare근거·10비승인false만반환한다. 경로/원문장면·대용량JSON/모델성과를노출하지않는다.

처리한성공/오류는no-store이고threadpool/process-local worker1·429busy를사용한다. 400형식/409핀충돌/413크기/429사용중/503자료사용불가를안전오류로구분하며예외원문경로를돌려주지않는다. GET405같은프레임워크기본응답은별도다. HTTP200도statusBLOCKED이며학습/실행/정산/자동재개/독립성승인false다.

## UI 동작과비교해석

Agent Center LCLUC에만‘원본·후보 준비성 비교’네핀폼과명시조회버튼을연결했다. 진입/선택/렌더/이동으로자동조회나assess를하지않는다. 입력·선택Agent/모델/Job·hash/popstate·세대변경은이전결과와오래된응답을무효화한다. ‘응답 표시 중단’은화면응답표시를중단할뿐이미전송된서버작업취소가아니다.

프론트는고정핀·exact schema·상태·계수/상한·코드빈도·null/출처·bare·10false와교차모순을검사한다. 원본1111(628/233/250)/차단5→후보1095(628/217/250)/차단4를응답으로표시한다. 기대숫자를성공값으로가짜고정하지않는다. REFERENCE_CLASS_IMBALANCE3·CLASS_COVERAGE1과공유source차단원본관측/후보미관측을분리하며미관측≠누출완전해소/표본독립/원본인증임을함께표시한다.

나지class7픽셀은원본/후보train1418/val209/test1025·기여patch각0으로같다. 최소픽셀/기여patch기준과부족미해소를표시해차단감소만성공으로설명하지않는다. 다른5모델의과학검증상태를생성하지않는다. 기존SVG스타일과공통UI를사용한다.

## 시험증거·실제적용경계

최종 관련17 PASS/14.400초·독립backend17 PASS/17.124초, 신규UI13 PASS/460.2888ms·전체UI72 PASS/1137.5072ms·build75modules/18.69초·독립최종UI13 PASS/382.2987ms를확인했다. 이는합성경계·빌드근거이며실행서버/API·브라우저를보장하지않는다. 최종backend전체는 **761건 중760 PASS·1 SKIP/398.767초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련17 PASS/14.400초·독립17 PASS/17.124초와 최종신규UI13 PASS/460.2888ms·독립최종13 PASS/382.2987ms·전체UI72 PASS/1137.5072ms·build75modules/18.69초는범위를분리해backend761에합산하지않는다. 보호141참조·32기존코어SHA와카탈로그14기록canonicalSHA가불변이며이전추적코드/데이터/프론트중의도한main배선/AgentCenter두파일만변경됐다. 신규파일/문서/evidence도있어전체workspace변경2개라는뜻이아니고원자snapshot보장도아니다. 각반복/프론트시험을backend전체에중복합산하지않는다. 이해에이전트는API/브라우저/시험을실행하지않는다.

새기능은UI영향이있어web_ui인계/화면연결/프론트시험/실행중서버/실제브라우저를분리해완료를확인한다. 기존원본/후보QA와자료/원장/lock/예약136,314,880B·Registry/학습/정산/재개는변경하지않는다. 전체개발/10분보고는계속한다.

## 발표 1분

“원본과 후보의 저장된 준비성검사를 나란히 보는 수동비교창을 연결했습니다. 네지문을 명시해 조회하며 새 검사는 실행하지 않습니다. 원본1111패치·5차단과 후보1095패치·4차단을 구분하고, 같은 차단코드가 세분할에 있으면 빈도3을 보존합니다. 원본검사표에 없는 장면 수는 미저장으로 두고 복사확인서의 선언값과 후보의 실제캡처를 따로 표시합니다. 나지 픽셀과 기여패치 부족은 그대로라 차단 수가 줄어도 학습승인이나 완전한 누출해소라고 설명하지 않습니다.”

## 발표 5분·10분

1. **0~1분:** 검사표두장/확인증/작은비교창비유를말한다.
2. **1~2분:** 네pin·4JSON한정·최소projection/no새QA를설명한다.
3. **2~3분:**1111→1095/5→4와코드빈도·미저장null/선언/관측을구분한다.
4. **3~4분:** 나지픽셀/기여patch미해소·공유차단미관측한계·실제/시험근거를설명한다.
5. **4~5분:** 수동조회/오래된응답무효화·표시중단≠서버취소·승인false를말한다.

10분확장에서는보고서와receipt한도·typedpolicy/signature참조·원본/후보manifest역할·worker1/no-store/오류·실행서버적용과build차이를설명한다.

## Q&A

**비교조회가QA를다시실행하나?** 네고정JSON의기록만읽고source/candidate/raster/assess를호출하지않는다.

**5에서4면학습가능한가?** class7불균형3개/val209부족1개가남아BLOCKED다. 공유항목미관측도완전독립승인이아니다.

**원본장면수는1384인가?** 이oldreport에는미저장이라null이다. stage선언1384와후보선언/캡처1368을따로표시한다.

**표시중단은서버취소인가?** 응답표시만무효화하며이미전송된서버읽기를취소하는계약은아니다.

**원본경로/큰JSON도화면에오나?** 최소요약/pin만반환하며경로/원문장면/거대JSON은노출하지않는다.

## 이후갱신

API독립/전체·실제HTTP/브라우저·보존최종근거를읽고INDEX·변경이력·관련해설/계약/구조/용어·대본/FAQ/시연을함께갱신했다. 완료화면을전체ML/프로젝트승인으로보지않는다.

## 실제 API·수정후 브라우저 관측 — 전체/보존 확정

Root API8002의POST는200·2,161bytes/no-store로저장비교를반환했다. 틀린핀409·형식400·본문초과413도안전오류/no-store였고GET405는프레임워크기본응답이다. 원본경로/원문상세비노출·새assess/훈련0을확인했다.

Root는5174의 LCLUC evidence화면에서1111→1095/5→4·REFERENCE_CLASS_IMBALANCE빈도3·나지val209/기여patch각0·원본physical미저장null·stage선언1384/1368·후보캡처1368을확인했다. 명시200·입력clear/409·허브이동과back/forward/back에서이전결과제거·수동재조회를확인했다. 기존5173서버에새카드가적용됐다는근거는아니다.

실제첫검증에서두형제카드의동일Reactkey로console오류6건과header의상속space-between을발견했다. candidate-qa:keynamespace/형제key의미회귀와카드scope의flex-start로수정했다. 최종신규13 PASS/460.2888ms·전체UI72 PASS/1137.5072ms·build75modules/18.69초다. 이전12/71/build17.63초는수정전이력이고독립UI12/804.0825ms는당시경계반복근거이며최종13 PASS/382.2987ms를다시확인했다.

수정후reload→결과없음→명시200·허브back/재조회·입력clear409·backforwardbackclear를다시확인했다. desktop1449×1087에서수평넘침0·headerflex-start이며2026-10-17T08:24:15UTC이후새console오류0이다. 과거6건로그는보존한다. 이번모바일/반응형실측은수행하지않아이전화면검증을이번카드의모바일완료로복제하지않는다. 응답표시중단은서버취소가아니며조회는새QA를실행하지않는다.

## 최종보존과다음계획

최종backend전체는 **761건 중760 PASS·1 SKIP/398.767초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련17 PASS/14.400초·독립17 PASS/17.124초와 최종신규UI13 PASS/460.2888ms·독립최종13 PASS/382.2987ms·전체UI72 PASS/1137.5072ms·build75modules/18.69초는범위를분리해backend761에합산하지않는다. 보호141참조·32기존코어SHA와카탈로그14기록canonicalSHA가불변이며이전추적코드/데이터/프론트중의도한main배선/AgentCenter두파일만변경됐다. 신규파일/문서/evidence도있어전체workspace변경2개라는뜻이아니고원자snapshot보장도아니다.

다음76은PLANNED다. 고정후보QA보고서·정책에서분할별나지요구픽셀/기여patch부족을산출하는읽기전용후속데이터요구계약을검토한다. 실제이를충족할새영상/라벨/장면목록은없으며최소추가량만으로준비완료를보장하지않는다. 현재설계대기·미구현이고새수집/학습은없다.
