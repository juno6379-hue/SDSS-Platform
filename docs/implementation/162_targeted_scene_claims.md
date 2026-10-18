# 162 — 표적 수집을 위한 프로세스 내 scene claim

상태: `TESTED_SYNTHETIC`. 신규 `SceneClaimRegistry`는 하나의 coordinator 객체를 공유하는 두 worker가 같은 scene을 동시에 다른 split로 채택하지 않도록 메모리에서 check와 claim을 한 lock 안에서 수행한다. collector·157·160·원장·API·159 후보를 변경하거나 연결하지 않았다. 파일·네트워크·운영 원장 쓰기는 0이다.

## 입력과 사용

```python
from app.data.targeted_scene_claims import SceneClaimRegistry

registry = SceneClaimRegistry({
    'schema_version': 1,
    'kind': 'DECLARED_SCENE_SPLIT_HISTORY',
    'source_manifest_sha256': 'a' * 64,  # caller 선언 예시, 실제 파일 검증 아님
    'scenes': [{'scene_id': 'existing-scene', 'split': 'train'}],
}, max_claims=256)
result = registry.claim({
    'schema_version': 1, 'scene_id': 'new-scene',
    'split': 'val', 'owner_id': 'worker-1',
})
```

seed는 위 exact4 키만 허용한다. caller가 명시적으로 축약한 scene 이력만 받으며 raw manifest나 파일 경로를 받지 않는다. source_manifest_sha256은 lowercase64 SHA **지문 선언**이다. 파일 존재·바이트·출처와 대조하지 않는다. scenes는 최대1024개이고 각 record는 정확히 scene_id/split이다. 같은 scene/split의 반복 선언은 set으로 합쳐진다. 같은 scene의 여러 split 선언은 오류를 숨기거나 어느 한쪽을 선택하지 않고 해당 scene을 quarantine한다. quarantine된 scene과 무관한 scene은 계속 검사할 수 있다.

request는 정확히 schema_version/scene_id/split/owner_id다. schema_version은 bool이 아닌 정수1이다. split은 train/val/test 중 하나다. scene_id는1~160자, owner_id는1~80자이며 ASCII 영숫자로 시작하고 이후 영숫자·`_ . : -`만 허용한다. 공백·경로 슬래시·줄바꿈·bool을 허용하지 않는다. 식별자는 대소문자를 구분하는 caller 문자열이고 이미지 별칭·동일 scene의 다른 ID를 찾아 합치지 않는다.

138 `_copy_json`을 seed/request 각각에 사용해 깊이16·8192노드·256KiB 및 list1024/dict128 한도, exact builtin JSON, cycle/surrogate/NaN/Inf/53bit 밖 정수 차단을 유지한다. 복사한 값만 검사·저장하므로 정상 호출 후 caller가 입력을 바꿔도 내부 상태는 바뀌지 않는다. caller가 복사 중 동시에 dict를 바꿔 예외가 나면 고정 오류로 닫힌다. 동시에 바뀌는 입력의 원자적 snapshot을 보장하지 않으므로 caller는 요청 인계 중 입력을 변경하지 않아야 한다.

## 한 lock 안의 판정

입력 사본 검증 후 아래 상태 판정을 같은 객체의 `threading.Lock` 안에서 연속 수행한다.

1. 초기 seed/cap이 잘못됐으면 항상 거부한다.
2. seed의 같은 scene에 여러 split이 있으면 `SEEDED_SCENE_QUARANTINED`다.
3. seed의 기존 단일 split과 요청 split이 다르면 `DECLARED_SPLIT_CONFLICT`다.
4. 이미 claim됐다면 같은 scene/owner/split 조합만 replay다. 다른 owner는 같은 split이어도 `SCENE_ALREADY_CLAIMED`, 같은 owner의 다른 split도 거부한다.
5. 신규 claim 수가 cap에 도달하면 `CLAIM_CAP_REACHED`다. 그렇지 않으면 scene/owner/split을 함께 저장한다.

max_claims는 bool이 아닌1~1024 정수이며 기본256이다. **cap은 이 객체에서 새로 받아들인 고유 scene claim 수**다. seed 이력 개수·거절 횟수·idempotent replay는 cap을 소비하지 않는다. seed의 기존 scene도 같은 split으로 첫 claim이 성공하면 cap1개를 소비한다. cap 검사와 삽입이 같은 lock 안에 있어 동시에 다른 scene을 claim해도 한도를 넘지 않는다. cap이 가득 차도 기존 정확한 replay는 허용한다.

자동 release·환불·TTL·영속화·예외 시 claim rollback은 없다. 한 번 받아들인 claim은 객체 수명 동안 남는다. claim 뒤 실제 수집 실패를 이 모듈이 알거나 해제하지 않는다. owner는 caller가 정한 식별자이며 기관 권한이나 신원 인증 결과가 아니다.

## 반환과 차단 경계

