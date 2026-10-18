# 152 — 나지 256 표적창을 기존 공유 예산으로 수집하는 최소 구현 RFC

상태: **PLANNED / 구현·다운로드·학습 미실행**. 이 문서는 다음 담당자가 실제 consumer 연결부터 구현할 수 있도록 입력·연결 지점·실패 처리·수락 조건을 고정한다. 148의 두 작업 실제 재개 성공과 구분한다. 이번 단위는 이 RFC만 작성하며 기존 코드·시험·데이터를 바꾸지 않는다.

## 1. 무엇을 해결하나

148은 수집기를 다시 작동시켜 적격 패치11개를 늘렸지만 신규 나지 픽셀은0이었다. 단순히 다음 일반 후보를 계속 받는 것보다, **이미 로컬에 있는 동년 Esri 참조에서 나지가 관측되는 작은 위치를 골라 그 위치의 Sentinel 영상256×256픽셀을 실제로 받는 연결**이 필요하다.

ML의 `evidence/integration/ml-resume-audit-20261018-local-banten-label-search.json`은 로컬 라벨 crop17개에서 반텐/validation의 나지256픽셀 이상·행정경계95% 이상인 후보10개를 찾았다. 10개 모두 검사한 기존 영상과256창은 겹치지 않지만 같은 중심의1024창은 기존 영상과 겹친다. 그래서 현재1024 전용 validator로 모두 거부되는 것은 예상된 결과다. 기존1024 계약을 몰래 약화하거나 후보의 window_size를1024로 속이지 않는다.

이10개는 **실제 로컬 약한라벨 바이트의 검색 결과**다. 동년 맑은 Sentinel 영상 선정·신규 source scene 분할검사·실제256 header·품질 마스크 적용은 아직 하지 않았다. '바로 다운로드할 수 있는 승인 계획', 독립 현장 정답 또는 학습 준비 완료로 부르지 않는다. 목표는 처음부터 큰 후보 생성기/진단기를 더 만드는 것이 아니라 선택한1~2개 후보를 기존 수집기까지 연결하는 것이다.

## 2. 실코드에서 재사용할 것과 정확한 공백

| 파일·함수 | 현재 동작 | 이번 최소 변경 |
|---|---|---|
| `backend/app/data/candidates.py:validate_candidate_plan` | window_size1024 고정, 기존/추가 중심의1024 footprint 중복검사 | 변경하지 않음. 별도256 계획 validator 사용 |
| 같은 파일 `footprint(lon,lat,crs,side)` | UTM 10m 가정의 side 매개변수 지원 |256 계획의 예상 footprint 보조계산에 재사용 가능. 실제 header 대신 사용 금지 |
| `scripts/collect_training_parallel.py:extra_jobs` | 기존 후보를1024 template config로 변환하고 laneB key 사용 | 그대로 보존. 별도 `targeted_bare_jobs`만 추가 |
| 같은 파일 `main/reserve/work/finalize` | 같은4GiB 원장,2worker,2초간격,최초429공유중단,중앙정산 | target-only opt-in도 같은 경로로 연결. 두 개까지만 실행 |
| 같은 파일 `continuation_jobs` | 시작 snapshot의 pending key/config를 검산하고 명시적으로 제외 | 기존중단2개의 예약/파일 보존에 재사용. 임의재시도/환불 없음 |
| `scripts/collect_samples.py:collect_windows` | window_size1..1024, 동년Esri, SCL/6밴드/마스크·교정/계측/종료 보고서 | window_size256 자체는 이미 지원. scene 선택 veto와 실제 source footprint guard 연결이 필요 |
| 같은 파일 `select_quality_candidate` | 구름/중심SCL 기준으로 후보를 선택 | 선택 전 다른split의 scene_id 제외, 동시worker 선택scene 등록 hook 추가 |
| `backend/app/data/service.py:_read_cog_window_impl` | bbox **중심**을 원본CRS로 변환하고 src.index로 내림 후side 픽셀 읽음 | HTTP/계측 코드는 재사용. bbox가 실제 crop 경계를 지정하지 않는 점을 별도 guard로 검증 |
| `scripts/collect_training_grid.py:materialize_patches` |256 배수 source를 나눔. image/label/quality 격자검사, valid≥.8/inside≥.95 |256 source면1패치 생성 가능. target mode에서 기존경로 덮어쓰기 방지와 actual-footprint 검산을 호출 전에 추가 |
| `backend/app/data/budget.py:CollectionLedger` | 먼저예약, pending 자동재실행 거부, 정상계측종료만 정산 | 변경하지 않음. 전역예산 추가/초기화 없음 |
| `backend/app/data/parallel.py:run_two_workers` |2개씩 제출, 중앙reserve/finalize, 첫429새제출중단 | 그대로 재사용. 실제 scene 간 충돌을 worker-local 판단만으로 통과시키지 않음 |

