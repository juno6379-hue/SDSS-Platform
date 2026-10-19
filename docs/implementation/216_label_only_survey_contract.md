# 216 — 원격 라벨 전용 SURVEY 출처와 표적 소비 연결 제안

상태: **PLANNED**. 설계 문서만 작성했다. 제품 구현·원격 요청·새 라벨/영상·native/운영 스캔·원장 쓰기·학습은 모두 0이다. 현재 바로 다운로드할 수 있는 완성 기능이 아니다. [213 RFC](213_dense_bare_discovery_contract.md)를 구체화하며, [215 실제 탐색](215_selected_new_labels_actual.md)의 두 신규 라벨 후보 0 결과를 전제로 한다.

## 해결할 실제 공백

`collect_samples.collect_windows()`의 `label_first`는 선택 scene과 필요시 후보 SCL을 읽은 뒤 동년 Esri 확대 라벨을 보존한다. 공식 class 검사·예비 분포·dominant deferral 뒤에는 기본적으로 여섯 영상 밴드를 계속 읽는다. 라벨만 받고 끝내는 명시 모드는 없다. `quality_insufficient`가 되면 라벨 취득 지점까지 오지 못할 수도 있다. 그러므로 기존 함수를 호출하고 사후에 RGB 파일을 지우는 방식은 라벨 전용 수집이 아니다.

`find_bare_targets173.discover()`는 current manifest의 실제 patch 행에서 `source_window.raw_source_crops.raw-esri_io.tif`를 찾는다. `label_source`, `label_year`, source URL과 동년 출처를 검증한다. 214의 선택 참조는 이 실제 행에 존재해야 한다. 독립 SURVEY 라벨은 여기에 없으며 현재 API로 소비할 수 없다.

`targeted_bare_plan.prepare_targeted_bare_jobs()`는 `source_lineage_ref` JSON의 `scenes[].source_crops` 중 SHA가 일치하는 단일 연차 수집행을 요구한다. SURVEY receipt를 기존 annual report 모양으로 꾸미는 것은 출처 계약을 속인다. 173과 175 모두 별도의 명시 소비 경로가 필요하다. 기존 경로의 존재 검사를 느슨하게 바꾸지 않는다.

## 첫 구현의 작은 범위

Root가 선택한 한 위치·한 연도·한 seed만 실행한다. 위치를 무작위 생성하거나 기존 whole province 중심을 자동 승인하지 않는다. 목적은 새 위치의 동년 weak label 확보이며 영상·patch 등록은 0개다. 기본은 실행하지 않는 plan이고 원격은 고정 요청 SHA와 별도 `--execute`가 있어야 한다.

먼저 구현할 파일 소유 제안은 다음과 같다. 편집권은 Root의 별도 배정 후에만 생긴다.

| 파일/함수 | 최소 변경 및 재사용 |
|---|---|
| 신규 `backend/app/data/bare_survey_contract.py` | `validate_survey_request(root, request, expected_digest)` / `validate_survey_receipt(root, receipt_ref, ledger_state)` / `discover_survey_labels(...)` / `validate_target_label_lineage(...)`. 엄격 스키마·핀·survey 출처·고정 256창 제안 검증을 담당한다. |
| 신규 `scripts/collect_bare_label_survey.py` | `run_survey(..., execute=False)` 단일 coordinator. global execution lock, 활성 원장, 예약, 서비스 계측/회로, trace/terminal 게시를 연결한다. 기존 target collector를 중첩 호출하지 않는다. |
| `scripts/collect_samples.py:collect_windows` | 신규 keyword `survey_context=None`. 기본 None은 기존 동작/출력/key 동일. 검증된 context가 있는 경우에만 Esri 라벨 공식검사·보존 직후, dominant deferral/여섯 밴드/patch 전에 SURVEY 전용 결과로 종료한다. legacy annual row를 공용 aggregate에 게시하지 않는다. |
| `scripts/find_bare_targets173.py` | 기존 `discover()` 계약을 유지한다. 미래 새 `discover_survey(...)`에서만 검증된 SURVEY refs를 받는다. raster 창 평가의 공통 순수 내부 helper 추출로 중복을 줄이되 legacy 전체 출력 동등 시험을 둔다. |
| `backend/app/data/targeted_bare_plan.py` | source_lineage의 기존 annual branch는 유지. 명시 `kind=BARE_LABEL_SURVEY_RECEIPT`일 때만 새 검증기를 호출하는 좁은 branch를 추가한다. target 필드/window/grid 검사는 그대로이며 plan 전체를 다른 출처 모드로 자동 전환하지 않는다. |
| `backend/app/data/targeted_inventory.py` 및 `targeted_live_guards.py`의 입력 연결 | 별도 survey 폴더의 검증된 registry/receipt를 source inventory·scene registry에 명시 합친다. 기존 scanner가 새 폴더를 자동 관측한다고 가정하지 않는다. 실제 SCL은 support로 포함하고 Esri 참조 라벨만 명시 역할로 구분한다. 기존 legacy SCL 계약은 유지한다. 후속170 coordinator에는 이 추가 입력을 고정 digest로 전달하는 좁은 연결이 필요하다. |
| 신규 `tests/test_bare_label_survey.py` + 기존173/175/170 회귀 | Temp raster/원장·모의 HTTP 및 기존 기본 출력 동등, 오류/미정산 보존을 검사한다. 새 schema/실행 가이드/시험 증거 문서를 같은 단위로 마감한다. |

