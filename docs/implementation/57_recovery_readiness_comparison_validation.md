# 57. 저장 readiness와 물리 corner 보고서의 범위·근거 대조

## 쉬운 설명과 상태

이 도구는 원본 manifest, 저장 readiness, 저장 물리 source corner 보고서의 **고정 SHA를 확인하고 JSON snapshot끼리 연결되는지** 대조한다. 이미 저장한 차단 근거와 물리 자료 전체의 근사 공간 진단이 서로 다른 범위를 가졌다는 점을 표시한다. 새 readiness 판정, raster 헤더 확인, 픽셀 분석, 공간 연산을 실행하지 않는다.

구현·합성 시험은 `TESTED_SYNTHETIC`이다. 실제 자료 실행과 전체 회귀는 Root가 수행해 별도 증거로 기록한다. 모든 결과는 `BLOCKED`, 승인 false, 환불 0, exactly-once `UNKNOWN`이다. `CONSISTENT_SAVED_SCOPE_METADATA`는 세 저장 문서가 검사한 메타데이터 계약에 맞는다는 뜻이며 현재 영상·기하·학습 적격성 또는 차단 해제를 보증하지 않는다.

## 입력과 신뢰 경계

- manifest: DATA root 아래 `first-group-training-esri-v1/annual-window-report.json`, caller SHA 필수, 최대 64 MiB.
- readiness: DATA root 아래 `first-group/readiness-resume-20261017.json` 기본값 또는 `--readiness`, caller SHA 필수, 최대 32 MiB.
- corner report: 프로젝트 `evidence` 아래이면서 inspected DATA root 밖의 기존 JSON, caller SHA 필수, 최대 32 MiB.
- 세 SHA는 lowercase 64자리 hex, 입력은 서로 다른 파일이어야 한다. UTF-8만 허용하고 BOM/NUL/UTF-16/32, 중복 key, NaN/Infinity/overflow float, 깊이 32 초과를 거부한다. 깊이는 JSON decode 전에 검사한다.
- 세 파일은 각각 최초/최종 두 번 제한된 읽기를 수행하고 SHA와 size/mtime/ctime/inode/device를 대조한다. 따라서 JSON byte read 총 상한은 2 × (64+32+32) MiB이다. raster byte 예산이나 raster SHA 검사가 아니다. 원격·DATA/evidence root 이탈·논리 경로 재지정은 거부한다. 최종 비교는 원자 snapshot 보증이 아니다.

## 검사 범위와 계약

원본 JSON의 모든 physical scenes를 대상으로 명시 province, optional split, source_window.path/SHA 형식과 canonical 기대 SHA 충돌을 검사한다. province 추정·quality_status 필터링은 하지 않는다. 최대 100,000 rows, 10,000 canonical sources, 10,000 cross-split pairs를 계획한다. raster path는 resolve만 하며 raster 파일의 존재/stat/header/content를 확인하지 않는다.

`readiness.default_policy().province_splits`의 현재 6개 주 4/1/1 mapping과 해당 구현 파일 SHA 및 mapping SHA를 기록한다. 저장 readiness의 policy 및 group_splits, 단일 input_manifest canonical path/SHA를 대조한다. `province_groups`는 저장 component 연결로 그대로 전달한다. component 개수와 group_splits key 개수는 같은 개념이 아니므로 두 개수의 차이를 오류로 보지 않는다.

저장 eligible patch count는 train/val/test의 bool 아닌 비음수 정수여야 하고 physical count를 초과하면 issue이다. 원본 class count·적격성·quality 필터·배정 과정은 다시 계산하지 않는다. 저장 blockers를 순서·내용 그대로 출력에 복사하며 새 원인으로 바꾸지 않는다. `prepared_payload` 필드가 필수이고 null이면 eligible scene witness는 `UNKNOWN_NOT_PERSISTED`, 내용이 있으면 `PRESENT_NOT_ANALYZED`이다. token/bbox 개별 witness를 이 도구가 분석하는 계약은 없으므로 분기 원인은 언제나 `UNKNOWN_NOT_PERSISTED`이다. blocker 설명 문자열, verified_files, province component 연결만으로 token 또는 bbox 분기 원인을 확정하지 않는다.

corner report는 같은 manifest, 현재 고정 policy map·구현 SHA를 참조해야 한다. JSON source metadata로 canonical sources·각 source의 rows/provinces/splits 및 모든 unordered cross-split pair를 재구성해 유일 집합을 대조한다. 동일 source의 여러 split은 direct finding, within-split pairs는 OUT_OF_SCOPE이다. 입력 보고서의 다음 항목도 검사한다.

