# 64. capture의 선택적 원본 식별 단서 전달 계약

## 쉬운 설명과 상태

readiness assess가 이미 메모리에 가진 image_path/image_sha256를 선택적 진단 단서로 전달한다. 새 파일을 읽거나 hash하지 않고, 다음 lineage 소비자가 후보를 좁힐 때 사용할 수 있는 **선언 metadata 계약**만 추가했다. 이번에는63 lineage의 후보 소비 로직을 바꾸지 않는다.

구현과 합성 시험은 `TESTED_SYNTHETIC`이다. 실제 자료 assess를 재실행하지 않았고 기존 실제 보고서를 덮어쓰거나 새 필드를 소급 추가하지 않았다. 식별 단서가 있어도 source authenticity/exact 원본 row binding/ready/scientific flags는 false다. 기존 gate·정책·분할·scene 순서·0patch·witness는 바꾸지 않는다.

## 하위호환 구조

생산코드 변경은 `backend/app/ml/readiness_connectivity_adapter.py` 한 파일이다. 기존 assess의 detached-copy 입력에는 이미 image_path/image_sha256가 있으므로 assess를 수정할 필요가 없다.

- 기존 capture schema_version=1 유지.
- projected_scene_metadata의 정확한5키 및58 helper 입력 불변.
- scene_mapping의 기존 구조 불변.
- helper가 완료되어 component 비교를 끝낸 capture에 **최상위 optional source_identity** 병렬 객체만 추가.
- unsupported policy/metadata/budget 등 기존 조기 미포착 결과에는 이 객체가 없을 수 있다.

63 reader는 이 optional capture 필드를 소비하지 않는다. 새 객체가 있는 경우와 과거처럼 없는 경우에 기존 literal 후보/AMBIGUOUS 결과가 같음을 합성 시험했다. 과거 실제 pinned report는 source_identity가 없는 원형 그대로이며 별도 historical 증거다. 이 변경이 과거 report 생성 시점·실행코드 신원을 인증하지 않는다.

## identity schema version1

```json
{
  "identity_schema_version": 1,
  "identity_capture_status": "DECLARED_METADATA_CAPTURED",
  "identity_claim": "ALREADY_COMPUTED_ASSESS_METADATA_NOT_FILE_AUTHENTICATION",
  "coverage_status": "COMPLETE_DECLARED_METADATA",
  "scene_count": 1,
  "complete_declared_scene_count": 1,
  "unknown_not_provided_scene_count": 0,
  "partial_or_invalid_scene_count": 0,
  "scene_identities": [
    {
      "scene_index": 0,
      "eligible_position": 0,
      "identity_status": "DECLARED_PATH_AND_SHA256",
      "image_path_declared": "relative/image.tif",
      "image_path_status": "DECLARED_NOT_FILE_VERIFIED",
      "image_sha256_declared": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "image_sha256_status": "DECLARED_NOT_FILE_VERIFIED"
    }
  ],
  "path_normalized_or_resolved": false,
  "source_files_read_or_hashed": false,
  "source_authenticity_verified": false,
  "exact_original_row_binding_verified": false,
  "ready_for_training": false,
  "scientific_accuracy_validated": false
}
```

scene_index/eligible_position는 assess 내부 appended scenes의 순서이며 원본 manifest row 번호가 아니다. eligible_patches가0인 scene도 같은 위치에 포함한다. 입력 scene을 변경하지 않고 문자열 scalar만 복사한다. 새 helper/파일/경로 확인·네트워크 호출은 없다.

## 값·상태와 한도

image_path는 원형 str을 보존한다. relative/absolute/URL처럼 보이는 문자열을 실제 경로로 파싱·정규화·resolve하지 않는다. 경로가 어디에 있는지 또는 파일이 존재하는지는 확인하지 않는다. 허용된 literal path가 실제 원본을 지칭한다는 인증도 아니다.

