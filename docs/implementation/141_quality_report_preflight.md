# 141 — 저장된 품질 보고서의 등록 전 읽기 점검

상태: **TESTED_SYNTHETIC**. `inspect_stored_quality_report(data_root, image_manifest, mask_manifest, report_identity, report_metadata, manifest_output_uri)`는 140이 저장한 보고서와 manifest sidecar 두 파일을 읽어, 호출자가 명시한 선언에서 재구성한 바이트·SHA·고정 참조 및 전체 report manifest schema와 대조한다. 성공은 **STORED_REPORT_FILES_VERIFIED_UNREGISTERED**이며 등록·기관 품질 승인·실행 승인이 아니다. 신규 source, 집중 시험, 이 문서만 추가하며 기존 140 이하 소스는 수정하지 않는다.

## 입력과 검산 기준

입력은 140과 동일하다. `data_root`는 절대 기존 디렉터리의 정확한 builtin str 또는 concrete Path이고, custom `__fspath__`를 호출하지 않는다. 네 선언 입력은 139의 bounded builtin 사본과 명시 metadata 계약을 따른다. 보고서의 source/spatial/temporal/RAW 또는 STAGED/access를 이미지에서 추정하거나 자동 복사하지 않는다. manifest 경로도 호출자가 명시한다.

139의 준비 결과를 무조건 신뢰하지 않는다. 별도 고정 입력 사본에서 expected21을 재구성하고, 다른 인자 사본으로 `complete_quality_report`를 한 번 호출해 전체 typed shape·flags·draft·바이트·SHA·refs를 대조한다. 이후에는 가변 반환값을 다시 읽지 않고 고정 expected 사본만 사용한다. 부모 반환의 오염이나 예외는 고정 오류와 빈 결과로 닫는다.

## 두 파일의 읽기 경계

140의 순수 경로 검사와 root/부모 검사를 재사용한다. 상대 경로만 허용하고 절대/drive/UNC/URI, ADS, `..`/`.`/빈 segment, 말미 점·공백, Windows 금지 문자·예약 장치명과 Unicode C*를 거부한다. 역슬래시를 정규화하고 NFC+casefold 충돌 검사를 유지한다. 두 파일은 같은 기존 부모에 있어야 하며 영상·마스크 artifact와 충돌할 수 없다. sidecar는 입력의 quality_report_ref와도 충돌할 수 없다. image의 quality_report_ref와 실제 보고서 경로가 같은 정상 선언은 허용한다. 이번에는 파일이 이미 있어야 하며, 선존재를 거부하는 writer는 호출하지 않는다.

root 및 모든 조상과 파일 부모의 일반 디렉터리 여부, symlink/reparse/junction 속성, resolve 일치와 dev/ino identity를 검사한다. 두 파일은 일반 파일이어야 한다. 각 파일을 `O_RDONLY`와 플랫폼이 제공하는 `O_BINARY`/`O_NOFOLLOW`로 연다. lstat/fstat의 identity·크기·mtime/ctime을 대조하고, 누적 읽기 바이트가 **각 2 MiB**를 넘으면 즉시 중단한다. SHA는 그 동일 복사 바이트에서 계산한다. 파일을 생성하거나 수정하고, 부모를 만들고, 삭제·재시도·복구를 추정하는 동작은 없다.

순서는 report → manifest다. 각 파일의 복사 바이트는 expected report bytes 또는 expected manifest의 strict sorted UTF-8 canonical JSON과 **바이트 단위로 정확히 같아야 한다**. 의미상 같은 JSON이어도 공백·키 순서·표현이 다르면 거부한다. 관측한 untrusted JSON을 따로 파싱해 선언을 대체하지 않는다. 파일 읽기 실패나 변조는 FILE_UNAVAILABLE / FILE_INVALID / FILE_LIMIT / FILE_CHANGED / FILE_BYTES_MISMATCH 등 고정 code와 역할만 반환한다. 원문 예외나 절대 root 경로를 노출하지 않는다.

## 전체 manifest schema 확인

저장 바이트가 일치한 뒤 `dataset_registry.canonical_manifest`에 **expected report manifest의 별도 사본**을 한 번 전달한다. 이 단계는 139의 제한된 순수 선언 검사를 넘어 기존 GMAIS manifest schema·고정 버전·공간/시간 조건을 검산한다. cold cache에서는 저장소의 `dataset-manifest.schema.json`을 로컬에서 읽는다. 따라서 자료 파일 두 개의 읽기와 별도로 **신뢰하는 로컬 schema 파일 읽기**가 있을 수 있다. schema loader·cache와 설치된 FormatChecker의 동작은 기존 구현을 따르며, 이 기능이 별도 완전한 RFC3339 parser를 추가하는 것은 아니다.

