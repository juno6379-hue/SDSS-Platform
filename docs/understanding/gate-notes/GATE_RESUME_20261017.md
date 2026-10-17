# Gate RESUME 20261017 — 개발 이해·발표 준비

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `docs/implementation/00_next_session_handoff.md`; `docs/implementation/23_ml_readiness_resume_20261017.md`; `docs/implementation/23_ui_completion.md`; `evidence/integration/ml-readiness-resume-20261017.json`; `evidence/integration/resume-tests-script-20261017.log` |
| confidence | 중간: 현재 소스·기존 로그 기반; 신규 시험·학습·운영 승인 미수행 |
| status | BLOCKED: 최신 실자료 학습; 이해·발표 문서 작성 완료 |

> 발표 기준은 2026-10-17 기록이다. 시험 통과는 기존 로그의 역사적 결과이며 이번 문서화에서 재실행한 결과가 아니다. [현재성 대조](../EVIDENCE_SNAPSHOT.json).

## 한 문장 요약

실제 코드와 기존 실자료 QA·시험·UI 기록을 연결해 6개 분야 플랫폼의 구조, 학습 차단, 계약·실행·승인의 차이를 설명하는 이해자료와 발표 대본을 작성했다.

## 1분: 왜 필요한가

개발 보고서는 부품 목록이고 발표는 그 부품이 어떻게 함께 작동하고 무엇을 아직 못하는지 설명하는 안내서다. 이번 Gate는 소스 기능을 추가하는 개발이 아니라 현재 근거를 이해하고 발표하기 위한 문서 작성이다. 의사라벨·합성 시험·실자료 감사·과학 승인·운영 인수를 분리한다.

## 5분: 배경·구조·근거

원재료→검사→분석 장비→지도 작업대라는 비유로 시작한다. STAC 검색과 실제 수집을 나누고, 6밴드·라벨·품질 mask 정합과 해시로 출처를 고정한다. 모델 학습 입력의 충분성과 독립성을 검사하고, 계약이 Job/Trace/Result를 연결한다. 현재 Workflow는 계획 전용이고, SDSS는 미검증 결과를 게시하지 않는 구조다. 실제 기관 운영·외부 모델 납품·정책 판정은 미완료다.

```mermaid
flowchart LR
 A[완료된 코드·파일목록] --> B[기존 로그·QA·스냅샷 대조]
 B --> C[상태·이론·코드 연결]
 C --> D[1·5·10분 해설]
 D --> E[발표 대본·시연·Q&A]
 E --> F[다음 Gate 변경 때 갱신]
```

## 실제 코드·입출력 연결

| 업무 | 위치 | 입력 → 출력 | 근거·현재 범위 |
|---|---|---|---|
| 데이터 | `backend/app/data/service.py:search_stac`, `read_cog_window` | AOI/기간 → metadata/raster | 실제 자료 QA 기록; 재수집 미실행 |
| ML | `backend/app/ml/readiness.py:assess`, `network.py:TinyUNet` | manifest → 자격·blocker | 최신 정식 학습 BLOCKED |
| 계약 | `backend/app/gmais_api.py:create_router` | Job/Workflow JSON → 추적·상태 | 실제 DAG 실행 전 PLAN_ONLY |
| 게시 | `backend/app/sdss_results.py:project_result` | Result → 검증된 layer/report projection | fixture 검사; 승인 운영 Result 없음 |
| UI | `frontend/src/Icon.tsx:IconFrame`, `ModelAnalysisWorkspace.tsx` | 선택·상태 →6화면·SVG | 기존 로컬 브라우저/빌드 증거 |
| 근거 질의 | `frontend/src/GeoQuery.tsx`, `POST /api/query` | 정형 질문 → 기록 | 정책 RAG/자동 판정 미연결 |

CRS·격자·기간·분류 단위는 원본 manifest/검증 자산을 따라야 한다. UI bbox를 공식 경계로 바꾸어 말하지 않는다. 면적·연도별 결과는 실측/의사라벨/가정을 구분하며 새로운 수치를 만들지 않는다.

## 실제 검증 기록과 한계

