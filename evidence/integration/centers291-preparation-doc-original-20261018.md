# 291 — 고론2025·동자바2025 로컬 위치 계획 준비

상태: **PREPARED_ONLY / ROOT_GO_PENDING**. 실제182 CLI·source 사본 생성·래스터 header/배열·운영 source/ledger/model 읽기/복사·HTTP·collector·운영쓰기0이다. Root290 QA의 원본 hold를 유지하며 이번에는 새 runner/고정 준비 JSON/이 문서/준비 freeze만 작성했다.289의 시각v2 제품 구현은 시작하지 않았다.

## 목적과 우선순위

Root가285 후 고론2022 적격36개로 최소28을 충족했다고 인계했다. 다음 대상은 **고론2025(부족10) → 동자바2025(부족1)**이며 고론2022를 제외한다. 과거 제안64개를 원순서로 기억해 제외한 뒤 새 위치 최대4개를 제안할 준비다. 아직 새 후보 수는 확정하지 않았다. 향후 후보4개가 나와도 실제 확보4개나 부족 감소4개라는 뜻은 아니다.

현재 핀과 수치는 Root가 제공한 선언이며291이 운영 원본을 다시 읽어 검증한 값이 아니다. 원본이 바뀌면 기존 GO로 따라가지 않고 차단하도록 고정했다.

## 기존64개 원배열과 입력 고정

| 입력 | 개수 | 원파일 SHA-256 | 배열 canonical SHA |
|---|---:|---|---|
| `data/centers284-fresh-20261018/prior-merged.json` | 60 | `af7c8eb615271027fe9bb1ad3b95e85fa0542c9e7638bb566fd4b61c456efb25` | `3029d3fa9456af0e0995eeb7fc857c1b29b739e9c3fea0a3e28bef1790d6fe37` |
| 같은 디렉터리 `proposal.json` | 4 | `1cb1bb7a37168251fdb949636c8915add94b57db99c9ebd0e0a9b6d7b267ace5` | `72467a6fd06e2ac40dd900cbc18507a5aa56a3d88f260ff0c403640af1b9ddb0` |

두 배열을 그대로 이어 붙인64개 canonical SHA는 `d855117832cdfde64e03a37a0891fa925ef1088f42fbc768b26120a7c399e7fd`다. 준비 중 완료된 과거 proposal JSON만 읽어60/4개 수·유일성·배열 SHA를 확인했다. 원래 파일과 순서는 수정하지 않았다. 실행 시에도60개/4개 구간별 exact 보존·유일성·원파일 SHA를 다시 검사한다.

Root가 고정한 현재 source SHA는 `9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7`, 크기68,220,381B다. 원장은 `4a4f4a47b522b9497b944ac00b29d2368a977c1a4eb6dfe972a34959fcc68722`다. 준비 JSON의 이 값과 그 JSON SHA를 runner에 고정했으므로 자동 새 원본 추종이 없다.

boundary ref는 `data/first-group-boundaries/selected-six.geojson` SHA `de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909`, base config ref는 `configs/first-group.collection.json` SHA `8b0c1b2aad13a3344200998ec62a18853c5308adf4ec57b1af835333845fd7e3`다. 원본 hold 동안291은 boundary/raster bytes를 읽지 않았고284의 고정 refs를 보존했다. 실제 실행 GO 뒤에 이 SHA도 검산한다.

## 새 파일과 원판 보존

준비 파일:

- `evidence/integration/centers291-prepared-20261018.json` SHA `4934542b5aa861b6737532e4495816d3c9ecaf3d3a940785edf1d37a1300275c`.
- `evidence/integration/centers291-prepare-20261018.py` SHA `87ab2abaac3bcfad0738055dd138a0657197e6ab0123ed8e48c09d755b135a26`.

검증된284 runner SHA `c15cb938f60f07821e5b7f906f0c25afd823abd428d05dde3fe203cdcd07565b`를 확인한 뒤 새291 코드에 복사했다. 변경은 새291 경로/64개 수·60/4 구간/새 prepared SHA/새 source·ledger·대상 목록이다.284 원판·준비·실결과·로그는 그대로다. 준비 code pins는284 목록의 현재 소스 SHA를 읽어 모두 같음을 확인했다. 모델/운영 자료를 import하지 않았다.