schema 함수의 반환도 무조건 신뢰하지 않는다. 정확한 tuple 두 항목, expected manifest와 typed 동등한 dict, expected canonical SHA와 일치하는 정확한 str digest를 요구한다. 잘못된 schema 결과는 MANIFEST_SCHEMA_OUTPUT_INVALID, schema 검증 예외는 MANIFEST_SCHEMA_INVALID로 닫는다. 최종 응답에는 schema 함수의 가변 dict 대신 고정 expected manifest 사본만 넣는다.

두 번째 파일과 schema를 확인한 뒤 **첫 번째 파일을 포함한 두 경로 모두**의 최종 stat 및 부모 identity를 다시 확인한다. 첫 report를 읽은 뒤 sidecar를 읽는 동안 report가 바뀐 경우도 전체 성공으로 반환하지 않는다. 이 검사는 동시 원자 snapshot이 아니며 마지막 stat 이후의 변경까지 막지 못한다. 등록을 실제 수행할 다음 단계가 있다면 그 경계에서 다시 확인해야 한다.

## exact23 결과와 실패 정책

필드는 다음 13개와 기존 10개 false다: schema_version, scope, status, issue, report_output_uri, manifest_output_uri, report_sha256, manifest_sha256, fixed_refs, report_manifest_draft, files, stored_report_files_verified, manifest_schema_verified.

scope는 `READONLY_STORED_QUALITY_REPORT_PREFLIGHT_ONLY`다. 성공 때만 두 검증 flag가 true이고, 상대 output URI·고정 SHA·refs·report draft를 반환한다. files는 report/manifest 순서의 exact3 `{role, verified, bytes}` 두 개다. 성공은 두 항목 모두 verified=true이고 읽은 바이트 수를 갖는다. 실패는 status=BLOCKED, 고정 `{code,field}` issue를 가지며 **새 null payload와 두 verified=false/bytes=null 항목**으로 닫는다. 먼저 읽은 파일이 맞았더라도 부분 draft/SHA/refs나 부분 성공 flag를 반환하지 않는다. 실패의 false는 읽기가 없었다는 뜻이 아니다.

다음 값은 성공해도 모두 false다.

- artifact_bytes_verified, registry_references_verified, registry_registered
- quality_report_verified, quality_mask_verified, source_authority_verified
- scientific_accuracy_validated, execution_authorized, state_dict_verified, workflow_supported

stored_report_files_verified는 보고서·sidecar의 복사 바이트만 뜻한다. manifest_schema_verified는 해당 schema의 선언 수용과 canonical digest 일치다. 둘 다 영상/마스크 실파일·헤더·픽셀, 품질 의미·최소 유효율 정책, ACL·기관 권위, 모델·학습·실행·등록 완료를 검증하지 않는다. report stage와 image stage가 다르거나 report access가 입력보다 덜 제한적인 선언이더라도 새로운 등급 정책을 발명하지 않는다. 실제 소비자의 기존 PUBLIC 및 품질/마스크 gate는 그대로다.

## 시험과 현재 한계

최종 집중은 **11 PASS / 2.265초 / exit 0**, `evidence/integration/quality-report-preflight-agent-20261018.log`다. 실제 Temp 140 저장 파일에서 exact23/SHA·두 readonly open·139 한 번·원본 입력/파일 불변, 누락/일부 바이트/변조/비canonical JSON·크기 초과·성장 읽기 차단, sidecar를 읽는 동안 첫 파일 변경과 fd 읽기 중 변경 차단을 확인했다. 경로 충돌과 예약 문자, 명시 reparse/부모 identity mock, 오염된 completion 및 schema 결과, 검산 직후 가변 반환값 변경을 시험했다. Store.put/connect와 writer 호출을 금지하고 영상/마스크를 열지 않는 경계를 확인했다. cold schema 읽기 1회도 별도로 관측했다.

초기 집중은 11개 중 10 PASS / 1 FAIL / 3.514초로 `quality-report-preflight-agent-initial-20261018.log`에 보존했다. `+00:60` offset을 기존 FormatChecker가 거부할 것이라는 시험 기대가 이 설치에서 성립하지 않았다. 제품 소스 결함으로 기록하지 않으며 기존 parser를 수정하지 않았다. 최종 schema 실패 시험은 real canonical_manifest에 명시적으로 더 엄격한 임시 Draft202012Validator를 주입한 **모의 schema 정책 실패**다. 저장소 schema를 바꾸거나 실제 기존 schema가 해당 날짜를 거부했다고 주장하지 않는다. 초기와 최종 시험을 합산하지 않는다.

