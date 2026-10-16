# LCLUC 개발 기록

작성일: 2026-10-15, 후속 실자료 실증: 2026-10-16. 이 문서는 `backend/app/ml/`의 실제 구현과 시험만 기록한다. 사용자의 마스터 개발 명령서를 구현 기준으로 사용했고, U-Net 선정은 사용자 지시의 초기 구현 방식이다. TECH-4가 특정 신경망 구조를 요구한 것으로 해석하지 않는다.

## 1. 실행환경 조사

빈 저장소에서 시작했다. Python 3.11.9, NumPy 설치를 확인했다. PyTorch는 설치되어 있었고, Rasterio와 PyProj는 없어서 다음 명령으로 설치했다.

```powershell
python -m pip install rasterio pyproj
python -c "from backend.app.ml.service import runtime_status; print(runtime_status())"
```

확인 결과: Rasterio 1.4.4, PyProj 3.7.2, PyTorch 2.14.0+cpu. `cuda_available=False`, 실행 장치는 CPU이다. torch는 기본 API import에 강제되지 않고 학습·추론·전문가 평가를 호출할 때 필요하다. 설치 여부는 `runtime_status()`에서 확인한다.

## 2. 공간자료 및 전처리 구현

파일: `raster.py`, `dataset.py`.

- 데이터 루트 외부 경로를 거부한다. 원본 영상을 수정하지 않는다.
- CRS가 없는 래스터를 거부하고, 영상·라벨의 CRS, affine transform, 폭·높이를 비교한다. 불일치는 조용히 수용하지 않는다.
- 명시적 `reproject_to_reference` 유틸리티를 제공한다. 범주형 라벨은 최근린, 연속형 영상은 bilinear를 사용한다. 서비스 prepare 호출이 자동 재투영하지는 않는다.
- 모든 입력 밴드의 NoData 및 NaN/Inf를 제외한다. 밴드 순서와 반사도 scale/offset을 저장한다. Sentinel 계열 예시 기본 scale은 0.0001이며 센서별 정확한 설정은 호출자가 지정한다. Landsat는 제품 메타데이터의 scale/offset을 적용해야 한다.
- 외부 품질 마스크에서 0을 구름·그림자 등 제외 영역으로 취급한다. 자동 구름 탐지 AI는 구현하지 않았다.
- 기본 256×256 패치를 만들고 경계는 0 영상/255 ignore 라벨로 채운다. 시험에서는 16×16도 허용한다. 모두 ignore인 패치는 제외한다.
- 장면의 독립 `group`을 기준으로 70/15/15를 근사한다. 최소 세 그룹을 요구하고 작은 자료에서도 세 분할이 남도록 조정한다. 다른 group 간 동일 원본 SHA256, 동일 scene_id 또는 WGS84로 변환한 경계의 공간 중첩을 거부한다. 같은 장면·인접 타일을 반드시 동일 group과 scene_id로 지정해야 한다. 비중첩 인접 타일의 원본 scene 정보가 누락된 경우에는 자동 판별할 수 없다. 경계 사각형 비교이므로 복잡한 footprint에서는 보수적으로 거부할 수 있다.
- 원본 영상·라벨 SHA256, 출처, 밴드, 정규화, 클래스, seed 및 분할을 manifest에 남기고 manifest 내용 해시로 dataset version을 생성한다.

### 라벨 체계

Dynamic World 공식 확률 밴드 순서는 water, trees, grass, flooded_vegetation, crops, shrub_and_scrub, built, bare, snow_and_ice이다. 내부 코드는 0~8, 제외 픽셀은 255이다. `label_source=dynamic_world`는 해당 순서의 9개 확률 밴드를 요구하며 기본 최대확률 임계값 0.8 미만을 제외한다. 원본 확률 영상을 유지하므로 저신뢰 픽셀을 재검토할 수 있다.

`label_source=worldcover`의 초기 매핑은 다음과 같다. 이는 제안된 통합 분류체계이며 전문가가 확정한 의미적 등가 관계가 아니다.

