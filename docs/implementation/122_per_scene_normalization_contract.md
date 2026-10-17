# 122 — per_scene 정규화 선언의 순수 호환성 관측

후속123은 [세 역할 실제 파일 SHA reader](123_per_scene_normalization_files.md)를 별도 추가했다.122 pure helper의5개 false와 동작은 바꾸지 않았다.123만 읽은 바이트/선언 일치에 제한해 artifact_bytes_verified=true를 제공하며 Registry·checkpoint 신원·권위·실행 검증을 부여하지 않는다.

## 쉬운 설명

6밴드 모델과 추론 장면의 정규화 설명이 서로 맞는지, 파일을 열거나 모델을 실행하지 않고 비교한다. `DECLARATIONS_CONSISTENT_UNVERIFIED`는 제공된 설명의 형식과 값이 맞는다는 뜻이다. 영상·보정 근거·원 metadata의 실제 SHA 확인, 기관 권위, 실행 승인 또는 과학 정확도를 뜻하지 않는다.

신규 `backend/app/ml/per_scene_normalization_contract.py`의 `inspect_per_scene_normalization_contract(checkpoint_manifest, source_scene, normalization, evidence)`만 추가했다. 기존 Workflow·서비스·API·UI·Registry·모델을 바꾸거나 helper를 연결하지 않았다. 이 단위 완료 후에도115 Workflow는 global만 실행하며 per_scene은 계속 차단한다.

## 기존 동작과 연결 공백

| 기존 위치 | 확인한 계약 |
|---|---|
| `backend/app/lcluc_workflow.py:132` | normalization_mode 기본global, global 이외는 NORMALIZATION_MODE_UNSUPPORTED |
| 같은 파일141~142 | checkpoint manifest의 global scale/offset 검사 |
| 같은 파일148~174 | Registry·연도·품질 SHA·밴드/header 검사 후 image 항목에 year/image_path/source/license만 투영 |
| `backend/app/ml/service.py:276` | per_scene 추론이면 장면 normalization 필요 |
| 같은 파일281~284 | nonsynthetic per_scene이면 실제 normalization verifier 호출 후 영상에 scale/offset 적용 |
| 같은 파일416~419 | 직접 timeseries 서비스는 장면 normalization/source_scene/quality_mask를 추론기로 전달 가능 |
| `backend/app/ml/normalization.py:23` | 실제 영상 SHA·제품ID·밴드, evidence SHA·보정값, 원 metadata SHA·출처 진술 검사 |
| `backend/app/ml/readiness.py:11` | 6밴드 순서 B02/B03/B04/B08/B11/B12 |
| 같은 파일195~216 | 제품 보정 근거·원 metadata·품질 마스크 gate |
| 같은 파일353 | per_scene_product_metadata 입력 서명 |

기존 `channel_values`는 NumPy 형변환을 하므로 bool/numeric string도 일부 수용한다. 새 helper는 이를 바꾸는 후행 gate가 아니라 **별도 신규 strict 진단 범위**다. 기존 서비스의 scalar/vector 변환·실파일 확인을 대체하지 않는다. per_scene에서는 장면별 계수가 서로 달라도 정상이며 checkpoint manifest의 global scale/offset과 같아야 한다고 검사하지 않는다. 실제로 helper는 그 두 필드를 읽지 않는다.

## 입력과 관측 순서

네 입력은 정확한 builtin dict다. 전체 checkpoint/evidence의 추가 키는 허용하되 dict당 최대128키·정확한 builtin str 키만 허용한다. 미지 추가 값은 순회·복제·직렬화하지 않아 순환 값도 무관하다. 이128키 한도는 기존 전체 시스템 schema의 변경이 아닌 신규 진단의 명시 범위다.

manifest의 mode가 없거나 `global` 또는 다른 정상 지원외 문자열이면 `OUT_OF_SCOPE`와 issue null을 반환하며 나머지 입력은 읽지 않는다. 기존 global1..16밴드 지원을6밴드로 좁히지 않는다. 명시 null·잘못된 타입·빈/제어문자 mode는 INVALID다. mode 원문을 trim/보정하거나 새 기본 per_scene mode를 추정하지 않는다.