- producer schema/kind/mode/status/scope, physical counts, source 계획/시도 수, pair 계획/기록/intersection 시도 수, budget, 완료 분류, issues 및 finding 목록.
- 저장 GTiff header의 양수 int dimensions/count, nonblank CRS, 유한·비특이 affine 6계수, band count와 dtype 길이. 저장 corner의 4개 2D 유한 좌표·범위, pixel-edge corners, closed Polygon ring, topology 상태/유한 positive planar area, always_xy/errcheck/offline flag. **이는 저장 필드의 최소 구조·논리 검사이며 현재 header 또는 geometry 재검증이 아니다.** projection 계산이나 GEOS를 호출하지 않는다.
- 저장 Shapely/GEOS·pyproj/PROJ runtime 정보, network entry/exit 일치 및 restored true, 비실행·비승인·무쓰기·무네트워크 flag.
- pair status/area/boolean flags 일관성. DISJOINT는 empty/area0, CONTACT는 nonempty/area0/touches, positive overlap은 정확히 area>0이며 미세 양수도 숨기지 않는다. equal과 양방향 contains는 일관되어야 한다. 큰 정수 면적을 float로 옮길 수 없으면 issue로 진단한다.

일부 source/pair 누락, 중복, NOT_CHECKED/UNKNOWN, issue 또는 카운트·flag 모순이 있으면 `ISSUES_FOUND`이고 전체 disjoint로 요약하지 않는다. `stored_corner_all_cross_pairs_disjoint`는 전수 계획된 쌍이 1개 이상이고 모든 snapshot 계약이 충족되며 각 쌍이 DISJOINT일 때만 true이다. 후보 pair가 0인 경우 all-disjoint는 false이다. `stored_corner_no_cross_split_candidates` 역시 완전한 저장 보고서에서 positive finding과 shared source finding이 모두 없을 때의 좁은 요약이다. 이 값은 접촉·정확 공간독립·eligible leakage 해결의 증거가 아니다.

## API와 사용법

내부 Python 진입점:

```python
inspect_recovery_readiness_comparison(
    data_root, expected_manifest_sha256, expected_readiness_sha256,
    corner_report_path, expected_corner_sha256, *, readiness_path=None,
)
```

실제 명령은 Root가 새 출력 파일로만 실행한다.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python scripts/inspect_recovery_readiness_comparison.py --data-root data `
  --expected-manifest-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --expected-readiness-sha256 6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db `
  --corner-report evidence/integration/recovery-source-split-overlap-live-final-20261017.json `
  --expected-corner-sha256 ce78468e38d432a1bfb3894fc80c2d3c04751d4458728c0db44a141de862846b `
  --output evidence/integration/recovery-readiness-comparison-live-final-20261017.json
