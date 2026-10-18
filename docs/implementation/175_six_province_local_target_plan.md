# 175 — 고정6주·6연도 로컬 나지 표적 계획

상태: `TESTED_SYNTHETIC`. [174 A 설계](174_six_province_targeted_execution_plan.md)의 로컬 계획 확장만 구현했다. `prepare_targeted_bare_jobs`는6주 고정 분할을 받아들이지만 성공도 기존 `LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED` / `EXECUTION_GUARDS_NOT_CONNECTED`, `execution_supported=false`다. **train/test 표적 실행은 구현·승인하지 않았다.** 170 dispatcher·live guard·collector·원장·173 실제 후보를 변경하거나 호출하지 않았다.

## 바뀐 계약

고정 map은 `app.data.readiness_connectivity_witness.FIXED_PROVINCE_SPLITS`의 단일 선언을 import한다. caller가 map을 덮어쓰는 입력 키는 없다.

| province | fixed_split |
|---|---|
| south_sulawesi | train |
| gorontalo | train |
| southeast_sulawesi | train |
| east_java | train |
| banten | val |
| west_java | test |

target province는 위 이름과 정확히 같아야 하고 fixed_split도 대응 값과 같아야 한다. 알 수 없는 주나 서자바=train·반텐=test 등 재배정을 `TARGET_INVALID`로 거부한다. 기존 exact schema, bool이 아닌2020~2025 정수 year, target ID 유일성, 최대2 target·batch, 모든 기존 정책값과 파일 읽기 상한을 유지한다. aggregate64MiB·라벨64MiB cap을 상향하지 않았다.

plan이 사용하는 각 province마다 경계 GeoJSON의 `properties.province_id`가 같은 feature가 정확히1개, base_config.aois의 id가 같은 항목이 정확히1개 있어야 한다. 누락·중복은 각각 `BOUNDARY_INVALID` / `BASE_AOI_INVALID`다. 다른 province의 경계나 baseAOI로 대체하지 않는다. 두 주가 한 plan에 있어도 target마다 자기 geometry를 선택하고 config AOI·province_id·job province/split을 그 target에서 파생한다. 마지막 target의 geometry를 다른 job에 재사용하지 않는다.

key는 `target256-bare-{province}-{year}-{target_id}-{plan_sha앞12}`다. 반텐의 입력 plan·정책·구조를 바꾸지 않았으므로 기존 반텐 key·job 전체 내용·config canonical SHA 계약은 유지한다. plan canonical SHA는 이전과 같은 알고리즘이다. 실제파일·경로·지문이 달라지면 동일한 SHA나 key를 보장한다는 뜻은 아니다.

## 실제 라벨 격자

기존 EPSG32748 literal 대신 **실제 고정 라벨의 projected CRS·미터 변환계수1.0·north-up10/-10 격자**를 요구한다. label은 내부 GTiff, 허용 정수형1밴드이고 GCP·RPC·subdataset은 거부한다. geographic CRS·feet 단위·회전·비유한 변환·9m/20m 등은 허용하지 않는다. 메타데이터의 CRS 문자열만 믿고 통과시키지 않는다.

각 라벨의 actual CRS 문자열/affine/shape와 source_label_grid가 정확히 같아야 한다. 실제256창의 모서리와 target_footprint_native도 정확히 같아야 하고, 실제 CRS에서 변환한 WGS84 corner envelope와 supplied bbox가 기존1e-8도 이내로 같아야 한다. 주별 CRS를 고정 표로 강제하지 않는다. 한 주가 적도/UTM 경계에 걸치더라도 실제 고정 라벨의 허용 격자를 기준으로 판단한다.

출처 SHA, proposal의 같은 crop/SHA·province/split/year·local offset, lineage의 유일한 crop와 label_year/동년URL 선언은 유지한다. 실제 라벨256창의 code8 수가 caller/proposal과 정확히 같고256 이상이어야 한다. 실제 주 경계 inside95%, 기존 적격/비적격/이력 patch와 source 영상의 양성 면적 겹침 거부, 두 target 사이의 교차연도·교차주 겹침 거부도 유지한다. 예외 시 부분 jobs를 노출하지 않는다.

TIFF 바이트는 기존 pinned MemoryFile로 읽고 PAM·외부 georeferencing·디렉터리 탐색을 비활성화하며 PROJ network를 OFF로 설정한다. source 년도 선언 검산은 현장 정답·촬영진실·과학적 나지 인증이 아니다. 라벨의 code8≥256은 앞으로 실제 영상·품질 마스크가 적용된 최종 나지 픽셀 성과와 다르다.

