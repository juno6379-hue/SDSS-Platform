# 138 — 미등록 품질 보고서·마스크 선언 묶음의 순수 준비

상태: **TESTED_SYNTHETIC**. 신규 `prepare_quality_mask_bundle(image_manifest, mask_manifest, report_identity)`는 caller가 명시한 두 전체 manifest 선언과 새 보고서 identity로131이 소비하는 보고서 JSON bytes·SHA·고정 참조와 미등록 draft/patch를 준비한다. 신규 `backend/app/data/quality_mask_bundle.py`, 집중 시험, 본 문서만 추가한다. 기존 schema·Registry·131/133 reader·collector·실행 gate·API/UI는 수정하지 않는다. 파일을 읽거나 쓰고 등록하는 함수가 아니다.

## 입력과 선언 subset

image_manifest와 mask_manifest는 caller가 명시한 전체 dict다. builtin JSON만 깊은 사본으로 만들며 depth16·node8192·dict128키·list1024항목·key128자·string4096자·canonical 크기 budget256 KiB를 제한한다. dict/list subclass·custom object·cycle·lone surrogate·비유한 float·절댓값2^53−1 초과 int를 거부한다. dict 키의 제어문자도 거부한다. 모든 결과 mutable 객체는 원본 입력과 분리된다.

상위 required/optional key, schema_version0.2.0, 두 자료의 raster 유형, 고정 id/version/SHA, source의 institution/product/license 명시 문자열, 유한 bbox/CRS·순서·WGS84 범위, aware start/end·순서와 calendar 문자열, lineage ref/선택 role·URI, 선택 units/resolution/limitations/quality_report_ref의 형식을 검사한다. id/version은96번 순수 계약을 재사용해1~256자·빈값/제어문자/별칭 latest/current를 거부하고 유효한 패딩 문자열은 보존한다.

이 검사는 **새 내부 bounded 선언 subset**이며 전체 upstream JSON Schema validator를 실행한 것이 아니다. 날짜는 ASCII 대문자T/Z·명시 offset·소수초 최대6자리의 제한된 aware 형식이다. calendar 문자열·source URI의 실제 의미/출처를 인증하지 않는다. 기존 `canonical_manifest()`는 cold cache에서 schema 파일을 읽으므로 순수 준비 함수에서 호출하지 않는다. 독립/Temp consumer 시험에서만 전체 schema와 별도 대조한다. subset 수용과 upstream 전체 수용의 동등성을 주장하지 않는다.

두 입력의 quality_status는 caller가 명시한 **RAW 또는 STAGED만** 수용한다. STANDARDIZED/VALIDATED/REJECTED를 자동으로 만들거나 승격하지 않는다. access_class는 원선언의 PUBLIC/RESTRICTED/CONFIDENTIAL을 유지한다. 준비 성공이 PUBLIC/ACL 통과를 뜻하지 않으며 실제131 소비는 별도로 PUBLIC을 요구한다.

mask.source.mask_semantics는 정확한4키 `{schema_version:1,kind:'binary_validity',valid_value:1,invalid_value:0}`여야 한다. 숫자는 정확한 int이며 bool을 거부한다. 마스크 값·dtype/nodata/header·정답 의미를 보거나 추측하지 않는다. image의 source.band_names 등 기존 확장 선언도 자동 보완하지 않는다.

## 보고서 identity·경로·충돌

report_identity는 정확한3키 `{id,version,artifact_uri}`다. 세 ref의 id/version 쌍이 서로 달라야 한다. artifact 경로에는123의 상대 경로 **문법만 순수 문자열로** 적용한다. 최대512자, 역슬래시→슬래시 정규화 비교, 절대/drive/UNC/URI/빈 segment/`.`/`..`/segment128자 초과/말미 공백·점을 거부한다. Path.resolve/stat/open·실제 root·symlink/junction·파일 존재를 검사하지 않는다. 따라서 문법 통과를 안전한 쓰기 경로 인증으로 확대하지 않는다.

보고서 artifact는 정규화 후 image/mask 두 artifact 경로와 달라야 한다. 이후 caller가 보고서를 저장하면서 원영상/마스크를 덮는 위험을 줄이는 새 준비 정책이다. image의 기존 quality_report_ref가 있으면 같은 정규화 경로여야 하며 다르면 충돌로 거부한다. mask의 optional quality_report_ref도 선언 타입과 상대 문법을 검사하지만 새 보고서로 자동 바꾸지 않는다. image/mask 서로의 경로 alias는 이 단계에서 허용하며 물리적으로 다른 파일·6밴드 영상/1밴드 mask·의미 정합은 후속132/133의 별도 범위다.

