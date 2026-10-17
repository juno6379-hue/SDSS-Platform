# 124 — 모델 고정 참조와 실제 checkpoint manifest의 읽기 결합

## 쉬운 설명과 범위

123에서 checkpoint_manifest는 caller가 준 설명이었다. 신규 `backend/app/ml/model_checkpoint_manifest.py`의 `read_pinned_model_checkpoint_manifest(store, model_ref, training_report_sha256)`는 저장 모델의 명시 버전 선언·부모 SHA를 검사하고 실제 `best.pt` 복사 바이트의 SHA와 학습 보고서 SHA를 확인한 다음, **같은 checkpoint 복사 바이트**에서 manifest를 읽는다. 보고서의 input_signature/copied manifest를 실제 checkpoint manifest 대신 사용하지 않는다.

이는 내부 읽기 함수다. Dataset Registry·장면별123 파일 관측·전연차·품질·구름 mask·모델 실행에 아직 연결하지 않는다. Store.get 외의 등록·쓰기·생성·학습·추론·load_state_dict를 수행하지 않는다. 기존 main/API/UI/115 gate·ML 서비스·123 소스를 수정하지 않았다. caller manifest에서 실제 checkpoint manifest 추출로 진전했지만6밴드 per_scene 실행 연계 완료는 아니다.

## 입력과 exact15 결과

model_ref는 exact `{id,version,sha256}`다. id는 기존 등록 namespace의 ASCII `[A-Za-z0-9_-]{1,100}`, version은96의 원형 보존·1..256문자·alias 거부 검사, 두 SHA는 lowercase hex64다. model version을 manifest.version과 비교하지 않는다. manifest.version은 데이터셋 버전일 수 있다.

결과 필드는 다음 exact15다.

| 필드 | 의미 |
|---|---|
| schema_version | 1 |
| scope | PINNED_MODEL_CHECKPOINT_MANIFEST_READ_ONLY |
| status | BLOCKED / MANIFEST_BOUND_UNVERIFIED |
| issue | null 또는 exact {code,field} |
| registration_observation | 100의 관측 또는 null |
| model_ref | 형식 검증된 원형 참조 복사 또는 null |
| training_report_sha256 | 형식 검증된 요청 pin 또는 null |
| checkpoint_manifest | 실제 복사 바이트에서 읽고 검증한 detached JSON dict 또는 null |
| checkpoint_artifact_verified | 해당 checkpoint 복사 바이트 SHA 일치 여부 |
| training_report_artifact_verified | 해당 report 복사 바이트 SHA 일치 여부 |
| state_dict_verified | 항상 false |
| source_authority_verified | 항상 false |
| scientific_accuracy_validated | 항상 false |
| execution_authorized | 항상 false |
| workflow_supported | 항상 false |

두 artifact flags는 해당 역할의 바이트 확인 이력이다. 뒤에서 ZIP/manifest/보고서 의미 검사가 실패해도 앞서 확인한 역할은 true일 수 있으며 전체 성공·checkpoint 실행 가능·승인을 뜻하지 않는다.100의 authority/실파일/실행 false도 그대로 유지한다. manifest 안의 caller가 작성한 execution_authorized 같은 이름의 필드가 true여도 wrapper의 승인 false와 별개다. 반환 manifest는 내부 metadata이며 path 등 caller 내용을 포함할 수 있어 자동 외부 공개 계약으로 삼지 않는다. 오류에는 caller 값·경로·예외 원문을 넣지 않는다.

## 읽기 순서와 참조 결합

1. 요청 형식을 검사한 후 Store.get('models', id)를 한 번 호출한다. 정확한 builtin dict·DB key/본문id를 검사하고100의 CONSISTENT_UNVERIFIED 및 원형 version/부모 checkpoint SHA/부모 training_report SHA가 요청과 일치해야 한다. 명시 버전 선언을 기관 권위로 승격하지 않는다.
2.123의 내부 root/relative/snapshot reader를 재사용해 고정 `models/{id}/best.pt`와 같은 디렉터리 `report.json`만 읽는다. 다른 basename/namespace를 자동 추정하지 않는다. Windows 상대 역슬래시는 비교에만 정규화한다. checkpoint8MiB·report2MiB, 루트·모든 ancestor의 symlink/junction·탈출·UNC·비정규파일·성장/변경을 기존 reader 경계로 거부한다.
3.복사 checkpoint SHA와 요청 pin을 비교하고, 복사 report SHA와 요청 pin을 비교한다. strict JSON report의 training_state=completed/model_id/checkpoint_sha256을 확인한다. report에 model_version이 있으면 원형 요청 version과 정확히 같아야 한다. report의 input_signature 또는 다른 copied manifest를 fallback으로 사용하지 않는다.
4.동일 checkpoint 바이트의 BytesIO로 ZIP 정책을 확인한 뒤 `torch.load(BytesIO, map_location='cpu', weights_only=True)`를 한 번 호출한다. False fallback·사용자 함수 allowlist 추가·load_state_dict·forward·추론은 없다.
5.읽은 최상위 checkpoint는 builtin dict·tiny_unet architecture여야 하며 그 manifest를 아래 JSON 범위로 detached 복사해 반환한다. 이 architecture 문자열은 호환성 검증·실제 TinyUNet state 증명이 아니다.

