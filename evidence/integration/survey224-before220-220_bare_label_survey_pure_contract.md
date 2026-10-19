# 220 — 라벨 전용 SURVEY 순수 계약 모듈

상태: **IMPLEMENTED / TESTED_SYNTHETIC**, 실행 연결은 **PLANNED**다. 새 `backend/app/data/bare_label_survey_contract.py`는 전달받은 JSON 선언만 검증한다. HTTP·runner·원장·파일SHA·header·실품질·registry·173/175 소비자 연결은 구현하지 않았다. 기존collector/제품파일은 수정하지 않았고 운영 원본/원장 읽기0이다. [216 설계](216_label_only_survey_contract.md)의 첫 내부 단위이며 219의 실제 실행과 분리돼 있다.

## 쉬운 의미와 경계

앞으로 라벨만 모으는 작업을 RGB 영상이 완성된 행처럼 꾸미지 않도록 별도 요청과 영수증의 형식을 고정했다. 이 모듈이 통과시킨 것은 **문서에 적힌 값들의 일관성**이다. 파일이 실제로 존재하고 그 SHA/CRS가 맞는지, 원장에 실제 정산됐는지, 구름이나 나지 품질이 좋은지는 확인하지 않는다. 임의값을 써도 문법상 맞을 수 있으므로 외부 증거 검증을 대신하지 못한다.

모든 결과는 실행/출처 승인false다. 후속 소비자는 이 typed 객체만으로 다운로드·환불·학습을 시작하면 안 된다. 실제자료 검증·같은global lock/원장/scene·SCL지원영역/분할·신규target품질이 연결되기 전까지 현재173/175에 전달할 수 없다. SCL blanket제외/legacy예외 완화는 없다.

## 공개 Python API

```python
from app.data.bare_label_survey_contract import (
    validate_survey_request, validate_survey_receipt, SurveyContractError,
)
checked_request = validate_survey_request(request_dict)
checked_receipt = validate_survey_receipt(receipt_dict, request_dict)
declared = checked_receipt.to_dict()  # 매번 새 사본
assert checked_receipt.execution_supported is False
assert checked_receipt.provenance_verified is False
```

성공은 frozen dataclass `ValidatedSurveyContract`다. 필드는 `kind:str`, canonical 요청 digest인 `request_sha256:str`, 불변 문자열 `canonical_json:str`, `status='DECLARED_CONTRACT_VALID_EXECUTION_PLANNED'`, `execution_supported=False`, `provenance_verified=False`다. `to_dict()` 사본을 변경해도 검증 결과나 원입력은 바뀌지 않는다. 이 클래스의 직접 생성은 검증을 대신하지 않으며, receipt API는 항상 원request dict를 다시 검증한다.

실패는 `SurveyContractError(ValueError)`와 고정 `SURVEY_*` 코드만 반환한다. 경로·입력값·민감정보·원예외문을 오류에 붙이지 않는다. 파일 경로를 찾거나 resolve/stat하지 않는다. web API/CLI/브라우저 화면은 추가하지 않았다.

## request v1의 정확한 필드

최상위는 다음 키만 허용한다. 빠진 키/추가 `execute`·학습승인 키도 거부한다.

