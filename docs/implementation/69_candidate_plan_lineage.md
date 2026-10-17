# 69. 신규 Dataset 후보계획과 현재 선언 계보의 읽기 참조 패키지

상태: **TESTED_SYNTHETIC / PLAN_ONLY / BLOCKED**. 기존 split repair 계획과 최신 저장 보고서·출처 대조 결과를 하나의 참조로 연결한다. 후보 manifest 생성, 원본 제외·삭제·재배정, Registry 등록, 학습을 수행하지 않는다. 실제 다섯 JSON 실행·보존·전체 회귀는 Root의 별도 증거로 연결한다.

## 왜 필요한가

기존 계획은 고정 `test → val → train` 우선순위를 저장한 PLAN_ONLY 문서다. 최신 출처 대조 결과는 현재 내부 장면과 원본 manifest 후보 행의 선언 path/hash를 연결한다. 두 결과를 연결하면 어떤 선언 후보가 계획상 유지 또는 제외되는지 설명할 수 있다. 내부 장면 index와 원본 행 index가 같다는 이유로 연결하지 않는다. 선언 후보가 한 행이어도 원본 파일 진실성이나 정확한 원본 행 binding 인증은 false다.

현재 실제 자료에 대한 목표 설명은 기존 28회원·400넓은 후보 연결·28유일 선언 후보, 0패치 회원 3개, Banten 16행 제외 계획과 West Java 유지 계획 및 projected 적격 패치 `train628/val217/test250=1095`다. 이는 입력에 하드코딩한 성공조건이 아니며, Root가 고정 JSON 실행 후 확인할 항목이다. 이 문서의 합성 시험 수치와 실자료 수치를 구분한다.

## 새 구현과 기존 코어 보존

- `backend/app/ml/candidate_plan_lineage.py`: 순수 `build_candidate_plan_lineage`와 bounded `inspect_candidate_plan_lineage`.
- `scripts/inspect_candidate_plan_lineage.py`: 다섯 JSON SHA pin을 받는 읽기 CLI. stdout 또는 새 evidence만 작성한다.
- `tests/test_candidate_plan_lineage.py`: 작은 합성 다섯 JSON 시험.

기존 `split_planning.py`, `split_validation.py`, `write_plan`, readiness/adapter/helper, lineage 소비자, API/화면은 수정하지 않는다. 이미 있는 후보 생성/검증 기능을 중복 구현하거나 호출하지 않는다. 특히 이번 패키지는 **전체 planner 재계산이 아니다**. `full_planner_recomputation=NOT_PERFORMED`, `priority_scope=SAVED_POLICY_DECLARATION_NOT_RECOMPUTED`로 표시한다. 기존 계획의 선택된 메타데이터를 대조한다는 뜻이며, 전체 conflict graph나 planner 버전 digest의 재현성을 증명하지 않는다.

## 입력·계약·대조 범위

정확히 다섯 입력 이름을 사용한다.

| 이름 | 내용 | CLI 경계/파일당 한도 |
|---|---|---|
| plan | 저장된 split-repair-v1 PLAN_ONLY | evidence / 4MiB |
| source | 원본 aggregate manifest | DATA / 64MiB |
| old_readiness | 계획의 저장 readiness 참조 | DATA / 16MiB |
| new_report | 최신 source identity 보고서 | DATA / 16MiB |
| lineage | 최신 선언 path/hash 소비 결과 | evidence / 4MiB |

순수 함수 `build_candidate_plan_lineage(documents, references, *, data_root_literal, token)`는 파일·DB·네트워크를 읽지 않는다. 각 reference는 정확히 `{path,sha256}`이며 SHA는 **호출자 선언**이다. 순수 함수 자체의 pin 검증 상태는 `CALLER_DECLARED_REFERENCES_ONLY`다. 파일 바이트가 실제 SHA와 같은지는 CLI 읽기 wrapper만 검증한다. token은 비어 있지 않은 명시 원문 문자열 최대 4096자이며 자동 추정하지 않는다.

저장 계획에서 검사하는 필드는 schema/version/status/false 승인, source/oldreadiness 참조, 고정 4/1/1 province map과 우선순위, retained/excluded의 exact uint·중복 없는 정렬·전체 행 partition, quality_eligible 행 기반 before/projected_after 계수다. bool은 정수가 아니다. source는 최대 100,000행, year는 int 또는 ASCII 네자리 문자열 2015~2026 범위로 제한한다. 기존 row 원형을 바꾸거나 새 후보를 만들지 않는다.

