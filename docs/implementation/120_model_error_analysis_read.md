# 120 — 고정 모델 오류 분석의 인증 유지 읽기 API

## 쉬운 설명과 구현 범위

112가 완료 학습의 고정 best epoch validation/test 혼동행렬에서 내보낸 JSON·클래스 CSV·오분류쌍 CSV를 기존 모델의 버전·체크포인트·학습 보고서 SHA에 묶어 읽는다. 새로 평가·추론·학습하거나 누락된 파일을 생성하지 않는다. Draft 모델도 과거 오류 분석을 읽을 수 있으며 조회 성공은 운영 승인·독립 정답 인증이 아니다. 실제 데이터셋의 새로운 정확도 측정은 수행하지 않았다.

신규 `backend/app/model_error_analysis_api.py`의 factory는 `create_model_error_analysis_router(get_store)`다. 호출자가 제공한 Store의 `get('models', id)`만 사용하며 main을 import하거나 Store를 생성·쓰기하지 않는다. Root가 기존 main에 import/include 두 문장으로 연결한다. 전체 앱의 기존 인증 정책을 상속한다. 토큰 설정 여부와 RBAC 정책을 이 모듈에서 새로 만들지 않는다.

## 요청·응답 계약

- `POST /v1/models/error-analysis`: 읽기 전용 조회.
- `POST /v1/models/error-analysis/assets/{index}`: 같은 pins로 재검증한 복사 바이트 다운로드.
- 두 요청의 exact3 JSON: `{schema_version:1, model_ref:{id,version,sha256}, training_report_sha256}`. body 최대16KiB, 중복 키·비유한 숫자·잘못된 UTF-8·추가 키를 거부한다.
- id는 기존 실험 등록과 같은 `[A-Za-z0-9_-]{1,100}`이다. version은96의 1..256 문자 검사와 alias 거부를 그대로 사용한다. Unicode와 유효한 패딩을 보존하며 정규화하지 않는다. SHA는 lowercase hex64다.

조회 성공200의 exact10 필드는 `schema_version:1`, `scope:'PINNED_TRAINING_ERROR_ANALYSIS_READ_ONLY'`, `status`, `issue`, `model_ref`, `training_report_sha256`, `analysis`, `artifacts`, `scientific_accuracy_validated:false`, `standard_gmais_result:false`다.

`AVAILABLE`이면 issue는 null, analysis는112 결과에서 `artifacts`와 `csv_formula_escape`를 제외한 본문이다. `by_split.val/test`의 클래스별 FP/FN·precision/recall·분모 부재 null·오분류쌍을 그대로 제공한다. `UNAVAILABLE`이면 analysis는 null, artifacts는 빈 목록이고 issue는 `MODEL_VERSION_DECLARATION_UNAVAILABLE` 또는 `ERROR_ANALYSIS_UNAVAILABLE`다. legacy 선언·파일이 없다고 가짜0 통계를 채우지 않는다. unavailable download는404다.

artifacts는 정확히 다음 순서의 `{index,filename,sha256,bytes}` 세 개다. index 경로는0/1/2만 허용하고 caller가 파일 경로를 제출하지 않는다.

| index | filename | 최대 크기 |
|---|---|---|
| 0 | error-analysis.json | 8MiB |
| 1 | error-analysis-classes.csv | 8MiB |
| 2 | error-analysis-confusions.csv | 8MiB |

attachment는 고정 filename·JSON/CSV MIME·`Cache-Control:no-store`·`X-Content-Type-Options:nosniff`를 사용한다. CSV formula escape를 포함한 원본 바이트를 보존한다.

오류는 `{error:{code,message:'고정 모델 오류 분석을 읽을 수 없습니다.',retryable:false}}` 고정 envelope다. `INVALID_REQUEST`400, `REQUEST_TOO_LARGE`413, `NOT_FOUND`404, `PIN_CONFLICT`409, `STORED_OUTPUT_CHANGED`503, `RESOURCE_UNAVAILABLE`503만 노출한다. 기존 전역 인증의401은 기존 `{detail}` 계약을 따른다. 예외 원문·경로·파일 내용은 오류에 넣지 않는다.

## 검증과 I/O 경계

v1은 `models/{id}/best.pt`, 같은 디렉터리 `report.json` 및 위 세 파일만 지원한다. 다른 basename/namespace는 자동 추정하거나 역채우지 않는다. Windows 상대 경로의 역슬래시는 비교에만 정규화한다. 경로 탈출뿐 아니라 내부 symlink/junction과 lexical/resolve 불일치도 거부한다.

저장 record id와 checkpoint/training SHA가 요청과 일치해야 한다. exact5 버전 선언은100의 `CONSISTENT_UNVERIFIED`여야 하며 원형 version을 비교한다. 이 선언은 caller metadata이며 기관의 인증·불변 resolver가 아니다. 실제 checkpoint를 최대64MiB 읽어 SHA만 검사하며 torch로 로드하지 않는다. 학습 보고서는 최대8MiB·SHA·strict finite JSON을 검사한다.

보고서 completed/model_id/checkpoint SHA·정확 int selected_epoch·선택 history validation의 typed canonical 동치를 확인한다. 기존112 순수 `confusion_error_analysis`로 저장된 val/test 혼동행렬을 재집계하여 `report.error_analysis` 본문과 비교한다. 새 예측이나 독립 평가가 아니다. reference_kind는 원문128자 이하 제어문자 없는 문자열이며 출처 권위로 승격하지 않는다. JSON artifact도 검산 본문과 일치해야 한다. bool과 int는 canonical JSON 바이트가 달라 혼동하지 않는다.

