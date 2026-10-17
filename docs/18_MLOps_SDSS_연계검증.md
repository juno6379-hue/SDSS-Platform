# MLOps–SDSS 연계 구현·검증 기록

## 1. 목적과 검증 경계

2026-10-16 실제 출처의 완료 실험 등록부터 검증 검토, 승인·배포, 공간 추론, 변화 지도, 보고서까지 연결했다. 운영 데이터가 충분하거나 모델 정확도가 검증되었다는 뜻은 아니다. 운영 카탈로그의 기존 `baseline2021_cpu_v1_model`은 Draft 실험 모델이며 독립 평가를 충족하지 않았다. 검증 기준을 우회해 승인하거나 배포하지 않았다.

서버/API·모델 수명주기는 통합 담당, 데이터 수집은 수집 담당, 학습·제품 정규화는 ML 담당, 프런트·독립 정합 감사·연계 시험은 웹 담당이 병행했다. 각 담당 파일 밖의 API 변경은 계약을 합의한 뒤 해당 담당자가 구현했다.

## 2. 개발 순서와 API 연결

1. 모델 목록을 `ModelReview.tsx`로 연결하고 `/models/{id}/readiness`가 반환한 `allowed_transitions`, `can_deploy`, `blockers`, 체크포인트 해시 상태를 표시했다. 서버가 허용하지 않은 전이·배포 버튼은 비활성이다. 사용자가 입력한 상태나 승인 요청은 독립 평가를 대체하지 않는다.
2. 완료 실험의 `report_path`를 `/models/register-experiment`로 제출하는 선택적 입력을 추가했다. 서버는 체크포인트·데이터셋 버전·보고서 해시를 검사하고 Draft로만 등록한다. 등록 성공이 독립 평가 완료가 되지는 않는다.
3. 모델의 실제 test OA/mIoU와 클래스별 IoU·precision·recall·F1, 참조 종류를 함께 표시했다. 약한 라벨과의 일치도를 독립 정답 정확도로 표시하지 않는다. 독립 평가 요청은 전문가 참조 진술 및 출처를 포함하는 실제 JSON으로 제출하며 작업을 추적한다.
4. 배포된 모델 선택을 공간 추론 입력의 모델 ID와 연결했다. 제품별 정규화 모델은 실제 calibration 근거 경로·SHA·scale·offset 및 입력 영상 SHA·scene ID·밴드명 계약이 필요함을 안내한다. 서버가 등록된 배포 체크포인트를 선택한다.
5. `AnalysisReview.tsx`에서 저장된 실제 분석을 선택하고 `/analyses/{id}/map-data`의 WGS84 GeoJSON·bbox를 MapLibre에 표시했다. 작은 실제 도형을 확인할 수 있게 bbox 확대 상한을 18로 조정했다. 통계는 전체 래스터 결과이며 제한된 벡터 피처 수에서 면적을 다시 계산하지 않는다.
6. 분석 보고서 미리보기와 인증 헤더를 유지하는 파일 다운로드를 연결했다. GeoTIFF·전이 CSV·GeoJSON·보고서 경로는 서버 응답이 있을 때 표시한다. 분류지도 간 변화와 독립 변화 정확도 검증은 구분한다.
7. `patch_inventory` 실제 검증 재고, split 수, 클래스 픽셀 비율을 수집 요약과 분리했다. 후보 2,304개나 목표 1,000패치를 실제 완성 패치로 표시하지 않는다.

## 3. 자동 통합 시험

`tests/test_mlops_sdss_flow.py`는 임시 데이터 루트·임시 SQLite·아주 작은 합성 래스터와 체크포인트를 사용한다. 운영 카탈로그·운영 모델을 변경하지 않는다. 통합 담당의 정상 실행 환경에서 **5시험 전체 통과, 20.106초**를 확인했다.

| 시험 | 실제 검증 내용 | 과학적 해석의 제한 |
|---|---|---|
| 평가 경계 | 실제 평가 서비스가 합성 모델의 독립 평가를 거부, 승인·배포 차단 | 합성 모델을 독립 검증 모델로 만들지 않음 |
| 전체 경로 | 격리 mock 독립평가 응답으로 수명주기 계약 검증 후 실제 소형 추론→변화 계산→map-data→보고서/산출물 응답 | mock 평가 응답은 API 계약 시험용이며 성과 증거가 아님 |
| 해시 변경 | 검토 이후 체크포인트 변경 시 배포 409 차단 | 평가가 다른 체크포인트로 이전되지 않음 |
| 격자 오류 | 반 픽셀 어긋난 두 시점 입력이 실패하고 분석이 등록되지 않음 | 단순 CRS 동일만으로 정합 통과하지 않음 |
| 완료 실험 등록 | 파일·보고서·데이터셋 SHA 확인, 승인 플래그가 있어도 Draft, 중복 ID 거부 | 임시 수작업 합성 보고서를 실제 학습 성과로 주장하지 않음 |

