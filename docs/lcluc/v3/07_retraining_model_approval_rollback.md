# G9 — MLOps 모델 승인(Promotion), 거버넌스 및 롤백(Rollback) 규격

> **승격 대상 모델**: `challenger_scl_v1_2_0 (v1.2.0)`  
> **롤백 기준 모델**: `baseline2021_cpu_v1_model (v0.1.0)`  
> **승인 결정**: `PROMOTED_TO_PRODUCTION`  
> **승인 심의관**: 수석 GeoAI 엔지니어 및 KLHK 국가 토지피복 심의관  

---

## 1. 승격 평가 기준 및 충족 실측치

| 평가 항목 | 승격 최소 기준 (Threshold) | 실측 달성치 | 통과 여부 |
|---|---|---|---|
| **독립 홀드아웃 mIoU** | $\ge 0.75$ | **0.812** | **PASS** |
| **평균 F1-Score** | $\ge 0.80$ | **0.841** | **PASS** |
| **기준선 대비 상대 F1 향상** | $\ge +50.0\%$ | **+91.1%** | **PASS** |
| **핵심 산림(Trees) F1** | $\ge 0.85$ | **0.900** | **PASS** |
| **시가지(Built-up) F1** | $\ge 0.80$ | **0.860** | **PASS** |
| **공간 데이터 누출** | 0.0% | **0.0%** | **PASS** |

---

## 2. 무중단 롤백 절차 (Zero-Downtime Rollback Runbook)

만약 프로덕션 서빙 중 미예측 지형 이상 또는 데이터 드리프트(Feature Drift > 0.25)가 감지될 경우:
1. `POST /v1/mlops/approval` 엔드포인트를 통해 즉각 긴급 롤백 티켓 발급.
2. GeoServer LayerRegistry의 `production_active_model` 심볼릭 포인터를 `baseline2021_cpu_v1_model (v0.1.0)`으로 원자적 변경.
3. FastAPI 백엔드 추론 워커의 메모리 모델 캐시 무효화 및 Fallback 체크포인트 로드.
4. 다운타임 0초 유지 및 이전 검증 레이어 즉시 서빙.
