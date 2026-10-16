# Model Type Profiles

## 1. 학습형(trainable_ml)
새 데이터 QC → 학습 준비성 → 누출방지 Split → Frozen dataset+code+env → retrain → 적합성·독립시험 → baseline 비교 → model card → 내부 전문가 승인 → staging/rollback smoke → 운영 승인.
**학습 데이터 부족**, 단일클래스 Collapse 또는 독립시험 부재 시 `DRAFT/BLOCKED`. WorldCover 의사라벨 일치도와 진짜 정확도를 구분.

## 2. 수치/물리형(calibrated_physical)
관측·초기/경계조건 검증 → parameter bounds/prior 설정 → baseline 재현 → 목적함수/보정기간 확정 → recalibration → 독립 시공간 관측검증 → mass/energy/physical consistency → sensitivity/uncertainty → 전문가 승인 → staging/rollback.
보정(calibration)과 독립 검증(validation) 구간은 겹치지 않도록 기록. 모델 본체 버전과 parameter-set 버전을 모두 고정.

## 3. 통계형(statistical)
표본·변수/불확실성 점검 → 추정/재추정 → holdout 또는 시계열 백테스트 → 편향·재현성 검증 → 승인.

## 4. 외부서비스형(external_service)
버전·SLA·Data Rights·API Contract 확인 → 고정 테스트 벡터 및 시나리오 검증 → 제공기관 검증자료 검토 → 장애/중단/계약만료 대책 → 통합 승인. 내부 retraining을 강제하지 않음.

### 공통 금지
과학모델 준비되지 않은 경우 모의 결과를 실제 SDSS 의사결정 결과로 표시하지 않는다. 관측변수의 단위·기준면·시간/공간 분해능이 상이하면 결합을 차단한다.