- `schema_version:1`, `kind:BARE_LABEL_SURVEY_REQUEST`, `survey_id`(소문자영숫자/하이픈1..48), `config_sha256`(고정설정의 소문자64자리SHA).
- `current_manifest_ref`, `boundary_ref`, `ledger_ref`, `base_config_ref`: 모두 정확한 `{path,sha256}`. source/boundary/ledger는`data/`, baseconfig는`data/` 또는`configs/`. 네 경로는 대소문자 무시시에도 중복 불가다. 실제파일 SHA를 검사한 것은 아니다.
- `seed:{seed_id,province,fixed_split,year,bbox_wgs84,period_start,period_end,justification_ref}`. 주는기존6주, split은4개train/Bantenval/WestJavatest 고정. 연도는int2020..2025이며 bool금지다. bbox는유한한[minlon,minlat,maxlon,maxlat]·정상순서다. 시간은UTC `YYYY-MM-DDTHH:MM:SSZ`·동년·시작<끝이다. justification은고정ref다. bbox의실제주내95%는공간검증미구현이다.
- `selected_scene:{id,datetime,source_group,stac_ref}`. source_group은`province/id`, acquisition ID의연도와선언datetime의연도를검사하고 datetime은기간내여야한다. 기존순수 `references.esri_annual_plan()`로 실제Sentinel-2형태ID의MGRS supercell 규칙을 검증한다. scene이실재한다는검증은아니다.
- `policy`: 정확히 maximum_batches1·maximum_cog_bytes67108864·maximum_metadata_bytes1048576·maximum_label_side2048·request_spacing_seconds2·transient_asset_retries0·stop_on_first_429true. 숫자의bool/float 대체도거부한다.
- `budget_snapshot:{additional_maximum_bytes,new_charged_bytes,preserved_pending_bytes,rate_limit_active}`. 추가최대4GiB고정, 이미청구/예약한양은0..(4GiB−65MiB), 보존pending은0..이미청구양, 회로false다. 실제잔액·pending2의136314880바이트보존여부는원장검증미구현이며 선언값만검사한다. 새예산을추가하거나과거pending환불을승인하지않는다.
- `output_relative_path`는정확히`data/bare-label-surveys/<survey_id>`, `patches_materialized`는int0, 아래11개권한필드는모두false다.

권한필드: `execution_supported`, `collection_executed`, `quality_eligible`, `training_ready`, `independent_ground_truth`, `rgb_collected`, `source_authenticity_verified`, `raster_header_verified`, `ledger_verified`, `registry_connected`, `target_consumer_connected`.

216보다 좁은 이번subset은 **선택scene이이미명시된 계획만** 받는다. 선택전seed를주고STAC검색하는runner는없다. `config_sha256`도요청에명시해receipt의설정digest가다른값으로바뀌지않게했다. 이 필드는base config파일SHA와파생설정digest가다를수있음을구분하며실설정파일과의일치는외부검증범위다.

## receipt v1의 정확한 필드

최상위는 `schema_version:1`, `kind:BARE_LABEL_SURVEY_RECEIPT`, `collection_purpose:SURVEY_LABEL_ONLY`, `survey_id`, `request_sha256`, `batch_key`, `config_sha256`, `selected_scene`, `label`, `candidate_scl_refs`, `accounting`, `patches_materialized`와위11개false필드다. request digest/설정/선택scene을exact결속하며batch key는`bare-survey-<survey_id>-<requestdigest앞12>`다. 기존training manifest의`scenes`·RGB완료상태·eligible field는허용하지않는다.

`label:{ref,label_source,label_year,source_url,license,dataset_version,grid}`에서 source는`esri_io`, 연도는request와동일한int, license는CC-BY-4.0이다. URL/version은기존`esri_annual_plan(year,selected_scene.id)`의**Esri v003 동년supercell 계획과정확히동일**해야한다. signed query·다른host/tile/year/version은거부한다. 라벨경로는새survey폴더의`raw-esri_io.tif`다. URL계획이존재/다운로드성공했다는증거는아니다.

`candidate_scl_refs`는이번v1에서선택scene에결속한**정확히1개**만받는다. 각항목은`{ref,scene_id,role,grid}`, role은`SCL_CANDIDATE_SUPPORT`, scene_id는선택scene ID와동일하다. 경로는같은survey폴더의`qa-candidate-XX-SCL.tif`다. 다섯candidate를나중에읽더라도다른scene의출처까지확인하려면별도pinnedscene계약확장이필요하다. 이모듈이기타후보를검증했다고표현하지않는다.

