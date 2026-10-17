# 원본영상 헤더 네 모서리·명시 주 교차 최소 진단 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 작은 GTiff/GeoJSON·좌표변환·엔진 오류 fixture를 포함한16개 시험을 통과했다. **VERIFIED_REAL(계획 메타데이터):** 고정 manifest는 source image91개, 명시(source,boundary,province)고유 관계86개, 경계1파일/482,365B와 legacy80행 UNKNOWN을 갖는다. 실제91헤더/경계1회 진단은 root가 별도 근거로 확정한다. **BLOCKED:** 실제 픽셀 내부 포함률·정확 footprint/면적·source간 공간 독립/분할 누출·공식 경계/기관 승인·과학성능·정산/재개는 미검증이다.

[문서54](54_recovery_boundary_relations_validation.md)의 지역 도형 사이 관계와 별도로, source_window의 **헤더 네 pixel-edge 모서리를 직선으로 연결한 임시 polygon**과 명시된 주 geometry를 최소 진단한다. source 바이트를 다시 해시하지 않고 원본 래스터/경계/분할/모델·기존 코어·원장을 변경하지 않는다.

## pin·명시 계획·진단 계층

[recovery_source_footprints.py](../../backend/app/data/recovery_source_footprints.py)의 `inspect_recovery_source_footprints`가 고정 aggregate manifest를 caller SHA로 pin한다. 기존 private bounded manifest/boundary read·strictUTF8/깊이/JSON·구조/위상·safeGTiff header·관계 helper를 읽기 재사용하며 public inspector 재호출·경계 재읽기를 하지 않는다.

source_window.path/sha256은 명시되어야 한다. boundary_path/boundary_sha256의 양키가 없는80행은 UNKNOWN_BOUNDARY_REFERENCE_ABSENT이며 기본 경로나 다른 주 feature로 연결하지 않는다. source 자체의 헤더는 이 행에서도 검사한다. declared boundary가 있으면 row.province는 nonblank 문자열이어야 한다.

경로/기대SHA 형식·canonical상충·누락 파일·partial/null/malformed source/boundary 참조는 전체 plan INVALID이며 헤더/경계 content 읽기를 시작하지 않는다. source/경계가 같은 canonical 경로에 상충 SHA를 가지는 경우도 거부한다. source SHA는 형식·상충만 확인하고 새 byte 일치 근거로 표현하지 않는다.

고유 source-header 예산은 기본128/정수1..10000, 고유(source,boundary,province)관계는 기본256/정수1..10000이다. caller가 실제91/86으로 제한할 수 있다. 전수 계획이 예산보다 크면 source header0·관계0으로 실패한다. 경계16파일/4MiB/128feature/100000position/depth32·manifest 최초/최종각64MiB도 그대로 적용한다. 이 한도는 hard CPU/time 보장은 아니다.

진단 계층은 다음과 같이 구분한다.

- 명시 plan/안전 경로/한도 실패는 파일 관측 전 차단한다.
- 경계 content SHA·구조·위상·지역 연결이 진단상 실패해도 유효한 source header와 임시 corner polygon은 독립적으로 검사할 수 있다.
- 유효한 명시 주 geometry가 없으면 관계는 UNKNOWN_BOUNDARY_PROVINCE_GEOMETRY다. 정상 경계여도 row.province가 없는 key라면 UNKNOWN이며 다른 feature를 선택하지 않는다.
- source header/변환/임시 geometry 오류면 관계는 UNKNOWN_SOURCE_FOOTPRINT다. 다른 source의 알려진 진단 결과와 구분한다.
- strict 인코딩/JSON·자원 한도·경로/stale 같은 global 안전 오류는 전체 실행을 실패시킨다. 모든 종류의 경계 오류에서 항상 source header0이라고 표현하지 않는다.

## source 헤더와 네 모서리

고유 source91개를 각각 한 번 safe GTiff helper로 읽는다. TIFF magic·실제 driver GTiff·read-only/internal georef·PAM NO/READDIR EMPTY_DIR/PROJ_NETWORK OFF/VRT Python NO, 일반 로컬 파일·data root confinement·finite/nonsingular affine·CRS/양의 dimensions 조건을 사용한다. pixel read나 이미지 전체 SHA는 호출하지 않는다.

원본 width/height의 **pixel-edge** `(0,0),(width,0),(width,height),(0,height)`에 전체 affine6계수를 적용한다. pixel center나 `+0.5`를 사용하지 않고 회전/skew도 보존한다. 축정렬 bbox의 네 점으로 대체하지 않는다.

이 네 점만 pyproj로 source CRS→EPSG:4326 임시 변환한다. `always_xy=True`, `errcheck=True`, `allow_ballpark=False`, `only_best=True`다. 설치 runtime pyproj3.7.2/PROJ9.5.1과 실제 실행 버전/네트워크 상태를 보고서에 기록하며, 필드가 없으면 UNKNOWN이다. 원본 raster나 boundary CRS를 다시 투영해 저장하지 않는다.

