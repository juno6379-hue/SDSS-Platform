# 332. 원장 metadata_io 어댑터 — 격리 구현·합성 시험

상태: **TESTED_SYNTHETIC**. 격리 작업공간에서 구현하고 합성 시험을 마쳤습니다. 실제 원장, 170 수집 worker, HTTP에는 연결하지 않았습니다. 공유 적용 여부는 아래 독립 검토 결과와 333 문서를 따릅니다.

## 1. 쉬운 설명

수집 예산 원장(`global-ledger.json`)을 읽고 쓰는 코드는 지금 `CollectionLedger`(`backend/app/data/budget.py`)가 직접 `read_text`와 `.tmp` 교체로 처리합니다. 이 방식에는 세 가지 빈틈이 있습니다.

- 크기 상한이 없습니다.
- 128MiB 명시 profile의 I/O 계상(16GiB scope)에 포함되지 않습니다.
- 원장이 바뀌었는지 SHA로 고정해 확인하지 않습니다.

332는 원장 쓰기 경로를 **명시적으로 선택했을 때만** 다음과 같이 바꾸는 어댑터 `LedgerMetadataIO`를 추가합니다.

- 기존 원장과 과거 원장 목록을 SHA로 고정하고, 8MiB 상한을 파일을 열기 전에 검사합니다.
- 읽기와 쓰기를 모두 같은 profile scope에 계상합니다.
- 쓰기는 331의 원자적 JSON 저장기(`targeted_atomic_json.replace_json_value`)로 처리합니다.
- 허용된 새 batch 키 최대 2개만 예약할 수 있고, 이 어댑터가 예약한 키만 정산할 수 있습니다.
- 기존 pending 2건을 포함한 기존 행과 필드는 한 글자도 바뀌지 않아야 저장됩니다.

기본값 `metadata_io=None`에서는 기존 동작과 출력 바이트가 그대로입니다.

## 2. 이론적 배경

- **fail-closed**: 확인할 수 없는 상태에서는 진행하지 않고 멈춥니다. 어떤 실패든 어댑터는 `stopped` 상태가 되고, 이후 모든 호출을 거부합니다.
- **커밋 결과 구분**: 쓰기 실패를 하나로 뭉치지 않고 다음처럼 구분해 예외 속성 `ledger_metadata_commit_outcome`에 남깁니다.
  - `NOT_ATTEMPTED`: 교체 전에 중단됨
  - writer의 `UNKNOWN`: 쓰기를 측정하지 못함. 보수적으로 계상함
  - `APPLIED`: 교체는 끝났지만 그 뒤 검증이 실패함
  - `APPLIED`라도 pin을 전진시키거나 환불, 롤백, 재시도하지 않습니다.
- **상태 전이 검증**: 저장하기 전에 직전에 읽은 상태(`_before`)와 저장할 상태를 비교합니다. 허용되는 변화는 두 가지뿐입니다. `updated_at`만 예외로 둡니다.
  - 허용된 새 키 1개의 pending 예약과, 그만큼의 `new_charged_bytes` 증가
  - 이 어댑터가 예약한 키 1개의 settled 정산과 차액 감소. 429 회로 개방도 이때 함께 허용
  - 그 밖의 필드 변화는 모두 거부합니다.

## 3. 코드·데이터 동작

| 파일 | 변경 |
|---|---|
| `backend/app/data/ledger_metadata_io.py` | 새 파일. `LedgerMetadataIO(root, ledger_ref, historical_refs, allowed_batches, manifest_profile)` |
| `backend/app/data/budget.py` | `__init__`에 keyword-only `metadata_io=None` 추가. `_read`/`_save`/`reserve`/`settle`에 어댑터 위임 hook 추가(+15/−1행) |

생성 조건은 다음과 같습니다.
- 명시 profile scope가 활성이어야 합니다(`LEDGER_EXPLICIT_SCOPE_REQUIRED`).
- marker가 writer의 `EXPECTED_MARKER`와 정확히 같아야 합니다.
- 원장과 과거 원장 참조는 모두 root 안이어야 하고, 같은 경로가 중복되면 안 됩니다.
- 허용 키는 1~2개이며 각각 config SHA를 지정해야 합니다.