| path 상태 | 의미 |
|---|---|
| ABSENT | image_path key 자체가 없음 |
| NULL_DECLARATION | 명시 null |
| INVALID_TYPE | 정확한 str 타입이 아님 |
| TOO_LONG |4096 code point 초과 |
| EMPTY_DECLARATION | 빈 문자열 또는 공백만 있음 |
| INVALID_CONTROL_CHARACTER | NUL/C0/DEL 제어문자 포함 |
| INVALID_UNICODE | unpaired surrogate 등 strict UTF8 직렬화 불가 |
| DECLARED_NOT_FILE_VERIFIED | bounded UTF8 literal 선언이며 파일 미검증 |

길이를 whitespace/control/UTF8 검사보다 먼저 확인해 무제한 문자열을 선스캔하지 않는다. invalid 값은 출력 value를 null로 두고 상태만 기록한다. Path 객체·list/bool 등도 str로 바꾸지 않으며 임의 객체 메서드를 호출하지 않는다.

image_sha256는 이미 계산된 메타데이터를 전달한다. 정확한 str·길이64·lowercase hex만 DECLARED_NOT_FILE_VERIFIED로 복사한다. key 없음/명시 null/비str는 각각 ABSENT/NULL_DECLARATION/INVALID_TYPE, 길이가 다르면 INVALID_LENGTH, uppercase/비hex는 INVALID_SHA256_FORMAT이다. 자동 lowercase·hash 재계산은 하지 않는다.

각 scene의 identity_status는 다음과 같다.

- 두 key 모두 absent: UNKNOWN_NOT_PROVIDED. legacy 부재를 invalid 선언으로 바꾸지 않는다.
- path/hash 모두 형식상 허용: DECLARED_PATH_AND_SHA256.
- 한 key absent: PARTIAL_DECLARATION. 다른 key가 null/invalid여도 알려진 부분 선언 상태다.
- 그 외 명시 null/invalid 조합: INVALID_DECLARATION.

전체 coverage는 빈 scene 목록이면 NO_SCENES, 전부 완전한 선언이면 COMPLETE_DECLARED_METADATA, 전부 legacy 부재면 UNKNOWN_NOT_PROVIDED, 나머지는 PARTIAL_OR_INVALID_DECLARED_METADATA다. complete/unknown/partial counts는 해당 내부 scene 목록을 기준으로 합계가 맞는다. 이 'complete'는 단서 필드의 선언 완전성이며 출처·학습 적격성 완전성은 아니다.

기존 adapter의 최대2000 scenes·전수 pair budget을 통과한 목록만 이 단계에 도달한다. 경로4096·SHA64의 scalar 한도는 유지하지만 전체 report가 항상 특정 byte cap 안이라는 보장은 아니다. 각 consumer의 기존 report byte cap은 그대로 적용한다.

## 실패 격리

identity의 missing/invalid 값은 기존 capture_status·witness·gate 결과를 바꾸지 않는다. identity 객체 생성 자체에서 예상 밖 예외가 발생해도 별도 try 경계에서 아래 최소 객체로 격리한다.

```text
identity_schema_version=1
identity_capture_status=NOT_CAPTURED_ERROR
error_type=<예외 클래스>
scene_count=<기존 appended 수>
scene_identities=null
source_files_read_or_hashed=false
source_authenticity_verified=false
exact_original_row_binding_verified=false
ready_for_training=false
scientific_accuracy_validated=false
```

소비자는 optional 객체 부재 또는 identity_capture_status를 먼저 확인해야 한다. 미포착·invalid를 정상 단서 또는 exact binding으로 승격하지 않는다. 기존 outer gate가 weak-label ready일 수 있다는 사실과 이 diagnostic의 false 승인 flags를 구별한다.

## 시험 증거

