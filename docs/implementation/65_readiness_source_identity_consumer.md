# 65. 원본 식별 선언 단서의 lineage 소비

## 쉬운 설명과 상태

64의 optional source_identity version1이 있는 report에서는 기존 province/group/scene_id 후보 집합을 **선언 path+SHA pair**로 더 좁힌다. 기존 broad 후보·회원·total counts를 바꾸지 않고 별도 source_identity_refinement 영역을 추가한다. source_identity가 아예 없는 과거 report는 기존 결과 key/값을 그대로 반환한다.

새 소비 동작은 `TESTED_SYNTHETIC`이다. 실제 자료 assess를 실행하거나 기존 실제 report를 수정하지 않았다. Root가 legacy report로 읽기 CLI와 전체 회귀를 별도 수행한다. complete pair로 후보가1개가 되어도 DECLARED_METADATA_ONLY이며 exact row binding·source authenticity·학습/과학 승인은 false다.

## 입력 version1 검증

기존63의 pinned2JSON/UTF8/깊이/byte cap/경로·report 선행 검사는 그대로다. optional source_identity가 있으면 다음을 추가 확인한다.

- identity_schema_version 정확한 int1. unknown version/bool 또는 extra/missing key는 ValueError.
- source_files_read_or_hashed/source_authenticity_verified/exact_original_row_binding_verified/ready_for_training/scientific_accuracy_validated는 정확한 bool false.
- scene_count는 기존 report count와 typed 동일. scene_identities 길이·scene_index/eligible_position 순서가 전체 projected metadata와 일치.
- complete/unknown/partial counts 및 coverage_status가 각 record의 status·field states와 일치.
- DECLARED_NOT_FILE_VERIFIED path는 bounded/nonempty/제어문자 없는 UTF8 str, SHA는 lower64hex. invalid/absent/null 상태는 값이 null이어야 한다. unknown field state 또는 identity_status 조합은 거부.
- DECLARED_METADATA_CAPTURED의 정확한 v1 구조를 확인한다. NOT_CAPTURED_ERROR의 알려진 최소 v1 구조는 error_type·count·null records/false flags를 확인하고 미포착으로 수용한다.

전체 field-state 계약은 문서64와 같다. 양 field ABSENT는 UNKNOWN_NOT_PROVIDED, 한쪽 ABSENT는 PARTIAL_DECLARATION, 양쪽 정상 선언은 DECLARED_PATH_AND_SHA256, 그 밖 명시 invalid는 INVALID_DECLARATION이다. discarded invalid 원본 값을 복구하거나 유효 값으로 추정하지 않는다.

일부/잘못된 optional 객체를 조용히 신뢰해 후보를 제거하지 않는다. malformed/unsupported version은 실패하며 known missing/partial/invalid/NOT_CAPTURED_ERROR는 원래 후보·불확실성을 보존한다. CLI는 기존 오류 처리대로 실패시 새 evidence 파일을 쓰지 않는다.

## 순수 lexical path+SHA 대조

새 consumer는 후보 경로에 resolve/stat/read/hash를 추가하지 않는다. 경로는 metadata literal만 사용한다. DATA root는 기존63이 JSON confinement을 위해 이미 얻은 값이다. 상대 assess 경로와 root 내부 absolute raw 경로를 **Pure path component**로 비교한다.

- Windows drive-root DATA: slash/backslash를 지원하고 root boundary/drive를 확인한 뒤 relative components의 casefold key를 사용한다. protocol은 WINDOWS_CASEFOLD_COMPONENTS.
- POSIX absolute DATA: slash components를 case-sensitive로 비교한다. Windows drive/backslash 경로는 비교하지 않는다. protocol은 POSIX_CASE_SENSITIVE_COMPONENTS.
- 두 경우 모두 URL/UNC/extended UNC, drive-relative/root-relative 모호 경로, DATA 밖 absolute 경로, '..'/'.' component, ADS colon, 예약device·끝점/공백, Win32 금지문자 < > " | ? *, trailing separator를 비교불가로 처리한다. 이 보수적인 portable subset 때문에 POSIX에서 실제로 허용되는 일부 문자도 비교하지 않는다.

이 key는 프로토콜상 lexical 비교 규칙이며 symlink/hardlink/실제 OS 대소문자 처리·inode 동일성·파일 존재를 검증하지 않는다. exact filesystem path identity는 false다. hash 역시 원본 JSON의 선언 값끼리 비교하며 파일 content hash를 새로 계산하지 않는다.

## 보수적인 후보 축소

