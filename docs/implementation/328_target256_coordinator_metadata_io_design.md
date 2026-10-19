# 328 — target256 실coordinator 명시 profile 연결 설계만

상태: **PLANNED / 구현·시험·운영I/O0 / 실집행 BLOCKED 유지**.327 공유 회귀 중인 제품·시험을 수정하지 않고 코드만 읽었다. 실제 source/원장/모델/proposal/label/운영data 읽기·복사0, worker/예약/HTTP/native/대형검증 재실행0이다.327의 합동 시험포장 실패와 Root 교정은 별도 소유다.325 동결판·원로그를 소급 수정하지 않는다.

이번 설계는325의 LOCAL_PREFLIGHT_JSON_ONLY를170 CLI/전역lock/worker/finalize까지 확장할 때 필요한 실제 호출·JSON I/O 목록이다. 목록 작성이나325 local성공으로 전체 계측·수집 연결 완료를 주장하지 않는다.

## 1. 명시 경로의 호출 계약

현재 `collect_targeted_bare.py:329–342` CLI는2MiB request snapshot→_json→run_targeted, run_targeted:179–197은 execute일 때 전역execution lock을 잡고 validate_request를 호출한다. validate_request:133의232 exact parser는outerv1/v2만 수용하고149는legacy175/source64entry다. 따라서현재공유적용만으로v3가실수집경로에연결된것이아니다.

새v3경로는다음순서로설계한다.

1. request bootstrap은2MiB/strict JSON·원문identity를bounded하게읽는다. exactouterv3/planv2/양쪽128marker·3GiBmarker·원v3canonical을319로검증한다. 크기/ambientcontext로분기하지않고defaultv1/v2는기존코드/오류를그대로쓴다. bootstrap실읽기bytes는명시operation활성화직후누적debit한다.
2. 명시128/16GiB operation을단한번생성하고source128/3000scenes+history/depth32/node4M·고정role표로모든JSON read/hash/write를연결한다.325와중첩시기존budget참조를재사용한다. 현재서버용sourceprofile JSON을자동갱신하거나운영데이터를작게복제하지않는다.
3. 실행이면독점global-ledger.execution.lock 내부에서 **fresh validate**를다시수행한다. exactcurrentaggregate핀=plan.current_manifest_ref핀,현원장/oldpending·baseconfig/경계·원제안·local175명시경로·167 fullpending/support·physical3000을재검산한다. dryrun/316결과는예약권한으로재사용하지않는다.
4. 232옵션선택은319가검증한v3→내부v2 envelope의명시투영으로만한다. 원request/RootGO/receipt/key는원v3canonical에결속하고내부envelope지문을실행승인으로쓰지않는다.3GiB지원한도와128JSON한도는별개다.
5. sourceSHA에결속된검증aggregate를 `scene_registry(aggregate, source_sha256)`에전달한다.176 자체는manifest파일reader가아니며현재targeted_live_guards.py:137–142가scenes+history를고정split scene registry로만든다. sharedscene/window객체를worker마다새로만들지않는다. 실B02정렬/선택scene/window/split/SCL/80·95품질조건은변경하지않는다.

v3 sourceprofile은1024용candidate_metadata_policy가아니다.256경로에DEFICIT_AOI_BBOX_CONTAINS_V1이나candidate_metadata_filter를끼워넣으면265의side1024계약과충돌한다. metadata I/O 전달인자는별도로둔다.

## 2. 실제 JSON I/O 호출 목록

아래목록은코드상도달경로이며운영파일내용을읽은관측이아니다. 입력hash도실제bytes read로계상하고동일파일반복읽기·마지막재핀을생략하지않는다. rawTIFF/COG/XML/ETag/lock파일은이JSON표와구분한다.

