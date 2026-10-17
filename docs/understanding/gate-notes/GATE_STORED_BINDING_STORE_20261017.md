# Gate Stored Binding Store 20261017 — configured Store 단일조회와 내부 대조 연결

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | d474d5bce6c2a6c4bd8ba141c9256d15f6004631 (108까지 구현 검토 기준; 이 메타데이터 정리는 후속 문서 커밋) |
| evidence_paths | `backend/app/stored_job_binding_handoff_store.py`; `tests/test_stored_job_binding_handoff_store.py`; `docs/implementation/82_stored_job_binding_handoff_store.md`; `evidence/integration/stored-binding-store-adapter-related-20261017.log`; `evidence/integration/stored-binding-store-adapter-independent-20261017.log`; `evidence/integration/stored-binding-store-adapter-live-validation-20261017.json`; `evidence/integration/stored-binding-store-adapter-live-check-20261017.py`; `evidence/integration/stored-binding-store-adapter-full-tests-20261017.log`; `evidence/integration/stored-binding-store-adapter-live-integrity-20261017.json` |
| confidence | 코드·합성/독립·실제저장소읽기관측/로컬전달재생; 출처인증/실제executor 미확인 |
| status | TESTED_SYNTHETIC: adapter; 실제readonly Store참조+localreplay 혼합근거; 실행미연결 |

## 쉬운 설명

손님이 주문서 파일을 직접 건네는 대신, 설정된 문서보관함에서 주문번호로 한 번 꺼내 내부 대조 담당자에게 넘긴다. 꺼내 왔다는 사실과 문서 내용이 맞는지, 보관함 자체가 믿을 만한지, 실제 배달목록인지는 서로 다른 질문이다. 주문번호가 잘못됐으면 보관함을 열지 않는다.

## 이론적 배경

81은callerJob객체를대조했다.82는configuredStore에서Job을get한뒤81을호출해callerJob/expected별도인자를없앴다. Store선택과신뢰구성은caller/app책임이며읽기관측이암호학적출처인증으로바뀌지않는다. 조회상태와81선언대조상태를분리하면자원오류를입력불일치로혼동하지않는다.

## 실제 함수·네 조회상태

`inspect_stored_job_binding_handoff(store, requested_job_id, supplied_envelope)`는boundedliteral을먼저검사한다. invalid이면get0/hashnull·comparisonnull이다. valid이면supplied가malformed여도 `store.get('gmais_jobs', id)`를1회시도하고반환객체를81로넘긴다. 추가list/put/Registry/resolver/자산/학습호출은없다.

| store_status | attempted/observed | calls | comparison |
|---|---|---:|---|
| INVALID_REQUEST | false/false |0|null |
| OBSERVED | true/true |1|81 MATCH/BLOCKED/UNKNOWN |
| NOT_FOUND | true/false |1|null |
| RESOURCE_UNAVAILABLE | true/false |1|null |

Store가None/배열/손상Job을반환해도반환관측은OBSERVED이고innercomparison이BLOCKED다. OBSERVED를입력정상/실행승인으로설명하지않는다. getcalls1은adapter가Store.get을한번시도했다는뜻이지SQL실행/내부파일read횟수가1이라는뜻이아니다. wrapper15false·inner81의15false/7IO0을구분한다. 전체adapter가DB0인것은아니다.

## 오류 경계·출력

기존Store.get의missingKeyError는args개수1·exactstr·validatedID와같은길이를확인한뒤값이같아야NOT_FOUND다. 다른KeyError는RESOURCE_UNAVAILABLE이며nested/custom equality·거대값을비교전에차단한다. sqlite/Unicode/OS·알려진파싱/type/value/overflow/recursion/memory오류만get경계에서안전분류한다. MemoryError를분류한다고메모리부족에서도응답이보장되는것은아니다.

예상밖RuntimeError/AssertionError·KeyboardInterrupt/SystemExit는전파한다. catch는get만감싸므로81comparison버그를저장소오류로덮지않는다. wrapperissues는안전code만·requesthash와inner안전hash/count/code/index를보존하며rawJob/Agent/Trace/Dataset·role/manifestpin/URI/경로/예외는노출하지않는다. 유효ID의requesthash는lookup실패에도유지한다.

## 한계·현재성

기존Store.get은body전체를읽고json.loads한다. 선택metadata상한은파싱이후범위라boundedDBparser·전체RAM/IO/CPU하드상한은아니다. store_read_observedtrue도stored_job_origin_verifiedfalse를바꾸지않고현재Registry/assetbytes/manifest·TOCTOU/실제executor·ACL/READY·과학/학습승인은확인하지않는다. supplied는caller선언이며실제executor포착이라고인증하지않는다.

원본/원장/lock/분할/모델/Job·Registry쓰기를하지않으며legacy역채움도없다. 새API/UI/CLI/executor체인미연결내부adapter라이번직접UI/프론트재시험/브라우저는없고79/80카드가현재executorfalse를유지한다. 기존후보4/원본5차단·나지부족·terminal2missing/예약136,314,880B는그대로다.

## 시험·실제 Store 읽기의혼합근거

관련12 PASS/1.416초·독립12 PASS/1.084초다. TempStore/fakeStore를이용해get1/invalid0·malformed반환OBSERVED/innerBLOCKED·missingKeyError안전경계·자원/프로그래밍/비교오류분리·15false/IOscope·입력불변/원문비노출·Job/expected인자없음을확인했다. fixturesetup의Store생성/put은합성준비이며adapter쓰기아니다. 반복시험을전체에합산하지않는다.

