"""최종 고정 모델의 참조/예측 혼동을 설명한다. 학습·평가 gate를 바꾸지 않는다."""
import csv
import hashlib
import io
import json
from pathlib import Path


def _need(value, message):
    if not value:
        raise ValueError(message)


def _text(value):
    return (type(value) is str and 1 <= len(value) <= 128
            and all(ord(c) >= 32 and not 127 <= ord(c) <= 159
                    and not 0xD800 <= ord(c) <= 0xDFFF for c in value))


def confusion_error_analysis(confusion, class_names):
    """행=참조, 열=예측의 9클래스 집계. 관측하지 못한 비율은 null이다."""
    _need(type(class_names) is list and len(class_names) == 9 and all(_text(v) for v in class_names),
          '오류 분석에는 9개 클래스 이름이 필요합니다.')
    _need(type(confusion) is list and len(confusion) == 9
          and all(type(row) is list and len(row) == 9 for row in confusion),
          '오류 분석 혼동행렬은 9×9 목록이어야 합니다.')
    _need(all(type(v) is int and 0 <= v <= 2**53-1 for row in confusion for v in row)
          and sum(map(sum, confusion)) <= 2**53-1, '혼동행렬 계수는 범위 안 정수여야 합니다.')
    support = [sum(row) for row in confusion]
    predicted = [sum(row[i] for row in confusion) for i in range(9)]
    classes = []
    for i, name in enumerate(class_names):
        tp = confusion[i][i]
        status = ('REFERENCE_AND_PREDICTION_ABSENT' if not support[i] and not predicted[i]
                  else 'NO_REFERENCE_SUPPORT' if not support[i]
                  else 'REFERENCE_PRESENT_NOT_PREDICTED' if not predicted[i] else 'OBSERVED')
        classes.append({'class_index': i, 'class_name': name, 'status': status,
            'reference_pixels': support[i], 'predicted_pixels': predicted[i],
            'true_positive_pixels': tp, 'false_negative_pixels': support[i]-tp,
            'false_positive_pixels': predicted[i]-tp,
            'recall': tp/support[i] if support[i] else None,
            'precision': tp/predicted[i] if predicted[i] else None,
            'omission_rate': (support[i]-tp)/support[i] if support[i] else None,
            'commission_rate': (predicted[i]-tp)/predicted[i] if predicted[i] else None,
            'recall_evaluable': support[i] > 0, 'precision_evaluable': predicted[i] > 0})
    pairs = [{'reference_class_index': i, 'reference_class_name': class_names[i],
              'predicted_class_index': j, 'predicted_class_name': class_names[j],
              'pixel_count': confusion[i][j], 'reference_class_fraction': confusion[i][j]/support[i]}
             for i in range(9) for j in range(9) if i != j and confusion[i][j]]
    pairs.sort(key=lambda v: (-v['pixel_count'], v['reference_class_index'], v['predicted_class_index']))
    total = sum(support)
    return {'schema_version': 1, 'scope': 'FINAL_CONFUSION_ERROR_ANALYSIS_ONLY',
            'matrix_axes': 'ROWS_REFERENCE_COLUMNS_PREDICTION', 'reference_pixel_count': total,
            'misclassified_pixel_count': total-sum(confusion[i][i] for i in range(9)),
            'classes': classes, 'confusion_pairs': pairs,
            'unobserved_reference_classes': [i for i in range(9) if not support[i]],
            'unpredicted_reference_present_classes': [i for i in range(9) if support[i] and not predicted[i]],
            'spatial_error_map_generated': False, 'independent_accuracy_certified': False}


def _csv_cell(value):
    # CSV quoting alone does not prevent spreadsheet formula interpretation.
    if type(value) is str and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def write_training_error_analysis(report, destination, data_root):
    """완료된 best 모델 val/test만 내보낸다. 테스트로 epoch를 선택하지 않는다.

    같은 바이트의 기존 artifact만 재사용한다. 다른 기존 파일은 덮어쓰지 않는다.
    """
    _need(type(report) is dict and report.get('training_state') == 'completed',
          '완료 모델의 오류 분석만 내보낼 수 있습니다.')
    epoch = report.get('selected_epoch')
    history = report.get('history')
    _need(type(epoch) is int and type(history) is list and 1 <= epoch <= len(history),
          '고정 best epoch 근거가 필요합니다.')
    validation = report.get('selected_validation_metrics')
    _need(type(history[epoch-1]) is dict and history[epoch-1].get('val') == validation,
          '선택 epoch의 validation 지표가 일치하지 않습니다.')
    test = report.get('test_metrics')
    _need(type(validation) is dict and type(test) is dict, '완료 val/test 지표가 필요합니다.')
    names = report.get('class_names')
    result = {'schema_version': 1, 'scope': 'SELECTED_BEST_EPOCH_FINAL_ERROR_ANALYSIS',
        'selected_epoch': epoch, 'model_id': report.get('model_id'),
        'checkpoint_sha256': report.get('checkpoint_sha256'),
        'reference_kind': report.get('reference_kind', 'unverified_or_pseudo_label'),
        'claim': '고정 best 모델의 참조 일치도 오류 분석입니다. 독립 정답·과학 정확도 인증이 아닙니다.',
        'test_used_for_epoch_selection': False, 'training_policy_changed': False,
        'scientific_accuracy_validated': False,
        'by_split': {split: confusion_error_analysis(metrics.get('confusion_matrix'), names)
                     for split, metrics in (('val', validation), ('test', test))}}
    root = Path(data_root).resolve()
    directory = Path(destination).resolve()
    _need(directory.is_relative_to(root) and directory != root and directory.is_dir(),
          '오류 분석 출력은 DATA 아래 모델 디렉터리여야 합니다.')
    payloads = {'error-analysis.json': (json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2)+'\n').encode('utf-8')}
    tables = [('error-analysis-classes.csv', 'classes'), ('error-analysis-confusions.csv', 'confusion_pairs')]
    columns = {'classes': list(result['by_split']['val']['classes'][0]),
               'confusion_pairs': ['reference_class_index', 'reference_class_name', 'predicted_class_index',
                                    'predicted_class_name', 'pixel_count', 'reference_class_fraction']}
    for filename, key in tables:
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(['split', *columns[key]])
        for split in ('val', 'test'):
            for row in result['by_split'][split][key]:
                writer.writerow([split, *[_csv_cell(row[field]) for field in columns[key]]])
        payloads[filename] = stream.getvalue().encode('utf-8-sig')
    # Validate every target before writing any artifact.
    for filename, raw in payloads.items():
        path = directory/filename
        _need(not path.is_symlink() and path.resolve().parent == directory,
              '오류 분석 출력 경로가 변경됐습니다.')
        if path.exists():
            _need(path.is_file() and path.read_bytes() == raw, '기존 오류 분석 artifact를 덮어쓰지 않습니다.')
    artifacts = []
    for filename, raw in payloads.items():
        path = directory/filename
        _need(not path.is_symlink() and path.resolve().parent == directory,
              '오류 분석 출력 경로가 변경됐습니다.')
        if not path.exists():
            with path.open('xb') as stream:
                stream.write(raw)
        _need(path.is_file() and not path.is_symlink() and path.read_bytes() == raw,
              '오류 분석 artifact가 작성 중 변경됐습니다.')
        artifacts.append({'path': path.relative_to(root).as_posix(), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
    return {**result, 'artifacts': artifacts, 'csv_formula_escape': 'Leading = + - @ after whitespace is prefixed with apostrophe.'}
