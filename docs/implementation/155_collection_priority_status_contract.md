# 최신 수집 목표·품질 현황 API 계약

기준: 2026-10-18. 구현은 `backend/app/collection_priority_status.py`이며 기존 `GET /api/data/collection-status`의 `collection_targets` 필드로 연결한다. 조회는 수집·학습·등록을 실행하지 않는다.

## 수치의 의미

현재 원본 aggregate의 원바이트 SHA와 `quality_status` 저장 선언을 함께 제공한다. 물리·적격·부적격 수, 고정 split, 6주×2020~2025 적격 수를 재집계한다. 1차 적격 목표1200과 주×연도당28 계획 바닥의 부족량을 각각 계산한다. 한 셀의 초과분을 다른 셀의 부족에서 차감하지 않는다. 전체 목표1000~3000, 수집 정지 충분성1200, 지역 균형 계획28은 서로 다른 지표다.

`class_quality`는 원본 manifest의 참조라벨 히스토그램을 집계한다. ESRI 원분류8 나지의 split별 픽셀/비율/256픽셀 이상 기여 패치와 동일 scene의 split 교차 목록을 제공한다. 이 필드는 native 파일 재검사나 독립 정답 검증을 수행하지 않는다. 누출 제거 후보의 최신 QA와 원본 재고를 혼동하지 않는다.

## 필드·오류와 품질 기준

`available=false`는 누락·빈 목록·미지원 지역/연도·잘못된 split·비정상 히스토그램 등으로 현재 수치를 계산하지 못한 상태다. 0개 완료나 학습 준비로 표시하지 않는다. 성공은 `available=true`, 원본SHA, `count_basis=manifest_quality_status`, 집계·행·품질 기준을 포함한다. `native_raster_reverified`, `learning_ready`, `scientific_accuracy_validated`는 이 조회에서 항상 false다.

최종 패치 기준은 유효율80%·해당 주 내부95%이며 필수클래스는 split별 비율0.5%·기여패치5개(각256픽셀 이상)·절대픽셀256 이상·최대참조클래스90%다. 클래스 균형·누출·공간성·동년성·보정/출처 검증은 별도 학습 gate에서 계속 적용한다. ESRI는 약한 참조이며 기관/현장 정답 승인을 뜻하지 않는다.

## 검증·UI 인계

집중 및 기존 collection-status 관련13개 시험이1.105초에 통과했다. 물리/적격 분리, 초과분 상쇄 방지, scene 누출·나지 기여 분리, 미확인 입력 차단을 검증했다. 추가 수집 우선순위·pending 관련을 포함한27개가2.313초에 통과했다. 묶음은 중복되므로 합산하지 않는다. 근거는 `evidence/integration/priority-status-tests-20261018.log`, `priority-collection-root-tests-20261018.log`다.

web_ui 담당에게 위 계약을 인계했다. 기존 CollectionStatus와 ModelReview에서 원본과 후보를 분리해 연결하며 [154 UI 문서](154_collection_progress_ui.md)에 frontend 시험과 실제 서버·브라우저 반영을 기록한다. 이 문서 초안 시점에는 서버 재적용·브라우저 검증이 대기 상태다.

## 후속 적용·고정 후보 계약

로컬 API8002를 PID8564로 재적용했고 `/api/health`200과 catalog14행 SHA 보존을 확인했다. 기존 token-unset loopback 개발 모드를 유지했으며 인증코드·token·사용자 설정은 변경하지 않았다. helper가 처음 `/health`를 요청한404 이력은 남겼고 올바른 기존 경로로 검증했다. 근거: `evidence/integration/priority-status-api-restored-20261018.json`.

최상위 `candidate_quality`는 명시 `data/first-group-training-priority/latest-candidate.json` receipt만 읽는다. 최신 파일 glob이나 원본 값으로 후보 수치를 대체하지 않는다. 고정 source/candidate/QA3개 파일 SHA, QA의 실제 split개수·차단개수, 빈 scene교차목록을 대조하며 부족하거나 변조됐으면 `available=false`다. `source_matches_current_manifest`로 추가 수집분 포함 여부를 구분한다. 파일 지문 일치는 독립 정확도·운영 등록 승인이 아니며 이 조회는 학습을 승인하지 않는다.