`bind` 단계에서 확인하는 것은 다음과 같습니다.
- 생성자의 경로와 과거 원장 순서가 정확히 일치하는지
- 원장 파일이 이미 존재하는지. 어댑터 모드는 자동 초기화를 하지 않습니다.
- 허용 키가 원장에 아직 없는 새 키인지

## 4. 테스트 증거

| 실행 | 결과 | 근거 |
|---|---|---|
| 첫 실행 시도 | 실행기 import 오류 1건. `tests.` 모듈 경로가 다른 설치 패키지와 충돌해 제품 코드가 실행되지 않음 | `focused332-launcher-import-error.log` |
| focused 첫 실행(수정 전) | 34/34 PASS | `focused332-first.log` |
| 수정 전 최종 focused·portable | 각 34/34 PASS | `pre-review332/` |
| **수정 후 focused 최종** | **45/45 PASS**, 8.57초 | `focused332-final.log`, `focused332-final-result.json` |
| **수정 후 portable**(baseline 디렉터리 없는 Temp 복사본) | 같은 45건 PASS, 9.70초. 고유 90건이 아님 | `portable332-final.log`, `portable332-final-result.json` |
| 돌연변이 검사(새 시험을 수정 전 코드로 실행) | 7건 FAIL. F1·F2·F3 관련 시험이 수정 전 결함을 실제로 잡아냄 | `mutation332-pre-review-code.log` |
| main 의존 시험 9개 모듈(적용 전 기준) | 147/147 PASS, 63.55초 | `target333-application-root-20261019/pre-apply-dependents.log` |

시험이 확인하는 범위는 다음과 같습니다.
- 예약·정산과 기존 pending 정확 보존, 같은 scope 계상
- 허용 키 상한, marker·scope 필수
- 과거 원장 순서, root 밖 경로와 별칭 거부
- 자동 초기화 금지, 잘못된 pin 거부
- 과거 원장 교체 시 중단, 8MiB 열기 전 차단, 중복 키 JSON 거부
- bool 금액 거부, 기존 pending 정산 금지, 다른 인스턴스 키 정산 금지
- 429 회로, 기존 행·전역 상수 변조 거부
- 부분 쓰기, UNKNOWN(측정 불명과 `os.replace` 실패), 교체 후 검증 실패(APPLIED·pin 미전진), scope 소진
- 다른 operation 거부, lock 경합 시 남의 lock 미삭제
- legacy `None` 경로의 출력 바이트·오류 메시지·초기화가 기존과 같음
- 리뷰 후속: legacy 검사 실패(예산 초과·중복 정산·lock 경합)도 어댑터 중단, bind 실패 뒤 재사용 금지, 검증 뒤 caller 객체를 변조해도 기록에 반영되지 않음, 직접 `_save`로 예산 초과·429 해제 거부, 배열 형식 과거 원장 거부

모든 작업공간 경로는 `evidence/integration/target332-workspace-20261019/` 아래에 있습니다.

## 5. 독립 정적 검토와 수정

별도 검토 에이전트가 코드를 읽기 전용으로 검토했습니다. 데이터 손상으로 이어지는 차단 결함은 없었지만, 아래 세 가지를 지적했습니다.

| ID | 지적 | 조치 |
|---|---|---|
| F1 | legacy 검사 실패(429, 예산 초과, 기존 pending, 중복 정산, 측정값 초과) 뒤에도 어댑터가 멈추지 않아 "모든 실패 시 중단" 주장과 어긋남 | `CollectionLedger._guard()`를 추가해 `snapshot`·`reserve`·`settle`을 감쌌습니다. `None` 경로에서는 `nullcontext`라 동작이 없습니다. |
| F2 | `bind` 앞부분의 실패가 어댑터를 멈추지 않아 재사용될 수 있음 | `bind`의 모든 실패(두 번째 bind 포함)를 중단으로 처리했습니다. |
| F3 | 검증한 객체와 실제로 쓰는 객체가 같은 caller 객체라 그 사이 변조가 가능(TOCTOU) | 한 번 깊은 복사한 `candidate`를 검증·기록·`_before`에 똑같이 사용합니다. |

다음 F4~F9는 참고 사항으로, 아래 한계에 반영했습니다.

