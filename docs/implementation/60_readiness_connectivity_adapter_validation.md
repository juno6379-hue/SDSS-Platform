# 60. 기본 off readiness 연결 근거 adapter

## 쉬운 설명과 상태

`assess(..., connectivity_diagnostics=True)`를 명시하면 기존 gate 판정을 끝낸 뒤 같은 평가에 추가된 scene 메타데이터의 연결 근거를 관측한다. 기본값은 false이며 기존 결과 key와 값이 그대로다. 기존 token/bbox union, blocker 순서, fixed split, 통계, verified_files, prepared_payload는 그대로 두고 True에서만 별도 `connectivity_diagnostics` 필드를 추가한다.

새 adapter와 합성 판정동등성 시험은 `TESTED_SYNTHETIC`이다. 실제 전체 자료 readiness를 다시 실행하지 않았다. Root가 저장 report의 witness 부재·보호 상태와 기존 코드 구조를 별도로 확인한다. 이 옵션은 과거 저장 판정의 원인을 복원하지 않는다. diagnostic status는 항상 BLOCKED이고 자체 ready/scientific/실행·정산·자동재개 승인 false, 환불 0이다. **outer gate가 합성 또는 약한 라벨 실험에 ready여도 내부 diagnostic은 BLOCKED일 수 있다.** capture 상태는 gate의 ready 또는 정확도 승인과 다르다.

## 실제 연결과 격리

기존 `backend/app/ml/readiness.py:assess`에 keyword `connectivity_diagnostics=False`를 추가했다. 정확한 bool만 허용하며 0/1/문자열/None/np.bool_는 자료 처리 전에 ValueError다. False에서는 adapter를 import/call하지 않고 추가 결과 필드를 생성하지 않는다.

True에서는 원래 report를 완성한 뒤 try 경계 내부에서 `(scenes, policy, province_groups, inputs)`의 detached deepcopy를 만들고 순수 adapter를 호출한다. 진단 과정이 입력 복사본을 수정한 뒤 예외를 발생시켜도 원래 gate 보고서·payload·policy·refs는 변하지 않는다. projection/copy/import/capture 예외를 관측 실패 상태로 담으며 blocker를 추가하지 않는다. adapter도 helper에 policy mapping 복사본을 전달한다. 기존 union 알고리즘은 진단 재계산으로 교체하지 않는다.

## 장면 범위와 토큰 의미

중요한 차이는 **patch count와 scene count가 같지 않다**는 것이다. 기존 assess는 앞단 파일·정규화 QA 등을 통과한 scene을 append하며, 해당 scene의 eligible_patches가 0이어도 token/bbox 연결에 참여한다. adapter는 그 내부 scenes 전체를 원래 순서로 투영한다. count>0 필터, 임의 scene 삭제, 목록 truncation을 하지 않는다. 진단 이름에 eligible metadata라는 58 인터페이스가 있어도 이번 호출의 실제 범위는 `ALL_APPENDED_ASSESS_SCENES_INCLUDING_ZERO_PATCH`이다. 독립적으로 적격성을 재평가하지 않는다.

- `scene_index`와 `eligible_position`은 assess 내부 scenes의 0부터 시작하는 순서다. 원본 manifest row index 또는 과거 저장 scene index가 아니다.
- `scene_mapping`에는 각 scene의 province/eligible_patches, zero patch 포함 여부, 원래 token 타입을 기록한다. patch 합계를 scene 수로 해석하지 않는다.
- 기본 scalar str/int/finite float/bool/None의 원래 truthiness와 str 의미를 지원한다. source_group이 falsy이면 빈 문자열로 투영하여 **두 token 역할 모두 skip**한다. scene_id는 항상 str 변환하므로 None은 `'None'`, 숫자 123은 `'123'`이다. 공유 namespace·last owner·동일 행 no-op 의미를 유지한다.
- source_group/scene_id의 list/dict/다른 객체 타입, 지나치게 긴 문자열·지원하지 않는 수치/좌표는 조용히 바꿔 해석하지 않고 NOT_CAPTURED로 남긴다. 기존 gate의 판정 자체는 바꾸지 않는다.
- 이미 assess가 계산한 bounds_wgs84를 그대로 list로 복사한다. adapter는 bbox를 새로 densify/반올림/재투영하지 않는다. 58의 엄격한 유한·양수 면적·경위도 범위 계약에 맞지 않으면 미포착이다. 추가 raster header/pixel/GEOS·네트워크 처리는 없다.