고정 오류 code는 INVALID_INPUT / MODEL_NOT_FOUND / MODEL_RECORD_INVALID / REGISTRATION_NOT_BOUND / PIN_CONFLICT / CHECKPOINT_PATH_INVALID / SHA256_MISMATCH / TRAINING_REPORT_INVALID / CHECKPOINT_ARCHIVE_INVALID / CHECKPOINT_LOAD_UNAVAILABLE / CHECKPOINT_FORMAT_INVALID / MANIFEST_INVALID / READ_UNAVAILABLE이며, 재사용 reader의 ROOT_UNAVAILABLE / PATH_INVALID / FILE_UNAVAILABLE / FILE_LIMIT / FILE_CHANGED도 유지한다. field는 고정 계약 역할 이름이다. 이 함수는 HTTP 상태나 API를 추가하지 않는다.

## ZIP·manifest·loader 한도

checkpoint는 Torch 기본 ZIP_STORED archive만 지원한다. 최대512항목·전체 uncompressed32MiB·항목8MiB·data.pkl2MiB이며 전체 checkpoint 파일8MiB가 먼저 적용된다. encrypted/compressed/legacy non-ZIP·중복 이름·traversal·역슬래시/colon·디렉터리 entry·여러 archive root·data.pkl 부재를 거부한다. Python zipfile이 이해하는 기본 Torch ZIP64 header 구조는 허용하되 위 실제 크기 한도를 늘리지 않는다. ZIP64라서 대형 파일을 허용하는 것은 아니다.

manifest는 builtin JSON dict/list/str/int/float/bool/null만 허용한다. dict당128키·정확 str키1..128자·키 제어문자/고립 surrogate 거부, 값 문자열4096자·고립 surrogate 거부, 깊이16·node65536·int53비트·float finite·detached JSON 약2MiB 한도다. 복사 중 누적 byte budget도 제한하여 공유 값 반복의 복사 증폭을 줄인다. 순환·tensor·tuple·custom type/key를 거부한다. JSON 값 문자열의 escaped control은 JSON 표현으로 허용되며122 같은 후속 의미 검사의 제한과 다르다. manifest{}와 state_dict 누락/잘못된 shape도 실제 manifest 읽기 범위에서는 성공할 수 있고 state_dict_verified는 false다.

**설치 Torch 및 호출 환경의 ambient allowlist를 상속한다.** 이 helper는 safe_globals를 add/clear/replace하지 않으며 빈 baseline을 추정하거나 강제하지 않는다. 처음 제안한 empty guard는 현재 Torch2.14.0+cpu 자체 기본 등록도 막아 정상 파일이 항상 차단되는 것으로 시험에서 확인하여, 공개 전 신규 helper의 guard를 제거했다. 기존 실행 API/런타임 허용목록 정책을 바꾸지 않았다. unsupported custom pickle은 고정 오류로 막고 weights_only=False 재시도하지 않는다.

weights_only와 ZIP 한도는 악의적인 tensor metadata의 CPU/RSS/시간 DoS 또는 모든 pickle 위험을 완전히 격리하는 sandbox가 아니다. ZIP parser의 entry 목록 구성도 사전 raw8MiB 안에서 먼저 일어날 수 있다. 전역 allowlist는 다른 thread가 변경할 수 있고 검사/추정만으로 격리할 수 없다. 별도 process나 hard resource limit를 이번 단위에 추가하지 않았다. 신뢰할 수 있는 내부 로컬 작업에만 쓰며 외부 공개 시 clean process 등 별도 실행 격리 설계가 필요하다. mapped drive 매체의 물리적 로컬성도 증명하지 않는다. source_url HTTP 조회·네트워크 라이브러리 호출은 없다.

## 시험과 증거

