# 63. 고정 JSON 두 개의 token 회원·원본 후보 lineage

## 쉬운 설명과 상태

이 내부 도구는 caller가 **명시한 literal token**을 현재 readiness report의 전체 projected scene metadata와 원본 aggregate의 전체 raw rows에서 찾는다. 공유 namespace의 source_group/scene_id 역할, falsy group skip, 0patch scene을 구분한다. 연결 event의 내부 scene index를 원본 manifest row 번호로 단정하지 않고, 같은 metadata key의 **모든 후보 집합**을 보여준다.

구현 및 작은 fixture 검증은 `TESTED_SYNTHETIC`이다. 실제 pinned report/manifest 검사는 Root가 CLI 1회로 수행하고 별도 증거에 기록한다. 도구는 항상 BLOCKED/승인 false·환불0·exactly-once UNKNOWN이다. 후보1개도 실제 원본 row·파일·제품 진실의 인증이 아니다. 0patch 제거·차단 해소·과거 원인 복원·기하 독립을 시험하지 않는다.

## 범위와 입력

```python
inspect_readiness_connectivity_lineage(
    data_root, expected_report_sha256, expected_manifest_sha256, token,
    *, report_path=None, max_candidates=1000, max_members=2000,
)
```

- report 기본값: DATA root/first-group/readiness-connectivity-20261017.json, caller lower64hex SHA 필수, 최대16MiB.
- aggregate: DATA root/first-group-training-esri-v1/annual-window-report.json, caller lower64hex SHA 필수, 최대64MiB.
- token: 정확한 str, 최대4096 code point. caller가 지정한다. 자동 token 추론·prefix·공백 제거·정규화가 없다. 빈 literal 문자열도 query할 수 있다.
- raw rows 최대100000, projected scenes 최대2000. 두 입력의 존재·regular-file stat·byte cap을 **content read 전에 모두** 계획한다.

strict UTF8/no BOM/no raw NUL, decode 전 depth32, duplicate key/NaN/Infinity/overflow float 거부는 기존 bounded JSON helper를 재사용한다. 각 JSON은 최초와 최종 두 번 bounded read/SHA/stat 검사를 한다. 총 byte read 상한은2×(64+16)MiB이며 원본 raster 예산이 아니다. input logical path→resolved target을 기록해 마지막에 재대조한다. remote/root 이탈·pin mismatch·변경은 ValueError로 거부한다. CLI는 report 상대 경로를 cwd absolute로 바꾸되 미리 resolve하여 logical alias를 없애지 않는다.

원본 aggregate의 source_manifests113개를 따라가지 않는다. 후보의 image_path/SHA는 JSON의 literal 선언으로만 출력하며 image별 resolve/stat/hash/read를 수행하지 않는다. remote로 보이는 image_path도 **출력용 선언 문자열**일 뿐 접근하지 않는다. report·aggregate 두 JSON을 읽는 기능과 후보 파일의 실제성 검증을 구분한다.

## report 선행 계약

최소 report schema1, blocked/ready false/scientific false, six-province 기본 required_provinces 순서·기존4/1/1 mapping, group_splits, canonical single input_manifest path와 caller manifest SHA를 확인한다. capture는 all-appended-scenes scope/CAPTURED_COMPONENTS_MATCH/게이트 component 일치가 필요하다. scene_mapping/projected metadata 길이·typed scene count·유일하고 순서대로인 내부 index/eligible_position/province/patch count를 확인한다. patch 합계는 원래 split별 합계와 일치해야 하며 scene count로 바꾸지 않는다.

capture/witness의 ready/scientific/실행·정산·자동재개 false, IO/환불 int0, union_complete true, component map, 정확한 typed limits 일치를 확인한다. scene/pair 계획이 선언 한도 안인지, 전체 pair 수 n(n-1)/2, 저장 edge cap/min(total,limit), 종류별 count 합계·token≤2n/bbox≤nC2, truncation flag/coverage 정합과 token occurrence 수를 대조한다. scene 문자열·4좌표는 bounded literal/유한 geographic positive bbox여야 한다.