| 호출 위치 | 실제 JSON I/O | 연결할 역할/상한 |
|---|---|---|
|170 main:335 + validate:138/166|request bootstrap, current aggregate 최초·재핀|request2MiB / source128MiB+3000/depth32/node4M|
|170 validate:141/142/167|ledger ref·active ledger·최종재핀|ledger8MiB|
|170 validate:148|base config.read_bytes|config2MiB|
|325 local175 helper/document + targeted_bare_plan|proposal/source/boundary/lineage JSON|2MiB/128MiB/2MiB/8MiB; 현재325reader 재사용|
|167 inspect:55/58/112/162–164|manifest/ledger/pendingconfig 및끝재핀|source128/ledger8/config2MiB; 전체support의TIFF는별도|
|170 physical_patch_inventory:79|모든worker-result를읽어미등록실물추적|workerreceipt8MiB(기존cap)|
|170 work:235/237 + grid.write_json:29 + samples.load_config:24|jobconfig 원자쓰기·UTF8config 읽기/period파생|config2MiB; 원configSHA와effectiveSHA 구별|
|samples.collect_windows:282|기존window-state 읽기/설정digest|state역할 필요(현재직접read_text 무상한)|
|samples.collect_windows:295/306/316/326/586|회로·전송예약·실측·실패·최종window-state 반복쓰기|state역할 필요; 매번실제쓰기계상|
|samples.record_event:62–64|collection-history.jsonl append|JSONL 단위/파일누적cap 신규명시 필요|
|samples.collect_windows:403/431|redacted stac-item.json / calibration.json쓰기|STAC localJSON1MiB 제안 / calibration config급2MiB 제안|
|service.search_stac→_json_response:219–220|원격STAC/signing JSON응답 실제본문read+parse|기존batch metadata1MiB 별도유지 + localJSON16GiB 실제read로도계상|
|service.register_local→_record:485–493|manifest 항목JSON 새파일쓰기|artifact-manifest역할 필요(현재write_text 무상한)|
|samples.collect_windows:587/604|batch annual-window-report 반복/최종쓰기|lineage/report8MiB 제안(기존후속lineage읽기8MiB와정렬)|
|170 work finally:270/274|window-state.read_bytes와worker-result쓰기|state/workerreceipt8MiB 제안|
|CollectionLedger._read:44/47 + sha256:10|active ledger JSON읽기와과거원장반복hash|ledger/과거원장8MiB;현재내부read_text/read_bytes 무상한|
|CollectionLedger._read:50–53|초기화분기의historical SHA·마지막run-result JSON|같은historical-ledger8MiB; 새v3에서자동초기화금지권고|
|CollectionLedger._save:61–65|reserve/settle의.tmp JSON쓰기→replace|ledger8MiB/실부분쓰기/identity;원전액pending 보존|
|170 finalize:293→grid.write_json|추가patch/source_manifest/error가붙은aggregate쓰기|source128MiB/3000행 구조·원문핀 version전이|
|grid.materialize_patches:205–207→service._sha|boundary GeoJSON source provenance hash|boundary2MiB JSONread 계상; image/quality SHA는TIFF별도|
|170 worker_started/finished/main:231/298/336/341|stdout JSON상태·완료·실패 record|개별JSONrecord cap/actualwrite·unknown 측정 필요|

원시STAC응답1MiB가pretty savedJSON1MiB이내라는보장은없다. 새v3의저장cap을1MiB로정하면형식팽창시저장전차단해야하며자동상향하지않는다. 기존개별cap이없던state/JSONL/calibration/artifact/report출력에위숫자/역할을적용하는것은 **명시v3의새tightening 정책 제안**이며Root가고정role표를승인해야한다. 아직선택·구현됐다고주장하지않는다. 기존v1/v2는원행동을유지한다. numericcap을caller에노출하거나모든JSON을source128로분류하지않는다.

`collect_training_grid.py` 전체CLI의baseconfig/build_batches/reference_preview 경로는170가함수로호출하는경로와구분한다.170는write_json/materialize_patches를가져오지만grid전체CLI·reference_preview를실행하지않는다. 실제v3worker가새로호출하는경로가생기면목록과fixture를갱신해야한다. service.download_asset의ETag/part는현재windowCOG경로와구분하고실호출되지않는것을계측완료로세지않는다.

## 3. API와 소유 제안

