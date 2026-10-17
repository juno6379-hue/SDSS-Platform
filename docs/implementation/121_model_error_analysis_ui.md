# 121 — 고정 학습 모델의 val/test 오류 분석 인증 조회 UI

상태: **TESTED_SYNTHETIC / 운영 학습·평가·등록 없음**.112가 보관한 오류 분석을120 읽기 전용 API로 조회한다. 선택 모델별 기본 접힌 패널이며 실제 완료 report/artifact를 새로 만들거나 학습·독립 평가·모델 승인·배포를 수행하지 않는다. 기존 ModelReview의 등록·독립평가·승인·배포 버튼과 자동 readiness 회로는 변경하지 않는다.

## 연결과 고정 참조

새 `ModelErrorAnalysis.tsx`/adapter/client/scoped CSS와 시험을 추가했다. 기존 `ModelReview.tsx`는 import 한 곳과 선택 모델 안의 sibling 한 곳만 연결한다. 기존 provenance의 key는 그대로 두고 신규 패널은 `errors:`+model ID로 구별한다. 상단 Workspace/App/api.ts와 이전 Workflow/지도/전이행렬은 변경하지 않는다.

저장 metadata에서 모델 ID·명시 version declaration·checkpoint SHA·training_report_sha256가 모두 정합해야 요청 pin을 만들 수 있다. ID는120의 ASCII `[A-Za-z0-9_-]{1,100}`, version은96과 같은1..256 Unicode code point/제어문자·단독 surrogate·공백뿐인 값/strip·lower 후 latest/current 거부 규칙을 적용한다. 패딩/Unicode 버전은 전송할 때 원형을 보존한다. 선언 exact5/schema1/source=CALLER_EXPLICIT_REGISTRATION·부모 두 SHA 일치와 optional model_version 정합을 검사한다. dataset_version/latest/임의 경로에서 추정하거나 자동 채우지 않는다.

pin이 없으면 **고정 참조 미확보 / 실제 artifact 존재 미확인**을 표시하고 조회를 비활성화한다. pin이 있어도 조회 전 파일 존재·SHA는 미검증이다. AVAILABLE 후에는 해당 서버 읽기 시점의 바이트 검증 응답이며 이후 현재 파일 상태나 기관 권위를 보장하지 않는다고 설명한다. caller 버전 선언이나 Draft 조회 가능을 인증·승인으로 승격하지 않는다.

## API·응답 계약

버튼 클릭만 POST `/v1/models/error-analysis`를 호출한다. 요청 exact3은 `{schema_version:1,model_ref:{id,version,sha256},training_report_sha256}`다. 모델 선택·패널 열기·pin 변경에서 자동 조회하지 않는다. wrapper는 exact10/schema1/scope=PINNED_TRAINING_ERROR_ANALYSIS_READ_ONLY·요청 ref/학습 보고서 SHA 결합·scientific_accuracy_validated=false·standard_gmais_result=false를 검사한다.

- AVAILABLE: issue=null,112 exact analysis body와 고정 artifact3개가 있어야 한다. selected_epoch는 양의 정수, model ID/checkpoint SHA는 요청과 일치하며 reference_kind·val/test·test_used_for_epoch_selection=false·training_policy_changed=false·과학 false를 검사한다.
- UNAVAILABLE: 고정 issue MODEL_VERSION_DECLARATION_UNAVAILABLE 또는 ERROR_ANALYSIS_UNAVAILABLE, analysis=null·artifacts=[]만 허용한다. **미제공은 FP/FN0·측정 성공이 아니다.** 파일 생성/평가로 대체하지 않는다.
- 오류:400/413/404/409/503의 고정 code/status·exact error envelope/retryable=false와 기존401/403을 안전하게 처리한다. native message·경로·원문 예외를 표시하지 않고 자동 재시도하지 않는다.

