# 334. 나지(Class 7) 표적 수집 어댑터 — 64MiB 병목 해소 및 원장 격리 통합

상태: **TESTED_SYNTHETIC**. 격리 작업공간(`evidence/integration/target334-workspace-20261019`)에서 구현 및 합성 검증을 완료했습니다. 메인 리포지토리 파일은 일체 수정하지 않았으며, 실제 운영 원장과 라이브 제공자 STAC에는 연결하지 않았습니다.

---

## 1. 쉬운 설명

기존 표적 나지(Class 7/8) 수집 파이프라인(`scripts/collect_targeted_bare.py`)은 약 69.6MB 크기의 매니페스트(`annual-window-report.json`)를 읽으려 할 때 레거시 64MiB 파일 크기 상한(`_pinned(..., 64*1024**2)`)에 걸려 `FILE_LIMIT` 예외를 발생시키며 즉시 차단(fail-closed)되었습니다. 또한 수집 예산 원장 변경 시 128MiB 리소스 프로파일 및 SHA256 핀 고정 검증이 누락되어 있었습니다.

Unit 334는 이 병목을 해결하기 위해:
1. **명시적 v3 요청 분기 도입**: `schema_version == 3` 요청인 경우, 128MiB 상한(`ROLE_LIMITS['source'] = 134217728`)을 지원하는 `prepare_explicit_targeted_bare_jobs` (`run_explicit_local_preflight`)를 호출하여 69.6MB 매니페스트를 정상 검증·수용합니다.
2. **원장 메타데이터 어댑터(`LedgerMetadataIO`) 연동**: 수집 실행 시 `profile.scope(SOURCE_MARKER['name'])` 내에서 `LedgerMetadataIO`를 `CollectionLedger`에 바인딩하여 원장 읽기·쓰기를 원자적으로 감시하고 상태 전이를 검증합니다.
3. **136,314,880B 기존 pending 예약 완전 보존**: 과거 미정산 예약(136,314,880 바이트)을 환불하거나 훼손하지 않고 그대로 보존하며, 새로운 배치만 허용된 키로 예약·정산합니다.
4. **100% 하위 호환성 유지**: `schema_version`이 1 또는 2인 기존 레거시 요청은 기존 64MiB 경로와 `metadata_io=None` 기본값을 그대로 사용하여 과거 동작을 완전히 보존합니다.

---

## 2. 이론적 배경 및 아키텍처

- **이중 상한 프로파일 (Dual Cap Profiles)**:
  - 레거시 v1/v2 요청: 64MiB 엄격 상한 유지 (`prepare_targeted_bare_jobs`). 초과 시 즉시 차단.
  - 명시적 v3 요청: 계약 마커(`manifest_profile`, `local_support_profile`) 검증 후 128MiB 상한 프로파일 활성화 (`run_explicit_local_preflight`).
- **원장 상태 전이 원자성 (Ledger State Transition Atomicity)**:
  - `LedgerMetadataIO` 어댑터를 통해 원장의 SHA256 핀 일치 여부를 매 I/O마다 검증합니다.
  - 허용된 새 배치 키 1~2개에 대해서만 예약(`reserve`) 및 정산(`settle`)을 허용합니다.
  - 기존 배치(예: `preserved-old-pending`, 136,314,880B)는 어댑터 소유가 아니므로 임의 정산 또는 필드 변조 시 `LEDGER_SETTLE_NOT_OWNED`로 즉시 거부(`stopped=True`)됩니다.
- **Fail-Closed 안전 원칙**:
  - 검증 단계 또는 실행 중 원장·매니페스트 핀 불일치, 허용되지 않은 배치 접근, 디렉터리 변조 발생 시 즉시 중단되며 환불이나 자동 롤백을 수행하지 않습니다.
  - 예약 시도 후 실패한 배치는 `TargetedExecutionFailure`로 전파되어 미확인 전송을 방지합니다.

---

## 3. 코드·데이터 동작

### 3.1 수정 파일

| 파일 | 변경 내역 |
|---|---|
| `scripts/collect_targeted_bare.py` | • `validate_request`: `schema_version == 3` 감지 시 `validate_request_v3`, `inventory_envelope_v3`, `prepare_explicit_targeted_bare_jobs` 호출 (128MiB 사전점검). 레거시 v1은 64MiB 유지.<br>• `_request_metadata`: v3 요청에 대해 `manifest_profile` 및 `local_support_profile` 메타데이터 매핑.<br>• `run_targeted`: explicit 모드일 때 `profile.scope` 진입, `LedgerMetadataIO` 인스턴스화 후 `CollectionLedger(..., metadata_io=metadata_io)` 바인딩, `[p for p, _ in metadata_io._history]` 전달. |

### 3.2 요청 스키마 명세 (Schema Version 3)

