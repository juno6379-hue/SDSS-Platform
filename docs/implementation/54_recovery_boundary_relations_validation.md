# 같은 경계 파일의 Feature 간 교차 관계 진단 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 작은 경계·교차·엔진 오류 fixture를 포함한15개 시험을 통과했다. **VERIFIED_REAL(입력 계획):** 고정 경계1파일/6feature/17,940position에서는 무순서15쌍이 예상된다. 실제 진단은 root만1회 실행하여 별도 근거로 확정한다. **BLOCKED:** 공식ADM1·기관 승인·픽셀 내부 포함·독립 기하/과학성능·정산/재개는 미검증이다.

[문서53](53_recovery_boundary_topology_validation.md)의 feature별 위상 정상은 서로 다른 feature 사이의 겹침 없음과 다르다. 새 companion은 같은 파일 안의 유효 feature 무순서 쌍을 읽기 진단한다. 면적 교차를 발견해도 기관 경계 오류로 확정하거나 원본을 고치지 않는다. 다른 경계 파일 사이의 쌍은 OUT_OF_SCOPE다.

## 입력과 전수 pair 계획

[recovery_boundary_relations.py](../../backend/app/data/recovery_boundary_relations.py)의 `inspect_recovery_boundary_relations(data_root, expected_manifest_sha256, max_pairs=64, **limits)`가 구현이다. 기존 public structure/topology inspector를 재호출하지 않고 private bounded-read/strictUTF8/구조·runtime/위상 helper를 변경 없이 재사용한다. 같은 boundary raw1회로 SHA·strictJSON·구조·지역 식별 연결을 검사하고 그 도형을 geometry cache에 구성한다.

manifest pin, 명시 path/SHA 전수 계획, 경계4MiB/파일16/feature128/position100,000/depth32, manifest 최초/최종각64MiB와 경로/stat/변경 guard는 그대로다. legacy80행의 양키부재는 UNKNOWN이며 다른 주이름/경로로 추정하지 않는다.

모든 파일의 구조와 지역 연결이 통과한 뒤 같은 파일의 모든 `i<j`쌍 수를 합산한다. 기본 max_pairs64, 허용 정수1..8128(128 choose2)이며 caller가 실제15로 제한할 수 있다. boolean/float/0/상한초과를 거부한다. 전수 쌍 수가 예산보다 많으면 **pair 작업0**으로 실패하고 부분 결과를 전체 진단처럼 반환하지 않는다. 이 검사는 feature shape 구성보다도 먼저 수행한다.

pair 계획 후 모든 feature가 GEOS의 nonempty/valid/finite positive area 조건을 통과해야 쌍 연산을 시작한다. 도형 하나가 invalid/UNKNOWN이면 전체 pair0과 NOT_CHECKED_TOPOLOGY_ISSUES다. 선언 SHA/구조/지역 문제가 있으면 NOT_CHECKED_INPUT_ISSUES, 엔진 부재는 NOT_CHECKED_ENGINE_UNAVAILABLE다. 런타임 import/버전 조회와 실제 도형·pair 연산 시도는 구별한다.

feature당 shape는 한 번만 구성하고 유효 geometry를 cache한다. 각 쌍은 정확히 한 번 `_pair_relation`에 들어가며 intersection도 한 번 계산해 결과를 재사용한다. 같은 경계 파일을 여러 행이 참조해도 feature나 pair를 중복 생성하지 않는다. 입력/쌍 수 한도는 hard CPU·wall-clock 시간 보장이 아니다.

## 교차 결과와 정확한 양수 기준

교차 결과의 is_empty와 finite nonnegative area를 먼저 확인한다. 면적은 원래 lon/lat geometry의 **평면 degree² 진단값**이며 m²/km²·공식/측지 면적이 아니다.

| 상태 | 판단 | 해석 |
|---|---|---|
| DISJOINT | empty intersection·area0 | 교차 결과가 없음 |
| BOUNDARY_CONTACT | nonempty·area0·touches=true | 점/선 경계 접촉 |
| POSITIVE_AREA_OVERLAP | nonempty·area>0·touches=false | 양의 면적 교차 |
| UNKNOWN_* | 숫자/empty/touches 상충 또는 엔진 오류 | 분류되지 않음 |

intersects/disjoint는 교차 결과의 empty 여부에서 일관되게 기록한다. empty인데 area>0, area음수/NaN/Infinity, nonempty area0인데 touches=false, area>0인데 touches=true는 UNKNOWN이다. GEOS 예외도 UNKNOWN_ENGINE_ERROR와 exception type으로 남긴다.