이 선행 검사는 report 최소 구조·계수·상태의 일관성이다. **witness event 전체·union을 재연산하지 않으며 실행코드 신원 또는 report 생성 환경을 인증하지 않는다.** 현재 회원 조회는 잘린 witness prefix가 아닌 전체 projected_scene_metadata에서 한다. stored_witness_truncated와 membership 조회의 완전성을 별도로 표시한다.

## raw 의미와 회원 조회

기존 readiness의 값을 그대로 선택한다.

```python
province = row.get('province', row.get('province_id', row.get('aoi')))
group = row.get('source_group', row.get('scene_id'))
identifier = row.get('scene_id')
```

키가 없을 때만 default가 적용된다. 명시 province=None은 aoi로 넘어가지 않고, 명시 source_group=None/0/''는 scene_id로 넘어가지 않는다. 지원 scalar str/int/finite float/bool/None의 truthiness/str 변환은 adapter와 같다. falsy group은 빈 문자열로 투영되어 **두 token 역할을 모두 skip**한다. scene_id는 항상 str이므로 None은 'None'이다.

각 matching row에 literal_roles와 active_token_roles를 나눈다. group이 falsy인 row는 query literal이 scene_id와 같아도 SKIPPED_FALSY_SOURCE_GROUP이며 active token 회원 수에 넣지 않는다. source_group과 scene_id의 cross-role 값이 같으면 같은 namespace에서 조회한다. 같은 행 두 역할이 query에 맞아도 row 회원1개·역할2개로 표시한다.

raw province는 bounded string을 지원하고, 미지원 token 타입·긴 문자열·province None 등의 row는 UNKNOWN_UNSUPPORTED_RAW_METADATA로 누계한다. 일부 raw row를 해석하지 못하면 raw_metadata_membership_complete=false/RAW_METADATA_INCOMPLETE다. 이 경우 query 부재나 전체 회원 완전성을 선언하지 않는다. raw rows를 실제 eligibility·year/files/dedup/quality로 재평가하거나 임의 필터링하지 않는다.

## 후보 집합과 계수

각 report literal member에 대해 `(province, normalized_source_group, normalized_scene_id)`가 같은 raw 후보를 모두 모은다. scene 순서·전체 row 개수가 우연히 같아도 내부 index를 raw row identity로 사용하지 않는다.

- NO_MATCH: 같은 metadata key의 원본 후보가 없음.
- UNIQUE_METADATA_CANDIDATE: 후보1개. metadata 후보라는 뜻이며 exact binding은 false.
- AMBIGUOUS_MATCH_SET: 후보가 여러 개. 같은 index나 첫 row로 선택하지 않는다.

후보 row에는 raw manifest_row_index, image_path_declared, declared_patch_image_sha256와 상태를 기록한다. 경로/hash가 없거나 타입·길이/hex 형식이 잘못되면 MISSING_OR_INVALID, 형식이 맞아도 DECLARED_NOT_FILE_VERIFIED다. 후보 파일의 실제 경로·SHA를 검증했다는 주장은 없다.

`candidate_link_count_total`은 전체 report literal 회원 각각의 후보 길이 합이다. `unique_candidate_raw_row_count`는 고유 metadata key별 원본 후보 행 수 합이다. 예를 들어 동일 key의 report16개/raw16개면256 후보 연결과16개 원본 행이다. `candidate_link_count_stored`는 실제 출력에 보존한 연결 수다. 각 count는 cap 적용 전에 계산한다.