```

CLI의 명시 상대 입력 경로는 현재 작업 디렉터리 기준이다. Python core API의 상대 readiness 경로는 DATA root, 상대 corner 경로는 project evidence 기준이다.

기본 stdout은 ASCII JSON이다. `--output`은 project evidence 아래 DATA 밖의 새 파일로만 UTF-8 exclusive create한다. 기존 파일/입력 alias는 덮어쓰지 않는다. stderr는 CP949 환경에서도 ASCII escaped 오류를 반환한다. snapshot 내용의 issue는 안전한 진단 JSON을 반환하며 CLI 종료0은 issue0이나 운영 승인과 같은 뜻이 아니다. pin/path/strict JSON/변경/한도 오류는 종료1이고 새 결과 파일을 쓰지 않는다.

주요 출력: `comparison_status`, `inputs`, `fixed_split_policy`, `physical_row_counts_by_fixed_split`, `saved_eligible_patch_counts_by_split`, `physical_minus_saved_eligible_by_split`, `saved_readiness_blockers`, `saved_province_groups`, `eligible_scene_witness_status`, `shared_source_token_or_bbox_branch_cause`, `corner_snapshot_complete_and_consistent`, `stored_corner_all_cross_pairs_disjoint`, `issues`.

## 시험과 한계

관련 합성 시험: `tests/test_recovery_readiness_comparison.py`. 실행 로그: `evidence/integration/recovery-readiness-comparison-tests-20261017.log`. 작은 fixture는 project evidence 임시 경로에만 생성한다. 원본 raster가 존재하지 않아도 저장 근거 대조가 성공하는 시험 및 readiness.assess/header 호출 trap으로 현재 자료를 재검사하지 않음을 확인한다. root별 경로·pin/UTF-8/깊이/중복 key·NaN/수치·SHA 충돌, 변경·논리 retarget, partial/중복 pair·typed counts, provenance, positive/contact/tiny positive, runtime/header/corner 필드 누락, nonexecution/network flags, CP949 stdout·새 UTF-8 출력과 입력 보존을 확인한다. 독립 시험과 전체 회귀는 같은 시험을 중복 합산하지 않는다.

실제 사전 확인에 따르면 saved eligible는 628/233/250(1111), physical은 848/272/264(1384)이며, 저장 blocker는 5개다. 이러한 사전 관측은 이 구현의 실제 실행 완료를 뜻하지 않는다. 최종 실제 검사는 Root의 pinned 3JSON 증거를 확인한다. 현재 저장 snapshot에 eligible scene/token/bbox witness가 없으므로 물리 corner 보고서가 모두 DISJOINT여도 기존 shared-source 및 class 관련 차단은 해제하지 않는다.

이 기능은 공개 API·프론트 상태·버튼 계약이 없는 내부 읽기 CLI이므로 UI 변경이 필요 없다. 기존 원장·예약 136314880B·lock·모델·분할·collector·readiness policy를 변경하지 않는다. label 과학적 의미, 공식 기하 정확도, current content hash, 정확 footprint, 픽셀 coverage, 운영 정산·자동 재개는 검증하지 않는다.

## Root 실제 저장자료 범위 대조

**VERIFIED_REAL(고정SHA JSON스냅샷 일관성·범위 대조 한정):** Root CP949 CLI 종료0, [실제 JSON](../../evidence/integration/recovery-readiness-comparison-live-final-20261017.json), [CLI 로그](../../evidence/integration/recovery-readiness-comparison-cli-final-20261017.log). 세입력고정SHA 아래 CONSISTENT_SAVED_SCOPE_METADATA/issue0, 저장blocker5를원형보존했다. physical1384(train848/val272/test264)와저장eligible1111(train628/val233/test250), 산술차이220/39/14를표시했다. 이차이는제외행목록·제외이유를복원한것이아니다.

저장corner의91source/2227전수교차진단기록이완료·일관함을대조해 recorded all-disjoint=true/no-candidates=true로표시했다. 이는현재영상·기하를다시검사한것이아니다. savedprepared_payload=null/eligible_scene_witness_status 및 shared_source_token_or_bbox_branch_cause는UNKNOWN_NOT_PERSISTED이며 저장Banten–WestJava연결성분맵은분기witness가아니다. 현재policy implementationSHA대조는저장readiness생성시점코드버전의증명이아니다.

현재rasterstat/header/pixels/GEOS/readiness.assess·적격성·분할누출해결·source내용SHA재검증은없었다. 실제companion비교는Root만1회, 구현/독립담당은합성JSON만사용했다. 원본/원장/lock/예약136314880B/분할/모델·기존5차단·terminal없는2건·BLOCKED/학습·실행·정산·재개승인false/환불0 유지.

다음 PLANNED 작은 단위는 향후준비성진단에서 source-group/scene-token/bbox 연결증거를제한저장할계약과순수진단helper를구체화하는작업이다. eligibility를증명하는입력이없으면증거부재로표시하고이과거보고서의원인분기를소급추정하지않는다. 기존assess/gate/정책/분할변경·연결통합/재실행은별도후속이며현재단위에서수행하지않았다.

## Root 전체 회귀·보존

최종관련17PASS9.343초/독립17PASS8.723초, 초기16·중간17/8.876초는보완전이력이며독립시험을전체에중복합산하지않는다. 독립검토의equal/contains모순재현후논리검사·hugeinteger면적예외·runtime/header/corner최소형식·prepared_payload필수키/group_splits·CLI상대경로를보완했다. [전체 회귀](../../evidence/integration/recovery-readiness-comparison-full-tests-20261017.log)는 **538건/537PASS/1SKIP/174.829초/종료0**이다. SKIP은기존OSsymlink권한/deterministic경계시험PASS다.

[보존 증거](../../evidence/integration/recovery-readiness-comparison-live-integrity-20261017.json)는 보호132참조SHA·존재/기존계약18SHA/입력3JSONSHA불변·이전추적코드/데이터/계약변경0·저장blocker5원형완전보존을 기록한다. 이는현재source/raster·기하/원자snapshot증명이아니다. 원장/lock/예약/분할/모델·준비성차단/모든승인false·환불0/BLOCKED를유지했다. 공개API/UI상태변화없는내부CLI이므로이번UI수정·기존49UI시험/build·실브라우저재검증은불필요하다. 향후화면연결시확정API·상태·오류·실제근거를web_ui에전달한다.


## 연결 근거 후속 상태

[58 연결 근거 순수 helper](58_readiness_connectivity_witness_validation.md)의 구현·합성 시험을 완료했다. 이 함수는 향후 caller가 명시적으로 공급할 메타데이터를 진단한다. 기존 saved report의 적격 장면 근거는 여전히 부재하며 원인 UNKNOWN_NOT_PERSISTED를 바꾸지 않는다. readiness에 증거를 통합·보존하는 작업과 실제 eligibility 신원 검증은 후속 PLANNED이며, 이 문서의 실제 scope 대조·기존5차단 판정은 유지한다.
