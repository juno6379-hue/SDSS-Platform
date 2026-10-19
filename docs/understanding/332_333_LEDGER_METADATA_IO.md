# 332·333 — 수집 예산 원장 metadata_io 어댑터 격리 구현과 메인 공유 적용

- updated_at: 2026-10-19 12:55:00 KST
- source_commit: 333 공유 코드베이스 적용 및 192건 통합 검증 완료 기준 (freeze332 `b6f23c4b...` 적용)
- evidence_paths:
  - `docs/implementation/332_ledger_metadata_io_isolated.md`
  - `docs/implementation/333_ledger_metadata_io_shared_application.md`
  - `evidence/integration/target333-application-root-20261019/application.json`
  - `evidence/integration/target333-application-root-20261019/completion.json`
  - `evidence/integration/target333-application-root-20261019/main-applied-332-tests.log`
  - `evidence/integration/target333-application-root-20261019/post-apply-dependents.log`
  - `backend/app/data/ledger_metadata_io.py`
  - `backend/app/data/budget.py`
  - `archive/budget.py.pre333`
  - `tests/test_ledger_metadata332.py`
  - `tests/fixtures/budget332_legacy.py`
- confidence: 메인 적용 코드, 신규 45건 단위 시험, 기존 의존 9개 모듈 147건 시험 로그, 2차 독립 정적 검토 결과와 변이 검사 로그를 직접 확인.
- status:
  - **VERIFIED_REAL**: 메인 코드베이스 192건 전체 테스트 통과 (신규 45 PASS + 기존 의존 147 PASS, FAIL=0, SKIP=0).
  - **TESTED_SYNTHETIC**: 격리 모의 환경에서의 45건 단위 시험 및 F1~F3 변이 결함 검출 시험.
  - **BLOCKED**: 170 실제 수집기 worker/coordinator 연결, 64MiB 제한 수집 실행, 외부 HTTP 요청, 실제 운영 원장(`data/first-group-training-budget/global-ledger.json`) 직접 수정 0.

---

## 1. 쉬운 설명

수집 예산 원장(`global-ledger.json`)은 위성 영상을 다운로드할 때 허용된 데이터 전송량(예산)을 초과하지 않도록 기록하는 장부입니다. 기존에는 `CollectionLedger`가 파일을 직접 읽고 `.tmp` 파일로 교체해 저장했으나, 세 가지 안전 빈틈이 있었습니다:
1. 파일 크기 상한이 없어 거대 파일 열람 시 메모리 장애 위험이 있었습니다.
2. 128MiB 명시 리소스 프로필(16GiB 스코프)의 I/O 계상에 포함되지 않아 자원 추적에서 누락되었습니다.
3. 원장 파일이나 과거 원장이 외부에서 변조되었는지를 파일 지문(SHA-256)으로 잠가서 확인하지 않았습니다.

Unit 332·333은 이를 해결하기 위해 **명시적으로 활성화했을 때만 동작하는 `LedgerMetadataIO` 어댑터**를 구현하고 메인 코드베이스에 성공적으로 적용했습니다.
- 원장을 열기 전에 **8MiB 상한(`LEDGER_CAP`)**을 먼저 검사해 메모리 폭주를 차단합니다.
- 기존 원장과 과거 원장 목록의 SHA-256 해시를 고정(pin)하여 단 한 글자라도 다르면 즉시 거부합니다.
- 읽기와 쓰기 모든 I/O를 같은 16GiB 프로필 스코프에 계상합니다.
- 저장은 Unit 331에서 검증된 원자적 JSON 저장기(`targeted_atomic_json.replace_json_value`)를 사용하여 안전하게 교체합니다.
- 허용된 신규 batch 키(최대 2개)만 예약할 수 있으며, 이 어댑터가 직접 예약한 키만 정산할 수 있습니다. 기존 2023년 반텐·서자바 미정산 배치(136,314,880B)를 포함한 기존 데이터는 단 1비트도 변조되지 않아야만 저장이 허용됩니다.

기본값(`metadata_io=None`)에서는 기존 수집기와 동일하게 동작하며 출력 바이트도 100% 동일합니다.

---

## 2. 이론적 배경

1. **Fail-Closed (실패 시 차단 원칙)**:
   - 시스템이 불확실한 상태를 감지하면 임의로 추측하거나 우회하지 않고 즉시 영구 정지(`_stopped = True`) 상태가 됩니다. 이후의 모든 I/O 호출은 차단됩니다.
