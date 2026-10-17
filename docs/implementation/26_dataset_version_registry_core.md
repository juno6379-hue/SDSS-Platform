# 불변 Dataset 버전 Registry 코어

## 2026-10-17 — 향후 내부 등록의 명시 모델 버전 선언 (97)

`register_experiment(store, report_path, *, model_version=...)`에서 호출자가 명시한 미래 버전을 선택적으로 보존한다. 옵션 생략은 기존 응답·레코드 바이트와 raw training의 임의 필드 복사를 그대로 유지한다. 명시할 때만 96 문자 검증과 보고서 필드 충돌 검사를 거쳐 모델 레코드의 exact5 `model_version_declaration`에 버전 원문·기존 checkpoint SHA·훈련 report SHA를 연결한다. 잘못된 명시 값은 기존 검사가 끝난 뒤 첫 Store.put 전에 거부한다.

기존 main/API·훈련 producer·UI는 이 옵션을 전달하지 않는다. 따라서 현재 공개 요청·화면의 동작은 그대로다. 명시 선언은 caller metadata이며 기관 권위·원본 인증·과학/모델/실행 승인이 아니다. 같은 모양의 raw 필드도 생략 경로에서 복사될 수 있으므로 키/source만으로 명시 호출이 생성했다고 인증하지 않는다. 기존 model_id 또는 dataset_id 중복 거부·Draft·독립평가 false·쓰기 순서를 유지한다.

기존 기록의 dataset_version을 모델 버전으로 대체하거나 역채움하지 않는다. 두 번 쓰기의 비트랜잭션·동시경쟁/전역 immutable 한계도 해결했다고 표현하지 않는다. 사용법·충돌 규칙·합성 임시 Store 시험·한계는 [문서97](97_model_version_declaration.md)를 따른다.

확인: 2026-10-17 KST. 이번 단위는 내부 Python 코어와 임시 자료 계약시험이며 운영 Registry/API 통합 완료가 아니다.

## 구현

`backend/app/dataset_registry.py`는 vendored GMAIS v0.2 Dataset Manifest schema를 직접 검사한다. 공간 범위·시간 순서·고정 버전을 확인하고 data root 상대경로 자산의 SHA를 대조한다. 기존 `datasets`와 다른 `dataset_versions` namespace에 원문 manifest와 별도 manifest SHA를 저장한다. 원문 schema에 운영 필드를 끼워 넣지 않는다.

- `register_version(store, manifest)`: dataset_id/version의 안정 식별자를 만들고 `BEGIN IMMEDIATE` 및 일반 `INSERT`로 같은 버전의 교체를 차단한다. 같은 내용의 반복 요청은 처음 등록 기록을 그대로 반환한다.
- `resolve_version(store, id, version, sha256)`: 저장 record key·manifest ID/version을 요청 신원과 대조하고 manifest SHA와 요청 자산 SHA 및 현재 자산을 다시 검사한다. 독립 검토에서 발견한 다른 유효 버전으로의 치환 문제도 차단했다.
- `latest/current` 자료·lineage 참조, schema/범위/시간 오류, hash 불일치, 원격/UNC/루트 탈출 경로를 거절한다.
- VALIDATED 품질에는 로컬 보고서 참조가 필요하지만 그 보고서의 과학적 타당성을 검증하지 않는다. 독립 과학검증과 배포 승인 필드는 항상 false다.

## 검증

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_dataset_registry_versions.py -v
```

신규11 PASS / 1.335초. `evidence/integration/dataset-versions-tests-20261017.log`. 임시 fixture에서 동일등록/버전분리/덮어쓰기 거절/동시8등록/손상 manifest/다른 유효 manifest로의 신원 치환/실파일 변경/공간·시간·schema/품질과 승인 분리를 확인했다. 실자료 등록·원장/manifest 변경·학습·다운로드는 하지 않았다.

## 남은 범위

HTTP API·기관 ACL·기존 dataset projection·실자료 등록 정책·불변 자산 저장소·lineage 부모 존재 검증·Job input resolver 연결은 후속이다. 이 코어 때문에 LCLUC의 dataset/science/deployment gate를 READY로 바꾸지 않는다. 현재 파일은 고정 해시 참조로 검사하며 자산 자체를 불변 저장소로 복제하는 구현은 아니다.

### 2026-10-18 후속: 실제 등록·ML 오류분석·GeoLLM 기술검토

[111](111_data_pipeline_completion.md)은 수집 source report를 RAW/STAGED 문서로 공통 버전에 연결한 명시 CLI이며 운영등록/AI-ready 승인이 아니다. [112](112_lcluc_ml_completion.md)는 기존 TinyUNet RGB 체크포인트를 확인하고 완료best 모델의 val/test 오류분석을 실제 학습 report에 연결했다. class7·QA차단과 독립 검증 라벨 미확보를 해제하지 않는다. [113](113_lcluc_integration_acceptance.md)의 LCLUC전용 새 orchestration은 후속PLANNED다. [114](114_geollm_technical_review.md)는 현재 앱에 LLM/RAG 미연결임을 확인하고 설치된 Ollama 모델의 별도 실응답·실패·임베딩과 Qwen3:8b 후보/N/A를 구분한다. 기존 정상 GeoLLM API/UI·운영 DB/원장은 변경하지 않았다. 최신 전체 시험·보존·이해자료·다음 수락 조건은 인계서의111~114 절을 따른다. 이 변경만으로 Data/ML/운영·기관UAT 전체 완료를 선언하지 않는다.
