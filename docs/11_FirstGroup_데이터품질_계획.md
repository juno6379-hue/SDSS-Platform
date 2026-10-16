# First Group 데이터 품질·학습 준비 감사

작성: 2026-10-16. 기준은 사용자가 새로 지정한 First Group 여섯 주와 2020~2025 연차이다. 본 문서는 자료 재고와 품질을 감사하며 새 모델의 정확도를 주장하지 않는다.

## 1. 대상 확정과 기존 실험의 범위

|고정 ID|주 이름|현지 이름|
|---|---|---|
|south_sulawesi|South Sulawesi|Sulawesi Selatan|
|gorontalo|Gorontalo|Gorontalo|
|southeast_sulawesi|Southeast Sulawesi|Sulawesi Tenggara|
|banten|Banten|Banten|
|west_java|West Java|Jawa Barat|
|east_java|East Java|Jawa Timur|

기대 재고는 **6개 주×6개 연도=36개 주·연도 조합**이다. `configs/first-group.collection.json`은 이 여섯 주만 포함해야 한다. 기존 서자바·중부자바·남술라웨시 세 지역 CPU baseline에는 First Group이 아닌 Central Java가 포함된다. 따라서 기존 OA/mIoU는 First Group 학습·평가 결과가 아니다. 원래 실험 기록은 보존하고 감사에서 Central Java를 제외한다.

새 경계는 `data/first-group-boundaries/selected-six.geojson`이다. geoBoundaries gbOpen ADM1, 표현연도 2017, 원 출처 OpenStreetMap/Wambacher, ODbL 1.0인 공개 참조 경계이다. 현재 발주기관이 승인한 최신 법적 경계로 표시하지 않는다. 경계 취득의 원 URL·메타데이터·해시는 `boundary-manifest.json`에 보존되어 있다. 감사는 참조 polygon을 래스터 CRS로 변환해 주 내부 픽셀 비율을 기록하고 내부 픽셀만 라벨 품질 계산에 사용한다. 해안·도서·행정개편과 단순화 경계의 오차는 별도 검토가 필요하다.

## 2. 개발 순서와 실행 계약

1. 사용자 지정 여섯 주의 영문·현지 이름 및 고정 slug를 확정했다.
2. 수집 담당의 연차 manifest와 실제 로컬 GeoTIFF 계약을 맞췄다.
3. `scripts/audit_first_group.py`에 파일·공간 정합·클래스·연도·해시·패치 감사를 구현했다.
4. 주와 원본 source group의 모든 연차를 같은 holdout에 묶는 분할 계획을 구현했다.
5. 기존 세 지역 자료를 먼저 감사해 First Group에 속하는 두 지역만 재고로 인정했다.
6. 신규 여섯 주 2021 자료 수집이 끝나면 같은 도구로 재검사한다. 여섯 패치 수준에서는 모델 학습을 반복하지 않는다.
7. 36개 조합과 충분한 유효 패치, 전문가 독립참조가 확보된 뒤에만 별도의 First Group 학습 계획을 확정한다.

```powershell
python scripts/audit_first_group.py --manifest data/baseline2021/annual-window-report.json --output data/first-group/quality-audit-legacy-baseline.json

# 신규 수집 보고서가 존재한 다음 실행
python scripts/audit_first_group.py --manifest data/first-group-2021/annual-window-report.json --output data/first-group/quality-audit-2021.json

# 서로 다른 연차 보고서를 통합할 때
python scripts/audit_first_group.py --manifest data/first-group-2020/annual-window-report.json data/first-group-2021/annual-window-report.json --output data/first-group/quality-audit.json
```

두 번째와 세 번째 명령은 해당 파일이 실제로 확보된 뒤에 실행하는 계약 예시이다. 없는 자료를 생성하거나 수집 완료로 처리하지 않는다. 감사 자체는 네트워크를 호출하지 않는다. `--config` 기본값은 `configs/first-group.collection.json`, `--data-root` 기본값은 `data`, 기본 품질 기준은 `--min-valid-fraction 0.8`이다. 잘못된 여섯 주 config는 거부한다.

## 3. 재고와 충분성을 구분하는 기준

