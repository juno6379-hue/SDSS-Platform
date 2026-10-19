# 302 — 남은 동자바2025 로컬 위치 계획 준비

상태: **PREPARED_ONLY / ROOT_GO_PENDING**. 기존302 작업 충돌이 없음을 확인했다. 새 runner·prepared·문서·준비 freeze만 작성했다. 실제182 CLI/header/배열·운영 source/ledger/model 읽기/복사·source 사본 생성·HTTP/collector/실QA0이다. Root301 API 준비와 파일 소유가 겹치지 않는다.

## 현재 의미와 대상

Root297 native 인계는 신규16개 중15개 적격, 나지0이다. 원본1763/적격1391(849/292/250), 고론2025는33으로 최소28 충족, 남은 부족은 **동자바2025 한 셀**이다. 이 값은 Root의 완료 인계이며302가 원본을 재검사한 값이 아니다. native15는 새 cohort QA/게시 승인이 아니고 현재 게시1360은 old9d 기준으로 stale다.

다음 대상은 `east_java:2025` **하나만**이다. 고론2022·2025는 제외한다. 기존68개 위치를 원순서로 보존해 제외하고 새 위치 최대4개를 제안할 준비다. 기존 주별2개 한도상 실제2개가 나올 수 있지만 아직 CLI를 실행하지 않았으므로 후보 수는 미확정이다. 위치 제안을 자료 확보나 부족 감소로 계산하지 않는다.

## 고정 입력과 원판

Root 현재 source SHA는 `9e63564c87647a144665bbb6bbe49b4a95d09bbd2c3bc0f3725861c54d5e7109`,68,887,373B, ledger는 `574d382dd9da51ae56dc8fb135532f8f2e5c542b2c4cafdf73a6ee8dd9c6045f`다. 준비 중 이 운영 파일이나 원본 snapshot 본문을 읽지 않았다. 실행 GO 뒤만 전후 SHA/file identity를 검산하고 새 `data/centers302-fresh-20261018/source.json` 사본을 한 번 만든다. 지금 디렉터리/사본은 만들지 않았다. 원본이 바뀌면 자동 승계하지 않고 차단한다.

| 과거 입력 | 수 | 원파일 SHA |
|---|---:|---|
| `data/centers291-fresh-20261018/prior-merged.json` | 64 | `278d02829ff3ffeef46532a7c41177c698a8ae060439060a87eabc2635ad0720` |
| 같은 디렉터리 `proposal.json` | 4 | `e92d2cb2feefab44b1ed5209d56d3da02f0097306dd23bed0d2dbd0eca1a8a57` |

metadata 배열을 그대로 이어 붙인68개 canonical SHA는 `0daf086fbdb52e3f86621ad45debd05fad173786ec36e1be78fcefad81f3fb09`다. 준비 중 기존 메타데이터만 읽어64/4개 수·유일성·구간별 배열 SHA를 확인했다. 과거 제안의 집행 여부에 따라 제외 기록을 지우지 않는다. 실제 실행에서도 원순서/SHA를 다시 검사한다.

부모291 runner SHA `87ab2abaac3bcfad0738055dd138a0657197e6ab0123ed8e48c09d755b135a26`를 확인하고 원판을 변경하지 않은 채 새302에 독립 복사했다. 새 source/ledger·경로·68개/64+4구간·prepared SHA/단일target만 고정했다. 기존27개 code pins는 현재도 같은 SHA임을 확인했다. 다른 collector 제품/Root301 파일은 수정하지 않았다.

새 runner는 `evidence/integration/centers302-prepare-20261018.py` SHA `b1bfeb4e11281294925fbf0e8b075a2da8de8f4e1b7bedad8c9c0eee76761ada`, prepared는 `centers302-prepared-20261018.json` SHA `e3b206e4f4192b74e77542d4679ae7e4e2ee3868e86a3833566bf7d862497169`다.

## 유지하는 계약과 Root GO

정확 `--manifest-profile bounded128m-3000-v1`/descriptor `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`를 명시한다. source/candidate128MiB·3000행·고정 node/depth/누적JSON IO와 개별 raster/header64MiB·작은 역할 caps를 바꾸지 않는다. 자동 상향은 없다. boundary/config는 기존 de7722…c909/8b0c…d7e3 refs를 보존하며 준비 중 boundary/raster를 읽지 않고 실행 GO 뒤 검산한다.

기존 source/ledger/code/GO·검증ref/원배열 전후 pin, execution lock 부재, 단1CLI/새경로만 쓰기/claim 독점·partial 보존/noRetry·자식 finally wait를 유지한다. 실패 자동 삭제·환불·재시도하지 않는다. 이 로컬계획은 full pending/support·scene/window/split·최종80/95/나지256·독립정답 검증을 대신하지 않는다.

새 GO는 기존과 같은 strict9keys다. 실제 Root 실행 전에는 승인 파일을 만들지 않았다.

