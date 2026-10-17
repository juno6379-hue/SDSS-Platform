# 140 — 두 새 품질 보고서 파일의 배타적 저장

상태: **TESTED_SYNTHETIC**. 신규 `write_quality_report_files(data_root, image_manifest, mask_manifest, report_identity, report_metadata, manifest_output_uri)`는139의 미등록 완전 draft를 검산한 뒤 **새 report 파일과 새 manifest sidecar 두 개만** 생성한다. 신규 `backend/app/data/quality_report_storage.py`, 집중 시험, 본 문서만 추가한다. 기존138/139·Registry·collector·API/UI·실행 gate와 원본 자료를 수정하지 않는다. 실제 제품 동작을 시험한 자료는 Temp fixture뿐이며 운영 root에 실행하지 않았다.

## 명시 입력과139 출력 사본

data_root는 명시한 절대 기존 디렉터리이며 정확한 str 또는 concrete Path만 받는다. custom `__fspath__`를 호출하지 않는다. 다른 네 입력은139의 명시 계약이고 manifest_output_uri는 root 상대의 새 sidecar 경로다. report 경로는 report_identity.artifact_uri로 고정한다. 기본 경로·기관·제품·QA·버전을 추정하지 않는다.

입력과 report metadata를 bounded builtin 사본으로 만들고139를 정확히 한 번 호출한다. 사본에서 독립 재구성한 expected21과 typed shape/flags/drafts/bytes/SHA/refs/lineage를 검산한다. 실제 파일에 쓸 bytes와 manifest는 **검증 기준의 detached expected 사본**에서만 가져오며 mutable139 dict를 검산 후 재조회하지 않는다. 잘못된 completion 출력은 파일 접근 전에 COMPLETION_OUTPUT_INVALID로 차단한다.139의 source/spatial/temporal subset·RAW/STAGED·접근 선언·기관/QA 미승인 한계는 유지한다.

report bytes는139의 고정 내용 그대로이고 sidecar는 완전 report manifest의 strict sorted UTF-8 canonical JSON이다. 각각 최대2 MiB를 제한하고 SHA256을 계산한다. 이 bytes 준비는 전체 upstream schema·파일 실존·품질/ACL 검증을 대신하지 않는다.

## 원본·이전 보고서를 덮지 않는 경로 정책

상대 경로는 123/138의 문법을 바탕으로 절대/drive/UNC/URI·ADS colon·`..`/`.`·빈 segment·말미 공백/점·segment 128자 초과를 거부한다. 추가로 Windows 금지 문자 `< > " | ? *`, 모든 Unicode C* category, Windows 예약 장치명 CON/PRN/AUX/NUL/COM/LPT 및 보수적 예약 별칭을 차단한다. 이는 새 writer의 보수적 내부 정책이다. 역슬래시를 슬래시로 정규화한 뒤 NFC+casefold로 역할 충돌을 비교하며 실제 입력 문자열은 허용된 원형을 유지한다. 이 비교가 OS의 모든 이름/짧은 경로/매체 alias를 증명하는 것은 아니다.

report와 sidecar는 서로 달라야 하고 둘 다 image/mask artifact와 casefold 충돌하지 않아야 한다. sidecar는 image/mask의 모든 명시 quality_report_ref와도 충돌하지 않아야 한다. raw image quality_report_ref가 새 report target을 가리키는 것은139의 정상 미등록 draft와 호환되도록 허용한다. **그 경로에 실제 항목이 이미 존재하면 내용·종류에 관계없이 거부**한다. 같은 bytes가 이미 있어도 replay 성공으로 취급하지 않는다. 다른 image quality_report_ref는139 자체가 거부한다.

두 output은 같은 정규화 parent 문자열을 사용해야 한다. root와 output parent 및 모든 ancestor는 이미 존재하는 일반 디렉터리여야 한다. resolve 일치, lstat의 directory/symlink/reparse 속성·tag와 dev/ino identity를 확인한다. 부모를 자동 mkdir하지 않는다. Windows junction/reparse도 거부하며 UNC root는 지원하지 않는다. mapped drive의 실제 저장 매체나 OS 접근 권한을 인증하지 않는다.

두 output의 부재를 먼저 검사하므로 두 번째 파일이 이미 있으면 첫 번째도 만들지 않는다. 실제 생성은 `O_CREAT|O_EXCL|O_WRONLY`와 플랫폼에서 제공하는 O_NOFOLLOW·O_BINARY를 사용한다. 파일이 검사 뒤 경쟁으로 생겨도 EXCL이 기존 항목을 덮어쓰지 않는다. mode0600 요청은 플랫폼 의미에 따르며 Windows ACL 설정을 보장하지 않는다.

## write·fsync·사후 바이트 검산과 부분 실패