후보 receipt QA 불일치·변조·현재수집과 다른 cohort의 표시를 포함한 최종 관련14개 시험이1.002초, 우선수집·pending을 함께 확인한30개가1.901초에 통과했다. 초기13/27시험 이력도 그대로 보존한다. 첫 우선수집 결과는1432물리/1141적격·cell부족132, 나지추가14픽셀이며 나지 차단해소는 아니다. 실행 중 이후 값은 조회한 manifest SHA와 함께 해석한다. 근거: `priority-status-tests-final-20261018.log`, `priority-collection-root-tests-final-20261018.log`, `priority-collection-final-20261018.json`.

## 2026-10-18 10:44 KST — 152–157 검증 마감과 후속 수집 지속

이 항목은 아래의 초기 진행 기록을 갱신한다. 완료된 3회·6batch에서 신규64물리/42적격/나지 선언162픽셀을 확보했다. 최신 완료 관측은1464물리/1164적격/300부적격,train681/val233/test250,1200목표 부족36·셀당28 부족109다. 최초151 부족은 주·연도 셀별 합계이며151개 셀이 아니다. 기존1400행·이후1432행 canonical내용과 pending2 전액136314880B를 보존했다. 총 신규계상87636806B, 기존4GiB 한도 잔여2254269438B다. 2차 동자바2025 두 건은 COG 범위 오류 실패이며 정산을 수집성공으로 계산하지 않는다. 3차32행은 실제래스터·SHA·품질을 별도 검증해23적격/나지148픽셀을 확인했다.

153 고정1400원본의 새후보는 반텐 동일장면16행을 제외해1384행/1106적격(639/217/250)이다. 실제QA239.188초·4335파일 SHA 확인·교차scene/sourcegroup/imageSHA 누출0을 검증했다. 나지4차단은 남아 학습미준비·독립정확도미검증이다. 이후42개 적격이 이 후보에 포함됐다고 표시하지 않는다.159는 별도1432원본을 고정하여 첫19개 적격을 포함한 다음 후보 실제QA 진행중이며 UI후보 pointer는 최종검증 전 교체하지 않는다.

web_ui 실제 브라우저 응답01:41:01.686168Z에서1464/1164/300·목표36/셀109를 확인했다. 별도1106후보의 source불일치·차단4·미준비 경고, 콘솔오류0·가로넘침0·소스7SHA 동일이다. API8002 PID36400에 실제적용했고 catalog14행 SHA와 기존개발인증모드를 보존했다. 조회15.8384658초는 단일로컬관측이며 지연SLA가 아니다. 오래된 manifest는 기존native증거 재해시를 생략하되 미준비 상태를 유지한다. 관련backend48PASS5.326초, 격리된76949기준+소유7프런트 파일288PASS36.4999934초·120모듈build32.33초다. 초기fixture누락실패 로그를 보존했으며 공동Toolbox123모듈build와 구분한다.

157 나지256표적은 로컬반텐2020/val 약한참조2411픽셀·inside1.0·1526개기존영상/SHA/기하 양성겹침0을 검증했으나 execution_supported=false다. pending/rawsupport footprint,scene veto/sharedclaim,실제선택B02 정렬,배타출력이 아직미연결이다. 실제표적Sentinel 수집이나 나지차단 해소로 표현하지 않는다. 다음 집행가드160은 대기열이며 별도 에이전트 실행을 확인하지 못했다.

4차는 반텐2025 g01/g02 정확2건을 계획SHA4268eb34bcdb78d6c9efdc08b1c6020eaf0ad2f5ce8fb5e9bfe179dfd2f1d496로 검증해 PID22020 시작했다. 아직완료관측 전이며 새예산/기존pending환불/중복수집은 하지 않는다. 기존2worker·2초간격·최초429공유중단·3000상한·고정split·80%유효/95%주내 품질을 유지한다. 나지 기준은 split별0.5%·기여5패치(각256픽셀이상)·절대256픽셀이상·최대클래스90%다. 수집재고는 선언집계, 검증후보는 고정nativeQA, 운영등록승인은 별개다.

관련설계/구현/API/사용법/시험근거/인계와 이해자료14개를 같은단위로 갱신한다. 전체프로젝트는 미완료이며 geoai-2 ACTIVE10분과 실제수집/159QA 실행상태를 구분한다. 다른채팅 Toolbox/App/PlatformShell 및159 WIP는 이번152–157 Git대상에서 제외한다. 실행중로그는 변경가능하므로 마감시점 복사본만 고정증거로 취급한다.

