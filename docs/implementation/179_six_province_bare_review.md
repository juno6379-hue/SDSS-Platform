# 179 — 6개 주 나지 후보의 로컬 품질·겹침 검토와 계획 연결

상태: **VERIFIED_REAL — 로컬 50후보의 native 약한라벨·과거지원 겹침 검토에 한정**. 실제 원격 수집·이미지 품질·독립 정답·학습 승인은 완료가 아니다. 구현의 실패 경계는 별도의 **TESTED_SYNTHETIC** 시험으로 검증했다.

## 실제 50후보 검토 결과 — 2026-10-18 12:08 KST

Root의 명시적 승인 후 9차 종료 원본 **1,617행**과 원장을 `data/bare179-review-20261018/`에 원바이트 고정했다. PID39096을 12:02:58에 시작하여 report 시각12:08:03에 끝냈다. 약5분5초는 프로세스 시작·보고시각 차이이며 정밀 timer나 SLA가 아니다. 동시 수집을 시작하지 않았으며 종료 후에도 원운영 source·ledger SHA가 동일했다.

| 주 | 원후보 | 과거 지원 겹침 없음 | 과거 지원과 겹침 | 로컬 검증 오류 |
|---|---:|---:|---:|---:|
| 남술라웨시 | 9 | 8 | 1 | 0 |
| 고론탈로 | 1 | 0 | 1 | 0 |
| 남동술라웨시 | 11 | 8 | 3 | 0 |
| 동자바 | 8 | 3 | 5 | 0 |
| 반텐 | 15 | 4 | 11 | 0 |
| 서자바 | 6 | 0 | 6 | 0 |
| 합계 | **50** | **23** | **27** | **0** |

26개 실제 raw 라벨·4,668,329B에서 50창의 픽셀·기하를 재계산했고, 전체 1,193지원자산 inventory를 **한 번** 검사했다. 기존 pending2도 확인했다. 후보 상호 겹침은 **56쌍**으로 별도 기록했다. 과거 겹침 없는23개를 모두 동시에 수집해도 된다는 뜻이 아니다. 현재 50후보 안에서 고론탈로·서자바는 clear0이므로 추가 로컬 후보 탐색이나 별도 표적 제안이 필요하다. 6주 공통 검토·계획 shape 연결과 각 주에서 실제 수집 가능한 후보 확보를 구별한다.

실제 report는632,883B, SHA `36aaf1107292eee74b0f6a2ce462d90e40a22de498ca31aaff1c1ded636775f0`다. 현재 원본 SHA는 `03c58af67c5f44e9824488c3e7f0595746b007addb37f846119511b0f19dd367`, 원장 SHA는 `7d27c5231c43c0014de92a11fa517c5a4d5c662005785ac75054d37dc27544fb`다. 후속 수집에는 이 시점의 핀이 오래된 근거가 되므로 실제 집행 전에 다시 검증한다.

- [실제 report](../../evidence/integration/bare179-report-20261018.json), [종료 로그](../../evidence/integration/bare179-actual-20261018.log)
- [고정 request](../../evidence/integration/bare179-request-20261018.json), [원운영 pin·복사 receipt](../../evidence/integration/bare179-request-pin-20261018.json), [원바이트 고정 코드](../../evidence/integration/bare179-prepare-request-20261018.py)
- [독립 최종검산](../../evidence/integration/bare179-final-verification-20261018.json), [검산 코드](../../evidence/integration/bare179-final-verification-20261018.py), [검산 로그](../../evidence/integration/bare179-final-verification-20261018.log)

## 목적과 실행 경계

`scripts/review_bare_targets179.py`는 173의 고정 proposal과 현재 manifest·ledger·공식 6주 boundary의 명시 SHA를 받는다. 원격 호출·수집·원장·원본 수정은 없다. 입력/native 검증 오류가 하나라도 있으면 전체 검토가 차단된다. 과거 영상과의 겹침은 입력 변조가 아니므로 후보별 관측으로 남긴다. 항상 `execution_supported:false`, `actual_quality_eligible:false`, `scientifically_verified_bare:false`다.

검토 과정은 다음과 같다.

1. 6주 고정 split·2020~2025년·전용 경계 SHA를 확인한다. 고정 proposal과 현재 원본은 수집 시점이 달라도 되며 양쪽 참조를 보존한다.
2. 실제 로컬 raw ESRI 라벨 바이트 SHA, 10m 미터 단위 투영격자, 단일 정수 band, native 256×256 창, 주 경계 안쪽 면적 95% 이상, 나지 코드8 256픽셀 이상을 검산한다. 173의 선언 숫자를 그대로 성공으로 신뢰하지 않는다.
3. 라벨이 있는 batch의 `annual-window-report.json`을 현재 ledger의 report 경로에 결합한다. 정확한 crop SHA가 단 하나의 scene에 있어야 하며 주·연도·ESRI 연차 URL·crop 경로가 일치해야 한다. 같은 SHA와 창의 중복은 거부한다.
4. `inspect_targeted_inventory`(167)를 전체에서 **한 번만** 호출한다. `inventory_verified`, `pending_footprints_verified`, `source_pins_verified`가 모두 true여야 한다. 첫 후보가 과거 영상과 겹쳐 결과 status가 BLOCKED여도 이 세 필드가 true면 완료된 inventory 스캔만 재사용한다. 차단을 집행 허가로 바꾸지 않는다.
5. 각 후보에 대해 `TargetedWindowClaims`(170)의 보수적 수치 기하 검사로 고정 전체 assets와 과거 겹침을 대조한다. 후보끼리의 겹침 쌍도 별도로 기록한다. 과거 겹침 없음은 후보 사이 독립성을 뜻하지 않는다.
6. 원본·원장·proposal·boundary·라벨·lineage SHA를 끝에서 재확인한다. 순차 검사이므로 원자적 snapshot·실행 예약은 아니며 실제 collector는 반드시 다시 검사한다.

