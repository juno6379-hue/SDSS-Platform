# 경계 JSON 구조·지역 식별자·명시 출처 읽기 진단 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 작은 GeoJSON과 악성 깊이/인코딩 fixture를 포함한16개 시험을 통과했다. **VERIFIED_REAL(계획 메타데이터):** 고정 manifest의 명시1,304행은 고유 경계 JSON1개/482,365B를 참조하며 레거시80행은 boundary path/SHA 양키가 없다. 실제 경계 읽기는 root만 한 번 수행하여 별도 증거로 확정한다. **BLOCKED:** topology·self intersection·공식 ADM1·기관 승인·픽셀 내부 포함·독립 기하·정산/재개는 미검증이다.

[문서51](51_recovery_auxiliary_headers_validation.md)에서 OUT_OF_SCOPE였던 경계를 별도 companion으로 읽는다. 구조·명시 지역 식별 연결만 진단하며 원본 boundary/manifest·원장·lock·분할·모델이나 기존 코어를 수정하지 않는다. 구조 검사를 공식 행정경계 검증으로 표현하지 않는다.

## 실제 소비 코드와 제한한 구조 계약

[collect_training_grid.py](../../scripts/collect_training_grid.py)의 `build_batches`는 features[].properties.province_id를 key로 geometry를 사용한다. `materialize_patches`는 `transform_geom('EPSG:4326',...)`로 geometry를 변환한다. 이 소비 관계를 근거로 다음을 검사한다.

- JSON은 type=FeatureCollection과 비어 있지 않은 features 배열이어야 한다. 각 항목은 type=Feature, properties.province_id가 공백만이 아닌 문자열이어야 한다.
- province_id 중복을 마지막 값으로 묵인하지 않는다. 중복 feature는 DUPLICATE_PROVINCE_ID/AMBIGUOUS_PROVINCE다. 미기재·blank·boolean도 진단한다. shapeName/shapeISO/shapeType 같은 부가 필드를 공식성 근거로 채택하지 않는다.
- 지원하는 geometry는 Polygon/MultiPolygon의2D 좌표 구조다. polygon/ring은 비어 있지 않아야 하며 ring은4개 이상 position과 동일 첫/끝 position을 요구한다.
- position은 길이2의 숫자 배열이고 boolean을 거부한다. 모든 값은 finite이며 longitude[-180,180], latitude[-90,90] 범위여야 한다. 큰 정수의 float 변환 overflow도 안전하게 INVALID로 진단한다. 3D 좌표는 이번 지원 구조 밖이다.
- 명시 crs가 있으면 EXPLICIT_CRS_DECLARATION_NOT_SUPPORTED로 진단한다. 다른 CRS를 추정 변환하지 않는다. 실제 소비의 lon/lat 전제를 부분 구조로 확인하는 기능이며 일반 GeoJSON의 모든 schema·CRS를 지원한다고 주장하지 않는다.

모든 ring의 열거된 position은 짧은 invalid ring에서도 vertex budget에 포함한다. ring 방향·distinct vertex 수·면적·구멍 포함·self intersection·topological validity는 검사하지 않는다. 구조상 닫힌 bow-tie도 구조를 통과할 수 있음을 합성시험으로 명시했다.

## pin·전수 계획·UNKNOWN

[recovery_boundary.py](../../backend/app/data/recovery_boundary.py)의 `inspect_recovery_boundary(data_root, expected_manifest_sha256, **limits)`는 고정 aggregate 경로의 caller 소문자64자리 SHA를 요구한다. boundary 원본은 source_window.boundary_path/boundary_sha256의 명시값만 사용한다.

양키가 모두 없으면 UNKNOWN_REFERENCE_ABSENT이며 기존80행을 다른 행이나 기본 경로로 보완하지 않는다. 한키만 있음/null/빈path·잘못된SHA/같은canonical경로의상충SHA/명시 파일누락/잘못된rowprovince는 전체 계획 INVALID이고 boundary content 읽기0이다. 기존 helper는 변경 없이 confinement·stat·SHA형식 검사에 재사용한다.

동일 canonical 경계는 한 번 읽고 같은 raw의 SHA와 strict JSON을 검사한다. 선언 row.province는 해당 문서의 properties.province_id에 원형 문자열로 연결한다. MISSING_PROVINCE/AMBIGUOUS_PROVINCE/INVALID_FEATURE_STRUCTURE/UNKNOWN_BOUNDARY_INVALID를 분리하며, UNIQUE_PROVINCE_MATCH는 유일 식별자 연결일 뿐 경계의 공식 승인이나 그 픽셀의 주 내부 포함 증거가 아니다. UNIQUE_PROVINCE_MATCH 하나만으로 전체 FeatureCollection 구조가 유효하다고 결론내리지 않는다. 다른 feature나 root CRS 선언의 issue가 있을 수 있으므로 files의 구조 status와 전체 issues를 함께 읽어야 한다. feature 개수를 항상6개로 고정하거나 알려진 schema가 없는 부가 사실을 추측하지 않는다.

