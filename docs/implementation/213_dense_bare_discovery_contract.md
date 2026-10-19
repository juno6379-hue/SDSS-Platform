# 213 — 새 나지 밀집 위치 발견을 기존 계측 수집 경로에 연결하는 계약 검토

상태: **PLANNED / 계약 검토만**. 제품 코드·시험 파일·운영 자료를 수정하지 않았고, 후보 스캔·native·HTTP·새 수집·학습0이다.212에서 확인한 부족량을 실제로 줄이기 위한 다음 내부 구현 제안이며 실행 승인이나 원격 자료 확보 결과가 아니다. 실제 집행은 Root 단일 coordinator만 수행한다.

## 문제와 첫 구현의 목표

212의 저장값 기준 원본 나지는 train2,562/val2,998/test1,025픽셀이다.0.5% 고정분모 부족은256,738/91,126/80,240픽셀, 기여 패치 부족은4/3/5개다. 기존50+37후보의 중복 포함 선언 합도17,808/17,081/28,625에 그친다. 비슷한 숲 창을 더 받거나 나지256개만 있는 패치를 몇 개 더 받는 것으로 해결된다고 가정하지 않는다.

첫 구현은 **근거 있는 새 확대 라벨에서 나지가 더 밀집한 비겹침256창을 발견하고, 출처가 고정된 실제 target plan/request까지 연결하는 것**이다. 별도 통계 JSON만 더 만들고 실행 소비 연결을 미루는 완료 보고는 피한다. 다만 아래 품질/support 연결이 막히면 그 이유를 명시해 BLOCKED로 반환한다. 임의 좌표·임의 라벨 URL·새 정답·추정기관승인을 생성하지 않는다.

## 직접 읽어 확인한 재사용 경로

|현재 코드 |재사용할 동작 |이번 계약에 남은 공백 |
|---|---|---|
| `collect_samples.collect_windows` |shared guard·선택 scene·metadata/XML·계측 fetch·source report |label만 받고 멈추는 명시 mode가 없음 |
| 같은 함수 `label_first` 분기 |실제 선택 scene에서 `esri_annual_plan(year,scene_id)`로 동년 라벨 URL 결정, crop 저장·공식 code 검사·histogram |현재는확대 crop 전체histogram만 보고6밴드로 진행.256 밀집창 생성/receipt 연결 없음 |
| 같은 함수 `fetch` |요청 전 COG상한예약, 실측·불명계측의 보수적보존,32MiB fetch별 상한·총64MiB |discovery도이중앙경로를써야 하며 `urlopen` 별도 다운로드 금지 |
| `service.configure_metadata_budget/read_cog_window` |metadata1MiB·COG HTTP 본문 계측,2초/429, 실제 native header/window guard |제안 단계에서 이 비용을 무료/0B로 가정하지 않음 |
| `references.esri_annual_plan` |실제 선택 Sentinel scene의 MGRS supercell·2020~2025/동년 Esri URL/분류체계 |좌표로 임의 tile을 발명하거나 다른 해 라벨로 대체하지 않음 |
|175 `prepare_targeted_bare_jobs` |고정 label/lineage/proposal refs·실제256 native창·나지계수·fixed split·geometry 검산 |discovery-only lineage를 허용하려면 명시 상태/연도/출처 연결의 시험 필요 |
|170 `run_targeted` 및 live guard |fresh support/physical검산·단일lock·동년scene/분할·실B02·최종80/95/256·계측정산 |사전발견자료가 live 승인서는 아님. 자기 SCL support 충돌도 아래에서 해결해야 함 |

현재1024 job의 `label_first`는 최대2048 native픽셀을 읽으므로 이미 받은 영상의 바깥쪽까지 라벨이 있을 수 있다. 반면256 job은최대512다.209의 새 두 source가 저장한 확대 라벨은193/192의 과거 탐색 시점보다 나중 자료다. 그 파일의 실제 존재/출처/SHA·밀집성은 이번 RFC에서 다시 검사하지 않았다.

## 두 입력 모드 — 먼저 로컬 고정 근거를 소비한다

권장 API는 미래의 `prepare_dense_bare_discovery(root, request)`와 명시 실행 coordinator `run_dense_bare_discovery(root, request, expected_sha256, execute=False)`다. 최대seed1개/실행이며 모든 기본값은 계획 전용이다. v1은 다음 mode를 명시적으로 구분한다.