작업 순서는 출처/계측 수집 계약 → 로컬 SURVEY 후보 소비 → 175/170 명시 연결이다. 첫 단계까지만 구현하면 `SURVEY_LABEL_SAVED`일 뿐 target 연결 완료가 아니다. 범위를 한 번에 승인하지 않더라도 최종 consumer가 어디서 막히는지 명시한다.

## 요청과 새 출력의 정확한 구분

제안 request v1은 아래 키를 정확히 허용하고 알 수 없는 키·bool 숫자·비유한 값·중복 refs·alias·변경된 pin을 거부한다.

- `schema_version:1`, `kind:BARE_LABEL_SURVEY_REQUEST`, `survey_id`, `current_manifest_ref:{path,sha256}`, `boundary_ref:{path,sha256}`, `ledger_ref:{path,sha256}`, `base_config_ref:{path,sha256}`.
- `seed:{seed_id,province,fixed_split,year,bbox_wgs84,period_start,period_end,justification_ref:{path,sha256}}`. 연도는 2020–2025, split은 고정 주 매핑과 동일, bbox/기간은 유한·동년·주 경계 관계를 검증한다. 현재 입력으로 승인되지 않은 실제 좌표나 근거는 이 RFC에 발명하지 않았다.
- `policy:{maximum_batches:1,maximum_cog_bytes:67108864,maximum_metadata_bytes:1048576,maximum_label_side:2048,request_spacing_seconds:2,transient_asset_retries:0,stop_on_first_429:true}`. 첫 구현에서는 정확값만 허용한다. `output_relative_path`는 신규 `data/bare-label-surveys/<survey_id>/`로 고정하고 source/patch/model/published 경로를 허용하지 않는다.

현재 원본/원장 ref는 입력 시점 스냅샷이다. 실행 시 global lock 안에서 active 파일 SHA와 비교한다. DATA의 고정 사본은 active와 바이트 SHA가 같으면 허용하되 실제 예약은 고정 active `CollectionLedger`만 사용한다. stale 원장 ref를 현재 잔액으로 해석하지 않는다.

새 폴더만 생성하고 `request.json`, `selection-context.json`, `trace.jsonl`, `stac-item.json`, 원본 라벨, 실제 받은 후보 SCL, `receipt.json`을 보존한다. registry는 `data/bare-label-surveys/registry.json`의 SURVEY 전용 인덱스이며 published manifest/annual training aggregate와 별개다. index는 성공 receipt 참조만 추가하며 trace/receipt가 증거 본문이다. 쓰기 전 원본 identity/미존재·경로 escape/reparse/alias를 검사한다.

receipt v1은 `kind:BARE_LABEL_SURVEY_RECEIPT`, `collection_purpose:SURVEY_LABEL_ONLY`와 다음 사실을 명시한다.