각 파일의 open이 성공한 즉시 created=true를 기록한다. 새 fd가 regular/size0인지 확인하고 short write를 처리하는 write-all loop로 끝까지 기록한 뒤 fsync한다. 부모 경계와 fd identity/크기를 다시 확인하고 닫는다. lstat와 읽기 전용 fd의 identity를 비교하며 bounded chunk read로 실제 저장된 바이트의 크기와 SHA를 검산한다. 전후 stat 및 fd의 dev/ino/size/mtime/ctime 일치를 확인한다.

모든 bytes와 SHA 검산이 끝나야 그 파일의 verified=true/bytes가 남는다. 이후 두 파일 모두 검산돼야 stored_outputs_verified=true다. 두 파일을 묶는 원자 transaction은 없고 directory fsync도 수행하지 않는다. report fsync 후 sidecar가 실패하면 report나 일부 sidecar를 **그대로 보존**한다. rollback·삭제·truncate·overwrite·자동 재실행·예약/원장 수정은 하지 않는다.

stored_outputs_verified는 각 파일을 순차적으로 읽은 시점의 관측이다. 첫 파일이 두 번째 검사 중이나 반환 후에도 변경되지 않았다는 동시 snapshot 보장이 아니므로, 후속 141에서 등록 전에 다시 검증해야 한다.

재시도 요청도 선존재 파일 때문에 차단된다. 이전 파일의 주체·유효성·복구 완료를 추정하지 않는다. open이 성공했다는 부분 이력은 실제 경로에 파일을 계속 독점 소유한다는 권한 증명이 아니다. 부모 경계와 사후 identity 검사는 동시 디렉터리 치환·모든 TOCTOU·전원 장애/매체 내구성·OS sandbox/CPU/RSS/시간 SLA를 완전히 보장하지 않는다. O_NOFOLLOW는 제공되는 플랫폼의 leaf 범위이며 없는 OS에서도 사전/사후 검사와 EXCL을 사용한다.

## exact21 결과

필드는 schema_version:1, scope:`EXCLUSIVE_NEW_QUALITY_REPORT_FILES_ONLY`, status, issue, report_output_uri, manifest_output_uri, report_sha256, manifest_sha256, fixed_refs, outputs, stored_outputs_verified와139의10개 false다.

- artifact_bytes_verified / registry_references_verified / registry_registered
- quality_report_verified / quality_mask_verified / source_authority_verified
- scientific_accuracy_validated / execution_authorized / state_dict_verified / workflow_supported

status는 BLOCKED / PARTIAL_FILES_PRESERVED / FILES_WRITTEN_UNREGISTERED다. outputs는 report/manifest 순서의 두 exact4 `{role,created,verified,bytes}`다. bytes는 검산 완료 시 정수이고 미완료는 null이다. created는 이 호출의 EXCL 생성 관측이며 이전 시도에서 남은 파일 유무를 대신하지 않는다. 실패 시 원본 path/exception 문자열을 issue에 넣지 않고 고정 `{code,field}`만 사용한다. 유효한 preflight 뒤의 부분 실패에는 caller가 명시한 상대 output URI와 계획 SHA/ref가 남을 수 있어 잔존 파일을 구분할 수 있지만 성공을 뜻하지 않는다.

주요 오류는 ROOT_INVALID, PATH_INVALID, OUTPUT_PATH_CONFLICT, OUTPUT_PARENT_MISMATCH, DIRECTORY_UNAVAILABLE/CHANGED, OUTPUT_ALREADY_EXISTS, OUTPUT_UNAVAILABLE, OUTPUT_LIMIT, OUTPUT_CHANGED, OUTPUT_WRITE_FAILED, COMPLETION_OUTPUT_INVALID와 기존139의 선언 입력 오류다. 생성 파일이 하나라도 관측된 실패는 PARTIAL_FILES_PRESERVED다. 레지스트리 등록·image/mask 실파일/헤더/값·품질 의미·기관 권위·실행 승인은 하지 않는다. stored_outputs_verified는 두 **새 출력 파일**의 관측만 뜻하므로 전체 source artifact 검증 flag는 계속 false다.

## 집중 시험과 인계

최종 담당 집중 **10 PASS / 2.185초 / exit 0**는 `evidence/integration/quality-report-storage-agent-20261018.log`다. 실제 Temp root와 새 두 파일의 exact21/SHA·139 한 번·원본 manifest/영상/마스크 불변·Store 호출 0, 어느 output이든 선존재 및 같은 bytes replay 거부, 부모 부재/mkdir 0·경로 충돌/예약명/ADS/Unicode controls, 두 번째 생성 경쟁·short write·fsync 실패의 부분 보존, 검산 후 mutable139 bytes/manifest 변조의 고정 expected 사용, custom root fspath 거부·reparse predicate 차단을 확인했다. reparse predicate 시험은 실제 junction 생성 검증과 구분한다.