```json
{
  "schema_version": 3,
  "maximum_batches": 1,
  "manifest_profile": {
    "name": "bounded128m-3000-v1",
    "sha256": "db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4"
  },
  "local_support_profile": {
    "name": "TARGETED_LOCAL_SUPPORT_3G_V1",
    "sha256": "062bf36199ee4e0f142cb117cad2f0c5b25411eb3ddd43ed37b30ca3b7a75a7a"
  },
  "plan": { ... },
  "ledger_ref": { ... }
}
```

### 3.3 원장 예약·정산 라이프사이클

1. **검증 단계 (`validate_request`)**:
   - 매니페스트(128MiB 상한), 원장(8MiB 상한) 스냅샷 핀 확인.
   - `prepare_explicit_targeted_bare_jobs`로 로컬 플랜 및 배치 제안 생성.
   - `physical_patch_inventory` 및 `inspect_targeted_inventory` 검증.
2. **사전 준비 단계 (`reserve`)**:
   - 새 배치 키에 대해 디렉터리 생성 및 `ledger.reserve(key, COG_BATCH + METADATA_BATCH, config_sha256)` 호출.
   - 어댑터가 허용 목록과 키 일치를 확인하고 원장에 pending 기록.
3. **수집 작업 단계 (`work`)**:
   - STAC 파라미터 로드 후 `collect_windows` 호출 및 B02/품질 검사.
4. **정산 및 발행 단계 (`finalize`)**:
   - `ledger.settle(key, measured_bytes, report_path)` 호출.
   - 어댑터가 소유권을 확인하고 원장에 settled 기록 및 실사용 바이트 차감.
   - 기존 136,314,880B pending은 불변 상태로 유지.

---

## 4. 테스트 증거

격리 작업공간에서 총 32개 테스트 케이스(Unit 334 전용 9건 + 레거시 회귀 23건)를 실행하여 100% 통과를 검증했습니다.

| 환경 / 실행 모드 | 테스트 케이스 수 | 통과 여부 | 소요 시간 | 기록 파일 |
|---|---|---|---|---|
| **Focused Mode** (작업공간 내 실행) | 32 / 32 PASS (334 9건 + 레거시 23건) | **PASS** (0 fail, 0 skip) | ~67.8s | `focused334-final.log`, `focused334-final-result.json` |
| **Portable Mode** (완전 격리 Temp 디렉터리 복사) | 32 / 32 PASS (334 9건 + 레거시 23건) | **PASS** (0 fail, 0 skip) | ~70.5s | `portable334-final.log`, `portable334-final-result.json` |

### 주요 검증 항목:
1. `test_legacy_v1_fails_closed_with_file_limit_on_69m_manifest`: 레거시 v1 요청 시 69.6MB 매니페스트에 대해 `FILE_LIMIT` 발생 및 fail-closed 확인.
2. `test_explicit_v3_preflight_resolves_69m_bottleneck`: 명시적 v3 요청 시 128MiB 프로파일이 69.6MB 매니페스트를 오류 없이 수용 및 검증 완료.
3. `test_explicit_dry_run_returns_verified_status_without_ledger_writes`: dry-run (`execute=False`) 시 원장 수정 없이 `LOCAL_DISPATCH_INPUTS_VERIFIED` 반환.
4. `test_execution_with_ledger_metadata_io_preserves_old_pending_reservation`: `execute=True` 실행 시 `LedgerMetadataIO` 바인딩, 새 배치 정상 settled 정산, 기존 136,314,880B pending 보존 확인.
5. `test_ledger_adapter_fails_closed_on_invalid_transition`: 작업 중 원장 변조 시 `TargetedExecutionFailure` 발생 및 fail-closed 검증.
6. `test_contract_validation_rejects_tampered_manifest_marker_before_io`: 계약 마커 변조 시 I/O 이전에 계약 거부.
7. `test_contract_validation_rejects_missing_support_marker_before_io`: support 마커 누락 시 계약 거부.
8. `test_unregistered_batch_key_cannot_be_reserved`: 미등록 배치 키 예약 시도 시 어댑터 즉시 차단.
9. `test_unowned_batch_key_cannot_be_settled`: 미소유 배치 키(기존 pending 등) 정산 시도 시 `LEDGER_SETTLE_NOT_OWNED` 차단.
10. `test_collect_targeted_bare_legacy.py`: 23개 레거시 테스트 전건 무수정 통과 (100% 하위 호환성).

---

## 5. 15개 후보 나지 현황 및 안전 경계

Unit 316 / 320 / 323 분석 결과 도출된 50개 후보 나지 윈도우의 현황은 다음과 같습니다:

