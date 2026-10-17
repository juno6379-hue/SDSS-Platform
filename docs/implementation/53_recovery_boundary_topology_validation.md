# 고정 경계의 feature별 GEOS 위상 진단 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 작은 Polygon/MultiPolygon·위상 오류·엔진 오류 fixture를 포함한13개 시험을 통과했다. **VERIFIED_REAL(입력 계획):** 명시 경계는1파일/482,365B·6feature·17,940position이며1,304참조행과 레거시80행 UNKNOWN이다. 실제 경계 위상은 root가 별도1회 실행으로 확정한다. 설치 환경은 Shapely2.1.2/GEOS3.13.1이며 각 보고서가 실행 시 관측한 버전을 기록한다. **BLOCKED:** 공식ADM1·기관 승인·픽셀 포함·독립 기하/과학성능·정산/재개는 미검증이다.

[문서52](52_recovery_boundary_validation.md)의 구조 진단은 자기교차·위상을 검사하지 않았다. 이번 별도 companion은 제한을 통과한 동일 raw의 feature geometry에 대해서만 읽기 GEOS 진단을 추가한다. 원본 geometry·manifest·기존 코어/원장/lock/분할/모델을 변경하지 않고 자동 repair를 하지 않는다.

## 동일 raw·선행 조건·한도

[recovery_boundary_topology.py](../../backend/app/data/recovery_boundary_topology.py)의 `inspect_recovery_boundary_topology(data_root, expected_manifest_sha256, **limits)`는 기존 public inspector를 호출하지 않는다. 대신 기존 private bounded read/strictUTF8 depth/JSON/구조 helper를 변경 없이 재사용하고, 새 companion 안에서 같은 raw1회로 SHA·구조와 topology 입력을 처리한다. 구조 검사 후 경계를 다시 읽거나 과거 구조 보고서를 현재 원본의 승인으로 신뢰하지 않는다.

manifest caller SHA·source_window의 명시 path/SHA·canonical상충·경로·rowprovince·파일존재를 전수 계획한다. 경계 파일16개/총4MiB,feature128개/position100,000개/depth32를 그대로 적용한다. strict UTF8(no BOM/NUL), 문자열depthscan·중복키/비유한 수 거부·Polygon/MultiPolygon2D/ring/범위·province_id고유성과 실제 참조지역 연결을 재확인한다. manifest는 별도 최초/최종각64MiB 상한으로2회 읽고, boundary actual_boundary_bytes_read는 shared 경계1회분만 센다.

다음의 경우 feature shape/is_valid 진단을 시작하지 않는다.

- 명시참조 partial/null/형식·상충/파일누락 등 plan INVALID
- boundary SHA 불일치 또는 JSON/구조 issue
- 중복/누락 지역 식별자나 참조지역 연결 issue
- 경계/feature/vertex/depth 자원 한도 위반
- 알려진 경계가 없는 전부 UNKNOWN/미기재 상태

레거시80행은 참조를 추정하지 않고 UNKNOWN으로 두며, 명시한 known 경계의 feature만 진단할 수 있다. 런타임 import/버전 조회는 plan 실패에서도 수행될 수 있으므로 `topology_engine_attempt_count=0`은 **shape/위상 진단 시도0**이지 library import조차 없었다는 뜻이 아니다. 입력 byte/좌표 상한은 GEOS 작업량을 제한하지만 hard CPU·wall-clock time 또는 메모리 절대 상한을 보장하지 않는다.

## feature별 실제 진단

기존 [candidates.py](../../backend/app/data/candidates.py)도 사용하는 Shapely의 shape로 geometry를 구성하고 다음 읽기 속성만 확인한다.

1. `is_empty`: 빈 도형 여부
2. `is_valid`: GEOS의 feature 내부 위상 유효성
3. `explain_validity`: 유효/무효 이유
4. `area`: finite이고 양수인지

비어 있지 않고 GEOS valid이며 finite positive area일 때 VALID_TOPOLOGY다. 자기교차·shell 밖 hole·겹친 MultiPolygon 구성·퇴화 도형은 INVALID_TOPOLOGY로 기록한다. 하나의 MultiPolygon 안 구성 간 겹침은 is_valid 대상이지만 **서로 다른 Feature 사이의 겹침·접경·인접성은 검사하지 않는다**. cross_feature_overlap_checked=false다. 서로 완전히 겹치는 별도 feature 둘도 각각 valid일 수 있음을 합성시험으로 명시한다.