## 여전히 실행 차단

성공 플래그의 의미는 고정 로컬 라벨과 **manifest에 명시된** 기존 영상 겹침 관측뿐이다. pending/support footprint 전체·실제 Sentinel scene split·live B02·출력 배타·예산/429·전송/정산·최종256 quality mask·최종 나지·학습을 승인하지 않는다. 기존 실행 관련 false flags를 바꾸지 않았다.

174 B/C의 live selected scene 고정map/AOI binding 확장, 최신 manifest/ledger/167 inventory와 actual B02/참조의 소비 연결은 별도 소유·후속 작업이다. local plan이 train/test job 제안을 반환해도 현재 실제 dispatcher를 그 주에서 실행해도 된다는 뜻이 아니다. 이번 작업은 HTTP·Store·실데이터 읽기·수집·운영 원장 쓰기0이며 Temp 합성 GTiff만 사용했다.

## 시험 근거

```powershell
$env:PYTHONPATH='.runtime;.;backend;tests'
python -m unittest test_targeted_bare_plan -v
```

`evidence/integration/six-province-local-plan-agent-20261018.log`: 최종 **16 PASS / 16.204초**다.16개 시험에는6주×6연도36개 정상 fixture subtest, 관측173의 native CRS 형태(EPSG32748/32749/32750/32751/32651), 서자바와 반텐의 같은32748·다른split 구분, 잘못된 split/unknown주, boundary/baseAOI 누락·중복, 혼합2주의 서로 다른 geometry와 config marker, 기존 반텐 job 전체/key/config SHA 불변 회귀가 포함된다.36개 subtest를 별도36 PASS로 더하지 않는다.

라벨code8=255 거부/256 허용, feet·geographic·9m·20m, 실제 GCP/RPC/NaN transform GTiff 차단, 기존 SHA/lineage/native/bbox/overlap/경로 시험과 네트워크 차단 중 합성 로컬 파일 불변도 검증한다. 기존 잘못된 CRS 시험은 이제 다른 projected metre CRS 자체를 거부하는 대신 caller의 stale32748 grid와 실제32648 불일치를 `LABEL_GRID_MISMATCH`로 잡는다. 투영계 확장이 의도한 변화다.

수정 전 source SHA는 `4042ca3302581e08c59dee8109ed6bc1d8b21f2fa5decf463747b2cb4b0e845a`, test SHA는 `28d97cb45472512acf54250f6f5c80a1e334c2decb913bb671e40a72a7083453`다. 최종 전후 핀은 집중 로그와 Root 인계를 따른다. 초기14 PASS/19.142초 및 중간16 PASS/11.360초는 반복 실행 이력이며 합산하지 않는다. Affine/rasterio 경고는 시험 실패가 아니다.

내부 로컬 helper 확장이며 API/UI의 실행 상태나 버튼을 추가하지 않아 이번 단위 자체에 화면 연결은 필요 없다. Root의 독립 검토·이해자료·공통 인계 갱신 뒤에도 실제6주 표적 수집은 B/C와 실자료 검증이 남는다.

## Root 독립 검토·관련 회귀

`six-province-local-plan-independent-20261018.json`은최종source/test/doc핀을읽고A계약의차단결함0을기록했다.시험을재실행한결과와구분한다. Root는현재공유51194db와175최종시험의6모듈회귀를실행해 **77 PASS/0 SKIP/30.8192002초**를확인했다(`six-province175-root-related-20261018.py/.json/.log`).집중16개는관련77개안에포함되고36개fixture subtest를별도합산하지않는다.실GTiff/임시원장/모의HTTP범위이며운영수집0이다.

공유main51194db에는A의source SHA c2011f678a7860d734889abb96514daf1944b9ed888ee02dd502de8030a0fccb가이미포함됐지만이후보완시험/문서가마감되지않은시점이있었다.이단위는해당소스에맞춘175전체시험·관련설계상태·별도이해자료를같이완료해범위/기대값을일치시킨다.시험SHA ec240fdc2950e9b6219ece303a5df787bfd038e4280dbb07dad2272abccc6575다.175의해설/대본/FAQ는 `docs/understanding/175_SIX_PROVINCE_LOCAL_TARGET_PLAN.md`에기록했다.