max_candidates는1..10000이며 구체 후보 link 전체 저장 budget, raw 회원 목록·선언 row detail 각각의 최대 길이에 적용한다. max_members는1..2000으로 report 회원 저장 길이를 제한한다. 모든 회원/후보 count는 전체 scan 기준으로 남기고 output_truncated·candidate_links_truncated를 표시한다. 고유 key→raw index cache와 목록 길이로 총수를 계산하므로 2000×100000 후보를 모두 순회·복사하지 않는다. 합성 50×1000=50000 연결 case에서도2개만 구체화했다. 이 한도는 hard peak-memory/CPUtime 보장이 아니다.

## 주요 결과와 CLI

주요 필드는 lineage_status, report/raw literal/active/skipped 회원 수, raw_unknown_row_count, binding_status_counts_all_report_literal_members, report_members, raw_members, candidate_rows, 전체/저장 후보 계수, output_truncated다. TOKEN_NOT_FOUND/RAW_ONLY_MEMBERSHIP/REPORT_MEMBER_NO_RAW_MATCH/RAW_METADATA_INCOMPLETE/OBSERVED_MEMBERSHIP_OUTPUT_TRUNCATED/OBSERVED_METADATA_MEMBERSHIP를 구분한다. 보고서 status는 항상 BLOCKED이며 exact_row_binding_verified=false다.

```powershell
python scripts/inspect_readiness_connectivity_lineage.py --data-root data `
  --expected-report-sha256 95f7622ac72ef6a3d43aafc35a3607a4e9f39ed2912ac01280a07cc62c854e35 `
  --expected-manifest-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --token S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431 `
  --output evidence/integration/readiness-connectivity-lineage-live-20261017.json