|감사 항목|계산과 의미|
|---|---|
|명목 패치 `nominal_patch_count`|ceil(높이/256)×ceil(폭/256). 경계 padding도 포함하므로 완전한 실제 패치와 다르다.|
|실제 256 패치 `actual_256_patch_count`|floor(높이/256)×floor(폭/256). 실제 파일에 완전히 존재하는 256×256 창 수이다.|
|일부 유효 패치 `nonempty_patch_count`|padding 포함 창에 유효한 라벨이 하나라도 있는 수. 학습 가능한 고품질 패치 수가 아니다.|
|품질 적격 `eligible_patch_count`|최소 3개 입력 밴드가 있고 실제 완전한 256 창에서 영상·라벨·주 내부·외부 품질 마스크를 통과한 픽셀이 80% 이상인 수.|
|시기까지 적격 `temporally_eligible_patch_count`|품질 적격이면서 입력영상 관측연도와 라벨 제품연도가 요청 연도에 모두 일치하는 수. 1,000개 목표 판정에는 이 값을 사용한다.|
|실제 영상 셀|파일을 열고 CRS 등을 확인한 비합성 영상이 있는 주·연도. 선언된 다운로드 성공만으로 인정하지 않는다.|
|정합 라벨 셀|실파일·같은 CRS/transform/크기·범주형 품질을 확인한 참조가 있는 주·연도. 영상 연도 불일치가 확인되면 제외한다.|
|시기 일치 라벨 셀|영상 관측연도와 라벨 제품연도가 모두 요청 연도와 일치하는 조합. 연도 미기재는 unknown으로 남긴다.|
|전체 원본 장면|`full_original_scene=true`로 별도 명시된 자료만 센다. 작은 원본 DN 창은 전체 위성 장면 다운로드로 세지 않는다.|

`synthetic=true` 자료는 시험 재고에는 남지만 실제 재고·패치 목표에 포함하지 않는다. 같은 영상·라벨 SHA256 쌍을 다른 연도에 복사해도 유효 패치 수를 늘리지 않는다. 원본 해시는 데이터의 동일성을 확인하는 값이며 데이터 진위나 라이선스 검토 완료를 자동 인증하지 않는다.

36개 주·연도별 영상과 해당 시기의 라벨이 모두 있어야 `all_36_image_label_combinations_available=true`가 된다. 전체 원본 장면 36개 확보는 `all_36_full_original_scenes_available`로 별도 표시한다. 36개 조합에 창 하나씩만 있어도 최대 36개 패치에 불과하다. **1,000~3,000개 목표, 공간 대표성, 클래스 균형, 전문가 독립평가는 별개로 충족해야 한다.** 학습 준비를 재고 감사만으로 자동 승인하지 않으므로 `learning_ready=false`를 유지한다.

## 4. 연도·라벨·방사보정 품질

라벨은 9개 내부 클래스와 255 ignore 체계를 사용한다. WorldCover 10~100 코드 매핑은 기존 ML 모듈과 같은 초기 매핑이며 맹그로브와 moss/lichen 등에 의미 손실이 있다. Dynamic World는 공식 순서 9개 확률 밴드, 기본 confidence 0.8을 적용한다. 원래 클래스 개수와 유효 클래스별 픽셀 수를 남겨 특정 클래스가 없는 창을 확인한다. 한 창의 클래스 비율을 주 전체 토지피복 면적으로 해석하지 않는다.

**WorldCover 2021을 2020·2022~2025의 정답으로 재사용하지 않는다.** `label_year`가 입력에 있으면 선언된 근거를 남긴다. 없으면 수집기가 보존한 원본 WorldCover URL의 `/v100/2020/` 또는 `/v200/2021/`와 로컬 라벨 SHA256 일치를 확인한 경우에만 제품연도를 보완한다. 근거가 없으면 null/unknown이고, 시기 적격으로 세지 않는다. 연도 일치는 최소조건이며 관측 계절·센서·연중 합성 기간이 일치한다는 뜻은 아니다.

2020은 WorldCover 2020 후보, 2021은 WorldCover 2021 후보를 검토한다. 나머지 연도는 Dynamic World 또는 해당 시기 전문가 참조가 필요하다. Dynamic World Earth Engine 프로젝트·인증·실제 export는 미확보 상태이며 인증정보가 없는데 수집 성공으로 표시하지 않는다. 공식 KLHK 등 참조자료는 접근권한과 사용조건을 확인해야 한다.

DN×0.0001 같은 수치 정규화는 제품의 실제 scale/offset 검증과 다르다. 센서·처리 baseline·밴드 순서·구름/SCL·NoData·최대 해상도 차이를 따로 기록한다. SCL이 라벨의 NoData에만 반영된 기존 자료는 원본 RGB 추론이 구름 마스킹되었다고 보고하지 않는다. 영상·라벨의 정합 실패는 해당 항목의 오류로 남기되 열 수 있는 영상 재고까지 숨기지 않는다.

## 5. 지역 및 원본 장면을 공유하는 holdout

