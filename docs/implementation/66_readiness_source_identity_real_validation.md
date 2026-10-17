# 66. 실제 source identity 전달·소비 검증

## 확인한 결과

**VERIFIED_REAL — 현재 보고서의 선언 metadata와 읽기 소비 결과에 한정.** Root가 실제 assess CLI1회와 consumer CLI1회를 실행했다. 구현·문서 담당은 이 실행을 반복하지 않고 새 JSON만 검증했다. 실제 gate는 여전히 blocked/ready=false, 기존5blocker·1111 patches가 유지된다.

새 source_identity는1384 scene 모두에 이미 계산된 image path/SHA 선언을 전달했다. 기존 verified_files의 input_image 기록과1384개 pair가 일치한다. 토큰 query의 기존 broad 후보는28회원/400연결/원본후보28행으로 유지되며, 별도 refinement는28연결/28고유 raw 후보/28개 UNIQUE_DECLARED_METADATA_CANDIDATE를 기록했다. **유일한 선언 후보이며 exact row binding·source authenticity는 false다.**

## 실행과 고정 입력

- 이전62 report: `data/first-group/readiness-connectivity-20261017.json`, SHA `95f7622ac72ef6a3d43aafc35a3607a4e9f39ed2912ac01280a07cc62c854e35`,11132483B. source_identity가 없는 과거 보고서 그대로다.
- 고정 aggregate: `data/first-group-training-esri-v1/annual-window-report.json`, SHA `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`.
- 같은 policy: `evidence/integration/readiness-connectivity-real-policy-20261017.json`. 기존 saved policy의 내용 그대로이며 gate·분할을 바꾸지 않았다.
- 새66 report: `data/first-group/readiness-source-identity-20261017.json`, **11858020B**, SHA `6bc86c9883716565946cff1700780db98aea005bca2e8da2c225520501dda642`.
- 새 consumer 결과: `evidence/integration/readiness-source-identity-real-lineage-20261017.json`, **88245B**, SHA `4f6f62356f568d5d8de482a66f5cd492079b3230de98b01021656fb1b65091bb`.

Root의 assess 실행 기록은 `evidence/integration/readiness-source-identity-real-execution-20261017.json`이다. 새 --readiness-output·기존 --plan·--connectivity-diagnostics를 사용했고 noexecute/noresume/학습·다운로드 요청0이다. 종료0·85.641초, 관측 process-tree RSS 최대214609920B/165samples, 강제중지 없음. timeout600초/2GiB 표본 감시이며 hard memory cap은 아니다. PROJ_NETWORK OFF/GDAL_PAM NO/READDIR EMPTY_DIR/VRT_PYTHON NO 환경을 기록했다.

consumer는 고정2JSON과 명시 token `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`을 사용해 Root가1회 실행했고 종료0이다. stdout 근거는 `readiness-source-identity-real-lineage-cli-20261017.log`다. 기존 실제 보고서를 덮어쓰거나 source_identity를 소급 추가하지 않았다.

## 이전62와의 typed 동등성

old62/new66 전체 report를 typed JSON으로 비교했다. 허용한 차이는 **assessed_at와 connectivity_diagnostics.source_identity만**이다. 이를 제외하면 모든 key·값이 동일하다.

- verified_files4335개, policy·coverage·class/reference 통계·input signature·manifest refs 모두 동일.
- 기존5blocker의 순서·내용·scene 그대로. SHARED_SOURCE_CROSSES_FIXED_SPLIT(west_java), train/val/test REFERENCE_CLASS_IMBALANCE와 val/class7 CLASS_COVERAGE209pixels 유지.
- prepared_payload는 계속 null이며 ready_for_training/scientific_accuracy_validated는 false.
- capture/components/witness·토큰/bbox 계수·truncation·0patch 포함 순서도 동일.

| 고정 split | appended scenes | eligible patches | 0patch scenes |
|---|---:|---:|---:|
| train |848|628|220|
| val |272|233|39|
| test |264|250|14|
| 합계 |1384|1111|273|

1111은 patch 합계이며 scene1384와 구별한다. source_identity 전달은0patch scene도 생략하지 않는다. 과거 원인 복원·장면 삭제 후 차단 해소 반사실은 실행하지 않았다.

## 실제 identity 전달 결과

identity_schema_version1/DECLARED_METADATA_CAPTURED이며 coverage는 COMPLETE_DECLARED_METADATA다. complete1384/unknown0/partial-invalid0, records 순서와 scene_index/eligible_position이0..1383으로 전체 scene 목록과 일치한다.

각 path/hash 상태는 DECLARED_NOT_FILE_VERIFIED, scene identity_status는 DECLARED_PATH_AND_SHA256다. identity의 relative path literal과 hash가 **같은 새 report에 이미 기록된** verified_files의 input_image path/SHA와1384개 모두 일치한다. input image metadata path와 hash는 각각1384개 유일값이다. 이 검증은 JSON 기록 사이의 관계 확인이며 문서 담당이 파일을 다시 열거나 hash한 것이 아니다.

