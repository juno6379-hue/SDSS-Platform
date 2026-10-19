# 269 — 기존 52개 후보를 제외하는 다음 로컬 위치 계획

상태: **VERIFIED_REAL_LOCAL_PLAN_COMPLETED_UNAPPROVED**. Root의 별도271 검증과 새 GO 뒤 로컬182 CLI 단1회를 완료했다. 수집 승인과 학습 승인은 false다. 아래 준비 계약과 실제 결과를 구분한다. 269 번호를 문서/evidence에서 검색해 충돌이 없음을 확인했다. main 제품·모델·운영 원장·게시 pointer·profile은 변경하지 않았다.

## 무엇을 준비하는가

이미 제안했던 위치를 같은 순서로 보존하고 제외한 뒤 남동 술라웨시2024 → 고론탈로2025 → 고론탈로2022 순서로 최대4개의 새 위치만 제안하는 **로컬 계획**이다. 계획에 후보가 생겨도 실제 사진 품질이나 공유 support/scene/window/pending 전체 검사가 통과했다는 뜻은 아니다. 원격 다운로드와 collector는 이 runner가 호출하지 않는다.

257의 `prior-merged.json` 48개와 `proposal.json` 4개를 원배열 그대로 이어 붙여52개를 제외한다. 기존 파일은 변경하지 않는다.

| 입력 | 파일 SHA | 원배열 SHA |
|---|---|---|
| `data/centers257-fresh-20261018/prior-merged.json` 48개 | `98f06c1297fb1a2cef9fbef6a3433a95cdb9fd3cbf151328f25ee6f7681299c0` | `a2cb0013be5d004bfc9b284ce53045e4cf8e434560ab80c8b0b1a0c25bde6b69` |
| 같은 디렉터리 `proposal.json` 4개 | `70f69e14f468f6ca3ce30c294b80c80a6ee2fd9f375e4925654ed9bb47892847` | `f136483cbda0683c3613f35c52a2190a7a724dc72fd5724ee2d9b6381ecca792` |

이어 붙인52개 원배열 SHA는 `661a233ee741aa2ef4046fd0db492db19730aa81ead9378e9f6cb81eb6dfc19b`다. `spatial_window_id`의 유일성,48/4개 구간별 원순서, 이전 파일 SHA를 실행 전후 재확인한다. 후보 배열 SHA는 key 정렬/compact JSON의 canonical 값이며 원파일 SHA와 구분한다.

## 현재 입력과 코드 고정

준비 JSON은 `evidence/integration/centers269-prepared-20261018.json`, 새 runner는 `evidence/integration/centers269-prepare-20261018.py`다. 245 runner를 그대로 재실행하지 않는다. 그 원판 SHA `15da0d95c6fdc898efcd17cc5b1eb64f2d757a85cdc8a9f12038da0c37a8a655`를 확인한 뒤 bounded reader·snapshot·전후 핀·단일 claim 구현을 새269 독립 파일에 복사하고52개/새 경로/현재 code pins/새 검증 계약으로 바꿨다. 245/257 판본은 보존한다.

Root가 전달한 운영 source는 `9473861797b729b6b6eb60607a7edfb67921fa2b259bc2b0ffa8b2af08fc1353`/66,827,338B, 원장은 `a92506b7b5b2ca5f668a21f9b111b32b3d2080a707ba9646bbf063c53dfe5aea`다. **준비 중 이 운영 파일들을 읽지 않았다.** 실제 GO 뒤에만 전후 SHA/identity를 검산한다. 새 `data/centers269-fresh-20261018/source.json`을 한 번 생성하고 이후 요청 준비가 이 사본을 재사용할 수 있게 남긴다. 전체 data/model/원장 복사는 하지 않는다.

행정경계는 `data/first-group-boundaries/selected-six.geojson` SHA `de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909`, base config는 `configs/first-group.collection.json` SHA `8b0c1b2aad13a3344200998ec62a18853c5308adf4ec57b1af835333845fd7e3`다. 182 CLI는 SHA `65fc9419680edbdc4daeb16a321eb8ca82d07df07f961d696b6a6a24a9742697`이며 `--manifest-profile bounded128m-3000-v1`을 명시한다. profile descriptor SHA는 `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`다. 자동 cap 확장이나 기본 상수 변경은 없다.

현재265 적용 후 code pins에는 아래 운영 선별 관련 판본도 포함한다. 준비 JSON에 전체 파일별 SHA를 고정했다.

