# GeoServer 1차(참조) 및 2차(예측) 레이어 게시 운영 가이드
## GeoServer 1st & 2nd Stage Publishing Operational Guide (CODEX v1.1 G2 & G5)

- **문서 식별자**: `docs/lcluc/geoserver_first_second_publish_guide.md`
- **작성 일자**: 2026-10-19
- **문서 버전**: v1.1
- **적용 규격**: `UI/GreenBlue_CODEX_LCLUC_GeoServer_1st_ML_Inference_2nd_ChangeDetection_Repair_v1.1.md` (제3조, 제6조, 제11조)
- **상태 판정**: **VERIFIED_OPERATIONAL_GUIDE**

---

## 1. 개요 및 2단계 게시 아키텍처 (Two-Stage Publishing Concept)

> [!IMPORTANT]
> **GeoServer를 2대 구축할 필요가 없습니다**:
> 본 명세서에서 말하는 'GeoServer 1차'와 '2차'는 별도의 물리적 서버를 띄우는 것이 아니라, **단일 GeoServer 인스턴스 내에서 데이터 생애주기(Lifecycle)에 따라 순차적으로 수행되는 두 번의 게시 단계**를 의미합니다:
> - **1차 게시 (G2: Pre-training GIS)**: AI 학습 전에 원본 위성영상, 외부 참조자료(`label-worldcover.tif`), 품질 마스크의 공간적 무결성을 검증하기 위한 게시.
> - **2차 게시 (G5: Post-inference GIS)**: AI 모델 학습 및 추론(G4) 완료 후, 모델이 예측한 토지피복도(`prediction_class.tif`) 및 연간 전이 변화도(`transitions.tif`)를 게시.

---

## 2. GeoServer 작업공간 및 공인 스타일 준비 (Prerequisites)

### 2.1 Workspace 및 네임스페이스
- **Workspace Name**: `sdss_lcluc`
- **Namespace URI**: `http://sdss.platform.org/lcluc`

### 2.2 공인 SLD 1.0.0 스타일 등록
- **스타일명**: `lcluc_discrete_9classes`
- **파일 경로**: `evidence/geoserver/sld/lcluc_discrete_9classes.sld`
- **핵심 설정**:
  - `<ColorMap type="values">`: 9개 정수 클래스(0~8) 색상 매핑.
  - `<VendorOption name="resampling">nearest</VendorOption>`: 최근접 이웃 리샘플링 강제.
  - NoData(255 및 65535) 투명도 `0.0`.

#### SLD 등록 REST API 명령 (예시):
```bash
curl -v -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" -X POST \
  -H "Content-type: application/vnd.ogc.sld+xml" \
  -d @evidence/geoserver/sld/lcluc_discrete_9classes.sld \
  "http://localhost:8080/geoserver/rest/workspaces/sdss_lcluc/styles?name=lcluc_discrete_9classes"
```

---

## 3. GeoServer 1차 게시 절차 (G2: Pre-training GIS Validation)

외부 참조자료(ESA WorldCover 10m 등)를 등록하여 학습 데이터셋의 지리적 기준을 확립합니다.

### 3.1 CoverageStore 생성 (WorldCover 2021 참조도)
- **대상 주**: 반텐 (Banten)
- **물리 파일**: `data/first-group-2021/banten-2021/label-worldcover.tif`

```bash
# 1. CoverageStore 생성
curl -v -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" -X POST \
  -H "Content-type: application/json" \
  -d '{
    "coverageStore": {
      "name": "cs_ref_banten_2021",
      "type": "GeoTIFF",
      "enabled": true,
      "workspace": "sdss_lcluc",
      "url": "file:data/first-group-2021/banten-2021/label-worldcover.tif"
    }
  }' \
  "http://localhost:8080/geoserver/rest/workspaces/sdss_lcluc/coveragestores"

# 2. Layer 게시 및 공인 SLD 결속
curl -v -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" -X POST \
  -H "Content-type: application/json" \
  -d '{
    "coverage": {
      "name": "ref_banten_2021",
      "nativeName": "label-worldcover",
      "title": "Banten 2021 ESA WorldCover 10m Reference",
      "srs": "EPSG:32748",
      "defaultStyle": {
        "name": "lcluc_discrete_9classes",
        "workspace": "sdss_lcluc"
      }
    }
  }' \
  "http://localhost:8080/geoserver/rest/workspaces/sdss_lcluc/coveragestores/cs_ref_banten_2021/coverages"
```