## 지원 policy와 한도

현재는 required_provinces가 **기본 FIRST_GROUP 순서와 정확히 같고** province_splits가 기존 six-province 4/1/1 mapping일 때만 포착한다. test_mode custom policy·다른 주 순서/분할은 NOT_CAPTURED_UNSUPPORTED_POLICY다. 기본 순서로 제한한 이유는 58의 fixed_split_conflict_events가 기본 주 순서를 사용하므로 사용자 지정 gate blocker 순서와 혼동하지 않게 하기 위해서다. 원래 gate는 custom policy를 계속 처리한다.

기본 한도는 2000 scenes / 전체 bbox pairs 1000000 / 저장 witness edges 10000이다. helper의 고정 hard cap을 넘는 값은 지원하지 않는다. 전수 scene 또는 pair 계획이 넘으면 모든 scene을 다루지 못한 상태를 NOT_CAPTURED_BUDGET으로 표시한다. scene list를 잘라 성공으로 반환하지 않는다. witness 저장 한도에 따른 truncation은 58처럼 전체 union 계산 완료와 별개다.

## 내부 API와 출력

```python
capture_readiness_connectivity(
    scenes, policy, province_groups, manifest_inputs, *, limits=None,
)
```

호출 가능한 내부 진단 함수이며 새 공개 API/CLI가 아니다. assess hook은 기본 limits를 사용한다. manifest_inputs는 readiness inventory가 이미 계산한 path/SHA 참조 최대128개를 복사한다. 이 adapter가 파일을 추가 검증했다는 뜻은 아니며 `manifest_reference_claim=ALREADY_COMPUTED_ASSESS_INPUTS_NO_ADDITIONAL_VERIFICATION`로 표시한다.

capture_status는 다음을 구분한다.

| 상태 | 의미 |
|---|---|
| CAPTURED_COMPONENTS_MATCH | 모든 appended scene의 지원 metadata로 helper를 완료하고 gate province_groups와 일치 |
| CAPTURED_COMPONENT_MISMATCH | helper 완료 후 component map이 달라짐. gate를 고치거나 blocker를 추가하지 않음 |
| NOT_CAPTURED_UNSUPPORTED_POLICY | custom policy 또는 required province 순서 등 지원 범위 밖 |
| NOT_CAPTURED_BUDGET | 전수 scene/pair 계획이 진단 한도 초과 |
| NOT_CAPTURED_UNSUPPORTED_METADATA | token/좌표/manifest refs 등 엄격 입력 범위 밖 |
| FAILED_DIAGNOSTIC | adapter/helper의 예상 밖 예외 |
| FAILED_ADAPTER_BOUNDARY | assess의 copy/import/capture 경계 예외. 안전한 최소 진단 필드만 제공 |

일반 adapter 결과는 scope, limits, scene_count/mapping, 이미 계산된 manifest refs, witness, gate_components_match를 갖는다. 성공시 projected_scene_metadata와 supplied_eligible_patch_sum도 포함한다. 조기 미포착 결과의 확인하지 못한 값은 null이다. boundary fallback은 schema_version/status/capture_status/error_type 및 gate_result_modified=false·ready/scientific/승인 false·환불0의 최소 객체다. 소비자는 capture_status를 먼저 보고 없는 포착 필드를 성공으로 간주하지 않아야 한다.

58 helper의 SOURCE_GROUP_MISSING 이슈가 있어도 원래 group skip·bbox union을 그대로 관측해 component map이 일치할 수 있다. CAPTURED_COMPONENTS_MATCH는 메타데이터 품질 승인 또는 학습 차단 해제가 아니다. 원래 gate가 SOURCE_GROUP_MISSING blocker를 기록하는 동작도 바꾸지 않는다.