세 artifact의 고정 경로·size·SHA를 각각 확인하고 복사 바이트만 반환한다. 읽기 누적이 상한을 넘으면 즉시 중단하며 읽기 전후 size/mtime/inode/resolve를 확인한다. 파일 읽기·SHA·검산·Store 접근은 worker thread에서 수행하여 async event loop를 막지 않는다. body 파싱은16KiB로 제한된다.

여러 파일과 Store를 묶은 원자 snapshot/잠금은 제공하지 않는다. 파일별 변조·재바인딩 검사는 있으나 동시 writer와의 모든 TOCTOU를 제거하지는 않는다. CSV는 저장 SHA/size와 고정 filename을 확인하며 통계에서 CSV를 새로 직렬화하여 검증하지 않는다. caller가 모든 metadata와 해시를 함께 위조한 경우 기관 출처를 인증하지 못한다.112의 세 파일 쓰기 자체도 비원자적이며 이 API가 그 쓰기 정책을 바꾸지 않는다. 다운로드 때 같은 pins로 다시 검사하므로 앞선 조회 후 변화는 실패할 수 있다.

## 시험 근거

`tests/test_model_error_analysis_api.py`는 TempStore·known9×9 confusion·임의 checkpoint bytes와 실제112 writer로 파일을 생성한다. 모델을 로드하거나 학습하지 않는다. 기존 main의 authorized 함수 AST만 격리 앱에서 사용하며 운영 main import와 운영 Store 접촉은0이다.

- 집중 최종 **14 PASS / 2.695초 / exit0**: `evidence/integration/model-error-analysis-api-focused-final-20261018.log`.
- 관련 **48 PASS / 7.665초 / exit0**: `evidence/integration/model-error-analysis-api-related-20261018.log`. 신규14·112 writer·100 provenance·97 선언 시험을 포함한다. 집중과 중복 합산하지 않는다.
- 최초12 PASS 로그 `model-error-analysis-api-focused-20261018.log`도 보존했다. 이후 동시 reader와 symlink/junction 분류 경계 시험을 추가했다.

실제 CSV escape·세 파일 동일 바이트·nullable 지표·Draft 조회·미확보/무생성·인증401·400/413/404/409/503·각 파일 변조·재바인딩 후 semantic 오염·Windows 경로·상한·8동시 reader·원본 바이트 불변·Store.put0을 확인했다. Windows symlink/junction 생성은 권한 변경 없이 플랫폼 predicate를 주입해 거부 경계를 시험했다. 실제 junction 생성 검증으로 표현하지 않는다.

소스/시험 동결을 Root와 UI 담당에게 전달했다. UI 담당은 exact pins 조회·상태·통계·인증 유지 다운로드/SHA를 별도 화면에 연결한다. Root의 main 배선·독립/전체 회귀·실제 브라우저·보존 검증은 이 집중시험과 구분해 후속 근거로 기록한다. 이해자료 갱신은 Root가 완료 소스·시험 근거를 이해 에이전트에 인계한다. 운영 등록·수집·학습·배포·파일 생성은 모두0이다.

## 최종 통합·독립·브라우저 근거

Root가 main의 import/include 두 문장으로 연결하고 기존 라우트 보존 시험 **24 PASS / 4.333초**를 확인했다. 전체 backend는 **1184건 실행·1183 PASS·기존1 SKIP / 399.529초 / exit0**다. 로그는 `evidence/integration/model-error-read-backend-all-20261018.log`이며 위 집중/관련 묶음과 중복 합산하지 않는다. UI 전체 시험은 **261 PASS**, production build는 **108 modules / 21.85초**다.

별도 임시 Store에서 구성한 완료 보고서·실행 불가능한 임의 checkpoint 바이트와 실제112 writer를 사용해 main 서버를127.0.0.1:8003에 연결했다. 이 checkpoint는 로드하지 않았고 학습·추론을 수행하지 않았다. 자료의 scope는 `TESTED_SYNTHETIC_CONSTRUCTED_TRAINING_REPORT_NO_TRAINING_NOT_EXECUTABLE_CHECKPOINT`다. val은12참조픽셀 중5오분류, test는10중3이며 val의 class7→1 두 픽셀은 precision null·recall0, test class7은 참조/예측 부재로 검산했다. `evidence/integration/model-error-read-browser-fixture-20261018.json`은 이 구성 자료의 요청·응답·보고서·모델 metadata를 담는다. 운영 완료 모델이나 실제 과학 정확도 증거가 아니다.

Root 독립 live HTTP **6건 통과**는 actual main의200 조회·수작업 지표/null·세 다운로드 SHA·409/404·중복 키400·상한413을 확인했다. 근거는 `evidence/integration/model-error-read-independent-20261018.py`, 같은 stem의 `.json` 및 `.log`다. 인증401은 앞선 격리 앱의 실제 authorized AST 시험과 구분한다.

Root 브라우저 최종 `evidence/integration/model-error-read-browser-20261018.json`은 모델 선택·이전으로 이동 후 기존 결과 비표시·JSON 다운로드 SHA 및 기존5174의 pin 미확보 조회 버튼 비활성을 확인했으며 최종 errors0이다. 초기 key 경고는 별도 browser-initial JSON에 보존했고 UI에서 key를 고쳤다. 임시 구성 자료를 이용한 브라우저 동작 확인이지 운영 자료·승인·독립 정답 확보가 아니다.

보존 근거 `evidence/integration/model-error-read-live-integrity-20261018.json`에서 보호141·이전증거974·catalog14가 불변이고 기존 소스270개 중 허용4개 이외 변경0이다. 예약136314880바이트와 원본·원장·lock·분할·모델은 보존했다. 임시 fixture 파일 생성과 운영 파일 쓰기를 구분하며 운영 등록·수집·훈련·배포는0이다. 최종 근거 반영 후 문서를 동결했다.
