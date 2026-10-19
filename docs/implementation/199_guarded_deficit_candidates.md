# 199 — 추가1024 후보의 읽기 전용 사전검증과 전용 live guard

상태: **TESTED_SYNTHETIC / IMPLEMENTED_UNVERIFIED(운영 연결) / EXECUTION_BLOCKED**. 신규 내부 helper와1024 전용 상속 guard를 구현하고 임시시험을 통과했다. 운영 fullsupport/native 검사·HTTP·수집·학습·원장/lock 수정은0이다. 실제 coordinator 연결은 Root의 별도200 단위이며 이번 구현의 성공을 집행 승인으로 사용하지 않는다.

## 쉽게 설명

182/202는 새 촬영 장소를 제안한다.199는 그 제안이 현재 재고·원장과 맞는지, 과거 영상·미정산 예약과 겹치지 않는지, 실물 패치를 더 받아도3,000개를 넘지 않는지 확인하는 부품이다. 또한 나중에 실제 선택한 위성영상이 계획한1024×1024 위치에 맞는지 픽셀을 읽기 전에 확인하는 별도 guard를 제공한다.

이 부품은 수집 시작 버튼이 아니다. 모든 반환의 `status`는 **EXECUTION_BLOCKED**, `execution_supported=false`다. 사전검증이 통과하면 `local_checks_passed=true`와 고정 job/target/proof만 반환한다. 원격 품질·나지의 실제 존재·독립 정답·과학적 공간 독립성·학습 준비는 승인하지 않는다.

## 파일 소유와 기존 기능 보존

이번 소유는 다음 신규3파일뿐이다.

- `backend/app/data/deficit_candidate_guard.py`
- `tests/test_deficit_candidate_guard.py`
- 이 문서

기존 `TargetedLiveGuard`의256 규격·collector·원장·approval flags·185/195/UI·182/202 producer를 수정하지 않았다. Root의203 등 단일 운영 수집과 겹치는 운영 스캔도 하지 않았다. 제품 API/화면을 새로 연결하지 않는 내부 부품이므로 이번 직접 프론트 수정·build·브라우저 확인은 필요하지 않다.

## 읽기 전용 Python API

```python
prepare_deficit_candidate_jobs(project_root, request) -> dict
```

request는 다음 **정확한10개 키**를 가진다. refs는 각각 workspace 상대path와 caller의 소문자64hex SHA다. 아래는 계약 예시이며 현재 운영 요청이나 실행 명령이 아니다.

```json
{
  "schema_version": 1,
  "kind": "GUARDED_DEFICIT_1024_REQUEST",
  "proposal_ref": {"path": "data/새후보/proposal.json", "sha256": "고정 SHA"},
  "current_manifest_ref": {"path": "data/고정사본/source.json", "sha256": "현재 source SHA"},
  "ledger_ref": {"path": "data/고정사본/ledger.json", "sha256": "현재 ledger SHA"},
  "boundary_ref": {"path": "data/first-group-boundaries/selected-six.geojson", "sha256": "경계 SHA"},
  "config_ref": {"path": "configs/first-group.collection.json", "sha256": "config SHA"},
  "prior_plan_ref": {"path": "data/기존후보/prior.json", "sha256": "prior SHA"},
  "selected": [{"spatial_window_id": "명시 후보ID", "year": 2024}],
  "maximum_batches": 1
}
```

proposal/source/ledger/경계/prior는 DATA에 한정하고 config는 DATA 또는 configs를 명시할 수 있다. source128MiB·ledger8MiB·나머지입력2MiB의 기존 snapshot reader를 재사용한다. 여섯 입력의 논리경로 중복을 거부하며 file/path/SHA·strict JSON·입력사본 타입을 검산한다. 하위 기존 validator가 JSON을 재개방하는 부분까지 새 누적IO/RAM/시간 hardcap을 제공하는 것은 아니다.

## 사전검증 순서와 실제 범위

