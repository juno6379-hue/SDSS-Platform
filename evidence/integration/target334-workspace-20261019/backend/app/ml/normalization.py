"""제품 메타데이터에서 얻은 채널별 수치 변환. 물리적 출처 검증은 readiness에서 수행한다."""
import numpy as np


def channel_values(value, channels, name):
    array=np.asarray(value,dtype='float64')
    if array.ndim==0:
        array=np.repeat(array,channels)
    if array.ndim!=1 or len(array)!=channels or not np.isfinite(array).all():
        raise ValueError(f'{name}는 유한한 스칼라 또는 입력 채널 수와 같은 길이의 배열이어야 합니다.')
    if name=='scale' and (array<=0).any():
        raise ValueError('scale은 양수여야 합니다.')
    return array


def apply_normalization(image, scale, offset):
    channels=image.shape[0]
    scales=channel_values(scale,channels,'scale').astype('float32')[:,None,None]
    offsets=channel_values(offset,channels,'offset').astype('float32')[:,None,None]
    return image.astype('float32')*scales+offsets
def verify_inference_normalization(normalization, source_scene, image_path, band_names, root):
    """실영상 해시·제품 식별자·공식 보정 근거를 함께 확인한다. 출처 진술 자체를 공인하지 않는다."""
    import json
    from .dataset import file_digest
    from .raster import safe_path
    if not isinstance(source_scene,dict) or not source_scene.get('scene_id') or source_scene.get('image_sha256')!=file_digest(image_path) or source_scene.get('band_names')!=band_names:
        raise ValueError('추론 source_scene의 실제 영상 SHA·제품ID·밴드 서명이 필요합니다.')
    if not isinstance(normalization,dict) or not normalization.get('evidence_path'):
        raise ValueError('검증된 normalization 공식 제품 근거가 필요합니다.')
    evidence_path=safe_path(root,normalization['evidence_path'])
    evidence=json.loads(evidence_path.read_text(encoding='utf-8'))
    if file_digest(evidence_path)!=normalization.get('evidence_sha256') or evidence.get('status')!='verified_product_metadata' or evidence.get('product_id')!=source_scene['scene_id'] or evidence.get('band_names')!=band_names:
        raise ValueError('추론 제품/밴드와 보정 근거 서명이 일치하지 않습니다.')
    for name in ('scale','offset'):
        if not np.array_equal(channel_values(normalization.get(name),len(band_names),name),channel_values(evidence.get(name),len(band_names),name)):
            raise ValueError('추론 scale/offset이 공식 제품 보정 근거와 다릅니다.')
    if not evidence.get('source_url') or file_digest(safe_path(root,evidence['source_metadata_path']))!=evidence.get('source_metadata_sha256'):
        raise ValueError('추론 공식 제품 메타데이터 SHA/출처가 일치하지 않습니다.')
    return {'scene_id':source_scene['scene_id'],'image_sha256':source_scene['image_sha256'],
            'normalization_evidence_path':str(evidence_path.relative_to(root)),
            'normalization_evidence_sha256':file_digest(evidence_path),'basis':'caller_source_attribution_with_product_metadata_hash_checks'}