|WorldCover|통합 클래스|
|---|---|
|10 tree cover|1 trees|
|20 shrubland|5 shrub_and_scrub|
|30 grassland|2 grass|
|40 cropland|4 crops|
|50 built-up|6 built|
|60 bare/sparse|7 bare|
|70 snow/ice|8 snow_and_ice|
|80 permanent water|0 water|
|90 herbaceous wetland|3 flooded_vegetation|
|95 mangroves|1 trees|
|100 moss/lichen|2 grass|

맹그로브 및 moss/lichen 매핑에는 의미 손실이 있다. 두 라벨 출처의 시기·정의 차이가 있으므로 불일치를 오류로 판정하지 않는다. WorldCover/Dynamic World 불일치 검토 목록의 자동 생성은 후속 과제이다. 전문가 라벨은 `label_source=classes`로 이미 통합된 0~8 래스터를 입력한다.

## 3. 실제 모델 학습 및 추론

파일: `network.py`, `service.py`.

실제 PyTorch 연산을 수행하는 작은 2단계 U-Net encoder/decoder와 skip connection을 구현했다. 모델은 9개 클래스를 출력한다. U-Net++는 구현하지 않았으며 요청하면 오류를 반환한다.

CPU/CUDA 자동 선택, seed와 deterministic 알고리즘, batch size, 학습률, Adam/SGD, cross entropy 및 class weights, early stopping, 최적 validation loss checkpoint 저장을 구현했다. CUDA mixed precision 옵션을 제공하지만 현재 CPU 환경이므로 CUDA 실증은 수행하지 않았다. 입력 밴드/scale/offset/patch 크기를 checkpoint 안에 저장한다. 기존 dataset/model/output ID는 덮어쓰지 않는다.

매 epoch train/validation loss와 confusion matrix, OA, precision/recall/F1, class IoU, mean IoU를 기록한다. validation으로 선택한 최적 checkpoint를 다시 로드한 뒤 시험 분할을 평가한다. 부재 클래스 IoU는 null이며 평균에서 제외한다. 지역별·시기별 세분화 지표와 오류지도는 아직 별도 산출하지 않는다.

추론은 전체 영상을 패치로 나누어 CPU로 실행하고 원래 공간참조 및 NoData를 유지한 단일 밴드 분류 GeoTIFF를 기록한다. patch 경계가 존재할 수 있으며 중첩 blending은 후속 과제이다. 신뢰도 보정과 모델 불확실성 추정도 미구현이다.

단일 프로세스의 학습·추론·평가에는 재진입 잠금을 적용해 스레드 작업 큐의 PyTorch 전역 seed 설정 충돌을 방지한다. 다중 프로세스/분산 작업의 모델·데이터 ID 동시 생성은 외부 큐와 저장소의 잠금 관리가 추가로 필요하다.

### 서비스 입력 예시

모든 경로는 `data_root` 내부의 상대 경로이다.

```python
from pathlib import Path
from backend.app.ml.service import prepare_dataset, train_model, infer_raster, analyze_change
root = Path('data').resolve()
prepared = prepare_dataset({
    'dataset_id': 'lcluc_v1', 'patch_size': 256,
    'bands': [1, 2, 3, 4], 'scale': 0.0001,
    'scenes': [
        {'image_path': 'raw/region_a.tif', 'label_path': 'raw/labels_a.tif', 'group': 'region_a'},
        {'image_path': 'raw/region_b.tif', 'label_path': 'raw/labels_b.tif', 'group': 'region_b'},
        {'image_path': 'raw/region_c.tif', 'label_path': 'raw/labels_c.tif', 'group': 'region_c'},
    ],
}, root)
trained = train_model({'dataset_path': prepared['manifest_path'], 'model_id': 'unet_v1', 'epochs': 5}, root)
pred = infer_raster({'image_path': 'raw/t1.tif', 'checkpoint_path': trained['checkpoint_path'], 'output_id': 't1'}, root)
```

위 경로는 인터페이스 설명용이며 실파일이 존재한다는 뜻이 아니다. 실제 시험은 아래 unittest에서 생성한 합성 GeoTIFF를 사용한다.

## 4. 독립 평가 증빙 경로