1. exact schema/type·선택ID/연도·최대1~2batch·중복선택을 확인한다. bool을정수로수용하지않는다.
2. 여섯ref를읽고 실제 활성 `first-group-training-esri-v1/annual-window-report.json`과 `first-group-training-budget/global-ledger.json`의SHA도caller핀과대조한다. 오래된사본만맞는경우 `CENTER_ACTIVE_INPUT_CHANGED`로닫는다.
3. proposal의source/config/prior/boundarySHA와현재명시ref가같아야한다. stale182를현재SHA로고쳐승인하지않으며 `CENTER_SOURCE_SNAPSHOT_STALE` 등으로차단한다. producer의세미승인flag는계속false여야한다.
4. 원본+history최대3,000행,고정6주경계/config AOI,선택후보의정확연도·고정split·native1024·동년ESRI·미검증class/quality/실행flag를확인한다. 현재적격28이상인셀과이미적격인공간prefix·기예약/기정산key를거부한다. source계수는현재scenes에한정하고과거history로적격을부풀리지않는다.
5. 기존candidate validator로prior의기하와새proposal을대조하여아직집행하지않은prior장소도새이름으로재사용하지않게한다. 새center의미터CRS·10,240m 정사각형·명시WGS84 bbox·공식주내95%이상면적을직접검산한다. 최초g00~g03 전체재생성이나182의source-header별도감사를반복하는기능은아니다. 실제과거지원은다음fullinventory가담당한다.
6. 기존167 `inspect_targeted_inventory`를한번호출한다. inventory/pending/source핀true를요구하고,그전체assets를공유 `TargetedWindowClaims`에넣어선택후보들의과거지원·선택상호겹침을검사한다. source영상뿐아니라SCL/SWIR/B02/미정산지원의더큰범위가원본1024 기하와달라차단될수있다. 제안생성통과를fullsupport통과로확대하지않는다.
7. 기존 `physical_patch_inventory`를재사용해history/미등재/부분실물패치까지읽기전용계수하고 `physical_count+16*선택batch수≤3000`을확인한다. 같은관측을끝에서한번더대조한다. aggregate행수만물리상한으로쓰지않는다.
8. 정확4GiB·비활성429회로·원장의pending/settled 계상타입/합계·batch당65MiB(64MiB COG+1MiB metadata) 잔여량을확인한다. 실제예약·정산·refund·원장lock은호출하지않는다. 끝에서입력refs/활성source·ledger와물리관측을재확인하고서로다른job key를반환한다.

실제 운영자료에 이 함수를 호출하면 위 로컬fullsupport/물리순회가 수행된다. **199 담당은 그 운영 호출을 하지 않았다.** 시험의 fullsupport는Mock이고 물리함수 재사용 확인도 빈 임시폴더에 한정했다. 성공은 `issue=COORDINATOR_NOT_CONNECTED`와 `local_checks_passed=true`일 뿐이다. 실패는 jobs/targets를비운상태로고정이유를반환하며경로나원예외를일반메시지로노출하지않는다.

job에는 `nominal_patches=16`, native1024 config·6밴드·source SCL 후보하한65%·최종유효80%·cloud60·재시도0·제품metadata검증/원crop보존·동년ESRI를고정한다. 이름은requestSHA와후보ID SHA로결정되며기존legacy extra-key도검사한다. job의고정split을caller가재배정할수없다. proposal의나지존재flag를true로바꾸거나나지기여량을발명하지않는다.

## 1024 전용 상속 guard

```python
DeficitCandidateLiveGuard(job, target, shared_scenes, shared_windows)
```

`on_scene`는기존부모를그대로상속한다. `_binding`은부모의주·split·동년·단일AOI·bbox·미터CRS 조건을먼저검사하고,새job의1024/16명목패치·안전한owner key·target1024·native10,240m정사각형·WGS84bbox 일치를추가검사한다.

`on_window`는**선택scene의정확B02 URL일때만**새1024 분기를쓴다. 실제requested_side와window가1024×1024이고10m격자·같은미터CRS·회전없음·실window/계획bounds 차이≤10.000001m여야한다. 공유window claim을통과한뒤에만 `b02_checked=true`다. 256·잘린창·20m·다른CRS·1픽셀초과정렬은차단한다.

후보선정SCL·동년확대라벨·다른선택asset은 `super().on_window`로기존보호를재사용한다. 선택전영상금지·선택asset URL결합·reference재사용·과거지원/동시작업claim·scene seed격리/교차split거부를유지한다. 기존256부모가1024를거부하는회귀도통과했다.

service hook은COG header와범위를확인한뒤실제 `src.read` 앞에서호출된다. 따라서픽셀전차단은확인했지만앞선SAS/HEAD/header range까지network0이라는뜻은아니다. `b02_checked`도실격자callback 통과관측이지픽셀다운로드성공·파일SHA·영상품질·과학승인이아니다. 그뒤읽기/저장/품질이실패해도claim을자동해제하지않는기존계약을유지한다.

## import와 CLI 부작용 확인

