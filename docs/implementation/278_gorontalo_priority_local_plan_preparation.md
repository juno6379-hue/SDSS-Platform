# 278 — 고론탈로 우선 새 위치 계획 준비

상태: **PREPARED / LOCAL_CLI_NOT_EXECUTED / COLLECTION_UNAPPROVED**. 278 번호를 문서/evidence에서 검색해 기존 작업 충돌이 없음을 확인했다. 검색에 잡힌 다른 작업의 시각 문자열은278 작업 산출물이 아니다. 이번 소유 파일은 새 runner·준비 JSON·준비 freeze·이 문서뿐이다. 269 동결판과 원본 운영 자료는 수정하지 않았다.

## 쉽게 설명하면

Root가 남동2024 부족을 채웠다고 인계했으므로, 이미 제안한56개 위치는 그대로 기억해 제외하고 다음에는 **고론2025 → 고론2022 → 동자바2025** 순서로 새 위치 최대4개를 제안할 준비를 한다. 지금 완료한 것은 준비 파일이다. 아직 새 위치를 계산하는182 CLI도 실행하지 않았으며 다운로드·학습은 시작하지 않았다.

Root가 전달한 현재 원장 기준 잔여 예산은1,870,060,479B, 등록1,731행·적격1,364·부족15셀(고론2025 10/고론2022 4/동자바2025 1)이다. 게시된 후보1,348과 원본 적격1,364는 서로 다른 검증 범위다. **준비 단계에서 운영 source/ledger나 게시 pointer를 읽어 이 수치를 재검산하지 않았다.** Root273/275 완료 인계를 바탕으로 계획 입력만 고정했다.

## 기존56개 보존

| 입력 | 개수 | 원파일 SHA-256 | 후보 원배열 canonical SHA |
|---|---:|---|---|
| `data/centers269-fresh-20261018/prior-merged.json` | 52 | `bfe4b55d9413eea8972784748b1354ebc683285043dcc8f2a5c4fc5b8b03933e` | `661a233ee741aa2ef4046fd0db492db19730aa81ead9378e9f6cb81eb6dfc19b` |
| 같은 디렉터리 `proposal.json` | 4 | `661de17b3bed3f3cceb2624315a837ac0eec2bd4b71af039ac22f6299ee7d4de` | `2a90e3d076a106723a5f2821f26e70d7e8e03e4894d8de7cdefa1ae0af6b6a10` |

이어 붙인56개 원배열 canonical SHA는 `f6b728df70f2296809e7132b99239377d9f0f347ee7bef92dfd7c11f0df91862`다. 준비 중56개의 spatial_window_id 유일성을 확인했다. 실행 시52개/4개 구간별 exact 순서·SHA·유일성을 다시 검증하고, 원파일을 변경하지 않은 채 새 prior 파일을 만든다. 실제 수집에 사용되지 않은 과거 제안도 제외 목록에 유지한다.

## 새 입력·코드 핀

준비 JSON은 `evidence/integration/centers278-prepared-20261018.json` SHA `e33676f1589ffac3318614eb44ca1acedb581799f34249f276904a43ef79d492`다. 운영 경로는 그대로 두고 Root가 명시한 아래 새 값으로 이전269 핀을 자동 승계하지 않는다.

- source SHA: `0f436db2c320ca6a3b54ae265470d7c26e1e9d64fc657d35aa12619c3bb73b2b`, 크기67,518,599B.
- ledger SHA: `5d1ef4d2c1b917402ffdda2365c69d81984b1e682bad22a8cc00ad238456e86e`.
- boundary `data/first-group-boundaries/selected-six.geojson`: `de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909`.
- base config `configs/first-group.collection.json`: `8b0c1b2aad13a3344200998ec62a18853c5308adf4ec57b1af835333845fd7e3`.

실제 GO 뒤 새 `data/centers278-fresh-20261018/source.json` 사본을 한 번만 만들고 후속 요청 준비에서 재사용하도록 남긴다. 원장이나 전체 운영data/model은 복사하지 않는다. 원본 source/ledger는 전후 SHA·file identity로 검산하되 쓰지 않는다. 부분 산출물이 있으면 자동 덮어쓰기·삭제·재시도하지 않는다.

새 runner는 `evidence/integration/centers278-prepare-20261018.py` SHA `cbe09f3d190422f3088fa5be030e229765e63dd2c29d750b5e9a01a1b1f7df41`다.269 runner의 원 SHA `2058f84fc3d839c2776bfdab16ae15d14fb566a2973938b88435561e2e0a5a4f`를 확인한 뒤 독립 파일에 복사하고 새 경로/56개 구간/새 prepared SHA로 고정했다. 원269 runner·prepared·freeze·log·doc는 변경하지 않았다.