`evaluate_model`은 `checkpoint_path`, `image_path`, `label_path`, `output_id`, `reference_kind=expert_independent`, `label_provenance`, `reviewer`, `group`을 받는다. 합성 학습 모델을 거부한다. 기존 dataset의 모든 지역 group과 영상·라벨 SHA256 중복을 검사하고 정합한 전문가 라벨과 실제 추론 결과를 비교하여 지표와 `evaluation.json`을 기록한다.

전문가 신원과 라벨 작성 과정의 독립성은 사용자 진술이다. 자동 독립성 인증이 아니다. 영상의 WGS84 경계 중첩도 검사하지만 전문가의 작업 절차나 비중첩 자료의 출처 독립성까지 자동 검증하지 않는다. `independence_basis=user_attestation_with_duplicate_hash_and_group_checks`를 명시한다. 최종 운영 승인은 별도 검토가 필요하다.

## 5. T1/T2 변화 분석

T1/T2 범주형 분류 GeoTIFF의 공간 정합을 검사한다. 어느 시점에서든 NoData 또는 범위 외 클래스이면 통계에서 제외한다. 픽셀 전이 코드는 `from_class * num_classes + to_class`, 출력 NoData는 65535이다. 변화 GeoTIFF, 전이행렬 CSV 및 JSON 보고서를 생성한다.

투영 CRS는 affine 행렬식에 단위 환산 계수를 적용한 격자 면적을 사용한다. 이 방식은 투영 왜곡 영향을 받으므로 면적 보존 투영 선택이 필요하다. 경위도 CRS는 PyProj의 해당 타원체로 각 픽셀 네 모서리의 측지 면적을 계산한다. 회전 affine도 처리한다. changed area, 변화율, 각 클래스 순증감, 유효/제외 픽셀 수를 기록한다. 행정구역 집계는 후속 과제이다.

변화 픽셀만 rasterio polygon화하여 EPSG:4326 `changes.geojson`을 기록한다. feature에는 원래/새 클래스와 전이 코드 및 미검증 변화 품질표시를 담는다. `max_features` 기본/상한은 5,000이며 한도를 넘으면 중단하고 `vector_truncated=true`를 기록한다. GeoJSON이 1MiB 이하면 `geometry` FeatureCollection을 응답에 포함하고, 크면 파일 경로만 제공한다. 전체 면적·통계는 항상 전체 유효 래스터 행렬에서 계산하므로 벡터 제한과 무관하다. 지도용 제한된 벡터를 전체 변화통계로 재계산해서는 안 된다.

## 6. 시험 명령과 실제 결과

```powershell
python -m unittest discover -s tests -p test_ml*.py -v
```

1차: 7개 시험, 31.894초, 모두 PASS. 2차: 7개 시험, 14.132초, 모두 PASS. 후속 WorldCover 및 평가 증빙을 추가한 9개 시험은 14.535초에 PASS. 공간 누출 검사를 보강한 9개 시험은 10.106초에 PASS. 중복/공간중첩 거부 회귀시험을 추가한 10개 시험은 13.058초에 모두 PASS. 최종 실행 결과는 통합 검증 기록에서도 확인한다.

확인 항목: 그룹 20개의 14/3/3 분할 및 재현성, 루트 외부 경로 거부, 정합 불일치 거부, DW 저신뢰 ignore, 기본 256 padding, EPSG:32748의 10m 픽셀 한 개 변화=100m² 및 NoData 제외, EPSG:4326 측지 면적, 알려진 confusion matrix의 OA=.75/mIoU=.6, CPU 2epoch 실제 학습/체크포인트 재로딩/GeoTIFF 추론. 기능시험에 쓰인 자료는 임시 생성된 16×16×3밴드 합성 영상 세 지역이며 실 위성자료가 아니다.

합성 시험 지표는 실제 인도네시아 분류 정확도가 아니다. 독립 시험용 실제 참조자료, 목표 1,000~3,000개 실제 패치, 계절별 검증, 센서 간 검증이 아직 필요하다. 현재 학습 보고서 상태는 Draft이며 임의의 성능 목표를 달성했다고 표시하지 않는다.

