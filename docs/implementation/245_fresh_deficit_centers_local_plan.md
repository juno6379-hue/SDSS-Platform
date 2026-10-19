# 245 — 44개 이전 위치를 제외한 다음 로컬 제안

상태: **VERIFIED_REAL — 로컬 위치 계획 완료 / 수집·품질·학습 미승인**.

235 수집은 신규 패치0·적격0으로 끝났고239 좁은 감사 뒤 Root가245 로컬 계획 한 번만 명시 승인했다.245는 이전40개와235의4개 제안을 원배열·핀 그대로 보존해44개를 제외하고 다음 위치4개를 만들었다. 확보한 영상이나 부족량 감소로 합산하지 않는다.

## 실행과 실제 결과

Root GO `centers245-go-root-20261018.json`과 정확한 runner SHA를 검산한 뒤, 현재182 SHA `65fc9419680edbdc4daeb16a321eb8ca82d07df07f961d696b6a6a24a9742697`를 단 한 번 호출했다. 과거235 runner의 옛182 핀을 재사용하지 않았다.

- exec session86517 /182 CLI PID31648, exit0·프로세스 종료.
-2026-10-18 17:17:09 KST 완료, runner 측정59.109초. 이 시간은 새 snapshot 생성·CLI·후속 pin 검산을 포함한 구간이며 다른 실행과의 성능 비교가 아니다.
-명시 `--manifest-profile bounded128m-3000-v1` 사용.source가64MiB보다 작아도 전체237 JSON 소비 경로의 누적 보호를 활성화하려고 명시 선택했다. 크기에 따른 자동 선택이 아니다.
-기존115개 source header를 확인하고 새 위치4개를 제안했다. 추가 native 품질/배열 감사·선택scene/SCL/B02 검사·원격 요청·collector·학습은0이다.

| 제안 순서 | 주·연도 | 고정 split | 현재 적격 /28개까지 부족 | 새 위치ID |
|---|---|---|---|---|
|0|남동술라웨시2024|train|22 /6|centers182-southeast_sulawesi-f5fa8f8ccc4f|
|1|고론탈로2025|train|18 /10|centers182-gorontalo-cdd18dd42ff8|
|2|고론탈로2022|train|24 /4|centers182-gorontalo-c15f295679a6|
|3|남동술라웨시2024|train|22 /6|centers182-southeast_sulawesi-99e193f48bc8|

네 위치 모두 고정 경계의 native 기하 inside fraction1.0이다. actual_quality_eligible/execution_supported는 모두false다. 동자바2025 부족1을 포함한 전체 적격1358/부족21은 달라지지 않는다. 나지 밀집 여부도 검증하지 않았다.

## 원본·원장과 이전 제안 보존

원본 source SHA `4f8fcaff71868539aff16b3c351992696a6464b9cb229a5ff0f243778b7cd3e8`, 원장 SHA `9c452bfb3773dddf08dc1091640ed33cb7885b30bdd6b1f7b7ebb58616646c86`를 실행 전후 identity+전체 SHA로 검산해 동일함을 확인했다. 이 runner는 원본·원장·모델·게시pointer·Root profile247 UI 설정을 쓰거나 변경하지 않았다.

새 고정 사본은 `data/centers245-fresh-20261018/source.json` **한 개**만 생성했다.66827012B이고 SHA는 원본과 같다. 다음249 요청은 이 사본을 재사용하며 또 만들 필요가 없다. 기존227 snapshot과 다른 source이므로 과거 사본을 현재 것으로 재사용하지 않았다.

기존235 prior40 SHA `35400c8d857cc06df56632e49ba1f63d475914ab2bd7f7f664f80be0a8ce6bca`와235 proposal4 SHA `87e6f5f157d940e00c624f46821d30329135ef9182a0acb1db248bfb59a712da`는 원바이트 그대로다.245 prior44의0~39와40~43 배열을 각각 구조·canonical SHA로 대조해 원순서를 보존했다.44개 공간ID가 서로 다르고 새4개를 더한48개도ID 중복0이다. ID 중복 검사는 전체 pending/support·교차split 기하 검증의 대체가 아니다.

## 고정 산출물·후속 참조

| 산출물 | SHA256 |
|---|---|
|data/centers245-fresh-20261018/source.json|4f8fcaff71868539aff16b3c351992696a6464b9cb229a5ff0f243778b7cd3e8|
|data/centers245-fresh-20261018/prior-merged.json|380ac7849963558798fb5edd7e8f2dbff4ba55adc4ecd08f5dccfd8535dc9b4c|
|data/centers245-fresh-20261018/proposal.json|22cb58cc4b60b393d3f18ea2f31d30332b323f56113ec565bdc35710fbf84cd0|

근거는 evidence/integration/centers245-{prepared,preflight,cli,result,metadata-preservation}-20261018 접두사와 Root GO다. runner는 별도의 exclusive claim을 생성해 재시도/중복실행을 막는다. 이번 호출 횟수1이며 실패하면 partial을 보존하고 자동 재시도하지 않는 계약이다. 준비 단계에서는 active source/ledger를 읽지 않고 과거 제안 메타데이터·코드와 syntax만 검사했으며, 실제 운영 pin 읽기는 Root GO 뒤 수행했다.

## 남은 승인과 UI 영향

full_pending_support_inventory_verified=false다.199/200의 잠금 안 fresh 전체지원·기존pending·겹침·scene/window/split·예산·선택scene/SCL/B02/실품질 검산은 후속249에서 Root가 별도로 판단해야 한다.245를 그 검산 통과나 수집 승인으로 표현하지 않는다. 기존4GiB·공유2초·첫429·물리3000·미정산pending2 전액·모델/split 보호는 유지된다.

실자료 증가가 없어 현재 UI의 적격·부족 수치를 갱신하지 않는다. 이 단위는 실제 로컬 계획만 완료했고 다음collector 시작은 Root 소유다. 이해 담당은 새 위치와 확보 자료의 차이, 원배열 보존, 단일 snapshot 재사용, 후속 검산 미완료를 설명/FAQ/INDEX에 반영한다.