```json
{
  "schema_version": 1,
  "kind": "ROOT_AUTHORIZED_LOCAL_CENTERS302_PLAN",
  "local_plan_approved": true,
  "maximum_cli_invocations": 1,
  "source_sha256": "9e63564c87647a144665bbb6bbe49b4a95d09bbd2c3bc0f3725861c54d5e7109",
  "ledger_sha256": "574d382dd9da51ae56dc8fb135532f8f2e5c542b2c4cafdf73a6ee8dd9c6045f",
  "main_validation_ref": {"path": "<Root pinned validation>", "sha256": "<sha256>"},
  "runner_sha256": "b1bfeb4e11281294925fbf0e8b075a2da8de8f4e1b7bedad8c9c0eee76761ada",
  "main_validation_passed": true
}
```

승인 뒤 명령은 `python -X utf8 evidence/integration/centers302-prepare-20261018.py --run-local-plan --approval <Root302 GO.json>`다. 기본 noarg는 PLANNED/local_cli0/collectorfalse/network0만 출력한다. 준비 검증은 AST/noarg 및 과거 메타데이터·소스코드 SHA 대조뿐이다. 실제자료 스캔·QA를 실행하지 않았다.

Root 전략은 남은 동자바 소단위 수집 뒤 최종 원본을 고정해 QA를 한 번 묶는 것이다.302는 그 위치 계획 준비일 뿐 미래 수집/최종QA를 완료하지 않았다. old1360과 새 원본1391을 혼용해 current 표시하지 않는다. UI/API/보유량을 바꾸는 기능이 없어 화면 수정은 필요 없다. 실제 계획 완료 시 별도 실행 문서/freeze와 이해자료 인계를 추가하고 이 준비 동결판은 보존한다.


## 2026-10-18 22:11 KST — Root 실제 로컬계획 완료 후속

실제 상태는 **VERIFIED_REAL_LOCAL_PLAN_COMPLETED / COLLECTION_UNAPPROVED**다. 준비 절의 실행0은 당시 역사다. 추가 전 준비 문서를 `evidence/integration/centers302-preparation-doc-original-20261018.md`에 원바이트 보존하고 SHA `bb0add5f62db22ec34e8760985b81fbc10544c5f369da1726505b2a271b8aa6d`와 대조했다. 원준비 freeze는 archive에 보존된 역사 문서 지문을 가리키며 재발급하지 않았다. runner/준비 JSON도 바꾸지 않았다.

Root 실제 인계는 session43593/child182 PID38160,exit0/단1CLI/67.171초/로컬header118개다. 완료 메타데이터 시각은13:11:01.169971Z(22:11:01 KST)다. 기존68개 원배열 순서 보존·제외와 source/ledger 전후stable,HTTP0을 확인했다. 이 문서 담당은 CLI를 중복 실행하거나 운영 source/ledger/header를 다시 검사하지 않았다.

새 proposal은 `data/centers302-fresh-20261018/proposal.json` SHA **`e145e1fc2028bb00c26ceace8f814281fa8c48a9663ea18b1f31548d4eeec842`**다. 실제 동자바2025 두 곳을 제안했으며 스냅샷 적격27/부족1이다. 같은 디렉터리 prior-merged.json은 완료 metadata SHA를 직접 검산해 `60b748a50f05d847bb1807fa18a763d44e88007c672eb805a52e255d5e5e74fa`로 고정했다. sourcecopy는9e635…e7109/68,887,373B이며 원본/원장은 쓰지 않았다.

첫 후보 `centers182-east_java-5141c64815b2`/2025/train(112.12452853355475,-7.764251076494455) 한 곳만304 수집 준비에서 선택했다. 두 제안은 실제 확보2개나 부족감소2개가 아니다. 원본1391/부족1을 이 로컬계획으로 바꾸지 않으며 actual_quality/execution/trainingfalse·fullpending-support 검산미대체를 유지한다.

Root301은 새source9e profile 명시재결속/API 원본1391gap1·old1360stale·3차단false·잔여1,822,603,826B를 별도 완료했다고 인계했다. profile SHA는 `b9a2cd5cfe20bb570281882adcd1f47b4b81b0be4e69c0f0b91d606f0cd17f9e`이고 oldpointer996a…72c0는 보존됐다.305브라우저는 인계 당시 진행 중이므로 이 문서로 실제 브라우저 확인까지 완료했다고 주장하지 않는다.

304는 새 request/config/canonical·동일Root잠금안fresh inventory·독립검토/새실행승인을 요구하는 별도 준비다. currentsource/원장/나지·독립정답/학습 gate를 이 위치 계획으로 해제하지 않는다. 완료 근거를 Root에 인계해 이해자료에서 제안2개/실취득0과 원본1391/old게시1360을 구분하도록 요청한다. 추가 운영IO/HTTP·QA·수집0이다.