old/new readiness의 고정 source 참조, 정책·blockers·split 패치 계수·클래스/클래스 패치 계수는 typed 동일해야 한다. 최신 capture는 BLOCKED/COMPONENTS_MATCH, 전체 appended scene scope, false 승인/비실행 및 IO/refund0이어야 한다. 최대 2,000개 내부 장면의 순서·mapping·eligible_patches 합계를 확인하고 0패치 장면도 그대로 둔다. `eligible_patches` 합과 장면 개수는 다르다.

source_identity v1은 기존 순수 validator로 전체 구조·상태·선언 계수를 확인한다. 이번 제한된 소비 범위는 모든 내부 장면에 완전한 선언 path/hash가 있으며, token 회원의 선언 후보가 유일하고 lineage 출력이 완전/잘리지 않은 경우다. legacy/부분/비교불가/모호한 선언을 임의로 좁히거나 승인하지 않고 거부한다.

원본 행을 `(province, normalized_source_group, normalized_scene_id)`로 인덱싱한다. 기존 readiness scalar str/falsy/fallback 의미와 공유 token namespace를 사용한다. 전체 broad 후보 연결 수는 인덱스 목록 길이 합으로 먼저 계산해 최대 2,000을 넘으면 구체화 전에 거부한다. 원본 100,000행×장면 2,000의 Cartesian 배열을 만들지 않는다. 각 회원의 literal/active 역할·0패치 수·broad 후보를 최신 lineage와 typed 비교한다. 기존 순수 refinement를 사용해 DATA 안의 lexical 경로와 **선언** SHA를 대조하고, 저장 refinement 전체를 재생성한 메타데이터와 비교한다. 이는 58 연결 witness 계산이나 assess 호출이 아니다.

유일 선언 후보의 raw manifest index가 저장 계획 retained/excluded 어느 집합에 있는지 연결한다. 이 결과는 `internal_scene_index`와 `raw_manifest_candidate_row_index`를 분리한다. 서로 다른 순서의 합성 원본 행에서도 선언 경로·해시로 연결되는 회귀를 포함한다.

## 클래스·누출·실행 한계

class_impact는 저장 계획의 `CONSERVATIVE_BOUNDS_ONLY`를 인용한다. old readiness의 상한 계수, 제외 eligible 수×patch_size²를 뺀 보수적 하한, 클래스 패치 상한·bare ratio 상한의 산술/타입 구조만 확인한다. 새 라벨 픽셀이나 정확한 후보 클래스 통계를 계산하지 않는다. 실제 val class7의 저장 209픽셀 상한과 낮은 보수 하한이 있다면 그 한계를 그대로 남긴다. 클래스 부족 해결·독립 과학 검증은 false다.

저장 연결 witness를 전수 재생하지 않으며 bbox/GEOS·현재 raster/픽셀·source-manifest 113개를 검사하지 않는다. 저장 계획의 공간 누출 재검증도 하지 않는다. 현재 선언 path/hash 유일 일치가 원본 인증, 역사적 생성원인, 0패치 제거의 반사실 효과, 정확 기하/분할 독립성, 5개 학습 차단 해소, 학습 승인이라는 뜻은 아니다.

출력은 schema1 `CANDIDATE_PLAN_DECLARED_LINEAGE_REFERENCE`, `status=PLAN_ONLY`, `readiness_status=BLOCKED`다. candidate 생성/행 제외·재배정/Registry/assess/helper/원본 source raster 읽기·hash/공간 재검증/정확 클래스/학습·과학·정산·재개 승인은 모두 false, refund와 쓰기·네트워크는 0, exactly_once는 UNKNOWN이다. `source_files_read_or_hashed=false`는 원본 raster 추가 IO가 없다는 뜻이다. CLI가 다섯 JSON 바이트를 읽고 SHA를 검증하는 동작과 구별한다.

## bounded 읽기와 CLI 사용

모든 입력의 scope·서로 다른 대상·일반 파일 stat와 파일 크기를 전수 확인한 다음 내용을 읽는다. UNC/URL/drive-relative/ADS·장치명·모호한 경로는 resolve/stat 전에 거부한다. 각 JSON은 strict UTF8/no BOM·NUL, 중복 키·NaN/Infinity 거부, 파싱 전 깊이32 한도를 적용한다. 다섯 입력을 각각 최초·최종 두 번 읽어 SHA/stat/논리 경로→resolved 대상의 안정성을 확인한다. 최대 총 JSON 읽기 예산은 208MiB(104MiB×2)다. 다중 파일의 원자 snapshot이나 적대적 OS 교체를 원자적으로 방어한다고 주장하지 않는다.