1. **SAVED_LABEL_ONLY:** Root가 선택한 실제 source report·raw-esri_io.tif·선택STAC·quality evidence의 path+SHA만 받는다. 우선209처럼 새로 생긴 저장 확대 라벨을 bounded local window로 탐색한다. 원장 예약/HTTP0이다. 기존 탐색에 쓴 라벨과 같은 파일/같은 window를 새 ID로 재발견하지 않는다.
2. **METERED_LABEL_PROBE:** 새 원격 label이 필요한 경우만, 이미 출처를 검토한 공간 제안의 고정 seed ID+year를1개 선택한다. 현재 source/ledger/boundary/config/proposal pin을 단일global lock 안에서 검산하고 **한 batch에 COG64MiB+metadata1MiB**를 같은4GiB 원장에서 먼저 예약한다. STAC/품질/Esri crop을 기존 계측 경로로 받는다. label-only의 명시 종료 지점을 새로 구현해야 하며 지금 실행할 수 있는 mode가 아니다.

SAVED 모드를 우선하는 이유는 이미 계상하고 저장한 라벨을 다시 받지 않기 위해서다. 새 seed도 Root가 명시한 기존 proposal/허용 영역에서만 고른다. 호출자가 입력한 임의 lon/lat·임의 URL·전체 국가 원격 스캔은 허용하지 않는다. 필요 seed가 없으면 `NO_PINNED_DISCOVERY_SEED`로 끝내고 좌표를 만들어 채우지 않는다.

## 명시 요청 필드 v1 제안

|필드 |계약 |
|---|---|
|schema_version/kind/mode |int1/`DENSE_BARE_DISCOVERY_REQUEST`/위 두 mode 중 하나 |
|current_manifest_ref/ledger_ref/boundary_ref/config_ref |실제 path+SHA. DATA고정사본은 active SHA와 같아야 함 |
|seed_ref |proposal/source report의 path+SHA와 선택 index/ID. source province/year/fixed split은 근거와 대조 |
|source_label_ref/source_lineage_ref/selected_scene_ref |SAVED에서 필수 path+SHA. METERED에서는 결과에 고정될 필드이며 입력에 가짜 refs를 채우지 않음 |
|quality_evidence_ref |있으면 path+SHA·선택scene·SCL grid/footprint·관측fraction·해당 target 범위 포함 여부. 없음은미검증으로명시 |
|policy |window_size256, stride128, max_windows512, max_returned_targets2, 공식source code8, min_declared_bare_pixels와 min_declared_bare_fraction의 명시 유리수 |
|execution_limits |METERED만 maximum_batches1/COG64MiB/metadata1MiB, 기존2초·첫429·retry0·동일4GiB. caller가 늘릴 수 없음 |

밀집 선별 값은 Root가 명시하는 개발 sampling 조건이다. 예시 `min_declared_bare_pixels=1024`, fraction=`1/50`(2%)는 가설값이며 구현/운영 기본값으로 확정한 것이 아니다. 단순256기여 기준보다 높은 밀집도를 찾는 목적이고, 최종 과학적 품질 기준을 새로 정의한 것이 아니다. 비교는 `bare_pixels*denominator >= reference_valid_pixels*numerator`의 정수식으로 한다. reference_valid는 Esri ignore0/10을 제외한 약한라벨 픽셀로, SCL/영상 유효픽셀과 이름을 구분한다.

strict JSON·bounded 크기/노드·bool-as-int·중복키·비유한수·알 수 없는 키·경로/alias·같은 파일 pin 충돌은 거부한다. 모든 source/label/quality/lineage refs는 실제 workspace DATA 파일이어야 하고, signed URL/query·임의 Python callback·새 credential·기관 권한은 받지 않는다.

## METERED label-only의 순서와 비용