서브 환경은 Windows asyncio 소켓 초기화 제한으로 TestClient가 멈추는 현상을 확인했다. 동일 시험을 통합 담당 환경에서 수행해 위 결과를 얻었다. 제한을 우회하거나 시험 성공을 추정하지 않았다.

## 4. 실제 브라우저 합성 지도 검증

Computer Use 스킬 절차로 Chrome에서 격리 API 8001·격리 Vite 5174를 검증했다. `scripts/serve_sdss_fixture.py`는 임시 루트에만 자료를 생성하며 화면 상단과 분석에 **합성 fixture·실제 정확도 아님**을 표시한다. 운영 API 8000·UI 5173과 분리했다.

16×16 픽셀의 10m 합성 클래스 지도 두 장에서 중앙 8×8을 변경했다. 실제 분석 응답은 유효 256픽셀, 전체 25,600m², 변화 **6,400m²·25.00%**였다. 실제 WGS84 GeoJSON **1개 polygon**이 지도에 주황색으로 표시되었고 bbox 이동을 확인했다. 외부 기저지도 타일 일부 실패는 경고로 표시되었으며 자체 변화 도형은 렌더링되었다.

보고서 미리보기에서 전이 행렬과 합성 경고를 확인했다. 다운로드 버튼으로 실제 `analysis-synthetic-map-fixture.md`가 사용자 Downloads에 생성되었고 파일 크기는 **4,382 bytes**였다. 이 파일은 합성 지도 기능 시험 산출물이다. 브라우저 다운로드 이벤트 대기는 시간 초과했지만 실제 파일 존재·크기·첫 문장을 파일 도구로 확인했다. 합성 면적이나 mock 평가 수치를 운영 성과로 포함하지 않는다.

검증 후 담당자가 격리 서버를 종료하고 임시 데이터 루트를 정리했다. 작업 Chrome은 운영 5173으로 복귀했다.

## 5. 운영 읽기 검증과 현재 제한

최신 운영 API를 재기동한 뒤 실제 모델 화면에서 기존 Draft 모델의 체크포인트 해시 ‘일치’, 독립 평가 미충족 blocker, 승인·검증 전이 및 배포 버튼 비활성을 확인했다. 실제 등록·평가·승인·배포·재학습을 브라우저로 실행하지 않았다.

대시보드의 검증 재고는 확인 시점에 실제 2패치(train 0/val 1/test 1)였고 클래스별 픽셀 비율을 실제 응답으로 표시했다. 이후 수집이 진행 중이므로 이 시점 수치를 전체 프로젝트의 최종 수치로 고정하지 않는다. 6개 주×2020~2025년 목표 36셀, 수집 후보·성공 창·가용 라벨·품질·학습 적격 패치는 각각 다른 단위다. 실제 대량 자료와 완료 실험이 확보되면 API 재조회와 독립 감사를 추가 수행해야 한다.

최종 웹 빌드 `npm.cmd run build`는 TypeScript 통과·38모듈·16.73초·종료 코드 0이다. CSS 79.41kB(gzip 12.66kB), JS 1,329.94kB(gzip 371.33kB)이며 MapLibre 포함 큰 청크 경고가 남았다.

## 6. 정합 감사 연계

정합 감사의 기존 실제 증거는 `data/audits/recovery32-alignment.json`의 WC 2쌍 전 픽셀 재현 성공이며, 독립 지상 정확도는 아니다. 큰 원본 창 1024²에서 자른 256² 패치는 원본 affine→패치 affine로 직접 재투영하고 source_window/window_in_source를 보고서에 보존하도록 확장했다. 동일 원본 SHA의 반복 읽기는 프로세스 내 경로·크기·mtime·ctime 키로 줄이며 파일 변경 시 재계산한다. 읽는 도중 변경되면 실패한다.

ESRI와 WC 원시 코드표를 분리하고 ESRI cloud10/NoData0은 학습 ignore255, water1은 학습 water0으로 검산한다. rangeland11은 grass와 shrub의 합성 의미이므로 WC grass와 같은 의미라고 주장하지 않는다. 선택 보고서의 모든 행·지원되는 실제 쌍의 모든 픽셀을 검사하며 전체 주 면적·원격 전체 COG의 전수 검증으로 확장해 표현하지 않는다. 신규 수집 실행 완료 전에는 해당 산출물을 감사 성공으로 기록하지 않는다.

