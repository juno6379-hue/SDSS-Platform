# 225 — 추가 수집 예산 원장의 읽기 전용 관측

상태: TESTED_SYNTHETIC / VERIFIED_REAL. 코드·격리 시험·빌드와 Root 검토 이후 실제 API·브라우저 적용을 확인했다. 비용·원격 수집·학습·새 후보 QA는 실행하지 않는다.

## 쉬운 설명

수집 현황 화면에는 현재 전체 예산 금액을 보여주는 기능이 없었다. 최근 실행의 예산은 과거 실행 기록이므로 현재 전체 원장으로 대신 사용할 수 없다. 새 카드는 고정 경로의 전체 원장을 읽고 **관측한 시점의 한도·사용·잔여·미정산 예약**을 보여준다. 조회 뒤에도 수집이 예약·정산하면 숫자는 바뀔 수 있다.

원장에 예약이 남았다는 사실만으로 프로세스가 지금 실행 중이라고 판단하지 않는다. 실제 실행 여부는 **미확인**으로 명시한다. 예산 잔여가 있다고 품질·집행·학습을 승인하지 않는다.

## 원장 의미와 계산

기존 `backend/app/data/budget.py`의 `_read`, `reserve`, `settle`을 읽어 계약을 확인했다. `reserve`는 예약 전액을 `new_charged_bytes`에 더한다. 정상 정산 때만 예약과 측정액의 차액을 차감한다. 따라서 다음 계산을 사용한다.

- 추가 총한도 = `additional_maximum_bytes` (기존 기본 4294967296 bytes = 4 GiB, 검증 허용범위는 기존 writer의 1 byte~4 GiB).
- 정산·예약 포함 사용 = `new_charged_bytes` = 정산 배치의 charged 합 + 전체 pending의 예약 전액 + `external_research_metadata_body_bytes`.
- 계산 잔여 = 추가 총한도 − 정산·예약 포함 사용.
- 과거 집계 `historical_charged_bytes`는 추가 예산의 사용에 다시 더하지 않는다. `combined_maximum_bytes`는 과거 집계 + 추가 한도인지 검증만 한다.
- 기존 미정산 2건은 Banten/West Java 2023 laneB의 명시 batch key·config SHA로 식별한다. 이 두 건의 미정산 금액은 이미 전체 사용에 포함되어 있으므로 다시 차감하거나 자동 환불하지 않는다. 새 pending은 전체 예약 합계에는 포함하지만 기존 두 건과 구분한다. 기존 두 건이 향후 정상 정산되면 미정산 건수와 금액은 그 상태대로 감소한다.

새 코드는 `CollectionLedger`를 생성하거나 그 `snapshot()`을 호출하지 않는다. 해당 메서드는 lock을 쓰므로 읽기 전용 조회에 부적합하다. 원장·lock·보고서·등록 자료를 쓰거나 환불하는 경로는 없다.

## 조회·오류 API 계약과 사용법

`GET /api/data/collection-budget-status`는 기존 앱 인증을 그대로 적용하고 `Cache-Control: no-store`를 반환한다. 요청 본문·임의 파일 경로·수집 실행 옵션은 받지 않는다. 일반 수집 현황 `GET /api/data/collection-status`에도 `collection_targets.budget_status`로 같은 독립 관측을 붙인다. 기존 재고·latest_run 집계는 대체하지 않는다.

```text
GET http://127.0.0.1:8002/api/data/collection-budget-status
Authorization: Bearer <기존 설정 토큰>   # 토큰 설정 시에만 필요
```

성공 응답 `schema_version: 1`, `available: true`, `status: OBSERVED_LEDGER_SNAPSHOT`, `scope: ADDITIONAL_BUDGET_INCLUDES_PENDING_NOT_PROCESS_LIVENESS`를 사용한다. 금액 필드는 모두 정수 bytes다.

| 필드 | 의미 |
|---|---|
| `additional_maximum_bytes` | 추가 총한도 |
| `charged_including_pending_bytes` / `remaining_bytes` | 예약 포함 사용 / 계산 잔여 |
| `settled_batch_bytes` / `metadata_body_bytes` | 정산 배치 / 외부 조사 본문 |
| `pending_bytes` / `pending_count` | 현재 원장의 전체 미정산 예약 |
| `old_pending_bytes` / `old_pending_count` | 명시한 기존 두 배치 중 아직 pending인 부분 |
| `source_manifest_sha256` / `ledger_sha256` | 관측 원본·원장 바이트 SHA256 |
| `observed_at` / `ledger_updated_at` | 이번 관측 UTC / 원장에 기록된 저장 시각 |
| `rate_limit_active` | 원장의 HTTP429 차단 선언; 현재 HTTP 요청 시험 아님 |
| `process_verification: UNKNOWN` | 실제 프로세스 실행 여부를 검사하지 않음 |
| `execution_approved: false` | 집행 승인 아님 |

파일 없음·손상·한도 초과·링크·변경 감지·숫자 모순은 HTTP200의 다음 안전 응답이다. 이전 금액·부분 합계·내부 경로·예외 원문은 반환하지 않는다. 인증 실패는 기존 HTTP401이다.

```json
{"schema_version":1,"available":false,"status":"UNCONFIRMED","process_verification":"UNKNOWN"}
```

## 일관성과 읽기 한도