1. 단일 execution lock을 선점하고 fresh source/ledger/물리/전체support·seed년도/split을 검산한다. 기존 pending2/136,314,880B는 그대로 둔다. 새source leaf만exclusive로 소유하고 별도 `discovery-<requestsha>` key에65MiB를 예약한다.
2. 기존 STAC query의 cloud/계절/상한을 사용한다. 선택 scene의 실제년도/MGRS·고정split·shared scene claim을 검산한다. scene 없음이면 metadata 실측만 정산하고 label을 다른 tile/연도에서 추정하지 않는다.203이 이 경우였다는 이력을 보존한다.
3. 기존 SCL 후보 선별과 spatial guard를 사용한다. Root 명시 threshold를 받되198의 선택 `.8~1`/기본호환 계약을 유지한다. SCL 저장은예비 품질이지 최종6밴드/SCL/경계 합격이 아니다.
4. `esri_annual_plan(year, selected_scene_id)`로 정한 URL만 `fetch`로 읽고 `preserve_source_crop` 방식의 실제 raster/SHA/header를 저장한다. 확대 side는기존 `min(2048, side*2)`와 native cropping 계약을 유지한다. COG읽기를별도 off-ledger downloader로 우회하지 않는다.
5. 공식 class 검사·histogram·선택context/기존 dominant deferral 관측을 남긴다. 새 `reference_discovery_only` 상태로6밴드 전에종료하는 명시 opt-in을 구현한다. 기본collector의 기존6밴드 진행/deferral은 변경하지 않는다. source report에는 year/label_year/source URL/selectedscene/raw crop path+SHA를 실제근거로 기록하고 영상합격/label alignment처럼 꾸미지 않는다.
6. worker finally/terminal은 metadata/COG 실측·상한·불명계측·source/label/SCL refs·source pins를 저장한다. 중앙정산만 새discovery batch를settle한다. finally 실패/계측불명은전액pending/자동재시도0이다. 이 단계는 학습 patch0이며 학습 aggregate rows를늘리지 않는다.

한번의discovery 상한은65MiB다. 이후256영상 실제 취득은 **별도의170 batch 예약**이다. 두 단계가 생기면 최악의명시예약은130MiB이며 그모두동일4GiB 잔여 안에서검산해야 한다. 원샷65MiB가 두단계의무제한전송을허용한다고부르지않는다. discovery 미사용액의 정상 실측정산과 기존미정산2개의환불은완전히별개다. 이번RFC는 현재잔액을새로조회하거나예산을늘리지않았다.

## 고정 라벨에서 실제 target 입력으로 이어지는 부분

실제 raw label header/affine/CRS의256창을stride128로최대512개만평가한다. 각창의 Esri class8 밀집도·주내95%·공식ignore비율을 계산하고원본source/label SHA·native window/corners·WGS bbox·declared count를동결한다. 같은 좌표의 다른년도/상호부분겹침·이미집행한source/pending/B02/support와겹침은별도로검산한다. source시점이바뀌면새 current pin으로다시검토하고과거proposal SHA만덮어쓰지않는다.

출력은 actual refs와선택scene·fixed split·저장된품질근거의범위를담은 `DENSE_BARE_DISCOVERY_RECEIPT` 및기존175의exact target/proposal 필드를갖춘새계획이다. target plan을만들수없으면이유를fixedcode로반환한다. 단순히분포숫자만내고끝내는것을consumer연결완료로보지않는다.

새 target의실제 품질근거가없거나그영역이저장된SCL범위밖이면 `TARGET_QUALITY_EVIDENCE_REQUIRED`다. 중심1024 SCL이좋아도바깥2048라벨에서찾은256창의구름상태를검증했다고표현하지않는다. 이후170단계에서동년선택scene/SCL을실제로검사하고그저장refs를고정한뒤에만영상소비를계속한다. stored quality evidence만으로최종80/95/나지256의검사를대체하지않는다.

## 반드시 먼저 해결할 self-support 겹침 공백

현재 `inspect_targeted_inventory`는`raw-esri_io.tif` 등정해진참조라벨만이전영상범위검사에서제외한다. `qa-candidate-XX-SCL.tif`는일반support로포함된다. 따라서discovery에서어떤256창의SCL을저장한뒤별도170을fresh호출하면 **자신의미리보기SCL과겹쳐기존support검사에서차단될수있다.** 201처럼B02본체가닿기만해도보조support는실제로겹칠수있다.

이상태에서SCL을이름만바꾸어숨기거나모든SCL을inventory에서빼면안된다. 다음둘중한계약을명시적으로구현·독립검토하기전에는handoff를BLOCKED로둔다.

- **작은1차범위:** 이미저장된확대label에서기존영상/SCL/support바깥의새256창만계획한다.170의기존fresh inventory를그대로통과시키고, target 고유 SCL은그170실행의동일owner 안에서받는다. discovery source/SCL이겹치지않는경우만기존consumer를최소변경으로재사용한다.
- **후속좁은preview재사용계약:** 정확한discovery request/settled ledger key/scene/SCL path+SHA/header/공식SCL역할을검증한자기preview만같은source년도의후속target에재사용한다. 과거B02/SWIR·다른SCL·다른owner·pending/미정산·임의파일에는예외를주지않는다. source/inventory/guard에provenance-aware role이필요하므로별도명시옵션/시험없이는추가하지않는다.170의단일lock안에서중첩dispatcher를호출해재잠금을우회하는방식도금지한다.