199모듈을import하는것만으로collector CLI를import하지않는다. 물리관측이실제로필요할때만함수내지연import로 `scripts.collect_targeted_bare.physical_patch_inventory`를재사용한다. 해당모듈의기존모듈초기화와sys.path 설정은수행되지만 `main`,argparse실행,CollectionLedger생성,예약,HTTP는호출하지않는다. 순환import는발생하지않았고관련부모guard/producer시험과함께검증했다.

신선한Python subprocess에서199import후 `scripts.collect_targeted_bare`가로드되지않음을확인했다. 물리helper는빈Temp sources/patches에서원장생성trap과파일목록불변을확인했다. 이시험을운영전체physical inventory 검증으로표현하지않는다.

## 시험 근거

초기집중18건 **18PASS/10.536초** 후6주와2batch 경계를보강했다. 최종신규20건을포함한관련회귀는 **55PASS/16.396초·종료0**다. 신규20+부모256guard20+기존candidate3+202producer12이며초기18을중복합산하지않는다.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_deficit_candidate_guard test_targeted_live_guards test_data_candidates test_propose_deficit_centers182 -v
```

실제임시JSON/기하·작은기존producer GTiff와모의support/COG를사용했다. 신규시험은다음을확인한다.

- exacttype/추가키/최대2/중복·stale source/config/prior/경계·활성원본대조·미승인flag보존·기존prior장소/해소셀/기예약차단.
- fullsupport3flag·정확1회호출·과거겹침·physical2984+16허용/2985+16거부·2968+32허용/2969+32거부·4GiB/429/원장합계·입력변경후반환jobs0.
- 6주고정train/val/test의새preflight와1024 B02성공,256부모불변·256/잘린창/CRS/해상도/URL/AOI/owner변조차단·1픽셀경계.
- 부모SCL/라벨재사용·scene교차split보호·실service의모의COG callback에서잘못된B02격자를실픽셀read호출0으로차단·import지연·Temp파일불변.

기존rasterio affine의 `PendingDeprecationWarning`은최종도구출력에남았고실패로숨기지않았다. 전용운영증거/CLI를새로만들지않았으며담당실행도구출력과Root통합로그를시험근거로사용한다. 최신전체backend/frontend 전체회귀나실브라우저를이번에실행했다고주장하지않는다.

최종 helper SHA는 `c8eece7cbb0d3fed77f704b65eda9e51fe2e300ea56fdfd4aa020d9c9653204f`, 시험SHA는 `86574bf6033b6dc837880076ea8f14d043fa3951182dd640419fed5232ec78a4`다.

## 200 coordinator가 반드시 연결할 계약

199는 `selection_context`를생성하지않는다.200은현재분할클래스/지역연도상태에따른명시context를준비하고,검증한source와같은seed의 **shared scene_registry** 및 **shared TargetedWindowClaims(fullassets)** 한쌍을모든worker에함께연결해야한다. 개별worker마다별도registry를만들면동시선택scene/지원창검사가분리되므로허용하면안된다.

단일execution lock의명시취득·현재입력과물리관측의lock안재확인·기존pending2전액보존·CollectionLedger예약/실정산·2worker/공통2초/첫429중단·새출력배타성·3000실물상한·선택B02 callback 연결·실파일/실품질/등록·실행미확정실패인계는 **200 실제실행계약**이다.199의성공반환이그계약을완료했다는뜻은아니다. 기존pending을해제/환불하거나proposal승인flag를true로바꾸는기능을추가하지않았다.

Root는202의fresh proposal과현재source/config/prior 지문을고정하고별도로승인한운영preflight·coordinator연결·시험·실자료감사·UI반영을같은후속단위로마감해야한다. 이전182 stale자료는199에서차단되며그기존파일을현재cohort처럼고쳐쓰지않는다. 완료코드와시험은Root/understanding담당에게전달해이해자료·대본·FAQ·INDEX/변경이력을갱신한다. 전체개발·10분보고·나지/독립정답/학습승인은계속후속이다.

## Root의 별도 실제205 검토 후속

위199담당의운영검사0은구현/임시시험단계의사실로보존한다. 이후Root가[205 실제검토](205_fresh_southeast_guard_review.md)에서동결helper를단1회운영로컬호출했다.129.516초·inventory1회/1,254assets·두job의로컬조건통과·physical1,668+32≤3,000·입력불변을확인했지만 `EXECUTION_BLOCKED/COORDINATOR_NOT_CONNECTED`와수집/HTTP/예약/정산0을유지한다. 실제B02/품질과200집행연결은별도미완료다. helper/시험동결SHA는변경하지않았다.