geometry 좌표가 lon/lat인 원래 자료 그대로 계산하므로 area는 **square_degrees_planar_diagnostic(평면 degree²)**다. m²/km²·공식 면적·측지학적 면적이 아니다. 면적을 만들기 위한 재투영도 하지 않는다.

buffer(0)·make_valid·repair·normalize·reproject나 geometry 재저장을 호출하지 않는다. 원본 ring이 구조상 닫혔는지도 먼저 검사하므로 닫히지 않은 ring을 엔진의 자동 보정으로 통과시키지 않는다. 결과는 진단이며 invalid geometry를 변경해 학습 대상으로 바꾸는 기능이 아니다.

## 엔진 버전·오류·상태

geometry_runtime은 available/shapely_version/geos_version을 기록한다. 2.x의 top-level GEOS version을 우선 읽고 구버전 호환 경로는 필요한 경우에만 시도한다. 버전 필드가 없거나 조회에 실패하면 UNKNOWN이며 설치 버전을 추측하지 않는다. import 실패는 엔진 미사용 가능 상태다.

shape/property/설명 함수 오류는 UNKNOWN_ENGINE_ERROR와 exception type을 기록한다. 엔진 부재는 NOT_CHECKED_ENGINE_UNAVAILABLE, 형식/지역 입력 문제는 NOT_CHECKED_INPUT_ISSUES, plan 실패는 NOT_STARTED_PLAN_REJECTED다. 검사되지 않은 상태를 valid로 표현하지 않는다. engine attempt count는 feature별 시도 수이며 성공 수가 아니다.

known feature 전부 valid여도 legacy 참조가 남으면 KNOWN_TOPOLOGY_VALID_PARTIAL/INCOMPLETE_REFERENCES다. 전부 참조 없음은 NO_RECORDED_REFERENCES다. topology feature checks와 files의 구조 status를 구분한다. 파일 구조가 STRUCTURE_MATCH여도 해당 geometry가 INVALID_TOPOLOGY일 수 있다.

항상 status=BLOCKED, exactly_once_applied=UNKNOWN, ready_for_training/training_executed/scientific_accuracy_validated/settlement/execution/automatic_resume=false, 환불0·네트워크0·원본쓰기0이다. official_adm1_verified/boundary_authorization_verified/pixel_inside_coverage_checked/geometric_independence_checked도 false다. 유효한 기하학적 도형은 실제 행정경계의 정확성·기관 권한·픽셀 포함률·독립 학습 표본·과학성능 승인과 별개다.

## 안전한 읽기·CLI

논리 경로→resolved target, 읽기 전후/종료 stat, manifest 최종 SHA를 재확인하고 원격/UNC/root 이탈·내용/alias 변경을 거부한다. lock이나 다중 파일 원자 snapshot은 제공하지 않는다. 기존 소비/원장/모델 상태를 갱신하지 않는다.

[inspect_recovery_boundary_topology.py](../../scripts/inspect_recovery_boundary_topology.py)는 CP949 stdout/stderr ASCII escape와 UTF8 새 evidence만 제공한다. 기존/evidence 밖/data root 아래 출력은 진단 전에 거부한다.

```powershell
python scripts/inspect_recovery_boundary_topology.py --data-root data `
  --expected-manifest-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --max-local-bytes 4194304 --max-boundary-files 16 `
  --max-features 128 --max-vertices 100000 --max-json-depth 32 `
  --output evidence/integration/recovery-boundary-topology-live-20261017.json