2. **Commit Outcome (커밋 결과의 명확한 3단계 구분)**:
   - 쓰기 실패를 단순 에러로 뭉뚱그리지 않고 커밋 진행 단계에 따라 명확히 구분하여 예외 객체 속성(`ledger_metadata_commit_outcome`)에 보존합니다:
     - `NOT_ATTEMPTED`: 파일 교체(`os.replace`)를 시도하기 전에 검증 실패로 중단됨.
     - `UNKNOWN`: 쓰기 청크 계측 불명 또는 교체 도중 예외 발생으로 실제 디스크 반영 여부를 확정할 수 없음. 보수적으로 계상하며 자동 재시도하지 않음.
     - `APPLIED`: 디스크 파일 교체는 성공했으나 그 직후 사후 검증(과거 원장 재확인 등)에서 실패함. 이 경우에도 pin을 전진시키거나 자동 롤백/환불을 시도하지 않으며 즉시 중단하고 감사관에게 인계함.
3. **엄격한 상태 전이 검증 (Strict Transition Validation)**:
   - 저장 직전 상태(`_before`)와 새 상태(`state`)를 비교하여 허용되는 변경은 오직 두 가지뿐입니다:
     - 허용된 새 키 1개의 `pending` 예약 추가 및 그만큼의 `new_charged_bytes` 증가.
     - 본 인스턴스가 예약했던 키 1개의 `settled` 정산 완료 및 차액만큼의 `new_charged_bytes` 감소 (필요 시 HTTP 429 회로 차단 동시 기록 허용).
   - 타 인스턴스의 키 정산, 기존 pending 배치 변조, 전역 예산 한도 변경 등 허가되지 않은 상태 변조는 즉시 예외를 발생시키고 차단합니다.
4. **불변성과 호출자 오염 방지 (TOCTOU Defense)**:
   - 검증된 객체와 실제 직렬화되는 객체가 달라지는 경쟁 조건(Time-of-Check to Time-of-Use)을 막기 위해, 입력 상태를 깊은 복사(`candidate = copy.deepcopy(state)`)하여 단일 불변 사본으로 검증·저장·`_before` 갱신을 일관되게 수행합니다.

---

## 3. 코드와 데이터 동작

```mermaid
flowchart TD
    A[CollectionLedger 초기화] -->|metadata_io 지정| B[LedgerMetadataIO.bind]
    B -->|경로/참조/8MiB/신규키 검증| C[바인딩 성공]
    
    subgraph ReserveFlow [예약 흐름 (reserve)]
        D[CollectionLedger.reserve] --> E[CollectionLedger._guard]
        E --> F[LedgerMetadataIO.reserve_arguments]
        F -->|키/config_sha/최대2GiB 검증| G[LedgerMetadataIO.read]
        G -->|8MiB 캡/SHA 핀/구조 검증| H[신규 pending 상태 전이]
        H --> I[LedgerMetadataIO.save]
        I -->|replace_json_value 원자적 교체| J[원장 저장 완료]
    end
    
    subgraph SettleFlow [정산 흐름 (settle)]
        K[CollectionLedger.settle] --> L[CollectionLedger._guard]
        L --> M[LedgerMetadataIO.settle_arguments]
        M -->|본 어댑터 소유 키 확인| N[LedgerMetadataIO.read]
        N --> O[settled 상태 전이 검증]
        O --> P[LedgerMetadataIO.save]
        P -->|원자적 교체 및 핀 갱신| Q[정산 완료]
    end
    
    E -.->|검사 실패 시| R[self._stopped = True 영구 차단]
    L -.->|검사 실패 시| R
```

### 주요 구성 요소
- `backend/app/data/ledger_metadata_io.py`:
  - `LEDGER_CAP = 8388608` (8MiB): 열기 전 파일 크기 상한 강제.
  - `LedgerMetadataIO`:
    - `__init__`: root, ledger_ref, historical_refs, allowed_batches, manifest_profile 검증. 16GiB 명시 프로필 스코프 활성화 필수.
    - `bind(ledger)`: 원장 객체와의 결속 검증, 파일 존재 및 8MiB 검사, 허용 키가 미존재하는 신규 키인지 확인. 실패 시 영구 정지.
    - `stop_on_failure(ledger)`: 레거시 검사 단계에서 에러 발생 시 어댑터를 즉시 영구 정지시키는 콘텍스트 가드.
    - `read(ledger)`: 물리적 8MiB 사전 캡 확인, SHA 핀 검증, 원장 구조(`_structure`) 및 과거 원장 정합성 검증, `_before` 상태 스냅샷 저장.
    - `reserve_arguments`: 허용 목록 및 config SHA 일치 여부 확인.
    - `settle_arguments`: 본 어댑터가 직접 예약한 키(`_owned`)인지 검증.
    - `save(ledger, state)`: `_transition` 검증, UTC `updated_at` 부여, `targeted_atomic_json.replace_json_value` 원자적 쓰기 위임, 커밋 결과별 예외 속성 보존.
