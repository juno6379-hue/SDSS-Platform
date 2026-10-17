# 2026-10-17 ML 재개 검증

`ml_pipeline`은 인계서 P1에 따라 기존 모델·원본 manifest·수집 원장·기존 `training-readiness.json`을 보존하고 별도 QA를 수행했다. 실제 신규 학습의 `--execute`는 사용하지 않았다. 합성 회귀시험의 임시 학습은 기존 모델이나 실자료 학습과 분리된다.

## 구현 수정

- `backend/app/ml/readiness.py`: Esri 연간 파일의 익년 1월 1일 종료와 동년 12월 31일 종료 표기를 모두 수용한다. 실제 URL basename 전체를 검사하므로 다른 연도·부분 기간·위장 확장자·쿼리/상위 경로의 날짜로 통과하지 않는다. 기존 제품 버전/동년 라벨 조건은 유지한다.
- 고정 지역 holdout 사이에 같은 원본 scene 또는 공간 중첩이 발견되면 차단하되, 원본 component 병합으로 validation 통계가 test로 옮겨가는 진단 오류를 수정했다. 선언된 4/1/1 분할을 보존하며 `SHARED_SOURCE_CROSSES_FIXED_SPLIT`을 유지한다. 충돌을 해결하거나 학습을 승인한 변경이 아니다.
- 수집 manifest가 기록한 `patch_sha256.image/label/quality`를 실제 파일의 SHA-256과 대조한다. 기록이 있는 행의 누락/불일치를 차단하며, 구형 manifest의 기록 없는 행은 기존처럼 새 해시를 고정한다.
- 수집기의 주 경계 포함률 95% 조건을 ML 충분성 계수에도 적용한다. 기존 ML QA는 품질 마스크만 검사하여 경계 포함률 미달 9개를 더 집계했다. 포함률이 명시된 행은 기준 미달일 때 클래스·패치·고유 위치에 집계하지 않는다. 과거처럼 포함률 필드가 없는 manifest의 처리 방식을 유지하며, 이 경우 공식 경계 검증이 새로 수행됐다는 뜻은 아니다.
- `tests/test_ml_readiness.py`: 두 날짜 관례와 잘못된 기간/URL, Esri 실제 QA 경로, 충돌 시 고정 holdout 통계 보존을 회귀 검증한다.

## 실행 검증

실제 환경 스크립트는 `scripts/test.ps1`이다. `.runtime/scripts/test.ps1`은 없다. Python 경로는 해당 스크립트와 같이 `.runtime;backend`로 설정했다.

- readiness: **20 PASS, 9.720초**.
- ML pipeline: **17 PASS, 55.829초**. 임시 합성 raster의 실제 CPU train/checkpoint/resume/infer 계약을 포함한다.
- 위 시험은 코드 계약 검증이며 독립 현장 정확도나 운영 승인 증거가 아니다. rasterio/Affine의 기존 PendingDeprecationWarning은 있었으며 실패는 없었다.

## 최신 실자료 QA

입력은 `data/first-group-training-esri-v1/annual-window-report.json`, 계획은 `data/first-group/experiment-esri-v003-2020-2025.json`이다. 고정 입력 SHA-256은 `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`다. 원본 manifest 1,384행의 메타데이터 표시는 적격 1,111/부적격 273이며 아래 정식 QA와 구분한다.

최종 별도 출력은 `data/first-group/readiness-resume-20261017.json`이다. 평가시각은 **2026-10-17 08:49:23 KST**, 출력 SHA-256은 `6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db`다. `evidence/integration/ml-readiness-resume-20261017.json`에 입력/출력/구현 파일 SHA, 시험, 충돌 scene, 경계 제외 9개 경로를 기록했다. 입력 manifest SHA는 QA 시작 전과 종료 후 동일하다.

| 검사 | 최종 결과 |
|---|---|
| 파일/출처/정합 | 4,335개 고유 파일 해시 고정. 수집 기록의 영상/라벨/품질 SHA, 6밴드, 원본 제품 정규화 XML 근거, 라벨/외부 mask 정합 검사. `SCENE_QA_ERROR`, 날짜/밴드/정규화 blocker 없음 |
| 범위/수량 | 36/36 주·연도, 총 **1,111 적격**, train/val/test **628/233/250**. 수집기 적격 집계와 일치 |
| 학습 주 고유 위치 | South Sulawesi56/Gorontalo64/Southeast Sulawesi53/East Java44, 최소32 통과. val Banten58/test West Java59 |
| 원본 scene 분할 | **실패**. `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`가 Banten val 16행·West Java test 12행에 걸침. 이 중 적격은16/9 |
| bare 클래스(train) | 1,418픽셀, **0.003532%**, 기여 패치0 |
| bare 클래스(val) | 209픽셀, **0.001390%**, 기여 패치0 |
| bare 클래스(test) | 1,025픽셀, **0.006307%**, 기여 패치0 |
| 최종 gate | **BLOCKED / ready_for_training=false**, blocker5개. `prepared_payload=null`, 신규 학습·추론·모델 등록 미실행 |

bare 기준은 split별 비율≥0.5%, 256픽셀 이상 기여 패치≥5이며 모든 split이 미달한다. validation bare는 별도 최소256픽셀에도 미달한다. 5개 blocker는 원본 scene 분할1 + split별 bare imbalance3 + validation bare 픽셀 부족1이다. 수량/공간 바닥이 통과한 사실이 클래스·누출 gate를 대체하지 않는다.

최초 중간 QA의 1,120개는 경계 포함률 조건을 누락한 계수였다. valid≥0.8이지만 주 경계 포함률<0.95인 East Java3/Banten6을 제외하면 1,111개로 수집기와 일치한다. 고정 split 통계가 val0/test489로 표시됐던 최초 초안은 위 최종 출력으로 대체됐으며 인용하지 않는다. 원본 행을 삭제하거나 split을 바꾸지 않았다.

## 다음 실제 blocker 해결 순서

1. data owner/root가 고정 holdout의 원본 scene 충돌을 해소하는 **새 버전의 대표 부분집합/manifest**를 설계한다. 원본을 덮어쓰거나 충돌 blocker를 해제하지 않는다. 경계 인접 주를 나눈 고정 split과 원본 scene 독립성을 함께 만족해야 한다.
2. 실제 bare 관측을 split별로 확보하고 비율·기여 패치·공간/연도 대표성을 다시 평가한다. 없는 클래스를 복제하거나 다른 의미의 라벨로 대체하지 않는다.
3. 안정된 새 manifest의 전체 readiness가 통과한 경우에만 별도 실험을 계획한다. Esri 의사라벨 일치도는 현장 정확도가 아니며, 독립 현장 검증·전문가 승인·배포 인수는 별도 미충족이다.

주 경계 포함률은 수집 manifest의 근거를 사용했으며 공식 AOI 승인이나 새 경계 재계산을 수행한 증거가 아니다. 기존 모델과 기본 `training-readiness.json`은 변경하지 않았다.