원장은 고정 `first-group-training-budget/global-ledger.json`에서 최대 8 MiB, 원본 manifest는 고정 `first-group-training-esri-v1/annual-window-report.json`에서 최대 64 MiB다. 원본은 스트리밍으로 해시만 계산하며 JSON/래스터를 로드하지 않는다. 원장 JSON은 UTF-8·BOM/NUL 거부·깊이16·중복 key/NaN/Infinity 거부, 최상위/배치 schema·정수 안전 범위·건수·합계를 검증한다.

data root 자체와 그 아래 경로의 symlink/reparse를 거부한다. 파일 읽기 전후 dev/inode/size/mtime/ctime 및 열린 descriptor의 identity를 비교한다. 원본과 원장을 각각 다시 읽어 identity·전체 SHA가 일치할 때만 관측한다. 읽는 사이 atomic replace나 변경이 감지되면 미확인으로 닫으며 자동 재시도하지 않는다. 잠금을 잡지 않으므로 반환 이후 미래 변경을 막지 못한다. API의 관측 시각을 최신 상태의 영구 보장으로 해석하지 않는다.

한 번의 성공 관측은 원본 최대128 MiB 및 원장 최대16 MiB 읽기를 추가할 수 있다. 영상·라벨 fullhash나 native QA는 수행하지 않으며, HTTP 지연 SLA를 검증했다고 주장하지 않는다. 향후 캐시나 읽기 최적화는 같은 지문·변경 감지 계약을 보존해야 한다.

## 화면 연결

CollectionProgress의 작은 예산 카드에 한도·사용·잔여·기존 미정산 예약, 사용 구성, 관측·저장 시각, 두 SHA, 프로세스 미확인을 표시한다. adapter가 범위·합계·시각·승인 false·process UNKNOWN을 다시 검증한다. 예산 snapshot의 source SHA와 함께 받은 재고 source SHA가 다르면 전체 재고를 손상으로 보지 않고 예산 카드만 미확인으로 처리한다. 누락·손상·변경 중인 응답에서 과거 금액이나 latest_run 수치로 대체하지 않는다.

## 시험·검토·인계

격리 backend API/helper 11 PASS: 인증·no-store·빈 root 무쓰기, 산식·기존/신규 pending 분리, strict 숫자·schema·인코딩·깊이·파일 한도, data root/하위 reparse·descriptor retarget·전후 identity/SHA 변경, 기존 재고 유지. 프론트 adapter/실제 컴포넌트 렌더 16 PASS(기존195 회귀 포함): 카드 값·시간·지문·미확인 process, source 불일치 때 이전 금액 제거, 기존 범위/후보 검증. 별도 기존 collection priority 12 PASS는 합산하지 않는 관련 회귀다.

최종 TypeScript/Vite 빌드와 소스 SHA는 `evidence/integration/budget225-freeze-20261018.json`에 기록한다. 초기 핀은 `budget225-before-20261018.json`, 시험과 빌드는 `budget225-*-20261018.log`에 보존한다. 수집기 core·예산 writer는 수정하지 않았다. Root의 data-root reparse 검토 의견은 새 검증과 Temp 시험으로 반영했다. Root 독립 검토와 명시 적용 지시 전까지 API 재시작·실브라우저 조회를 수행하지 않는다. 공통 원장·API 이해자료·대본/Q&A는 완료 근거와 함께 Root에 인계한다.


## 225 실제 API 적용과 브라우저 확인 완료

상태: **VERIFIED_REAL**. Root 독립 검토와 적용 지시 이후 기존8002 소유 PID20676/uvicorn 명령·포트를 확인하고 해당 API만 숨김 재기동했다. 새 PID40492의 health200·localhost 인증·5174 CORS·dashboard 등록 개수 보존을 확인했다. Vite5174와 collector는 재시작하지 않았다.

새 `GET /api/data/collection-budget-status`는 HTTP200/0.378673초였다. 한도4294967296·사용2398022341·잔여1896944955·기존pending2합136314880 bytes, settled2258031733 + metadata3675728 + pending136314880 = 사용2398022341을 검산했다. pending을 잔여에서 다시 빼지 않는다. 이 단일 요청의 계측은 전체 수집 현황 API 지연 SLA가 아니다.

기존 Chrome view17에서 한 번 새로 조회한 재고 응답 시각은 **15:17:49.337627 KST**, 예산 관측 시각은 **15:17:51.063011 KST**로 별개다. source SHA `9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987`, ledger SHA `61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7`가 실제 카드에 표시됐다. 카드4개·시각·두SHA·사용구성·프로세스 미확인·승인 아님 설명을 실제 캡처에서 확인했다.

같은 응답은 등록 원본1715·적격1358(816·292·250)·셀 부족21과 기존 후보1339·차단3/source불일치, 검토37/두주/source불일치·미검사/집행미승인을 유지한다. 콘솔 warning/error0·가로 넘침 없음이다. 운영 원본·원장·두pointer SHA는 재기동 전과 브라우저 확인 후 동일했다. 원장·lock·pointer쓰기0이며 신규 수집·QA·학습·배포를 실행하지 않았다. 위의 실적용 대기는 이 결과로 해소됐으며 격리시험·실 API·HMR 표시·실제 새 응답을 구분한다.

적용 receipt는 `evidence/integration/service225-api-application-20261018.json`, 최종 근거는 `service225-budget-final-ui-20261018.json`과 `.dom.txt`, `.checks.json`, `.inventory.png`, `.budget.png`, `.cohort.png`다. 원장과 원본은 관측 이후 변경될 수 있으며 이번 화면은 명시한 시점의 값이다.