독립적인 여섯 주만 있을 때 seed 42의 계획은 약 70/15/15인 **4주 train / 1주 validation / 1주 test**이다. 초기 계획상 train은 South Sulawesi/East Java/Gorontalo/Southeast Sulawesi, validation은 Banten, test는 West Java이다. 이것은 학습 수행이나 독립성 검증 완료가 아닌 고정 계획이다.

같은 주의 2020~2025 전 연차·인접 창은 항상 같은 분할에 둔다. 다른 주라도 동일 `source_group`/원본 scene ID 또는 동일 영상 SHA256을 공유하면 연결요소로 묶어 같은 분할에 둔다. 원본 공유 제약이 4/1/1과 충돌하면 누출 방지를 우선하고 실제 주별 분할 개수를 기록한다. 독립 연결요소가 세 개 미만이면 분할을 차단한다.

감사 `inventory[].dataset_group`을 데이터 준비의 `group`으로 사용해야 한다. `province_splits`를 무시하고 모든 연차 패치를 무작위로 나누지 않는다. 새 원본 공유 관계가 발견되면 분할 계획 버전을 검토하고 이전 평가와 섞지 않는다. 장소를 달리해도 학습 라벨 제작과정이 모델·시험 영상에 의존했을 수 있으므로 최종 test에는 전문가가 독립 작성한 참조와 검토 증빙이 필요하다.

## 6. 실제 감사 결과와 회귀시험

기존 `data/baseline2021/annual-window-report.json`으로 첫 감사를 실행했다. 36개 기대 조합 중 실제 First Group 영상/정합 라벨은 **서자바 2021·남술라웨시 2021의 두 조합**뿐이었다. 시기 근거가 맞는 품질 적격 패치는 두 개, 전체 원본 장면 셀은 0개이며 `learning_ready=false`이다. 중부자바 한 항목은 대상 밖으로 제외됐다. 결과는 `data/first-group/quality-audit-legacy-baseline.json`에 저장했다.

이후 Gorontalo 재시도를 포함해 신규 First Group 2021 여섯 주 RGB/WorldCover 창이 모두 확보됐다. `data/first-group-2021/annual-window-report.json`으로 재감사하여 `data/first-group/quality-audit-2021.json`에 저장했다. 입력은 전부 B02/B03/B04, 256×256이며 2021 영상과 2021 라벨 제품연도 근거가 모두 맞았다. 주 참조 polygon 내부 픽셀 비율은 여섯 창 모두 100%였다. 그러나 유효 라벨 비율과 품질 적격은 다음과 같다.

|주|SCL/NoData/주 경계 통과 유효 비율|80% 품질 적격 256 패치|계획 분할|
|---|---:|---:|---|
|South Sulawesi|62.9883%|0|train|
|Gorontalo|80.6763%|1|train|
|Southeast Sulawesi|88.5071%|1|train|
|Banten|66.1591%|0|validation|
|West Java|62.8174%|0|test|
|East Java|99.4934%|1|train|

실제 재고는 **36개 조합 중 2021의 6개**, 명목/완전 256 패치는 여섯 개, 시기·품질 적격 패치는 **세 개**뿐이다. 나머지 30개 주·연도 조합은 미확보다. 현재 고정 holdout에서 적격 패치는 train 3, validation 0, test 0이므로 평가용 품질 자료부터 추가해야 한다. 1,000개 목표와 독립 평가조건을 모두 충족하지 않는다. 특히 Gorontalo는 trees 52,768/52,872 유효 픽셀, Southeast Sulawesi는 trees 58,003/58,004로 한 클래스가 거의 전부여서 여섯 주 개수만으로 클래스 대표성을 판단하지 않는다.

이번 수집은 작은 창의 원본 DN을 RGB로 결합한 자료이며 원격 원본 COG 자산 전체와 각 전처리 소스/SCL 원본 파일을 모두 불변 보존한 수집이 아니다. 전체 원본 장면 셀은 0개로 유지한다. 새로운 연차 수집에서는 원본 창/품질 마스크와 처리 이력을 별도 보존해야 한다. 2020·2022~2025와 해당 시기 라벨이 확보된 것으로 계산하지 않았고 **여섯 패치로 새 학습을 반복하지 않았다.** 기존 세 지역 모델과 분리해 이번 단계는 품질 감사와 수집 충분성 확인에 집중한다.

```powershell
python -m unittest discover -s tests -p test_ml_first_group.py -v
```