유효 artifact_uri와 version의 caller 원형은 출력에 보존한다. 비교를 위한 슬래시 정규화가 원본 입력 자체를 수정하지 않는다. 입력 draft가 이미 Registry에 같은 id/version으로 등록됐는지 조회하지 않는다. quality_report_ref를 추가하면 image manifest 내용이 바뀌므로 이미 등록한 버전에 그대로 덮어쓰려 하면 기존 immutable 등록 정책이 거부할 수 있다. caller는 필요하면 **새 id/version을 명시한 미등록 draft**를 준비해야 하며 함수가 버전을 추정/증가시키지 않는다.

## 생성하는 bytes와 미완성 report patch

보고서 envelope는131의 정확한5키 `schema_version:1,scope:'LCLUC_QUALITY_MASK_EVIDENCE',image_ref,mask_ref,quality_status`다. quality_status는 image의 RAW/STAGED 선언 원형이다. canonical JSON은 Python `sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')`의 strict UTF-8 bytes이고 그 bytes의 SHA256을 새 report ref로 만든다. 파일 바이트를 읽어 확인한 SHA가 아니다. 입력 선언의 finite float와 -0.0은 사본에서 보존하며 임의 보정·float32 변환·영점 정규화를 하지 않는다. 보고서 envelope 자체에는 float 필드가 없고 선언 참조와 문자열·정수만 들어간다.

report_identity 세 필드만으로 report의 기관·제품·license·공간·기간·품질/접근 metadata를 발명할 수 없으므로 **완전 report manifest를 생성하지 않는다.** report_manifest_patch는 정확한7키 schema_version0.2.0, dataset_id, version, data_type=document, sha256, artifact_uri, lineage만 가진다. lineage는 quality_input_image와 quality_input_mask의 명시 ref 두 개다.

report_metadata_required는 source/spatial/temporal/quality_status/access_class의5개 필드를 명시한다. 이 metadata는 caller가 별도로 실제 근거에 따라 제공해야 한다. image의 기관/제품/license/공간/기간을 report 본체의 사실로 자동 복사하지 않는다. patch 단독은 upstream 전체 manifest 검증에 실패하는 것이 정상이며 준비 결과를 등록 완료·등록 가능 인증으로 표현하지 않는다.

image_manifest_draft는 caller 사본에 명시 report artifact를 quality_report_ref로 결합하고, mask_manifest_draft는 검증한 caller 사본이다. report bytes를 실제로 exclusive 저장하고 완전 report metadata를 결합해 등록할지 결정하는 작업은 caller/후속의 책임이다. 이 함수는 그 쓰기·덮어쓰기·등록을 실행하지 않는다.

## exact22 결과와 false 경계

결과는 schema_version:1, scope:`UNREGISTERED_QUALITY_MASK_BUNDLE_PREPARATION_ONLY`, status, issue, image_manifest_draft, mask_manifest_draft, report_manifest_patch, report_metadata_required, report_envelope, report_bytes, report_sha256, fixed_refs와 다음10개 false다.

- artifact_bytes_verified / registry_references_verified / registry_registered
- quality_report_verified / quality_mask_verified / source_authority_verified
- scientific_accuracy_validated / execution_authorized / state_dict_verified / workflow_supported

status는 BLOCKED 또는 **REPORT_METADATA_REQUIRED_UNREGISTERED**다. 성공해도 필요한 report metadata가 남고 미등록·미검증이다. fixed_refs는 image_ref/quality_report_ref/mask_ref의 exact3 pinned refs다. report_bytes만 Python bytes이며 나머지는 bounded JSON-compatible 값이다. caller가 bytes를 별도 저장해야 하므로 결과 전체를 그대로 JSON serialize하지 않는다.

실패 issue는 안전한 고정 `{code,field}`만 반환하고 raw path·caller 값·예외 원문을 노출하지 않는다. 코드에는 INVALID_MANIFEST, QUALITY_STATUS_UNSUPPORTED, MASK_SEMANTICS_INVALID, REPORT_IDENTITY_INVALID, REFERENCE_CONFLICT, PATH_INVALID, QUALITY_REPORT_REF_CONFLICT가 있다. 실패 시 draft/patch/envelope/bytes/ref는 null이고 필요한 metadata 목록과 false flags만 남는다.

## 집중 시험과 동결

담당 집중 **9 PASS / 1.103초 / exit 0**는 `evidence/integration/quality-mask-bundle-agent-20261018.log`다. exact22·envelope5·patch7·metadata5·bytes/SHA·패딩 version 원형·10false, no open/stat/resolve/Store/cold schema·입력 사본, RAW/STAGED·접근 선언 미승격, 명시 semantics, 참조/경로/기존 report 충돌, normalized path와 image/mask alias의 미검증 범위, cycle/NaN/Inf/unsafe int/surrogate/depth/string/custom type을 검증했다. 독립 읽기 지적의 mask optional quality_report_ref도 양 manifest 공통 검사에 반영하고 부정 회귀를 포함했다. Affine PendingDeprecationWarning은 Temp fixture 생성 로그에 보존했다.