Root는Store생성자의DDL없이mode=ro subclass에서기존Store.get을재사용했다. 실제legacy2의로컬8replay는UNKNOWN4/BLOCKED4,missingget1/invalidliteralget0로총get9였다. catalog14/원Jobbody는불변이다. supplied는로컬선언복사/변조이며실제executorcapture/운영MATCH관측은없다. 운영API/POST·역채움·QA/훈련0이며readonly조회관측과pureinnerDB0을구분한다. 최종 전체 회귀는 844건 중 843 PASS·기존 Windows symlink 권한 제약 1 SKIP이며, 342.991초·종료 0이다. 관련 12개·독립 12개와 로컬 재생 8회를 이 수에 더하지 않는다. deterministic 경계시험은 통과했다. 이해에이전트는DB/명령/시험을실행하지않는다.

## 발표1분

“설정된 Store에서 Job을 한 번 읽고 기존 입력 대조 기능에 넘기는 작은 adapter를 추가했습니다. 요청번호가 잘못되면 읽지 않고, 못 찾음과 자원오류·반환관측을 구분합니다. 문서를 읽어 왔더라도 내용이 잘못되면 내부 대조는 차단되며 보관함의 출처가 인증된 것도 아닙니다. 실제 기존 두 Job을 읽어 로컬 선언을 재생했을 때 모름4회·차단4회를 관측했고 실제 실행기를 확인하지 않았습니다. Store의 전체 JSON읽기는 남아 있어 메모리 하드제한이나 현재 파일·실행 승인을 보장하지 않습니다.”

## 발표5분·10분

1. **0~1분:** 설정된 보관함과 주문 번호, 대조 담당자의 비유를 말한다.
2. **1~2분:** Job을 직접 받지 않는 이유와 정상 요청1회·잘못된 요청0회, 네 조회 상태를 설명한다.
3. **2~3분:** 보관함의 반환 관측과 내부 대조 결과가 다른 이유를 보여준다.
4. **3~4분:** 합성12개·독립12개와 실제 읽기9회·로컬 재생8회, 전체 회귀를 구분한다.
5. **4~5분:** 출처 인증과 메모리 상한이 없고 실제 실행기·새 화면은 연결하지 않았음을 말한다.

10분확장에서는KeyError선검사·get오류만catch/비교버그전파·15false·조회실패requesthash유지·Store신뢰구성책임을설명한다.

## Q&A

**get1이면 DB도 한 번만 읽나?** adapter의 get 호출 시도가 한 번입니다. Store 내부 SQL이나 파일 읽기 횟수는 별개입니다.

**OBSERVED면 정상 입력인가?** 값이 반환됐다는 뜻입니다. 손상된 Job이면 내부 대조는 BLOCKED입니다.

**Store에서 왔으니 출처 인증인가?** Store를 선택한 앱과 호출자의 신뢰 경계는 별도입니다. stored_job_origin_verified는 false입니다.

**실제 MATCH나 실행이 있었나?** legacy의 로컬 재생8회는 UNKNOWN4회·BLOCKED4회였습니다. 실제 실행기 전달이나 운영 MATCH는 관측하지 않았습니다.

**화면과 API는 바뀌었나?** 내부 adapter이며 공개 API·화면·실행 체인에는 연결하지 않았습니다. 기존 카드는 그대로입니다.

## 이후갱신

최종 전체·보존 근거를 읽고 INDEX·변경 이력·계약·Orchestrator·구조·용어·발표·FAQ·시연을 함께 갱신했다. 다음 단위는 PLANNED다. 설정된 Store에서 Job을 한 번 읽고, 유효한 저장 RECORDED를 확인한 뒤 현재 resolver의 한 번의 검증 결과와 비실행 대조하는 내부 preflight를 검토한다. 저장 근거의 유효성, 현재 integrity·quality·PUBLIC 진단, 저장 대비 현재 선언의 일치를 따로 표시한다. 현재 resolution이 BLOCKED면 pin이 같아도 차단하며, legacy의 과거 pin을 현재 Registry로 역채우지 않는다. 직접 입력 참조만 대상이고 전이 계보·기관 인증·TOCTOU·실행기 검증은 아니다. 기존 resolver는 Registry와 현재 자산을 읽으므로 전체 IO 0이나 메모리 상한을 보장하지 않는다. 아직 코드·API·UI·Workflow·실행 체인 연결은 없다. 전체개발/10분보고는계속한다.


## 최종 검증과 보존

전체 회귀는 **844건 중 843 PASS·기존 Windows symlink 권한 제약 1 SKIP**, 342.991초·종료 0이다. 관련 12 PASS/1.416초와 독립 12 PASS/1.084초는 반복 검증이며 전체에 합산하지 않는다. 기존 deterministic 경계시험은 통과했다.

실제 증거는 읽기 전용 Store로 기존 Job 두 건의 선언을 로컬 재생한 범위다. 재생 8회는 UNKNOWN 4회·BLOCKED 4회였다. 없는 Job 조회 1회와 잘못된 요청의 조회 0회를 포함해 Store.get은 총 9회였다. supplied는 로컬 복사본이므로 실제 실행기 전달 관측이나 운영 MATCH 성공이 아니다.

시험 종료 후 보호 참조 141개, 기존 코어 44개, 카탈로그 14개 기록과 기존 Job 본문이 그대로임을 확인했다. 이전에 추적하던 코드·데이터·시험·프론트의 변경 목록도 비어 있다. 이는 지정한 보호 범위의 비교이며 전체 워크스페이스나 원자적 snapshot 보장은 아니다. 운영 POST·capture 역채움·새 QA·학습·실행기 연결은 없었다.

공개 API와 기존 79/80 화면 계약이 바뀌지 않은 내부 adapter이므로 직접 UI 수정·프론트 재시험·실제 브라우저 검사는 하지 않았다. 기존 카드의 executor 검증 false는 유지된다. 원본 준비성 5차단과 후보 QA 4차단도 해제하지 않는다.