```powershell
python scripts/inspect_candidate_plan_lineage.py `
  --data-root data `
  --plan evidence/integration/ml-split-repair-plan-20261017.json --plan-sha256 <pin> `
  --source data/first-group-training-esri-v1/annual-window-report.json --source-sha256 <pin> `
  --old-readiness data/first-group/readiness-resume-20261017.json --old-readiness-sha256 <pin> `
  --new-report data/first-group/readiness-source-identity-20261017.json --new-report-sha256 <pin> `
  --lineage evidence/integration/readiness-source-identity-real-lineage-20261017.json --lineage-sha256 <pin> `
  --token <explicit-literal-token> `
  --output evidence/integration/<new-reference-package>.json
```

명시된 CLI 상대 경로는 cwd 기준 absolute로 만들고 논리 alias는 미리 resolve하지 않아 wrapper가 재검사할 수 있게 한다. `--output`이 없으면 전체 reference package를 ASCII JSON stdout으로 출력한다. 있으면 UTF-8 evidence 파일을 exclusive `x`로 새로 만들고 stdout은 요약한다. 기존 파일/깨진 symlink/입력 별칭/DATA 내부/경계 밖/Windows ADS·장치명·끝점·공백 출력을 거부한다. parent target을 재검사하지만 OS 원자적 parent-swap 방어는 아니다. 새 출력 쓰기 중 예외가 나면 부분 새 파일을 임의 삭제하지 않으며, 기존 입력·원장·lock 정리는 하지 않는다. stderr도 ASCII escape하여 CP949 경로 인코딩 예외를 피한다.

## Root 실제 고정 JSON 검증 및 보존 확인

2026-10-17 16:09 KST 기준 `VERIFIED_REAL_FIXED_JSON_METADATA_ONLY`. CP949 환경의 실제 CLI 1회가 종료 0으로 완료됐다. 입력 5개 바이트 SHA와 안정성을 재검사했으며, 출력은 `evidence/integration/candidate-plan-lineage-live-20261017.json`(19,766바이트, SHA256 `ee49f84c2b1e4a0aff72db321185b4d6d442f9878cca138dd7af116a0bf1760c`)이다.

저장된 `split-repair-v1-754e7a5a0569eb9b` 계획은 원본 1,384행 중 1,368행 유지·16행 제외 예정이다. 조회 토큰의 28개 선언 후보에는 계획상 제외 16개와 유지 12개가 연결되며, 0패치 3개·적격 패치 25개·기존 broad 연결 400개를 보존한다. 계획의 적격 패치는 1,095개(628/217/250)이고 실제 기존 적격 패치는 1,111개(628/233/250)로 변경되지 않았다. val bare 클래스 상한 209와 저장된 차단 5건이 유지된다.

전체 회귀는 671개 중 670 PASS·기존 환경 제약 1 SKIP, 246.659초, 종료 0이다. 독립 검토는 19 PASS/9.834초이다. 로그는 `candidate-plan-lineage-full-tests-20261017.log`, `candidate-plan-lineage-independent-20261017.log`이다. `candidate-plan-lineage-live-integrity-20261017.json`은 보호 참조 134개, 기존 계약 26개, 입력 5개 SHA 및 catalog 14행의 보존을 기록한다. 기존 추적 backend/scripts/data/tests/frontend 파일의 변경은 없다.

이는 고정 JSON의 선택 메타데이터 연결 검증이다. 전체 계획 재계산·전체 witness 재실행·정확 클래스 픽셀 재계산은 수행하지 않았다. 실제 후보 생성·원본 행 제외/재배정·Registry 기록·학습·승인도 수행하지 않았다. 새 API/UI 계약이 없어 기존 UI를 유지한다. 다음 단위는 기존 split plan writer/validator를 재사용하는 새 evidence 전용 후보 산출물의 안전한 생성·재검증 설계이며, 현재 후보 생성 상태는 `false`이다.

## 합성 시험·인계

관련 시험: **19 PASS / 9.466초 / 종료0**, `evidence/integration/candidate-plan-lineage-related-20261017.log`.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_candidate_plan_lineage -v
```

작은 다섯 JSON만 사용했다. 계획 partition·typed uint·참조/SHA·old/new gate 계수·보수 클래스·완전 identity·lineage false flags·잘림·후보 오염·모호/비교불가 path·행 순서 변경·0patch·후보 사전예산·scope/사전size·strictJSON·바이트 변경/논리retarget·CP949/new-only/Windows별칭·원본 바이트 보존·순수 코어 무IO/무planner/무assess/helper를 확인했다. 실제 데이터를 담당 에이전트가 중복 실행하지 않았다.

새 공개 API/UI 계약을 추가하지 않는 내부 PLAN_ONLY reference CLI이므로 이번 단위에서 화면 변경은 없다. Root가 실제 고정 다섯 JSON 1회 실행, 전체 회귀·134보호 참조/26기존 계약·catalog 보존 및 운영 문서/인계/이해자료 갱신을 맡는다. 이 단위 완료는 전체 프로젝트 완료가 아니다.