pyproj 네트워크의 이전 상태를 관측하고 변환 동안 false로 설정·확인한 뒤 finally로 이전 값을 복원한다. transformer의 network context도 false인지 검사한다. 정상과 예외에서 기존 true/false 상태를 보존하고, 최종 복원이 미확인/불일치면 PROJECTION_NETWORK_RESTORATION_UNVERIFIED issue다. 이 내부 CLI의 runtime 설정 관측이며 다른 외부 thread가 동시에 상태를 바꾸는 환경에 대한 원자적 격리 보장은 없다.

변환점은2D finite longitude[-180,180]/latitude[-90,90]여야 한다. 경도 span 또는 연속 모서리 jump>180이면 anti-meridian을 잘못 잇는 거대 polygon을 만들지 않고 UNKNOWN_UNSUPPORTED_LONGITUDE_WRAP로 남긴다. 임의 longitude wrap/분할/repair를 하지 않는다. 변환 실패·엔진 부재/오류·유효하지 않은 임시 polygon도 UNKNOWN이다.

## 명시 주 geometry와 관계

경계는 같은 raw1회 SHA/strictJSON·FeatureCollection/2D/ring/province_id 구조 검사와 feature별 GEOS 위상을 통과한 geometry만 cache한다. corner polygon 역시 nonempty/valid/finite positive area여야 한다. 명시 source/boundary/province 관계마다 한 번 비교하며 반복행을 한 결과의 scene_indexes로 합친다.

기존 관계 helper의 DISJOINT/BOUNDARY_CONTACT/POSITIVE_AREA_OVERLAP/UNKNOWN 진단을 사용한다. 교차 area는 **정확히>0**이면 positive이며 임의 epsilon으로 숨기지 않는다. 포함/동일 여부도 임시 geometry 관계일 뿐 픽셀 포함 판정이 아니다. area_units=square_degrees_planar_diagnostic이며 m²/km²·측지/공식 면적이 아니다. ratio/비율 값을 계산하지 않는다.

corner-only polygon은 투영 곡선인 실제 영상 외곽을 densify한 footprint가 아니다. 네 변을 직선으로 이어 만든 근사 진단이며 정확한 footprint·면적·국경/주 내부 충분성·pixel QA를 증명하지 않는다. DISJOINT도 자동 행정/자료 오류로 확정하지 않는다. source대source 교차/공간 누출·학습 split 독립성은 이번 범위가 아니다.

## 상태·보존·한계

known 진단이 완료되어도 legacy80행은 KNOWN_CORNER_DIAGNOSTICS_PARTIAL/INCOMPLETE_BOUNDARY_REFERENCES다. projection/경계/관계 UNKNOWN이나 미복원 상태는 ISSUES_FOUND다. completion은 최소 진단 실행 완료이지 해당 주의 전체 영상 적격성이 아니다.

항상 status=BLOCKED, exactly_once_applied=UNKNOWN, ready_for_training/training_executed/scientific_accuracy_validated/settlement/execution/automatic_resume=false, 환불0·네트워크0·원본쓰기0이다. source_content_sha_revalidated/pixel_arrays_read/pixel_inside_ratio_computed/geodesic_area_computed/curved_edges_densified/exact_raster_footprint_verified/source_to_source_intersections_checked/training_split_leakage_resolved도 false다. 공식 ADM1·경계 권한·독립 기하 승인도 하지 않는다. 기존5ML blocker·terminal없는2건/예약136314880B와 원본/원장/lock/분할/모델 상태를 바꾸지 않는다.

파일 stat/논리 경로 target·manifest 최종 SHA를 전후 재확인하지만 원자 snapshot이나 OS lock을 제공하지 않는다. safe header 관측의 source SHA 형식 일치를 현재 이미지 내용 SHA 검증으로 표현하지 않는다.

## CLI·시험·인계

[inspect_recovery_source_footprints.py](../../scripts/inspect_recovery_source_footprints.py)는 CP949 stdout/stderr ASCII escape와 UTF8 새 evidence만 제공한다. 기존/evidence 밖/data root 아래 출력은 관측 전에 거부한다.

```powershell
python scripts/inspect_recovery_source_footprints.py --data-root data `
  --expected-manifest-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --max-source-headers 91 --max-relations 86 --max-local-bytes 4194304 `
  --output evidence/integration/recovery-source-footprints-live-20261017.json

$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_source_footprints.py -v
```

exit0은 BLOCKED 진단 보고서 생성이며 UNKNOWN/ISSUES가 있을 수 있다. pin/형식/경로/자원/stale global 오류는 exit1이다.

