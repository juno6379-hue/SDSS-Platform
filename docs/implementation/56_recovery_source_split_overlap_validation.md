# 물리 source의 고정 split 간 corner 교차 후보 진단 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 작은 GTiff·고정 split·후보/실패 fixture를 포함한15개 시험을 통과했다. **VERIFIED_REAL(계획 메타데이터):** manifest 전체1,384physical행/source91개에서는 cross-split후보2,227쌍·동일단일split1,868쌍 OUT_OF_SCOPE·shared canonical source의cross-split0개가 예상된다. 실제 헤더/후보 진단은 root가 별도1회 실행으로 확정한다. **BLOCKED:** eligible표본 누출 해소·정확 footprint/픽셀중첩·분할 독립/과학성능·정산/재개 승인은 미검증이다.

[문서55](55_recovery_source_footprints_validation.md)의 source-주 관계와 별도로 이번 companion은 **물리 source 간 모서리근사 교차 후보**를 현재 고정 province split에 연결한다. 같은 source의 여러 patch를 독립 영상으로 중복 세지 않고 경계 레이어도 읽지 않는다. 후보 탐지는 분할 재배정·데이터 삭제·새 후보 manifest 발행·학습 실행을 하지 않는다.

## 실제 정책과 physical/eligible 구분

[readiness.default_policy](../../backend/app/ml/readiness.py)는 south_sulawesi/gorontalo/southeast_sulawesi/east_java=train, banten=val, west_java=test의4/1/1 정책을 반환한다. 구현은 이 실제 함수를 읽어 사용하며 호출자가 다른 map을 주입하는 옵션은 없다. 결과 fixed_split_policy에 함수·현재 implementation path/SHA·map·map SHA를 기록하고 종료 시 implementation 변경도 거부한다. 고정 실험 정책을 기관 승인으로 표현하지 않는다.

readiness는 이미지/라벨/quality 바이트·시기/출처/정규화·유효 픽셀·주 내부 비율·클래스 대표성·적격 patch 계수 등 추가 조건을 검사한다. 이번 함수는 그 gate를 실행하지 않고 **전체1,384physical행**을 대상으로 한다. quality_status로 필터하지 않는다. 실제 physical split행수 train848/val272/test264는 기존 eligible628/233/250과 별개이며, 원본 eligible1,111개를 새로 평가했다는 뜻이 아니다. 픽셀을 읽지 않으므로 eligibility_recomputed/eligible_subset_leakage_assessed/readiness_gate_revalidated=false다.

## pin·전수 계획·source mapping

[recovery_source_split_overlap.py](../../backend/app/data/recovery_source_split_overlap.py)의 `inspect_recovery_source_split_overlap(data_root, expected_manifest_sha256, max_source_headers=128, max_pairs=10000)`는 caller 명시SHA로 고정 aggregate를 pin한다. 기존 bounded64MiB/strictUTF8·depth32/중복키·비유한JSON guard와 source-header/corner helper를 변경 없이 읽기 재사용한다.

각 physical행에 명시 province와 source_window.path/sha256이 필요하다. province_id/aoi나 다른 행에서 값을 추정하지 않는다. 알 수 없는 주·boolean/누락/손상값·명시 row.split과 고정map 불일치·canonical기대SHA상충·파일누락은 plan INVALID/header0/pair0다. row.split이 없을 때에는 명시 고정 map을 사용하며 원본 행을 쓰거나 split을 재배정하지 않는다.

canonical source별로 province set/fixed split set·행 index/rows_by_split을 기록하고 헤더·geometry는 한 번만 만든다. 같은 canonical source가 여러 split에 참조되면 SHARED_CANONICAL_SOURCE_CROSSES_FIXED_SPLITS라는 **직접 메타데이터 finding**이다. source가 단1개라 서로 다른 source쌍0개여도 이 finding은 남는다. 이는 eligible데이터의 실제 사용/누출 해소 여부를 판정하는 기능은 아니다.

