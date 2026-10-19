# 313 — 309 후보 게시 후 현재 원본 profile/API 연결 준비

## 2026-10-18 23:07 KST — 실제 재결속·API 완료 / 브라우저 대기

이 절이 아래 미실행 준비를 대체한다. 원준비 문서는 `evidence/integration/doc313-preparation-before-actual-root-20261018.md`에 SHA2369461e6ca5748250a67380cc8c126746fea829998a8683f6cf858a280591bf로 원바이트 보존했다. 원freeze·코드 지문을 소급 바꾸지 않았다.

Root는314 독립 검토의 추가차단없음과312 실제 publication SHAae247af18730fc9d391b8c5730d5db5c72772b1545d2b5112a8aa6f1a7bf0356를 확인하고 실제 실행했다. 기존profile b9a2cd5cfe20bb570281882adcd1f47b4b81b0be4e69c0f0b91d606f0cd17f9e는 원바이트 archive 후 같은128 descriptor에서 현재source0c149로만 재결속했다. 새config SHAe63f89cae95c33bad9f5195e9750b684232ee89a895309d591668e7519767a68, selection receipt SHA5f1ae06a0763d99bed1fced60e97365f8b10797e00d99e1417d2f2be42ae7544다.

session35865 exit0, 실API GET200/32.657초/11checks 모두true를 확인했다. 재고 응답 시각23:07:16.963124 KST와 예산 관측23:07:18.670589를 분리한다. 원본1407/셀부족0·신규후보1391(865/276/250)/현재source일치·나지3차단/학습false·bare50만과거source경고·잔여1799757940/oldpending136314880사용포함·운영4핀/config보존을 확인했다. APIchecks SHAba1168cd452c0e1a01cbbec785611428362ccc9c706ae585d406629d5d001cc8, 결과파일은 `evidence/integration/profile313-api-checks-root-20261018.json`이다.

API40156:8002와frontend32748:5174의 실제OS·listen 상태를 실행 전 확인했으며 서버restart·QA재실행·제품변경0이다. 32.657초는 단1관측이며 SLA/지연원인/최대성능 보장이 아니다. config반영과API 검증은 모두 완료했지만 브라우저는 별도315 인수 후 검사 중이다. 실제 화면 완료를 이 문서에서 미리 선언하지 않는다. 수량 최소조건과 나지·독립정답·학습/운영 승인은 별개이고 전체 개발은 미완료다.

상태: **PREPARED_UNAPPROVED / IMPLEMENTED_UNVERIFIED**. 309 QA 실행 중 Root가 순차 준비한 내부 코드다. 실제 승계·profile 쓰기·API/브라우저·운영 원본 읽기0이며, 준비를 운영 성공으로 보지 않는다.

## 목적과 고정 조건

현재 profile b9a2cd5cfe20bb570281882adcd1f47b4b81b0be4e69c0f0b91d606f0cd17f9e는 이전 source9e63564c87647a144665bbb6bbe49b4a95d09bbd2c3bc0f3725861c54d5e7109에 결속돼 있다. 새 후보 QA309의 실제 완료 검증과312 안전 게시가 성공한 뒤에만, 동일 bounded128m-3000-v1 descriptor에서 현재 source0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658로 명시 재결속한다. 원본1407/셀부족0, 원장d5ee31ff7970adaaa6b166805c240616efa8e9af713bb8394c7a166346f21c91와 잔여1799757940B는304/307 감사 인계값이다. 이 준비는 운영 파일을 다시 읽어 확인한 작업이 아니다.

원판 `evidence/integration/profile294-post290-root-20261018.py` SHA a75fdac5f66830ba5c322aa1bd7237ad4939b6b644f73edc6fd340b303d5928a를 `profile313-before294-code-root-20261018.py`로 원바이트 보존했다. 새 `profile313-post309-root-20261018.py` SHA 7f630140edf01bb7f79992ba948167258cfe70925f023717b0e30869d6169b27/5902B는 번호·312 publication 경로·고정 source/ledger/oldprofile/oldsource·API 기대 원본수/부족량/예산만 바꿨다. 기존 제어·검산·HTTP순서·descriptor·한도를 유지하며 compile만 수행했다. 제품 코드나 실행 중 QA 코드 변경은 없다.

## 실행 계약과 실패 처리

실제312 publication의 정확 SHA를 `--publication-sha256`에 전달해야 한다. 준비 시 최종 후보 수를 상수로 넣지 않으며, publication의 candidate_view에서 실제 수량을 받는다. 완료 상태·정확 marker·retained rows/partition·파일 SHA 불일치0·현재source일치·학습false·나지3차단을 요구한다. 실제 QA가 이 기대와 다르면 실행을 멈추고 결과를 검토하며 gate를 낮추지 않는다.

같은128 scope/누적16GiB 안에서 source/ledger/두pointer와 oldconfig를 검산하고, lock 부재·새 출력 경로 부재를 요구한다. oldconfig를 원바이트 archive한 뒤 source SHA만 바꾼다. 원config와4개 운영핀을 교체 직전 다시 확인하고 exclusive temp/fsync/os.replace를 수행한다. selection receipt가 먼저 기록된 뒤 기존8002 API에 Origin5174로 단1 GET한다. API 응답은2MiB 이내, timeout150초이며 재시도나 서버 재시작은 없다.

API 확인은 원본1407/부족0·새 publication의 실제 후보수·현재source일치·나지3차단/학습false·bare50의 과거source 경고·잔여1799757940/oldpending136314880 사용포함·운영4핀과config불변을 구분한다. 첫API 실패 전에config가 이미 변경됐을 수 있으므로 selection receipt로 실제 적용 여부를 판정한다. 자동 rollback·재실행·환불·QA 재실행을 하지 않는다. GET 지연 한 번을 SLA나 원인 진단으로 확대하지 않는다.

## 후속 인계

최종 freeze/독립 정적 검토/Root 검토와 실제312 publication 성공 지문 전 실행하지 않는다. 실행 직전 현재 OS/API8002·frontend5174와 source/ledger/lock을 다시 확인해야 한다. 다른8000 앱은 건드리지 않는다. 성공하더라도 실브라우저 미검증 상태이므로 web_ui 담당이 기존 탭에서 실제 수치·시점 경고·나지차단·예산/관측시각·콘솔·overflow를 별도로 확인한다.

사용법은 준비 코드의 parser와 같은 `python -X utf8 -u evidence/integration/profile313-post309-root-20261018.py --publication-sha256 <실제312 publication SHA>`이며 지금 실행하라는 명령이 아니다. Root별 승인 뒤에만 실행한다. 완료 코드·증거는 설계/계약/API·사용법·인계와 별도 understanding_agent 대본/FAQ/INDEX/이력에 같은 단위로 반영한다. 수량충족을 나지·독립정답·학습/운영 승인으로 확대하지 않는다.
