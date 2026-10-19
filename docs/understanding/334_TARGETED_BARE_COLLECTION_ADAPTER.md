# 334. 표적 나지(Class 7) 수집 어댑터 64MiB 병목 해소 및 격리 검증

상태: **TESTED_SYNTHETIC** (격리 작업공간 `evidence/integration/target334-workspace-20261019`에서 32/32 전수 통과, 메인 미반영, 실제 수집 집행 가드는 **BLOCKED** 유지)

---

## 1. 쉬운 설명

프로젝트는 6개 주 9개 토지피복 클래스 중 심각하게 부족한 나지(Bare Ground, class 7)를 추가 수집하기 위한 표적 수집 계획(`prepare_targeted_bare_jobs`)을 갖고 있었습니다.
그러나 실제 약 69.6MB에 달하는 시계열 매니페스트(`annual-window-report.json`)를 사전 점검할 때, 시스템에 기본 설정된 64MiB 고정 상한선(`FILE_LIMIT`)에 걸려 파이프라인이 즉시 멈추는 병목이 발생했습니다.

Unit 334 작업은 Unit 333에서 메인에 공유 반영된 안전한 원장 어댑터(`LedgerMetadataIO`)와 128MiB 리소스 프로필(`ROLE_LIMITS['source'] = 134217728`)을 명시적 v3 요청 분기(`schema_version == 3`)로 연결했습니다.
이로써 69.6MB 크기의 매니페스트 사전점검을 가뿐히 통과하면서도, 기존 136,314,880B의 미정산 예약금을 완벽히 보존하고, 검증되지 않은 외부 원격 데이터가 유입되지 않도록 안전 가드(Fail-closed)를 유지했습니다.

---

## 2. 이론적 배경

### 2.1 리소스 프로필 상한과 계층적 I/O 바운딩
대규모 지리공간 메타데이터 처리 시 DoS 공격 및 메모리 누수를 방지하기 위해 파일 크기 및 I/O 상한(`Bounded Resource Profile`)을 강제합니다:
- 레거시 v1/v2 기본 상한: 64MiB ($67,108,864\text{ bytes}$)
- 명시적 v3/source 역할 상한: 128MiB ($134,217,728\text{ bytes}$)
- 단일 프로세스 전체 I/O 스코프 상한: 16GiB ($17,179,869,184\text{ bytes}$)

### 2.2 원장 어댑터(LedgerMetadataIO)의 트랜잭션 안전성
원장(`collection_ledger.json`)은 수집 비용과 예산 잔여액을 관리하는 핵심 자산입니다:
- 매 I/O마다 SHA-256 해시 핀을 검증하여 동시 프로세스 변조 방지.
- 원자적 임시 파일 쓰기 및 fsync 교체(`targeted_atomic_json.replace_json_value`).
- 허용된 새 배치 키(최대 2개)만 예약(`reserve`) 가능하며, 본 인스턴스가 예약한 키만 정산(`settle`) 가능.
- 기존 미정산 예약(`pending_reservations`, 136,314,880B)은 임의로 환불하거나 삭제하지 않고 전액 보존.

---

## 3. 코드·데이터 동작

1. **명시적 v3 요청 분기 (`scripts/collect_targeted_bare.py`)**:
   ```python
   if request.get("schema_version") == 3:
       jobs = prepare_explicit_targeted_bare_jobs(manifest_path, plan_config, profile=profile)
   else:
       jobs = prepare_targeted_bare_jobs(manifest_path, plan_config)
   ```
2. **원장 어댑터 인스턴스 바인딩**:
   ```python
   metadata_io = LedgerMetadataIO(ledger_path=ledger_path, profile=profile)
   ledger = CollectionLedger(ledger_path, metadata_io=metadata_io)
   ```
3. **Fail-Closed 예외 처리**:
   허용되지 않은 키 조작, 핀 불일치, 또는 128MiB 초과 시 즉시 `TargetedExecutionFailure`를 발생시키고 영구 정지(`stopped=True`).

---

## 4. 테스트 증거

격리 작업공간(`evidence/integration/target334-workspace-20261019`)에서 2가지 모드로 총 64건의 검증을 수행했습니다:

- **Focused Mode**: 신규 9건 + 레거시 회귀 23건 = **32 / 32 PASS** (소요시간 67.8초)
- **Portable Mode**: 격리 임시 디렉터리 복제 환경 32건 = **32 / 32 PASS** (소요시간 70.5초)
- **주요 검증 항목**:
  - 69.6MB 매니페스트 사전 점검 통과 (64MiB FILE_LIMIT 회피 확인)
  - 136,314,880B 기존 예약 바이트 불변 보존
  - 비인가 배치 키 예약/정산 시도 시 차단 및 어댑터 정지
  - 레거시 v1/v2 64MiB 경로 하위 호환성 100% 유지