source header cap은 기본128/정수1..10000, pair cap은 기본/최대10000이다. caller가 실제91/2227로 제한할 수 있다. boolean/float/0/초과값은 거부한다. 같은source의여러행/role을한번만관측하고전수예산부족은헤더/쌍작업전에fail closed다.

## cross-split 쌍 계획과 OUT_OF_SCOPE

서로 다른 canonical source의 무순서쌍 중 **서로 다른 split조합이 하나라도 있는 쌍**을 검사한다. A={train,val}, B={train}은 공유train이 있어도 val↔train 조합이 있으므로 대상이다. split집합의 교집합이 있다는 이유로 제외하지 않는다. 결과 cross_split_combinations에 실제 다른 split조합을 기록한다.

계획 수는 전체source nC2에서 각 **동일 단일split** cohort의 nC2를 뺀 값이다. 이를 예산과 먼저 비교한 뒤 최대7개 split-set cohort 사이에서 후보만 열거하므로, 대량의 같은train-only source를 불필요하게 전수 geometry쌍 연산하지 않는다. multi-split source끼리의쌍은 같은train 조합도 포함할 수 있지만 다른split조합이 있으므로 대상이다.

양쪽이 같은단일split일 때만 within_split_pair_status=OUT_OF_SCOPE다. 이 범위의 source가 겹치지 않는다고 판정한 것이 아니다. source 하나의 shared-cross-splitfinding과 서로 다른 sourcepair 수를 합산하지 않는다.

모든source가같은단일split이거나source1개면 NO_CROSS_SPLIT_PAIR_CANDIDATES다. source1개가여러split을공유하면 SHARED_SOURCE_FINDINGS_NO_DISTINCT_PAIRS다. 쌍0을누출0/승인통과로표현하지않는다. plan미평가이면계획수null이다.

## 헤더·임시 corner polygon·관계

기존 안전 GTiff helper로 source 헤더만 읽는다. TIFF magic/GTiff read-only/internal georef, PAM NO·READDIR EMPTY_DIR·PROJ NETWORK OFF·VRT Python NO와 finite nonsingular affine/CRS·dimensions를 검사한다. 이미지 전체 SHA를 현재 재검증하지 않으며 recorded SHA는 형식/상충만 확인한다.

기존 corner helper가 4개 pixel-edge `(0,0),(w,0),(w,h),(0,h)`에 일반 affine/회전/skew를 적용한다. offline pyproj의 always_xy/errcheck·allow_ballpark=false/only_best로 임시 EPSG:4326 변환을 하며 이전 network 설정은 finally로 복원한다. antimeridian jump/span>180·비유한/범위 밖/변환/geometry 오류는 UNKNOWN이다. runtime 버전과 전후 network 상태/복원 여부를 기록하고 복원이 미확인되면 issue다. 원본 래스터/경계/geometry를 재투영해 저장하지 않는다.

고유 source geometry를 cache하고 계획 쌍은 한 번만 관계 진단한다. DISJOINT/BOUNDARY_CONTACT/정확한 area>0의 POSITIVE_AREA_OVERLAP·containment/equality·미세 교차를 기록하며 임의 epsilon을 쓰지 않는다. area는 평면 degree² 진단이고 정확한 측지/공식 면적이 아니다.

source footprint가 invalid/UNKNOWN이면 해당 source가 포함된 쌍은 NOT_CHECKED_INVALID_CORNER_FOOTPRINT다. 다른 유효 source의 쌍은 독립적으로 진단할 수 있다. pair_diagnostic_record_count는 검사 안 됨을 포함한 계획 쌍별 기록 수, intersection_attempt_count는 실제 교차 함수 시도 수다. GEOS 오류는 UNKNOWN으로 남긴다.

