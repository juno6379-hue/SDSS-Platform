# Unit 360 — 두 요구 문서 통합 추적표와 Root 검증

## 1. 범위와 결론

대상 문서는 다음 두 개다.

1. `UI/GreenBlue_CODEX_LCLUC_GeoServer_1st_ML_Inference_2nd_ChangeDetection_Repair_v1.1.md`
2. `UI/GreenBlue_CODEX_LCLUC_PostGIS_Coverage_MLOps_Deployment_Master_v3.0.md`

세 작업자가 G6/G11 secondary·변화 경로, G9 MLOps API, 요구사항·화면 계약을 병렬로 점검했고 Root가 코드·시험·실행 서비스·실제 브라우저·운영 파일 지문을 통합 검증했다. 이번 단위의 결과는 **실행되지 않은 학습·예측·이관·게시·승격을 성공으로 표시하지 않는 fail-closed 기준선**이다. 전체 프로젝트는 미완료다.

## 2. 권위 증거와 금지 범위

| 항목 | Root 확인값 | 상태 |
|---|---|---|
| Git HEAD | `375f037379ac878353b652591d87a17efa51f021` | `VERIFIED_REAL` |
| 운영 source | 69,564,847 bytes, SHA-256 `0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658` | `VERIFIED_REAL` |
| 운영 ledger | 68,395 bytes, SHA-256 `d5ee31ff7970adaaa6b166805c240616efa8e9af713bb8394c7a166346f21c91` | `VERIFIED_REAL` |
| catalog | 184,320 bytes, 29 logical rows, SHA-256 `d08418826b858deccad972d5326cfaa2122f56aa13faef0fc1e3628650fdfc45` | `VERIFIED_REAL` |
| 데이터 준비성 | 1,779행, 적격 1,407(865/292/250), scene split conflict 1, 클래스 gate 실패 | `BLOCKED` |
| 실행 | collector·원장 쓰기·원격 실행·실학습·승격·운영 배포 0 | `VERIFIED_REAL` |

Unit355 catalog incident의 복구 증거는 `evidence/integration/unit355-catalog-incident-20261021/`에 보존했다. 보존된 과거 lock 파일은 현재 실행 lock이 아니다.

## 3. Repair v1.1 추적표

| Gate | 구현·검증 결과 | 상태 | 다음 조건 |
|---|---|---|---|
| AS-IS 감사 | 권위 source·ledger·catalog와 프로세스·서비스 중복 여부 확인 | `VERIFIED_REAL` | 변경 때마다 지문 재확인 |
| G1 수집·전처리 | 기존 1,779행과 품질 gate를 감사했으며 새 수집 0 | `VERIFIED_REAL` / `BLOCKED` | 승인된 증분 수집과 동일 mask 정책 필요 |
| G2 GeoServer 1차 | 로컬 primary TIFF 54개 존재. 합성 mask는 `TESTED_SYNTHETIC`; named layer 전수 게시 미검증 | `BLOCKED` | Capabilities exact enumeration, GetMap, 원본 픽셀 대조 |
| G3 학습 준비·검증 | 권위 split 865/292/250, conflict 1과 class gate 실패, baseline 미고정 | `BLOCKED` | conflict 제거, 클래스 0.5%/기여 5 충족, 독립 holdout |
| G4 연차 추론 | checkpoint·실행 manifest·prediction artifact 0 | `BLOCKED` | 실행된 모델과 입력/출력 SHA 필요 |
| G5 GeoServer 2차 | 합성 prediction 생성 제거, 실제 secondary 0 | `TESTED_SYNTHETIC` / `BLOCKED` | 검증된 prediction/confidence/mask와 named publication |
| G6 변화탐지 | 고정·난수 통계 제거, 모든 미측정 값 null | `TESTED_SYNTHETIC` / `BLOCKED` | 동일 grid의 T1/T2 model prediction과 common-valid mask |
| G7 UI | 참조지도 Swipe API·화면·0/50/100·키보드 실제 확인 | `VERIFIED_REAL` | 과학 결과는 prediction/pixel API 전까지 차단 |
| Job·게시 상태 | 성공 상수 제거, reason code와 409 write-free 차단 | `TESTED_SYNTHETIC` | 실행 증거 기반 상태 전이 필요 |
| 자동·사람 수용시험 | 집중 시험·빌드·로컬 HTTP·브라우저 수행 | `VERIFIED_REAL` / `TESTED_SYNTHETIC` | drag/touch·지도 동기화 자동 E2E 보강 |

## 4. Master v3.0 추적표

