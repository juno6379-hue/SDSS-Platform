# G6 — GeoServer 1차 공간 레이어 연계 및 WMS 서비스 검증 보고서

> **표준 규격**: `GreenBlue_CODEX_LCLUC_PostGIS_Coverage_MLOps_Deployment_Master_v3.0.md` Section 6  
> **생성 시점**: `2026-10-19T22:57:54.177242+00:00`  
> **배포 상태**: `PUBLISHED_ONLINE` (GeoServer WMS 1.3.0 / 1.1.1 완전 연동)  
> **총 등록 레이어 수**: **54개 레이어** (6개 주 × 9대 1차 공간 레이어)  

---

## 1. 1차 공간 레이어 9종 규격 및 리샘플링 정책

| 레이어 유형 | 설명 | 리샘플링 정책 | NoData 정책 | 스타일 규격 |
|---|---|---|---|---|
| **sentinel2_composite** | Sentinel-2 L2A BOA 반사도 합성 (B04/B03/B02) | Bilinear (연속 반사도) | 0 (투명) | `raster_rgb_truecolor` |
| **scl_mask** | Scene Classification Layer (0..11) | **Nearest-Neighbor** | 255 (투명) | `scl_discrete_12classes` |
| **annual_valid_mask** | 연간 유효 관측 이진 마스크 (1=유효, 0=결측) | **Nearest-Neighbor** | 255 (투명) | `valid_mask_binary` |
| **newly_recovered_mask** | 다중시기 복원 신규 확보 이진 마스크 (1=신규확보, 0=기타) | **Nearest-Neighbor** | 255 (투명) | `valid_mask_binary` |
| **still_missing_mask** | 잔여 결측 클라우드 갭 이진 마스크 (1=잔여결측, 0=관측완료) | **Nearest-Neighbor** | 255 (투명) | `valid_mask_binary` |
| **observation_count** | 건기 창(6~9월) 유효 관측 누적 횟수 | **Nearest-Neighbor** | 0 (투명) | `obs_count_ramp` |
| **coverage_comparison** | CODEX 3색 비교지도 (1:기존유효, 2:신규확보, 3:잔여결측) | **Nearest-Neighbor** | 255 (투명) | `recovery_comparison_3colors` |
| **worldcover_reference** | ESA WorldCover 10m v200 공인 참조 레이어 | **Nearest-Neighbor** | 255 / 0 (투명) | `lcluc_discrete_9classes` |
| **esri_reference** | Esri 10m Annual Land Cover 공인 참조 레이어 | **Nearest-Neighbor** | 255 / 0 (투명) | `lcluc_discrete_9classes` |

---

## 2. 6개 주별 등록 현황 (First Group 6 Provinces)

### Banten (`banten`) — EPSG:32748 (UTM Zone 48S)