positive_area_overlap_candidates는 **corner 근사 후보 finding**이며 eligible 표본의 정확한 누출·학습 독립성 판정이 아니다. 모서리 사이는 직선이고 곡선 edge를 densify하지 않았으며 픽셀/label/quality·source 내용 SHA를 읽지 않았다. shared source·교차 후보가 있든 없든 기존 5개 ML blocker와 ready_for_training=false를 바꾸지 않는다.

## 경계 미사용·보존·승인 한계

boundary_status=BOUNDARY_NOT_USED다. 이전 단위에서 경계가 미기재된 80행도 이번에는 추정 연결하지 않고 다른 physical source와 동일하게 명시 source/province만 사용한다. 경계 파일이나 source-주 포함률을 현재 검사했다고 표현하지 않는다.

정책/manifest SHA·경로 target·source stat을 전후 확인하지만 원자 snapshot·OS lock을 제공하지 않는다. 입력/쌍 한도도 hard CPU/time 보장은 아니다. source 간 근사 관계를 실제로 진단해도 geometric_independence_verified/training_split_leakage_resolved=false다.

항상 status=BLOCKED, exactly_once_applied=UNKNOWN, ready_for_training/training_executed/scientific_accuracy_validated/settlement/execution/automatic_resume=false, 환불0·네트워크0·원본쓰기0이다. 원본 데이터·원장·예약136314880B/terminal 없는 2건·lock·분할·모델을 보존하며 원본 split 재배정/다운로드/학습/후보 발행을 하지 않는다.

## CLI·시험·인계

[inspect_recovery_source_split_overlap.py](../../scripts/inspect_recovery_source_split_overlap.py)는 CP949 stdout/stderr ASCII escape와 UTF8 새 evidence만 제공한다. 기존 파일/evidence 밖/data root 아래 출력은 진단 전에 거부한다.

```powershell
python scripts/inspect_recovery_source_split_overlap.py --data-root data `
  --expected-manifest-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --max-source-headers 91 --max-pairs 2227 `
  --output evidence/integration/recovery-source-split-overlap-live-20261017.json

$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_source_split_overlap.py -v
```

exit0은 BLOCKED 후보 진단 보고서 생성이며 finding/UNKNOWN이 있을 수 있다. pin/strict 인코딩/경로/한도/stale·정책 변경 실패는 exit1이다.

[시험](../../tests/test_recovery_source_split_overlap.py), [로그](../../evidence/integration/recovery-source-split-overlap-tests-20261017.log): **15 PASS, 9.129초**. physical 범위(quality_insufficient도 포함)/고정 정책 SHA, shared canonical 단일 source의 0pair finding, multi-split의 공통 split 후보·전수 계획, 동일 단일 split 제외, canonical cache·경계 미읽기, province/row.split/source 형식 상충의 plan0header·예산, invalid footprint 관련 쌍 NOT_CHECKED·시도 계수, contact/equal/tiny positive/UNKNOWN, network 정상/예외 복원·엔진/antimeridian, 정책 구현 변경 거부, 픽셀/전체 SHA/public reread/repair 금지·원본 bytes/목록 불변, strict 인코딩/pin/경로/누락/stale/alias·CP949/출력 보호를 검증했다. 구현/독립 담당은 합성자료만 사용하고 실제 91개 헤더는 root만 1회 검사한다. 독립시험을 전체 회귀에 중복 합산하지 않는다.

공개 API/화면 상태 계약 없는 내부 CLI라 UI 수정·실행 중 frontend 반영·브라우저 검증은 필요하지 않다. 후속 UI 연결은 web_ui에 확정 API·상태·오류와 실제 근거를 전달해야 한다. root는 실제 진단·보호 대조·전체 회귀·원장/인계와 이해 에이전트 갱신을 담당한다.

## Root 실제 물리 source 교차 후보 진단

