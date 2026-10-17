# 139 — 명시한 보고서 metadata와 검산한 품질 patch의 순수 결합

상태: **TESTED_SYNTHETIC**. 신규 `complete_quality_report(image_manifest, mask_manifest, report_identity, report_metadata)`는138의 미완성 report patch에 caller가 따로 명시한 source/spatial/temporal/quality/access를 결합해 완전한 **미등록 manifest draft**를 만든다. 신규 `backend/app/data/quality_report_completion.py`, 집중 시험, 본 문서만 추가한다. 기존138·reader·Registry·collector·실행 gate·API/UI를 수정하지 않는다. 파일 저장·등록·품질/기관 승인 단계는 아니다.

## caller 입력과 빈틈 없는 사본 경계

image/mask full manifest와 report_identity는138의 동일한 pure bounded 선언 subset으로 검사한다. report_metadata는 정확한5키 source, spatial, temporal, quality_status, access_class를 caller가 명시해야 한다. 누락·추가 키·patch identity와의 충돌을 추정/역채우기로 처리하지 않는다. image의 기관·제품·license·공간·기간을 report metadata로 자동 복사하지 않는다.

모든 입력을 먼저 strict builtin bounded JSON 사본으로 만든다.138과 같은 depth16/node8192/dict128/list1024/string4096/key128/canonical budget256 KiB, unsafe int/비유한 float/surrogate/cycle/custom type 거부를 사용한다. 유효하지 않은 사전 입력/metadata는138을 호출하지 않는다. 유효한 입력 경로는138을 **정확히 한 번** 호출하고 producer에 전달하는 인자도 검산용 사본과 분리한다. producer가 인자를 바꾸더라도 원본이나 검산 기준이 함께 변하지 않는다.

metadata의 source는 institution/product/license 명시 문자열과 선택 source_uri를 검사한다. 공간 선언은 bbox4/유한 수치·양의 범위·CRS 문법·WGS84 범위와 선택 geometry_uri를, 기간은 start/end/calendar·aware 날짜와 순서를 검사한다. 날짜 형식은138과 같은 ASCII 대문자T/Z·명시 offset·소수초 최대6자리의 새 내부 subset이다. calendar·source URI의 실제 의미/출처를 인증하지 않는다. 기존 `canonical_manifest()`의 cold schema 파일 읽기를 호출하지 않고, 문서 metadata를 raster인 척 바꿔 validator를 재사용하지도 않는다. 전체 upstream schema 검증과 등록 가능성은 별도 consumer 시험에서 대조한다.

report quality_status는 caller의 **RAW 또는 STAGED**만 수용하고 access_class는 PUBLIC/RESTRICTED/CONFIDENTIAL 원문을 보존한다. report 단계는 image/envelope quality와 다를 수 있다. 둘의 quality 동일 조건이나 PUBLIC<RESTRICTED<CONFIDENTIAL rank 정책을 새로 만들지 않는다. 공식 기관 QA/ACL/declassification 정책은 미확정이고 준비 함수가 판정하지 않는다. image RESTRICTED/report PUBLIC 선언도 준비될 수 있지만 image access 자체는 그대로이고 실제131 reader는 RESTRICTED를 차단한다. 이를 자료 공개·접근 승인으로 확대하지 않는다.

## mutable/untrusted138 결과의 재결합 검산

138을 두 번 호출해 같은 구현의 결과를 비교하지 않는다. 입력 사본에서 image/mask ref·semantics·report path·충돌·exact5 envelope·canonical bytes/SHA·patch7·metadata_required5·fixed refs를 독립 재구성한다.138이 반환한 exact22 전체를 이 bounded trusted expected shape와 **타입까지 엄격히** 비교한다.

schema int1·성공 status·null issue·10개의 정확한 False, 원형 identity/version/path, image quality_report_ref, mask semantics, 두 lineage 역할의 순서·pin, bytes 길이/내용과 SHA, patch와 required metadata 목록을 검사한다.0은False가 아니고1은True가 아니며 str/dict subclass·custom equality를 호출하지 않는다. 실제 parent가 큰 미지 tree나 cycle을 넣어도 expected shape의 길이/키/type 경계에서 거부한다. finite float의 canonical 표현도 비교해 -0.0을0.0으로 조용히 바꾸지 않는다.

parent가 BLOCKED·private issue·추가 키·잘못된 flag/bytes/SHA/ref/patch/소스 추정·부정 semantics를 반환하거나 예외를 내면 PREPARATION_OUTPUT_INVALID/bundle로 닫는다. raw parent/exception/path를 반사하지 않는다. 모든 payload는 최종 성공 이후에만 채우므로 오염된 부모의 부분 성공을 새 결과로 누출하지 않는다.

## 완전 draft와 그대로 이어지는 report bytes