## 7. 병렬 수집 lane B 로컬 계획 후속

웹 UI 빌드 완료 뒤 East Java/Banten/West Java의 공간 보완 후보를 로컬에서 계산했다. `scripts/plan_lane_b_candidates.py`는 공개 주경계의 안쪽 1.8~7.4km 띠에서 각 주 최대8개, 합계24개1024창 후보를 `data/first-group-training-esri-v2/lane-b-candidates.json`에 저장한다. 기존 v1 4center의1024창 footprint와 겹치는 후보를 제외하고 원래 ID·좌표를 변경하지 않는다. 창마다 256패치 중95%주내부 면적 가능한 개수를 계산하되 실제 픽셀 중심 mask·80%유효품질 판정을 대신하지 않는다. 경계 인근에는 해안과 다른 주 사이 경계가 함께 포함된다.

도시·농경·주내수역·나지는 탐색 의도이며 실제 클래스 존재가 확인되지 않아 `class_presence_verified:false`, `label_evidence:null`로 남겼다. 동년2020~2025 ESRI약라벨 계약을 명시하고, 해양 등 주밖 픽셀은 실제 패치에서 제외하도록 요구했다. 후보는 수집 담당에게 전달했으며 실행승인은false다. 담당자별 독립 네트워크 수집을 하지 않았고, 실제 병렬 실행은 공유 예산 원장·글로벌2초간격·첫429시전체중단을 갖춘 단일 coordinator만 담당한다. 이 로컬 계획을 원격2worker실행 증거로 표현하지 않는다.

## GMAIS master §9–10 후속 UI

새 마스터 문서에 따라 Agent Center·GeoQuery·표준 same-origin /v1 클라이언트·MOCK_ONLY 게시 차단을 추가했다. GMAIS v0.2는 초기 저장소 조사에서 미발견했으나 실제 패키지를 찾아 `contracts/upstream/GMAIS-v0.2`로 보존한 뒤 원본 OpenAPI·Schema를 읽었다. 현재 SOURCE_FOUND이며 초기 SOURCE_MISSING 판단을 정정했다. 표준 Job/Result 상태와 validation_level을 구분하고, Workflow 계획 endpoint는 원본 OpenAPI에 없는 RFC 확장임을 표시한다. 실제 데이터·모델 정형 조회의 브라우저 증거, 남은 gap, 표준 API의 라이브 연동 대기는 `docs/implementation/22_ui_sdss_geollm_evidence.md`에 기록했다.

### 표준 API 라이브 후속 확인

실제 Registry/Manifest/Capability/Readiness HTTP200, 명시적 계약 fixture Job 요청409, 동일 Job ID·Trace의 BLOCKED 조회200, Result409를 확인했다. 브라우저에서도 같은 Job/Trace와 Result·취소 버튼 비활성을 확인했다. RFC 계획은 실제 브라우저 응답 PLAN_ONLY/BLOCKED/execution_started=false이며 과학 추론·Result·지도·보고서를 만들지 않았다. 고정 Job은 `job-4c21cb611db54fffb798879453d2ffc6`, Trace는 `ui-contract-5d69cd44a4c14e26aa1a699df2372487`다. 시각·JSON/헤더·재현 경로·raw Result 탭의 브라우저 차단 한계는 docs/implementation/22_ui_sdss_geollm_evidence.md 최종 절과 frontend/evidence/gmais-live에 남겼다.

최종 브라우저 후 빌드 시도는 TypeScript 단계 후 Vite가 main.tsx realpath에서 EPERM 환경 제한으로 실패했다. 이전 성공한42모듈 빌드 근거와 구분한다. 정상 권한 재시도는 통합 담당의 추가 재시도 중지 메시지 전에 이미 시작했으며, 권한·보안 우회는 하지 않았다.

이미 시작된 정상 승인 빌드 재시도는 종료0으로 완료되었다. TypeScript 통과·42모듈·32.65초, CSS81.65kB(gzip13.16kB), JS1,356.73kB(gzip378.56kB)이며 큰 청크 경고만 남았다. frontend/evidence/gmais-live/build.log는 앞선 EPERM 실패 로그이고 build-success.json은 후속 실제 성공 출력의 구조화 기록이다. 두 결과를 구분해 보존했다.
