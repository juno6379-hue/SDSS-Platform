# 112. LCLUC 실제 아키텍처 확인과 완료 모델 오류 분석 연결

상태: **구현·TESTED_SYNTHETIC 완료 / 최신 실자료 학습 BLOCKED**. 새 오류 분석은 향후 완료 학습의 report에 직접 연결했다. 운영 자료로 학습·추론·QA를 실행하거나 기존 원본·분할·체크포인트를 변경하지 않았다. 이 단위가 6개 모델 또는 독립 과학 정확도 인증의 완료를 뜻하지 않는다.

## 실제 모델은 U-Net++가 아닌 TinyUNet이다

[network.py](../../backend/app/ml/network.py)의 `TinyUNet`은 encoder 8→16, bottleneck32의 두 pooling 단계와 bilinear upsample·단순 skip concatenation decoder(48→16, 24→8), 1×1 클래스 head를 사용한다. nested dense skip grid나 deep-supervision head는 없다. [service.py](../../backend/app/ml/service.py)는 `architecture='tiny_unet'`만 허용하고 U-Net++를 명시적으로 미구현 오류로 거부한다.

[아키텍처 증거](../../evidence/integration/lcluc-ml-architecture-20261018.json)는 실제 기존 `data/models/baseline2021_cpu_v1_model/best.pt`를 **`torch.load(map_location='cpu', weights_only=True)`**로 읽은 결과다. arbitrary pickle 실행·안전 global 추가·파일 재저장을 하지 않았다. 체크포인트 130145B의 SHA는 `ad74f5cf5ab4bfd42bffd94b2fa399bf28f3527bc8e9f424d6a9d5339b12cd6c`, architecture tiny_unet·epoch3, 첫 convolution `[8,3,3,3]`, head `[9,8,1,1]`, 파라미터29833개이며 현재 TinyUNet(channels=3)의 모든 state shape와 일치한다. 읽기 전후 SHA는 같다.

이 기존 모델은 RGB `[1,2,3]`·WorldCover 약한 라벨 실험이다. [현재 First Group 계획](../../data/first-group/experiment-plan.json)의 B02/B03/B04/B08/B11/B12 **6밴드 후보를 학습한 모델이 아니다**. 기존 report의 independent/scientific 필드 부재를 false가 저장된 것으로 바꾸어 표현하지 않는다. 클래스 이름·선택 validation·checkpoint SHA를 기록하지 않은 구형 report도 있으며 새 필드를 역채우지 않았다.

## 이번에 실제 학습 pipeline에 연결한 것

[새 error_analysis.py](../../backend/app/ml/error_analysis.py)는 순수 `confusion_error_analysis()`와 `write_training_error_analysis()`를 제공한다. `train_model`이 최저 validation loss로 best checkpoint를 고정하고 해당 모델의 최종 test 평가를 끝낸 뒤, 완료 report를 저장하기 전에 exporter를 호출한다. 테스트 집계를 epoch 선택·튜닝·class weight 계산으로 보내지 않는다. 기존 loss·train-only 가중치·고정 분할·seed·early stop·resume·prediction collapse gate와 `infer_raster`/`analyze_timeseries`/`evaluate_model`은 바꾸지 않았다.

행=참조, 열=예측의 9×9 혼동행렬에서 다음을 생성한다.

- 클래스별 참조/예측 픽셀, TP·FN·FP, recall/precision, omission/commission rate.
- 참조 미관측, 참조는 있으나 한 번도 예측하지 않은 클래스, 예측만 있는 클래스를 별도 상태로 표시.
- 대각선을 제외한 참조→예측 오분류쌍과 픽셀·참조 클래스 내 비율. 픽셀 수 내림차순, 동률은 클래스 index 순으로 고정.

분모가 없으면 recall/precision을 **null·evaluable false**로 표시한다. 지원하지 않은 클래스를 정확도0 또는 완벽한 분류로 오인하지 않도록 기존 metrics 값과 별도의 설명 계약을 둔다. 실제 공간 오류 지도·독립 라벨 평가·과학 인증은 생성하지 않는다.

완료 모델 디렉터리에 새 artifact 세 개를 쓰고 `report.error_analysis.artifacts`에 DATA 상대 경로·SHA256·바이트 수를 연결한다.

| artifact | 내용 |
|---|---|
| `error-analysis.json` | 고정 best epoch·참조 종류·checkpoint SHA·val/test 상세·미검증 범위 |
| `error-analysis-classes.csv` | val/test 각9행의 클래스 오류와 관측 가능 여부 |
| `error-analysis-confusions.csv` | val/test의 실제 비대각 오분류쌍; 오류0이면 header만 |