성공도 `LOCAL_SCENE_CLAIMED_EXECUTION_BLOCKED` / `EXECUTION_GUARDS_NOT_CONNECTED`다. 반환 claim은 caller에게 주는 새 deep copy이고 내부 dict를 공유하지 않는다. replay 여부와 현재 claim 수/cap, caller의 source SHA 선언을 제공한다. `snapshot()`도 같은 lock에서 fresh nested copy를 반환한다. 잘못된 seed/request는 `SEED_INVALID`/`CLAIM_REQUEST_INVALID`, 잘못된 cap은 `CLAIM_CAP_INVALID`로 닫는다. 실패는 claim=null이며 caller ID나 예외 원문을 오류 설명으로 출력하지 않는다. 정상 claim/snapshot에는 caller가 제공한 식별자만 포함된다.

모든 결과에서 다음은 false다: execution_supported, inventory_complete, source_pins_verified, pending_verified, footprints_verified, image_aliases_verified, quality_verified. 이는 출처 검증·과거 이력 완전성·pending/보조 영상 footprint·scene 별칭·품질·학습·운영 승인·예산 정산을 검증하지 않는다는 뜻이다. 과거 자료가 이미 multi split이면 그 scene만 격리하는 것이며 전체 데이터가 누출 없이 정상이라는 승인이 아니다.

**lock과 registry는 한 Python 객체의 한 프로세스에만 유효하다.** 다른 객체·다른 프로세스·재시작 후 registry와는 상태를 공유하지 않는다. 독립 coordinator 두 개가 같은 scene을 각각 받아들일 수 있으며 이를 지원 한계로 명시하고 시험했다. 실제 보호로 사용하려면 나중에 검증된 최신 inventory와 모든 worker가 공유하는 동일 객체를 caller가 연결해야 한다. 다중 프로세스는 별도의 공유 원자 저장소가 필요하며 이 단위의 구현 범위가 아니다.

## 시험과 UI 영향

```powershell
$env:PYTHONPATH='.runtime;.;backend;tests'
python -m unittest test_targeted_scene_claims -v
```

`evidence/integration/targeted-scene-claims-agent-20261018.log`: 최종 **10 PASS / 0.132초**다. 초기9 PASS/0.091초와 합산하지 않는다. Barrier+ThreadPool로 같은 unseen scene의 train/val 경쟁을20회 반복해 정확히1 claim·1거부를 확인하고, cap1에서 서로 다른 scene의 동시 요청도 정확히1개만 받아들이는지 검사한다. 기존 cross-split 거부·multi-split quarantine·다른 owner 같은 split 거부·정확한 replay·가득 찬 cap에서 replay·반환값 오염·입력 변경·잘못된 seed/request와 cap·I/O 차단·독립 객체 비공유·복사 중 RuntimeError 비누출과 다음 호출 회복을 검사한다. 합성 thread 경쟁 시험이며 실제 collector·운영 scene 채택이나 다중 프로세스 통합시험이 아니다.

Root는 후속 read-only 관측에서 현재 manifest의 `(scene_id, split)`을 dedupe한 축약 선언과 그 manifest SHA 선언으로 별도의 private registry를 구성하고, 실제 저장 이력의 cross-split scene이 quarantine되는지 확인할 수 있다. 이 경우에도 모듈 자체의 source_pins_verified/inventory_complete는 false이며, 원본 파일 전체 재해시·과거/예약 이력 완전성 승인·자료 재분할·기존 수집 변경·dispatch가 아니다. 관측 시점과 별도 증거를 함께 기록해야 한다.

내부 메모리 helper만 추가했고 HTTP·화면·기존 Workspace 계약을 바꾸지 않았으므로 UI 연결과 브라우저 검증은 필요하지 않다. Root의 독립 검토·이해자료·공통 문서와 인계 갱신은 최종 마감에서 별도로 수행한다. 전체 프로젝트·표적 수집 실행 guard는 미완료다.
## Root 통합 수락 — 2026-10-18 11:00 KST

Root는 신규162·160·157의 관련 시험을 함께 실행해28 PASS/9.204초/exit0을 확인했다. 독립10 PASS/0.058초와 agent10 PASS/0.132초는 중복 범위이므로 합산하지 않는다. 근거는 `targeted-scene-claims-root-related-20261018.log` 및 `targeted-scene-claims-independent-20261018.json`이다.

실제 저장 manifest1512행에서 scene/split 선언을 축약해94개 고유 scene의 private registry를 만들었다. 여러 split에 걸친 기존 scene1개는 train/val/test 모두 quarantine으로 거부됐고, 단일 split scene의 다른 split 요청도 거부됐다. 같은 선언 split의 private claim1개만 기록했으며 원본 manifest SHA는 변하지 않았다. 축약 이력의 원본 지문은 관측 caller가 대조한 것이며 registry 자체의 source_pins_verified나 inventory_complete는 계속false다. 원본 manifest에 없는 source report·pending footprint·이미지 별칭 등 전체 이력의 완전성을 확인하지 않았다. 운영 worker의 공유 객체·실제 scene 선택·실제 수집에 연결한 결과도 아니다.

근거는 `targeted-scene-claims-real-history-20261018.py/json`이다. 설명/대본/FAQ는 별도 이해 담당의 `docs/understanding/162_TARGETED_SCENE_CLAIMS.md`에 기록한다. 기존 collector/API/UI 변경이 없는 내부 메모리 helper이므로 새 HTTP·화면 연결과 브라우저 검증은 이 단위에 필요하지 않다. 실행 연결·기존/예약 영역의 완전한 inventory·160 실제 crop 정렬·정산·최종 품질은 계속 후속이다.
