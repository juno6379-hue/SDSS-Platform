# 109. 영역별 완료 범위·잔여 핵심 과제 재검토

상태: **읽기 감사 / PLANNED 대기열**. 2026-10-17 개발 기록과 현재 소스를 대조했다. 이 문서는 신규 구현·수집·QA·학습·UI 작업을 시작하거나 전체 프로젝트 완료를 선언하지 않는다. Git commit/push는 개발 산출물 보존이며 과학·운영·기관 인수를 뜻하지 않는다. 실제 Git 결과는 Root의 별도 실행 근거로 확인한다.

## 판정 기준과 읽은 근거

`완료`는 명시한 제한 범위의 코드·시험·관측 완료다. **VERIFIED_REAL**은 해당 실제 파일/로컬 UI 관측 범위만, **TESTED_SYNTHETIC**은 합성·격리 시험만 뜻한다. 외부 납품·인증·분야 판단이 필요한 항목은 **BLOCKED**, 개발 가능한 후속 계약은 **PLANNED**로 구분한다. 내부 구현 완료와 운영 서버 적용·독립 과학 검증·기관 승인은 서로 다른 종료 조건이다.

상위 요구는 [요구사항 추적표](../01_요구사항_분석.md), [개발 로드맵](../03_개발_로드맵.md), [인수 기준](../05_검증_및_인수기준.md)을 따른다. 초기 문서의 미수집/77패치 등 당시 숫자는 현재 재고가 아니다. 현행 근거는 [통합 gap](04_gap_analysis.md), [데이터 진행](progress_data.md), [인계서](00_next_session_handoff.md), [운영 원장](../../CONTINUOUS_DEVELOPMENT.md), [ML gap 이력](04_gap_analysis_ml_draft.md)과 아래 최신 단위다. 제안서의 27개월 D1~D21·기관 RBAC/3D/edge 범위까지 이번 로컬 개발 완료로 계산하지 않는다.

## 현재 수치의 출처를 섞지 않는다

| 구분 | 확인된 범위 | 해석 제한 |
|---|---|---|
| 원본 재고 | 물리 1384 / 적격 1111, train/val/test 628/233/250 | 합산 manifest의 기존 재고이며 후보 QA와 다른 입력이다 |
| staging 후보 QA | 후보 물리 1368 / 적격 1095, 628/217/250, 차단 4 | [73](73_candidate_readiness_qa.md)의 실제 QA-only 1회. 학습 실행·준비 승인 아님 |
| 나지 class7 | 픽셀 1418/209/1025, 기여 패치 0/0/0 | [76](76_bare_class_requirements.md)의 저장 집계. split 바닥 부족 0/47/0, 기여 최소 5씩·ratio 세 split 미달 |
| 기여 패치 필요 범위 | train 0..5 / val 0..0 / test 0..4; 집계 필요량 차이 0/1071/255 | [108](108_bare_patch_feasibility.md)의 현재 집계 정수 모형. 미래 수집량·실제 분포·재라벨링 지시가 아님 |
| 수집 pending | Banten/West Java 2023 각 68,157,440B, 합 136,314,880B | 두 terminal worker 결과·source 보고서가 없다. 예약은 전액 보존 |
| 원장과 run 요약 | 원장 신규계상 1,933,512,405B / run 1,865,354,965B, 차이 68,157,440B | 차이만으로 특정 crash 지점·정산 가능액·부정확한 환불을 확정하지 않는다 |
| 모델·Job | 이전 보존 관측의 모델1은 Draft·독립평가 미완료, 기존 BLOCKED Job2 | 이번 문서 감사에서 운영 DB를 다시 열거나 새 레코드를 생성하지 않았다 |

수집 메타데이터의 새 읽기 근거는 [별도 조사](../../evidence/integration/bare-class-patch-feasibility-collection-next-review-20261017.json)다. 원장 SHA `154004a2527c7ef6e93bec0c8a3ebf00a2af8e0683a1d4ed5252d59769da74a8`와 run SHA `0e8dd6ef449e5e7397d02393def95a54cafedc5a58722ec93df56e39dc554a86`를 확인했다. 두 config→ledger·정규화 config→window-state 연결은 맞지만 terminal 누락을 대체하지 못한다. 각 상한−실측 33,554,432B는 환불액이 아니다. 빈 execution lock 존재와 실제 프로세스 종료·재개 승인을 구분한다.

## 영역별 완료와 남은 수락 조건

