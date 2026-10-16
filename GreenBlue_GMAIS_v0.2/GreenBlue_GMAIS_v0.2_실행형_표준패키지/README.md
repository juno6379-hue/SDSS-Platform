# GMAIS v0.2 개발기관 배포용 실행형 표준 패키지 (검토본)

**상태:** GreenBlue 내부 제안 / 개발기관 의견수렴용 / 컨소시엄·BIG 미승인. 서명된 계약·RFP/TOR 및 승인된 제안·협상 합의보다 우선하지 않습니다.

**목표:** LCLUC 1개 실제 데이터 기반 E2E 기준 구현(정식 학습은 준비도 충족 시만 허용), 기타 5개 모델은 기관별 납품 Agent 연계. 공통 Data/Agent/Orchestrator/MLOps/GeoLLM/SDSS 인터페이스 적용.

## 구성
- `docs/*.docx`: 실행형 표준규격서 및 개발기관 납품·검수 체크리스트
- `api/openapi.yaml`: Agent/Job/Update Ticket 북향 API 제안 명세
- `schemas/`: 데이터셋, Agent, 작업, 결과, Workflow, 갱신티켓 등 JSON Schema Draft 2020-12
- `examples/`: 검증 가능한 구조 예시 (실제 데이터/과학모델 결과 아님)
- `reference_adapter/server.py`: 네트워크 없이 계약 동작을 시험할 수 있는 로컬 참조 Adapter. 과학적 추론을 수행하지 않음
- `tests/`: 로컬 API·Schema·차단·상태전이 계약시험
- `kubernetes/`: Deploy/Job/ConfigMap 템플릿 (클러스터 환경 확정 전 운영 배포 금지)
- `templates/`: 기술 문서·RACI·검수 양식·표준 오류목록

## 시험
```bash
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```
로컬 참조 서버 시험(선택):
```bash
python reference_adapter/server.py
```

이 시험의 성공은 **API/스키마 참조 구현 적합성**만 의미합니다. 6개 과학모델 정확도, BIG 실환경 가용성, 운영보안 승인 또는 외부기관 납품 적합성을 입증하지 않습니다.

## 개발기관 제출 순서
1. RACI/담당·모델유형·실행방식 선정 → 2. Dataset/I-O/Agent 계약 제출 → 3. Model Card 및 검증계획 → 4. OCI/External API 실행명세 → 5. Contract Test·Sandbox 시험 → 6. 과학검증·Staging 승인 → 7. Production 배포는 별도 승인.