**VERIFIED_REAL(원본 전체물리행과 헤더4모서리 근사 후보 한정):** Root CP949 CLI 종료0, [실제 JSON](../../evidence/integration/recovery-source-split-overlap-live-final-20261017.json), [CLI 로그](../../evidence/integration/recovery-source-split-overlap-cli-final-20261017.log). 고정manifest1384physicalrows(train848/val272/test264),91canonicalsource 아래 caller max_source_headers91/max_pairs2227을 사용했다. 헤더91/시도91·분할간계획2227/진단record2227/실intersection2227 모두DISJOINT, 접촉0/양수면적후보0·issue0·동일canonicalsource의다중split직접finding0이다. 같은단일split끼리1868쌍은OUT_OF_SCOPE, 경계레이어는BOUNDARY_NOT_USED다.

실제고정정책구현SHA42945e3d864a0e63dab4d3100355bcd3506eecf2ada8bc654d573521ea1fdff2, mapSHA557e5dd998dcb4c99eff2ec45c8a7bbac405bf11e245528b46f0b02275e0579b를 기록했다. Shapely2.1.2/GEOS3.13.1·pyproj3.7.2/PROJ9.5.1, networkfalse→false/restoredtrue다. 실제자료는Root만1회 검사했고 구현/독립담당은합성자료만사용했다. [별도 계획 대조](../../evidence/integration/recovery-source-split-overlap-plan-check-20261017.log)는 고정seed40사례/7가능분할집합에서4532후보쌍을 독립전수계산에대조해모두일치했다. 이별도실험/독립시험을정규unittest총수에추가하지않는다.

2227개의근사분리는 적격1111패치의누출/정확영상외곽·픽셀교차/현재source전체SHA·공간독립/학습승인을 증명하지 않는다. 원본/원장/lock/예약136314880B/분할/모델·기존5ML차단·terminal없는2건 보존·BLOCKED/모든실행·학습·정산·재개승인false/환불0 유지. 이전단위의경계참조없는80행은이번source진단의누락행이아니며경계연결을추측하지않았다.

[기존 readiness](../../backend/app/ml/readiness.py)는 source_group/scene_id 토큰을 통한지역연결과 적격scene bounds_wgs84 bbox교차를 통한지역연결을 별도로 적용하고, 그연결성분이서로다른고정split에걸리면차단한다. 이번physicalsource의corner근사진단과같은검사가아니다. 실제기존차단에서어느분기가발생했는지는이번단위에서재분류하지않았으므로 원인·해결을확정하지않는다. 다음 PLANNED 단위는 저장readiness차단근거(그룹/장면토큰과적격bbox)와이번diagnosticscope차이를읽기대조하는최소리포트다. 기존gate/policy/분할을수정하거나차단을해제하지않는다.

## Root 전체 회귀·보존

관련15PASS9.129초/독립15PASS10.368초, 별도40사례4532후보쌍 계획실험과독립시험은정규총수에중복합산하지않는다. [전체 회귀](../../evidence/integration/recovery-source-split-overlap-full-tests-20261017.log)는 **521건/520PASS/1SKIP/160.195초/종료0**이다. SKIP은기존OSsymlink권한/deterministic경계시험PASS. [보존 증거](../../evidence/integration/recovery-source-split-overlap-live-integrity-20261017.json): 보호132참조SHA·존재/기존계약17SHA불변·이전추적코드/데이터/계약변경0·원본source91 stat/prefix16와91부모목록변화0. 이는현재source전체SHA/원자snapshot/적격성·표본독립의증명이아니다. 원본/원장/lock/예약/분할/모델·기존차단상태를보존했다.

공개API/화면 상태 없는 내부CLI로 UI수정·기존49UI시험/build·실브라우저 재검증은 불필요하다. 향후화면연결시확정API·상태·오류·실제근거를web_ui에전달해야한다.

## 후속 저장 범위 대조

[문서57](57_recovery_readiness_comparison_validation.md)은 본물리corner보고서와저장readiness·원본manifest의고정SHA/정책/범위·완료상태를JSON만읽어대조한다. 현재raster/기하나적격성을재평가하지않고저장되지않은분기근거는UNKNOWN으로유지한다.