- guard: `4052759b683f6f4f545a629466f2d4145e3ad9cc2ad8e6cdf5b1e3c0004a5dd2`
- coordinator: `9ae5ba986d3d48e89cfb269d8a242ffd6189d281649d98a11614c03e5ab3c9ab`
- collect_samples: `9ce6cf2a520edb14d8c67260e79fc5f605f11eab03d9d6773117e0fd193eb165`

코드를 고정했다고 로컬 계획이 v2 수집용 strict request를 대신하지 않는다. Root270이 새 선별 정책과 current config/request SHA를 결속하는 별도 수집 준비를 소유한다. 현재 기본 config는 이 위치 계획의 기준일 뿐 기존 승인서 재사용 근거가 아니다.

## 검증 대기와 GO 스키마

Root268의 첫 공유 프로젝트 검증은 **95통과+1실패**이며 실패 로그/결과를 보존한다. Root가 보고한 원인은 subprocess에 PYTHONPATH가 전달되지 않은 실행 설정 공백이다. 이 문서는 그 판을 PASS로 바꾸지 않는다. Root는 제품 코드를 그대로 두고 별도271 runner에서 명시 PYTHONPATH로 같은96개를 검증할 예정이다. 269는 그 **별도 최종 통과 근거**와 새 GO가 있어야 실행한다.

GO의 정확 키는 아래9개다. `main_validation_ref`는 Root가 확인한 별도271 최종 PASS 결과의 경로/SHA여야 하며, Root의 `main_validation_passed=true` 명시 확인과 결속한다. runner는 evidence 경로/SHA 전후를 검산한다. 단순268 실패 결과를 PASS라고 재해석하지 않는다.

```json
{
  "schema_version": 1,
  "kind": "ROOT_AUTHORIZED_LOCAL_CENTERS269_PLAN",
  "local_plan_approved": true,
  "maximum_cli_invocations": 1,
  "source_sha256": "9473861797b729b6b6eb60607a7edfb67921fa2b259bc2b0ffa8b2af08fc1353",
  "ledger_sha256": "a92506b7b5b2ca5f668a21f9b111b32b3d2080a707ba9646bbf063c53dfe5aea",
  "main_validation_ref": {"path": "<Root271 final PASS evidence>", "sha256": "<sha256>"},
  "runner_sha256": "<frozen269 runner SHA>",
  "main_validation_passed": true
}
```

실행 형태는 `python -X utf8 evidence/integration/centers269-prepare-20261018.py --run-local-plan --approval <Root269 GO.json>`다. 기본 실행은 PLANNED 출력만 하며 운영 입력을 읽지 않는다. GO가 있어도 source/ledger·code·prior·boundary/config 변경 또는 execution lock이 있으면 차단한다. 새 work/claim/log/preflight/result 경로가 이미 있으면 자동 재시도하지 않는다. 부분 산출물을 삭제하지 않는다.

허용된 실제 작업은 source snapshot 1회·prior52 보존 파일·기존182 CLI **단1회**다. 대상 순서를 명시하고 결과 후보가4개를 초과하면 완료로 승인하지 않는다. header 검산은 이 CLI가 수행하는 로컬 계획 범위이며 실제 전체 영상품질 검사나 원격 수집이 아니다. 자식 시작 뒤 stdout 출력 실패가 나도 finally에서 자식 종료를 기다려 중복 실행 위험을 줄인다.

## 준비 단계 검증과 남은 일

준비 시점에는 runner AST 문법만 검사하고 입력 배열/SHA 및 현재 코드 핀을 확인했다. 실제182 CLI·래스터 header·배열·원격·collector·학습·운영 source/ledger 읽기/쓰기 모두0이다. 이 준비를 계획 완료나 자료 확보로 보고하지 않는다. 독립 UI/API 변경이 없는 내부 계획이므로 화면 수정은 필요 없다. 실제 결과 뒤 Root를 통해 이해자료를 인계한다.

남은 일은 Root271 최종 검증 확인 → Root269 exact GO → 단1 로컬 CLI → source/ledger/code/원배열 전후 불변과 실제 결과 기록이다. Root270 수집은 별도 승인 단계이며 269로 실행 권한을 얻지 않는다.

## 실제 실행 — 2026-10-18 18:12~18:13 KST