mode가 정확히 `per_scene_product_metadata`이면 다음 순서로 필수 필드 형식을 검사한다.

| 입력 | 필수 필드 |
|---|---|
| checkpoint_manifest | bands, band_names |
| source_scene | scene_id, image_sha256, band_names |
| normalization | scale, offset, evidence_path, evidence_sha256 |
| evidence | status, product_id, band_names, scale, offset, source_url, source_metadata_path, source_metadata_sha256 |

bands는 정확한 builtin int6개, band_names는 문자열6개다. 계수는 정확한 builtin int/float scalar 또는 builtin list6개만 받으며 bool·numeric string·tuple·NaN/Inf를 거부한다. int는53비트 이하로 제한해 거대한 정수의 float 변환과 정밀도 손실을 숨기지 않는다. scale은 양수, offset은 유한한 부호 있는 값이다. scalar는 비교할 때만6성분으로 확장한다. 예를 들어 scale1과[1.0]*6은 수치 동등하다. 입력을 수정하거나 정규화된 결과물을 생성하지 않는다.

문자열은 공백뿐인 값·제어문자·고립 surrogate를 거부하고 원형을 보존한다. scene/product/status/mode는128자, band name64자, 두 path512자, source_url2048자 상한이다. path와 URL은 **opaque 선언 문자열**이다. 경로 해석·탈출 검사·접속·공식 URL/기관 인증을 수행하지 않는다. 따라서 `../...`나 caller 출처 문구가 형식상 통과해도 실제 경로/출처 검증 성공을 뜻하지 않는다. output에는 원문 path/URL/metadata를 노출하지 않는다.

필수 형식 검사를 모두 끝낸 뒤 다음 선언을 순서대로 비교한다: manifest bands=[1..6], manifest names=위6밴드 순서, source names=manifest names, evidence.status=`verified_product_metadata`, product_id=scene_id, evidence names=manifest names, normalization scale/offset=evidence scale/offset. 문자열은 원형 exact 비교하고 숫자는 scalar 확장 후 성분별 수치 동등을 비교한다. scene별 계수를 checkpoint global계수와 비교하지 않는다.

image/evidence/source_metadata의 SHA는 각 역할의 lowercase hex64 **형식만** 검사한다. 서로 다른 파일 역할의 SHA끼리 같은지 비교하지 않는다. 이 함수에는 실제 파일에서 관측한 same-role SHA 인수가 없으므로 image 선언↔영상 바이트, evidence 선언↔evidence 바이트, 원metadata 선언↔원metadata 바이트의 pin 비교도 수행할 수 없다. caller가 해시 문자열을 제공했다는 사실을 실파일 확인으로 승격하지 않는다.

## exact9 출력과 오류 우선순위

반환 필드는 `schema_version:1`, `scope:'PER_SCENE_NORMALIZATION_DECLARATIONS_ONLY'`, `status`, `issue` 및 아래5개 false다.

- execution_authorized
- artifact_bytes_verified
- source_authority_verified
- scientific_accuracy_validated
- workflow_supported

status는 OUT_OF_SCOPE / INCOMPLETE / INVALID / DECLARATION_MISMATCH / DECLARATIONS_CONSISTENT_UNVERIFIED다. issue는 null 또는 exact `{code,field}`이고 code는 MISSING_FIELD / INVALID_FIELD / INPUT_LIMIT / FIELD_MISMATCH다. field는 고정된 계약 필드 이름만 반환하며 caller 값을 담지 않는다.

우선순위는 manifest mapping/mode→manifest 필수 형식→source 형식→normalization 형식→evidence 형식→선언 값 비교다. 없는 키는 INCOMPLETE, 명시 null/잘못된 형식은 INVALID, 형식은 맞고 서로 다른 값은 DECLARATION_MISMATCH다. 입력을 자동 채우거나 보정하지 않는다.

## 시험과 한계

`tests/test_per_scene_normalization_contract.py`의 합성 선언 시험 **14 PASS / 0.031초 / exit0**, 로그 `evidence/integration/per-scene-contract-focused-20261018.log`다. scalar/vector 동등·제품별 계수·세 SHA 역할 분리·missing/null/불일치 우선순위·6밴드 순서·numeric string/bool·NaN/Inf/거대정수·한도·제어문자·Unicode·opaque path·원형 불변·추가 순환 값 미순회·custom key callback 방지·open 금지를 검사했다. import는 math/re만 있고 NumPy·Torch·service를 import하지 않는 AST 검사를 포함한다.