담당 최종 집중 **14 PASS / 5.810초 / exit0**: `evidence/integration/model-manifest-read-agent-focused-final-20261018.log`. 초기13건/5실패는 `model-manifest-read-agent-focused-20261018.log`에 보존했다. 실패 원인은 설치 Torch 자체의 기본 등록이 비어 있지 않은데 guard가 empty를 강제한 것이며, 승인된 신규 helper 수정 후 정상 actual manifest 읽기를 확인했다.

TempStore와 **실제 CPU TinyUNet6을 초기화해 저장한 checkpoint**를 사용했다. 훈련·forward·추론을 하지 않았다. 같은 해시 BytesIO/정확 loader kwargs·no load_state_dict·unsupported pickle/no fallback·allowlist add/clear0 및 전후 동일·각 SHA/보고서 재바인딩·ZIP 암호화/압축/중복/legacy/traversal·한도·invalid JSON manifest·cycle/custom/byte budget·명시 버전 원형·dataset 버전 구분·Draft/synthetic 읽기와 승인 false·state 부재/잘못된 state 한계를 시험했다. 파일·Store.put 불변도 확인했다.

source SHA `c62cb01364cc60ab481c16a8b31dfa4d57085f435b1442cb6001ec37325f591d`, test SHA `d8f80667e51196643ac43c824d5f40e24fd3a15b00821ec4acfeb4aee5582727`로 Root/독립 담당에게 동결 인계했다. Root는 관련/runtime/보존 근거, 독립 담당은 별도 실제 checkpoint/경계 fixture 검증을 맡는다. 같은 로그명을 중복 사용하지 않도록 담당 집중에는 agent suffix를 사용했다.

이전120의 전체 backend1184/front261은 이번에 재실행한 근거가 아니다. 미연결 내부 읽기 단위로 UI/API/frontend/build/browser 변경·재실행은 하지 않는다. 운영 모델 파일 load·등록·데이터 쓰기·수집·훈련·추론·배포0이다. Dataset Registry/연차/품질/mask/기관 승인·기존115 실행 연계는 별도 후속이며 global-only gate는 그대로다. Root가 완료 소스·시험·한계를 이해 에이전트에 인계해 설명·대본·FAQ·INDEX·변경이력을 갱신한다.

## 최종 독립·관련·실파일 대비·보존 근거

독립 **8 PASS / 0 SKIP / 1.9214184초 / exit0**는 `evidence/integration/model-manifest-read-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 실제 Torch2.14.0+cpu의 ambient safe_globals73개가 조회 전후 같고 add/clear하지 않음을 확인했다. unsupported load는1회 실패 후 고정 차단하며 weights_only=False 재시도가 없다. ZIP 정책 위반은 load 전에 거부했다. 실제 TempTinyUNet6 copied BytesIO·CPU weights_only·실제 manifest와 보고서 복사 구분·padding/Unicode 버전·bounded JSON/분리 복사·state 호환 미검증과5개 승인 false를 독립 fixture로 확인했다. 동결 helper SHA 및 Git816515e의 기존 핵심8 source SHA·tracked source 불변이며 제품 지적0이다. CPU/RSS/시간 및 ambient 격리 보장으로 해석하지 않는다.

Root 관련 **40 PASS / 7.241초 / exit0**는 `evidence/integration/model-manifest-read-root-related-20261018.log`다. 신규14·100 provenance12·123 reader14를 포함하며 집중·독립과 중복 합산하지 않는다.

Root runtime 대비 **6 PASS**는 `evidence/integration/model-manifest-read-runtime-20261018.py`와 같은 stem `.json`·`.log`다. 학습하지 않은 실제 CPU6밴드 checkpoint의 manifest를 보고서 decoy와 구분하고,123의 임시 GeoTIFF 자료와 수동으로 조합해 경계를 확인했다. 이것은 helper를 실제 Workflow/Registry/서비스에 자동 연결한 runtime이 아니다. detached 결과·checkpoint/report 바이트 변조·원형 padding version도 확인했다. 운영 checkpoint load·학습·추론·Store 쓰기는0이다.

`evidence/integration/model-manifest-read-live-integrity-20261018.json`은 보호141개·기존source281개·이전증거1035개·catalog14행 SHA·예약136314880바이트 불변을 기록한다. source/test 최종 동결 SHA를 유지했고 문서에 최종 근거를 반영해 동결했다. Dataset Registry 고정 참조와 장면 metadata,123의 자동 연계·전연차·품질/mask 결합은125 이후 별도 후속이며 이번에 완료했다고 표현하지 않는다.