paused/미완료 모델에서는 생성하지 않는다. 완료 report의 선택 epoch와 history validation이 일치해야 한다. 모든 target을 먼저 검사하고 DATA 아래 모델 디렉터리만 쓰며 symlink·기존 디렉터리 artifact·다른 내용의 파일은 거부한다. 동일 바이트 재호출만 재사용하고 신규 파일은 exclusive로 쓴 뒤 바이트를 확인한다. CSV의 클래스명은 공백 이후 `= + - @`로 시작하면 apostrophe를 붙여 spreadsheet formula 실행을 방지하며 원문 이름은 JSON에 보존한다. 쓰기 중 예외가 나면 부분 새 artifact를 자동 삭제하지 않는다. 세 파일의 OS 원자 commit이나 외부 동시 쓰기를 배제하는 lock을 구현한 것은 아니다.

## 1000~3000 유효 패치와 남은 ML gate

현재 기본 readiness는 유효 패치 최소1000·최대3000, split600/100/100, 6밴드·patch256·품질0.8·주 경계0.95·고정 4/1/1 분할과 class별 정책을 유지한다. 저장 원본 적격1111과 후보1095(628/217/250)를 구분한다. [73 후보 QA](73_candidate_readiness_qa.md)는 차단4를 유지하고, [76](76_bare_class_requirements.md)·[108](108_bare_patch_feasibility.md)은 class7 기여0·비율 부족 및 val 절대 픽셀 부족을 설명한다. 집계 필요량 차이1071/255를 미래 수집량으로 사용하지 않는다.

새 오류 분석은 이 gate를 우회하거나 데이터 수를 늘리지 않는다. 적격한 새 데이터·라벨을 승인된 신규 버전으로 확보→동일 정책 QA 통과→재현 가능한 학습→독립 참조 평가·분야 검토→승인의 순서가 남아 있다. 독립 라벨이 미확보이므로 WorldCover/Esri 일치도와 독립 실정확도를 분리한다.

## 검증과 호환 범위

[신규 시험](../../tests/test_ml_error_analysis.py) **12 PASS /0.494초**: 알려진 FP/FN·축 방향·지원0/null·참조는 있으나 미예측·오분류쌍 합계/정렬·빈/완벽 행렬의 인증false·형식/계수 거부·순수 무IO·TempDir export SHA/CSV·선택epoch·paused·인젝션·같은 내용 재사용/충돌 보존·루트 이탈·기존 나머지 service 함수 AST 불변을 검증했다.

관련 **29 PASS /43.790초**는 신규12와 기존 ML pipeline17의 묶음이다. 기존 16×16 합성 raster·임시 디렉터리의 작은 CPU train/checkpoint/resume/infer 시험을 포함한다. 운영 실자료 학습이 아니며 실제 과학 정확도 증거가 아니다. 신규12를29에 중복 합산하지 않는다.

- [집중 로그](../../evidence/integration/lcluc-ml-error-analysis-focused-20261018.log)
- [관련 로그](../../evidence/integration/lcluc-ml-error-analysis-related-20261018.log)
- [변경 전 service 원문](../../evidence/integration/lcluc-ml-original-service-20261018.py)
- [기존 저장 report 오류 관측](../../evidence/integration/lcluc-ml-existing-report-error-analysis-20261018.json): 저장 test confusion만 읽는 별도 근거. 영상/라벨·추론/평가를 다시 실행하지 않으며 구형 report에 없는 이름은 class index로 표시한다.

## API·UI 인계

새 endpoint는 없다. 기존 학습 완료 응답/모델 report에 선택적 `error_analysis` 객체와 세 export 경로가 추가되며 미완료 응답과 기존 모델 기록은 그대로다. 기존 모델 원본 JSON 화면에는 향후 새 등록 모델의 필드가 보일 수 있으나, 구조화된 오류 표·다운로드 버튼은 이번에 추가하지 않았다. 별도 UI 연결 시 DATA 상대 경로를 직접 정적 노출하지 않고 기존 인증 자산 다운로드 계약·404/권한·미완료/구형 null 상태를 검증해야 한다. 클래스 비율·불일치·약한 라벨 범위와 독립 인증false를 함께 표시한다.

완료 소스·시험·아키텍처와 한계를 Root에 전달한다. 이해자료와 공통 인계/운영 원장은 Root 소유이며 이 담당은 data/main/gmais/공통 문서를 수정하지 않았다.