최초 STAC 접근은 DNS 오류 `gaierror 11001`이 발생하고 외부 접근 승인 요청이 거절되어 중단했다. 이후 사용자가 허용한 정상 승인 경로에서는 Planetary Computer DNS/HTTPS 접속과 실제 Sentinel-2 B04 64×64 창 다운로드를 성공했다. 이 단일 밴드 연결시험 자료만 있던 시점에는 다중밴드·대응라벨·3지역 학습 세트가 없어 학습 완료로 표시하지 않았다. 이후 2021년 세 지역 다중밴드/WorldCover 자료가 확보되어 6-2절의 실제 학습까지 진행했다. 제한을 우회하지 않았으며 수집 모듈의 최신 검증 기록을 함께 확인한다.

## 6-1. 연차별 동일 AOI 분석 추가

`analyze_timeseries` 입력은 `checkpoint_path`, `images=[{'year':2020,'image_path':'...'}, ...]`, `output_id`이다. 2~100개의 명시적 관측 입력을 받으며 연도 정수·중복·오름차순을 검사한다. 모든 연차 영상의 CRS/transform/크기를 먼저 확인한 후 각 연도에 동일 checkpoint로 실제 추론한다. 인접연도와 최초 기준연도 대비 변화분석을 수행하며 공통 연도 쌍은 한 번만 계산한다. 빠진 연도를 보간하거나 합성하지 않는다.

`timeseries.json`에 연도별 분류 경로, 전이 GeoTIFF/CSV 및 행렬, 원본 영상 SHA256/출처/라이선스/관측일, checkpoint 해시, dataset version, 합성 여부와 품질 한계를 저장한다. 반환 키는 `classifications`, `adjacent_pairs`, `adjacent_observation_pairs`, `baseline_pairs`, `changes`, `provenance`, `quality`, `report_path`이다. `adjacent_pairs`는 정확히 1년 차이인 실제 연속연도만 의미한다. `adjacent_observation_pairs`는 가용 관측 간 쌍이므로 2020/2022 입력이면 2년 간격이며 연차변화로 표시하지 않는다. `quality.missing_years`와 `annual_coverage_complete`에 누락 연도를 명시한다. 입력 관측일이 없으면 unknown/null 상태로 유지한다. 동일 AOI의 여러 연차를 모델 학습에 사용하는 경우 동일 group에 배치해 시간축 누출도 방지해야 한다. 구름 제거는 입력 NoData/외부 마스크를 전제로 하고 자동 구름판독은 수행하지 않는다.

연차 기능을 포함한 11개 ML 시험을 실행하여 26.086초에 모두 통과했다. 합성 2020/2021/2022 영상의 실제 추론·3개 고유 전이쌍 산출, 연도 중복/역순 거부, 공간 불일치 거부를 검증했다. 초기 import 시 torch 가용성 확인에는 `find_spec`을 사용해 전체 시험 발견 단계의 불필요한 torch 초기화 비용을 줄였다.

연차 누락(2020/2022 입력 시 2021 누락 명시), 변화 GeoJSON 100m² 단일 feature, 벡터 한도 1개에서도 전체 래스터 200m² 통계를 유지하는 회귀시험을 포함한 최종 12개 시험은 23.415초에 모두 통과했다. 학습 manifest 파일 검사를 torch 초기화 앞에 배치해 존재하지 않는 입력은 즉시 실패하도록 했다.

## 6-2. 최초 실제 위성자료 CPU 기능실험 — 2026-10-16

실제 수집 완료 후 `data/baseline2021/annual-window-report.json`을 입력으로 최초 학습을 실행했다. 입력은 Planetary Computer 공개 Sentinel-2 L2A 2021년 영상의 서로 다른 세 지역 B02/B03/B04 256×256 창과 ESA WorldCover 2021 v200 정합 라벨이다. 전체 장면을 내려받은 것이 아니며 창 단위 패치 세 개뿐이다. 출처·라이선스·파일 SHA256 및 원래 CRS/해상도는 `data/baseline2021/manifests/`와 데이터셋 manifest에 남겼다. WorldCover 라이선스 기록은 CC-BY-4.0이며 기존 수집기 `license_verified=false` 상태를 과학적/법적 검토 완료로 바꾸지 않았다.

```powershell
python scripts/run_baseline.py --manifest data/baseline2021/annual-window-report.json --run-id baseline2021_cpu_v1 --epochs 3 --scale 0.0001 --offset 0
```

