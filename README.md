# Indonesia GeoAI–MLOps–SDSS

GitHub 연결 및 게시 범위는 [Git 게시 기록](docs/implementation/git_publication_20261017.md), 담당 영역별 남은 핵심 작업은 [완료·잔여 과제 감사](docs/implementation/109_area_completion_audit.md)를 확인하세요.

개발 원리와 발표 준비는 [이해 에이전트 자료](docs/understanding/INDEX.md)에서 시작하세요. [1분·5분 발표 대본](docs/understanding/presentations/1MIN_5MIN_SCRIPT.md), [예상 질문](docs/understanding/presentations/FAQ.md), [역할 규격](docs/agents/UNDERSTANDING_AGENT.md)을 제공합니다. 의미 있는 개발 Gate 이후 갱신하는 문서형 역할이며 백그라운드 서비스가 아닙니다.

2026-10-17: `UI/` 참조 7개 메뉴·6개 모델 Workspace와 검증 Result 어댑터를 통합했습니다. [UI 구현·제약](docs/implementation/23_ui_completion.md), [최신 재개 인계서](docs/implementation/00_next_session_handoff.md)를 확인하세요. 실자료 학습·과학 검증·기관 운영 승인은 별도 gate입니다.

추가 요청에 따라 PNG6종의 SDSS 헤더·사진 메뉴·분야별 분석 대시보드를 재현했습니다. 실제 위성 기저지도와 검증 대기 값으로 동작하며 시안의 가상 분석 수치를 표시하지 않습니다.

> 다음 세션을 이어갈 때는 [마스터 프롬프트 기준 구축 현황·재개 인계서](docs/implementation/00_next_session_handoff.md)를 먼저 읽으세요. 최신 실행상태를 다시 확인한 후 문서에 지정된 담당 경로별로 병렬 작업을 재개합니다.

인도네시아 기후행동 플랫폼의 LCLUC 우선 개발 체크포인트입니다. 데이터 수집, 실제 PyTorch CPU 학습·추론, 변화면적 계산, FastAPI, React/MapLibre를 구현했습니다. 전체 계약사업 완료 또는 실자료 독립 정확도 검증을 의미하지 않습니다.

우선 수집 범위는 First Group의 South Sulawesi·Gorontalo·Southeast Sulawesi·Banten·West Java·East Java6주이며2020~2025년 연차별36개 조합을 관리합니다. 기존 중부 자바 포함3지역 baseline은 초기 기능시험 이력으로 구분합니다.

## 개발 기록 읽는 순서

1. [요구사항·TECH-4/5 원문 추적](docs/01_요구사항_분석.md)
2. [아키텍처·API](docs/02_시스템_아키텍처.md)
3. [병렬 개발 순서·체크포인트](docs/03_개발_로드맵.md)
4. [충분한 자료 수집 기준](docs/04_데이터_수집계획.md)
5. [시험·인수 기준](docs/05_검증_및_인수기준.md)
6. [데이터 모듈 개발기록](docs/06_데이터수집_개발기록.md), [LCLUC 개발기록](docs/07_LCLUC_개발기록.md), [SDSS 개발기록](docs/08_SDSS_개발기록.md)
7. [통합 결과](docs/09_통합검증_개발기록.md), [STAC 네트워크 진단](docs/10_STAC_네트워크진단.md)
8. [First Group 품질·분할 계획](docs/11_FirstGroup_데이터품질_계획.md), [좌표·픽셀 정합 감사](docs/12_영상라벨정합_감사.md), [학습 설정·클래스 분포 감사](docs/13_학습설정_감사.md)
9. [연차 수집 중단 원인·확보량·재학습 조건](docs/14_연차수집_실패분석_및_재학습판정.md)
10. [후속 병렬 개발·재수집 기록](docs/15_후속개발_및_재수집_기록.md)
11. [충분 학습자료 단계별 수집](docs/16_충분학습자료_단계별수집계획.md), [연차 공개 참조 조사](docs/19_연차토지피복_공개참조_조사.md)
12. [학습·재개 실험 기록](docs/17_대량패치_재학습_기록.md), [MLOps·SDSS 연계 검증](docs/18_MLOps_SDSS_연계검증.md)
13. [대량 수집·학습·통합 실행 기록](docs/20_대량수집_학습_통합실행.md)
14. [Animate·Swipe 개발 기록](docs/21_Animate_Swipe_개발기록.md)

## 로컬 실행

Python3.11+, Node20+와 npm을 사용합니다. 아래 명령은 저장소 루트의 PowerShell 기준입니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
.\scripts\start-api.ps1
```

API: http://127.0.0.1:8000/api/health, OpenAPI: http://127.0.0.1:8000/docs.

별도 터미널:

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1
```

브라우저: http://127.0.0.1:5173. API 주소는 frontend의 VITE_API_BASE로 설정합니다. 공유 환경은 GEOAI_API_TOKEN을 설정하고 권한별 운영 인증을 추가해야 합니다. 기본 실행은 루프백 한정입니다.

```powershell
.\scripts\test.ps1
python scripts/diagnose_stac.py --help
python scripts/collect_samples.py --help
```

실제 네트워크 진단/수집 명령과 성공·실패 증거는 docs10을 따릅니다. 일괄 수집은 기본 계획만 생성하며 명시적 실행옵션과 용량예산이 필요합니다. 큰 장면을 무제한으로 받지 않습니다.

## ML 입력 예

GeoTIFF를 `data` 안에 등록하고 독립 지역 3개 이상을 준비합니다. 준비 scenes는 image_path/label_path/group/scene_id/label_source/source/license/date를 포함합니다. DW는 9개 확률 밴드, WC는 label_source=worldcover를 지정합니다. prepare 결과 manifest_path를 training의 dataset_path로 전달합니다. 전체 필드와 예시는 docs07에 있습니다.

합성 CPU 시험은 실자료 정확도가 아닙니다. 운영 inference API는 배포 모델을 요구하며 실험 추론은 `app.ml.service.infer_raster`를 직접 호출합니다. 독립평가는 `/api/models/{id}/evaluate`, 검토는 `/transition`, 로컬 배포는 `/deploy`입니다.

## Docker

```powershell
docker compose up --build api
```

API 컨테이너만 실행하며 기본 데이터는 호스트 `data`에 보존합니다. PostGIS·MLflow·Kubernetes·기관/RDTR·3D·벡터 RAG는 후속 통합 대상입니다. Docker 이미지 실행은 별도 검증이 필요하며 로컬 Python 시험 결과로 컨테이너 실행을 보장하지 않습니다.

### LCLUC·GeoLLM 개발 검토 (2026-10-18)

- [GeoLLM 실제 모델·RAG·도구 호출·지연 기술검토](docs/implementation/114_geollm_technical_review.md): 현행은 LLM 없는 정형 조회. 설치 모델의 별도 실측과 Qwen3 8B 개발 후보를 구분합니다.
- [수집 결과→공통 DatasetVersion 등록](docs/implementation/111_data_pipeline_completion.md)
- [실제 TinyUNet 아키텍처·최종 오류분석](docs/implementation/112_lcluc_ml_completion.md)
- [LCLUC 통합·staging·보안·UAT 수락 조건](docs/implementation/113_lcluc_integration_acceptance.md)

- [LCLUC 로컬 실행 코어·명시 CLI](docs/implementation/115_lcluc_workflow_executor.md): 고정 입력·단일 claim·실제 시계열 추론을 격리 시험했습니다. API/UI와6밴드 제품별 보정은 후속이며 운영 승인 완료가 아닙니다.