관련 `tests/test_readiness_connectivity_adapter.py`: **23 PASS / 6.047초**(기존17+새6), 로그 `evidence/integration/readiness-source-identity-related-20261017.log`. 원래17개 on/off 판정동등성 시험도 함께 실행했다. 독립/전체 회귀는 같은 시험을 중복 합산하지 않는다.

새6개 시험은 이미 assess가 계산한 image path/hash와 전달값 일치·outer gate 불변, 양key absent/partial/null/type/long/hashformat, NUL/제어문자/unpaired surrogate safe UTF8 JSON, literal path/no resolve/stat/open/hash·0patch/순서·입력 deep equality, identity 생성 예외에도 기존 capture/witness 일치, 기존63 reader의 optional 객체·legacy 부재 결과 동일성을 확인했다. 실제 source·기존 pinned report를 재평가하지 않고 합성 fixture만 사용했다.

초기23 PASS6.197초는 path whitespace 검사보다 len 검사를 앞으로 옮기기 전 이력이다. 최종 관련 결과는6.047초다. 새 optional 단서의 실제 사용·원본 후보 축소는 아직 PLANNED 소비 범위이며 실제 row 인증이나 과거 원인 복구로 발표하지 않는다.

## UI와 다음 단위

공개 CLI/API/UI 플래그나 화면 계약은 바꾸지 않은 내부 metadata 확장이라 UI 변경은 필요 없다. 기존 실제 보고서·원장·lock·예약·모델·분할은 보존한다. Root가 adapter 코드 SHA 변화·기타 계약 보존·전체 회귀 및 운영 문서/이해자료를 관리한다.

후속 단위에서63 reader가 version1 단서의 명시 path/hash와 원본 manifest의 선언을 읽기 대조해 후보 집합을 좁힐 수 있다. 그때도 singleton 후보는 declaration의 유일 일치일 뿐 source file 진실·픽셀/과학적 독립·학습/정산/자동재개 승인이 아니다. 이번 단위는 소비 로직·원본 행 삭제·0patch 필터·차단 해소를 구현하지 않는다.


## Root 최종 회귀·보존과 인계

- 전체 `scripts/test.ps1`: **630건/629 PASS/1 SKIP/192.060초/종료0**, `evidence/integration/readiness-source-identity-full-tests-20261017.log`. 기존 Windows OS symlink 권한 SKIP이며 deterministic 경계 시험은 PASS다.
- 독립 관련23 PASS/5.827초. 관련23 PASS/6.047초와 독립 재실행은 전체630건에 중복 합산하지 않는다.
- `evidence/integration/readiness-source-identity-live-integrity-20261017.json`: 보호133참조와 adapter 외 기존24계약 SHA 불변. 추적된 코드/데이터/시험의 변경은 adapter 및 관련 시험 두 파일뿐이다. readiness.assess 및 CLI는 수정하지 않았다.
- 고정 manifest·실제 report SHA, 기존5차단·패치628/233/250 불변. 기존 실제 report에 source_identity를 소급 추가하지 않았고 실제 assess 재실행/새 실제 report 생성은 없다. 이전28장면 원본 후보는 여전히 모호하다.
- 새 공개 API/UI 계약이 없는 내부 선언 metadata 확장이므로 이번 화면 변경 대상은 없다. 원본·원장·lock·예약136314880B·분할·모델을 보존하고 수집/학습/배포를 실행하지 않았다.
- 다음은63 reader의 선택적 identity version1 검증 및 선언 경로·해시 대조 소비 계약이다(PLANNED). 실제 파일 접근 없이 단서의 유일 일치와 파일 인증을 구분하고, legacy 부재·unknown version·invalid·중복·truncation을 합성 시험한다. 현재 실제 자료 모호성이 해소됐다고 발표하지 않는다.


소비 구현은 [65 선택적 식별 단서 소비](65_readiness_source_identity_consumer.md)를 참조한다. 선언 대조는 합성 검증됐으며 기존 실제 report에는 단서가 없어 실제 모호성은 유지된다.