## 자원·인코딩·변경 한도

고정 상한과 기본값은 boundary 파일16개·총읽기4MiB·총feature128개·총position100,000개·JSON nesting32다. caller는 양의 정수로 줄일 수 있고 boolean/float/상한 초과/알 수 없는 옵션은 거부한다. source/ref/province 계획과 사전stat 합이 끝나기 전에 boundary content를 읽지 않는다. file/byte 상한은 읽기 전, feature/position 상한은 구조 열거 중 fail closed다.

manifest는 별도64MiB 상한과 depth32를 사용한다(현재 실제53,868,103B). manifest는 최초/종료 SHA 확인을 위해2회 읽고 각 읽기에64MiB 상한을 적용한다. 이2회분은 boundary의 공유파일1회/총4MiB 예산 및 actual_boundary_bytes_read와 별도다. 파일은 unbuffered 최대64KiB로 계획된 크기만 읽고 descriptor fstat·읽기 전후 stat을 대조한다. boundary 실제 반환바이트를 actual_boundary_bytes_read에 기록하며 shared file은1회분만 센다. SHA와 JSON을 위해 boundary를 두 번 읽지 않는다.

UTF-8(no BOM/no raw NUL)만 지원한다. 명시 strict decode한 문자열을 quote/backslash 상태를 고려하여 depth scan한 뒤 json.loads에 전달한다. UTF-16/32 자동 디코딩을 허용하지 않아 escaped quote와 NUL이 nesting 검사를 우회하지 못하게 한다. duplicate key·NaN/Infinity·overflow 비유한 수·malformed JSON도 거부한다. UTF8 escape 문자열 안의 중괄호/대괄호는 깊이로 잘못 세지 않는다.

모든 경로는 data root 안의 일반 로컬 파일만 허용하고 원격/UNC/VSI/root 이탈을 거부한다. 논리 경로 target과 파일 stat, manifest 최종 SHA를 재대조하여 내용/alias 변경·누락 파일 출현을 감지한다. 다중 파일 원자 snapshot이나 OS lock은 제공하지 않는다.

## 결과·한계

known 구조가 맞아도 legacy UNKNOWN이 있으면 KNOWN_STRUCTURE_MATCH_PARTIAL/INCOMPLETE_REFERENCES다. 모든참조 미기재로 검사 파일0개면 NO_RECORDED_REFERENCES/read0이며 구조 성공이라고 표현하지 않는다. plan INVALID와 실제 SHA 불일치·구조/지역 issue를 구분한다.

항상 status=BLOCKED, exactly_once_applied=UNKNOWN, ready_for_training/training_executed/scientific_accuracy_validated/settlement/execution/automatic_resume=false, 환불0·네트워크0·원본쓰기0이다. topology_validated/self_intersection_checked/official_adm1_verified/boundary_authorization_verified/pixel_inside_coverage_checked/geometric_independence_checked도 false다. shapeType=ADM1 또는 byteSHA 일치가 공식성·행정권한의 근거가 되지 않는다.

## CLI·시험·인계

[inspect_recovery_boundary.py](../../scripts/inspect_recovery_boundary.py)는 CP949 stdout/stderr ASCII escape와 UTF-8 새 evidence만 제공한다. 기존/evidence 밖/data root 아래 출력은 읽기 진단 전에 거부한다.

```powershell
python scripts/inspect_recovery_boundary.py --data-root data `
  --expected-manifest-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --max-local-bytes 4194304 --max-boundary-files 16 `
  --max-features 128 --max-vertices 100000 --max-json-depth 32 `
  --output evidence/integration/recovery-boundary-live-20261017.json