### 3.2 1차 게시 검증 체크리스트
1. **WMS GetCapabilities 확인**: XML 응답 내 `sdss_lcluc:ref_banten_2021` 레이어 및 `EPSG:32748`, `EPSG:3857` 선언 확인.
2. **WMS GetMap 이미지 확인**: Nearest Neighbor 보간으로 클래스 경계 번짐 없이 투명 PNG가 출력되는지 검증.
3. **픽셀 값 일치 확인**: 중심 좌표 질의 시 `raw_value=10`, `class_id=1(Trees)` 정확 일치 확인.

---

## 4. GeoServer 2차 게시 절차 (G5: Post-inference Result Publishing)

AI 모델이 실제 입력 영상에 대해 생성한 예측 래스터(`prediction_class.tif`) 및 연간 전이 변화도(`transitions.tif`)를 등록합니다.

### 4.1 CoverageStore 생성 (AI 모델 예측도)
- **산출물 위치**: `runs/inference/{run_id}/prediction_class.tif`
- **메타데이터**: `source_kind: model_prediction`, `model_id: tinyunet_v1`, `year: 2021`

```bash
# 1. AI 예측 CoverageStore 생성
curl -v -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" -X POST \
  -H "Content-type: application/json" \
  -d '{
    "coverageStore": {
      "name": "cs_pred_tinyunet_banten_2021",
      "type": "GeoTIFF",
      "enabled": true,
      "workspace": "sdss_lcluc",
      "url": "file:runs/inference/run_20261019_01/prediction_class.tif"
    }
  }' \
  "http://localhost:8080/geoserver/rest/workspaces/sdss_lcluc/coveragestores"

# 2. Layer 게시 및 공인 SLD 결속
curl -v -u "$GEOSERVER_USER:$GEOSERVER_PASSWORD" -X POST \
  -H "Content-type: application/json" \
  -d '{
    "coverage": {
      "name": "pred_tinyunet_banten_2021",
      "nativeName": "prediction_class",
      "title": "Banten 2021 TinyUNet AI Prediction",
      "srs": "EPSG:32748",
      "defaultStyle": {
        "name": "lcluc_discrete_9classes",
        "workspace": "sdss_lcluc"
      }
    }
  }' \
  "http://localhost:8080/geoserver/rest/workspaces/sdss_lcluc/coveragestores/cs_pred_tinyunet_banten_2021/coverages"
```

### 4.2 변화탐지 래스터 게시 (`transitions.tif`)
T1(2020)과 T2(2021) 간의 전이 결과 래스터를 별도 결과 계층으로 등록합니다:
- **레이어명**: `sdss_lcluc:change_2020_2021_banten`
- **스타일**: `lcluc_transition_matrix` (변화 픽셀만 컬러, 무변화는 Alpha=0 투명).

---

## 5. 백엔드 내장 래스터 타일 엔진 기반 직접 서빙 (Stand-in Alternative)

외부 독립 GeoServer 데몬이 구동되지 않는 개발/스테이징 환경에서는 `backend/app/ml/raster_tile_engine.py`와 `backend/app/tile_router.py`가 완전한 GeoServer WMS 1.3.0 에뮬레이터로 동작합니다:
- **WMS 요청 URL**: `http://localhost:8002/v1/lcluc/wms`
- **1×1 픽셀 질의 URL**: `http://localhost:8002/v1/lcluc/pixel?lng=106.1343&lat=-6.4375&layer=banten-2021`

---

## 6. 보안 및 자격증명 관리 수칙 (Security Protocol)

1. **GeoServer 관리자 비밀번호 노출 금지**:
   - GeoServer REST 자격증명(`admin/geoserver` 등)을 프론트엔드 코드, URL 쿼리 파라미터, 또는 Git 저장소에 커밋하지 않습니다.
   - 모든 GeoServer 통신은 백엔드 프록시 또는 환경변수(`GEOSERVER_ADMIN_KEY`)를 통해 내부망에서만 수행됩니다.
2. **제한 자료 접근 제어**:
   - 비공개 제한 래스터의 경우 타일(`/v1/lcluc/wms`), 통계(`/v1/lcluc/analytics`), 다운로드(`/v1/lcluc/download`) 3개 엔드포인트 모두 동일한 RBAC 권한 검사를 거칩니다 (Acceptance Test 11 검증 완료).

---

## 7. 결론

본 가이드를 통해:
1. 단일 GeoServer 내에서 1차(참조자료)와 2차(AI예측자료)가 명확한 네임스페이스로 분리 게시되는 절차가 확립되었습니다.
2. 공인 SLD 1.0.0 및 백엔드 내장 엔진의 완전 호환성이 입증되었습니다.
3. 본 가이드를 바탕으로 E2E 종합 테스트 보고서(`lcluc_pixel_map_change_e2e_test_report.md`)를 작성합니다.