Temp 통합 시험에서는 **시험 caller가 따로 명시한** report source/spatial/temporal/quality/access에 patch를 병합하고, bytes를 Temp에 저장한 뒤 세 버전을 등록했다. 그 후131/133 reader가 소비하는지 확인했다. 준비 함수 자체는 Store·파일을 건드리지 않는다. 보고서 metadata를 별도로 만든 합성 소비 시험은 기관 QA나 실제 운영 자료/등록 근거가 아니다.

source SHA `72750fe9f1299a878a589e66ac1e0d53b01eddfc3af6237915e6e16bce623945`, test SHA `1bfa06a5a21346af4c8d30390c6deaaf4690138eced2e6e99eccf46c5c70ffa6`로 Root/독립 담당에게 동결했다. 기존 제품 파일·원본·원장·예약·모델·분할을 수정하지 않았다. Root는 관련/실파일 대비·보존·공통 인계/Git과 이해 에이전트 작업 배정을 맡고, 이해 담당은 완료 코드·시험·미등록/미확인 경계를 해설/발표/FAQ/INDEX/변경 이력에 반영한다.138은 준비 함수뿐이며 API/UI/frontend/build/browser 및 전체 backend의 신규 재실행을 요구하지 않는다.137의 전체 시험은 이전 근거다.

## Root 관련 시험과 보존

Root 관련4모듈 **39 PASS / 9.865초 / exit 0**는 `evidence/integration/quality-mask-bundle-root-related-20261018.log`다. 집중·독립과 중복 합산하지 않는다. `quality-mask-bundle-live-integrity-final-20261018.json`은 보호141개·기존 source314개·이전 증거1275개·catalog14행과 SHA·예약136314880바이트 보존을 기록한다. 기존 source314개는 변경0이다.

새 준비 함수는 UI/API/실행기에 연결되지 않았고 기존 사용자 흐름을 바꾸지 않으므로 이번 전체 backend/frontend/build/browser를 다시 실행하지 않았다.137의 전체1358 PASS/기존1 SKIP은 이전 근거로 유지하며138의 결과로 표현하지 않는다. 보고 예약 ACTIVE는 실제 수집/학습 실행과 구분하고 원본·원장·운영 모델·분할·예약을 보존한다. 부분 준비 성공이 collector의 nodata0·라벨/AOI 결합·명시 밴드 미확보 문제나 운영 준비 상태를 해결한 것은 아니다.

## 독립 최종 근거와 문서 동결

독립 **7 PASS / 0 SKIP / 1.4408525초 / exit 0**는 `evidence/integration/quality-mask-bundle-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 실제 fresh Temp6밴드 GTiff·checkerboard mask·SQLite 세 등록 참조를 만들고 caller가 명시한 report metadata에 patch를 결합했다.131/133의 실제 소비에서 get6회·valid128/invalid128/total256을 확인하고 read-only SQL·DB/전체 파일 불변을 검증했다. 세 등록은 시험 setup이며 준비 함수의 Registry/파일 조작은0이었다.

nodata0·value255·RESTRICTED의 세 반례는 준비에는 성공하지만 실제 소비에서 각각 intrinsic validity·binary 값·access 선언 차단으로 실패했다. 따라서 준비 성공을 header/값/ACL·품질·모델 실행 준비로 확대하지 않는다. 성공/실패의 I/O denial guards·입력 불변·Unicode/path/alias·잘못된 optional quality ref와10false도 검증했다. 최종 source/test SHA와 Git f01752a의 기존 핵심9개 source SHA가 일치하며 추가 제품 지적은 없다.

초기 독립7 PASS/1.1218초는 `quality-mask-bundle-independent-initial-20261018.json`·`.log`에 별도 보존하고 최종과 합산하지 않는다. 이번에는 HTTP/main/137 request-response·모델 metadata·운영 Registry를 갱신하지 않았다. 실제 report 저장·등록·collector mask nodata 전환·영상 description 보완·품질/기관 승인·전체 연차 확보는 완료하지 않았고 별도 후속이다. 최종 집중·관련·독립·보존 근거와 제한을 반영한 뒤 본 문서를 동결했다.

## 별도 상태 문서 검토

별도 갱신된 docs16/20은05:52 관측 시각과 정체 기간만 바뀌었음을 quality-mask-bundle-separate-status-docs-20261018.json으로 검산했다. 누계·manifest/원장 SHA는 그대로이며138의 수집 재개 성과로 표현하지 않는다.
