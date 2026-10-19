# 285 — 고론탈로2022 단일batch 준비

상태: PLANNED/IMPLEMENTED_UNVERIFIED. wrapper SHA66fe2ed5b76ed53342ce7cb84617cc500a3bb54c03ece64e65b65249fdee80ed는279판의finally wait·원pending전액·global lock/fresh200전검사·1batch16·실측정산/종료근거를유지한다. 차이는2022년Goro train/새prefix285와279zero감사확인이다. 새baseconfig의Goro AOI id선택·v2policy 포함expectedconfigSHA는freshrequest/Rootapproval에다시결속한다. runtime검증271은현재동일공유코드에대한96시험근거이며실inventory·품질성공을대체하지않는다. 286독립리뷰/새37+코드핀·현source/ledger/OS/lock/283실UI마감뒤Root만별도승인실행한다. 현재실행0,request만준비했다.

prepared requestcanonical89d5f20fbe642161abf17f33a41fd77f137a1850e90a87a9d934f1b44bd0ad7d/고론2022 center c755a6b48e9e/최대1batch16. 284고정새source9b580및새proposal1cb1bb…7ace5·prior60원순서보존을소비한다. 기준/예산/원본모델split/oldpending예약/187archive보존·가드우회0. 시작만으로성과를더하지않고실종료/정산/최대16단1bounded감사후실확보·나지기여를계산한다.

## 20:57 실제시작후속

20:57:02.858/supervisor38848/collector4060/session77798. Goro2022 centerc755a6b48e9e 최대1batch16/request89d5f20fbe642161abf17f33a41fd77f137a1850e90a87a9d934f1b44bd0ad7d/expectedconfig7e797bac47ebf683a9320bd63f741f85232c1bf375be9f6c8c06767ae0616709/approval9788aec4820a77f7518d57b32e685c00915106a09937094e97e488d478d5e9cb/39핀·wrapper66fe2ed5b76ed53342ce7cb84617cc500a3bb54c03ece64e65b65249fdee80ed. 286독립리뷰c66df8e34cf6a3d48e6a848effe8e4be3f249ece3f6eb58d6f86dceadf835599/추가차단없음·279waitAST동일/연도·prefix·제로감사참조변경뿐.20:57:23 toolbox_review OSprocess/lock있음/stdout비어있음/terminal없음→freshpreflight만확정/workerHTTP성과미확정. Root추가collector금지·toolbox_review 단일종료정산/OSlock관측·신규최대16감사준비소유/Root별GO전native0. 0patch면native0좁은감사·>0만단1신규native·그동안원본hold. 1364gap15/잔여1869043250·source9b580/ledger3e8d7는시작전값으로현재원장다시확인/성과미리추가금지.


위는285실제시작관측이며원준비당시실행0기록은보존한다.


## 실제 종료와 신규16개 독립 bounded native 감사

상태는 **VERIFIED_REAL — 이번 신규16개 실제 파일·배열·출처·정산 검사**다. 수집기는2026-10-18 21:03:10 KST 종료0/365.828초이며 신규16패치·12적격을 보고했다. 독립 관측에서 collector4060·supervisor38848 종료와 lock 해제를 확인한 뒤, Root 원본 고정 및 별도 GO를 받아 새16개만 정확히 한 번 감사했다. 원래 자료 전체 native 재검사·HTTP·추가 수집·재시도·원장/lock/profile/pointer 변경은0이다.

### 실제 품질과 나지 성과

기존165 제품 helper의 단1회 검사는15.376초에 끝났으며, 새 image/label/quality48래스터와4개 batch 문서의52개 SHA를 재확인했다. 16개 모두256×256·6밴드 영상과 label·quality의 CRS/affine/shape가 정합하고 주내 픽셀65,536개로100%였다. 실제 유효 픽셀 비율은52.522278~99.478149%이며12개가80% 유효·95% 주내 기준을 통과했다. 나머지4개의 유효율은52.522278%,68.101501%,53.617859%,79.457092%로80% 미달이다. 최종 품질 기준을 완화하지 않았다. 최대 클래스 비중90% 초과 여부는 제품의 별도 진단이며 이를 이번80/95 적격 판정과 혼동하지 않는다.