소스 SHA는 `b2f1f79c5b9773d9588d4e9b560f9df12ed94d2c1e5301b638cc9c432090f8ea`, 시험 SHA는 `14ed1420561d3b73c6317af48beb9cc71fb851f0d13abe7c435543b8ba94310d`로 Root/독립 검토자에게 동결 인계했다. 기존 실행 경계 회귀·독립 검증·보존 근거는 Root가 별도로 기록하며 최신 전체 backend1184건의120 이력과 이번 신규 시험을 혼동하거나 합산하지 않는다.

품질 마스크·spectral 의미·실제품 수치 단위·float32 변환 후 유한성/정밀도·6밴드 모델의 독립성·제품 metadata 기관 권위·연도별 evidence 실제 파일·Registry 연결·실제 checkpoint를 검사하지 않는다. synthetic/Deployed/독립 평가 gate도 이 함수 범위가 아니며 기존115가 계속 담당한다. 실파일 bounded reader·Registry pinned descriptor·장면별 evidence/source_scene/mask의 명시 전달과 실행 전 재검증은 별도 후속 설계가 필요하다. 이번 단위는6밴드 실행 연계 완료가 아니다.

UI에 연결하지 않은 내부 순수 함수이므로 API·frontend build·browser 재실행은 필요하지 않으며 현재 global-only 안내를 유지한다. 운영 자료 쓰기·모델 조회/변경·checkpoint 로드·수집·다운로드·훈련·추론·배포0이다. Root가 본 문서와 검증 근거를 이해 에이전트에 인계하여 쉬운 설명·발표·FAQ·INDEX·변경 이력을 갱신한다.

## 최종 독립·기존 경계·보존 증거

독립 검토는 **7 PASS / unittest0.014초 / byte 감사 포함 전체1.030초 / exit0**다. `evidence/integration/per-scene-contract-independent-20261018.py`와 같은 stem의 `.json`·`.log`에 고정했다. 동결 helper SHA 일치, Git9a79c3d의 핵심 기존8개 source SHA 동일, 기존 tracked backend/frontend/scripts/tests 변화0을 확인했다. global1..16 구분·strict 숫자/한도·형식과 값 불일치·scalar/vector6채널 의미 동등·opaque path·불변/no-I/O·exact9/5false를 별도 fixture로 시험했다. 기존 경계 회귀는 `evidence/integration/per-scene-contract-existing-boundaries-20261018.log`의 **4 PASS / 8.994초**다.

Root의 `evidence/integration/per-scene-contract-runtime-boundary-20261018.py` 및 같은 stem `.json`·`.log`는 **6 PASS**다. 임시6밴드 raster·보정 evidence·원 XML metadata를 생성해 baseline에서 pure 선언 관측은 consistent, 기존 실제 파일 verifier는 통과함을 확인했다. 이후 영상/evidence/XML 각 파일의 바이트 변조와 잘못된 유효 형식 SHA에서 pure는 형식만 검사하므로 consistent가 유지될 수 있지만 기존 file verifier는 거부했다. 제품 선언 불일치는 양쪽 모두 거부했다. 이 대비는 신규 helper의 무I/O 한계를 실험한 것이며 helper가 실파일 검증을 대신한다는 근거가 아니다. 훈련·추론·checkpoint 로드·운영 자료 접촉은0이다.

`evidence/integration/per-scene-contract-live-integrity-20261018.json`은 보호141·기존source277개 전체·이전증거1006개 전체 불변과 catalog14행 동일 SHA·예약136314880바이트 유지를 기록한다. 이전120의 전체 backend1184건/front261건은 이번에 재실행하지 않았다. 기존 source 전부 불변인 미연결 순수 추가이므로 신규 집중·독립·기존/실파일 경계 시험 범위로 검증했고, UI/API 변경·frontend 전체·build·browser 재실행은 하지 않았다. 이 묶음들은 중복 합산하지 않는다. 최종 증거를 반영하고 문서를 동결했다.