단일 assess 실행 중에는 최종 source report SHA가 존재하지 않는다. 따라서 59 envelope의 provenance 필드에 가짜 hash를 만들거나 강제로 연결하지 않는다. current module도 자신의 파일 SHA를 읽지 않는다. code SHA와 실제 검증은 Root의 preflight/종결 증거가 맡는다. 과거 saved scene 연결/원인을 소급 확정하지 않는다.

## 시험 증거

관련 `tests/test_readiness_connectivity_adapter.py`는 기존 ReadinessTests의 작은 합성 raster·metadata fixture를 재사용한다. **17 PASS / 4.605초**, 로그 `evidence/integration/readiness-connectivity-adapter-related-20261017.log`.

확인 범위는 다음과 같다.

- default/off가 adapter를 호출하지 않음, True에서 진단 필드 하나를 제외한 전체 보고서의 typed JSON 동일성. 준비 payload·blocker 순서·통계·refs를 함께 비교.
- 0patch scene이 token bridge로 fixed split 충돌을 만드는 case에서 해당 scene/witness를 포함. 3 scenes와 eligible patches2 구분.
- 숫자 group와 None scene_id의 literal str, falsy group의 두 token skip, zero witness 저장과 전체 계산 완료.
- custom policy에서 outer ready=True를 유지하면서 diagnostic만 unsupported/BLOCKED. 역순 required provinces도 원래 gate 상태·순서를 유지.
- helper/capture/import 예외, 지원하지 않는 metadata/bounds·budget·component mismatch가 gate를 바꾸지 않음.
- capture가 scenes/policy/groups/inputs를 수정 후 raise해도 ready payload 불변. helper가 전달받은 mapping을 수정 후 raise해도 gate/adapter caller 입력 불변.
- on/off의 기존 raster read·file_digest·Path.read_text 호출 목록이 같음. 순수 adapter file-open trap, 정확 bool 선검사.

초기14 PASS는 오류격리·순서 보강 전 이력이다. 최종 관련/독립 재실행을 전체 regression 수에 중복 합산하지 않는다. 실제 전체 자료 assess를 이 단위에서 다시 실행하지 않으며, Root가 전체 회귀·AST/보호 상태를 별도 기록한다.

## 기존 증거·UI·후속 범위

선택 옵션 추가 때문에 readiness.py의 현재 파일 SHA는 의도적으로 바뀐다. default_policy mapping·기존 union/차단/통계 코드의 의미는 유지한다. 과거56/57 saved corner report에 기록된 readiness 구현 SHA `42945e3d864a0e63dab4d3100355bcd3506eecf2ada8bc654d573521ea1fdff2`는 그 저장 snapshot의 역사 값이다. 현재 SHA에 맞추려고 기존 보고서를 재작성하지 않는다. current code SHA 비교만으로 과거 report 생성 시점 코드를 인증하는 것도 아니다.

영속저장·기존59 envelope 통합·CLI/API/UI 활성화·실제 전체 자료 readiness 재평가는 후속 범위다. 이번 변경은 기본 off 내부 Python 옵션이며 공개 사용자 흐름·프론트 계약이 없으므로 UI 변경이 필요 없다. 원본/원장/lock/예약/분할/모델과 58/59 코어는 수정하지 않는다. capture 결과는 기존 5ML 차단 해제 또는 과학·운영 승인으로 쓰지 않는다.


## Root 구문 동등성 및 실제 저장 상태 확인

[변경 전 소스](../../evidence/integration/readiness-connectivity-adapter-readiness-before-20261017.txt)의 SHA는 `42945e3d864a0e63dab4d3100355bcd3506eecf2ada8bc654d573521ea1fdff2`, 현재 실제 파일 bytes SHA는 `90b6b3a82c734c481c1477828c1630061ad495034cd38e950523e3a7a35fb4dc`다. [최소 변경 diff](../../evidence/integration/readiness-connectivity-adapter-source-20261017.diff)와 [AST 대조](../../evidence/integration/readiness-connectivity-adapter-ast-parity-20261017.json)는 추가된 정확 bool keyword/진입 검사와 최종 선택적 진단·반환 부분만 제거하면 원래 assess 및 나머지 모듈의 AST가 완전히 같음을 확인한다. default_policy AST도 불변이다. 이는 정적 구조 근거이며 과학적 성능 검증이나 과거 보고서 생성 코드 인증이 아니다.

