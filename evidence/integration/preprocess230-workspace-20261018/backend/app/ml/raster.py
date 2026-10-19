"""범주형 래스터 정합 및 공간 면적 계산. 원본 파일은 수정하지 않는다."""
from pathlib import Path
import numpy as np

CLASS_NAMES = ['water', 'trees', 'grass', 'flooded_vegetation', 'crops', 'shrub_and_scrub', 'built', 'bare', 'snow_and_ice']
ESRI_IO_MAPPING = {1:0,2:1,4:3,5:4,7:6,8:7,9:8,11:2}
ESRI_IO_CLASS_NAMES = ['water','trees','grass_or_shrub_rangeland','flooded_vegetation','crops','unused_separate_shrub_class','built','bare','snow_and_ice']
IGNORE = 255


def safe_path(root, value):
    root = Path(root).resolve()
    path = (root / str(value)).resolve()
    if not path.is_relative_to(root):
        raise ValueError('파일 경로는 data_root 내부여야 합니다.')
    return path


def read(path):
    import rasterio
    with rasterio.open(path) as src:
        if src.crs is None:
            raise ValueError('래스터 CRS가 필요합니다.')
        # 모든 밴드가 유효해야 한다. dataset_mask의 OR 규칙은 일부 결측을 놓친다.
        return src.read(), (src.read_masks() > 0).all(axis=0), src.profile.copy()


def assert_aligned(first, second):
    for key in ('crs', 'transform', 'width', 'height'):
        if first[key] != second[key]:
            raise ValueError(f'래스터 공간 정합 불일치: {key}; 먼저 reproject_to_reference를 실행하세요.')


def reproject_to_reference(source, reference, destination, categorical=True):
    """라벨은 최근린, 연속형 영상은 bilinear 보간으로 명시적 재투영한다."""
    import rasterio
    from rasterio.warp import reproject, Resampling
    with rasterio.open(source) as src, rasterio.open(reference) as ref:
        profile = src.profile.copy()
        profile.update(crs=ref.crs, transform=ref.transform, width=ref.width, height=ref.height)
        with rasterio.open(destination, 'w', **profile) as dst:
            for index in range(1, src.count + 1):
                reproject(rasterio.band(src, index), rasterio.band(dst, index),
                          src_transform=src.transform, src_crs=src.crs,
                          dst_transform=ref.transform, dst_crs=ref.crs,
                          resampling=Resampling.nearest if categorical else Resampling.bilinear)


def write_classes(path, data, profile, nodata=IGNORE, dtype='uint8'):
    import rasterio
    output = profile.copy()
    output.update(driver='GTiff', count=1, dtype=dtype, nodata=nodata, compress='deflate')
    # 입력의 타일 설정은 작은 출력에서 유효하지 않을 수 있어 제거한다.
    for key in ('blockxsize', 'blockysize', 'tiled', 'photometric'):
        output.pop(key, None)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, 'w', **output) as dst:
        dst.write(data.astype(dtype), 1)


def pixel_areas(profile):
    """일반 투영 CRS는 좌표 단위를 m로 환산하고 지리 CRS는 타원체 면적을 쓴다."""
    from pyproj import CRS
    crs = CRS.from_user_input(profile['crs'])
    transform = profile['transform']
    height, width = profile['height'], profile['width']
    if crs.is_projected:
        factor = crs.axis_info[0].unit_conversion_factor
        area = abs(transform.a * transform.e - transform.b * transform.d) * factor * factor
        return np.full((height, width), area, dtype=np.float64), 'projected_grid_area_m2'
    if not crs.is_geographic:
        raise ValueError('투영 또는 경위도 CRS만 면적 계산을 지원합니다.')
    geod = crs.get_geod()
    areas = np.empty((height, width), dtype=np.float64)
    for row in range(height):
        for col in range(width):
            corners = [transform * xy for xy in [(col,row), (col+1,row), (col+1,row+1), (col,row+1)]]
            area, _ = geod.polygon_area_perimeter([p[0] for p in corners], [p[1] for p in corners])
            areas[row, col] = abs(area)
    return areas, 'ellipsoidal_geodesic_m2'