새 구현의 권장 소유 파일은 `backend/app/data/targeted_bare_collection.py`(계획 검증·job 변환에 필요한 순수/로컬 검사), `scripts/collect_training_parallel.py`(명시 입력 배선), `scripts/collect_samples.py`(선택/수신 header guard), 새 집중시험이다. 새 standalone 진단 CLI만 추가하고 실제 collector를 미연결로 남기는 것은 수락하지 않는다.

## 3. 명시 입력 계약 v1

새 옵션은 `--targeted-bare-plan <workspace data 아래 상대 JSON 경로>`다. `--candidate-plan`과 함께 주면 시작 전 거부한다. **target-only mode**이므로 `v2_jobs/extra_jobs` 일반 큐를 뒤에 붙이지 않는다. 기본 명령과 기존1024 후보 입력은 그대로 유지한다. `--execute`가 없으면 새 계획만 출력/저장하고 HTTP0, 원장예약0이다. 실제 실행에는 `--execute --continue-unrelated-pending --max-batches 1|2`가 필요하며0(무제한)은 이 모드에서 거부한다.

초기v1은 province=`banten`, fixed_split=`val`, window_size256, reference=`esri_io`, source_taxonomy_code=`8`, 연도2020~2025만 허용한다. 다른주·split의 확장은 별도 변경이다. 후보는 아래1~2개만 caller가 명시 선택한다. 순위10개 전체 자동 소비는 하지 않는다.

최상위 exact 필드:

| 키 | 필수 값/검사 |
|---|---|
| `schema_version`, `kind` | 정확한 int1, `TARGETED_BARE_256_COLLECTION_PLAN` |
| `proposal_ref` | exact `{path,sha256}`. 위 ML 검색 JSON의 원바이트 pin |
| `current_manifest_ref` | exact `{path,sha256}`. 실행하려는 현재 aggregate의 원바이트 pin. 검색 당시53MB manifest와 다를 수 있음 |
| `boundary_ref` | exact `{path,sha256}`. 현재 selected-six.geojson과 고정 SHA |
| `policy` | exact `{window_size:256,source_taxonomy_code:8,minimum_declared_bare_pixels:256,minimum_valid_fraction:0.8,minimum_inside_fraction:0.95,maximum_new_batches:1|2}` |
| `targets` | 길이1~2. 중복 target_id/동일창 거부. 각 필드는 아래 표 |

target exact 필드:

| 키 | 값/검사 |
|---|---|
| `target_id` | caller가 붙인 안전한 ASCII ID1..40자 `[A-Za-z0-9_-]`. 전체 계획 내 고유 |
| `proposal_window_index` | 검색 JSON `ranked_windows`의 정수index. 해당행의 값과 아래출처를 교차대조 |
| `province`, `fixed_split`, `year` | `banten`, `val`, int2020..2025. 제안행·source 라벨 연도근거와 일치 |
| `source_label_ref` | exact `{path,sha256}`. `source_crop_path/source_crop_sha256`와 동일. data-root 내부 regular GeoTIFF |
| `source_lineage_ref` | exact `{path,sha256}`. 해당 라벨의 기존 source annual report. report의 year/label_year·Esri source URL의 연도·source_crops 경로/SHA를 실제 라벨 ref와 교차대조. 경로 이름만 보고 연도를 추정하지 않음 |
| `source_label_window` | exact int4 `[col_off,row_off,256,256]`, 비음수·native header 범위 안. 제안행 local_window_xy에 대응 |
| `source_label_grid` | exact `{crs,transform,width,height}`. 파일 header의 CRS/affine6/크기와 일치. north-up 10m/1band integer Esri crop만 수용 |
| `target_bbox_wgs84` | 유한한4수. 위 native window의 4corner를4326으로 변환해 재계산한 envelope와 허용오차1e-8도 이내 |
| `target_footprint_native` | exact `{crs,corners}`. source_label_window의 실제 affine로 계산한4corner. WGS envelope만으로대체하지 않음 |
| `declared_bare_pixels` | 실제 같은창을읽어 source code8 계수와 일치하고≥256. 제안값을 그대로 신뢰하지 않음 |

