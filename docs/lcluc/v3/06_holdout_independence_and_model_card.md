# G8 — 합성 시나리오 카드와 홀드아웃 검증 차단서

> **모델 식별자**: `challenger_scl_v1_2_0`
> **버전**: `v1.2.0`
> **아키텍처**: `Enhanced UNet with Spatial Attention & Residual Connections`
> **개발 기관**: SDSS GeoAI / MLOps Platform
> **증거 상태**: `TESTED_SYNTHETIC`
> **승인 상태**: `BLOCKED_NO_EXECUTED_TRAINING_OR_MEASURED_PREDICTIONS`

---

## 1. 지리적 홀드아웃 독립성

- 독립성 검증: **실패 시 닫힘(false)**
- 현재 연차 보고서에는 Banten/validation과 West Java/test에 동시에 등장하는 원본 Sentinel-2 scene이 있다.
- 따라서 `0% 누출`, `완전 배제`, `West Java 독립 홀드아웃`을 검증된 사실로 표현할 수 없다.
- 권위 연차 보고서는 1,779행 중 품질 적격 1,407행(Train 865 / Validation 292 / Test 250)을 기록한다.
- 세 split 모두 source class 8이 최소 0.5% 및 기여 패치 5개 기준에 미달하고 `learning_ready=false`다.

---

## 2. 실행되지 않은 계획 설정

- 아래 값은 실행 이력이 아니라 과거 문서에 있던 계획값이다.
- **입력 텐서 계획**: `(6, 256, 256)`
- **학습 에포크 계획**: 50 Epochs
- **배치 크기 계획**: 16
- **최적화 기법**: AdamW (Initial LR $1 \times 10^{-4}$, Cosine Annealing LR Schedule)
- **손실 함수**: Cross-Entropy (0.5) + Focal Loss (0.3) + Soft Dice Loss (0.2)

승격을 다시 검토하려면 실행된 학습 로그, 체크포인트 SHA-256, 독립 라벨, 예측 산출물,
실측 지표 재계산 증거, 분할 충돌 해소, 사람의 승인 기록이 모두 필요하다.