| 영역 | 제한 범위에서 완료된 것 | 외부/실자료 차단 | 내부에서 남은 핵심 구현 | 완료로 볼 수 있는 근거 |
|---|---|---|---|---|
| 수집·복구 | 제한 예산·reserve/settle·재개 차단, [24](24_collection_recovery_plan.md) snapshot 계획·stale 검증, [45](45_recovery_terminal_reconciliation.md) terminal 내용, [46](46_recovery_aggregate_reconciliation.md) 참조/중복·누락, 47~57 물리/공간 companion | pending2 terminal·완전 전송 계측·적용 시각 프로세스 종료 책임 근거 없음 | 아래 110 후보의 commit 단계·멱등 계약 → 후속 durable journal/원자적 coordinator·복구 실패 시험. 기존 collector에 즉시 적용하지 않음 | 임시 원장/aggregate에서 각 중단 지점·재호출·중복·충돌 시험, 원본·예산 보존. 운영 적용은 별도 승인·terminal/계측·프로세스 근거 필요 |
| 데이터·AI-ready | 고정 ID/version/SHA Registry, 경로·출처·입력/계보 검사, 원본 보존과 후보 plan/materialize/stage/QA 분리 | class7 대표성·독립 참조·공식 경계/분야 의미 적합성. 후보의 일부 누출 blocker 미관측을 전체 독립성으로 볼 수 없음 | 승인된 새 자료만 별도 버전·확인서로 접수하는 절차와 실패 복구; 입력 Registry/모델 resolver 권한 계약 | [26](26_dataset_version_registry_core.md), [73](73_candidate_readiness_qa.md)의 pin·동일 정책·고정 4/1/1 분할 보존 및 최신 QA, 기간/품질/라벨/경계/독립성 근거 |
| ML·LCLUC | Tiny U-Net CPU train/infer·정규화·지표·변화 계산, readiness·split·QA guard, 76/108 부족 설명 | 후보 차단4·학습 BLOCKED. class7 세 split의 ratio/기여 부족 및 val 절대 픽셀 부족. 전문가 독립 라벨/인수 기준 필요 | 자료 인수 뒤 동일 정책의 새 QA → 통과한 버전만 재현 가능한 학습·독립평가·모델 카드와 승인 패키지로 연결 | 최신 manifest/QA/checkpoint/독립평가 SHA·환경·seed·제품 정규화/분류체계 기록. 공개 의사라벨 일치도와 독립 과학 정확도를 분리 |
| 모델 승인·MLOps | 완료 실험 Draft 등록·중복 거부·선택적 버전 선언, hash 검사·평가/상태 전이·로컬 배포 이력; 100~106의 메타데이터 관측 | 기관별 검토 권한·서명·책임자·독립평가와 실제 승인 모델 없음 | 유형별 artifact/검증 분기·immutable 버전/동시성/트랜잭션 정책, 승인·배포·rollback adapter | [08 SOP](08_model_type_validation_sops.md), [MLOps–SDSS 이력](../18_MLOps_SDSS_연계검증.md)의 gate를 우회하지 않는 승인/배포·변조·실패 복구 시험과 기관 증거 |
| Orchestrator·입력 연결 | plan-only·입력 Registry/계보·차단 전파·ordered binding capture·caller-pinned Workflow/Job metadata 대조, 105/106 별도 모델 대조, [107](107_workflow_dependency_order.md) 정렬 공통화 | 승인된 실행 모델·실제 DatasetVersion/자료 ACL·외부 Agent 런타임 부족 | 실제 Job 실행 adapter, DAG 스케줄링·선행 Result→후속 입력의 명시적 동적 바인딩·retry/timeout/cancel·재시작/중복·보상 계약 | 고정 ID/version/SHA·Trace를 유지한 격리 E2E, 실패/재시작 exactly-once 또는 명시한 at-least-once 정책, 모델/입력·기관 gate 거부 시험. DAG 정렬·MATCH만으로 실행 불가 |
| UI·SDSS | PNG 참조 대시보드/카탈로그·하위 탐색·6 Workspace·공통 SVG, 실제 API 읽기·오류·stale/뒤로가기 방어, 지도 GeoJSON/다운로드·보고서 연결 | 독립 검증된 6모델 실제 Result·기관별 업무 UAT 없음 | 실제 검증 Result에 대한 COG 타일 렌더러·지도/시계열/변화/행렬/핫스팟/지역비교의 모델별 실제 데이터 계약·empty/error/accessibility/반응형 UAT | [106 UI](106_workflow_model_record_handoff_ui.md), [Result projection](../../backend/app/sdss_results.py), [AnalysisReview](../../frontend/src/AnalysisReview.tsx)의 실제 Result ID·자산·통계·보고서 일치. 예시 PNG 수치와 시연 데이터를 운영 실측으로 표시하지 않음 |
| 운영·보안·인수 | 로컬 SQLite·API token·자산 경로/해시 검증·Docker 개발 구성·시험·인계/이해자료 | staging/production 접근·기관 RBAC/자료 ACL·운영 승인·공식 인수 주체 미확정 | CI 품질/보안·의존성/SBOM·migration/백업복구·관측/로그/성능·실배포 rollback·필요 시 PostGIS/분산큐/MLflow adapter | [compose](../../compose.yaml)는 현재 API 개발 구성이다. MLflow 설치 감지/로컬 이력을 운영 Registry로 계산하지 않음. staging 실행·복구/성능/보안/UAT와 기관 서명 필요 |