기존 base key는 `(province, normalized_source_group, normalized_scene_id)`다. 기존 literal/active 역할, falsy 두 token skip, 0patch와 scene 순서는 그대로 유지한다.

complete valid identity pair이고 report path의 lexical 비교가 가능하며 해당 base의 **모든 raw 후보가 유효한 lexical path+declared image SHA를 가진 경우에만** pair로 좁힌다. raw 후보 중 하나라도 path/hash가 미기재·invalid·URL 등 비교불가면 그 base의 후보 집합 전체를 보존한다. 일부 raw row 자체가 미지원 metadata라 전체 membership이 불완전해도 원래 후보를 보존한다. 알 수 없는 후보를 불일치로 간주해 제거하지 않는다.

refinement_status는 다음을 구분한다.

| 상태 | 동작 |
|---|---|
| REFINED_DECLARED_METADATA_ONLY | complete pair로 lexical path/SHA 선언을 대조 |
| NOT_REFINED_IDENTITY_NOT_CAPTURED | identity 생성 실패·미포착, 원후보 보존 |
| NOT_REFINED_IDENTITY_INCOMPLETE | absent/partial/invalid 단서, 원후보 보존 |
| NOT_REFINED_UNSUPPORTED_LEXICAL_PATH | report path 비교불가, 원후보 보존 |
| NOT_REFINED_RAW_METADATA_INCOMPLETE | raw 회원 metadata에 unknown, 원후보 보존 |
| NOT_REFINED_RAW_DECLARATIONS_INCOMPLETE | base 후보 중 비교불가 선언 존재, 원후보 보존 |

대조한 결과가0/1/여러 개이면 NO_DECLARED_METADATA_MATCH / UNIQUE_DECLARED_METADATA_CANDIDATE / AMBIGUOUS_DECLARED_METADATA_MATCH_SET로 표시한다. 비교하지 못했으면 UNKNOWN_ORIGINAL_CANDIDATES_PRESERVED다. row index를 일치 증거로 사용하지 않는다. raw 동일 path/hash 중복 행도 유지하므로 두 선언이 같다고 raw 후보를 하나로 deduplicate하지 않는다.

## 별도 출력과 한도

기존 result의 report_members/candidate_rows와 broad candidate_link_count_total/unique_candidate_raw_row_count 등은 그대로다. optional 객체가 있을 때만 source_identity_refinement를 추가한다.

refinement에는 method/path protocol, 전체 report literal 회원의 status counts, refined candidate_link_count_total/unique_candidate_raw_row_count, 실제 저장 link count, members/candidate_rows, output_truncated와 false 승인 flags를 둔다. 각 member에 원래 count·refined count·선언 match 상태와 bounded raw row index 목록이 있다.

기존 max_members/max_candidates를 refinement에도 적용한다. total은 cap 전의 목록 길이로 계산하고 구체 link와 detail만 cap 안에서 저장한다. base별 raw index를 한 번 만들고 같은 path/hash key는 cache 조회한다. 원후보를 보존한 base는 전체 고유 row 수로, 완전히 대조한 base는 서로 다른 pair의 disjoint row list 길이 합으로 unique 수를 계산한다. 동일 pair를 여러 report 회원이 공유해도 unique raw 수를 중복 합산하지 않는다. raw 동일선언 중복 행 자체는 각각의 후보로 보존한다.

따라서 report50×raw1000=50000 선언후보 연결 case에서도 저장 cap2개만 구체화한다. 한도가 저장된 목록을 자르면 output_truncated가 true이며 전수 detail이 있는 것처럼 발표하지 않는다. hard CPU/memory 보증은 아니다.

## 하위호환과 시험

생산 변경은 readiness_connectivity_lineage.py 한 파일이다. CLI/assess/adapter/helper/schema 버전은 바꾸지 않았다. source_identity 부재에서는 새 refinement 영역도 없으며 기존 JSON 결과 key/값이 그대로다. Root의 실제 legacy 출력 byte SHA 비교는 별도 증거로 관리한다. 새 identity-bearing 실제 report를 만들기 위한 assess 실행은 수행하지 않았다.

관련 합성 검증은 다음과 같다.

- lineage 전체 **24 PASS / 8.893초**(기존16+새8).
- 허용된 adapter 하위호환시험 **1 PASS / 0.579초**. 새 refinement 영역만 분리한 뒤 기존 결과가 같고, 새 영역은 DECLARED_METADATA_ONLY/exactfalse임을 확인하도록 그 시험1개만 갱신.
- 독립 lineage **24 PASS / 8.200초**, adapter 호환1 PASS / 0.419초.