후속 새 경로는 `data/centers291-fresh-20261018/` 아래 `source.json`, `prior-merged.json`, `proposal.json`이다. **지금 이 디렉터리나 사본을 만들지 않았다.** Root의 hold 해제와 exact GO 뒤 source 고정 사본을 한 번만 생성하고 후속 요청 준비에 재사용하도록 남길 계획이다. 전체data/model/원장 복사는 하지 않는다.

## 유지하는 실행 보호

182 CLI에 `--manifest-profile bounded128m-3000-v1`을 명시한다. descriptor SHA는 `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`다. 현재 source가64MiB를 넘더라도 자동 profile 선택/상향이 아니다. source/candidate128MiB·3000행 및 고정 노드/깊이/누적JSON IO·기존 역할별 작은 cap을 유지한다. 개별 raster/header64MiB 등 기존 한도는 바꾸지 않는다.

기존 bounded reader/snapshot·source/ledger 전후 SHA/identity·code 전후 핀·동일 GO/검증 ref·원배열 검산을 유지한다. execution lock이 있거나 핀이 달라지면 중지한다. 단1로컬 CLI/최대4개 후보/새경로만 쓰기/claim 독점·partial 보존/noRetry를 유지하고, 자식 시작 뒤 stdout 실패도 finally에서 자식 종료를 기다린다. 원본/원장/모델·다른 collector·profile/pointer는 쓰지 않는다.

이 계획은 실제 전체 pending/support inventory나 scene/window/split·SCL/B02·80% 품질·95% 주내·나지256·독립정답 검증을 대신하지 않는다. 후속 실행 결과도 실수집·학습 승인은 false다. Root만 collector/원장/lock을 소유한다.

## Root GO 계약

기본 noarg 실행은 PLANNED만 출력하고 운영 입력을 열지 않는다. 실제 실행하려면 정확9개 키의 새 GO가 필요하다. 이전284/291 외 다른 GO를 재사용하지 않는다. `main_validation_ref`는 Root가 현재 code pin에 대응한다고 확인한 고정 검증 evidence path/SHA다.

```json
{
  "schema_version": 1,
  "kind": "ROOT_AUTHORIZED_LOCAL_CENTERS291_PLAN",
  "local_plan_approved": true,
  "maximum_cli_invocations": 1,
  "source_sha256": "9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7",
  "ledger_sha256": "4a4f4a47b522b9497b944ac00b29d2368a977c1a4eb6dfe972a34959fcc68722",
  "main_validation_ref": {"path": "<Root pinned validation evidence>", "sha256": "<sha256>"},
  "runner_sha256": "87ab2abaac3bcfad0738055dd138a0657197e6ab0123ed8e48c09d755b135a26",
  "main_validation_passed": true
}
```

승인 뒤 사용할 명령 계약이며 아직 실행하지 않았다:

```powershell
python -X utf8 evidence/integration/centers291-prepare-20261018.py --run-local-plan --approval <Root291 GO.json>
```

## 준비 검증과 완료 범위

번호 검색에서 기존291 작업 충돌이 없음을 확인했다. AST 문법과 기본 noarg PLANNED/local_cli0/collectorfalse/network0, 과거64개 메타데이터 및 코드 SHA만 검사했다. 실제182·header·래스터 배열·운영 source/ledger 읽기·실자료 사본/다운로드는0이다. 추가 제품 회귀나 실제 QA를 실행하지 않았다.

준비 freeze는 이 문서와 새 runner/prepared/noarg 근거 및 부모284 runner 지문을 고정한다. 이 준비 판을 결과에 맞춰 덮어쓰지 않고, Root 후속 GO 뒤 결과 문서와 실행 freeze를 새로 추가한다. Root290 hold가 유지되는 동안 실제 실행하지 않는다. UI/API/보유량을 바꾸는 준비가 아니므로 화면 변경은 필요 없다. 실제 계획을 완료하면 Root를 통해 이해자료에 “위치 제안”과 “취득 성과”를 분리해 인계한다.289의 순수v2 제안은 계속 RFC 상태다.