$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_boundary.py -v
```

exit0은 BLOCKED 진단 보고서이며 개별 SHA/구조/커버리지 문제가 있을 수 있다. pin/인코딩·strictJSON/안전경로/한도/stale 실패는 exit1이다. boundary JSON의 일부 syntax 오류는 INVALID 진단으로 반환할 수 있다.

[시험](../../tests/test_recovery_boundary.py), [로그](../../evidence/integration/recovery-boundary-tests-20261017.log): **16 PASS, 2.365초**. Polygon/MultiPolygon·지역연결·shared1회·legacy/빈검사, plan부분/null/형식/상충/누락/read0, byte/file/feature/vertex/depth 한도, string escape·UTF16/32 escapedquote 깊이공격(manifest/boundary), invalid short ring position누계, coordinate bool/nonfinite/hugeint/range/dimension, province누락/blank/중복/불일치, topology 미검사와명시CRS지원밖, pin/SHA/strictJSON, root이탈·변경/alias/missing출현, CP949/출력보호·원본bytes/목록불변을 검사했다.

독립검토에서 byte scanner와 json.loads(bytes)의 UTF16/32 자동 감지 차이로 깊이 우회가 가능함을 재현해 strictUTF8 문자열 scanner로 보완했다. invalid short ring의 누계 공백도 보완했다. 초기14/15개는 과거 이력이며 최종16개다. 독립시험을 전체 회귀에 중복 합산하지 않는다.

공개 API/화면 상태 계약 없는 내부 CLI라 UI 수정·실행 중 frontend 반영·브라우저 검증은 필요하지 않다. 후속 UI 노출은 web_ui에 확정 API·상태·오류와 실제 근거를 전달해야 한다. root는 실제 경계1회 읽기·보호대조·전체 회귀·원장/인계서와 이해 에이전트 갱신 인계를 담당한다.

## Root 실제 경계 검사

**VERIFIED_REAL(명시 경계의 바이트·구조·지역 식별 연결 한정):** Root CP949 CLI 종료0, [실제 JSON](../../evidence/integration/recovery-boundary-live-final-20261017.json), [CLI 로그](../../evidence/integration/recovery-boundary-cli-final-20261017.log). 명시 경계1파일 계획=실제482365B<=4194304B, SHA de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909 일치. 6개 Feature/17940개 정점의 구조가 정상이고 1304참조행 모두 UNIQUE_PROVINCE_MATCH, issue0이다. 하지만 legacy80행은 UNKNOWN이므로 KNOWN_STRUCTURE_MATCH_PARTIAL/INCOMPLETE_REFERENCES다. 미기재 행을 주 이름으로 추측해 연결하지 않았다.

실제 파일은 Root만1회 읽었고 구현/독립 담당은 합성자료만 사용했다. 구조·지역키 일치는 topology/자기교차/공식ADM1/기관권한·픽셀경계포함/기하독립·성능 승인을 의미하지 않는다. 원본/원장/lock/분할/모델·예약136314880B/5ML차단·terminal없는2건 보존, BLOCKED/학습·정산·실행·재개승인false/환불0 유지.

다음 PLANNED 단위는 이 구조 검사에서 제외한 경계 도형의 위상적 타당성 진단이다. 설치된 geometry 소비 라이브러리의 버전/검사 결과를 기록하고, invalid geometry라도 자동 repair/buffer/reproject로 바꾸지 않는다. 위상 정상도 공식 경계·권한/픽셀포함·독립 표본 승인이 아니다. 현재 단위에서 topology는 검사하지 않았다.

## Root 회귀·보존 결과

관련16PASS2.365초/독립16PASS2.304초, 독립시험은 전체에 중복 합산하지 않는다. [전체 회귀](../../evidence/integration/recovery-boundary-full-tests-20261017.log)는 **462건/461PASS/1SKIP/107.796초/종료0**이다. SKIP은 기존OSsymlink생성권한/deterministic경계시험PASS다. [보존 증거](../../evidence/integration/recovery-boundary-live-integrity-20261017.json)는 보호132참조SHA·존재/기존계약13SHA불변·이전추적코드/데이터/계약변경0·경계1파일stat/prefix16와부모목록변화0을 기록한다. 원자snapshot 보장이 아니며 원장/lock/예약/분할/모델을 수정하지 않았다.

독립검토에서 UTF16/32 escaped quote로 byte 깊이 검사를 우회하는 합성 사례를 재현한 뒤 strictUTF8 문자scan/BOM·NUL거부/manifest·boundary양쪽 회귀를 추가했다. 짧은 invalid ring의 좌표도 정점 예산에 합산하도록 보완했다. 최초15시험은 보완 전 이력이며 최종 관련/독립16을 기준으로 보고한다. 공식자료의 내용은 보완하지 않았다. 공개API/UI 변화 없는 내부 CLI이므로 이번 UI코드·기존49UI시험/build·실브라우저 재검증은 불필요하다.

## 후속 도형별 위상 진단

[문서53](53_recovery_boundary_topology_validation.md)은 본문에서 미검사인 도형별 GEOS 위상을 별도 진단한다. 구조 검사 결과와 구분하며, 자동 보정·공식경계/기관승인·Feature간교차/픽셀포함·표본독립 검증으로 확대하지 않는다.