Root271 최종 JSON `evidence/integration/selection271-project-validation-root-20261018.json` SHA `24b837029aafa7413a5a31b56ddbf9cdab91a7a6a53155e45b3608820aaaef9d`를 직접 읽고 검산했다. 별도96개 검증 exit0/141.469초·운영5핀/제품9핀 불변이며, 원268 실패 기록을 보존한다. 새 GO `evidence/integration/centers269-go-root-20261018.json` SHA `0fe7946ec5fadb4650f31d8b2fda4aa04dd0f56e187836d6a3b20b726c00662c`와 runner SHA `2058f84fc3d839c2776bfdab16ae15d14fb566a2973938b88435561e2e0a5a4f`도 확인한 뒤 승인 명령을 단1회 실행했다.

exec session **64065**, 로컬182 자식 PID **15296**이다. preflight 시각09:12:41.504720Z, 완료09:13:34.584299Z, exit0, runner 측정 **54.313초**, CLI invocations1이다. 이 PID는 collector가 아니라 로컬 위치계획/헤더검산이다. 원격·collector·학습0이다.

결과는 `evidence/integration/centers269-result-20261018.json`의 `LOCAL_PROPOSAL_COMPLETE_UNAPPROVED`다. 새 source 사본은 `data/centers269-fresh-20261018/source.json`/66,827,338B/SHA9473…1353으로 한 번 생성했고, 공유 원본과 원장은 쓰지 않았다. source/ledger의 전후 SHA·identity가 모두 같았다. code·GO·271 ref·기존 prior/proposal의 전후 핀 검사를 통과했다. 추가 보존 근거 `evidence/integration/centers269-preservation-20261018.json`에서52개 순서/구간/유일성·새ID 제외·boundary/config/code 후 핀을 모두 true로 확인했다.

새 merged prior SHA는 `bfe4b55d9413eea8972784748b1354ebc683285043dcc8f2a5c4fc5b8b03933e`, 새 proposal SHA는 **`661de17b3bed3f3cceb2624315a837ac0eec2bd4b71af039ac22f6299ee7d4de`**다. 로컬 기존 이미지 header115개를 검산했다. 실제 영상품질/전체 pending-support inventory를 새로 검증하지 않았다.

| proposal의 실제 배열 순서 | 주·연도 | spatial_window_id | 경도·위도 |
|---|---|---|---|
| 1 | 남동2024/train | `centers182-southeast_sulawesi-411ad85627a7` | 121.86859768157333, -4.001683264364351 |
| 2 | 고론2025/train | `centers182-gorontalo-da1b8a06c2fe` | 122.05818614879377, 0.5644754129351152 |
| 3 | 고론2022/train | `centers182-gorontalo-4771439e4b2d` | 122.43198529961823, 0.846786054863159 |
| 4 | 남동2024/train | `centers182-southeast_sulawesi-4976b0b4efb8` | 121.68183612318998, -3.625151297254438 |

CLI의 `--target` 우선순위는 남동2024→고론2025→고론2022로 명시했으며 결과 배열은 기존 구현이 교차 배치한다. 이를 남동 두 행이 항상 앞에 있다고 바꾸어 보고하지 않는다. 실제 소비 순서는 Root가 새 strict request의 `selected`로 명시해야 한다.

스냅샷 적격/28부족은 남동2024 22/6, 고론2025 18/10, 고론2022 24/4로 유지하며 후보 제안 수는 각각2/1/1이다. **이 후보4개는 확보량4개가 아니며 적격1,358·부족21을 줄이지 않았다.** v2 정책의 실제 원격 선별/화질 성공도 아직 증명하지 않는다.

후보 메타 요약 도중 보조 스크립트가 단일 `year` 키를 가정해 KeyError를 냈다. 실제 proposal 계약인 `years` 배열로 요약만 바로잡고 보존 JSON에 기록했다. 제품·동결 runner 변경이나182 CLI 재시도는 없었다. 허용 횟수는 여전히1이다.

최종 freeze에 runner/준비 JSON/실행 claim·preflight·log·result·보존 검사/새 snapshot·prior·proposal/GO·271 근거/이 문서의 SHA를 결속한다. Root270은 이 새 고정 사본과 proposal을 요청 준비에 재사용할 수 있으나, fresh 단일 잠금 안 전체 검증·선별정책/config/request 핀·별도 실행 승인이 여전히 필요하다. UI/API의 적격/보유량이 변하는 작업이 아니므로 화면 수정은 없다. 완료 근거를 Root에 전달해 이해자료 후속에 “새 위치 계획4개, 실제 수집0”을 구분하도록 인계했다.