```

CLI는 stdout에 ASCII 요약만 출력한다. --output은 project evidence 아래·DATA 밖의 명시적 새 파일로 UTF8 exclusive create한다. 기존 파일/final symlink·입력 alias·root 이탈·Windows ADS/예약device/끝점·공백을 선거부하고 logical output/parent를 재대조한다. 오류는 ASCII escaped stderr·종료1이다. 출력 도중 예외의 부분 새 파일은 자동 삭제하지 않는다. OS-level parent retarget과 open 사이의 완전한 원자 transaction을 보장하지 않는다. 저장 없이 호출하면 요약만 보이며 파일은 생성하지 않는다.

## 시험과 한계

관련 `tests/test_readiness_connectivity_lineage.py`: **16 PASS / 4.983초**, 로그 `evidence/integration/readiness-connectivity-lineage-related-20261017.log`. 합성 fixture만 사용했고 실제2JSON 검사는 Root 소유다.

검증 항목은 ambiguous/unique/no match·같은 index 승격 금지, 0patch 회원, missing-key vs explicit-null fallback, falsy 양 token skip, cross-role/numeric/None str, raw unknown와 부재 구별, 전수 count·output caps·큰 repeated-key cache, report typed counts/policy/limits/flags/부분 capture·ref path/SHA mismatch, strict JSON/depth/UTF16/크기선계획·변경/retarget, 선언 경로/hash 비검증, Windows output 별칭 거부·logical report alias 보존, CP949 ASCII summary/UTF8 새 파일·기존 입력 보존이다. assess/helper 호출 trap으로 진단 재실행이 없음을 확인했다.

독립/전체 회귀는 같은 시험을 중복 합산하지 않는다. 실제 코드 버전·source file truth·정확 source row identity·역사 cause·기하/픽셀 독립·0patch 삭제 반사실·학습/정산/자동재개 승인은 범위 밖이다. 기존24코어/CLI·원본/원장/lock/정책/분할/모델은 수정하지 않는다. 공개 API/UI 계약이 없는 내부 읽기 CLI이므로 UI 변경은 필요 없다. 후보를 더 좁히는 image path/hash metadata 단서의 향후 adapter 추가는 별도 설계 단위이며 이번에 구현하지 않는다.


## Root 실제 두 JSON 추적 결과

Root가 CP949 환경에서 CLI를 1회 실행해 종료0을 확인했다. [실제 출력](../../evidence/integration/readiness-connectivity-lineage-live-20261017.json)은 57548 bytes·SHA `cff1fb4b566cb8d9be4625df253411d3776ae1f0e485854798ac36673aac2a8e`, [CLI 로그](../../evidence/integration/readiness-connectivity-lineage-live-cli-20261017.log)는 ASCII 요약이다. 고정 현재 report95f762…와 aggregate manifestcdc374…의 JSON만 읽었다.

OBSERVED_METADATA_MEMBERSHIP에서 report/raw active token 회원은 각각28개(Banten16/West Java12)다. 고유 원본 후보 행28개에 대해 후보 연결400개를 모두 저장했고 truncation은 없었다. **28개 report 회원 전부 AMBIGUOUS_MATCH_SET이며 exact_row_binding_verified=false**다. Banten의 동일 키16회원 각각16원본후보, West Java12회원 각각12후보이므로16×16+12×12=400개의 후보 연결이다. raw metadata unknown은0이다. 내부 장면 순서·전체 개수의 일치만으로 하나의 원본 행을 확정하지 않았다.

실제 자료 메타데이터 추적의 검증이며 원본 영상·후보 파일/선언 hash의 진실성·과학적 독립/차단해소·역사원인 인증은 아니다. 실제 assess/연결 helper·header/pixels를 재실행하지 않았다. 현재 report에 per-scene 영상 경로/hash 식별 단서가 없다는 설명 공백을 확인했다. 다음에는 기존 assess가 이미 확인한 image_path/image_sha256를 추가 자료 IO 없이 선택 진단에 담을 최소 versioned 계약과 하위호환 trace를 검토·합성 검증한다. 현재 이 후속은 PLANNED이며 source identity나 원본 행 확정은 구현/실검증 완료로 표시하지 않는다.


## Root 전체 회귀·보존

[전체 회귀](../../evidence/integration/readiness-connectivity-lineage-full-tests-20261017.log)는 **624건/623 PASS/1 SKIP/176.415초/종료0**이다. 기존 Windows symlink 생성 권한 조건 1건을 건너뛰었고 deterministic 경계 시험은 통과했다. 관련16건/독립반복16건·별도8변조 실험을 전체 총수에 중복 합산하지 않는다.

[사전 기록](../../evidence/integration/readiness-connectivity-lineage-preflight-20261017.json)과 [최종 보존 증거](../../evidence/integration/readiness-connectivity-lineage-live-integrity-20261017.json)는 보호133참조(새 actual report 포함)·기존24진단/ML계약 SHA·manifest/current report pin 불변, 이전 추적 코드/데이터/계약 변경0, 기존 blocker5·패치628/233/250 보존을 기록한다. 새 코어/CLI/시험만 추가했으며 기존 source는 수정하지 않았다. 실제 영상·후보 path/stat/내용 SHA·assess를 재검사하지 않았고, 전체 workspace 또는 원자 snapshot 보장으로 확장하지 않는다. 원본/원장/lock/예약136314880B/분할/모델·terminal 없는2건·BLOCKED/모든 승인false/환불0 유지.

다음 PLANNED 단위는 선택적 adapter가 기존 assess 내부의 image_path/image_sha256를 추가 자료 IO 없이 진단에 전달하는 최소 versioned source-identity 계약과 lineage 하위호환을 설계·합성 검증하는 것이다. 현재 snapshot에는 이 단서가 없으므로 28개 모호함을 해소했다고 표시하지 않는다. 정책/분할/장면 삭제·gate판정 변경이나 실자료 assess 재실행은 이번 단위에 없었다. 내부 읽기 CLI로 새 API/UI 계약이 없어 화면 수정·기존49 UI시험/build 재실행·실제 브라우저 재검증 대상은 없다.


후속 전달 계약은 [64 선택적 원본 식별 단서](64_readiness_source_identity_contract.md)를 참조한다. 64는 adapter 기록만 추가하며 본 reader는 단서를 소비하지 않아 기존 실제 28장면의 모호성은 유지된다.