| Gate | 구현·검증 결과 | 상태 | 다음 조건 |
|---|---|---|---|
| G0 Baseline | 원본·원장·catalog 지문과 현재 프로세스 실측 | `VERIFIED_REAL` | 변경 단위별 snapshot 유지 |
| G1 PostGIS | schema·adapter·inspect/reconcile 구현. 무연결 script의 가짜 parity도 차단 | `IMPLEMENTED_UNVERIFIED` / `BLOCKED` | 승인된 PostGIS pilot, DDL 적용, typed backfill, reconcile, rollback drill |
| G2 전후 coverage | 432 inventory와 실제 coverage 측정을 분리, 수치 null | `VERIFIED_REAL` / `BLOCKED` | 36개 주·연도 동일-grid boundary/mask union |
| G3 수집 | 현재 단위 신규 수집 0 | `BLOCKED` | 승인·예산·중복 방지·bounded 실행 필요 |
| G4 전처리·합성 | 기존 source window 118개 실물 감사, 주 전체 합성 아님 | `VERIFIED_REAL` / `BLOCKED` | 장면 provenance·동일 grid·실제 annual composite |
| G5 복구율 | before/after pinned evidence 없어서 null | `BLOCKED` | 같은 AOI·분모·mask 정책의 두 버전 |
| G6 GeoServer 1차 | local primary 54, 합성 18, exact named publication 없음 | `BLOCKED` | 실제 registry merge와 전수 WMS 검증 |
| G7 AI dataset | 권위 보고서 기반 fail-closed split, baseline `NOT_PINNED` | `VERIFIED_REAL` / `BLOCKED` | spatial/class gate와 baseline 고정 |
| G8 학습·평가 | 고정 264/OA/F1/mIoU는 deterministic scenario | `TESTED_SYNTHETIC` / `BLOCKED` | 실제 학습·checkpoint·독립 평가 |
| G9 MLOps | summary 2.0, experiments·retrain·approval fail-closed | `TESTED_SYNTHETIC` / `BLOCKED` | 검증된 run·metric·사람 승인 |
| G10 연차 추론 | 실 prediction 0 | `BLOCKED` | immutable inference result 필요 |
| G11 GeoServer 2차 | 증거 manifest 검사만 구현 | `TESTED_SYNTHETIC` / `BLOCKED` | prediction 18개와 exact named publication |
| G12 변화분석 | 변화·탄소·파편화 값 null | `BLOCKED` | T1/T2 common-valid 기반 실측 |
| G13 SDSS UI | MLOps의 가상 운영 수치 제거, Swipe 실제 브라우저 확인 | `VERIFIED_REAL` | 과학 지표는 계속 차단 |
| G14 배포 | 로컬 API/UI/GeoServer HTTP 200 | `VERIFIED_REAL` / `BLOCKED` | staging/prod 보안·HA·DR·승인 배포는 미수행 |

## 5. API와 UI의 현재 계약

- `/v1/mlops/summary`: schema 2.0, `status=blocked`, 운영 모델·queue·배포 0, F1/mIoU/coverage null, verified approval 0.
- `/v1/mlops/experiments`: runs 빈 배열, best null.
- `POST /v1/mlops/retrain`: HTTP 409 `BLOCKED_NO_EXECUTED_TRAINING_OR_MEASURED_PREDICTIONS`, write 0.
- `POST /v1/mlops/approval`: HTTP 409 `BLOCKED_NO_VERIFIED_CANDIDATE_OR_HUMAN_APPROVAL_BASIS`, write 0.
- `/api/data/landcover-series`: 118 layers, 35 series, 210 comparisons, 183 reference-only, 27 blocked, model prediction 0.
- UI MLOps 화면은 unmeasured/null과 차단 이유를 표시하고 실행 버튼을 비활성화한다.
- Swipe는 참조지도 화면 비교만 허용하고 변화 통계와 pixel query를 차단한다.

## 6. Root 검증 결과

| 검증 | 결과 |
|---|---|
| G6 primary+secondary+tiles 통합 | 31 PASS, 137 warnings, 20.32초 |
| G9 MLOps router | 8 PASS, 1 warning, 14.33초 |
| G7 dataset split 전체 회귀 | 58 PASS, 425.71초 |
| MLOps UI 계약 | 1 PASS, 414ms |
| Frontend production build | 131 modules PASS, 20.08초; 기존 bundle-size warning |
| PostGIS 무실행 fail-closed | 1 PASS; 실제 PostGIS/운영 catalog 쓰기 0 |
| 로컬 서비스 | API 8002, UI 5174 및 proxy, GeoServer 8088 HTTP 200 |
| 실제 브라우저 | MLOps 차단 표시와 Swipe 0/50/100·keyboard 51 확인 |

## 7. 남은 P0

1. scene split conflict와 class coverage/contributor gate를 해결한 새 immutable dataset version을 만든다.
2. 실제 checkpoint를 생성하고 독립 holdout에서 prediction·confusion matrix·per-class metric을 측정한다.
3. 6개 주 T1/T2 prediction COG·confidence·valid mask를 동일 grid로 만들고 registry에 등록한다.
4. GeoServer Capabilities exact layer enumeration, GetMap, 원본 pixel 대조를 전수 수행한다.
5. 주 경계와 동일 mask 정책으로 36셀 coverage 및 before/after recovery를 실측한다.
6. 승인된 PostGIS pilot에서 DDL·backfill·reconcile·rollback drill을 수행한다.

이 조건 전에는 학습 준비, 모델 향상, 변화량, 전수 게시, 승격, 배포 완료를 보고하지 않는다.
