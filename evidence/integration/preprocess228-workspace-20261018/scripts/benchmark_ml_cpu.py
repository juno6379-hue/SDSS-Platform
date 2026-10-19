"""임시 합성 텐서로 CPU 연산 시간만 측정한다. 학습자료·모델·정확도 산출물이 아니다."""
import argparse
import json
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np

PROJECT_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT_ROOT))


def benchmark(steps=8,threads=2):
    import torch
    from backend.app.ml.network import TinyUNet
    torch.set_num_threads(threads);torch.manual_seed(42)
    model=TinyUNet(6).cpu();optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    image=torch.rand((1,6,256,256));label=torch.randint(0,9,(1,256,256))
    criterion=torch.nn.CrossEntropyLoss()
    def train_step():
        optimizer.zero_grad();loss=criterion(model(image),label);loss.backward();optimizer.step()
    for _ in range(2):
        train_step()
    train=[]
    for _ in range(steps):
        start=time.perf_counter();train_step();train.append(time.perf_counter()-start)
    model.eval();forward=[]
    with torch.inference_mode():
        for _ in range(steps):
            start=time.perf_counter();model(image);forward.append(time.perf_counter()-start)
    median=float(np.median(train));fmedian=float(np.median(forward))
    epoch=700*median+150*fmedian
    return {'measured_at':datetime.now(timezone.utc).isoformat(),'purpose':'synthetic_tensor_compute_timing_only',
            'counts_as_training_samples':False,'saved_model':False,'scientific_accuracy_claim':False,
            'torch_version':str(torch.__version__),'device':'cpu','threads':threads,'batch_size':1,'shape':[1,6,256,256],
            'warmup_steps':2,'measured_steps':steps,'train_step_seconds':train,'forward_seconds':forward,
            'train_step_median_seconds':median,'forward_median_seconds':fmedian,
            'estimate':{'scope':'1000 total, train700/val150/test150; computation only, NPZ I/O/hash/preparation excluded',
                        'epoch_compute_seconds':epoch,'twenty_epoch_compute_seconds':20*epoch,
                        'final_test_compute_seconds':150*fmedian},
            'recommendation':{'batch_size':1,'cpu_threads':threads,'max_epochs':20,'max_seconds_per_call':1800,
                              'resume':'atomic last.pt at completed epoch boundary; incomplete epoch rerun',
                              'warning':'Real dataset I/O and patch quality may materially increase elapsed time. Measure first real epoch before projecting.'}}


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--steps',type=int,default=8);parser.add_argument('--threads',type=int,default=2)
    parser.add_argument('--output',type=Path,default=PROJECT_ROOT/'data/audits/cpu-training-benchmark.json')
    args=parser.parse_args()
    if not 3<=args.steps<=30 or not 1<=args.threads<=8:
        raise ValueError('steps 3~30, threads 1~8 범위를 사용하세요.')
    result=benchmark(args.steps,args.threads)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'train_step_median_seconds':result['train_step_median_seconds'],'estimate':result['estimate']},ensure_ascii=False))


if __name__=='__main__':
    main()
