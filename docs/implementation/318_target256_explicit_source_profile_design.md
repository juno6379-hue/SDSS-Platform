# 318 — target256 명시 source profile 연결 설계만

상태: **PLANNED / 코드 구현·적용·실수집0 / target256 소비 BLOCKED 유지**.317이 확인한 prepare_targeted_bare_jobs의source64MiB 제한을 좁은 격리 변경으로 보완하기 위한 API/호출/시험 설계다. 실제source/proposal/원장/라벨/모델 읽기0, 시험/import/native/HTTP0·공유제품 편집0이다.316 읽기검토179의실행과 별도이며 설계로 gate를 해제하지 않는다.

## 현재 호출 경로

| 단계 | 코드 위치 | 실제 source 소비/전파 |
|---|---|---|
|179 검토·선택|scripts/review_bare_targets179.py:39,119,147–153|review의source128/167inventory128, select_plan은schema1 plan에current_manifest_ref를복사|
|175 로컬계획|backend/app/data/targeted_bare_plan.py:61,108|현재exactplanv1만수용, current_manifest_ref64MiB 읽기·listed image/sourcewindow metadata 사용|
|170 사전검사|scripts/collect_targeted_bare.py:130–176|currentaggregate128/ledger8을읽고149행175호출→162행167inventory→166행재핀/physical재검사|
|170 실제 coordinator|같은파일179행이후|전역lock내validate_request·검증aggregate로scene_registry생성·sharedwindows/worker/finalize·전역예산예약|
|176 scene/window guard|backend/app/data/targeted_live_guards.py:66이후 및scene_registry|175가 만든job/target와검증aggregate의sourceSHA·sharedscene/windowregistry소비;manifest를직접파일에서읽지않음|
|167 support inventory|backend/app/data/targeted_inventory.py:31,55–58,162–164|manifest128/ledger8·history전체/원장보고서support/pendingconfig와B02·전후핀|

175/176은 별도175.py/176.py CLI 파일명이 아니라 위 모듈/API의 구현 번호다.171/다른모델 연결을 이 단위로 확대하지 않는다.169/176의256·scene/window/split/B02정렬10.000001m·품질/SCL·supportclaim 코드는 변경하지 않는 설계를 우선한다.

## 버전과 명시 선택 제안

권고는 **새 outer request schema_version3 + local plan schema_version2**다. 현재outerv2는232의local_support_profile용 exact keyset을이미가지므로새필드를슬쩍넣으면기존동작이달라진다. outerv1/default2GiB, outerv2/exact3GiB, planv1/source64MiB는 원바이트 출력·key·configSHA·실패코드를 그대로 보존한다. planv1에프로파일이없어도현재ambientcontext가128이라는이유로자동상향하지않는다.

새outerv3는기존outerv2필드와정확 `manifest_profile:{name,sha256}`만추가하고, 새planv2도기존plan필드와같은marker를추가한다. 값은기존 `bounded128m-3000-v1`/`db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4` 하나뿐이다. 둘중하나누락·불일치·bool버전·알수없는키/marker/name·임의cap은어떤파일읽기/예약/네트워크보다먼저거부한다. 소스파일크기에따른자동선택/재시도/legacyfallback은없다.

새planv2를 만드는순수adapter를제안한다. `bind_explicit_source_profile(plan_v1, marker)`가deepcopy로planv2를만들고원plan을변경하지않는다. source_ref는기존명시핀을유지한다. 기존232 inventory_kwargs는v3를알지못하므로새helper가v3/planv2를먼저완전검증한뒤3GiB옵션전용내부envelope를명시적으로구성한다. 이envelope는검증된v3에서manifest_profile만분리하고schema2+기존inventory keyset으로정확투영하는순수adapter이며unknown입력을legacy로fallback하는것이아니다. 원requestcanonical/GO/receipt는원v3전체에결속하고내부envelope로바꿔재사용하지않는다.232파서원판을보존하면서두profile의역할을분리한다. 현재179 select_plan default출력은변경하지않고Root가별도v2작성권한을주어야한다. 새plan/requestcanonical에marker가들어가므로계획SHA·새target256jobkey·선택설정/예산예약정체성이달라질수있으며과거175/170실행proof·config·approval를재사용하지않는다. 변경config의실제digest계산은기존규칙을그대로쓰고미래expectedSHA를발명하지않는다.

## API 제안과 역할별 한도

새격리helper 후보 `backend/app/data/targeted_source_profile.py`에순수계약검사와명시scope진입을둔다. 예시API는 `validate_profile_contract(request, plan)`/`operation(marker)`/`read_pinned_json(root, ref, role, maximum)`다. 정확 marker검사→같은operation scope→각호출의role/기존개별cap·expectedSHA검증→depth/node/row검증순서다. 상한 numeric은caller임의선택이아니라코드의고정역할표에서가져온다. 역할이불명확하면실패한다.

source만128MiB이며 scenes+historical_noneligible 합3000, depth32/node4000000·누적JSON I/O16GiB를기존profile descriptor로재사용한다. proposal2MiB/boundary2MiB/baseconfig2MiB/lineage8MiB/ledger8MiB/request2MiB/receipt원기존cap·라벨/TIFF64MiB·support3GiB는그대로다. JSON source128을모든JSON/래스터에적용하지않는다. 기존read_metadata의status_report16/readiness16을사용한다는이유로legacyledger8/lineage8을몰래16으로늘리면안된다.

정확per-call최대8등을cap-before-open과동일fd실읽기에결속하려면기존profile reader에 **기존default불변인 선택적고정최대인자**를추가할지,새adapter가공용boundedread/parser를이한도로재사용할지구현전결정이필요하다. pre-stat8 확인뒤role16 reader를부르면그사이성장한9MiB를읽을수있어충분하지않다. post-read cap검사만하는안도거부한다. 이공용API변경은현재승인/편집하지않았으며별도소유와회귀가필요하다.