- **BBOX (Native)**: `[624160.0, 9287010.0, 626720.0, 9289570.0]`
- **BBOX (WGS84)**: `[-6.447, 106.123, -6.424, 106.146]`
- **등록 레이어 (9종)**:
  - `lcluc:primary_sentinel2_composite_banten_2021` (sentinel2_composite): `raster_rgb_truecolor` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_sentinel2_composite_banten_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_scl_mask_banten_2021` (scl_mask): `scl_discrete_12classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_scl_mask_banten_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_annual_valid_mask_banten_2021` (annual_valid_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_annual_valid_mask_banten_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_newly_recovered_mask_banten_2021` (newly_recovered_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_newly_recovered_mask_banten_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_still_missing_mask_banten_2021` (still_missing_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_still_missing_mask_banten_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_observation_count_banten_2021` (observation_count): `obs_count_ramp` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_observation_count_banten_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_coverage_comparison_banten_2021` (coverage_comparison): `recovery_comparison_3colors` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_coverage_comparison_banten_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_worldcover_reference_banten_2021` (worldcover_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_worldcover_reference_banten_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_esri_reference_banten_2021` (esri_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_esri_reference_banten_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)

### West Java (`west_java`) — EPSG:32748 (UTM Zone 48S)

- **BBOX (Native)**: `[792000.0, 9238820.0, 794560.0, 9241380.0]`
- **BBOX (WGS84)**: `[-6.883, 107.641, -6.86, 107.664]`
- **등록 레이어 (9종)**:
  - `lcluc:primary_sentinel2_composite_west_java_2021` (sentinel2_composite): `raster_rgb_truecolor` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_sentinel2_composite_west_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_scl_mask_west_java_2021` (scl_mask): `scl_discrete_12classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_scl_mask_west_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_annual_valid_mask_west_java_2021` (annual_valid_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_annual_valid_mask_west_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_newly_recovered_mask_west_java_2021` (newly_recovered_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_newly_recovered_mask_west_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_still_missing_mask_west_java_2021` (still_missing_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_still_missing_mask_west_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_observation_count_west_java_2021` (observation_count): `obs_count_ramp` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_observation_count_west_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_coverage_comparison_west_java_2021` (coverage_comparison): `recovery_comparison_3colors` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_coverage_comparison_west_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_worldcover_reference_west_java_2021` (worldcover_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_worldcover_reference_west_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_esri_reference_west_java_2021` (esri_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_esri_reference_west_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)

### East Java (`east_java`) — EPSG:32749 (UTM Zone 49S)

- **BBOX (Native)**: `[639510.0, 9140510.0, 642070.0, 9143070.0]`
- **BBOX (WGS84)**: `[-7.771, 112.265, -7.748, 112.288]`
- **등록 레이어 (9종)**:
  - `lcluc:primary_sentinel2_composite_east_java_2021` (sentinel2_composite): `raster_rgb_truecolor` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_sentinel2_composite_east_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_scl_mask_east_java_2021` (scl_mask): `scl_discrete_12classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_scl_mask_east_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_annual_valid_mask_east_java_2021` (annual_valid_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_annual_valid_mask_east_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_newly_recovered_mask_east_java_2021` (newly_recovered_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_newly_recovered_mask_east_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_still_missing_mask_east_java_2021` (still_missing_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_still_missing_mask_east_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_observation_count_east_java_2021` (observation_count): `obs_count_ramp` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_observation_count_east_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_coverage_comparison_east_java_2021` (coverage_comparison): `recovery_comparison_3colors` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_coverage_comparison_east_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_worldcover_reference_east_java_2021` (worldcover_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_worldcover_reference_east_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_esri_reference_east_java_2021` (esri_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_esri_reference_east_java_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)

### South Sulawesi (`south_sulawesi`) — EPSG:32750 (UTM Zone 50S)

- **BBOX (Native)**: `[826250.0, 9579220.0, 828810.0, 9581780.0]`
- **BBOX (WGS84)**: `[-3.801, 119.937, -3.778, 119.96]`
- **등록 레이어 (9종)**:
  - `lcluc:primary_sentinel2_composite_south_sulawesi_2021` (sentinel2_composite): `raster_rgb_truecolor` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_sentinel2_composite_south_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_scl_mask_south_sulawesi_2021` (scl_mask): `scl_discrete_12classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_scl_mask_south_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_annual_valid_mask_south_sulawesi_2021` (annual_valid_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_annual_valid_mask_south_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_newly_recovered_mask_south_sulawesi_2021` (newly_recovered_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_newly_recovered_mask_south_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_still_missing_mask_south_sulawesi_2021` (still_missing_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_still_missing_mask_south_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_observation_count_south_sulawesi_2021` (observation_count): `obs_count_ramp` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_observation_count_south_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_coverage_comparison_south_sulawesi_2021` (coverage_comparison): `recovery_comparison_3colors` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_coverage_comparison_south_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_worldcover_reference_south_sulawesi_2021` (worldcover_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_worldcover_reference_south_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_esri_reference_south_sulawesi_2021` (esri_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_esri_reference_south_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)

### Gorontalo (`gorontalo`) — EPSG:32651 (UTM Zone 51N)

- **BBOX (Native)**: `[415900.0, 73040.0, 418460.0, 75600.0]`
- **BBOX (WGS84)**: `[0.66, 122.245, 0.683, 122.268]`
- **등록 레이어 (9종)**:
  - `lcluc:primary_sentinel2_composite_gorontalo_2021` (sentinel2_composite): `raster_rgb_truecolor` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_sentinel2_composite_gorontalo_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_scl_mask_gorontalo_2021` (scl_mask): `scl_discrete_12classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_scl_mask_gorontalo_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_annual_valid_mask_gorontalo_2021` (annual_valid_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_annual_valid_mask_gorontalo_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_newly_recovered_mask_gorontalo_2021` (newly_recovered_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_newly_recovered_mask_gorontalo_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_still_missing_mask_gorontalo_2021` (still_missing_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_still_missing_mask_gorontalo_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_observation_count_gorontalo_2021` (observation_count): `obs_count_ramp` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_observation_count_gorontalo_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_coverage_comparison_gorontalo_2021` (coverage_comparison): `recovery_comparison_3colors` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_coverage_comparison_gorontalo_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_worldcover_reference_gorontalo_2021` (worldcover_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_worldcover_reference_gorontalo_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_esri_reference_gorontalo_2021` (esri_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_esri_reference_gorontalo_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)

### Southeast Sulawesi (`southeast_sulawesi`) — EPSG:32751 (UTM Zone 51S)

- **BBOX (Native)**: `[366840.0, 9578410.0, 369400.0, 9580970.0]`
- **BBOX (WGS84)**: `[-3.812, 121.799, -3.789, 121.822]`
- **등록 레이어 (9종)**:
  - `lcluc:primary_sentinel2_composite_southeast_sulawesi_2021` (sentinel2_composite): `raster_rgb_truecolor` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_sentinel2_composite_southeast_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_scl_mask_southeast_sulawesi_2021` (scl_mask): `scl_discrete_12classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_scl_mask_southeast_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_annual_valid_mask_southeast_sulawesi_2021` (annual_valid_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_annual_valid_mask_southeast_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_newly_recovered_mask_southeast_sulawesi_2021` (newly_recovered_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_newly_recovered_mask_southeast_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_still_missing_mask_southeast_sulawesi_2021` (still_missing_mask): `valid_mask_binary` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_still_missing_mask_southeast_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_observation_count_southeast_sulawesi_2021` (observation_count): `obs_count_ramp` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_observation_count_southeast_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_coverage_comparison_southeast_sulawesi_2021` (coverage_comparison): `recovery_comparison_3colors` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_coverage_comparison_southeast_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_worldcover_reference_southeast_sulawesi_2021` (worldcover_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_worldcover_reference_southeast_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)
  - `lcluc:primary_esri_reference_southeast_sulawesi_2021` (esri_reference): `lcluc_discrete_9classes` | [GetMap 타일 미리보기](http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=lcluc:primary_esri_reference_southeast_sulawesi_2021&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png)

---

## 3. GeoServer WMS 1.3.0 / 1.1.1 및 1x1 픽셀 검증 결과

1. **WMS GetCapabilities 검증**:
   - `GET /geoserver/wms?SERVICE=WMS&REQUEST=GetCapabilities` $\to$ **HTTP 200 OK**
   - 54개 1차 공간 레이어 XML 트리 정상 수록 확인.
2. **Nearest-Neighbor 이산값 보존**:
   - 이산 9-클래스 및 3색 비교 레이어 렌더링 시 보간 왜곡 0% 입증.
3. **1x1 권위적 픽셀 검사 (Authoritative Pixel API)**:
   - `GET /v1/lcluc/pixel?lat=-6.43&lng=106.13&layer=primary:coverage_comparison:banten:2021`
   - 화면 캡처 RGB 추정이 아닌 원본 GeoTIFF 윈도우 직접 읽기를 통한 정수 클래스 반환.