이공백때문에지금은METERED discovery결과를기존170에즉시전달할수있다고말할수없다. 처음에는209등기존고정label을소비해실제로비겹침target request까지준비하는작은범위가가장구체적이다. 가능한새창이0이면새seed를Root가명시하거나위preview재사용계약을구현해야하며좌표·정답·승인을발명하지않는다.

## 최소 구현 소유와 수락 시험 제안

첫단위후보는 신규 `backend/app/data/dense_bare_discovery.py`(bounded local scan→고정target/proposal 변환), `scripts/collect_dense_bare_discovery.py`(명시요청·lock/원장/terminal), `tests/test_dense_bare_discovery.py` 및새구현문서다. METERED를포함할때만 `collect_samples.py`의label-first 지점에기본off의명시 종료mode/receipt hook을추가한다.199/200의1024 deficit계약이나170의256 guard를묵시적으로넓히지않는다. 코드편집권한은향후Root가collector소유·실행핀을확인한뒤따로배정해야한다.

수락조건은다음과같다.

1. Temp 실제GeoTIFF/label/source/SCL/lineage로bounded density검색→실제175 exact plan→170 fresh검증/모의실행까지연결한다. 임의JSON count만맞추는시험으로끝내지않는다. 기본모드의출력/key·고정split·최종80/95/256은그대로다.
2. current/label/source/scene/quality pin·동년·CRS/affine/native crop·ignored class·bool/비유한/경로alias·선택범위/stale input을검사한다. 밀집나지와reference-valid분모를최종image-valid분모로혼동하지않는다.
3. 동일좌표다른연도·상호부분겹침·기존성공/비적격/미등재/부분source·pending·preview self-overlap을거부한다. 미래좁은preview예외를구현한다면정확owner/settled/scene/role/SHA외변형을모두거부한다.
4. METERED실행은Temp실원장/기존fetch·명시Mock HTTP로선택scene/SCL→동년Esri2048crop→early-stop→terminal/실측정산을검사한다.6밴드/materializer 호출0·원본pending불변·2초/첫429/재시도0·65MiB/4GiB상한을확인한다. 계측불명/terminal/정산/게시실패는완료·환불로발명하지않는다.
5. 실제현재자료로local검증과Root원격probe/target취득은서로다른승인·증거다. 새 fullscan/native를중복실행하지않고단일담당에배정한다. 최종나지gate 개선량은새 target native/QA후에만계산한다.

실행조건이갖춰지면Root는새고정요청과잔여예산을검토해한seed만시작한다. 신규밀집선언을발견해도독립정답·전체학습준비·모델승인·운영배포를확정하지않는다. 완료코드와증거는이해담당에게인계해쉬운설명·대본·FAQ·INDEX·이력을함께갱신한다.이번은RFC만이므로UI/API/브라우저변경도0이다.

## 215 실제 로컬 탐색 후속 — 2026-10-18 14:34 KST

[215 실제 결과](215_selected_new_labels_actual.md): Root가 209 신규 남동술라웨시 2021/2024 확대 라벨 두 개만 선택해 한 번 탐색했다. 4.860초·295,070바이트·450창에서 최대 나지 선언 10픽셀, 256 기준 충족/순위 후보 모두 0개다. 다른 다섯 주는 탐색하지 않았으며 원격·영상 취득·학습은 0이다. proposal SHA `206fef366b42fe196749d06eea2c52c41755af8bc03ec2cc92b882ab501c0ff8`, 원본/원장 전후불변은 Root 실행기 기록으로 확인한다.

이로써 이번 두 저장 라벨을 통한 저비용 우선 경로는 후속 표적 없이 종료했다. 기준 완화로 우회하지 않는다. 다음 216은 별도 SURVEY_LABEL_ONLY 출처·registry/trace와 기존 173/175 소비자 사이의 명시 계약 설계만 검토한다. 원격 라벨을 RGB 완료행처럼 등록해 선택 참조 존재 검사를 우회하지 않으며, 실제 S2 품질·source/support 겹침·동일 split/scene/원장 검사 전에는 표적 취득 준비 완료라고 하지 않는다. 이는 본 RFC의 계측 원장·명시 seed·후속 품질 필요 원칙과 일치한다.