JSON은 strictUTF8·중복키/NaN/Infinity/bool-as-int 거부·extra필드 거부·입력1MiB상한·bounded 구조를 적용한다. 모든path는data-root 상대경로로 제한하며 resolve 후 root경계·regular file·같은파일alias·입력변경을 검사한다. 서명URL·임의HTTP endpoint·임의 Python callback·새output-root는 입력받지 않는다. evidence의proposal_ref만 workspace evidence 아래 읽기전용 예외를 명시한다.

검색 당시 `source_manifest_sha256=cdc374…`를 현재aggregate SHA처럼 재사용하지 않는다. proposal의 역사적 출처는 보존하되 current_manifest_ref를 새로 pin하고 원본라벨SHA·실제header/픽셀·현재영상/예약과의겹침을 다시검사한다. 읽은파일은 검사전후 byte/SHA/stamp를 대조하고 바뀌면 거부한다. 이것은 다중파일 원자snapshot이나 OS sandbox가 아니다.

## 4. 네트워크 전 공간·예약·분할 검사

1. 기존 실행 collector 부재와 execution lock 단일소유는 Root handover 절차로 확인한다. 새옵션은lock을삭제/이동하지 않는다. 현재148 정상종료후lock없음은 새실행직전 재확인이필요하다.
2. 읽기전용 current aggregate에서 **적격뿐아니라 비적격·historical source-window**의 실제image경로/SHA/header를 deduplicate한다. 256 patch들의실제 footprint도읽는다. 기록bbox는중심AOI일수있으므로 실제영상범위의대용으로사용하지않는다.
3. 원장모든pending의config·partial header를읽어 보수적인예약 footprint를구성한다. 실header가있으면사용하되 전체예정창도합친다. 기존미완료2개는1024×10m 예상창에native픽셀 snapping·SWIR보조범위여유를더한다. geometry를확정할수없는pending이면그지역target을 BLOCKED로두고건너뛰거나다른ID로우회하지않는다.
4. 새target의256 native polygon과 기존성공/비적격/예약창·새target서로의 겹침을 공통미터CRS에서검사한다. **년도·province가다르더라도positive-area겹침을거부**한다. 라벨참조crop과겹치는것은정상이며영상중복과구분한다. 단순touch는 허용하지만 actual snapping의여유안전대를포함해최종검사를통과해야한다.
5. planned primary10m256 footprint 외에SWIR20m `130×130` 및SCL128의 보조원본범위도계산한다. 새raw-support영역과기존raw/source/pending이겹치면v1은보수적으로거부한다. 다른CRS/회전/unknown resolution이면추정통과시키지않는다. 이때현재10후보중일부/전부가거부될수있으며 surviving수량을미리보장하지않는다.
6. 원장상기존key/config충돌을검사한다. 새jobkey는`target256-bare-banten-<year>-<target_id>-<plan_sha12>`로고정하며id재부여로겹침을우회하지않는다. `source`/`patches`/target evidence의해당job디렉터리가존재하면이초기v1은재사용/덮어쓰기하지않고거부한다. 동일계획재호출이기존정산key면기존ledger skip만허용하며새쓰기없음을확인한다.
7. 기존pending2는`continuation_jobs`로제외하고전액136,314,880B를보존한다. 148이끝난현재잔여2,341,906,244B는과거관측이며실행시같은ledger에서재조회한다. target당기존상한65MiB(COG64+metadata1)로예약한다. 2개최대130MiB·기존4GiB한도·물리3000상한을유지한다. v1은작아서싸게받을것이라고예약상한을임의낮추지않는다.

## 5. 실제 job과 기존 collector 연결

`targeted_bare_jobs`는검증한target에서기존build_batches의해당province geometry/split만재사용한다. config는`years=[year]`,6논리밴드,`window_size=256`,`aois=[{id:target용안전ID,province_id:'banten',bbox:검증한target_bbox}]`, Esri동년라벨·기존cloud/SCL/finite기준·재시도0·기존예산을명시한다. nominal_patches=1이다. 기존일반모드의전역비교는16개를미리예약하는보수적3000cap인데target모드만job.nominal_patches를사용하되그값은입력이아닌검증결과1로고정한다.

work순서는기존reserve→config/selection-context저장→collect_windows→source검증→materialize_patches→worker-result→finalize이다. target provenance를config와source report에별도기록하고일반1024source선언으로위장하지않는다. `selection_context`의priority는source code8로고정한다. 기존forest deferral은보조판단이지256target의실제라벨검산대체가아니다.