한국시간 2026-10-16 09:40:00~09:40:56, 실제 경과 56.379초에 데이터셋 생성·CPU 3epoch 학습·최적 checkpoint 재로딩·세 지역 분류 GeoTIFF 생성까지 완료했다. 모든 산출물 `synthetic=false`이며 인위적 가상 위성영상으로 대체하지 않았다.

|지역|실제 관측일|분할|WC/SCL 유효 라벨 비율|
|---|---|---|---|
|남술라웨시 후보|2021-09-26|train 1패치|98.2239%|
|중부자바 후보|2021-09-30|validation 1패치|99.6399%|
|서자바 후보|2021-09-21|test 1패치|95.6299%|

seed 42, dataset version `717e5e1cce1a6d56`. 서자바 시험 참조 유효 픽셀 62,672개에서 **WorldCover 의사라벨 일치 OA=0.0134988512(약 1.35%), mean IoU=0.0026997702(약 0.27%)**였다. validation loss는 2.2770653→2.2749081→2.2736199였다. 이 낮은 결과를 그대로 남겼으며 실제 독립 지상정답 정확도나 운영 가능 성능으로 해석하지 않는다. 총 세 패치이므로 목표 1,000~3,000개를 충족하지 않는다.

실제 산출물:

- `data/results/baseline2021_cpu_v1/baseline-run.json`: 전체 실행·품질·분할·지표·추론 경로.
- `data/datasets/baseline2021_cpu_v1_dataset/manifest.json`: 원본 해시·지역·라벨·정규화 및 분할.
- `data/models/baseline2021_cpu_v1_model/best.pt`, `report.json`: 실제 가중치와 epoch별 학습/검증 및 시험 지표.
- `data/results/baseline2021_cpu_v1/predictions/{0,1,2}/classification.tif`: 서자바/중부자바/남술라웨시 분류지도.

정규화는 원본 DN×0.0001, offset 0이라는 명시적 수치 설정을 사용했다. 추가 STAC 메타데이터 검색은 승인 거절로 수행되지 않았고 제품의 반사도 scale/offset 원문을 확정하지 못했으므로 물리 반사도 정확도를 주장하지 않는다. 원본 장면 ID는 각각 2021년 당시 생성된 처리제품이지만 이것만으로 방사보정 검증을 대체하지 않는다.

별도로 허용된 서자바 원본 B04 전체 파일 수집의 `data/raw-reference/reference-report.json`에서는 `s2:processing_baseline=03.00` 및 N0300 제품 세대가 확인됐다. 그러나 명시적 raster:bands scale/offset 값은 없었고 나머지 두 지역 원문은 이 검토에서 확보하지 못했다. 따라서 방사보정 미검증 한계를 유지한다.

수집기의 SCL 구름·그림자 제외는 WorldCover 라벨의 0 NoData에 반영되어 학습/시험 지표에서 제외된다. 원본 RGB에는 구름 품질 마스크가 별도 저장되지 않아 이번 추론은 각각 65,536픽셀 모두를 분류했다. 따라서 해당 분류지도는 구름 잔존 가능성을 포함한다. 동일 연도 세 지역 자료만 있으므로 실제 T1/T2 변화나 2020~2025 연차 성능을 이 실험으로 주장하지 않는다.

재사용 CLI는 입력 부족 시에도 `baseline-run.json`에 실패 원인을 기록하고 종료한다. 선행 `--run-id baseline2021_preflight --check-only`는 대응 라벨이 한 지역뿐이던 시점에 최소 세 지역 미달로 정상 실패했다. 없는 자료를 생성하지 않았다. CLI 회귀시험 `python -m unittest discover -s tests -p test_ml_baseline_cli.py -v`는 두 개 모두 통과했다(1.349초).

### 실제 결과의 카탈로그 등록과 품질 마스크 후속

```powershell
python scripts/run_baseline.py --register-report data/results/baseline2021_cpu_v1/baseline-run.json
```

