# 182. 부족 셀을 위한 추가1024 공간후보 로컬 제안

## 범위와 현재 상태

고정 g00~g03 공간 작업이 이미 소진되면 명시 주 우선순위177만으로 신규 작업을 만들 수 없다. 새 `scripts/propose_deficit_centers182.py`는 고정된 source·공식경계·공식config·기존lane-B plan을 받아 기존1024창과 겹치지 않는 추가 공간을 결정론적으로 제안한다. 기존 `backend/app/data/candidates.py`의 `validate_candidate_plan`을 통과하는 schema1 후보 파일을 새 경로에만 쓴다.

**TESTED_SYNTHETIC:** 최종 관련12PASS/18.974초·종료0(신규9·기존candidate3). **VERIFIED_REAL_LOCAL_GEOMETRY_ONLY:** Root가9차종료·안정source를확인한뒤명시지시하여12:09~12:10 실제로컬스캔·추가4후보를생성했다. **PLANNED/BLOCKED:** 전체support/pending 검토·collector 소비·실제 수집. 초기합성단계에는진행중인9차와겹치는운영스캔을실행하지않았으며,후속허가뒤새소유디렉터리에만사본/제안파일을썼다. 기존운영source/원장/모델/예약/lock/UI/기존177·179·180·parallel 소스 변경0, 네트워크·수집·학습0이다.

새 소유 파일은 위 script, `tests/test_propose_deficit_centers182.py`, 이 문서와 `evidence/integration/centers182-*` 증거다. 후속실제파일소유는Root가허용한새 `data/centers182-actual-20261018/`뿐이다. 로컬제안을실제수집으로소비하지않았으며아래실측과후속차단을구분한다.

## 입력과 출력 계약

CLI는 `--source/--source-sha256`, `--boundary/--boundary-sha256`, `--config/--config-sha256`, `--prior-plan/--prior-plan-sha256`, `--output`을 모두 명시한다. 예시 경로를 자동 선택하거나 caller SHA를 입력 문서 안에서 꺼내 신뢰하지 않는다. source/경계/prior/output은 프로젝트 DATA 안의 로컬 경로이며 config만 별도로프로젝트configs 안의명시파일도허용한다. 출력은 부모가 이미 있는 새 파일이어야 하며 기존파일·symlink·모호한Windows 경로를 거부한다. 실패한 부분 출력을 자동 삭제·재시도하지 않는다.

운영 실행 시 Root가 확인할 config는 `configs/first-group.collection.json`이며 원본SHA를명시해읽을수있다. 별도DATA 사본을사용한다면Root가원바이트SHA를대조해야한다. 공식경계는 `data/first-group-boundaries/selected-six.geojson`, 기존plan은 `data/first-group-training-esri-v2/lane-b-candidates.json`의 검토된 사본/원본 pin을 쓴다. 프로젝트밖의config나임의경로를묵시적으로허용하지않는다.

source는64MiB/3,000행, 경계/config/기존plan은 각각2MiB 상한으로 strict JSON과 SHA를 검산한다.6주 경계와 config AOI가 정확히 같은 공식slug집합이어야 한다. split은 기존고정정책을 재사용하고 caller가 바꾸지 못한다.

출력은 schema_version1·executed_network=false·collector_consumption_approved=false이며 candidates마다 다음을 기록한다.

- 정확한 province/fixed_split/spatial_window_id·연도리스트·reference=esri_io.
- window_size=1024·미터UTM grid_crs·lon/lat/WGS84 bbox.
- 공식boundary SHA·source snapshot SHA·snapshot 셀 부족량·실제1024창의 주내 면적비.
- class_presence_verified/actual_quality_eligible/execution_supported=false.

검증된 출력 SHA는 기존 validator의 source_sha256으로 반환한다. 추가 source/config/prior SHA·source GTiff header inventory·한도·거부횟수·target별실제적격/부족/후보수·full_pending_support_inventory_verified=false도 기록한다. 후보가 없으면 빈 candidates/대상별0을 반환하며 수집/품질 성공 수를 만들지 않는다.

## 결정론적 공간 선정

우선 대상은 **남동술라웨시2024 → 고론탈로2024 → 고론탈로2025**다. 각 셀의 저장 적격이28개 이상이면 그 셀을 건너뛴다. 최대 두 라운드, 주별최대2개·전체최대4개이며 모두부족할 때 순서는 남동2024/고론탈로2024/고론탈로2025/남동2024다. 기존plan이허용하는 years는각후보에해당연도1개만기록한다.