엄격중복키/nonfinite/UTF8/BOM·JSON문법검사와새source구조검사는공통parser를재사용한다. resourceerror는일반PLAN_INVALID/LOCAL_INPUT_UNAVAILABLE로삼켜다음예약으로넘기지않고상위coordinator까지전파해야한다.175가현재catch하는ValueError/Exception과새ProfileResourceError의관계를명시적으로처리해야한다. 예산실패는execution_supportedfalse로보존하며gate를바꾸지않는다.

## 단일 scope·계측 누락 방지

170 CLI에서requestbootstrap은2MiB상한/정확SHA·최종파일identity를먼저검산하고,실읽기bytes를명시scope가활성화되는즉시누적debit하는기존309계약을참고한다. markedrequest 없이는scope를생성하지않는다. CLI→run_targeted→lock내validate_request→175/167의후속read/hash→source/ledger재핀은동일ContextVarbudget을재사용한다. 중첩함수가새16GiBbudget으로초기화하면안된다. app/backend import alias는기존공용state를재사용한다.

계측목록은source/current-snapshot/hash반복·proposal·boundary·ledger·config·lineage·workerreceipt·request/plan·출력JSON을role과cap으로명시한다. `_pinned`는TIFF에도공용으로쓰이므로모든_snapshot호출을sourceJSON으로취급하거나전역교체하지않는다. raw raster는기존별도physical/support한도이며JSONbudget으로분류하지않는다. cachehit은identity/pin을재확인하되실read0이면0으로계상한다. 성장/교체/alias/심볼릭·reparse·hardlink정책은기존strict읽기계약과동등이상으로고정한다.

**175만decorate해서전체metadata16GiB연결완료라고말할수없다.**170worker의ThreadPool/context전파와config/state/report/receipt writer가scope밖이면누락이다. 해당경로의실제메타데이터read/write전체를포함하겠다면thread마다같은budget참조를넘기고공용lock으로charge해야한다. read/write부분실패의실측/unknown처리와finalize영수증까지role/cap이필요하다. 원격COG+metadata1MiB계측과로컬JSON16GiB는서로대체하지않는다.

따라서첫작은내부구현은 **격리된명시localpreflight소스연결/합성검증까지만** 마감하고executiongate는false로둔다. 전체실coordinator메타I/O까지정의·구현·시험되지않으면Root가실연결을보류해야한다. 범위를좁힌것을전체계약완료라고보고하지않는다.

## 제안 파일 소유와 작은 단계

1. 격리workspace에관련코드/시험사본만복사하고mainbaselineSHA·신규부재·원바이트archive/manifest를동결한다. 운영data/model/원장/label복사0이다.
2. 새targeted_source_profile helper와순수version/marker검사·고정role source reader·기존175adapter경로를구현한다.175의legacy경로는분기전원동작그대로유지한다.시험은Temp합성만이다.
3. 별도coordinator소유가170CLI/lock내재검사/167inventory의동일scope·expectedpin·metadata계측·thread/write경로를연결한다.176에는검증된aggregate/sourceSHA를넘기며parentguard조건을바꾸지않는다. 전체완료전실집행0이다.
4. 독립정적검토/적절회귀/freeze→Root현재baseline대조/명시적용→readonlypreflight→별도Root소단위실행승인으로나눈다. 설계/시험성공은운영승인이아니다.

초기후보파일은새helper·`targeted_bare_plan.py`·`targeted_inventory.py`·`collect_targeted_bare.py`와새Temp시험이다. per-callcap공용reader확장이필요하면manifest_resource_profile.py/관련시험도 **별도명시소유승인**을받는다.232profile/199guard/255diagnostic/246/265/기존UI/API파일은불필요하게편집하지않는다. 이문서는코드수정GO가아니다.

## 합성·회귀 시험 계획만

-legacyplanv1/outerv1/v2는원판동일fixture에서반환dict/오류코드/canonical/jobkey/configSHA/falsegate를exact비교한다. profile없음·default64초과는예전FILE_LIMIT로막히고실행이나자동profile선택이없어야한다.
-새v3/planv2 marker양방향누락·mismatch·unknown/bool/version/key오염·현재source핀변조는파일open/예약/HTTP전에실패해야한다. source128+1/3001행/history포함/depth33/node4M+1·누적IO16GiB초과를Temp/작은budget모의로거부한다.운영실자료/대형래스터재스캔0이다.
-64MiB초과128이하의TempJSON은명시경로만통과하며boundary/config/ledger/lineage를source128로잘못늘리지않는다. sizegrowth·fd교체·parentalias/reparse·일부read/write·cachehit0read·最終sourcepin교체검사를포함한다.
-단일scope중첩/동일budget/dualimport/thread분리·같은operation의다중workercharge·resourceerror상위전파·예산실패후예약0/HTTP0·falsegate불변을확인한다.실worker원격호출은fake로차단한다.
-격리CLI배치에운영data/외부baseline폴더가없어도동작하는portableSHA고정fixture를쓰고누락/변조는failclosed/fallback·skip0으로검사한다.실pipeline실행대신stdout/exit/요청·proof호환을합성검증한다.

모든시험은계획이며아직실행0이다. 원격4GiB/2worker/2초/첫429/物理3000/최대2target·256/최종80%·주내95%·B02정렬/split/support/oldpending·학습false를유지한다.316검토결과가별도로완료돼도이설계자체는취득/품질/독립정답/학습게이트증거가아니다. Root는최종파일소유/API/단계를승인해야하며실UI변경과이해자료갱신은완료구현뒤별도인계한다.