[시험](../../tests/test_recovery_source_footprints.py), [로그](../../evidence/integration/recovery-source-footprints-tests-20261017.log): **16 PASS, 9.217초**.4pixel-edge/rotation-skew/UTM alwaysxy errcheck/offline, network priortrue 정상·예외 finally복원과관측미복원issue, anti-meridian/비유한/range/퇴화UNKNOWN, source/관계cache·경계raw1회·legacyfallback금지/헤더유지, 접촉·disjoint·주키누락, 명시plan상충/예산0header, source SHA format-only·invalidheader/경계위상·계층분리, 픽셀/전체SHA/repairtrap·원본bytes/sidecar목록불변, 엔진부재/관계오류, strict인코딩/pin/root이탈/stale/alias·CP949/출력보호를 검사했다. 초기14시험은 마지막2개 보완 전 이력이며 최종16개다. 독립시험을 전체 회귀에 중복합산하지 않는다. 실제91source header와 경계는 root만 실행한다.

공개 API/화면 상태 계약 없는 내부 CLI라 UI 수정·실행 중 frontend 반영·브라우저 검증은 필요하지 않다. 후속 UI 연결은 web_ui에 확정 API·상태·오류와 실제 근거를 전달해야 한다. root는 실제 진단·보호대조·전체 회귀·원장/인계와 이해 에이전트 갱신을 담당한다.

## Root 실제 헤더·주 연결 진단

**VERIFIED_REAL(원본 GTiff 헤더와 모서리 직선근사 진단 한정):** Root CP949 CLI 종료0, [실제 JSON](../../evidence/integration/recovery-source-footprints-live-final-20261017.json), [CLI 로그](../../evidence/integration/recovery-source-footprints-cli-final-20261017.log). caller max_source_headers91/max_relations86 아래 헤더91/시도91, CORNER_ONLY_FOOTPRINT_VALID91, 고유연결86/시도86 모두 POSITIVE_AREA_OVERLAP·issue0다. 경계1파일482365B의 고정SHA를 확인했고 legacy80행 경계참조는 UNKNOWN/fallback없음, footprint_validation=KNOWN_CORNER_DIAGNOSTICS_PARTIAL/coverage=INCOMPLETE_BOUNDARY_REFERENCES/BLOCKED다.

실제 runtime은 Shapely2.1.2/GEOS3.13.1·pyproj3.7.2/PROJ9.5.1이다. projection network 상태는 entry=false/exit=false/network_state_restored=true다. 네 모서리를 always_xy/errcheck로 변환한 임시 polygon과 주 경계에 양수 교차가 있었다는 관측이다. 영상전체가주내/정확곡선외곽·픽셀inside비율/정확측지면적·source내용SHA/표본공간독립·고정분할누출해결을 증명하지 않는다. source_content_sha_revalidated/pixel_arrays_read/exact_raster_footprint_verified/pixel_inside_ratio_computed/source_to_source_intersections_checked/training_split_leakage_resolved는 모두false다. 원본geometry/래스터 재투영·수선·쓰기는 없고 실제헤더91개/경계1파일은 Root만1회 검사했다.

다음 PLANNED 작은 단위는 현재 source간미검사인 모서리 근사 영역과 고정split의 연결·교차 후보 진단이다. readiness.default_policy의 고정province_splits와 실제 소비 분할/적격성 계약을 먼저 확인하고 원본1384행의 물리적source 맥락과 적격패치 집합을 구분한다. 유일source/주/split 매핑·총pair예산을 전수 계획하고 임시파생geometry만 사용하며 분할 재배정/후보발행/정산/학습은 하지 않는다. 근사 교차 후보를 정확 경계·표본독립성 검증이나 기존5ML차단 해제로 표현하지 않는다. 현재 이 단위에서 source간교차나 readiness전체재검증은 수행하지 않았다.

## Root 전체 회귀·보존

최종관련16PASS9.217초/독립16PASS10.829초. 초기14시험은 계층분리·network최종복원확인 시험2개 추가 전 이력이며 최종16만 전체발견에 포함했고 독립시험을 중복합산하지 않는다. [전체 회귀](../../evidence/integration/recovery-source-footprints-full-tests-20261017.log)는 **506건/505PASS/1SKIP/161.521초/종료0**이다. SKIP은 기존OSsymlink권한/deterministic경계시험PASS다. [보존 증거](../../evidence/integration/recovery-source-footprints-live-integrity-20261017.json)는 보호132참조SHA·존재/기존계약16SHA불변·이전추적코드/데이터/계약변경0·원본91+경계1파일stat/prefix16와92부모목록변화0을 기록한다. 이는source전체내용SHA나원자snapshot 증명이 아니다.

원본/원장/lock/예약136314880B/분할/모델·5ML차단·terminal없는2건 보존·BLOCKED/모든학습·실행·정산·재개승인false/환불0 유지. 공개API/화면 상태 없는 내부CLI로 이번 UI수정·기존49UI시험/build·실브라우저 재검증 불필요. 향후 화면 연결은 web_ui에 확정 API·상태·오류·실제 근거를 전달해야 한다.

## 후속 고정분할 후보 진단

[문서56](56_recovery_source_split_overlap_validation.md)은 전체물리source의모서리근사·고정split연결과분할간교차후보를별도로진단한다. 본문주경계연결과구분하며,적격성/원본scene토큰·bbox정책/readiness재평가나분할누출해결승인이아니다.