val/test 각 split은9개 클래스·최대72개 비대각 오분류쌍·고정 scope/행렬 축·과학/공간지도 false를 검사한다. TP를 대각선, 오분류쌍을 비대각선에 놓아 참조/예측 합계·FN/FP·전체/오분류 픽셀·비율·평가 가능 flags·관측 상태·미관측 ID 목록을 교차 검산한다. pairs 순서는 픽셀 내림차순·같으면 참조/예측 ID 오름차순이며 중복·희소배열·잘못된 index/이름을 거부한다. val/test 클래스 이름 순서도 같아야 한다. 비율 검산은1e-12 허용오차이고 픽셀 수는 safe integer다. 이 검산은 통계 일관성이지 독립 과학 정확도 인증이 아니다.

## 화면에서 읽는 방법

오류 분석은 **행=참조 라벨 / 열=예측 클래스**다.119의 **행=이전 시점 / 열=이후 시점** 전이행렬과 다르다. 선택 best epoch·원래 reference_kind·val/test 참조/오분류 픽셀 수, 클래스별 참조·예측·TP·FN·FP·precision/recall·누락/오포함률, 참조→예측 오분류쌍과 해당 참조 클래스 내 비율을 표시한다. 면적·시점 변화량으로 바꾸지 않는다.

- 참조·예측 모두 없음: 비율은 null/미관측·평가 불가다.
- 참조 없음/예측 있음: recall·누락률은 null이고 precision/오포함률은 분모가 있는 측정이다.
- 참조 있음/예측 없음: precision·오포함률은 null이고 recall/누락률은 분모가 있는 측정이다.
- 참조·예측 모두 관측: 실제 분모로 계산한0%도 유효 측정일 수 있다.

test는 validation으로 best epoch를 고정한 뒤의 최종 집계이며 epoch 선택에 사용하지 않았다는112 정책을 설명한다. weak label 일치도는 독립 정확도가 아니다. 클래스 이름은 실제 원문을 React text로 표시하며 임의 분류명을 넣지 않는다. 가로 표는 caption·scope header·키보드 초점/내부 스크롤을 사용하고 공통 SVG 스타일을 유지한다.

## 인증 다운로드와 늦은 응답

index0/1/2는 각각 error-analysis.json/error-analysis-classes.csv/error-analysis-confusions.csv다. 버튼은 **같은 exact pin body로 POST `/v1/models/error-analysis/assets/{index}`**하며 기존 `geoai_token` 탭 세션 Bearer를 유지한다. 임의 URL/원문 파일 경로로 이동하지 않는다. 파일명·index·SHA·positive bytes/각8MiB 상한을 검사하고 stream의 선언/누적 크기 초과를 cancel한다. 실제 크기·SHA가 metadata와 같은 복사 바이트만 Blob으로 저장한다. CSV의112 formula escaping 바이트를 보존하며 다운로드 중 내용을 재작성하지 않는다.

동기 pending guard가 중복 클릭을 막고 선택 모델·pin·route/popstate/hashchange/unmount·표시 중단에서 세대와 이전 결과를 폐기한다. 다운로드도 stream/해시 뒤 유효 세대에서만 클릭한다. 표시 폐기/취소는 이미 수행한 서버 읽기 롤백이 아니다. payload 상한은 전체 브라우저 RSS/HTTP chunk·timeout 보장이 아니며 reader.cancel은 best effort다.

## 시험·초기 보완·한계

신규11 PASS/4.141초(`evidence/integration/model-error-analysis-ui-related-final2-20261018.log`)다. 실제112 writer와 인증120 TestClient/TempStore의 AVAILABLE body·CSV3종을 사용했으며 모델 checkpoint는 opaque fixture bytes로 실행하지 않았다. Python112 helper의4개 관측 상태·null 분모를 교차 시험하고 pin/Unicode 패딩·오염/정수/rate/pair/flags·안전 오류·동기 중복/세대/이동/unmount·Bearer POST·크기/SHA·stale/cancel/짧은 파일 미저장을 확인했다. 운영 데이터·학습·실제 전문가 평가·브라우저 동작 증거와 구분한다.