양수 기준은 **정확히 area>0**이며 임의 epsilon으로 작은 교차를 숨기지 않는다. 1e-12 수준의 합성 교차도 POSITIVE_AREA_OVERLAP이다. 부동소수점/GEOS가 관측한 값이라는 한계는 그대로 남고 실제 현장 경계 정확도를 보증하지 않는다.

`.overlaps` 단독 판정은 containment/equality를 놓칠 수 있으므로 사용하지 않는다. positive area에서 equal/left_contains_right/right_contains_left도 기록한다. 동일 도형과 완전 포함도 면적 중첩으로 진단한다.

positive_area_overlap_pair_count와 area_overlap_findings는 **관계 진단 finding**이다. positive area만으로 기관 경계 오류 issue를 만들지 않으며 administrative_boundary_error_determined=false다. 같은/인접한 지역 식별자가 실제로 중첩되면 어떤 법적·사업적 의미인지 별도 권한 있는 검토가 필요하다.

## 범위·빈 검사·결과 상태

pair_scope=WITHIN_EACH_BOUNDARY_FILE_ONLY, cross_file_pairs_status=OUT_OF_SCOPE와 제외 쌍 수를 명시한다. 서로 다른 파일 각각 feature1개가 같은 도형이어도 이번 pair는0개다. 이를 전체 경계의 중첩 없음으로 해석하지 않는다.

전체 미기재는 NO_RECORDED_REFERENCES, 같은 파일 안에 후보 쌍이 없는 단일 feature/서로 다른 파일각1feature는 NO_PAIR_CANDIDATES다. 이때 pair_attempt_count0/cross_feature_pair_diagnostics_performed=false이고 관계 진단 성공처럼 표현하지 않는다. 계획이 평가되지 않았으면 planned_pair_count=null이며 제외 쌍 수는 pair_plan_evaluated와 함께 읽어야 한다.

legacy UNKNOWN이 남은 known pair 진단은 KNOWN_RELATIONS_DIAGNOSED_PARTIAL이다. 일반 RELATIONS_DIAGNOSED는 pair 검사 실행 완료이지 교차0이나 승인 통과가 아니다. UNKNOWN pair가 있으면 RELATION_ISSUES_FOUND다. pair_attempt_count는 시도 수이며 성공 수와 다르다. 위상 feature 결과와 pair 결과도 별도로 읽는다.

## 원본 보존과 한계

buffer/make_valid/repair/reproject/geometry 쓰기를 호출하지 않는다. 원본 파일·원장·lock·분할·모델을 수정하지 않고 source_files_written/network_requests/refund는0이다. 논리 경로 target·파일 stat·manifest 최종 SHA를 재확인하지만 다중 파일 원자 snapshot이나 lock은 제공하지 않는다.

항상 status=BLOCKED, exactly_once_applied=UNKNOWN, ready_for_training/training_executed/scientific_accuracy_validated/settlement/execution/automatic_resume=false다. official_adm1_verified/boundary_authorization_verified/pixel_inside_coverage_checked/geometric_independence_checked도 false다. pair 교차 진단은 장면/픽셀·학습 분할 독립성·행정 승인·모델 성능의 증거가 아니다.

## CLI·시험·인계

[inspect_recovery_boundary_relations.py](../../scripts/inspect_recovery_boundary_relations.py)는 CP949 stdout/stderr ASCII escape, UTF8 새 evidence만 제공한다. 기존/evidence 밖/data root 아래 출력은 진단 전에 거부한다.

```powershell
python scripts/inspect_recovery_boundary_relations.py --data-root data `
  --expected-manifest-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --max-pairs 15 --max-local-bytes 4194304 `
  --max-boundary-files 16 --max-features 128 --max-vertices 100000 --max-json-depth 32 `
  --output evidence/integration/recovery-boundary-relations-live-20261017.json

