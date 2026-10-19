# 218 — 부족 셀 수집의 로컬 support 검산 용량과 실패 진단 보완

상태: **IMPLEMENTED / TESTED_SYNTHETIC**. 운영 full inventory·collector·재시도·native·HTTP는 이번 담당이 수행하지 않았다. 211 과거 실행은 실패 그대로이며 수정판의 실제 현재 inventory 통과나 원격 수집 성공을 보장하지 않는다.

## 실제 정황과 원인 판단의 범위

Root 보고상 211은 34.422초 뒤 exit2, `DEFICIT_LOCAL_PROOF_INVALID_CENTER_FULL_INVENTORY_NOT_VERIFIED`로 예약/worker 전에 중단했다. source/ledger 불변, native0이다. 당시 CLI가 내부 inventory issue를 저장하지 않았으므로 과거 내부 예외를 사후에 확정 복원할 수는 없다.

[Root stat 진단](../../evidence/integration/inventory218-stat-diagnostic-root-20261018.json)은 같은 roots/refs의 경로/stat만 계산했으며 래스터/hash inventory를 재실행하지 않았다. 전체 파일1515개, support assets1275개, 합계 **2,166,734,413바이트**다. 기본2GiB=2,147,483,648보다 **19,250,765바이트** 크다. 단일 최대14,561,626바이트는 기존 개별64MiB 이내다. source/ledger pin은 각각 `80eef2d274942c7a7f9bf8ee2483af070a729060d84ceb1a19baacb52ae4976a` / `6e9e27b0ba9e4d222f9fde6b1e22f2adfd604701163d8e2c4653617c47af02fc`로 기록돼 있다. 이 문서 담당이 운영 파일을 다시 읽어 검산한 것은 아니다.

코드의 `inspect_targeted_inventory()`는 pending config/B02 존재 검산 뒤, 실제 support hash/raster loop에 진입하기 전에 `sum(asset.stat().st_size) <= max_bytes`를 검사한다. 기본 max_bytes는2GiB다. 위 stat 합계는 그 조건을 위반하는 구체적 재현조건이다. 이번 시험에서는 동등한 합계 초과가 `INVENTORY_LIMIT`→199 `CENTER_FULL_INVENTORY_NOT_VERIFIED`로 이어짐을 격리 검증했다. **과거211의 미저장 내부 issue를 실측했다고 표현하지 않는다.**

이 크기는 이미 저장된 모든 support 파일의 로컬 검산량이다. 원격 전송량·원장 사용액·JSON source 크기가 아니다. 나지/품질/겹침이 통과했다는 수치도 아니다.

## 변경 계약

`backend/app/data/deficit_candidate_guard.py`에 고정 `LOCAL_SUPPORT_PROFILE='DEFICIT_LOCAL_SUPPORT_3G_V1'`, `LOCAL_SUPPORT_BYTES=3*1024**3`를 추가했다. 199 부족 셀 proof의 단 한 번 `inspect_targeted_inventory(...,max_bytes=LOCAL_SUPPORT_BYTES)` 호출에만 적용한다. 요청에서 상한을 임의 지정하거나 초과할 때 동적으로 올리거나 재시도하지 않는다.

공용 `targeted_inventory.py` 함수의 기존 default2GiB와 허용 최대4GiB, 정수/bool 구분, max_files10000, 개별 support snapshot64MiB는 유지했다. 기존 일반/256 collector가 명시3GiB로 자동 전환되지 않는다. JSON source cap은 해당199/inventory 경로가 이미128MiB였으며 이번 변경은 이를 바꾸지 않았다. 164/173/182 등 다른64MiB JSON 경로도 변경하지 않았다.

COG64MiB+metadata1MiB/batch, 추가전역4GiB, 실제 원장 잔액/예약·정산, 기존pending2 전액136,314,880바이트, 물리3000/+16×inflight, 공유scene/window와분할, source/pending/SCL/미등재지원영역, 실제B02 1024, 최종80%/95% 품질,2초/첫429·재시도0은 모두 동일하다. 용량 여유 때문에 overlap·품질 검사를 생략하지 않는다.

## 제한된 진단을 실제 CLI까지 보존

공용 inventory의 반환값에는 다음 **관측값**을 추가했다. 관측 단계에 도달하지 않았으면 null이다. verified와 혼동하지 않는다.

```json
{
  "resource_limits": {"max_files": 10000, "max_support_bytes": 3221225472},
  "observed": {"enumerated_files": 1515, "support_files": 1275, "support_bytes": 2166734413}
}
```

199는 full proof 검증 전에 `inventory_diagnostic`을 저장한다. 이 필드는 `resource_profile`, 고정 `max_files/max_support_bytes`, 최대80자 `[A-Z_]+` issue 또는null, 그리고 `enumerated_files/support_files/support_bytes`만 포함한다. 정수는bool제외·0..2^63−1 범위이며 나머지는null이다. 임의 예외 문자열·path/current_asset·asset목록·trace를 복사하지 않는다. 실패 result의 `inventory`는 여전히null이고 job_proposals는 비어 있다. 기존 최상위 issue와 execution false 계약은 유지한다.

실제 `scripts/collect_deficit_guarded.py`는 기존 ValueError 하위 `DeficitLocalProofFailure`로 이 optional 진단만 전달한다. 알려진 profile/정확정수 상한을 다시 확인하고 코드/숫자를 재정제한다. `local_checks_passed=false`의 실패에만 보존하며, true지만 proof가 오염된 경우는 generic invalid와진단없음을 유지한다. `main()`의 실패 stdout에 아래처럼 optional 필드를 추가한다.