재학습 없이 기존 실제 산출물을 검증하고 카탈로그에 수동 등록했다. 데이터셋 ID는 `baseline2021_cpu_v1_dataset`, 모델 ID는 `baseline2021_cpu_v1_model`, 분석 ID는 `baseline2021_cpu_v1_prediction_0`부터 `_2`까지이다. 모델은 **Draft, independent_evaluation=false**로 유지하며 epoch 학습기록은 `training_history`에 보존했다. `registration.json`에 보고서 해시·수동 등록 시점·모델 체크포인트 해시를 기록한다. 초기 실행 보고서에는 체크포인트 해시가 없었으므로 이를 원본 체크섬 대조라고 주장하지 않고 등록 시 계산한 목록 해시로 명시했다. 실제 가중치 SHA256은 `ad74f5cf5ab4bfd42bffd94b2fa399bf28f3527bc8e9f424d6a9d5339b12cd6c`이다. 이후 신규 실행은 학습 완료 직후 체크포인트 해시도 저장한다.

등록기에서 `Store(..., recover_jobs=False)`를 사용하므로 실행 중인 다른 작업을 재시작 장애로 바꾸지 않는다. 기존 ID 재등록은 거부해 승인 상태와 검토 이력을 덮어쓰지 않는다. 해당 회귀시험을 포함한 CLI 세 개 시험은 1.384초에 모두 통과했다.

후속으로 `infer_raster`의 선택 입력 `quality_mask_path`와 `quality_mask_basis`를 추가했다. 영상과 같은 grid의 외부 이진 마스크에서 0 또는 마스크 NoData를 분류 결과 255로 제외한다. 연차 `images`에도 같은 필드를 지원하며 마스크의 경로·해시·용도를 provenance에 남긴다. 이 기능 추가는 기존 실분류 세 개가 SCL 적용 자료로 소급 변경되었다는 뜻이 아니다. 실제 SCL 기반 파생 마스크를 확보하거나 명시적으로 참조범위 마스크임을 표시한 후 새로운 output ID로 재추론해야 한다.

품질 마스크 처리 및 수동 등록 검사를 포함한 ML/CLI 총 15개 시험은 35.343초에 모두 통과했다.

후속 실제 학습 계약 감사(`docs/13_학습설정_감사.md`, `data/audits/training-contract.json`)에서 세 분류 모두 grass 코드 2만 100% 예측하는 붕괴를 확인했다. 따라서 기존 OA는 시험 WC의 grass 비율과 같은 의사라벨 일치도이며 과학적 실정확도가 아니다. First Group 여섯 주 신규 자료도 2021 창 여섯 개/80% 품질 적격 세 개 수준이므로 재학습하지 않았다. 시기 적격 1,000개 이상, 클래스·지역 대표성, 정규화·라벨 QA 및 전문가 독립 holdout 조건을 충족한 후에만 다음 학습을 검토한다.

## 7. 다음 개발 순서

### 신규 실자료 학습 경로 변경

최초 세 패치 baseline 이후 새 실자료 학습은 `scripts/run_experiment.py`와 ML readiness gate를 통해서만 수행한다. 기존 소규모 CLI를 그대로 다시 실행해 실제 재학습하는 경로는 거부하고, 과거 결과의 등록/조회만 유지한다. 준비 계약·밴드/정규화 근거·연도·품질·1,000개 이상 충분성·분할별 클래스 조건과 출력 붕괴 검사를 실행 코드에 연결했다. 실제 API 학습도 같은 gate를 검사한다. 자세한 스키마와 미충족 사유는 문서11·13 및 `data/first-group/training-readiness.json`에 있다. 기존 실제 checkpoint와 보고서는 변경하지 않았다.

1. 공급자별 제품 scale/offset·밴드·품질마스크를 고정하고 이미 확보한 세 지역을 넘어 실자료 표본 확대.
2. WorldCover/DW 시간·정의 차이를 검토하고 전문가 참조 분류체계 확정.
3. 독립 평가 AOI와 전문가 라벨의 접근권한·라이선스·작성 절차 확보.
4. 실자료 최초 학습·평가, 지역/시기별 지표 및 오류지도 산출.
5. 비교 가능한 U-Net++ 구현 후 동일 분할의 실험 및 MLflow 운영 추적 연계.
6. 행정구역/RDTR 교차 집계, COG 산출 및 대용량 window 처리 최적화.