각 공식polygon의대표내부점에서 UTM zone/북·남반구를 결정하고 미터계로 옮긴다. 기존 v2와 같은 `spatial_centers(geometry,4)`를 재생성해 첫4개center를 제외한다. 추가center는10,400m 고정격자의경계내부점에서 대표점거리/좌표순으로 고른다. 원본1024×10m창의외접원+100m를공식polygon안으로제한하는보수조건을 먼저 적용하고, 선택창 전체의 면적이95% 이상안에있는지도별도계산한다. 최종학습patch의95%품질판정과구분한다.

기존lane-B plan도 기존 `validate_candidate_plan(prior_plan,boundary,existing_v2_centers)`를 실제호출해검증한다. prior의모든center/ID를제외하고 source의 **모든연도·품질상태·historical_noneligible_patches**의 source_window를고유경로/SHA로모은다. GTiff 원바이트SHA를확인하고 MemoryFile로 실제 native bounds/CRS/transform을읽는다. 배열/라벨/영상품질은읽거나변경하지않는다.

source_window는미터투영계·북향격자·유한bounds이어야하며 GCP/RPC/subdataset을거부한다. 기존center와 sourcewindow를후보CRS로보수적으로densify변환하고1m 패딩해 양의면적겹침을거부한다. **같은위치의다른연도도새공간으로허용하지않는다.** 새후보끼리도즉시제외목록에넣어겹침을거부한다.

공간ID는 검증된 province/year/native좌표/sourceSHA/boundarySHA/configSHA의해시를포함한 `centers182-<province>-<12hex>`다. 기존ID와의충돌을거부하고 기존asset·원본파일·폴더를재사용하거나이름만바꿔독립공간을주장하지않는다. 아직소비하지않은과거새proposal도Root가prior-plan에포함해야한다. source만바뀌었다고이전미집행proposal의같은공간을다시독립승인하면안된다.

한도는 source header최대256파일·파일당64MiB·로딩payload합2GiB, 각주의투영격자후보최대100,000점, 최종출력2MiB다. SHA후검산과메타데이터읽기까지포함한전체I/O/RSS/시간hard sandbox는아니다. 전후 source/config/boundary/prior SHA와header핀을확인하며출력후에도입력과출력SHA를확인한다. 여러파일의OS원자snapshot/TOCTOU완전방어를보장하지않는다.

## 실행 미연결·잔여 차단

이entry는 source_window와선언된v2/lane-B센터의로컬기하만확인한다. **현재원장의미정산config/rawB02·모든SCL/SWIR/support파일·source목록밖의과거report디렉터리·동시실행claim은아직전체검사하지않는다.**167의현재전체inventory/pending검사가소비전에필수이며관련flag는false다. 이검사를대신했다고주장하지않는다.

중요하게도 기존 `extra_jobs`/`validate_candidate_plan`은 collector_consumption_approved=false를 실행차단으로 강제하지 않고 추가 source/config SHA도 자동검증하지 않는다. 따라서 새파일을단순히 `--candidate-plan`으로넘기고과거 검산을승인으로취급하면안된다. Root가후속소비전에현재 source+ledger핀·전체support/pending·출력배타성·3000물리상한·동일scene/split보호와새planSHA를확인해야한다. 필요한현재pin 연결은별도작은보호단위로구현한다.

동년ESRI는약한라벨이며새지역의나지존재/clear Sentinel 품질을보장하지않는다. expected bare intent·미터기하·95%원본창만으로실제적격패치수·0.5%비율/기여5개·독립정답·모델승인·자동학습을주장하지않는다. 실제수집은기존2worker/2초/최초429공유중단/4GiB동일원장/미정산예약보존/최대2batch를그대로사용해야한다.

## 시험과 인계

최종 `centers182-focused-combined-final-20261018.log`: **12PASS/18.974초·종료0**(신규9와기존candidate3). 임시공식형polygon·실제작은GTiff만사용했다. 결정론/최대4·각주2·정확연도·95%이상·기존validator통과, stale핀/기존출력거부, 이미28개인셀제외, 다른연도실제source header겹침거부, prior ID/공간재사용거부·prior2019거부, 잘못된config/파일cap/격자budget거부, 공식configs 경로의명시pin허용, 입력바이트/PAM보존/실행미승인flag를검증했다.

강화전8PASS10.994초·8PASS16.224초·9PASS11.108초·9PASS18.665초의로그도보존했으며묶음을합산하지않는다. 테스트진행중개발보강의중간상태와최종소스검증을구분한다. 외부rasterio affine연산의기존PendingDeprecationWarning은최종log에남아있으며실패가아니다. 기존candidate3PASS/4.919초도별도 `centers182-existing-contract-20261018.log`로보존했고최종12건에중복포함된다.