- 고정 request_ref/digest, 실제 batch key, config digest, 실행 전 source/ledger pins, seed/province/year/fixed_split.
- `selected_scene:{id,datetime,source_group,stac_ref}` 및 `candidate_scl_refs`와 선별 실측값. 실제 SCL이 없으면 빈 목록·품질 미검증이며 가짜 통과율을 넣지 않는다.
- `label:{path,sha256,source_url,license,dataset_version,label_year,grid:{crs,transform,width,height},footprint_native}`. signed query는 노출하지 않으며 URL host/path 및 공식 연도/Esri 계획 일치를 검사한다. 실제 header·affine·10m projected grid·한 밴드·허용 class를 다시 검산한다.
- `measurement:{metadata_body_bytes,cog_body_bytes,measurement_known,reserved_bytes,charged_bytes}`, terminal/정산 상태, 파일 크기/해시.
- `rgb_collected:false`, `patches_materialized:0`, `quality_eligible:false`, `training_ready:false`, `independent_ground_truth:false`.

registry에 등재됐다는 사실로 나지 gate 분자·분모·기여수나 coverage를 늘리지 않는다. 173의 전체 coverage는 계속 실제 current training manifest에서 계산한다. SURVEY 탐색 결과는 별도 `SURVEY_LABEL_WINDOW_PROPOSAL`로 출처를 구분하고, 기존 ranked 창 필드에 추가로 survey_receipt_ref/digest와 `origin:SURVEY_LABEL_ONLY`를 고정한다.

## 안전한 한 번 실행과 실패 정산

global `global-ledger.execution.lock`를 O_EXCL로 먼저 잡고 요청/원본/원장/경로/기존 pending·선택 공간을 검증한다. lock owner가 아닌 파일을 삭제하지 않는다. 새 survey key는 request digest/seed/year를 포함하고 기존 key 설정 변경·재사용은 거부한다. 기존 pending 2건 136,314,880바이트와 부분파일은 보존한다. 새 survey 때문에 전체 예산 4GiB가 늘어나지 않는다.

한 batch 65MiB를 공유 `CollectionLedger.reserve()`로 선예약한 뒤만 metadata/COG를 요청한다. 실제 residual은 실행 시 원장에서 계산한다. 209 완료 기록의 잔여 1,921,782,936바이트는 과거 시점 수치이며 현재 실행 승인이 아니다. discovery와 후속 target의 예약은 별개이고 최악 130MiB가 필요하다.

기존 서비스 `configure_request_spacing(2)`·공유 circuit·metadata budget·계측 fetch를 재사용한다. 후보 SCL/Esri가 COG 64MiB를 공유하고 STAC/product metadata는 1MiB를 공유한다. SCL 추가 비용을 라벨 비용 밖의 무료 작업으로 취급하지 않는다. 첫 429로 전체 중단·재시도0이다. survey는 1worker만 사용하므로 두 worker 상한 이내다.

survey에도 동일 scene registry와 지원영역 guard를 적용한다. 기존 source/patch·비적격/미등재/부분파일·pending·다른 survey의 실제 SCL 및 선택scene을 누락하지 않는다. scene id/source_group의 다른 split 사용을 거부한다. 발견된 새 창끼리/다른 연도 공간도 겹침 검사한다. discovery는 patch0이고 3000 물리 cap을 소비했다고 꾸미지 않으며, 실제 target 예약 시에는 기존 실물 inventory와 +1/표적 cap을 다시 검사한다.

try/finally에는 collector 진입 전후 실패를 모두 포함한다. 계측 가능한 종료만 실제 사용량을 정산한다. worker가 미진입했어도 예약 후 상태쓰기 실패로 계측을 확인할 수 없으면 전액 보존한다. terminal 쓰기·정산·registry 게시 각각의 성공 여부를 trace로 구분한다. 강제 종료 뒤 trace가 있다고 자동 환불/완료 판정하지 않는다. `CollectionLedger`와 registry는 단일 원자 transaction이 아니므로 정산 후 registry 게시 실패는 `SETTLED_UNPUBLISHED`로 기록하고 수동 검토한다. 반대로 미정산 receipt를 후보 소비자가 받아들이지 않는다. 복구 journal만으로 부분 전송량을 추정하지 않는다.