path_normalized_or_resolved/source_files_read_or_hashed/source_authenticity_verified/exact_original_row_binding_verified/ready/scientific는 모두 false다. 실제 Root assess는 기존 파일 hash·픽셀 QA를 수행했지만 optional identity 전달 자체는 추가 source IO가 없다는 범위다. 전체 CLI가 원본 입력을 전혀 읽지 않았다는 주장으로 바꾸지 않는다.

## 실제 consumer 결과

이전65 legacy consumer `readiness-source-identity-consumer-live-legacy-20261017.json`(SHA `cff1fb4b566cb8d9be4625df253411d3776ae1f0e485854798ac36673aac2a8e`)과 새 consumer의 broad 결과를 비교했다. 새 입력 report path/SHA와 별도 source_identity_refinement 영역을 제외하면 typed 전체 결과가 동일하다.

| 관측 영역 | 회원/연결/원본 후보 |
|---|---|
| 기존 token 회원 |28 active 회원 |
| 기존 broad metadata 후보 |400 연결·28 고유 raw 행,28회원 모두 AMBIGUOUS_MATCH_SET |
| 신규 identity refinement |28 연결·28 고유 raw 행·28 UNIQUE_DECLARED_METADATA_CANDIDATE |
| 저장 생략 |broad/refinement 모두 없음 |

refinement는 WINDOWS_CASEFOLD_COMPONENTS 프로토콜로 DATA-root-relative assess path와 raw absolute path를 순수 lexical 비교하고 SHA 선언을 대조했다. 문서 담당은 새 report의 identity와 consumer가 출력한 raw candidate detail을 PureWindowsPath 문자열 산술로 대조해28개 pair 일치를 확인했다. production helper/consumer를 다시 호출하거나 path resolve/stat/read/hash를 하지 않았다.

28개 query 회원 중0patch scene3개도 refinement 결과에 남아 있다. 이 사실은 현재 metadata 전달·소비에서0patch가 사라지지 않았다는 관측이다. 해당 scene 또는 전체0patch를 삭제한 결과는 시험하지 않았다.

새 refinement의 status는 DECLARED_METADATA_ONLY, exact_row_binding_verified/filesystem_path_identity_verified/original_file_or_product_authenticity_verified/ready/scientific는 false다. 서로 다른 단서로 broad 모호성을 줄인 것이며 실제 원본파일·제품·행의 진실을 인증하거나 내부 scene index를 원본 row index로 승격하지 않는다.

## 검증 산출물·시험 구분

`evidence/integration/readiness-source-identity-real-validation-20261017.json`의 **16개 JSON metadata 검증 항목 PASS**다. 새 unittest16개가 아니다. 새 report/consumer의 고정 SHA·strict bounded JSON을 확인하고, 허용 차이 외 전체 typed 동등성,4335파일 metadata·policy·5blocker·counts, identity exact schema/order/flags/완전선언·verified_files 관계, 기존 broad 영역 보존, refined singleton·원본 선언 detail pair·0patch 보존, 실행 no-training 기록을 확인했다. 최초/최종 JSON SHA/stat 안정성도 대조했다.

문서 담당은 old/new report·legacy/new consumer·Root execution JSON만 읽었다. assess/connectivity/consumer helper 재실행, source raster/header/pixel/content hash 추가 접근은0이다. 생산코드 수정도 없다. 이번 단위 전체 회귀를 새로 실행하지 않았으며 직전65 unittest/full-regression 증거를 이번 실행 건수로 합산하지 않는다.

Root 보존 증거 `evidence/integration/readiness-source-identity-real-live-integrity-20261017.json`은133개 보호 참조/25개 코드 계약·이전 tracked code/data/tests 변경0·policy/manifest/두 이전 report 보존을 기록한다. verified_files4335·기존5blocker·628/233/250 재현도 확인했다. 이번에 새 full 회귀를 실행하지 않았으며65의638건 회귀는 이전 이력이다. 독립 검토는 별도 운영 근거로 관리한다. 현재 metadata 단서의 실제 전달·소비를 확인했지만 과거 report 생성 runtime·과거 분기 원인 인증, 정확 기하 독립·누출 해결·정확도·학습/정산/자동재개 승인을 뜻하지 않는다.

## UI와 남은 범위

내부 optional metadata와 읽기 CLI의 실제 검증이며 새 공개 API/UI 상태·버튼은 추가하지 않았다. UI 변경은 필요 없다. 원본 report/원장/lock/예약/정책/분할/모델을 쓰지 않는다. Root가 보존/snapshot/운영 문서와 이해자료를 갱신한다.

5개 blocker가 그대로라는 점을 발표에 함께 설명해야 한다. source identity로 후보집합이 유일해졌다는 관측은 학습 가능 또는 차단 해제를 뜻하지 않는다. 추가 파일 진실 검증·독립 데이터 정책·과학적 누출 판단 또는 실행 승인은 후속의 별도 근거 범위다.

다음 **PLANNED** 단위는 실자료 진단의 최소 읽기 API projection과 명시 조회 UI 계약·노출 최소화 검토다. 이번66에서 API/화면을 구현하거나 자동 조회·실행을 연결하지 않았다. 현재 readonly metadata/false 승인 범위를 유지하는 별도 설계·시험·UI 담당 인계가 필요하다.
