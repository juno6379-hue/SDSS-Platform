# Gate Stored Binding Handoff 20261017 — 저장 기대 선언과 전달 선언의 순수 대조

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/stored_job_binding_handoff.py`; `tests/test_stored_job_binding_handoff.py`; `docs/implementation/81_stored_job_binding_handoff.md`; `evidence/integration/stored-job-binding-handoff-related-20261017.log`; `evidence/integration/stored-binding-handoff-independent-20261017.log`; `evidence/integration/stored-binding-handoff-live-validation-20261017.json`; `evidence/integration/stored-binding-handoff-live-replay-20261017.py`; `evidence/integration/stored-binding-handoff-full-tests-20261017.log`; `evidence/integration/stored-binding-handoff-live-integrity-20261017.json` |
| confidence | 코드·합성/독립시험·실제저장선언의로컬재생; 실제executor전달/Job출처인증 미확인 |
| status | TESTED_SYNTHETIC: 순수guard; 실제legacy참조+로컬replay UNKNOWN/BLOCKED; 실행미연결 |

## 쉬운 설명

기준 목록을 밖에서 따로 받지 않고, 주문서에 저장된 기대 목록부터 확인해 전달하려는 목록과 비교한다. 옛 주문에 기준 지문이 없으면 ‘모름’으로 남기지만, 주문 번호나 버전이 다르면 분명한 ‘차단’으로 표시한다. 두 목록이 맞아도 이 주문서가 진짜 저장소에서 온 것인지, 실제 배달 목록인지까지 인증한 것은 아니다.

## 이론적 배경

77은두선언의대조,79는Job의저장capture검증이었다.81은79를통과한RECORDEDexpected만77에연결해caller의별도expected주입경로를없앴다. 그러나Job객체자체는caller가입력한다. caller가Job/supplied를함께만들어MATCH를얻을수있으므로신뢰된저장소/실제executoradapter경계는여전히필요하다.

## 실제 함수·흐름

`compare_stored_job_binding_handoff(job, requested_job_id, supplied_envelope)`는먼저79projection으로Job/request/capture형식·신원/rolepresence/index/order·canonicalhash·시각을확인한다.77selfcompare로supplied의1..64bindings/256자·exacttypes·고정version/pin/상충을검사한다. optionalmanifestpin이없어UNKNOWN인supplied도형식상유효하지만malformedsupplied는legacy에서도BLOCKED다.

| 저장/전달 상태 | handoff 결과 |
|---|---|
| malformedJob/capture/supplied | BLOCKED·안전reason |
| RECORDEDexpected와supplied모두일치 | MATCH·선언일치만 |
| RECORDEDexpected의pin/신원/role/order누락·변조 | BLOCKED |
| 유효LEGACY/UNAVAILABLE·보이는requestlink같음 | UNKNOWN·저장expected미기록 |
| LEGACY/UNAVAILABLE여도Job/Agent/Trace/ref가다름 | BLOCKED |

BLOCKED > UNKNOWN > MATCH다. 같은declaredpin을새로supplied에넣어도저장expected를소급만들지않고Registry로역채우지않는다. 같은id의다른고정version은정상입력이고role부재/null·presence를구분한다. 기존77/79코드는수정하지않으며private선택request재대조는순수metadata처리라DB재조회가아니다.

## 결과·범위

저장capture상태와handoff상태·requestJobhash/expected배열hash/supplied배열hash·nullablecounts·declarations_match·safeissues를반환한다. 배열hash는순서/role/pinpresence를포함하지만Job/Agent/Trace전체digest가아니다. 예를들어suppliedJobID만바꾸면배열hash는같아도결과는BLOCKED다.

issues는side/index/code만최대512개범위로다루고rawid/version/role/SHA/URI/경로/원문예외를노출하지않는다. stored/supplied둘다무효면두쪽reason을보존한다. validexpected는supplied무효여도hash/count를유지할수있고invalidsuppliedhash/count는null이다. null은0개가아니다.

15flags는모두false이며current_files_revalidated/executor_bindings_compared/stored_job_origin_verified도false다. network/source읽기/source쓰기/DB/Registry/resolver/executor7호출0은guard자체범위다. 입력불변이지만caller의동시변경/OS원자snapshot/TOCTOU는보장하지않는다. URI/AOI/model/params·권한/READY·현재asset/manifestbytes·분할독립성/과학·학습승인은scope밖이다.

## 시험·저장기록로컬재생

관련13 PASS/0.057초·독립13 PASS/0.056초다. RECORDEDMATCH·15false·별도expected인자거부·legacy역채움금지/visiblemismatch차단·supplied/저장malformed우선·order/pin/role/type/상한/배열hashscope·입력불변/IO0/privacy를합성검증했다. 반복시험을전체에합산하지않는다.

Root는실제저장legacyJob2개의선택선언을읽고supplied를로컬복사·fakepin추가/변조해8관측을만들었다. UNKNOWN4/BLOCKED4이고실제MATCH/실행기handoffcapture는없다. actualstored참조와local suppliedreplay의혼합근거이며실제executor검증으로확대하지않는다. catalog14/원Jobbody는불변이고harness가DB를읽은것과guarddatabase_calls0을구분한다. 최종backend전체는 **832건 중831 PASS·1 SKIP/344.500초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련13 PASS/0.057초·독립13 PASS/0.056초와legacy로컬8replay관측을전체832에합산하지않는다. 종료후보호141참조·42기존코어SHA와카탈로그14기록canonicalSHA/원Jobbody불변을재확인했고이전snapshot추적code/data/tests/frontend변경은0이다. 신규코드/문서/evidence가있어전체workspace변경0/원자snapshot보장은아니다. 이해에이전트는DB/replay/시험을실행하지않는다.

## 현재성·UI

새API/UI/executor/DB호출경로에연결하지않은pure내부guard다. UI담당영향검토에따라직접화면변경/프론트재시험/브라우저확인은없고79/80카드의executor비교false는유지한다. 기존후보4/원본5차단·나지부족·terminal2missing/예약136,314,880B·모델/분할은그대로다. 단일guard를실제실행기완성이나전체프로젝트완료로보지않고전체개발/10분보고를지속한다.

## 발표1분

“저장된 주문의 기대 입력부터 확인하고 전달하려는 입력과 비교하는 순수 기능을 추가했습니다. 기준 expected를 별도 인자로 받지 않습니다. 옛 기록에 지문이 없으면 모름을 유지하지만 주문번호나 버전이 다르면 차단합니다. 실제 Job 두 건의 저장 선언을 로컬에서 재생해 모름4회·차단4회를 관측했고, 실제 실행기 전달을 확인한 것은 아닙니다. 저장 Job 객체 자체의 출처나 현재 파일·권한·준비도를 인증하지 않으며 실제 실행 경로 연결은 후속입니다.”

## 발표5분·10분

1. **0~1분:** 주문서저장기준과전달목록비유를말한다.
2. **1~2분:**79저장검증→RECORDEDexpected만77비교·외부expected인자없음을설명한다.
3. **2~3분:** legacyUNKNOWN과visiblemismatchBLOCKED·malformed우선순위를보여준다.
4. **3~4분:** 합성13/독립13·실제저장+로컬8replay·전체/보존근거를구분한다.
5. **4~5분:** Joborigin/실제executor/현재bytes미검증·15false7IO0·UI없음을말한다.

10분확장에서는공동invalidreason·배열hash/Jobidentity차이·nullcount·rolepresence·issue상한·caller동시변경/TOCTOU한계를설명한다.

## Q&A

**expected를밖에서바꿔줄수있나?** 별도expected인자는없고79검증된저장RECORDED안의값만사용한다. 다만Job객체자체의출처인증은하지않는다.

**legacy면항상모름인가?** 보이는Job/request/suppliedlink가다르면BLOCKED다. 미기록만남아야UNKNOWN이다.

**MATCH면실행기에전달됐나?** supplied는caller선언이며실제executor포착/파일검증·승인은false다.

**실제Job두건을실행했나?** 저장선언읽기와로컬replay뿐이며DB쓰기/Job실행없다.

**화면이바뀌었나?** 공개API/UI미연결내부pure라변경없고기존카드의executorfalse를유지한다.

## 이후갱신

전체/보존최종근거를읽고INDEX·변경이력·계약/Orchestrator/구조/용어·대본/FAQ/시연을함께갱신했다. 다음Store읽기adapter는아래PLANNED범위로구분한다.

## 다음 Store 읽기 adapter — PLANNED

후속은공개API/UI보다 configured Store에서Job get1회후81guard를호출하는내부readonlyadapter를검토한다. 예시이름은 inspect_stored_job_binding_handoff(store, id, supplied)이며callerJob/expected인자를받지않는방향이다. 유효literal get1/invalid get0·실행체인미연결·기존Job/Workflow BLOCKED/PLAN_ONLY를유지한다.

store_read_observed는읽기관측이지출처인증아니며81stored_job_origin_verifiedfalse는유지한다. Store.get은전체body를json.loads하므로선택metadata상한을boundedDBparser/전체RAM하드제한으로확대하지않는다. 현재읽기설계만있고adapter/공개API/UI구현은없다.