검증된 patch의7키와 caller metadata의5키가 겹치지 않는지 확인해12키 report_manifest_draft를 만든다. report schema_version은0.2.0, type은document, dataset_id/version/artifact_uri·SHA·두 lineage는 검증한 report identity와138 bytes에서 온다. source/spatial/temporal/report quality/access는 caller metadata에서만 온다.

report_bytes는138의 검산을 통과한 내용과 정확히 같은 **독립 expected 사본의 bytes**를 이어준다. 검산 뒤 mutable producer dict를 다시 읽지 않으므로 그 사이 parent가 값을 바꿔도 검산한 내용이 유지된다. 객체 identity의 동일성이 아니라 byte 내용의 동일성을 보장하는 계약이다. metadata 보완 때문에 exact5 보고서 body나 SHA를 새 내용으로 바꾸지 않는다. source의 finite float와 -0.0을 보존하고 float32 변환·보정·정규화를 하지 않는다. report body는 image quality 선언을 유지하며 report manifest 자체의 quality stage와 별개다. bytes는 JSON-compatible 응답 값이 아니므로 caller가 후속 저장을 선택해야 한다. 준비 함수가 저장·등록하거나 기존 id/version을 덮어쓰지 않는다.

## exact21 결과와 미등록 상태

반환은 schema_version:1, scope:`UNREGISTERED_EXPLICIT_QUALITY_REPORT_COMPLETION_ONLY`, status, issue, image_manifest_draft, mask_manifest_draft, report_manifest_draft, report_envelope, report_bytes, report_sha256, fixed_refs와138의10개 false다.

- artifact_bytes_verified / registry_references_verified / registry_registered
- quality_report_verified / quality_mask_verified / source_authority_verified
- scientific_accuracy_validated / execution_authorized / state_dict_verified / workflow_supported

성공 status는 **UNREGISTERED_REPORT_MANIFEST_PREPARED**다.138의 부족한 metadata가 명시적으로 채워졌지만 아직 미등록·파일 미확인이다. image/mask draft도 detached 사본이며 원 선언을 바꾸지 않는다. 실패는 BLOCKED이고 issue는 안전한 `{code,field}`만 가진다. 입력 subset 오류 code 외에 REPORT_METADATA_INVALID, REPORT_INPUT_INVALID, PREPARATION_OUTPUT_INVALID를 사용한다. 실패 시 모든 draft/envelope/bytes/SHA/ref는 null이고10false는 유지한다.

완전 draft는 input/policy 선언 조합이지 실제 파일·header·mask 값·보고서 지표·실제 QA 의미·기관 권위·ACL·학습/추론 가능성 검증이 아니다. 부분 준비를 실제 report 저장/등록·collector nodata0 전환·description 보완·운영 연차 확보로 표현하지 않는다.

## 집중 시험과 동결 인계

담당 최종 집중 **9 PASS / 1.234초 / exit 0**는 `evidence/integration/quality-report-completion-agent-final-20261018.log`다. exact21/full12·caller metadata 원형·보고서 bytes/SHA 동일·10false, metadata exact5/충돌/누락/날짜/RAW-STAGED,138 호출1회·bad metadata0회, exact22/flag/byte/SHA/ref/patch/role/path 오염·불완전 부모의 고정 안전 결과, producer 인자 변경·custom equality callback0, no open/stat/resolve/Store/cold schema, deep detach·negative zero·cycle/NaN/Inf/unsafe int/surrogate/custom type을 확인했다. image RESTRICTED/report PUBLIC·image RAW/report STAGED의 선언 보존도 시험했다.

Root 읽기 검토에서 검산 뒤 mutable producer의 report_bytes를 다시 읽는 한 항을 찾아 독립 expected bytes로 고쳤다. `_same`가 top-level 비교 성공을 반환한 직후 producer bytes를 POISON으로 바꾸는 명시 mock 회귀가 추가됐다. 최초8 PASS/0.705초 로그 `quality-report-completion-agent-20261018.log`는 보완 전 결과로 보존하고 최종과 합산하지 않는다. 기존138 및 다른 제품 소스는 변경하지 않았다.

별도 Temp 통합에서는 caller가 명시한 metadata의 완전 report draft를 upstream canonical validator로 검사하고 실제 Temp에 report bytes를 저장한 뒤 세 버전을 등록했다.131/133 실제 소비는 성공했고 mask 값 관측과 과학/품질 false를 유지했다. 이 파일/등록 쓰기는 시험 setup이며 순수 completion 함수의 쓰기가 아니다. Affine PendingDeprecationWarning은 fixture 생성 로그에 남겼다.