실제2022-07-20T02:14:01.024000Z 장면 S2A_MSIL2A_20220720T021401_R060_T51NVA_20240705T031025를 선택했다. ID 끝의2024 처리 시각을 관측연도2024로 오인하지 않으며, STAC 관측시각·행 연도·동년 참조라벨2022 결속을 검사했다. source grid는EPSG:32651,1024×1024,6밴드,10/-10m,회전0이다. 고정 raw B02 실제배열이 source 첫밴드와 완전히 같고, 16개 최종 패치의 affine·window·첫밴드가 해당 B02 부분영역과 일치했다.

동년 raw Esri 라벨을 nearest 방식으로 실제1024 목표 B02 grid에 정렬한 나지(class8) 실픽셀은0이다. source quality mask 적용 후0, 최종 label/주경계·전체밴드 유효지원 mask 후0, 적격12개에 포함되는 나지0 및 나지256픽셀 이상 기여패치0이다. 최종 행의 sample_class_coverage 값은165 helper가 실제 label histogram을 재계수해 정확히 일치함을 검증했다. source quality만의 mask와 최종 주경계·라벨지원·전체밴드 mask는 서로 다르다. 이번0은1024 목표범위와16개 최종 패치의 실제값이며, 확대2048 라벨 전체·고론탈로 전체에 나지가 없다는 주장이 아니다.

### 선택과 출처 검사의 범위

저장 metadata 요약은20입력·20개 AOI 포함·제외0·선택 풀5다. request/source SHA 결속, 인덱스·cloud rank 완전성, 개수 및 URL 미포함과 실제 선택 STAC bbox의 AOI 포함을 검사했다. 이번 실행에서는 새 메타데이터 필터의 제외 성과가 없었다. 원문20개를 원격 재요청하거나 모두 독립 재생한 것은 아니며, metadata bbox 포함을 실제 COG 기하 증명으로 대체하지 않았다.

저장 SCL 예비후보 기록은35.006714%,34.973526%로 앞선2개가65% 미달, 세 번째가86.117172%로 통과했다. 이 예비율은 최종10m 패치 유효율과 구별한다. 추적21개 고정 참조 파일 SHA를 확인했으며 이 중16개 patch image는 제품52개 검사와 중복이다. 따라서52+21을 고유73개 파일이라고 보고하지 않는다. 새 patch leaf의48개 tif가 신규16행의 image/label/quality 참조와 정확히 같아 신규 미등재 래스터0을 확인했다.

### 보존·정산·현재 수량

이전 source 고정사본의1731행 prefix와 기존 historical_noneligible_patches가 정확히 유지됐다. 원래 pending2행의 상태·예약/계상액·config SHA를 정확히 보존했으며 합계136,314,880바이트다. 이 금액은 이미 new_charged_bytes에 포함된 사용액으로 별도 재차감하지 않는다. 새 batch는 실제 settled, 최종화 시도·정산·발행 각각1회다. COG23,396,352바이트와 metadata362,711바이트의 합23,759,063바이트가 worker·window-state·원장에 일치하고, 잔여 예산은1,845,284,187바이트다.

등록행은1731→1747, 적격1364→1376, 주·연도 셀 부족은15→11이다. 이번 고론탈로2022의 부족4개는 해소됐지만, 추가12적격이 모두 셀 부족12 감소를 뜻하지는 않는다. 실물1748은 수집기 사전 inventory1732와 신규16의 합으로 관측 범위를 명시하며 전체 실물 재스캔은 하지 않았다. 원래 등록행과 실물 총량은 서로 다르다.

감사 전후 source SHA `9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7`(68,220,381바이트)와 ledger SHA `4a4f4a47b522b9497b944ac00b29d2368a977c1a4eb6dfe972a34959fcc68722`가 안정적이었다. 기존165의 명시128MiB source cap 범위에서 읽었으며64MiB 제한을 임의 상향하지 않았다. 새 candidate QA·receipt·게시·프로파일·API/UI 반영은 이 감사가 수행하지 않았고 Root의 별도 후속 근거가 필요하다. 학습 준비 false·독립 정확도 미검증은 유지된다.

근거: evidence/integration/deficit285-native-go-root-20261018.json(SHA61727b9a58468fbd77ffe2168a8e9ff6da8399192c6682001627558b2402b9f0), deficit285-native-runner-root-20261018.py(SHA479dff23370e2db3fd58918e456fc9b263ad614afd3b69baa1f252a66011a4cb), deficit285-native-root-20261018.json(SHA194affdac6f8838875251bdb8c6cb2807cc3492015b3b655ba71ae040ba8c455) 및 해당 log/stderr. 제품 helper 호출1회·오류0으로 완료했으며 결과를 덮어쓴 재실행은 없다.
