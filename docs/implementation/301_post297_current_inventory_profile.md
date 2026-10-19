# 301 — 297 실감사 후 현재 재고와 고정 후보 시점 분리

## 준비 상태와 목적

2026-10-18 22:08 KST, 준비 코드 문법 검증 완료·실행 전. 실제 실행 결과는 후속 절로 별도 기록한다. 기존 282 검증 경로를 새 source/ledger/pointer/profile에 명시 결속한 내부 운영 절차이며 공유 제품 코드는 수정하지 않았다.

297 단1 bounded native 감사가 신규16/15적격·나지0·원본/이력/pending 보존과 실정산을 확인했다. 현재 원본은1763행/1391적격(849/292/250), 셀 부족1은 동자바2025다. 고론2025는18+15=33으로 최소28을 충족한다. 실물1764는 사전1748+신규16의 추론이며 전체 실물 재스캔 결과가 아니다.

남은 동자바 소단위 수집을 먼저 진행한 뒤 최종 원본에서 후보 QA를 한 번 수행한다. 그동안 기존290 후보1360은 고정9d source의 실제 검증 결과로 보존하고 현재9e와 시점 불일치를 표시한다. 현재1391 적격과 후보1360은 서로 다른 검증 범위다. 새15개는 native 검증을 마친 원본 자료이며 기존 후보 QA에 포함된 것으로 표현하지 않는다.

## 코드·입력·변경

`evidence/integration/profile301-post297-root-20261018.py`는 `profile282-post279-root-20261018.py` 원판 SHA df34e0c865f5184055b7d71807bfd566aa090eacefccf942236b285803ec2be5를 보존 복사했다. 원바이트 사본과 최소diff는 `profile301-before282-root-20261018.py`, `profile301-vs282-root-20261018.diff`다. 준비 코드 SHA는3ba91d7c37e51f26d59341dd54f57c2cce364dc5734a37c46956a5e2d0d17993다.

실행은 정확한297 native 감사 지문을 요구한다. 감사 완료·helper16/15·old행/history/pending·두 읽기 안정성을 검증한 뒤 current source9e63564c87647a144665bbb6bbe49b4a95d09bbd2c3bc0f3725861c54d5e7109, ledger574d382dd9da51ae56dc8fb135532f8f2e5c542b2c4cafdf73a6ee8dd9c6045f, 현재1360 pointer996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0를 확인한다. 같은128 profile/16GiB 누적 JSON 범위에서 읽는다.

기존 config a644b5b2cdf8917d13028f7a89ceeb4996d5ad5dc54af2b6fb2c9fda2c98f9de의 원바이트를 archive하고, 같은 descriptor에서 source SHA만9d→9e로 명시 변경한다. 새 독점 임시파일/fsync·replace 전4운영핀 확인·selection 선기록·단1 API GET을 유지한다. 새 출력 선존재 시 차단한다. API 실패 시 설정은 이미 변경됐을 수 있으므로 selection과 archive를 보존하고 자동 rollback·재시도하지 않는다.

## 예정 API 검사·UI 인계

localhost8002 collection-status 단1GET에서 raw1391/gap1, 고정 후보1360/source 불일치, 나지3차단/학습false, bare50 과거 시점 불일치, 잔여1822603826B, oldpending136314880B(사용에 포함), 원본·원장·포인터4핀/config 보존을 확인한다. source와 후보 모두64MiB를 넘으므로 명시128 경로를 유지한다. 크기에 따른 자동 상향은 없다.

브라우저 완료는 API 검사와 구별한다. 실제 API 성공 뒤 web_ui에 기존 탭 단1새로고침·현재/고정 시점 경고·예산/asof·console·overflow 계약을 인계한다. 수동 중복 GET·새 탭·서버 재시작·제품 수정은 필요하지 않다.

## 실제 근거·한계

준비 시 문법 compile만 했으며 실행·HTTP·후보QA·native 재검사는0이다. 실행 후 입력 감사는 `deficit297-native-root-20261018.json` SHA e8c51e5c0afd86d4f0d89a58121103bad76ff3a5e4504079c41217ac08731096를 사용한다. source-profile 선택 변경은 원격 다운로드 예산 증액이나 품질 gate 해제가 아니다. 나지 각 split0.5%·기여5개는 여전히 미달이고, 독립정답·다른5모델 실행기/운영 승인 미확보 및 전체 개발 미완료를 유지한다. 별도 understanding_agent가 완료 후 설명·대본FAQ·INDEX·이력을 갱신한다.
# 2026-10-18 22:10 KST 실제 후속 — API 검증 완료

아래 준비 시점의 실행 전 상태를 대체하는 실제 결과다. 303 독립 정적 검토 c03bfcc3fc01dfb0ae2f130ec9c175433e0cac0beefb9b7c87fa187e4015b0e7에서 추가 차단이 없음을 확인한 뒤 Root가 native 감사 SHA e8c51e5c0afd86d4f0d89a58121103bad76ff3a5e4504079c41217ac08731096로 한 번 실행했다. 원준비 문서는 profile301-preparation-doc-before-result-root-20261018.md에 원바이트 보존했고 코드와 기존 freeze는 수정하지 않았다.

기존 profile a644를 원바이트 보존하고 같은 descriptor에서 source만9d→9e로 명시 결속했다. 새 config SHA는 b9a2cd5cfe20bb570281882adcd1f47b4b81b0be4e69c0f0b91d606f0cd17f9e이며 selection 시각은22:10:20.837128이다. API 단1GET은 exit0/HTTP200/31.922초, 11검사 모두true였다. 원본1391/gap1, 고정 후보1360과 bare50의 시점 불일치, 나지3차단/학습false, 잔여1822603826B, oldpending136314880B가 사용액에 이미 포함됨, 운영4핀/config 보존을 확인했다. 재고 응답22:10:51.805379와 예산 관측22:10:52.558416을 구분한다. 단일 지연은 SLA나 최대 성능 보장이 아니다.

근거는 profile301-selection/api-response/api-checks-root-20261018.json이다. 원본·원장·후보 포인터 쓰기, QA/native/게시 중복, 서버 재시작은0이다. 305 UI 담당에게 실제 API 계약을 인계했으며 기존 브라우저 페이지를 별도 확인한다. API 성공을 브라우저 완료로 표현하지 않는다. 같은 고정 source에서302 로컬 위치 계획의 병렬 읽기만 허용했고 다운로드·원본 변경·신규 수집은 아니다.