같은 검토 에이전트가 수정분만 다시 읽기 전용으로 검토했고, **차단 결함 없음**으로 판정했습니다. 확인한 내용은 다음과 같습니다.
- `None` 경로에서는 `nullcontext`가 동작을 바꾸지 않습니다.
- guard는 같은 예외 객체를 그대로 다시 던지므로 `ledger_metadata_commit_outcome`을 가리지 않습니다.
- 돌연변이 검사의 실패 7건이 기대한 F1·F2·F3 집합과 정확히 일치합니다.

## 6. 한계 (확대 해석 금지)

- 실제 운영 원장(`data/first-group-training-budget/global-ledger.json`)은 읽지도, 복사하지도, 쓰지도 않았습니다.
- 170 CLI·coordinator·worker, JSONL·stdout, HTTP에 연결하지 않았습니다. 따라서 실제 수집 경로의 64MiB 차단은 계속 **BLOCKED**입니다.
- 비협력 writer에 대한 원자적 CAS, 전원 차단 시 영속성, 여러 파일에 걸친 트랜잭션은 보장하지 않습니다.
- 기존 pending 2건(136,314,880B)은 보존만 할 뿐 정산하거나 환불할 수 없습니다.
- (F4) `metadata_io`는 공개 속성이라 호출자가 `None`으로 바꾸면 legacy 경로로 돌아갑니다. 따라서 보안 경계가 아니라 협력하는 호출자를 위한 안전장치입니다.
- (F5) lock 파일 생성·삭제와 stat 호출은 profile 예산에 계상하지 않습니다. Windows에서 lock 삭제가 실패하면 그 예외가 원래 예외를 가려, `ledger_metadata_commit_outcome`이 `__context__`에만 남을 수 있습니다. 이는 기존 legacy `locked()`의 동작입니다.
- (F6) 원장에 기록된 과거 원장 경로의 대소문자나 드라이브 문자가 다르면 거부됩니다(안전한 쪽). 측정 불명으로 남은 writer 임시파일 `.target329.tmp`는 사람이 정리하기 전까지 이후 쓰기를 막습니다.
- (F7) 어댑터 모드에서는 과거 원장이 8MiB 이하의 JSON 객체여야 합니다. legacy는 바이트 해시만 확인했습니다.
- (F8) 어댑터가 저장하면 원장 형식이 legacy의 `indent=2`에서 compact·sort_keys JSON으로 바뀝니다. legacy reader는 그대로 읽을 수 있습니다.
- (F9) 직접 `_save`를 부를 때 lock 보유 여부는 확인하지 않습니다. 정확한 pin 검사가 협력 writer 사이의 갱신 유실을 막습니다.
- (재검토 참고) lock 경합도 실패로 보기 때문에, 다른 협력 프로세스가 잠깐 lock을 잡기만 해도 이 어댑터 인스턴스는 영구 중단됩니다. 새 인스턴스를 만들어야 합니다. 두 번째 `bind` 시도도 원래 묶인 원장 사용까지 중단시킵니다. 안전을 위해 가용성을 양보한 설계입니다.
- 성능 수치는 단일 실행 관측값이며 SLA가 아닙니다.

## 7. 발표 스크립트 (30초)

"수집 예산 원장을 쓰는 코드는 크기 상한도 변경 감지도 없었습니다. 332는 이를 명시적으로 켰을 때만 동작하는 어댑터로 바꿉니다. 원장 SHA를 고정하고 8MiB 상한을 먼저 검사하며, 허용된 새 batch만 예약·정산하게 하고, 기존 미정산 2건은 한 글자도 바뀌지 않아야 저장됩니다. 실패하면 멈추고 환불이나 재시도는 하지 않습니다. 독립 검토에서 나온 세 가지를 고쳤고, 합성 시험 45건이 통과했습니다. 다만 실제 수집 연결은 아직 남아 있습니다."

## 8. Q&A

- **Q. 이제 나지 수집을 할 수 있나요?** 아닙니다. 170 수집 worker 연결(328 B·C 단계)이 남아 있어 64MiB 차단이 그대로입니다.
- **Q. 기존 수집기 동작이 바뀌나요?** 기본값 `None`에서는 바뀌지 않습니다. legacy 출력 바이트가 같다는 것을 시험으로 비교했습니다.
- **Q. APPLIED 오류가 나면 원장은 어떤 상태인가요?** 교체는 이미 됐을 수 있습니다. 어댑터는 멈추고, 사람이 원장을 다시 검산해야 합니다. 자동 롤백은 하지 않습니다.