시험 setup의 Temp 파일 생성과 제품의 읽기 전용 동작을 구분한다. 제품은 Store 생성/접속/등록, 원본 영상/마스크 읽기, Torch/GDAL, HTTP fetch를 호출하지 않는다. 파일 root가 mapped drive일 때 실제 매체가 로컬이라는 인증은 아니며, 부모 동시 치환·FIFO 교체/open blocking 등 모든 TOCTOU를 OS sandbox처럼 막는 기능도 아니다. 두 파일의 순차 읽기와 stat는 원자성·CPU/RSS/시간 SLA·기관 권한을 보장하지 않는다. schema cache와 저장소 schema는 신뢰하는 내부 실행 환경의 일부다.

source SHA `04758b1ac3e03fb392790e2c0c7d87aa261a9563b160d704cbf06023af09e62a`, test SHA `3b4dbf91d37a183cfa282c86a122d0755eae1ae615383a7eb0a303eee91a9a41`로 Root와 독립 담당에게 동결했다. Root는 관련 시험·원본 보존·공통 인계/Git·이해 담당 배정을 맡는다. 이해 담당은 완료 코드와 시험 근거를 읽고 해설·발표 대본·FAQ·INDEX·변경 이력을 갱신한다.

Root의 관련 7개 모듈은 **69 PASS / 13.656초 / exit 0**, `quality-report-preflight-root-related-20261018.log`다. `quality-report-preflight-live-integrity-final-20261018.json` 보존 감사에서 보호 파일 141개·기존 소스 320개·이전 증거 1331개, catalog 14행과 canonical SHA, 예약 136314880바이트가 유지됐다. 운영 dataset_versions는 0이며 수집·학습·등록·배포·Workflow dispatch도 0이다. 이전 전체 시험이나 중복 집중 시험과 합산하지 않는다.

독립 최종 `quality-report-preflight-independent-20261018.py/.json/.log`는 **13 실행 / 12 PASS / 1 SKIP / 실패·오류 0 / 3.166969초 / exit 0**다. source/test SHA가 동결 값과 일치하며 c216534 기준의 기존 10개 소스도 바뀌지 않았다. 실제 Temp 140 저장 → 141 읽기 전용/schema 점검 → 별도 Registry fixture 3건 등록 → 131/133 읽기 전용 소비에서 128/128/256 계수와 DB/파일 불변을 확인했다. 이 등록은 독립 시험 setup이며 제품 141의 동작이 아니다. 잘못된 저장 바이트/재포맷/크기 초과의 payload 초기화, 139/schema 검산 직후 가변 결과 변경, 첫 파일을 두 번째 읽기 중 바꾸는 명시 fault, 임시 부모 치환과 reparse fault를 구분해 검증했다. 실제 symlink 생성은 Windows 권한 오류 1314로 한 건 제외했으며 mock 경계 통과를 실제 링크 시험의 통과로 표현하지 않는다.

독립 초기 13 실행 / 11 PASS / 1 FAIL / 1 SKIP / 8.9813945초는 임시 부모 치환 fault가 호출한 mkdir를 제품의 무생성 guard가 함께 막은 시험 구성 문제였다. 초기 py/json/log 세 파일을 `-initial`로 보존하고, fault 자체의 직접 os.mkdir만 분리해 독립 시험을 정정했다. 제품 소스는 바꾸지 않았고 초기·최종 수치를 합산하지 않는다. 설치된 FormatChecker가 `+09:60`을 통과시키는 한계와 명시 stricter schema fixture의 실패도 각각 관측했으며, 기존 schema가 해당 timestamp를 거부한다고 주장하지 않는다.

새 내부 읽기 함수는 HTTP/main/137 계약·UI/Registry 자동 등록에 연결하지 않았다. 이번 frontend/build/browser 및 전체 backend 재실행은 범위에 포함하지 않는다. 이전 전체 시험은 이전 이력이고 이번 집중·관련·독립 점검과 합산하지 않는다. 운영 root를 시험하지 않았으며 원본·원장·lock·분할·모델·예약을 보존한다. 실제 등록·collector 보완·전체 연차 확보·품질 및 모델 승인은 후속이며, 등록 전 읽기 성공을 전체 개발 완료로 확대하지 않는다.

다음 142 후보는 호출자가 명시적으로 요청하는 등록 어댑터와 Temp Registry 검증이다. 이번 141에는 등록 어댑터나 운영 자동 등록이 없으며, 후속 단계에서도 기관 승인·원본 접근 정책과 등록 의도를 별도로 구분해야 한다.

## 후속142 명시적 보고서 등록

[142 등록 어댑터](142_quality_report_registration.md)는 기존 source2버전과141 저장 보고서를 확인한 뒤 caller 지정 Store에 report만 등록한다. 실제 쓰기는 명시 호출 범위이며 결과 미확정 시 DB/파일을 보존한다.141 자체의 읽기 전용 계약은 그대로이고 기관 품질·모델·실행 승인은 별도다.