**source scene 분할누출을 받기 전에 막는 최소hook:** 현재manifest와모든기존source STAC metadata에서`scene_id→fixed_split集合`를구성한다. `select_quality_candidate`에옵션`candidate_acceptor(item)`를추가하고SCL fetch 전에호출한다. target val이선택하려는scene이다른split에있거나이미복수split이면제외이유를기록하고다음STAC후보를본다. unknown identity는제외한다. 같은split의동일scene은물리창비중복검사를통과한경우에만허용한다. 두worker의신규scene선정도하나의공유lock/table로등록하여검사와claim을같은critical section에서수행한다. table/lock은caller가만들고일반모드기본hook=None을유지한다. 실패후scene claim 해제는같은owner인지확인하며이미합산된claim은유지한다.

scene분할문제가현재이미1건존재하므로'기존scene충돌0'을전역사전조건으로삼아전부막지않는다. **새target이다른split과동일scene을추가하지않는것**과기존충돌미해결을분리한다. 기존train/val/test배정을이기능이변경하지않는다.

## 6. 수신한 실제 header·기하·라벨 재검사

`service._read_cog_window_impl`은bbox의면적을clip하지않는다. bbox중심을원본CRS로변환한뒤src.index의내림으로native pixel중심을결정하고side를읽는다. 따라서라벨256창bbox를전달해도다른nativegrid의Sentinel256범위가정확히같다는보장은없다. 첫B02fetch직후`actual_source_guard`를호출해나머지5밴드대량수신전에다음을확인한다.

- width=height=256,6밴드의기준이될B02 CRS/affine이유효한north-up10m grid다. raster가장자리clip으로작아진창·회전·unknown CRS·10m아님은거부한다.
- 계획target nativepolygon과실제B02 four-corner footprint를동일미터CRS로변환한다. v1의명시기하허용치는corner최대편차≤15m 및intersection/union≥0.98이다. 이는단순src.index snapping한픽셀정도를허용하는설계수치이지과학적품질기준이아니다. 독립합성시험에서pixel경계·CRS변환·tileedge를확인해유지/수정근거를남긴다.
- 실제footprint가계획polygon의허용영역안이어도기존/예약/다른target polygon과positive-area겹치면거부한다. 작은허용오차가중복허용치로쓰이지않게분리한다. SWIR/SCL실header도앞서예약한보조영역안인지검사한다.
- B02에맞춰라벨nearest/SCLnearest/SWIRbilinear를맞추는기존코드를그대로사용한다. 완료image/label/quality header격자가완전히같고source label년도가동년인지검산한다.
- actualimagefootprint의province inside≥.95,quality/AOI/finite/nonzero/label≠0결합valid≥.8,그valid안의source code8≥256을최종256패치에서다시센다. preview의나지수가충분해도SCL/경계적용후모자라면`TARGET_BARE_SHORTFALL`로보고한다. 기존valid/inside기준을낮추지않는다.

선택/기하/나지조건을통과하지못한source는수신실패와구분한terminal상태를남긴다. 이미쓴새jobraw/계측근거는그대로보존하고기존파일은변경하지않는다. 최종target을통과한패치만이번target-modeaggregate추가대상으로삼는다. '물리파일은있지만집계보류' 상태와'quality_eligible패치'를명시적으로구분한다. 집계제외를원장전송비용삭제/환불로연결하지않는다.

## 7. 새 파일 쓰기와 장애 경계

target source/patch 경로는실행전exclusive mkdir로소유권을확보하고기존경로가있으면거부한다. 현재materialize_patches의`mkdir(exist_ok=True)/rasterio.open('w')`를그대로모든경로에안전하다고부르면안된다. target만별도exclusive wrapper와preflight를사용하고기본materializer경로정책은그대로둔다. config·원본crop·영상·마스크·라벨·patch는새target하위에만쓴다. 유일한기존공유쓰기는기존reserve/settle원장및중앙aggregate/run-result정상갱신이다. 원본옛scene/patch/분할/모델·과거원장·옛pending은불변이다.

최소v1도원장→aggregate→run-result가여러파일이므로원자commit이아니다. 신규worker terminal에target planSHA/configSHA·scene identity·source/patchSHA·전송계수·목표판정·집계여부근거를남기되이것만으로durable journal/exactly-once를구현했다고표현하지않는다. 실패지점주입시험에서생긴미정산pending은전액보존·자동재시도금지다. 실제재개는정산coordinator설계/수동인계의별도후속이다. 기존110순수commit선언검사가실제journal을대신하지않는다.