```json
{
  "status": "BLOCKED",
  "executed": false,
  "execution_started": false,
  "issue": "DEFICIT_LOCAL_PROOF_INVALID_CENTER_FULL_INVENTORY_NOT_VERIFIED",
  "inventory_diagnostic": {
    "resource_profile": "DEFICIT_LOCAL_SUPPORT_3G_V1",
    "max_files": 10000,
    "max_support_bytes": 3221225472,
    "issue": "INVENTORY_LIMIT",
    "observed": {"enumerated_files": 1515, "support_files": 1275, "support_bytes": 2166734413}
  }
}
```

이는 **격리 시험 출력 계약의 예시**이며 수정판이 현재자료에서 같은 오류를 냈다는 기록이 아니다. status/exit2·execute_requested·예약/실행권한/정산 의미는 변경하지 않았다. stdout은 운영 API/UI 응답이 아니며 화면 연결이 필요 없는 내부CLI 진단이다. 향후UI에 노출한다면 optional 진단 스키마를 별도 소비해야 한다. 현재 웹서버/API/브라우저 변경은 없다. 과거211 로그를 수정하거나 새로운 진단을 과거기록에 덧씌우지 않았다.

## 검증 방식과 한계

`tests/test_targeted_inventory.py`는 Temp의 작은 실제 GeoTIFF 헤더/CRS/겹침 처리와 **Mock stat 합계**를 조합했다. 34개 support의 각64MiB 모의크기로2GiB 초과→기본 차단, 고정3GiB에서 전체검사 진행을 확인했다. 48개×64MiB=정확3GiB 허용, cap보다1바이트 초과하는 합계 차단을 확인했다. 2–3GiB 실제 파일을 생성/전량 hash한 성능 시험이 아니다. stat 모의 구간의 support `_snapshot`은 작은 실제 TIFF bytes를 반환하도록 명시 Mock하며, 전달된 개별 상한64MiB를 검사했다. 기존 단일파일 snapshot의 실2GiB 전송/성능 보장으로 해석하지 않는다.

추가로 max_bytes의bool/0/음수/float/NaN/4GiB초과 거부, source/ledger/파일 불변, pending·역사source·SCL overlap·변조·drift·지리좌표 지원 등 기존 회귀를 실행했다.199 시험은 fixed3GiB 전달·bounded 진단·원장생성/쓰기0을 검증한다.200 시험은 실제 CLI subprocess(Temp cwd/sitecustomize로 request/helper만Mock, 운영읽기금지)를 통해 실패 stdout에 issue/bytes가 남고 비밀경로는 제거됨을 확인한다. Temp에서 `execute=True` 실패도 예약·worker0/owner lock해제/원본불변을 확인했다. 이 명령은 운영collector 실행이 아니다.

초기 집중 명령은 `tests.test_*` import 경로 설정 오류로2개 import 실패했고 실제시험0회였다. 원로그를 보존한 뒤 `PYTHONPATH=backend;.runtime;workspace;tests`와 모듈명 `test_*`로 바로잡았다. 집중 **38 PASS /17.344초**는 [재검증 로그](../../evidence/integration/inventory218-focused-recheck-20261018.log), 최초 명령실패는 [원로그](../../evidence/integration/inventory218-focused-20261018.log)에 있다. 실제CLI 격리회귀를 포함한 관련170/199/200/liveguard 최종 **108 PASS /34.655초**, skip0은 [관련 최종 로그](../../evidence/integration/inventory218-related-20261018.log)에 있다. 합성시험 완료이며 운영 full inventory 검산은 아니다.

제품3개의218전 bytes도 working파일을 되돌리지 않고 메모리에서 최소diff를 역적용해 재구성했다.211 reviewed code-pin의 SHA와 **정확히 일치한 경우에만** 새archive를 썼다. 이는 별도 역사원본 파일을 발견한 것이 아니다. [재구성 기록](../../evidence/integration/inventory218-before-reconstruction-20261018.json)과 `inventory218-before-reconstructed-{deficit_candidate_guard,targeted_inventory,collect_deficit_guarded}.py`를 보존했다. 대응SHA는 `c8eece7cbb0d3fed77f704b65eda9e51fe2e300ea56fdfd4aa020d9c9653204f`, `f4cc45b0e0cb6d94e112cd6c377ca1130c2e32359f7b01b8fdf8f9f210dffee9`, `6e41c4ead9262133b497e802050671da1bc0a969027a39735429a72c720f112a`다. 수정판 source/test/doc·시험 로그의 최종핀은 [218 freeze](../../evidence/integration/inventory218-freeze-20261018.json)에 기록한다.

## 운영 인계

Root가 변경소스 SHA·시험을 독립 검토한 뒤 새 pin·별도 실행으로만 실제 inventory를 확인한다. 현재 3GiB 안에 들어간다는 stat 산술은 이후 hash/CRS/소유/겹침/actual scene·B02 품질 통과를 보장하지 않는다. 원래211실패는 실패로 남고 자동 재시도는 없다. 이 완료코드·합성시험 및 과거 원인 한계를 Root의 이해담당에게 인계해 해설/대본/FAQ/INDEX/이력을 함께 갱신한다.