근거: evidence/integration/priority-collection-round3-final-20261018.json,priority-collection-independent-round3-20261018.json,priority-ml-20261018-final-verification.json,collection-progress-ui-final1464-browser-20261018.json,priority-root-related-final-20261018.log,priority-frontend-isolated-tests-20261018.log,priority-frontend-isolated-build-20261018.log,priority-collection-round4-launch-20261018.json.



### 159 후속 후보 QA 완료 — 2026-10-18 10:48 KST

PLANNED→VERIFIED_REAL(고정 원본의 파일/래스터 검사 범위):1432행 시점 원본의 새후보는 반텐16행을 제외해1416행/1125적격(train658/val217/test250)이다. sourceQA164.672초·candidateQA216.0초·별도4435파일 SHA10.328초 검사에서 불일치0·source identity 교차분할0을 확인했다. 나지1432/209/1025픽셀·기여0/0/0·차단4·학습미준비/독립정확도미검증은 유지된다. 부가 connectivity 진단은1001820쌍이 기존100만cap을 넘어 NOT_CAPTURED_BUDGET이며 가드를 완화하지 않았다. 최신1464 원본의 나머지23적격은 포함하지 않는다. UI pointer는 아직검증된153의1106후보를 표시한다.1125후보의 API/UI 승계는 다음작업이며 실제화면 반영완료로 표현하지 않는다. 근거:docs/implementation/159_next_collection_candidate_qa.md,evidence/integration/priority-ml-next-20261018-summary.json,priority-ml-next-20261018-final-verification.json.


## 2026-10-18 10:54 KST — 4차 수집 완료·159 후보 UI 승계

앞선1464/1164 관측 이후4차 반텐2025 g01/g02가 정상종료했다. 신규32물리/32적격/나지391픽셀로1496물리/1196적격/300부적격,train681/val265/test250이다. 전체1200 부족4·주연도 셀당28 부족97이다. 최초요청대비96물리/74적격을 추가했고 셀 부족151→97,나지추가553픽셀이다. 4차32개 실제래스터·유효/주내·클래스·SHA 및source/worker/원장 정합성을12.7664229초에 재검증했고 기존1464행과pending2전액136314880B를보존했다. 신규총계상2085380105B/한도잔여2209587191B,429false/실행lock정상해제다. 원본검증분할 나지는209→600픽셀,기여0→1개로 개선됐으나0.5%·기여5패치 기준은미달이다. 1200개충족과학습준비는별개다.

159의1432행고정source→누출16행제외후1416행/1125적격 후보는실제QA·4435파일SHA검증후명시receipt로승계했다. 기존153후보/receipt와교체전pointer원바이트를보존하고,새receipt3핀검산·readyfalse/차단4 검산후pointer원바이트가변하지않았는지비교하고os.replace로교체했다. DatasetRegistry/모델/원장/기존분할/학습상태전이0이다. 부가connectivity NOT_CAPTURED_BUDGET 한계는유지한다. 최신1496원본의55적격(23+32)은새1125후보QA범위밖이며sourceSHA불일치경고를유지한다.

실제API8002/프런트5174 소스변경·재시작 없이기존GET·명시수동새로조회로승계됐다. 브라우저응답01:52:31.145480Z에서원본1196(681/265/250)·후보1125(658/217/250)·차단4/미준비·시점불일치·원본검증나지600/기여1을확인했다. console warning/error0,가로넘침0이며분석/학습/배포/등록버튼을실행하지않았다. 전체페이지스크린샷1회timeout은브라우저캡처한계로기록하고실제viewport PNG/DOM/JSON을보존한다. 제품소스변경없으므로기존48관련backend·288격리frontend·build120근거를유지하며새전체회귀통과를주장하지않는다.

5차동자바2021 g02/g03은plan fe20a0b67e5b6215d3f0e4814a07e48b9645a2fb6ba90893b4c3049cd62b8ade,wrapperPID33756으로시작했고완료는미확인이다. 기존budget/2worker/2초/429중단/3000상한/고정split/품질정책을유지한다. 같은collector중복실행금지.157표적은계속집행차단이며160로컬자산영역검사작업은다른채팅소유기록과중복하지않는다. geoai-2 ACTIVE10분보고지속,전체개발미완료다.

근거:evidence/integration/priority-collection-round4-final-20261018.json,priority-collection-independent-round4-20261018.json,priority-collection-round5-launch-20261018.json,priority-ml-next-ui-promote-20261018.py,priority-ml-next-ui-receipt-20261018.json,priority-ml-next-ui-round4-20261018.json,priority-ml-next-ui-round4-20261018.png 및docs/implementation/159_next_collection_candidate_qa.md.