$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_boundary_relations.py -v
```

exit0은 BLOCKED 진단 보고서 생성이며 area finding/UNKNOWN이 있을 수 있다. 예산·pin·strictJSON·안전경로·변경 실패는 exit1이다.

[시험](../../tests/test_recovery_boundary_relations.py), [로그](../../evidence/integration/recovery-boundary-relations-tests-20261017.log): **15 PASS, 1.791초**.6feature15무순서쌍1회/geometry6cache/raw1회, 예산부족·잘못된한도 pair/shape0, 점/선접촉·disjoint·partialoverlap/containment/equality/미세positive, intersection1회·finding분리, invalidarea/상충/GEOS예외UNKNOWN, invalidtopology/plan/SHA/구조/지역 pair0, legacy/전부없음/단일feature/crossfile제외, 엔진부재, repair/public reread금지·원본bytes/목록불변, strict인코딩/한도/pin/경로/stale/alias·CP949/출력보호를 검증했다. 구현/독립 담당은 합성자료만 사용하고 실제 경계 진단은 root만1회 수행한다. 독립시험을 전체 회귀에 중복합산하지 않는다.

공개 API/화면 상태 계약 없는 내부 CLI라 UI 수정·실행 중 frontend 반영·브라우저 검증은 필요하지 않다. 후속 화면 연결은 web_ui에 확정 API·상태·오류와 실제 근거를 전달해야 한다. root는 실제 진단·보호대조·전체 회귀·원장/인계서를 담당하고 이해 에이전트에 완료 코드·시험·관계 finding·제외 범위와 한계를 전달한다.

## Root 실제 관계 진단

**VERIFIED_REAL(고정된 명시 경계의 같은파일 내 Feature쌍 진단 한정):** Root CP949 CLI 종료0, [실제 JSON](../../evidence/integration/recovery-boundary-relations-live-final-20261017.json), [CLI 로그](../../evidence/integration/recovery-boundary-relations-cli-final-20261017.log). caller max_pairs15 아래 계획15/시도15 전수진단: DISJOINT13/BOUNDARY_CONTACT2/POSITIVE_AREA_OVERLAP0, issue0다. 접촉쌍은 south_sulawesi–southeast_sulawesi와 banten–west_java이며 교차면적0이다. 면적중첩이 없다는 관측은 이 고정파일/엔진/범위에 한정한다.

명시경계1파일 계획=실제482365B<=4194304B·기대SHA일치, 6도형 위상과1304지역키연결 정상. 실제 Shapely2.1.2/GEOS3.13.1에서 검사했다. legacy80행 UNKNOWN이므로 pair_validation=KNOWN_RELATIONS_DIAGNOSED_PARTIAL/coverage=INCOMPLETE_REFERENCES이며 전체BLOCKED다. cross_file_pairs_status=OUT_OF_SCOPE(실제제외쌍0), 자동repair/reproject/원본쓰기없음. 실제경계검사는Root만1회, 구현/독립담당은합성자료만사용했다.

이 진단은 행정경계 오류 확정/공식ADM1/기관권한·raster픽셀포함·학습표본 공간독립/과학성능 승인과 별개다. area는평면degree² 진단이며 공식면적·m²가아니다. 기존5ML차단·terminal없는2건·예약136314880B와 원본/원장/lock/분할/모델·모든학습/실행/정산/재개승인false·환불0 유지.

다음 PLANNED 작은 단위는 경계 레이어끼리의 관계에서 실제 원본영상 source_window의 헤더 기반 footprint·주 연결 진단으로 범위를 확장하는 최소 계약이다. 실제소비 CRS/affine·좌표변환을 먼저 확인하고 고정manifest/명시 경계·source 영상 경로의 한도를 유지한다. 파생 footprint나 좌표변환 진단을 픽셀포함률·면적정확도/표본독립 증명으로 해석하지 않으며 원본geometry/래스터·분할을 수정하지 않는다. 현재 영상footprint 진단은 이 단위에서 미수행이다.

## Root 전체 회귀·보존

관련15PASS1.791초/독립15PASS1.764초이며 독립시험을 전체에 중복합산하지 않는다. [전체 회귀](../../evidence/integration/recovery-boundary-relations-full-tests-20261017.log)는 **490건/489PASS/1SKIP/107.418초/종료0**이다. SKIP은 기존OSsymlink권한/deterministic경계시험PASS다. [보존 증거](../../evidence/integration/recovery-boundary-relations-live-integrity-20261017.json)는 보호132참조SHA·존재/기존계약15SHA불변·이전추적코드/데이터/계약변경0·경계1파일stat/prefix16/부모목록변화0을 기록한다. 원자snapshot 보장이 아니며 기존데이터/원장/lock/예약136314880B/분할/모델·5ML차단·terminal없는2건 보존/학습·실행·정산·재개승인false/환불0/BLOCKED를 유지했다.

공개API/화면 상태 계약 없는 내부CLI이므로 UI수정·기존49UI시험/build·실브라우저 재검증은 이번 범위에 불필요하다. 향후 화면 연결시 확정 API·상태·오류·실제 근거를 web_ui에 전달해야 한다.

## 후속 원본영상 모서리 진단

[문서55](55_recovery_source_footprints_validation.md)는 본경계레이어관계와 별도로 source_window GTiff헤더의4pixel-edgecorner를 임시변환해 명시주와 관계를 진단한다. 모서리근사는정확footprint/픽셀비율/영상간표본독립이나 고정split승인을 증명하지 않는다.