최종 8개 시험을 1.568초에 모두 통과했다. 검증 범위는 36개 누락표, padding/완전 패치/80% 품질 기준 차이, 합성자료의 실제 목표 제외, Central Java 제외, 라벨 실패 시 영상 재고 보존, 4/1/1 및 원본 공유 holdout, 동일 자료 연도 복사의 패치 부풀리기 방지, 2021 라벨의 2020 참조 불일치, 주 polygon 밖 픽셀을 품질 계산에서 제외하는 동작이다. 시험 래스터는 임시 합성 fixture이며 실제 수집 개수로 집계하지 않는다.

## 6-1. 실행 가능한 정식 실험 준비 gate

`backend/app/ml/readiness.py`와 `scripts/run_experiment.py`로 재고 감사 다음 단계를 구현했다. 기본 실험 계획은 `data/first-group/experiment-plan.json`, 현재 판정은 `data/first-group/training-readiness.json`이다.

```powershell
python scripts/run_experiment.py --manifest data/first-group-2021/annual-window-report.json --write-default-plan data/first-group/experiment-plan.json
```

기본은 preflight만 수행한다. 실제 학습 명령에는 `--execute --run-id 새ID`가 필요하지만 **현재 자료는 gate가 blocked이므로 실행하지 않았다.** 실자료는 계획의 하한을 낮춰도 최소 1,000개 완전 256 패치, 유효 비율 80%, train 600/validation 100/test 100개가 필요하다. 기본 범위는 6개 주×2020~2025이며 명시적 계획에서 연구 연도를 한정한 경우에는 그 한정 범위의 의사라벨 실험으로만 보고한다. 범위를 현재 확보 자료에 맞춰 자동 축소하지 않는다.

입력 순서는 B02/B03/B04/B08/B11/B12 여섯 밴드다. 각 영상에 대해 채널 수와 이름 순서, 대응 라벨 연도·제품 버전·원 출처 URL, 실제 품질 마스크, 제품별 정규화 검증 기록을 확인한다. 공식 메타데이터 검증 JSON은 `status=verified_product_metadata`, product ID, band_names, scale/offset, 원본 메타데이터 경로·해시·URL을 담아야 한다. 적용 설정과 이 기록 및 원본 파일의 해시가 맞아야 한다. 기록이 없으면 수치 기본값을 추측해 통과시키지 않는다. 이 절차는 보존한 검증 기록의 일관성을 확인하며 서명된 공급자 진위나 라벨 지상정답을 자동 인증하는 것은 아니다.

같은 주의 전 연차, 같은 원본 scene/source group, 공간적으로 중첩되는 입력은 연결요소로 묶어 train/validation/test를 고정한다. gate가 산출한 `group_splits`를 실제 패치 생성에 전달하므로 준비 단계에서 재무작위 분할하지 않는다. 패치마다 저장 해시를 기록하고 학습 직전 원본/메타데이터/패치 해시와 실제 분할별 클래스 개수를 다시 검사한다. 기본 관심 클래스 water/trees/grass/crops/built/bare는 각 분할에서 256 유효 픽셀 이상을 요구하며, validation/test에만 있고 train에 없는 클래스도 차단한다. class weights는 **train 픽셀 개수만** 이용한 역제곱근 가중치이고 관측 클래스 평균을 1로 정규화한다. 부재 클래스는 가중치 0이며 validation/test 분포로 가중치를 조정하지 않는다.

첫 preflight는 기존 RGB 보고서를 선택해 새 여섯 밴드 계약의 `BAND_SIGNATURE` 차단 등을 확인했다. 이후 32MiB 제한 보충 수집으로 Banten/West Java의 2021 여섯 밴드·라벨·SCL·품질 마스크·제품 XML 두 조합이 확보되어 **새 여섯 밴드 보고서만 선택해 재평가**했다.

```powershell
python scripts/run_experiment.py --manifest data/first-group-recovery32/annual-window-report.json
```

최신 `training-readiness.json`은 **36개 조합 중 2개, 적격 패치 train 0 / validation 1 / test 1, 차단 사유 15개, blocked**이다. 34개 조합 미확보, 총 2/1000 패치, train 자료 없음, 분할별 표본 수와 클래스 coverage 부족을 기록했다. 두 영상의 밴드/라벨 연도/품질 마스크/제품별 정규화 근거 계약은 통과했으므로 단순히 “정규화 미검증”이나 “6밴드 자료 없음”으로 보고하지 않는다. 공식 XML과 제품 ID 일치 및 quantification=10000, PB03 no-offset 근거에 따라 채널별 scale=.0001/offset=0이 검증됐다. `reflectance_conversion_verified=false`는 수집된 원본 DN 자체에 변환을 아직 적용하지 않았다는 뜻이며 보정 근거가 없다는 뜻이 아니다. 실제 모델 패치 준비 단계에서 제품별 설정을 적용한다.