$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_boundary_topology.py -v
```

exit0은 BLOCKED 읽기 보고서 생성이며 invalid/unknown이 있을 수 있다. global pin·strictJSON·안전경로/한도/stale 실패는 exit1이다. geometry 엔진 오류는 UNKNOWN 진단으로 남겨 승인과 구별한다.

## 시험·UI·인계

[시험](../../tests/test_recovery_boundary_topology.py), [로그](../../evidence/integration/recovery-boundary-topology-tests-20261017.log): **13 PASS, 1.829초**. 정상 Polygon/hole/분리된MultiPolygon, bow-tie/외부hole/겹친MultiPolygon/퇴화, 서로다른Feature overlap미검사, same-raw1회/shared참조/legacy·대상0분리, plan/SHA/구조/지역/한도 engine0, runtime버전누락·엔진부재/오류·empty/nonfinite area, repair/reproject/public-inspector 재호출 금지·원본bytes/목록 보존, UTF16/32 escapedquote depth·strictJSON·pin/root이탈/stale/alias·CP949/출력보호를 검증했다. 구현/독립 담당은 합성자료만 검사하며 실제 경계는 root만 실행한다. 독립시험 수는 전체 회귀에 중복 합산하지 않는다.

공개 API/화면 상태 계약 없는 내부 CLI라 UI 수정·실행 중 frontend 반영·브라우저 검증은 필요하지 않다. 후속 화면 연결은 web_ui에 확정 API·상태·오류와 실제 근거를 인계해야 한다. root는 실제 위상 진단·보호대조·전체 회귀·원장/인계서를 담당하고 이해 에이전트에 완료 코드·시험·엔진 버전·부분 커버리지와 한계를 전달한다.

## Root 실제 위상 진단

**VERIFIED_REAL(고정된 명시 경계의 도형별 평면 GEOS 진단 한정):** Root CP949 CLI 종료0, [실제 JSON](../../evidence/integration/recovery-boundary-topology-live-final-20261017.json), [CLI 로그](../../evidence/integration/recovery-boundary-topology-cli-final-20261017.log). 명시경계1파일 계획=실제482365B<=4194304B·SHA일치, 6Feature/17940정점 구조와1304지역링크 정상/issue0. 실제 runtime은 Shapely2.1.2/GEOS3.13.1이며 6도형 모두 VALID_TOPOLOGY/is_empty=false/is_valid=true/finite_positive_area=true/Valid Geometry다.

legacy80행은 계속 UNKNOWN이므로 topology_validation=KNOWN_TOPOLOGY_VALID_PARTIAL/coverage=INCOMPLETE_REFERENCES다. 각도형의 유효성이 서로다른Feature간 겹침 부재나 공식ADM1/기관권한·픽셀경계포함/독립표본·과학성능을 증명하지 않는다. area_square_degrees_planar는 평면 진단값으로 공식면적·m²가 아니다. 자동repair/buffer/make_valid/reproject·원본쓰기는 없고 실제경계읽기는 Root만1회였다. 구현/독립담당은 작은 합성자료만 사용했다.

다음 PLANNED 작은 단위는 서로다른Feature 사이의 읽기 전용 교차 진단이다. 도형위상 유효성과 고정파일을 먼저 확인하고 총pair한도 아래 접촉/면적교차를 구분하며, 지도오류/승인상태나 원본geometry를 자동 변경하지 않는다. 교차진단도 공식경계·기관승인·픽셀포함·공간표본독립 검증과 별개다. 현재 cross_feature_overlap_checked=false를 유지한다.

## Root 전체 회귀·보존

관련13PASS1.829초/독립13PASS1.809초, 추가 합성적대실험과 독립시험은 전체총수에 중복합산하지 않는다. [전체 회귀](../../evidence/integration/recovery-boundary-topology-full-tests-20261017.log)는 **475건/474PASS/1SKIP/103.359초/종료0**이다. SKIP은 기존OSsymlink권한/deterministic경계시험PASS다. [보존 증거](../../evidence/integration/recovery-boundary-topology-live-integrity-20261017.json)는 보호132참조SHA·존재/기존계약14SHA불변·이전추적코드/데이터/계약변경0·경계1파일stat/prefix16/부모목록변화0을 기록한다. 원자snapshot 보장이 아니며 기존데이터/원장/lock/예약136314880B/분할/모델·5ML차단·terminal없는2건을 보존했다. BLOCKED/모든학습·실행·정산·재개승인false/환불0 유지.

공개API/화면 상태 계약을 바꾸지 않은 내부CLI이므로 UI코드 수정·기존49UI시험/build·실브라우저 재검증은 이번 범위에 필요하지 않다. 향후 UI에 노출할 때에는 확정 API/상태/오류·실제 증거를 web_ui에 전달해야 한다. 이번 실제 engine 버전은 Shapely2.1.2/GEOS3.13.1이며 preflight의 GEOS CAPI접미표기는 같은 설치 라이브러리의 상세 버전 표현이다.

## 후속 Feature 간 관계 진단

[문서54](54_recovery_boundary_relations_validation.md)는 본문에서 미검사인 같은파일 내 서로다른Feature쌍의 접촉/면적교차를 별도로 진단한다. 본문도형별위상과 구분하며, 후속결과도 공식경계/기관오류 판정·raster포함·표본독립 검증으로 확대하지 않는다.