## 명시 입력과 출력

request는 정확히 다음 키를 갖는다. 각 ref는 workspace 기준 상대경로와 실제 파일 SHA256이다. proposal은 `evidence/integration/`, 나머지는 `data/` 안의 파일이어야 한다.

```json
{"schema_version":1,"proposal_ref":{"path":"evidence/integration/…/proposal.json","sha256":"…"},"manifest_ref":{"path":"data/…/source.json","sha256":"…"},"ledger_ref":{"path":"data/…/ledger.json","sha256":"…"},"boundary_ref":{"path":"data/…/boundary.geojson","sha256":"…"}}
```

CLI는 `--request`, `--request-sha256`, `--output`을 모두 명시한다. 출력은 `evidence/integration/`의 새 `.json` 파일에 exclusive 생성하며 기존 파일을 덮어쓰지 않는다. 출력 상한은 2MiB, 후보 최대128개, 라벨 최대128파일·768MiB, 개별 라벨64MiB다. 모든 상한은 실패 시 truncation 성공으로 전환하지 않는다. 167의 기존 전체 inventory 최대10,000파일·2GiB 상한도 유지한다.

결과 `targets`는 157/175의 정확한 target 키를 갖는 **계획용 목록**이다. `source_lineage_ref`도 실제 고정된다. `select_plan(result,[index])` 또는 최대2개 index로 정확한 `TARGETED_BARE_256_COLLECTION_PLAN`을 만들 수 있다. 과거 겹침이나 선택된 후보 상호 겹침은 selection 단계에서 거부한다. 175/176/170의 새 입력 검증·예산·실제 STAC 장면·B02 격자·출력 품질 가드는 여전히 필수다. 이 함수는 파일이나 HTTP를 쓰지 않는다.

## UI 계약

180 API/UI 담당과 합의한 `report['ui_summary']`의 정확한 projection:

```json
{"schema_version":1,"status":"LOCAL_TARGET_REVIEW_FINISHED","recorded_at":"UTC ISO","current_manifest_sha256":"64hex","execution_supported":false,"actual_quality_verified":false,"scientific_accuracy_validated":false,"summary_by_province":[{"province":"banten","candidates":15,"support_clear":0,"overlap":15,"local_invalid":0}],"candidate_total":50}
```

위 숫자는 **계약 형식 예시일 뿐 실측 결과가 아니다**. 실제 projection에는 6주 행이 정확히 하나씩 들어간다. 각 행의 candidates는 support_clear+overlap+local_invalid와 같으며 overlap은 **과거 지원영상과 겹친 수**다. 후보 사이 겹침은 본체 `candidate_mutual_overlap_pairs`에 따로 있다. local_invalid는 완료 보고에서0이며 입력/native 오류는 완료 보고를 만들지 않고 전체 차단한다. 실제 원격 영상 품질 확인은 false다. manifest SHA가 후속 수집으로 달라지면 API/UI는 이전 시점 검토로 표시해야 한다.

운영 receipt 게시와 API·실브라우저 검증은 Root/180 소유이며 이 구현이 자동 게시하지 않는다.

## 시험 근거와 한계

`tests/test_review_bare_targets179.py`는 작은 실제 GTiff를 읽고 격자·나지·경계를 검사한다. 전체167 스캔은 mock이며 170 겹침 기하는 실제다. 전체 inventory 재검증과 실제 50후보의 성공은 이 합성 시험으로 주장하지 않는다.

native 픽셀·공유 라벨 캐시·1회 inventory·6주 고정 split·lineage 고정·과거 겹침 관측·후보 상호 겹침·변조/누락/중복/상한·검토 중 metadata/라벨 변경·기존 출력 보존을 검증한다. 최초 unittest import 명령 오류, 합성 UTM 경계 fixture 오류와 missing-lineage 예외형 처리 보완 이력은 `bare179-focused-initial-*` 로그에 보존했다. 마지막 경우 CLI의 `_Blocked` catch를 추가하여 실제 파일 누락이 통제된 REVIEW_BLOCKED로 끝나게 했다.

집중 11개 시험은 [로그](../../evidence/integration/bare179-focused-11test-20261018.log)에서 모두 PASS(6.169초)다. 이후 6주 반복 native 시험을 추가한 관련 회귀는 **45PASS·8.445초**(자체12개와 167/170 관련 시험)로 [관련 로그](../../evidence/integration/bare179-related-20261018.log)에 기록했다. 위 실제 운영 로컬 검토와 합성·임시 시험은 범위를 구별한다.

약한 ESRI 라벨, 면적 기반 inside, 보수적 겹침 검사만으로 독립 정답·공간적 과학 독립성·학습 준비·운영 승인을 확인할 수 없다. 이미 보존 중인 pending 예약을 삭제·환불·재시도하지 않는다.
