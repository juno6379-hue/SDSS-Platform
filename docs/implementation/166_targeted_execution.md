# 166 — 나지 표적 수집의 로컬 준비 controller

- updated_at: 2026-10-18 KST
- source_commit: 작업 트리 신규 166 파일, Root 최종 커밋에서 고정
- evidence_paths: `evidence/integration/targeted-execution-agent-final-20261018.log`
- confidence: 합성 래스터·경계/동시성 시험 범위에서 확인
- status: TESTED_SYNTHETIC / 실제 표적 dispatch BLOCKED

## 구현 범위와 목적

`backend/app/data/targeted_execution.py`의 `TargetedPreparationController`는 기존 160 자산 검사와 162 단일 프로세스 scene claim을 연결한다. 같은 장면을 두 worker가 중복 채택하거나 기존 출력에 덮어쓰는 것을 막기 위한 내부 준비 단위다. 실제 수집기·HTTP·원장·기존 수집 lock·운영 모델은 수정하거나 호출하지 않는다.

`execution_supported=false`는 성공한 로컬 준비 결과에서도 유지한다. 로컬 native GTiff 검사 성공은 Sentinel B02의 출처·촬영연도·승인, 전체 inventory 검증, 데이터 품질 통과 또는 네트워크 실행 허가가 아니다. 과거 157/160/162의 미연결 상태를 이 단위만으로 해소했다고 표현하지 않는다.

## Python 계약

```python
controller = TargetedPreparationController(
    project_root, existing_output_root_under_data, "val", shared_scene_claim_registry)
result = controller.prepare({
    "schema_version": 1,
    "scene_id": "selected-scene-id",
    "split": "val",
    "owner_id": "worker-1",
    "output_name": "target-2025-001",
    "geometry_request": geometry_request_160,
})
```

`SceneClaimRegistry`는 모든 worker가 **동일한 인스턴스**를 공유해야 한다. 여러 프로세스·다른 객체의 원자적 claim을 제공하지 않는다. 생성자의 고정 split과 요청 split이 다르면 출력 생성 전에 차단한다. 162 seed의 기존 단일 split과 충돌하거나 기존 여러 split scene이면 해당 helper가 차단한다. 기존 seed의 완전성은 caller 책임이며 이 controller가 검증한 것으로 표시하지 않는다.

출력 parent는 이미 존재하는 `project_root/data/`의 하위 디렉터리여야 한다. `data` 자체나 누락된 parent는 허용하지 않는다. 루트·조상의 경로 alias 검사와 parent identity 검사 후 영숫자/밑줄/하이픈 단일 leaf를 `os.mkdir`로 배타 예약한다. Windows 장치 예약명·경로 구분자·점/공백 이름은 거절한다. 기존 파일·디렉터리는 비어 있더라도 덮어쓰거나 재사용하지 않는다.

배타 예약 → scene claim → 160 `inspect_targeted_asset_geometry` → parent/leaf identity·빈 상태 재검사 순서다. 160은 pinned 영상과 라벨 각각의 실제 CRS·격자·크기에서 요청 **전체 bbox의 native envelope**가 포함되는지 검사한다. 영상·라벨의 동일 격자를 요구하거나 resampling하지 않는다. 비선형 투영 전체영역에 대한 수학적 증명이 아닌 densified 수치 관측이며 기존 160의 한계를 그대로 유지한다.

성공 상태는 `LOCAL_PREPARED_EXECUTION_BLOCKED`, issue는 `EXECUTION_GUARDS_NOT_CONNECTED`다. `scene_claim`과 `asset_geometry`는 각 helper의 관측을 포함하고, `output_relative_path`는 프로젝트 상대경로다. budget/rate-limit/inventory/quality/preprocessing/settlement/training flags는 모두 false다. HTTP endpoint와 dispatch entry는 없다.

## 실패와 보존

주요 issue는 `CONTROLLER_INVALID`, `REQUEST_INVALID`, `FIXED_SPLIT_CONFLICT`, `OUTPUT_ALREADY_EXISTS`, `OUTPUT_PARENT_CHANGED`, `OUTPUT_RESERVATION_CHANGED`, `OUTPUT_RESERVATION_NOT_EMPTY` 및 160/162의 기존 guard code다. 원본 경로나 요청 문자열을 오류 메시지로 반사하지 않는다.