### 5.1 공간 중복 분석 결과
- **총 평가 대상**: 50개 후보 윈도우
- **기존 지원 자산과 중복 (Overlapping Existing Support)**: 35개 (사전 제외)
- **기존 자산 미중복 후보 (Clear of Existing Support)**: 15개
  - 남선라웨시 (South Sulawesi): 8개
  - 동자바 (East Java): 3개
  - 반텐 (Banten): 4개
  - 동남술라웨시 (Southeast Sulawesi): 0개
  - 고론탈로 (Gorontalo): 0개
  - 서자바 (West Java): 0개

### 5.2 상호 중복 및 집행 미승인 경계 (Critical Findings)
> [!CAUTION]
> 1. **후보 간 상호 중복 (Candidate-to-Candidate Mutual Overlaps)**:
>    - 50개 후보 간 상호 교차 중복 쌍이 총 **56쌍** 존재합니다.
>    - 따라서 "기존 자산 미중복 15개"는 서로 완전히 독립된 15개 위치가 아니며, 후보 간 공간적 중첩이 포함되어 있습니다.
> 2. **원격 SCL / B02 품질 상태**:
>    - 15개 후보의 품질 상태는 **"미검사·집행 미승인"** 상태입니다.
>    - 실제 원격 Sentinel-2 STAC 자산에 대한 SCL 유효 화소율(80%) 및 B02 대역 품질 검증이 아직 수행되지 않았습니다.
> 3. **파이프라인 실행 상태 (BLOCKED)**:
>    - `execution_supported = False`
>    - `learning_ready = False`
>    - `scientific_accuracy_validated = False`
>    - 실제 다운로드 및 모델 학습 투입은 승인되지 않았으며, 집행 가드는 **BLOCKED** 상태를 엄격히 유지합니다.

---

## 6. 한계 및 안전 경계 (Limitations & Operating Guards)

1. **메인 저장소 무변경 (Strictly Zero Mutations)**:
   - 본 작업의 모든 구현 및 산출물은 `evidence/integration/target334-workspace-20261019/` 내부에 격리되어 있습니다.
   - 메인 브랜치의 소스 코드(`backend/`, `scripts/`)는 한 줄도 수정되지 않았습니다.
2. **원장 잔여 예산 및 기존 예약 보호**:
   - 기존 원장에 기록된 136,314,880B pending 예약은 취소되거나 환불되지 않고 그대로 보존됩니다.
3. **네트워크 및 실제 입출력 차단**:
   - 실제 Planetary Computer / Earth Search STAC 엔드포인트에 대한 HTTP 호출을 발생시키지 않았습니다.
   - 실제 운영 데이터셋(`data/first-group-training-esri-v1`)에 대한 쓰기를 수행하지 않았습니다.

---

## 7. 발표 스크립트 (30초 요약)

> "Unit 334는 표적 나지 수집 경로에서 약 69.6MB 매니페스트가 레거시 64MiB 제한으로 차단되던 병목을 해소했습니다. 명시적 v3 요청 시 128MiB 사전점검 경로를 활성화하고, LedgerMetadataIO 어댑터를 바인딩하여 136,314,880 바이트의 기존 미정산 예약을 안전하게 보존하면서 원자적 원장 전이를 보장합니다. 격리 환경에서 32개 전 테스트를 통과했으며, 기존 자산과 겹치지 않는 15개 후보지는 후보 간 56쌍의 상호 중첩과 미검사 상태로 인해 여전히 실행 차단(BLOCKED) 상태로 안전하게 관리됩니다."

---

## 8. Q&A

**Q1. 이번 작업으로 실제 나지 패치 수집이 시작되나요?**  
A. 아닙니다. 이번 작업은 64MiB 사전점검 병목을 해소하고 원장 어댑터를 격리 검증한 단계입니다. 15개 후보 나지는 원격 SCL/B02 품질이 미검사 상태이며, 후보 간 상호 중첩(56쌍) 해소 및 운영 승인 전까지 `execution_supported=False`로 실행 차단(BLOCKED) 상태가 유지됩니다.

**Q2. 기존 레거시 수집 요청의 동작이 변경되나요?**  
A. 전혀 변경되지 않습니다. `schema_version`이 1 또는 2인 요청은 기존 64MiB 사전점검과 기본 원장 I/O 경로(`metadata_io=None`)를 그대로 타게 되며, 레거시 테스트 23건이 100% 동일하게 통과함을 입증했습니다.

**Q3. 원장 변조나 잘못된 배치 키가 들어오면 어떻게 되나요?**  
A. `LedgerMetadataIO` 어댑터가 즉시 위반을 감지하고 `stopped=True` 상태로 진입하여 이후 모든 쓰기 호출을 영구 거부(fail-closed)합니다. 어떠한 자동 환불이나 불완전한 상태 롤백도 발생하지 않습니다.