- `backend/app/data/budget.py`:
  - `CollectionLedger.__init__`: keyword-only `metadata_io=None` 인자 추가.
  - `_guard()`: 어댑터 모드일 때 `stop_on_failure`로 감싸고, 레거시 모드에서는 무동작 `nullcontext()` 반환.
  - `_read()`, `_save()`: `metadata_io`가 존재하면 어댑터 메서드로 위임.
  - `snapshot()`, `reserve()`, `settle()`: `self._guard()` 및 `locked()` 안에서 안전하게 인자 검증 및 상태 전이 실행.

---

## 4. 테스트 증거

| 구분 | 대상 모듈 / 테스트 파일 | 결과 | 소요 시간 | 비고 |
|---|---|---|---|---|
| **신규 단위 시험 (격리)** | `tests/test_ledger_metadata332.py` | **45 / 45 PASS** | 8.57초 | 격리 작업공간 합성 시험 (`focused332-final.log`) |
| **이동성 검증 (Portable)** | 임시 디렉터리 내 독립 실행 | 45 / 45 PASS | 9.70초 | baseline 없는 환경에서 동일 45건 검증 |
| **돌연변이 검사 (Mutation)** | 수정 전 코드 vs 신규 45건 시험 | **7건 FAIL** | - | F1, F2, F3 결함이 수정 전 코드에서 정확히 검출됨을 입증 |
| **메인 신규 단위 시험** | `tests/test_ledger_metadata332.py` | **45 / 45 PASS** | 8.918초 | 메인 코드베이스 반영 후 검증 (`main-applied-332-tests.log`) |
| **기존 의존 모듈 회귀** | 기존 9개 의존 모듈 회귀 시험 | **147 / 147 PASS** | 44.906초 | `test_collect_deficit_guarded` 등 9개 모듈 (`post-apply-dependents.log`) |
| **메인 통합 합계** | 신규 45 + 기존 의존 147 | **192 / 192 PASS** | - | **FAIL=0, SKIP=0, ERROR=0** (`completion.json`) |

### 독립 정적 2차 검토 조치 내역
1. **F1**: `CollectionLedger`의 레거시 검사(예산 초과, 429 회로, 기존 pending 등) 실패 시 어댑터가 멈추지 않던 결함 -> `_guard()` 콘텍스트 매니저를 도입하여 모든 실패 시 즉시 영구 정지(`_stopped = True`).
2. **F2**: `bind()` 진입 초기 실패 시 어댑터가 멈추지 않아 재사용될 가능성 -> `bind` 내 모든 실패(중복 bind 포함)를 즉시 정지 처리.
3. **F3**: 검증한 객체와 직렬화할 객체 간 TOCTOU 변조 위험 -> `copy.deepcopy(state)`로 생성한 불변 `candidate`를 검증, 직렬화, `_before`에 동일하게 사용.

---

## 5. 한계와 안전 경계 (확대 해석 금지)

- **BLOCKED — 실제 수집 실행 미연결**:
  - 본 구현은 원장을 안전하게 읽고 쓰기 위한 I/O 어댑터 계층의 완성입니다.
  - 170 실제 수집기 worker/coordinator 연결(328 B·C 단계)은 아직 연결되지 않았으므로 실제 64MiB 차단은 유지됩니다.
  - 실제 운영 원장(`data/first-group-training-budget/global-ledger.json`)은 직접 읽거나 쓰지 않았습니다(운영 I/O 0, 외부 HTTP 0).
- **기존 미정산 예약분 보존**:
  - 기존 2023년 반텐·서자바 2개 중단 배치(136,314,880B)는 그대로 보존되며, 본 어댑터로 정산하거나 자동 환불할 수 없습니다.
- **협력적 호출자 전제 (F4)**:
  - `CollectionLedger.metadata_io` 속성은 런타임에 호출자가 `None`으로 교체할 수 있으므로, 악의적 프로세스를 차단하는 보안 경계가 아니라 올바른 워크플로우를 보장하는 안전장치입니다.
- **가용성보다 안전성 우선**:
  - 락 경합 발생 시에도 안전을 위해 어댑터가 즉시 영구 정지되므로, 경합 시에는 새 어댑터 인스턴스를 생성해야 합니다.

---

## 6. 발표 스크립트