---

## 5. 15개 후보 나지(Class 7) 현황 및 안전 경계

Unit 316/320/323 분석 결과 도출된 50개 후보 나지 윈도우의 공간적·운영적 상태:
- **기존 자산 미중복 후보 (15개)**: 남술라웨시 8개, 동자바 3개, 반텐 4개 (서자바 0, 고론탈로 0, 동남술라웨시 0).
- **후보 간 상호 중복**: 50개 후보 간 상호 교차 중복 쌍이 **56쌍** 존재하여, 15개 미중복 후보 역시 상호 완전히 독립된 15개 위치가 아님.
- **원격 품질 상태**: SCL 유효 화소율 및 B02 품질 미검증 상태 ("미검사·집행 미승인").
- **실행 차단 유지**: `execution_supported = False`, `learning_ready = False`, `scientific_accuracy_validated = False`. 실제 수집 집행 가드는 **BLOCKED** 상태를 엄격히 유지함.

---

## 6. 발표 스크립트

### 1분 스크립트
"Unit 334에서는 69.6MB 시계열 매니페스트 사전점검 시 발생하던 64MiB 고정 상한 병목을 해결했습니다. 명시적 v3 요청 분기와 128MiB 리소스 프로필, 그리고 앞서 검증된 원장 어댑터를 결합하여, 기존 1억 3,600만 바이트의 미정산 예약을 안전하게 보존하면서 대용량 사전점검을 완벽히 통과시켰습니다. 격리 테스트 32건을 100% 통과했으며, 실제 데이터 수집 가드는 여전히 엄격한 Fail-closed 상태를 유지하고 있습니다."

### 5분 스크립트
"신사숙녀 여러분, GeoAI 학습 데이터셋에서 가장 중요한 요소 중 하나는 클래스 간 불균형 해소입니다. 현재 우리 데이터셋은 나지 클래스가 0.5% 미만으로 극도로 부족합니다. 이를 보완하기 위한 표적 수집 파이프라인이 준비되어 있었으나, 6개년 시계열 매니페스트 크기가 약 69.6MB에 달해 레거시 64MiB 메모리 제한에 걸려 있었습니다.

Unit 334는 이 병목을 풀기 위해 두 가지 핵심 아키텍처를 도입했습니다. 첫째, 128MiB 리소스 프로필을 지원하는 `prepare_explicit_targeted_bare_jobs`를 명시적 v3 인터페이스로 연결했습니다. 둘째, Unit 333에서 메인에 통합된 원자적 JSON 교체기 및 원장 어댑터(`LedgerMetadataIO`)를 바인딩하여, 파일 I/O 과정에서 단 하나의 바이트도 누수되거나 변조되지 않도록 했습니다.

특히 2023년 반텐·서자바의 1억 3,600만 바이트에 달하는 미정산 예약금을 인위적으로 삭제하거나 환불하지 않고 100% 원본 그대로 유지했습니다. 또한 후보 나지 50개 중 유효한 15개 지점 역시 상호 56쌍의 공간적 겹침이 존재하고 원격 위성 품질이 아직 미검사 상태임을 규명했습니다. 이에 따라 시스템은 실제 수집을 즉시 집행하지 않고, 과학적 품질 기준이 충족될 때까지 Fail-closed 차단 상태를 유지하도록 설계되었습니다."

---

## 7. 예상 Q&A

**Q1: 128MiB 상한으로 올리면 메모리 부하가 커지지 않나요?**
A1: 아닙니다. 이 상한은 사전점검 파일 읽기 상한일 뿐 상시 메모리 점유량이 아닙니다. 파이프라인의 전체 I/O는 16GiB 스코프 안에서 엄격히 계상되며, 읽기가 끝난 메모리는 즉시 해제됩니다.

**Q2: 15개 후보 나지를 지금 바로 수집하면 학습 게이트를 통과할 수 있나요?**
A2: 즉시 수집할 수 없습니다. 15개 후보 지점은 Sentinel-2 SCL 유효 화소율(80% 이상)과 B02 품질이 아직 과학적으로 검증되지 않은 '미검사' 상태이며, 상호 겹침이 존재합니다. 품질 검증과 운영 승인 없이 수집을 집행하면 가짜 데이터나 노이즈가 유입되므로 안전 가드를 통해 차단(BLOCKED) 상태를 유지합니다.