이 호출이 생성했고 parent·leaf identity가 그대로인 **빈 디렉터리만** 비재귀 `os.rmdir`로 해제한다. 외부 파일이 생기거나 identity가 바뀌면 보존한다. cleanup은 `NOT_NEEDED`, `OWN_EMPTY_RESERVATION_RELEASED`, `PRESERVED` 중 하나다. 기존 출력과 다른 예약을 제거하지 않는다. 실패한 scene claim도 해제하지 않아 재시도보다 보수적 차단을 선택한다. 같은 owner의 162 idempotent replay 역시 새 출력 생성 권한이 아니므로 `SCENE_CLAIM_REPLAY_REQUIRES_EXISTING_OUTPUT`으로 차단한다.

성공 시 빈 예약은 유지되지만 현재 controller는 그 안에 파일을 쓰거나 후속 처리를 실행하지 않는다. 이후 writer·원장 정산·오류 회수의 소유권 계약은 후속 연결이 필요하다. 디렉터리 검사는 순차 검사이고 OS 수준 트랜잭션이나 적대적 filesystem 교체에 대한 완전한 보안 증명은 아니다. 신뢰할 수 있는 프로젝트 data parent에서 동일 coordinator의 worker를 조정하는 범위다.

## 시험과 근거

`tests/test_targeted_execution.py`는 12개 사례로 다음을 검사한다.

- 실제 생성한 GTiff 영상·다른 해상도 라벨의 native 검사, 입력 bytes 보존, 실행 false.
- 기존 파일/디렉터리 보존, 동일 leaf 동시 예약 한 명만 성공.
- 공유 scene 동시 claim 한 명만 성공, 패한 worker의 자기 빈 예약만 해제.
- 고정 split 및 seed split 거부, pin 불일치, 실패 claim 유지와 replay 차단.
- 실패 중 생성된 외부 파일과 다른 예약 보존, 부모/leaf 교체 시 해제 금지.
- 잘못된 root·예약명·입력 거부, Windows reparse 속성 차단.
- 실제 symlink 생성 검사는 OS 권한이 없으면 skip하며 그 경우 실 symlink 보호 검증 성공으로 보고하지 않는다.

재현: `PYTHONPATH=backend;.runtime` 환경에서 `python -m unittest discover -s tests -p test_targeted_execution.py -v`. 최초 10개 시험과 중간 12개 로그 이후 same-owner replay 보강을 추가했으므로 최종 소스의 시험 근거는 `targeted-execution-agent-final-20261018.log`다. 합성 관측을 프로젝트의 새 적격 패치 확보로 계산하지 않는다.

최종 결과는 **12개 실행 / 11 PASS / 1 SKIP, 3.496초**다. SKIP은 이 Windows 세션의 실제 symlink 생성 권한 부재이며 reparse 속성 mock 경계 시험은 별도로 PASS다. Rasterio의 PendingDeprecationWarning은 기록하되 테스트 실패가 아니다.

## 다음 연결과 인계

Root의 pending/raw-support footprint inventory 검사와 연결하고, 157 proposal·선택 STAC/B02 출처·고정 split·native 자산의 동일 요청 pin을 확인해야 한다. 기존 예산 사전예약·2 worker/2초 공유 제어·최초 429 전역 중단·물리 상한·전처리 품질·성공/실패 정산을 하나의 controller 계약으로 통합하고 시험하기 전까지 실제 표적 HTTP를 허용하지 않는다. 현재 일반 부족분 수집기는 별도 기존 경로에서 동작하며 이 helper가 실행한 것으로 보고하지 않는다.

내부 기능으로 API/UI에 새 상태를 노출하지 않아 이번 단위에서 화면 변경은 필요 없다. 이해 에이전트는 “기존 출력 보존과 장면 경쟁 방지의 로컬 연결은 시험됨, 실제 표적 수집은 아직 차단”으로 설명해야 한다. 공통 인계서·이해자료·UI 갱신은 완료된 코드/최종 시험을 받은 Root 담당이 수행한다.