관련 로그는 `evidence/integration/readiness-source-identity-consumer-related-20261017.log`, 독립 로그는 `readiness-source-identity-consumer-independent-20261017.log`다. 관련24+호환1 실행을 전체 회귀25개 증분으로 합산하지 않는다. 새 unittest 증분은8개이며 기존 회귀·독립 반복과 구분한다.

새 시험은 complete pair 후보 축소와 기존 broad counts 불변, 동일선언 중복·unique계수, legacy absence/partial/invalid/미지원 경로 보존, raw 비교불가 전체집합 보존, version/flags/order/status/fieldstates 변조거부, NOT_CAPTURED_ERROR, Windows/POSIX lexical no resolve/stat/open 경계, declared mismatch0·대규모 repeated-key/cache·cap을 확인했다. 0patch 회원을 포함하고 singleton 인증 승격을 금지했다. 모든 실제 파일 경로는 없어도 되는 선언이며 실제 source IO를 하지 않는다.

## 제한·UI·후속

source path/hash 선언을 소비하는 내부 읽기 확장이라 공개 CLI/API/UI 인자나 화면 계약은 바뀌지 않는다. UI 변경은 필요 없다. 원본 보고서·원장·lock·예약·정책·분할·모델을 쓰지 않는다. Root가 보호 baseline/전체 회귀/운영 문서·이해자료를 관리한다.

singleton 선언 후보는 provenance 파일 진실·실제 content·정확 원본 row·과거 생성 원인·기하 독립·0patch 제거 후 차단 해소 또는 학습/정산/자동재개 승인이 아니다. path/hash가 없는 과거 보고서를 이번 코드로 소급 보강하지 않는다. 실제 새 선언-bearing report 관측 또는 추가적인 원본 인증은 별도로 제한한 실행·증거 범위다.


## Root 실제 legacy 하위호환 확인

고정 report SHA95f7622ac72ef6a3d43aafc35a3607a4e9f39ed2912ac01280a07cc62c854e35 및 manifest SHAcdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f, 명시 product token으로 CP949 환경 CLI를1회 실행해 종료0을 확인했다. 새 evidence output은57548B/SHA cff1fb4b566cb8d9be4625df253411d3776ae1f0e485854798ac36673aac2a8e이며63 결과와 바이트 동일하다. `evidence/integration/readiness-source-identity-consumer-live-legacy-validation-20261017.json`에 기록했다.

현재 실제 report에는 source_identity가 없으므로 refinement도 없다. 실제28회원·후보연결400·유일원본후보28·전원 AMBIGUOUS_MATCH_SET/exact false를 그대로 유지한다. 이 결과는 legacy 하위호환의 실자료 증거이며 새 identity 소비의 실자료 검증은 아니다. 두 고정JSON만 조회했으며 source 영상·다른 manifest·assess/helper는 실행/접근하지 않았다.

다음 단위는 기존 정책/입력 핀과 보호 baseline·timeout/RSS 감시를 설정하고 새 exclusive noexecute readiness 보고서를 만들어64/65의 선언 단서 전달·소비를 실제 관측하는 작업이다(PLANNED). 기존 보고서·원본·원장·lock·예약·모델·분할과 게이트를 보존하며 훈련/다운로드/배포 없이 수행한다. 관측 전 후보 축소·정확 원본 행 확정·학습 차단 해소를 주장하지 않는다.


## Root 전체 회귀·보존

전체 `scripts/test.ps1`은 **638건/637 PASS/1 SKIP/190.384초/종료0**이다. `evidence/integration/readiness-source-identity-consumer-full-tests-20261017.log`를 참조한다. 기존 Windows OS symlink권한 SKIP이며 deterministic 경계 시험은 PASS다. 관련/독립의24+호환1 재실행을 전체638건에 중복 합산하지 않는다.

`evidence/integration/readiness-source-identity-consumer-live-integrity-20261017.json`은 보호133참조·lineage외24계약SHA 불변, 의도한 lineage core·lineage시험·adapter호환시험 파일만 변경됨을 기록한다. producer adapter/readiness/CLI, 고정manifest/currentreportSHA·5차단·패치628/233/250은 그대로다. 원본·원장·lock·예약136314880B·분할·모델을 보존했고 학습/다운로드/배포를 실행하지 않았다. 이 보존 검사는 명시 baseline 범위이며 OS 전체 원자 snapshot 보장은 아니다.


후속 실자료 관측은 [66 식별 단서 전달·소비 실자료 검증](66_readiness_source_identity_real_validation.md)에 기록했다. 기존 보고서 보존 하에 새 보고서에서 선언 대조만 확인했으며 정확 원본 인증·학습 차단 해소는 아니다.