## 6모델의 상태를 개별로 인수한다

현재 [실제 manifest 생산 코드](../../backend/app/gmais_api.py)의 `_agent_manifests()`는 LCLUC만 implemented=True, readiness=BLOCKED로 둔다. 나머지 다섯 모델은 **NOT_IMPLEMENTED / external-adapter-required**다. 화면 여섯 개·manifest 여섯 개는 과학 실행기 여섯 개가 아니다. `provider='GreenBlue local platform'`도 외부 기관 책임이나 납품 완료를 인증하지 않는다.

| 모델 | 지금 있는 것 | 남은 핵심 및 검수 |
|---|---|---|
| LCLUC | 학습·추론·변화 baseline 코드, gate와 UI | 적격 최신 자료·독립 평가·승인/배포 후 실제 GMAIS 성공 Job→Result→지도/보고서 연결 |
| 기후 상세화 | interface·Workspace | 납품 runtime/API 또는 구현 책임·다운스케일링 입력/모형·시공간 검증/불확실성·기관 계약 시험 |
| 순 탄소발자국 | interface·Workspace | 활동자료/배출계수·단위/기준연도/경계·모형/산정 runtime·독립 분야 검수 |
| 생물다양성 | interface·Workspace | 종/서식지 자료·출처/접근권·분야 모형 runtime·공간/독립 검증 |
| 해수면 상승·지반침하 | interface·Workspace | 관측·수직기준/시나리오·물리/보정 runtime·기준면/불확실성 검증 |
| 홍수·가뭄 | interface·Workspace | 강수/수문/지형·시간창/극한현상 자료·물리/통계 runtime·사건별 검증 |

외부 다섯 모델의 소유 기관·image/API·실측자료·정확도 기준은 미확정 부분을 확정으로 쓰지 않는다. 내부에서는 공통 SDK/입출력·오류·취소·자산·단위·검증 근거와 mock 계약 시험을 준비할 수 있으나, mock 통과는 해당 분야 모형 구현·납품·과학 인수를 대신하지 못한다. 상세 원칙은 [유형별 SOP](08_model_type_validation_sops.md)와 [요구 R11/R14](../01_요구사항_분석.md)를 따른다.

## 우선순위와 다음 실행 가능한 작은 단위

1. **P0·자료 보존/복구 기반:** 원장/lock/pending을 유지하고 110 후보인 순수 commit 단계 계약을 구현·합성 시험한다. proposed 새 파일은 `backend/app/data/recovery_commit_contract.py`, `tests/test_recovery_commit_contract.py`이며 아직 구현하지 않았다. operation ID·batch/config 및 전후 원장/aggregate pin, PREPARED→LEDGER_RECORDED→AGGREGATE_RECORDED→COMMITTED 허용 전이·동일 관측 재생·충돌/역행을 검사하는 I/O0 기반이다. 모든 정산/환불/재시작/실행 승인은 false, exactly_once UNKNOWN을 유지한다. 실제 durable journal/원자적 apply는 후속이며 계약 검사 통과만으로 pending을 해제하지 않는다.
2. **P1·class7→동일 정책 QA:** 현재 부족을 근거로 분야 담당이 적격 자료·라벨 확보 방식을 정한다. 공식 권한·예산·시기/경계/제품·고정 분할·출처/겹침 조건을 충족하는 입력만 신규 버전으로 접수한다. 108의 1071/255를 미래 수집 픽셀 지시로 쓰지 않는다. 새 자료/manifest에만 별도 SHA-pin QA를 수행하고 현재 후보·과거 보고서를 보존한다.
3. **P2·QA→ML 독립평가→승인:** QA가 모든 gate를 통과한 뒤 별도 허용된 학습을 수행한다. 독립 참조·분류체계/정규화·지역/기간 성능·오차/불확실성을 검토하고 책임 있는 승인/배포 근거를 연결한다. 자료 부족 동안 내부의 평가/승인 패키지·실패/변조 시험은 준비할 수 있다.
4. **P3·승인 모델→실제 실행→SDSS:** 먼저 단일 LCLUC Job의 승인/입력 gate·자산 Result·상태 이력을 연결하고, 그 다음 DAG의 명시적 선행 출력 바인딩과 재시작·취소를 확장한다. 실제 Result가 생긴 범위부터 UI/COG/통계/보고서 E2E를 인수한다. 105/106의 메타데이터 대조 MATCH_UNVERIFIED를 resolver/모델 신원 인증으로 사용하지 않는다.
5. **병렬 외부/운영:** 외부5의 runtime·자료·검수 계약과 기관 RBAC/자료 ACL·staging·UAT를 별도로 확정한다. 내부 SDK/계약 시험·CI/보안/복구 기반은 독립 작은 단위로 개발하되 운영 배포·대규모 수집·학습을 묵시적으로 시작하지 않는다.

