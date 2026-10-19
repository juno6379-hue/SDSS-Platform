# G8 — 모델 카드(Model Card) 및 홀드아웃 독립성 검증서

> **모델 식별자**: `challenger_scl_v1_2_0`  
> **버전**: `v1.2.0`  
> **아키텍처**: `Enhanced UNet with Spatial Attention & Residual Connections`  
> **개발 기관**: SDSS GeoAI / MLOps Platform  
> **승인 상태**: `PRODUCTION_APPROVED`  

---

## 1. 지리적 홀드아웃 독립성 보장 (Geographic Independence Proof)

- **평가 분할**: West Java (서부 자바 전역)
- **학습 분할 참여 여부**: **0% (완전 배제)**
  - Train: East Java, South Sulawesi, Gorontalo, Southeast Sulawesi
  - Val: Banten
  - Test: **West Java Only**
- **공간적 데이터 누출(Spatial Leakage)**: **0.0%**
  - 자바 섬 서부와 동부/술라웨시 간 150km 이상 물리적 이격
  - 동일 원본 씬(Scene) 또는 인접 타일 공유 원천 차단

---

## 2. 하이퍼파라미터 및 학습 환경

- **입력 텐서**: `(6, 256, 256)` (Sentinel-2 6-밴드 정규화 표면반사도)
- **학습 에포크**: 50 Epochs
- **배치 크기**: 16 (혼합 정밀도 FP16 / CPU Fallback 지원)
- **최적화 기법**: AdamW (Initial LR $1 \times 10^{-4}$, Cosine Annealing LR Schedule)
- **손실 함수**: Cross-Entropy (0.5) + Focal Loss (0.3) + Soft Dice Loss (0.2)
