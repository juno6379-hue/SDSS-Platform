"""공식 Esri/Impact Observatory 연차제품의 출처와 분류체계를 명시한다.

URL 계획의 존재/다운로드 성공은 별도 검증한다. WorldCover와 이 제품의
Rangeland 의미 차이를 숨기지 않고 별도 taxonomy로 유지한다.
"""
import re

ESRI_HOST = "lulctimeseries.blob.core.windows.net"
ESRI_BASE = f"https://{ESRI_HOST}/lulctimeseriesv003"
OFFICIAL_EXPLORER = "https://livingatlas.arcgis.com/landcoverexplorer/"
OFFICIAL_RELEASE = "https://www.esri.com/about/newsroom/arcnews/latest-land-cover-data-release-shows-more-change-over-time"
CLASS_CROSSWALK = {1: 0, 2: 1, 4: 3, 5: 4, 7: 6, 8: 7, 9: 8, 11: 2}
TAXONOMY = "esri_io_v003_rangeland_merged_v1"


def esri_annual_plan(year, scene_id):
    if isinstance(year, bool) or not isinstance(year, int) or not 2020 <= year <= 2025:
        raise ValueError("검토한 연차 참조 범위는2020~2025입니다")
    # Sentinel-2 MGRS tile의 zone+위도대가 공개제품 supercell ID와 대응한다.
    # 직접 임의경도에서 추정하지 않고 실제 선택된 원본 scene tile을 사용한다.
    match = re.search(r"_T(\d{2}[C-HJ-NP-X])[A-Z]{2}_", scene_id)
    if not match:
        raise ValueError("실제 Sentinel-2 장면ID에서 MGRS supercell을 확인하지 못함")
    tile = match.group(1)
    end = f"{year}1231" if year >= 2024 else f"{year + 1}0101"
    return {"url": f"{ESRI_BASE}/lc{year}/{tile}_{year}0101-{end}.tif", "year": year,
        "tile": tile, "label_source": "esri_io", "version": f"EsriIOv003-{year}",
        "license": "CC-BY-4.0", "license_evidence": OFFICIAL_RELEASE,
        "url_rule_evidence": OFFICIAL_EXPLORER, "availability_verified": False,
        "taxonomy_signature": TAXONOMY, "crosswalk": CLASS_CROSSWALK,
        "ignore_source_classes": [0, 10],
        "semantic_limit": "Rangeland includes grass/shrub; target2=grass_or_shrub_rangeland; separate shrub class5 unused",
        "temporal_limit": "same_year_annual_composite_weak_reference_not_acquisition_date_ground_truth",
        "metadata_license_conflict": "IO STAC collection license=proprietary vs official release/registry CC-BY-4.0"}