## 기존 target consumer에 진실하게 넘기기

새 `discover_survey()`는 exact receipt path/SHA 1개, 그 receipt에 명시된 실제 label ref만 받는다. 정산 원장 key/config digest·실제 파일SHA/연도/grid를 검증한다. original manifest의 ref인 것처럼 `label_refs`에 삽입하지 않는다. 새 256창의 선언 나지≥256·주내≥95%·ignore/class·실측 native geometry를 평가하고 고정 proposal을 만든다. 전체 cohort coverage와 SURVEY 창 스캔 범위를 따로 표시한다.

175의 새 lineage branch는 SURVEY receipt를 명시 소비하고 독립 검산한다. 기존 `scenes` 행을 합성하지 않는다. 표적 plan/request의 실제 label window/CRS/footprint/선언 count와 170의 source/pending/support/selectedscene/window/split guard는 유지한다. survey scene은 출처 anchor이며 후속 target 실제 선택scene을 보장하지 않는다. 후속 scene이 달라지면 저장 survey SCL을 target 품질 증거로 재사용하지 않는다.

213의 self-support 공백은 그대로 남는다. 첫 구현에서는 이미 받은 survey SCL/support와 겹치지 않는 창만 넘긴다. target 고유 SCL/실영상 품질은 170의 같은 실행 안에서 새로 확인한다. 중앙1024 밖의 확대2048 라벨에서 발견한 창에 중앙 SCL 품질을 복사하지 않는다. own SCL 겹침이 발생하면 `SURVEY_PREVIEW_SUPPORT_OVERLAP`로 차단한다. 이름 변경·모든 SCL 제외·legacy SCL 예외 완화는 금지다. provenance로 좁게 검증하는 preview 재사용은 별도 후속 설계/승인 범위다.

최종 image-valid≥80%, 주내≥95%, 실제 patch 나지≥256은 그대로다. 198 선별 강화 선택 옵션은 최종 품질 검사를 대체하지 않는다. 후보가 0이거나 overlap/품질 조건이 미충족이면 정직하게 0/차단으로 끝낸다. .5% 비율과 split별 기여5 충족 여부는 실제 target native/QA 후에만 재계산한다.

## 수락 조건과 다음 결정

1. **합성/격리 시험:** Temp 실제GeoTIFF+모의HTTP로 선택scene/SCL→Esri→명시 조기종료를 검증한다. 여섯 밴드/materializer 0호출·aggregate/model 원바이트 동일·고정 split·기본모드/key/출력 동등을 확인한다. 214 selectedrefs·175 annual lineage를 모두 회귀한다.
2. **오류 시험:** 변조 ref/header/연도/공식 URL/class, bool/NaN, path alias/reparse, duplicate/다른split scene, pending/상호/SCL 겹침, budget64MiB+1MiB, 첫429·전역2초, 예약후context쓰기실패·worker finally실패·정산/게시실패를 검사한다. 미계측 전액 보존과 owner lock 해제만 검증한다.
3. **로컬 연결 검증:** 별도 승인된 저장 SURVEY receipt 1개에서 proposal→175 exact target→170 plan-only까지 한 번 연결한다. 모의 영상품질 통과를 실제 품질 성공이라 표시하지 않는다. 지금은 실 SURVEY receipt가 없어 이 단계가 막혀 있다.
4. **운영 실행:** Root가 고정 source/원장 잔액·명시 seed·새 source pin/코드 시험을 독립 검토한 뒤 단1회 survey 실행을 별도로 승인한다. 새 candidate가 있을 때만 별도 target request/실행/native/QA를 승인한다. 본 문서는 어느 실행도 승인하지 않는다.

Root에 먼저 필요한 결정은 신규 SURVEY 스키마/저장소/단일 coordinator와 기존 collector의 기본off hook 소유 배정이다. 이어 173/175의 명시 소비 branch를 함께 검토해야 실제 소비 연결이 된다. 현재 UI/API 노출은 없고 이해자료에는 라벨 발견·영상 품질·학습 준비를 구분해 반영한다.
