"""실제 내려받은 영상·약한 참조라벨·모델 출력을 나란히 검토한다."""
import argparse
import json
import os
from pathlib import Path
import numpy as np
import rasterio
# 글꼴 캐시도 작업 폴더에 보존하여 사용자 전역 설정을 변경하지 않는다.
_cache = Path(__file__).resolve().parents[1] / 'tmp' / 'matplotlib'
_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', str(_cache))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-root', default='data')
    parser.add_argument('--run-id', default='baseline2021_cpu_v1')
    args = parser.parse_args()
    root = Path(args.data_root).resolve()
    report = json.loads((root / 'results' / args.run_id / 'baseline-run.json').read_text(encoding='utf-8'))
    # 영상은 물리 반사도가 확정되지 않아 시각 검토용 DN 백분위 스트레칭만 적용한다.
    mapping = {10:1,20:5,30:2,40:4,50:6,60:7,70:8,80:0,90:3,95:1,100:2}
    colors = ListedColormap(['#419bdf','#397d49','#88b053','#7a87c6','#e6bf5e','#c29164','#c34242','#d1c6ac','#eeeeee'])
    colors.set_bad('#222222')
    fig, axes = plt.subplots(3, 3, figsize=(12, 11))
    for i, (scene, prediction) in enumerate(zip(report['quality'], report['predictions'])):
        with rasterio.open(root / scene['image_path']) as src:
            image = src.read()[[2,1,0]].transpose(1,2,0).astype(float)
        lower = np.percentile(image, 2, axis=(0,1))
        upper = np.percentile(image, 98, axis=(0,1))
        image = np.clip((image-lower)/np.maximum(upper-lower, 1), 0, 1)
        with rasterio.open(root / scene['label_path']) as src:
            raw = src.read(1)
        label = np.full(raw.shape, np.nan)
        for original, target in mapping.items():
            label[raw == original] = target
        with rasterio.open(root / prediction['classification_path']) as src:
            predicted = src.read(1).astype(float)
            predicted[predicted == 255] = np.nan
        axes[i,0].imshow(image)
        axes[i,1].imshow(label, cmap=colors, vmin=0, vmax=8, interpolation='nearest')
        axes[i,2].imshow(predicted, cmap=colors, vmin=0, vmax=8, interpolation='nearest')
        axes[i,0].set_ylabel(scene['group'].replace('_candidate','').replace('_',' ').title(), fontsize=11)
        for ax in axes[i]:
            ax.set_xticks([]); ax.set_yticks([])
    for ax, title in zip(axes[0], ['Downloaded Sentinel-2 RGB\nDN percentile display', 'WorldCover 2021 weak labels\nMasked cloud/invalid pixels', 'Tiny U-Net prediction\n3-epoch CPU baseline']):
        ax.set_title(title, fontsize=11)
    metrics = report['training']['test_metrics']
    fig.suptitle(f"2021 Indonesia: actual downloaded pixels and functional baseline\nWeak-label test agreement OA={metrics['overall_accuracy']:.2%}, mIoU={metrics['mean_iou']:.2%}; independent evaluation pending", fontsize=13)
    fig.tight_layout(rect=(0,0,1,.94))
    output = root / 'results' / args.run_id / 'preview.png'
    fig.savefig(output, dpi=130)
    plt.close(fig)
    print(output)


if __name__ == '__main__':
    main()