양쪽grid는`{crs,transform,width,height}`다. CRS는canonical EPSG32601..32660/32701..32760, transform은유한6원소·회전0·north-up다. 라벨은10m/크기1..2048, SCL은10또는20m/크기1..1024이며CRS가같아야한다. 이는선언된shape/grid검사다. 실제밴드수/dtype/header/픽셀값/footprint/주경계/선택B02와alignment는읽지않았고, rawgrid를실측했다고하지않는다. SCL의존재선언만으로최종유효80%가검증되지않는다.

경로ref는소문자SHA64자리와canonical로컬상대path만허용한다. 부모이동·빈segment·역슬래시·ADS/드라이브/UNC·제어문자·Windows예약device·trailingdot/space를거부한다. symlink/reparse/inode/실제alias는검사하지않는다. 실제consumer에연결할때기존confined/descriptor/SHA검산을별도로통과해야한다.

## accounting 선언의 두 상태

accounting의키는`{state,measurement_known,reserved_bytes,charged_bytes,metadata_body_bytes,cog_body_bytes}`로고정한다. reserved는int65MiB고정이다.

| 상태 | 허용하는선언 |
|---|---|
| `DECLARED_MEASURED_SETTLED` | measurement_knowntrue, metadata0..1MiB/COG0..64MiB의int실측선언, charged=두값정확합 |
| `UNSETTLED_FULL_RESERVATION` | measurement_knownfalse, charged=65MiB전액, 실측두필드null |

미정산을0바이트로쓰거나계측불명에부분환불을쓰면거부한다. 실제원장settled를확인한상태로명명하지않기위해`DECLARED_`를명시했다. 이receipt는현재실행이없으므로`collection_executed=false`다. 미래실제runner의실행증거receipt는별도버전/실제외부검증을설계해야하며현재schema에true를넣는우회는허용하지않는다. 정산후registry게시실패/강제종료journal/원장reserve/finally는이번순수모듈에없다.

## 오류·구조budget·시험

형식실패코드는REQUEST/RECEIPT/REFERENCE/PATH/ID/CONFIG/SEED/BBOX/TIME/YEAR/SCENE/POLICY/BUDGET/GRID/LABEL/SCL/ACCOUNTING/APPROVAL 등구체`SURVEY_*`분류다. 모든JSON입력은먼저최대10000노드·깊이24·container128·문자열4096·정규UTF8canonical64KiB로제한한다. cyclic/NaN/무한/거대정수·임의객체도fixedcode로거부한다. dict입력이므로원JSON문자열의중복키검사는하지않는다. 원바이트parser를만드는후속consumer는중복키/UTF8/BOM/NUL/파일cap을별도검사해야한다.

시험은합성JSON만으로request/receipt결속·불변복사·allfalse·strictkeys/types·경로/alias/SHA·6주split·연도/시간·Esri공식v003 MGRS·grid·선택SCL·65MiB/4GiB선언상한·실측합계·미정산전액보존을확인한다. `open/Path.open/socket.socket`를금지한상태에서도성공하므로모듈검증중I/O없음을확인했다. 실Temp raster/원장자료를만들필요없는순수단위이며운영source/ledger읽기0이다.

초기집중18PASS/0.175초로그는[focused](../../evidence/integration/survey220-focused-20261018.log), 중간관련60PASS/20.581초는[related](../../evidence/integration/survey220-related-20261018.log)다. config/선택SCL/scene경계를추가한最終판은 **60PASS/15.841초·skip0**이며 [final 로그](../../evidence/integration/survey220-final-20261018.log)와 [freeze](../../evidence/integration/survey220-freeze-20261018.json)에최종소스/시험/문서핀을기록한다. 기존173/175/198관련시험은기존consumer가동작한다는회귀이며SURVEY연결완료의증거가아니다.

완료코드·시험·후속경계는Root이해담당에인계한다. 다음구현은216의실제coordinator/원장/trace와truthfulsurveyregistry, 명시173/175소비branch및실제S2품질·supportguard까지별도로배정/검토해야한다. 이번단위에그실행승인은없다.
