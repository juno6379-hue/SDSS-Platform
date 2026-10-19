# 180 — 연차 균형·명시 우선순위·나지 후보 로컬 검토 UI

상태: TESTED_SYNTHETIC / 운영 receipt 게시·서버 적용·실제 브라우저 확인은 Root 인계 후 별도 기록.

## 목적과 수량 해석

연차별 자료는 대표성을 고려해 균형 있게 확보하지만, 현재 정책의 셀별 28개는 최소 바닥이며 모든 주·연도의 같은 개수를 강제하는 할당량이 아니다. 초과 확보분으로 타 연도의 부족을 상쇄하지 않는다. 기존 자료를 삭제하거나 동일 장면을 중복 추가하여 숫자를 맞추지 않는다. 균형 표본 추출은 후속 전처리에서 공간·연차·클래스와 고정 split을 함께 검토한다.

사용자의 다음 수집 우선순위는 남동술라웨시 → 고론탈로다. 화면의 정책 표시는 실제 실행 배치·현재 worker·완료 성과를 의미하지 않는다. 완료 수량과 부족 수량은 기존 manifest 동적 집계에서 읽고 이번 변경에서 숫자를 하드코딩하지 않는다. 고정 후보 QA도 기존 pinned cohort를 유지한다.

## API additive 계약

기존 `GET /api/data/collection-status`의 `collection_targets.balance_policy`에 다음을 추가한다.

- scope: `PLANNED_COLLECTION_PRIORITY_NOT_RUNNING_JOBS`
- minimum_floor_not_equal_quota / preserve_existing_patches / deduplicate_before_enrollment: true
- priority_provinces: `[southeast_sulawesi, gorontalo]`

`collection_targets.bare_target_review`는 새 read-only projection이다. 기존 CollectionStatus의 자식 전달과 ModelReview의 기존 GET를 그대로 사용하므로 신규 HTTP 요청·polling·쓰기·버튼 집행은 추가하지 않는다. 구버전 응답에 새 필드가 없으면 기존 재고를 계속 표시하며 해당 정책·검토는 미확인으로 표시한다.

## 명시 receipt와 검증

API data_root 아래 `first-group-training-priority/latest-bare-review.json`만 읽는다. newest glob은 사용하지 않는다.

```json
{"schema_version":1,"report":{"path":"first-group-training-priority/review179.json","sha256":"<64 lowercase hex>"}}
```

`path`는 data_root 상대이며 `data/` 접두사를 자동 보정하지 않는다. 절대 경로·상위 경로·빈 세그먼트·역슬래시·콜론·제어문자·symlink·Windows reparse 경로를 거부한다. receipt 64KiB, report 2MiB 이하만 읽는다. 파일 원바이트 SHA256가 receipt와 일치해야 한다. 입력은 쓰지 않는다.

Report의 `ui_summary` 계약:

- schema_version: 1; status: `LOCAL_TARGET_REVIEW_FINISHED`
- recorded_at: timezone 포함 ISO; current_manifest_sha256: 64 lowercase hex
- execution_supported / actual_quality_verified / scientific_accuracy_validated: false
- candidate_total: 비음수 정수
- summary_by_province: 6개 주 각각 정확히 한 행. 행은 province/candidates/support_clear/overlap/local_invalid만 포함하며 각 카운트 0..10000 정수
- 행의 candidates = support_clear + overlap + local_invalid; 전체 합계 = candidate_total

179 담당과 합의한 overlap은 **과거 저장 영상 범위와의 겹침**이다. 후보 상호 겹침은 보고서 본체의 별도 검사이며 위 표의 비겹침을 집행 가능으로 확대하지 않는다. `NOT_PUBLISHED`, `INVALID_RECEIPT`, `INVALID_OR_BLOCKED_REPORT`는 합계 없이 available:false를 반환한다. 부분 실패한 보고서의 일부 행을 승인하거나 미존재를 0개로 대체하지 않는다.

성공 projection은 보고서 원본 SHA와 현재 manifest SHA의 일치 여부, 보고서 시각·경로·지문을 명시한다. 원본이 바뀌면 과거 검토 수량은 그 고정 시점의 기록으로 표시하고 최신 겹침검사·실집행 허가로 해석하지 말라는 경고를 붙인다.

## UI 범위

주별 후보 / 과거 범위와 비겹침 / 과거 범위와 겹침 / 로컬 부적합 / 원격 SCL·B02 품질을 표로 구분한다. 신규 원격 품질은 `미검사 · 집행 미승인`이다. 실제 선택 장면·B02/SCL·물리 출력·현재 원장 및 후보 상호 겹침은 집행 직전 보호 장치에서 별도 확인해야 한다. 이 변경은 실제 표적 수집 성공이나 과학적 독립성·학습 승인을 생성하지 않는다.

Frontend는 백엔드 projection의 source/current 일치 플래그를 자체 비교하고 SHA·6주 중복·합계·false 승인 플래그를 검사한다. 새 나지 검토가 잘못됐더라도 기존 유효 재고와 고정 후보 표를 지우지 않고 검토 부분만 미확인으로 표시한다.

## 시험 근거

- `evidence/integration/ui180-backend-related-20261018.log`: 수집 status 관련 19 PASS, 2.161초. 합성 임시 파일·receipt 검증이며 실제 원격 수집 시험이 아니다.
- `evidence/integration/ui180-frontend-focused-20261018.log`: adapter·기존 GET/취소·구버전·정책·나지 검토 11 PASS, 0.982초.
- 누락/경로 이탈/바이트 한도/SHA 변조/부분 보고서/타입·합계 오류/linked 입력/과거 source/미승인 플래그를 검증했다. linked 경로는 모의 검증이다.
- `evidence/integration/ui180-typescript-20261018.log` 및 `ui180-final-20261018.json`: 공유 작업공간 TypeScript build 검사 exit0, 30.844초. 다른 Toolbox 작업이 포함된 공유 공간이므로 게시 범위의 격리 빌드는 Root가 별도 수행한다.
- 초기 시험에서 Python 3.11의 Path.is_junction 부재를 발견하여 lstat Windows reparse flag 검사로 교정했다. 이후 관련 19개 시험 통과. 실제 junction 생성 시험은 하지 않았다.

## 인계

Root가 실제 179 보고서 지문과 data_root 상대 receipt를 게시하고 API 프로세스 적용 여부를 확인한다. 실제 브라우저에서 최신 재고·고정 후보의 구분·시점 경고·6주 나지 표·콘솔/가로 넘침을 검증한 뒤 운영 확인 결과를 추가해야 한다. collector·원장·모델·배포 승인·기존 데이터는 본 변경에서 쓰지 않는다. 다른 Toolbox/App/PlatformShell/CSS는 편집하지 않았다.