새격리 `TargetedExecutionJSONIO` adapter가고정role표·profilebudget·projectroot·expectedpin/versionmap을소유한다. read_json/hash_json/replace_json/append_jsonl/write_new_json/emit_json_record를제공하고각실read/write를같은budget에계상한다.325의maximum_bytes API로source외역할을원상한보다좁힌다. legacyAPI는metadata_io=None일때원함수를그대로호출하고ambient128만으로새경로를자동활성화하지않는다.

필요한명시인자후보는 collect_samples.load_config/collect_windows/record_event, grid.write_json/materialize_patches, service.search_stac/_json_response/register_local/_record, CollectionLedger의metadata_io다. 내부service._record와boundary hash까지인자가도달해야한다. 단지170의write_json만wrapper로바꾸면samples/service/budget의우회읽기·쓰기가남는다. v3scope만보고모든기존caller를전역patch하는방법은배제한다.

읽기는exact role/cap-before-open/동일fd/전후identity/pin·strictparser를사용한다. 원격JSON응답은batchmetadata1MiB를유지하면서16GiB localJSONoperation의actualread에도넣는다. XML본문은기존remote metadata예산에들어가지만JSONbudget과는분리한다. 서명URL/조회민감정보를로그에새로노출하지않는다. 실제sourceaggregate를쓸때는3000행/depth/node/bytes를 **쓰기전** 검산한다.

replace_json은고정rolecap/expected oldidentity·SHA,독점temp·actualbytewrite/flush/fsync·교체직전statepin을검사한다. aggregate/ledger는운영중의도적으로바뀌므로최초inputpin을끝까지그대로강요하지않고,해당owner가성공commit한새bytes/SHA만versionmap에전이한다. 외부교체는실패하고budget이나originalsourceprovenance는초기화하지않는다. scene_registry의seedsourceSHA는실행시검증된원input이며ownappend뒤미래원본까지검증했다는뜻이아니다.

## 4. ThreadPool·직렬 budget 전파

현재parallel.py:70은executor.submit(work,job)이며ContextVar는worker로자동전파되지않는다. 명시v3coordinator에서만work를감싸 **submit마다새copy_context()**를캡처하고그context.run(work,job)을worker에서실행한다. 같은Context객체하나를동시에두worker에run하면오류나므로재사용하지않는다. 복사된context에는 **같은Budget인스턴스참조**가들어가야하고worker별scope가새16GiB를만들면안된다.

reserve/finalize는기존처럼메인스레드에서만실행하고각worker의remote metadata1MiB컨텍스트는배치별로초기화한다. JSON budget은전체operation공유·직렬화한다. fileJSON뿐아니라remoteJSON본문을포함한다면room확인→실read→actualcharge를같은serialized transaction으로묶거나동등한예약프로토콜이필요하다. 확인뒤lock을풀고두worker가동시에read하면한도를넘긴뒤charge실패가날수있다. 기존Budget에는refund/reservation프로토콜이없으므로새기능없이단순공유변수만붙이지않는다.

가장작은안은최대1MiB JSON read 가능room을먼저검사하고그JSON요청/read/charge범위를serialized로두는것이다.이는metadata요청을직렬화하지만rawCOG/래스터전송과2worker계약은그대로다. JSONbudgetlock을보유한채future.result/ledger다른worker대기를하지않는다. filesystemledgerlock→JSONtransaction 순서와request/circuit lock의해제순서를시험해교착을막는다.

기존parallel기본API를바꾸지않고v3caller만contextboundwork를넘기는안을우선한다. 다만아래resourceerror전파분기는parallel의정확한오류구분이필요하므로그파일도별도소유승인을받는다. legacydefault는기존submit/stop_reason/예외결과를보존한다.

## 5. 오류가 예약·정산을 숨기지 않게 하는 계약

필수공백은parallel.py:59의reserve exceptValueError다. ProfileResourceError는ValueError파생이어서현재그분기에잡히면global_budget_remaining_insufficient로축약될수있다. v3자원오류는그분기보다먼저식별해추가submit중지·이미접수된future회수·기존finalize각1회시도뒤원오류를전파해야한다. 일반실잔여예산부족동작은legacy와같다.