SCL/B02 단계에서거부해도사용한metadata/COG본문은기존계측에따라새job만정산한다. 계측불명확·finally실패는예약전액보존한다. 첫HTTP429는전체공유회로로중단하고후속target/다른주/연도우회호출을하지않는다. 요청간격최소2초·2worker·자산재시도0과운영중복실행금지를그대로유지한다.

## 8. 구현 순서와 수락 조건

**첫 구현단위:** strict targetplan validator/job변환 + target-only CLI배선 + scene veto/shared claim + B02/최종source guard + existingreserve/work/materialize/terminal/finalize연결을같은단위로만든다. CLI가계획검사만끝내고실제consumer를남기는완료보고는하지않는다. 필요하면소유영역을validator/collector와독립시험으로나누되같은파일동시편집을피한다.

### TESTED_SYNTHETIC로 확인할 것

1. Temp GeoTIFF/경계/원장/검색제안으로실제CLI `--execute` 경로를돌리고HTTP만명시Mock한다. 선택한256target1개가소스256→patch1개→정상원장정산→aggregate/run-result에정확히1번추가되는것을확인한다. helper만검사하고연결시험을생략하지않는다.
2. 기본1024모드·기존후보validator의동작과SHA/예약정책을보존한다. 새옵션없을때새validator/scenehook0회,혼합옵션거부,실행플래그없을때HTTP0/예약0,수량0·3·무제한거부를검사한다.
3. 잘못된SHA/경로alias/year/CRS/affine/창크기·staleaggregate·changedlocalcrop·중복target·기존 성공/비적격/pending/새target서로겹침·보조footprint충돌을네트워크전에거부한다.
4. STAC같은scene이다른split이면SCL/B02요청0,동시에선택한두workerclaim충돌도거부한다. 기존scene분할문제는그대로경고하며target실행성과로지우지않는다.
5. service의centerfloor/반픽셀/10m경계/다른CRS/tileedge/20mSWIR패딩을실제Temp nativeheader로검증한다. planned허용내라도actualoverlap이면집계0,이미쓴raw보존/비용계상은남는다.
6. quality·province·bare기준충족과각각1단계미달을분리한다. source code8와model class7을혼동하지않고실제validmask적용후계수한다.
7. 예상치못한worker예외·터미널쓰기실패·settle후aggregate쓰기실패·run-result쓰기실패를명시fault injection한다. oldpending2/과거자료불변·새pending보존·자동retry0을확인한다. exactly-once성공주장은하지않는다.
8.2worker/중앙reserve/finalize·2초spacinghook·첫429이후새HTTP0·65MiB예약상한·같은4GiB·3000cap을기존관련시험과연결검증한다.

### VERIFIED_REAL_LOCAL로 확인할 것(HTTP0)

현재ML제안10개/실제라벨header·픽셀을읽어caller가선택한1~2개를새계약으로변환한다. 현재aggregate·모든기존source/pending·보조 footprint까지재검사하고살아남는수량과거부이유를남긴다. proposal당시와현재manifestSHA를분리하고입력파일전후불변을확인한다. **살아남는후보0이면곧바로다운로드하지않는다.** 256후보위치/guard조건을재검토하는작업으로보고하며검사를우회하거나1024기존validator를완화하지않는다.

### 운영 실행으로만 확인할 것

Root가실행직전singlecollector/lock·backup·원장·현재고정pin을확인한후새plan의최대2target만실제실행한다.각target의STACscene·실제header/footprint·품질/inside/bare계수·계측/정산/terminal·신규집계와기존자료보존을독립감사한다. 완료보고에는'다운로드시도', '영상수신', '표적조건통과적격패치', '기존학습차단해소'를별도숫자로쓴다.

한validation나지패치가256이상이되어도5개기여패치·분할별0.5%·기존scene누출·독립라벨조건이자동해결되는것은아니다. 새전체readiness검사로남은차단을보고하고학습을별도승인/조건충족없이실행하지않는다. 이RFC/작은표적수집완료를전체플랫폼완료로표현하지않는다.

## 9. 문서·화면 인계

완료구현과집중/관련시험·실로컬검사·실제운영실행증거를각각구분해152의구현후속문서에기록한다. Root는이해담당에게완료코드와증거를전달해쉬운설명→이론→코드/데이터→시험→대본→Q&A, INDEX·변경이력을함께갱신한다. 이번은내부CLI/수집계약으로UI/API변경없음;화면에실행버튼을추가하지않으므로브라우저재검증은필수범위가아니다. 향후표적수집상태를화면에보이면API·상태/오류·인증계약을별도확정해web_ui담당에게인계한다.
