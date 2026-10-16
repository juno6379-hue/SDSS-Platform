"""모델 승인 및 배포의 상태 전이를 한 곳에서 검증한다."""
from .store import now

TRANSITIONS = {'Draft': {'Validated'}, 'Validated': {'Draft', 'Approved'}, 'Approved': {'Retired'}, 'Deployed': {'Retired'}, 'Retired': set()}


def transition(model, status, reason):
    if not isinstance(status, str) or not isinstance(reason, str):
        raise ValueError('상태와 검토 근거는 문자열이어야 합니다.')
    if status not in TRANSITIONS.get(model['status'], set()):
        raise ValueError(f"허용되지 않은 전이: {model['status']} -> {status}")
    if not reason or not reason.strip():
        raise ValueError('검토 근거를 입력하십시오.')
    # 의사라벨/합성자료 시험만으로 운영 승인할 수 없다.
    if status in ('Validated', 'Approved') and not model.get('independent_evaluation'):
        raise ValueError('독립 참조라벨 평가 증거가 없어 검증/승인을 진행할 수 없습니다.')
    result = dict(model, status=status)
    result['history'] = [*model.get('history', []), {'status': status, 'reason': reason, 'at': now()}]
    return result


def deploy(model):
    if model['status'] != 'Approved':
        raise ValueError('Approved 모델만 배포할 수 있습니다.')
    if not model.get('checkpoint_path'):
        raise ValueError('배포할 체크포인트가 없습니다.')
    return dict(model, status='Deployed', history=[*model.get('history', []), {'status': 'Deployed', 'at': now(), 'reason': '로컬 추론 서비스 배포'}])
