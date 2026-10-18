# 159후보 UI승계와4차수집완료 인계

## 2026-10-18 10:54 KST — 4차 수집 완료·159 후보 UI 승계

앞선1464/1164 관측 이후4차 반텐2025 g01/g02가 정상종료했다. 신규32물리/32적격/나지391픽셀로1496물리/1196적격/300부적격,train681/val265/test250이다. 전체1200 부족4·주연도 셀당28 부족97이다. 최초요청대비96물리/74적격을 추가했고 셀 부족151→97,나지추가553픽셀이다. 4차32개 실제래스터·유효/주내·클래스·SHA 및source/worker/원장 정합성을12.7664229초에 재검증했고 기존1464행과pending2전액136314880B를보존했다. 신규총계상2085380105B/한도잔여2209587191B,429false/실행lock정상해제다. 원본검증분할 나지는209→600픽셀,기여0→1개로 개선됐으나0.5%·기여5패치 기준은미달이다. 1200개충족과학습준비는별개다.

159의1432행고정source→누출16행제외후1416행/1125적격 후보는실제QA·4435파일SHA검증후명시receipt로승계했다. 기존153후보/receipt와교체전pointer원바이트를보존하고,새receipt3핀검산·readyfalse/차단4 검산후pointer원바이트가변하지않았는지비교하고os.replace로교체했다. DatasetRegistry/모델/원장/기존분할/학습상태전이0이다. 부가connectivity NOT_CAPTURED_BUDGET 한계는유지한다. 최신1496원본의55적격(23+32)은새1125후보QA범위밖이며sourceSHA불일치경고를유지한다.

실제API8002/프런트5174 소스변경·재시작 없이기존GET·명시수동새로조회로승계됐다. 브라우저응답01:52:31.145480Z에서원본1196(681/265/250)·후보1125(658/217/250)·차단4/미준비·시점불일치·원본검증나지600/기여1을확인했다. console warning/error0,가로넘침0이며분석/학습/배포/등록버튼을실행하지않았다. 전체페이지스크린샷1회timeout은브라우저캡처한계로기록하고실제viewport PNG/DOM/JSON을보존한다. 제품소스변경없으므로기존48관련backend·288격리frontend·build120근거를유지하며새전체회귀통과를주장하지않는다.

5차동자바2021 g02/g03은plan fe20a0b67e5b6215d3f0e4814a07e48b9645a2fb6ba90893b4c3049cd62b8ade,wrapperPID33756으로시작했고완료는미확인이다. 기존budget/2worker/2초/429중단/3000상한/고정split/품질정책을유지한다. 같은collector중복실행금지.157표적은계속집행차단이며160로컬자산영역검사작업은다른채팅소유기록과중복하지않는다. geoai-2 ACTIVE10분보고지속,전체개발미완료다.

근거:evidence/integration/priority-collection-round4-final-20261018.json,priority-collection-independent-round4-20261018.json,priority-collection-round5-launch-20261018.json,priority-ml-next-ui-promote-20261018.py,priority-ml-next-ui-receipt-20261018.json,priority-ml-next-ui-round4-20261018.json,priority-ml-next-ui-round4-20261018.png 및docs/implementation/159_next_collection_candidate_qa.md.


최종 감사 산출물 정정: 최초4차 감사의 패치별 실제검사 assertion은32적격/391나지였지만 JSON요약에 이전회차23/148상수가 남아 마감검산에서 차단됐다. 최초JSON/script를 summary-initial로 보존하고 요약을 실제 observations에서 계산하도록 수정했다. 재검사는10.2128606초/exit0이며32/391을 확인했다. 수집 원본·원장·품질판정 변경은0이다. 이는 제품수집 오류가 아닌 감사 helper의요약 오류다. 근거:evidence/integration/priority-collection-independent-round4-summary-initial-20261018.json,priority-collection-independent-round4-20261018.json,priority-collection-independent-round4-final-20261018.log.


## 2026-10-18 11:00 KST — 5차 완료: 적격1212·셀 부족85, 6차 시작

최신 완료 관측은1512물리/1212적격/300부적격, 학습697·검증265·시험250이다. 최초 요청의1122적격보다90개 늘었고 셀당28 계획 부족은151→85개다. 전체1200 수량 목표 부족은0이지만 나지 균형·독립 검증·학습 승인은 미충족이다. 주별 부족은 South Sulawesi0/Gorontalo17/Southeast Sulawesi45/East Java18/Banten5/West Java0이다.

5차 동자바2021 g02는 COG 범위 오류로0개, g03은16개 모두 적격이었다. 별도9.4286137초 검사로 새16개 실제 배열·품질·SHA, 원본1496행과 기존pending2전액 보존을 확인했다. 감사helper 최초 실행은 worker가 정상 종료했어도 scene이 failed인 경우를 처리하지 못해 멈췄고, scene-level 실패 분기를 추가해 재검사했다. 최초 실패 로그도 보존했다. 수집 제품 코드·품질 가드 변경은0이며 실패 batch를 성과에 포함하지 않는다. 누적 신규계상2106330497B/4GiB 한도 잔여2188636799B,429false/5차 lock 정상해제다. 이후6차 예약·전송으로 잔여량은 바뀔 수 있다.

원본 나지 픽셀은 학습1586/검증600/시험1025,256픽셀 이상 기여 패치는0/1/0이다. 전체 요청 이후 나지 선언559픽셀을 추가했지만 각 split0.5%·기여5개 기준은 미달이다. UI응답01:58:33.471802Z에서 원본1212/후보1125·차단4/미준비·고정1432 source와 현재원본 SHA불일치를 실제 확인했다. 후보에 이후71개 적격을 포함했다고 표시하지 않는다. 콘솔오류/경고0·가로넘침0, 학습/등록/배포 실행0이다.

6차 동자바2024 g01/g02를 plan228a9c72695da9cc4b367f9632456601614d2bc0bac7788a9a6200bedb17ea01, wrapperPID8688로 시작했다. 완료·추가수량은 미확인이다. 단일coordinator·2worker·2초간격·최초429공유중단·기존예산·3000상한·고정split·품질기준을 유지한다. 수량1200을 넘었어도 기존 balanced_coverage의 나지/클래스 gate가 미충족이므로 자동 학습이나 승인으로 전이하지 않는다. 157 표적 집행은 계속 BLOCKED이며 다른채팅160 자산기하 검사 소유와 중복하지 않는다.10분 보고 geoai-2 ACTIVE와 실제 수집·학습 상태를 구분한다.

근거:evidence/integration/priority-collection-round5-final-20261018.json,priority-collection-independent-round5-20261018.json,priority-collection-independent-round5-initial-20261018.log,priority-ml-next-ui-round5-20261018.json,priority-ml-next-ui-round5-20261018.png,priority-collection-round6-launch-20261018.json. 관련 구현/API/UI/인계와 이해자료14개 및161 이해노트를 함께 갱신했다.