최종script SHA는 `c7853c4c99a42509063508ffd0d3173abd6c53174ef591b3a5e979dc839ccf2d`, 시험 SHA는 `ecd3dc3a1aabf714b34b7a12c47b21f7d4d9845b2f2fe61f66ea63fa68cd459a`다. `centers182-contract-20261018.json`은합성검증과운영미실행·잔여지원검사차단을구분한다.

초기코드·합성단계는운영proposal/헤더검산0으로마감했고,Root가9차terminal/정산·원본안정을확인한뒤아래로컬스캔을명시지시했다. 이후소비전167전체지원검사는여전히Root소유이며운영적격증가로표현하지않는다.

## 후속 허가된 실제 로컬 스캔 — 2026-10-18 12:09~12:10 KST

`centers182-actual-runner-20261018.py`가원본1617행을새 `data/centers182-actual-20261018/source.json`에원바이트로복사했다. SHA `03c58af67c5f44e9824488c3e7f0595746b007addb37f846119511b0f19dd367`, 저장적격1296·셀당28 부족합44의cohort다. root가허용한sourceSHA와다르면자동재핀/재시작하지않게했다.

source·ledger·boundary·config·기존lane-B의5개핀을고정했고metadata stat변화를감시했다. 변화하면owned제안process만종료하고부분출력을보존/거부하는장치를썼다. 실제실행에서는drift0·5개SHA/identity전후모두일치였다. 원장SHA는 `7d27c5231c43c0014de92a11fa517c5a4d5c662005785ac75054d37dc27544fb`다. product script는위동결SHA 그대로사용했다.

실제 source_window **107개**의원바이트SHA/nativeGTiff header와기존v2첫4center/lane-B를검산했다. 기존center/source겹침2개를거부하고새1024후보4개를생성했다. **45.922초·종료0**, 12:10:07KST 완료이며새collector나HTTP를시작하지않았다.

| 후보 ID 끝12hex | 주/연도 | 고정split | 중심 lon,lat | snapshot 적격/부족 | native 원본창 주내면적 |
|---|---|---|---|---|---|
| ff61391db6ca | 남동술라웨시2024 | train | 121.8688497631,-3.8135448402 | 10/18 | 1.0 |
| 9cce26141403 | 고론탈로2024 | train | 122.2450704869,0.7526702927 | 25/3 | 1.0 |
| fa0c1ffb8559 | 고론탈로2025 | train | 122.3385467628,0.6585999635 | 18/10 | 1.0 |
| 19cd11b0e656 | 남동술라웨시2024 | train | 121.7753330209,-3.7193498472 | 10/18 | 1.0 |

정확한ID는 `centers182-<province>-<끝12hex>`이며정확bbox/CRS는새proposal에있다. 남동은EPSG32751,고론탈로는EPSG32651이며이실측격자만기록한것이지모든미래source CRS를주별고정한것은아니다.

출력은 `data/centers182-actual-20261018/proposal.json`, SHA **`e9dcd4a9c6ae994c9cb48fb7acbce3b217494279edfc0076b540e3860b88c565`**다. 명시기존validator를통과했지만 collector_consumption_approved/full_pending_support_inventory_verified/execution_supported는false다. 나지존재·영상품질·실제적격수증가·완전한공간독립성은미확인이다.

별도 `centers182-actual-final-verifier-20261018.py`는107header핀·source사본/경계/proposal SHA를다시계산하고4후보의native1024면적/주내비율·실제snapshot셀부족·모든107source bounds와후보간겹침0을독립검산했다. **5.781초·종료0·불일치0**, proposal/source사본 전후불변이다. 이독립검산은v2/prior templatecenter를다시생성하지않았으며원래product검사와구분한다. 전체pending/SCL/rawB02/support inventory도수행하지않았다.

근거는 `centers182-actual-preflight-20261018.json`, `centers182-actual-result-20261018.json`, `centers182-actual-cli-20261018.log`, `centers182-actual-final-verification-20261018.json`이다. Root는현재source/ledger를다시핀하고167전체inventory를검사한뒤후속집행을판단한다. 이담당은proposal을어떤실제수집의 `--candidate-plan`으로도소비하지않았다.
# 202 명시 셀 선택 후속

`scripts/propose_deficit_centers182.py`는 기존 기본 목록과 출력 호환을 유지하면서 선택 `targets` 및 반복 CLI `--target province:year`를 지원한다. 남동2021·고론2022를 다른 연도 후보로 재해석하지 않고 별도 고정 원본에서 명시할 수 있다. 관련12시험을 통과했으며 운영 재제안·실행 승인은 아직 하지 않았다. 새 계약·시험·한계는 [202 문서](202_explicit_deficit_proposal_cells.md)를 따른다. 최대4후보·주당2후보와 full pending/support 미검증·집행 미승인 상태는 유지한다.