| 항목 | 기존 결과 | 종류 | 뜻하지 않는 것 |
|---|---|---|---|
| manifest 재고 | 물리1,384/적격1,111, 36/36셀, 628/233/250 | VERIFIED_REAL: 기존 실자료 QA | 모델 정확도 |
| 고유 파일 해시 | 4,335개 고정 | VERIFIED_REAL: 08:49 KST QA | 이번 전체 파일 재감사·내용의 참 |
| 최신 gate | scene 충돌1+bare 불균형3+val 픽셀부족1, ready=false | BLOCKED | 수량 통과만으로 학습 허가 |
| 회귀 | `scripts/test.ps1` →197 PASS/50.284초 로그 | TESTED_SYNTHETIC: 모의·합성 포함 | 이번 재실행·현장 평가·운영 승인 |
| UI adapter |5 PASS 기록 | TESTED_SYNTHETIC | 실제 승인 Result 생성 |
| UI·SVG |6화면 확인·build PASS 기록 | VERIFIED_REAL: 로컬 UI 범위 | 6개 모델 실행기·과학 승인 |
| GMAIS | v0.2 checksum 관리된 내부 제안 | IMPLEMENTED_UNVERIFIED: 계약 호환 | BIG/컨소시엄 승인 표준 |

기준 manifest SHA `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`, readiness SHA `6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db`. [이번 읽기 스냅샷](../EVIDENCE_SNAPSHOT.json)의 현재 SHA 대조와 과거 전체 QA를 구분한다. 기존 CPU baseline Draft는 최신 자료 학습 차단과 함께 설명한다. TECH-4는 기존 조사 색인·문서 근거이며 이번 원문 전체 재검증은 아니다. 공식 서명계약·기관 R&R·주 총수 합의는 미확인이다.

## 발표 대본·질문·시연

30초: “이번에는 개발 결과를 읽을 수 있는 설명 패키지를 만들었습니다. 6개 분야 UI·공통 계약·실자료 검사의 근거가 어디 있는지 연결하고, 최신 LCLUC 학습이 왜 차단되는지 발표할 수 있도록 정리했습니다. 정확도와 운영 승인은 아직 완료로 말하지 않습니다.”

1분과5분은 [발표 대본](../presentations/1MIN_5MIN_SCRIPT.md)을 읽는다. 10분은 [현재 구조도](../CURRENT_ARCHITECTURE.md)와 기능6문서를 확장 순서로 사용한다. 슬라이드: 원재료와 검사 / 기준 모델 / 여섯 작업대 / 계약과 승인 / 다음 단계.

예상 질문: ①6개 모델 완성? →UI·계약과 실행기 구분. ②왜 차단? →scene·bare5개 blocker. ③197 PASS의 뜻? →과거 계약시험. ④자동 정책판정? →정형 읽기·RAG 미연결. ⑤운영 가능? →독립 평가·승인·배포 인수 남음. 자세한 답은 [FAQ10개](../presentations/FAQ.md), 재현 환경·기대 결과·실패 시 기록 시연은 [DEMO_STORY](../presentations/DEMO_STORY.md)다.

## 다음 Gate에서 갱신하는 방법

Root가 완료한 변경파일·실행명령·로그·데이터 종류·기준시각·SHA·승인 상태를 전달한다. 이해 에이전트는 코드와 증거를 읽고 [템플릿](../GATE_TEMPLATE.md)으로 새 노트를 만든 뒤 영향 기능 문서→대본·FAQ·시연→INDEX 순으로 갱신한다. 자료가 없으면 미확인, 계획만 있으면 PLANNED로 남긴다. 변경이 없으면 중복 산출물을 만들지 않는다. 자동 백그라운드 작업이 아니라 실제 개발 작업 시 호출하는 역할이다.

- 다음 데이터 Gate: pending terminal/전송 근거와 새 manifest 버전·대표성 계획.
- 다음 ML Gate: scene 독립성·bare 대표성·전체 readiness, 이후 독립 현장 평가·전문가 승인.
- 다음 통합 Gate: 승인 LCLUC executor·불변 Registry·표준 Result·기관 UAT 증거.
- 다음 운영 Gate: 실제 K8s/staging/rollback/monitoring·권한·기관 인수.

소스·원본자료·가중치·원장·감사로그·승인 상태는 이 문서 작업에서 변경하지 않았다.