초기 집중 10 PASS / 1.832초 원로그는 `quality-report-storage-agent-initial-20261018.log`로 보존했다. 이후 Windows 금지 문자 6개를 native 파일 호출 전에 PATH_INVALID로 거부하도록 보강하고, 각 문자에 대해 os.open 호출 0·report 생성 0을 확인했다. 기존 Windows에서도 native lstat가 해당 경로를 차단해 파일 생성은 없었다. 실제 부분 파일 사고가 발생했다는 뜻이 아니며, 이번 보강은 OS와 무관하게 오류를 조기에 일관되게 반환하는 경계다. 초기와 최종 시험 수를 합산하지 않는다.

별도 Temp setup에서 저장한 sidecar와 원래 caller image/mask manifest를 실제 Registry에 등록한 뒤133이 소비하는지 확인했다. 이 등록은 시험 setup이며 writer는 Registry/Store를 호출하지 않는다. 테스트 fixture 생성/정리와 제품의 무삭제 정책을 구분한다.

최종 관련 회귀는 **58 PASS / 12.861초 / exit 0**이며 `quality-report-storage-root-related-final-20261018.log`에 기록했다. 초기 관련 58 PASS / 10.422초 근거와 구분하며 합산하지 않는다.

독립 최종 근거 `quality-report-storage-independent-20261018.py/.json/.log`는 **12 실행 / 11 PASS / 1 SKIP / 실패·오류 0 / 6.86528초 / exit 0**다. 실제 Windows directory symlink 생성은 권한 오류 1314로 한 건 제외했다. reparse 및 parent identity 차단의 명시적 mock 시험은 별도로 통과했으므로, 이를 실제 링크 생성 시험의 통과로 표현하지 않는다. 실제 Temp 두 새 파일과 입력 SHA 보존, 별도 명시 Registry fixture 등록 후 131/133의 읽기 전용 소비, 두 번째 파일 생성 경쟁의 승자 보존, 두 번째 파일의 일부 11바이트 기록 후 실패 보존, 검산 후 mutable completion 변조 방어를 확인했다. report와 manifest 각각 금지 문자 6개에 대해 PATH_INVALID·os.open 0을 검증했다. 시험 helper의 초기 오류 근거는 `-initial`로, 구 native guard 관측 11 PASS / 1 SKIP / 4.478초는 `-pre-native-guard`로 보존하며 최종 수치와 합산하지 않는다.

`quality-report-storage-live-integrity-final-20261018.json`은 보호 파일 141개, 기존 소스 318개, 이전 증거 1309개가 모두 변경되지 않았음을 기록한다. catalog 14행과 canonical SHA, 예약 136314880바이트를 보존했고 운영 수집·학습·등록·배포·Workflow dispatch는 0이다. 저장 성공은 두 새 출력 파일의 관측이며, 원본 자료나 기관 품질 판정의 변경이 아니다.

최종 source SHA `220910abb10c19a07b0af458b6cdf163c16f9864c36dd123a622dbd11db91622`, test SHA `61548f8234d2cb2d5ec4428e9fa39dc789b5d138785a9ea75ffb6faeae63cbaa`로 Root/독립 담당에게 재동결했다. Root는 관련/실파일 대비·보존·공통 인계/Git과 이해 에이전트 작업 배정을 맡는다. 이해 담당은 검증된 코드·시험·부분 실패/미등록/미승인 범위를 해설/발표/FAQ/INDEX/변경 이력에 반영한다. 140은 새 내부 writer이며 CLI/HTTP/main/UI/Registry에 연결하지 않았고 운영 root에 실행하지 않았다. 새 내부 기능의 연결 범위가 이 두 파일 저장에 한정되어 전체 backend/frontend/build/browser는 이번에 재실행하지 않는다. 이전 137 전체 시험은 이전 근거이며 이번 시험으로 표현하지 않는다. 원본·원장·예약·분할·운영 모델은 보존한다.

후속 141 후보는 caller가 명시한 저장 report/manifest의 schema·SHA·ref를 읽기 전용으로 등록 전에 확인하는 단계다. 이번 파일 저장 성공은 해당 점검이나 Registry 등록 완료를 뜻하지 않으며, 운영 자동 등록은 하지 않는다.

## 후속141 저장 파일 재점검

[141 읽기 전용 점검](141_quality_report_preflight.md)은 명시된 report/manifest를 다시 읽고 기대 bytes/SHA·전체 report manifest schema·고정 ref를 확인한다.140 순차 저장 관측을 영구 유효 증명으로 사용하지 않으며 Registry 등록·원본 영상/마스크 검증·승인은 별도다.