[실제 저장 상태 기록](../../evidence/integration/readiness-connectivity-adapter-live-saved-state-20261017.json)과 [로그](../../evidence/integration/readiness-connectivity-adapter-live-saved-state-20261017.log)는 고정 SHA saved readiness에 새 connectivity_diagnostics 필드가 없고 prepared_payload=null, 기존 blocker5·패치628/233/250이 그대로임을 확인한다. 실제 자료로 assess를 재실행하거나 과거 보고서를 다시 생성하지 않았다. 연결 scene 수·0patch scene 실재 여부와 원인 분기는 UNKNOWN_NOT_PERSISTED다. 현재 내부 옵션 연결 구현은 합성 검증 상태이고 실자료 포착은 IMPLEMENTED_UNVERIFIED다.

최종 독립 시험은 **17 PASS / 4.435초**, [독립 로그](../../evidence/integration/readiness-connectivity-adapter-independent-20261017.log)에 별도 graph/BFS oracle 200개 합성 사례 대조도 기록했다. scalar/falsy/공유 namespace·last-owner·strict bbox·0patch 포함·입력 불변과 component 일치를 확인했으며 독립 반복·별도 사례를 전체 unittest 총수에 중복 합산하지 않는다.


해시 기록 정정: 현재 파일은 CRLF 428줄·32867 bytes다. 줄바꿈을 LF로 정규화한 텍스트 SHA `2f70b1f3757186e24a24e3275dc36a6d6592e5c0560291af80eb4441a3b6d366`와 실제 파일 bytes SHA를 구분해 AST 증거를 수정했다. 코드·시험을 변경한 것이 아니며 AST 동등성과 전체 회귀 결과는 유지한다.


## Root 전체 회귀·보존·다음 작업

[전체 회귀](../../evidence/integration/readiness-connectivity-adapter-full-tests-20261017.log)는 **589건/588 PASS/1 SKIP/164.510초/종료0**이다. SKIP은 기존 Windows symlink 생성 권한 조건이며 deterministic 경계 시험은 통과했다. 관련/독립 반복17건과 별도 BFS 200사례는 전체 총수에 중복 합산하지 않는다.

[최종 보존 증거](../../evidence/integration/readiness-connectivity-adapter-live-integrity-20261017.json)는 보호132참조·기존21진단 코어/계약 SHA·저장 readiness SHA 불변, 기존 blocker5 원형 완전 보존, 패치628/233/250 보존을 기록한다. 이전 추적 코드/데이터/계약 중 변경은 의도한 readiness.py 한 파일뿐이다. 실제 raw SHA와 정규화 텍스트 SHA를 구분했으며 원래 gate 본문·나머지 모듈·default_policy AST 불변 근거를 함께 기록했다. 원본/원장/lock/예약136314880B/분할/모델·terminal 없는2건·BLOCKED/모든 승인false/환불0 유지. 실제 자료 assess 재실행이나 과거 보고서 재기록·현재 원본 영상 내용 검사는 없었다.

다음 작은 단위는 기존 `scripts/run_experiment.py`의 기본 off 진단 플래그와 출력 계약을 연결하고 합성 CLI 시험으로 기본동작·실행승인·기존출력/원본 보존을 확인하는 것이다. 진단 요청시 새 출력 경로를 요구해 기존 readiness/입력 파일 덮어쓰기를 방지한다. 실제 자료 검사·영속 envelope 저장·학습 실행은 별도 범위다. 이번 단위는 내부 Python 선택 옵션으로 새 CLI/API/UI 노출이 없으므로 화면 수정·49 UI시험/build·실제 브라우저 재검증 대상은 없다.


## CLI 후속 연결

[61 기본 off CLI 옵션](61_readiness_connectivity_cli_validation.md)을 구현·합성 검증했다. 명시 옵션과 새 출력 경로를 요구하고 기존 파일 덮어쓰기를 보호하며 진단 요약을 추가한다. 기본 off와 학습 승인 체인은 보존했다. 실제 자료 재평가·학습·UI 활성화·envelope 저장 연결은 이 후속에서도 수행하지 않았다.