Root 최초 실제 브라우저에서 AVAILABLE 뒤에도 조회 전 미검증 문구가 남는 시제 모순을 발견해 조회 전/읽기 성공 시점 설명을 구분했다. 또한 기존 provenance와 같은 sibling key를 신규 패널에 사용해 React duplicate-key 경고가 발생한 원인을 확인했다. 신규 key만 errors: prefix로 바꾸고 원래 provenance key/기존 flow는 보존했다. 초기 경고는 `model-error-read-browser-initial-20261018.json`에 보존하며 최종 수정 결과와 구분한다. 최종 전체 frontend는261 PASS/26.266초(`model-error-analysis-ui-tests-final-20261018.log`), production build는108 modules/21.85초/exit0(`model-error-analysis-ui-build-final-20261018.log`)다. 기존 큰 bundle 경고는 남는다. 초기 통과 로그와 최종 key 보강 기준 로그를 합산하지 않는다.

## Root 실제 브라우저·독립·보존 근거

`evidence/integration/model-error-read-browser-20261018.json`은 별도 UI5175/API8003의 구성 report로 AVAILABLE를 읽어 validation 참조12/오분류5·test 참조10/오분류3을 확인한다. water precision60%·recall75%, validation bare 참조2/예측0에서 precision=null/recall0%, test bare 참조·예측 모두0에서 precision/recall 모두null을 표시했다. 구성 report·실행할 수 없는 opaque checkpoint이며 학습/추론·실제 독립평가를 수행한 자료가 아니다.

모델 선택 변경·뒤로 가기는 이전 결과를 지웠고 최종 새 탭 console 오류는0건이었다. 초기 classes CSV 다운로드1616B·SHA `2514d7da7b856861a58d5efc31a9247015d67dff98d94ea51c96f4926e31dea9`, 최종 JSON 다운로드12276B·SHA `38e044870676bf5e32386e8cf81ff18c917fd4238e1de79aac468159e1801def`가 metadata와 일치했다. 기존 실행 중UI5174에도 새 패널이 반영됐으며 legacy 모델은 고정 참조가 없어 조회 disabled/실제 artifact 미확인으로 표시하고 console 오류0건을 확인했다. 화면은 `model-error-read-browser-final-20261018.png`와 `model-error-read-legacy-ui-20261018.png`다.

Root 독립 live HTTP6시나리오는 실제 main 앱 응답과 writer fixture 동치·손계산 분모/null·3개 다운로드 바이트/SHA·409 pin 충돌·404 모델/index·400 duplicate/413 body limit를 확인했다. `model-error-read-independent-20261018.py/.json/.log`를 따른다. 이것은 인증·일관성 읽기 계약 시험이며 운영 API 요청·학습·추론·checkpoint load는0이다. API 단위시험/브라우저/Node 시험 수와 중복 합산하지 않는다.

실제 브라우저의 Bearer 세션·강제 지연·표시 중단 중 취소·변조 asset·모바일은 재현하지 않았다. 인증·세대·크기/SHA·취소 음성 근거는 별도 API/TestClient·Node mock 시험과 구분한다. legacy 모델의 저장 report는 있지만112 오류 분석 필드와 버전/학습 보고서 SHA pin이 없어 이 UI가 과거 성능을 새로 만들어 보이지 않는다.

`model-error-read-live-integrity-20261018.json`은 보호141·이전 증거974개 불변, 기존 소스270개 중 허용4개 외 변경0, catalog14행 canonical 불변과 예약136314880B 보존을 확인한다. 이번 API 연결을 위한 main import/include와 기존 route 기대 시험2개는 Root 소유 변경이며 UI 담당은 ModelReview 두 연결 지점만 수정했다. 운영 수집·학습·등록·배포·Workflow dispatch0이고 실제 모델은 Draft를 유지한다. backend 전체 회귀의 최종 결과는120/Root 통합 로그 `model-error-read-backend-all-20261018.log`를 따르며 이 UI 문서의 frontend 건수와 합산하지 않는다. 전체 프로젝트 완료나 실제 과학 인수로 표현하지 않는다.