최종 source SHA `d98c9d52e8add04b5a620d78d4e988e633477f761003ae646f6dc99906efab39`, test SHA `86f3f04a7778bd688ccb922e9dc59108dee6340d9ffbce0fa97b1894b51be07d`로 Root/독립 담당에게 재동결했다. 기존 소스·원본·원장·예약·모델·분할은 수정하지 않았다. Root는 관련 회귀·보존·공통 인계/Git과 이해 에이전트 배정을 담당한다. 이해 담당은 완료 코드·시험·미등록/기관 미승인 범위를 해설/발표/FAQ/INDEX/변경 이력에 반영한다.139는 내부 순수 준비 함수로 HTTP/main/UI·운영 Registry와 연결하지 않았으므로 frontend/build/browser·전체 backend를 신규 재실행하지 않는다.137의 전체 시험은 이전 이력이다.

## 보완 전 독립 근거

보완 전 독립 **7 PASS / 0 SKIP / 0.9096376초 / exit 0**는 `evidence/integration/quality-report-completion-independent-initial-20261018.py`와 같은 stem `.json`·`.log`에 보존했다. 실제 fresh Temp report의 upstream schema 검산·SQLite 세 버전 setup 후131/133 read-only 소비에서128/128/256 계수와 DB/전체 파일 불변을 확인했다. report STAGED/image RAW/envelope RAW는 각각 caller 선언을 유지했다. image RESTRICTED/report PUBLIC은 준비되지만 실제 소비는 BLOCKED였으며 nodata0·255도 준비 성공이 소비 성공을 뜻하지 않는 반례였다.

untrusted138 출력의 typed 오염16종·custom equality callback0·인자 사본 변경 방어·실패 payload null·성공/실패 I/O guard0·metadata 사전 차단을 검증했다. 이는 재동결 전 source의 근거이며 mutable parent bytes 보완 후의 독립 결과와 합산하지 않는다. Git200d22c의 기존11개 source SHA는 그대로다. 이 helper는 HTTP/main/137 계약·UI·운영 Registry 등록과 연결하지 않았으므로 frontend/build/browser를 다시 실행할 필요가 없고 과거 결과를 이번 시험으로 표현하지 않는다.

## 재동결 후 독립 최종 근거

최종 독립 **8 PASS / 0 SKIP / 2.0615961초 / exit 0**는 `evidence/integration/quality-report-completion-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 위 실제 Temp 완전 metadata·schema·131/133 소비·128/128/256·read-only6get·DB/파일 불변·접근/품질/값 반례와 typed 오염 경계를 최종 source로 다시 확인했다.

추가 회귀는 최종 소스의 지정한 한 표현만 과거 producer bytes 재읽기로 되돌린 **격리 모듈**을 만들고, 그 원문 SHA가 최초 `0ef9c2930df1224eeb1f130b80b0dd15d799776d734cf713805abb08e05240e9`와 정확히 같은지 검증했다. 명시 mock이 검산 직후 parent bytes를 바꾸면 이전 버전은 bytes/SHA가 불일치하고 수정본은 expected snapshot bytes/SHA가 일치했다. 이는 합성 callback 경계 재현이며 운영 동시성/전체 원자성 시험이 아니다. 제품 소스를 되돌리거나 기존138 파일을 수정하지 않았다.

최종 source/test SHA가 재동결값과 같고 기존11개 source는 불변이며 추가 지적은 없다. 보완 전 독립7건과 최종8건을 합산하지 않는다. 실제 report 저장/등록·collector mask 전환·기관/품질/모델 실행 승인은 여전히 별도 후속이다.

## Root 관련 회귀·보존과 마감

Root 최종 관련 **48 PASS / 12.067초 / exit 0**는 `evidence/integration/quality-report-completion-root-related-final2-20261018.log`다. expected bytes 보완 전 관련47건의 `quality-report-completion-root-related-20261018.log`와 구분해 보존한다. 초기 집중8·관련47·독립7과 최종 집중9·관련48·독립8을 중복 합산하지 않는다.

`evidence/integration/quality-report-completion-live-integrity-final-20261018.json`은 보호141개·기존 source316개·이전 증거1291개·catalog14행 SHA·예약136314880바이트 불변을 기록한다. 기존 제품 source 변경은0이며 운영 원본·원장·모델·분할·예약을 보존했다. 순수 새 함수의 집중·관련·독립·Temp 소비 검증으로 마감하며 전체 backend/frontend/build/browser를 이번에 다시 실행한 것으로 표현하지 않는다. 이해 담당에게 완료 코드·실제 시험·미등록/미승인 및 합성 재현의 한계를 전달했다. 최종 근거 반영 후 본 문서를 동결했다.

## 후속140 새 경로 저장

[140 저장 계약](140_quality_report_storage.md)은 호출자 명시 두 새 경로에 report와 canonical manifest를 EXCL 생성한다.139 선언/bytes는 유지하며 기존 파일은 동일 내용도 거부한다. 부분 생성은 보존하고 등록·QA/ACL·승인·실행을 자동으로 수행하지 않는다.