**최신 정식 6밴드 적격 패치 2개**와 앞 절의 **기존 RGB 품질 적격 패치 3개**는 다른 자료·계약이므로 합산하지 않는다. 기존 세 지역 모델과 신규 자료로 실제 재학습하지 않았다.

두 수집 보고서의 순수 재고/품질을 함께 감사한 `data/first-group/quality-audit-current.json`도 생성했다. 서로 다른 실제 창은 8개(3밴드 6개+6밴드 2개), 고유 주·연도 셀은 여전히 2021의 6개다. 완전 256 패치는 8개, 밴드 계약을 혼합한 품질 적격 재고는 5개(train 3/validation 1/test 1)다. 이는 재고 품질 합계이며 하나의 정식 학습 데이터셋 패치 수가 아니다. 새 여섯 밴드 실험에 그대로 다섯 개를 사용할 수 없고 정식 준비 판정의 두 개와 구분한다. 기존 `quality-audit-2021.json`은 수정하지 않았다.

판정 파일에는 status, ready_for_training, blockers, input_manifests/verified_files의 상대 경로·SHA256, policy, coverage, patch_counts_by_split, class_counts_by_split, group_splits, input_signature가 있다. API는 ready 판정을 읽을 때도 원본 해시를 재검증해야 하고 파일 변경 시 stale로 처리해야 한다. 과학적 정확도 검증 필드는 항상 false이다. 충분한 자료가 있어도 결과는 WC/DW 의사라벨 일치도 실험이며 전문가 독립 참조가 없으면 실정확도로 보고하지 않는다.

ML 관련 총 37개 시험을 55.435초에 모두 통과했다. 합성 fixture의 gate 양성 경로, 실제 최소 1,000개 하한 우회 거부, 근거 파일 변조, WC 2021의 2020 재사용 거부, source group 누출 차단, train-only 가중치, 단일/거의 단일 출력 감지, 6밴드 제품별 offset 실제 CPU 학습·추론을 검증했다. 합성 양성 경로는 내부 테스트 전용이며 CLI에 실자료 하한을 낮추는 시험 옵션은 없다.

## 7. 다음 체크포인트

1. 신규 여섯 주 2021 수집 결과의 실제 파일·해시·구름·주 경계 내부·연도 근거 재감사.
2. 2020 및 2022~2025 영상/해당 시기 라벨의 누락표 해소와 인증·라이선스 확보.
3. 클래스·지역·시기 대표성을 고려해 시기 적격 실제 256 패치 1,000~3,000개 확보.
4. 고정 holdout과 First Group 학습·검증 계획 검토. 독립 참조가 없으면 의사라벨 일치도 실험으로 명시하고 실제 정확도 검증은 보류.
5. 충분성 충족 뒤 실제 실험을 수행하고 기존 세 지역 baseline과 별도로 보고.

## 8. 대량 자료 실험으로 연결

2026-10-16 후속 구현은 [대량 패치 재학습 기록](17_대량패치_재학습_기록.md)에 정리했다. 실제 1,000~3,000개, train/val/test 600/100/100 이상, 고정 네 학습 주마다 50개 패치와 32개 공간 위치 이상을 검사한다. 같은 공간 모든 연차와 원본 scene은 같은 분할에 고정한다. 각 분할의 주요 클래스 참조 픽셀 분포와 실제 예측 분포를 별도로 검사한다.

새 정식 입력은 Esri v003 동년 의사라벨만 선택한 2020~2025년 계획이다. 기존 RGB/WC 품질 재고는 별도로 보존하며 새 Esri 적격 패치 수에 더하지 않는다. 새 보고서가 수집 중인 현재 preflight는 blocked이며 실제 대량 재학습을 하지 않았다. 두 해만 사용하는 명시적 개발 계획도 같은 1,000개 기준을 유지하고 전체 36개 주·연도 목표 달성으로 보고하지 않는다.

첫 Esri Gorontalo2020 16개 패치의 참조 trees 비율은 97.7703%로 편중됐다. 이후 기본 정책은 split별 최대 단일 참조 클래스 90%, 주요 클래스별 최소 0.5%와 클래스 256픽셀 이상 포함 패치 5개를 추가 검사한다. 이는 공개한 개발 샘플링 기준이며 자연 분포·독립 정확도를 보장하지 않는다. 수집 담당에게 도시·수변·나지·농경지 공간 보충을 요청했으며 실제 추가 학습은 여전히 금지 상태다. 상세 실제 파일 감사와 변조/편중 검사는 문서17의 후속 기록을 따른다.