110 후보의 필요성은 [수집 다음 검토](../../evidence/integration/bare-class-patch-feasibility-collection-next-review-20261017.json)와 [collector](../../scripts/collect_training_parallel.py)의 `finalize()`·[CollectionLedger](../../backend/app/data/budget.py)의 `settle()`에서 확인했다. 현재 순서는 원장 settle 저장→aggregate 수정/저장→run-result 저장이며 이미 settled인 batch를 다시 settle하면 거부한다. 이는 중단 지점별 전이·멱등 검증이 필요한 설계 공백이며, 특정 crash가 실제 관측되었다거나 현재 차이를 이 원인으로 입증했다는 뜻은 아니다.

## 변경·시험·인계 경계

이번 작업에서 추가한 것은 이 감사 문서 한 파일뿐이다. 소스·환경·원본·원장·lock·예약·분할·모델을 변경하지 않았고 운영 API/DB·다운로드·수집·새 QA·학습·배포를 실행하지 않았다. 기존 시험 수를 새 시험 실행으로 표현하지 않는다. 107의 전체 1069건/1068 PASS/기존1 SKIP와 108의 관련66/독립26 PASS는 각 문서의 이전/해당 단위 근거다. 108의 별도 oracle 1015집계/29001분포는 unittest 건수에 더하지 않는다.

Root는 이 대기열에서 실제 배정·구현·시험·보존·관련 문서와 이해자료 갱신을 완료한 단위만 완료로 보고한다. UI 영향 기능은 web_ui에 상태/오류/API 계약을 넘겨 실제 브라우저 적용까지 구분한다. 10분 보고·예약 ACTIVE와 실제 agent/수집/학습 실행 상태를 계속 구분하며 전체 미완료 상태를 유지한다.

## 사용자 확인 — 외부 실행기·독립 검증 라벨 미확보
+
+사용자는 다른5개 모델 실행기(API/SDK/코드)와 독립 정확도 검증용 라벨 자료가 별도로 준비되어 있지 않다고 확인했다. 해당5개 모델은 미연결·실행기 미구현/미제공, 독립 검증 라벨은 미확보로 관리한다. 기존 약한 라벨/학습자료까지 없다는 뜻은 아니며 보존한다. 자료 위치를 이미 확보한 것처럼 가정하거나 과학·운영 승인으로 대체하지 않는다. 외부 의존은 BLOCKED로 명시하고 내부 복구/데이터/ML/오케스트레이터 구현은 계속한다. 근거: `evidence/integration/recovery-commit-contract-external-dependencies-20261017.json`.
+
### 110 후속: commit 단계 선언 검사

[110 구현 문서](110_recovery_commit_contract.md)의 독립 순수 함수가 caller의 단계·세 target SHA·재관측·충돌을 검사한다. 기존 이 문서의 실자료 검사/형식·수집기·예산코드는 바뀌지 않았고 실제 journal/정산·집계/재개 coordinator는 미연결이다. 기존 pending2/예약·원장-run 차이를 해결하거나 exactly-once를 인증한 것이 아니다. 최종 신규14·관련66PASS/1SKIP·독립62PASS/1SKIP·보존 범위는 `evidence/integration/recovery-commit-contract-live-integrity-20261017.json`을 따른다. 해당 내부 선언 검사만 완료이며109의 실제 지속화/복구 수락 조건은 남는다.