collect_targeted_bare.work:266,collect_samples.collect_windows:579와내부라벨/후보/fetch의일반except,classify_error,167 inventory의ValueError/Exception도검토대상이다. 자원오류를searchfailed/PLAN_INVALID/LOCAL_INPUT_UNAVAILABLE로삼키고다음HTTP를계속하면안된다. optinv3에서명시resourceerror우선전파/공유stopEvent설정이필요하다. I/O자원중단과HTTP429회로는별도원인으로기록하고IO소진을rate_limit_active=true로위장하지않는다. 이미진행중전송은종료/계측을회수하고새요청만중지한다.

partialwrite는성공한실bytes만계상하고원래오류를보존한다. 새temp/append regularfile은동일fd/전후길이로알수있는범위만측정한다. pipe/stdout이나overwrite에서fstat길이차이0을실제전송0으로보면안된다. write가예외를내고실부분길이를알수없으면허용upperbound를보수계상하고JSON_WRITE_MEASUREMENT_UNKNOWN으로중단한다. 원격JSONread partial/unknown도같은원칙과기존provider1MiB보존이필요하다. 예산밖unmetered완료fallback은금지한다.

16GiB소진후workerstate/receipt/ledger정산도쓸수없을수있다. 새예산을발명하거나원pending을환불하지않는다. 예약전에는모든알수있는local검산/상한을끝내고,예약뒤실측/receipt가불명확하면현재batch의전액예약을보수적으로유지한다. finalization은한번시도하되JSONbudget이허용하지않으면 **정산/게시미완료·pending전액** 상태로Root후속감사에넘긴다. 전송실물·workerreceipt·등록aggregate가다를수있음을숨기지않는다. budget밖에서ledger를고쳐settled로만들거나성공terminal을쓰지않는다. 기존oldpending2의전액·원배열은항상보존한다.

## 6. 작은 격리 구현 단위와 시험 계획만

A단위: 새실행JSONadapter/고정role표와CollectionLedger의명시metadata_io만격리구현·Temp예산/부분쓰기/역사핀시험. 고정내부cap중미확정role을Root가먼저선택한다. 이단위는예약운영연결/HTTP0이다.

B단위: 170v3CLI/lock내freshvalidate→325명시175→167fullpending/support/source핀→176sharedregistry까지dryrun으로연결한다.169/176기존guard조건은수정하지않는다. source/ledger/물리·pending의동시변경·alias·v3canonical/새key/configpin을시험한다. executable gate는아직false로둔다.

C단위: 명시I/O 인자를samples/service/grid실제JSONreader/writer끝까지전달하고ThreadPoolcopy_context/serializedbudget·자원stop/finalize를합성subprocess에서연결한다. 원격은fake로막고state/report/ledger/receipt실Tempwrite만수행한다. 전체I/O목록이하나라도미연결이면전체16GiB집행연결완료라고마감하지않는다.

회귀는defaultv1/v2/legacyplanv1의원판반환·오류·canonical/key/configSHA·예산/429/submit/finalizeexact를대조한다. marker누락/오염·source변경/상한128/행3001/depth33/node4M·8MiBledger/lineage/2MiBconfig·unknownrole·copycontext2개가같은budget공유·서로다른operation격리·callback중mutation·부분/unknownwrite·cachehit0read·resourceerror상위전파/추가HTTP0·oldpending보존·finalize각1회·submit실패후reservation누락0이negative목록이다.

마지막한합성subprocess는baseline폴더없는Temp공간에서최대2 fakeworker·고정requestv3/planv2·고정source·모의STAC·작은GTiff만사용한다. 실제HTTP/open을가드하고호출을추적한다. source/input read·allJSONwriters·최종stdout까지예산장부와실byte를대조하고실행/정산/게시각단계와오류를분리한다. 신규64~128대형JSON/native/fullinventory반복시험을운영데이터에서하지않는다. portablefixture는자체포함/SHA엄격/누락변조fail·skip/fallback0이다.

327 시험실패는global sys.modules 부재가정을선행import와혼동한시험포장문제이며Root가시험1파일교정/전체회귀를소유한다. 이설계는그공유모듈을편집하거나시험을중복실행하지않았다. API/UI·이해자료는실완료코드/증거뒤Root가별도인계하며아직학습/원격품질/나지확보/전체개발완료를승인하지않는다.