준비 JSON에 현재 관련 코드의 전체 SHA를 고정했다.269 준비 당시 코드와 모두 같음을 확인했다. 주요 핀은182 CLI `65fc9419680edbdc4daeb16a321eb8ca82d07df07f961d696b6a6a24a9742697`, guard `4052759b683f6f4f545a629466f2d4145e3ad9cc2ad8e6cdf5b1e3c0004a5dd2`, coordinator `9ae5ba986d3d48e89cfb269d8a242ffd6189d281649d98a11614c03e5ab3c9ab`, collect_samples `9ce6cf2a520edb14d8c67260e79fc5f605f11eab03d9d6773117e0fd193eb165`다. 실제 실행 직전/직후 다시 대조한다.

## 명시profile·기존 보호

182 CLI에 `--manifest-profile bounded128m-3000-v1`을 명시한다. descriptor SHA는 `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`다. 현재 source가64MiB를 넘었다고 자동 상향하지 않는다. source/candidate128MiB·3000행 및 노드/깊이/누적JSON IO의 고정 profile을 사용하며 개별 raster/header64MiB 등 다른 역할 한도를 바꾸지 않는다.

CLI 호출은 단1회, 신규 후보 최대4개다. 기본 실행은 PLANNED 출력만 한다. 실제 GO 뒤에도 execution lock이 있거나 source/ledger/code/prior/boundary/config 핀이 다르면 차단한다. 자식 시작 후 출력 실패도 finally에서 자식 종료를 기다린다. 실패 partial 파일은 보존하고 자동재시도하지 않는다. Root만 collector·원장/lock 집행을 소유한다.

이것은 로컬 기존 이미지 header 기반 위치 계획이다. 실제 전체 pending-support 검산·SCL/RGB/B02 품질·scene/window/split 실수집 가드·중복/독립정답·학습 승인이나 원격 예산 증가는 제공하지 않는다. 새 proposal을 만든 뒤 실제 수집하려면 Root가 fresh strict request/config/정책·원장 핀과 별도 실행 승인을 다시 결속해야 한다.

## Root GO 스키마와 명령

정확9개 키를 요구한다. `main_validation_ref`는 현재 코드 핀에 대응하는 Root의 고정 검증 근거이며 실행 전후 evidence 경로/SHA를 확인한다. 예전268 실패를 PASS라고 바꾸지 않는다. 실제 운영source가 이미 바뀌었으므로269 GO는 재사용하지 않는다.

```json
{
  "schema_version": 1,
  "kind": "ROOT_AUTHORIZED_LOCAL_CENTERS278_PLAN",
  "local_plan_approved": true,
  "maximum_cli_invocations": 1,
  "source_sha256": "0f436db2c320ca6a3b54ae265470d7c26e1e9d64fc657d35aa12619c3bb73b2b",
  "ledger_sha256": "5d1ef4d2c1b917402ffdda2365c69d81984b1e682bad22a8cc00ad238456e86e",
  "main_validation_ref": {"path": "<Root pinned validation evidence>", "sha256": "<sha256>"},
  "runner_sha256": "cbe09f3d190422f3088fa5be030e229765e63dd2c29d750b5e9a01a1b1f7df41",
  "main_validation_passed": true
}
```

다음은 승인 뒤 사용할 명령 계약이며 아직 실행하지 않았다.

```powershell
python -X utf8 evidence/integration/centers278-prepare-20261018.py --run-local-plan --approval <Root278 GO.json>
```

## 준비 검증과 남은 일

준비 단계: runner AST 통과, 기존 메타데이터56개·코드/boundary/config SHA 확인, noarg 기본 실행이 `PLANNED_AWAITING_ROOT_GO`/local_cli0/collectorfalse/network0임을 확인한다. 운영source/ledger 읽기·쓰기0, 실제182 CLI0·header/배열0·HTTP/collector/모델/추가QA0이다. 따라서 새 후보 수나 적격/부족 감소를 아직 확정하지 않는다.

준비 freeze는 이 세 파일의 최종 지문을 별도 새 evidence로 고정한다. Root 검토·exact GO 뒤 단1로컬 실행/결과/전후 핀을 별도 기록하고 실행 freeze를 추가 발행한다. 이 준비 freeze를 나중 결과에 맞춰 덮어쓰지 않는다. UI/API에 새 기능이나 보유량 변화가 없는 내부 준비이므로 화면 수정은 필요 없다. 실제 계획을 완료하면 Root를 통해 이해자료에 “로컬 제안”과 “실제 수집 성과”를 분리해 인계한다.