### 1분 발표 (경영진/비전공자)
> "수집 예산 원장은 위성 영상 수집 비용을 통제하는 핵심 장부입니다. 기존에는 파일 크기 제한도, 위변조 감지 장치도 없어 잠재적 위험이 있었습니다. 이번 Unit 332와 333을 통해 원장을 열기 전 8MiB 크기를 먼저 검사하고, 파일 해시를 대조해 단 한 글자라도 바뀌면 저장을 차단하는 안전 어댑터를 개발하여 메인 시스템에 적용했습니다. 두 차례의 독립 정적 검토를 거쳐 결함을 모두 보완했으며, 기존 시스템과의 호환성을 포함한 192개 전체 테스트를 100% 통과했습니다. 실제 수집기 연결 전 단계의 데이터 안전 장치가 완벽히 확보되었습니다."

### 5분 발표 (실무자/기술위원회)
> "Unit 332와 333의 핵심은 수집 예산 원장 I/O의 원자성과 안전성 확보입니다.
> 
> 기존 `CollectionLedger`는 단순 파일 쓰기와 임시 파일 교체를 사용해 8MiB 초과 방지 부재, 128MiB 리소스 프로필 I/O 누락, SHA 핀 검증 부재라는 세 가지 문제가 있었습니다.
> 
> 새로 개발된 `LedgerMetadataIO` 어댑터는 첫째, 열기 전 파일 크기를 8MiB 이내로 강제하고, 둘째, 기존 원장 및 과거 원장의 SHA-256을 고정하여 원장 변조를 원천 방지하며, 셋째, 모든 읽기/쓰기를 동일한 16GiB 스코프 프로필에 계상합니다.
> 
> 특히 상태 전이 검증을 통해 오직 허가된 최대 2개의 신규 배치만 예약할 수 있고, 본 어댑터 인스턴스가 직접 예약한 배치만 정산할 수 있도록 격리했습니다. 과거 2023년 반텐·서자바의 미정산 배치 136MiB는 절대 수정되지 않도록 불변성을 보장합니다.
> 
> 독립 정적 검토에서 지적된 세 가지 결함(레거시 실패 시 정지 누락, bind 초기 실패 시 재사용 가능성, TOCTOU 경쟁)을 완벽히 해결했으며, 변이 검사를 통해 7개 결함이 정확히 차단됨을 입증했습니다. 메인 코드베이스 적용 후 신규 단위 시험 45건과 기존 의존 모듈 147건, 총 192건의 테스트가 전원 통과(VERIFIED_REAL)했습니다. 실제 수집 파이프라인 연결을 위한 견고한 토대가 마련되었습니다."

---

## 7. 질의응답 (Q&A)

**Q1. 이번 작업으로 실제 위성 영상 나지(Bare Land) 수집을 즉시 시작할 수 있습니까?**
- **답변:** 아닙니다. 이번 작업은 원장의 I/O 안전성을 보장하는 어댑터와 원자적 저장기를 메인에 준비한 단계입니다. 170 실제 수집기 worker 연결(328 파이프라인)이 아직 남아 있어 실제 네트워크 수집 64MiB 차단은 계속 BLOCKED 상태로 유지됩니다.

**Q2. 기존에 동작하던 수집기나 레거시 코드에 영향이 있습니까?**
- **답변:** 없습니다. `CollectionLedger`의 기본 인자는 `metadata_io=None`으로 유지되며, 이 경우 기존 레거시 경로와 바이트 단위로 동일한 출력을 생성합니다. 메인의 9개 의존 모듈 147건 시험이 모두 변경 없이 통과함으로써 완벽한 하위 호환성이 검증되었습니다.

**Q3. 쓰기 작업 도중 `APPLIED` 에러가 발생하면 원장은 어떻게 처리됩니까?**
- **답변:** `APPLIED`는 디스크 파일 교체(`os.replace`)는 완료되었으나 그 직후 수행된 검증에서 문제가 발생했음을 의미합니다. 이 경우 어댑터는 영구 정지되며, 자동 롤백이나 환불을 시도하지 않습니다. 파일이 실제로 변경되었을 수 있으므로 운영 감사관이 수동으로 원장을 확인하고 검산해야 합니다.

**Q4. 기존에 남아 있는 2023년 반텐·서자바 미정산 예약분(136MiB)은 어떻게 처리됩니까?**
- **답변:** 본 어댑터는 기존 미정산 예약분을 절대 건드리지 않고 그대로 보존합니다. 어댑터가 예약하지 않은 과거 배치는 정산 대상에 포함될 수 없으며, 상태 전이 검사에서 기존 행이 1비트라도 변경되면 저장이 거부됩니다.
