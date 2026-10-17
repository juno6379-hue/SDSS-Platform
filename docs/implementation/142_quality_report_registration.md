# 142 — 호출자가 명시한 저장 보고서 한 버전의 등록

상태: **TESTED_SYNTHETIC**. `register_stored_quality_report(store, data_root, image_manifest, mask_manifest, report_identity, report_metadata, manifest_output_uri)`는 141의 저장 파일 점검과 기존 원본 두 버전의 재확인 뒤 **보고서 한 버전만** 기존 Dataset Registry에 등록한다. 호출자가 이미 초기화한 Store와 명시 root를 받아야 한다. 신규 source·집중 시험·이 문서만 추가하며 기존 141 이하, Store, Registry 코어와 운영 자료는 수정하지 않는다.

이 어댑터는 내부 명시 호출 경계다. HTTP/CLI/UI나 운영 자동 등록에 연결하지 않았고, 실제 호출 시험은 Temp Store에서만 했다. 성공은 REPORT_REGISTERED_UNAPPROVED이며 기관 품질·ACL·과학 정확도·모델 또는 Workflow 실행 승인이 아니다.

## 이미 초기화한 Store와 명시 입력

Store는 정확한 `Store` 타입이어야 한다. 서브클래스나 별도 proxy를 자동 초기화하지 않는다. `data_root`는 140의 명시 절대 root 정책을 따르고 `store.root == data_root`, `store.db == data_root/catalog.sqlite3`여야 한다. DB는 이미 존재하는 일반 파일이어야 하며 symlink/reparse가 아니고 resolve 경로도 같아야 한다. root와 조상의 최초 directory identity, DB dev/ino를 기억하고 접속 전·source 확인 사이·등록 직전·등록 후·readback 후 다시 검사한다. 정상 SQLite 쓰기로 DB 크기·mtime이 바뀌는 것은 허용하고 같은 파일 identity와 부모 경계를 유지한다.

누락 DB는 연결 전에 차단하여 새 catalog 생성으로 넘어가지 않는다. `Store(...)` 생성·테이블 초기화·mkdir를 어댑터가 호출하지 않는다. 단, 검사 뒤 파일 교체나 삭제의 모든 race를 봉쇄하는 OS sandbox는 아니다. 기존 Store는 일반 SQLite 연결을 사용하므로 hot journal 복구·외부 프로세스까지 포함한 모든 상황의 물리 쓰기 0을 주장하지 않는다. 이번의 “등록 전 차단”은 register_version/INSERT 호출 이전 상태를 뜻하며, 정상 Temp 시험의 기존 rows 불변과 운영 실행 0을 별도로 검증한다. 명시 등록 단계에서는 SQLite가 DB와 journal 등을 쓸 수 있다. 보고서·sidecar·원본 영상/마스크 파일 자체는 쓰지 않는다.

## 저장 파일과 고정 기준 사본

네 선언 입력은 139의 bounded builtin 사본으로 고정한다. report metadata의 source/spatial/temporal/RAW 또는 STAGED/access는 호출자가 제공한 원형이며 기본값·기관·제품·보고서 품질 승인을 추정하지 않는다.

139의 순수 기준에서 expected report bytes·manifest·refs를 재구성하고 141의 성공 exact23을 만든다. 다른 인자 사본으로 141을 **한 번** 호출해 전체 typed 결과와 비교한다. flags의 0/1과 bool, draft·바이트 수·SHA·refs·URI 차이를 허용하지 않는다. 관측한 141 반환 dict는 검산 뒤 다시 읽지 않고 고정 expected만 사용한다. 실패는 STORED_REPORT_PREFLIGHT_FAILED이며 source 조회·등록으로 넘어가지 않는다. 이 단계는 자료 두 파일의 각 2 MiB 점검 및 cold 로컬 schema 읽기를 상속한다.

141을 통과하면 반환 refs/hash와 stored_report_files_verified·manifest_schema_verified가 이력으로 남을 수 있다. 후속 source 확인이나 등록이 실패해도 이 값은 **앞선 관측 또는 계획값**이며 등록 완료를 뜻하지 않는다. registry_registered와 registry_outcome_verified를 함께 확인해야 한다.

## 원본 두 버전의 재확인

고정 image/mask refs 각각에 기존 `resolve_version`을 한 번씩 호출한다. 기존 Registry의 id/version/SHA·canonical manifest digest와 실제 source 파일 SHA 검사를 재사용한다. 반환 record는 bounded builtin 사본으로 만든 뒤 정확한 6키, id·manifest digest·caller raw manifest와의 typed 동등성·registered_at·두 승인 false를 검사한다.

source의 등록 manifest는 **caller가 준 raw manifest와 정확히 같아야 한다**. 138/139가 준비한 image draft의 quality_report_ref를 기존 source에 자동 덧붙이지 않으며, 없는 source 버전을 자동 등록하지 않는다. 예를 들어 기존 image가 보고서 경로를 선언하지 않았는데 caller가 그 경로를 새로 넣었다면 기존 버전과 다르므로 차단된다. 이 한계를 immutable version을 덮어써서 해결하지 않는다. source 두 개의 확인이 끝나야 source_dataset_refs_verified=true다.

반대로 기존 image와 caller raw 양쪽 모두 quality_report_ref가 없다면 두 선언은 같으므로 보고서 등록 자체는 가능하다. 기존 image 버전은 그대로여서 131 소비자는 해당 필드 부재로 차단된다. 이 반례는 “보고서 등록 성공”과 “소비 준비”가 다름을 보여 준다. 정상 소비를 시험하는 fixture는 처음 source를 등록할 때부터 quality_report_ref를 명시한다. 이를 자동 patch나 새로운 source 필수 입력 정책으로 바꾸지 않는다.

source 파일 읽기는 여기서 명시적으로 허용한다. 기존 `resolve_version → verify_artifact → asset_sha256`은 전체 source 파일을 해시하며 신규 141의 보고서 2 MiB 한도를 원본 영상/마스크에 적용하지 않는다. source 파일 크기·읽기 시간·RSS hard cap이나 모든 내부 링크에 대한 새 OS 정책을 추가한 것이 아니다. GDAL/Torch로 원본을 열거나 픽셀·헤더·의미·실품질을 판정하지 않는다. 기존 Store.get은 DB body를 제한 없이 json.loads한 뒤 반환하므로, 이후 bounded 사본 검사가 DB 원문 decode 전체 메모리 한도를 보장하지도 않는다.

## 보고서 한 건 등록과 미확정 결과

source 확인 뒤 Store 경계를 다시 검사하고, 기존 `register_version(store, fixed_report_manifest)`를 **한 번** 호출한다. source를 새로 등록하거나 자동 패치하지 않는다. register_version의 기존 immutable id/version·실제 보고서 SHA 확인과 INSERT 정책을 유지한다. 같은 고정 manifest를 다시 요청하면 기존 record를 재사용할 수 있고 registered_at도 유지된다. 같은 id/version의 다른 manifest를 덮어쓰지 않는다.

register_version을 호출하기 **직전** registration_attempted=true로 바꾼다. 이 이후 예외는 이미 commit된 뒤 발생했을 수 있다. 따라서 상태는 REGISTRATION_OUTCOME_UNCONFIRMED이고 등록 성공·등록 부재·rollback 완료를 추정하지 않는다. 충돌 거부도 일단 호출한 뒤라 같은 미확정 범주로 닫는다. 새로 남은 행이나 파일을 삭제하거나 자동 재시도하지 않는다.

등록 함수의 반환값도 무조건 신뢰하지 않는다. 정확한 6키 `{id, manifest, manifest_sha256, registered_at, scientific_accuracy_validated, deployment_approval}`의 bounded 사본이어야 한다. 고정 report id/version의 key·expected manifest/digest와 일치하고 두 승인값은 정확한 false여야 한다. registered_at은 bounded builtin str, timezone-aware UTC이며 기존 now().isoformat() 표기의 원형을 요구한다. timestamp는 기록 일치 검사이며 권위 있는 시각 증명이 아니다.

이후 `store.get('dataset_versions', fixed_key)`로 읽은 record도 같은 검사를 거치고, 반환 record의 고정 사본 전체와 typed 동등해야 한다. 성공 응답에는 가변 Registry 반환이 아닌 검산된 detached snapshot을 넣는다. 등록 반환 오염·readback 실패·Store 경계 변경은 모두 결과 미확정으로 남기고 registration_record는 null이다. registry_registered=false도 이 경우 “DB에 행이 없다”는 뜻이 아니다.

## exact22 반환 계약

기본 7키는 schema_version:1, scope:`EXPLICIT_STORED_QUALITY_REPORT_REGISTRATION_ONLY`, status, issue, fixed_refs, report_manifest_sha256, registration_record다. 단계 5키는 source_dataset_refs_verified, stored_report_files_verified, manifest_schema_verified, registration_attempted, registry_outcome_verified다. 여기에 기존 10개 flag를 유지한다.

성공 상태 REPORT_REGISTERED_UNAPPROVED에서만 registry_registered=true와 registry_outcome_verified=true다. BLOCKED는 등록 호출 전 실패, REGISTRATION_OUTCOME_UNCONFIRMED는 등록 호출 이후 확인되지 않은 결과다. issue는 고정 `{code,field}`이고 원문 예외·절대 경로를 노출하지 않는다.

나머지 9개는 항상 false다: artifact_bytes_verified, registry_references_verified, quality_report_verified, quality_mask_verified, source_authority_verified, scientific_accuracy_validated, execution_authorized, state_dict_verified, workflow_supported. source_dataset_refs_verified는 두 기존 버전의 이번 조회와 해시 대조 범위이며 전체 DAG·자료 독립성·기관 품질 승인 검증이 아니다. 기존 레코드의 scientific_accuracy_validated와 deployment_approval도 false로 유지한다.

source 조회·보고서 조회·등록·readback은 하나의 원자 transaction이 아니다. source가 조회 후 바뀌거나 sidecar가 141 뒤 바뀌지 않았다는 동시 snapshot을 보장하지 않는다. 96은 등록 시 report 자체의 SHA를 다시 확인하지만 이 기능은 source 전체를 함께 commit하는 transaction이나 반환 후 불변을 제공하지 않는다. exact Store라는 타입 조건도 객체의 동시 root/db 변경·메서드 monkeypatch·악의적 프로세스를 막는 보안 capability가 아니다. 신뢰하는 로컬 내부 호출 환경과 기존 SQLite/파일 정책의 한계를 상속한다.

## 집중 시험과 인계

최종 집중은 **10 PASS / 5.983초 / exit 0**, `evidence/integration/quality-report-registration-agent-20261018.log`다. 실제 초기화된 Temp Store에 source 2건을 먼저 등록하고 어댑터가 report 1건만 넣는 경로를 확인했다. 141 한 번·resolve 두 번·register 한 번, source rows/원본 파일 불변과 133의 읽기 전용 소비를 검증했다. 이번 집중 fixture는 all-zero mask라 계수는 **valid 0 / invalid 256 / total 256**이며 최소 유효율이나 품질 승인이 아니다.

같은 보고서 재호출은 같은 record/registered_at과 DB·파일 불변을 확인했다. DB 누락·root 불일치·잘못된 Store·source 부재/바이트 변조/raw manifest 불일치·141 오염은 등록 호출 전에 차단됐다. 명시 mock으로 141 검산 직후 가변 결과 변경, 두 source 확인 뒤 db retarget, conflicting report, 실제 commit 후 예외, 등록 반환 0/bool 오염과 readback 예외를 시험했다. postcommit 실패에서는 report 행을 보존하고 미확정 상태를 반환했다. 이를 실제 운영 동시성 시험으로 표현하지 않는다.

초기 두 집중 로그는 `quality-report-registration-agent-initial-20261018.log`와 `-initial2-20261018.log`에 보존했다. 각각 10 실행 / 9 PASS / 1 FAIL, 4.853초와 5.038초다. 첫 번째는 기존 133의 전체 status 대신 약칭을 기대한 시험 오류, 두 번째는 재사용 fixture의 all-zero mask를 checkerboard로 잘못 기대한 시험 오류였다. 시험 기대값만 기존 실제 계약에 맞추었고 제품 source는 수정하지 않았다. 초기와 최종을 합산하지 않는다.

source SHA `f401dbe295655e9b47b9b75d02cf9d1c7c28574e88386adb9fcabc7d714f475f`, test SHA `4e6eda4fee0e94c7cd68fc4dfc45e4370c4985f03edf67e2a7130e112ce413d3`로 Root와 독립 담당에게 동결했다. Root는 관련 회귀·원본 보존·공통 문서·Git 및 이해 에이전트 배정을 맡는다. 이해 담당은 완료 코드와 실제 시험 증거를 읽고 해설·발표 대본·FAQ·INDEX·변경 이력을 갱신한다.

Root 관련 회귀는 **79 PASS / 18.854초 / exit 0**, `quality-report-registration-root-related-20261018.log`다. `quality-report-registration-live-integrity-final-20261018.json`에서 보호 파일 141개·기존 소스 322개·이전 증거 1348개·catalog 14행과 canonical SHA·예약 136314880바이트가 보존됐다. 운영 dataset_versions는 0이다. 06:35 프로세스 확인에서 실제 수집·학습은 없었으며, ACTIVE/10분 보고 예약과 별개다. 이 보존 감사의 기존 증거 파일 수를 backend 시험 수로 혼동하지 않는다.

독립 최종 `quality-report-registration-independent-20261018.py/.json/.log`는 **13 실행 / 12 PASS / 1 SKIP / 실패·오류 0 / 10.4445115초 / exit 0**다. source/test SHA가 동결 값과 일치하고 baseline 4f55aeb의 기존 10개 소스도 보존했다. 독립 정상 fixture는 checkerboard mask라 133 소비 계수는 **128/128/256**이며, 담당 집중의 all-zero fixture **0/256/256**과 구분한다. 실제 Temp source 2건 setup 후 report 한 건만 추가하고 동일 record 재호출의 DB/파일 불변을 확인했다. 원본 native 파일 SHA 변조·source 부재/manifest 불일치·DB 부재/retarget/inode 교체, 141 오염, 등록 전후 commit fault, 반환/읽기 검산 실패와 mutable 반환 변경을 명시 fault로 검증했다. quality_report_ref 없는 기존 image나 RESTRICTED source는 보고서 등록이 성공하더라도 131 소비가 차단되는 반례를 확인했다. 실제 catalog symlink 생성은 Windows 권한 오류 1314로 한 건 제외하며 다른 mock 경계 통과와 구분한다.

독립 초기 **13 실행 / 5 PASS / 7 ERROR / 1 SKIP / 10.3659233초**는 시험의 DB rows 조회 helper가 SQLite connection을 `with`로만 감싸고 명시 close하지 않아 Windows Temp 정리에서 잠금이 남은 구성 문제였다. 제품 Store.connect는 이미 finally에서 close한다. 초기 py/json/log를 `-initial`로 보존하고 시험 helper만 try/finally close로 교정했으며 제품은 수정하지 않았다. 최종 정리 오류는 0이다. 독립 JSON의 초기 임시 경로 7개는 별도 잔존 관측에서 모두 부재였고 제거 메커니즘을 추정하지 않는다. 원장·lock·운영 경로를 정리하거나 재귀 삭제한 것이 아니다. 초기·최종·관련·집중 수치를 합산하지 않는다.

새 내부 함수는 main/API/137UI·CLI에 연결하지 않아 이번 frontend/build/browser 및 전체 backend는 재실행하지 않는다. 기존 전체 시험은 이전 이력이며 이번 관련·독립 시험과 합산하지 않는다. 운영 Store나 원본 자료에 이 어댑터를 호출하지 않았다. 원본·원장·lock·분할·모델·예약을 보존하며, 품질 보고서 한 건의 명시 등록을 전체 연차 자료 확보·QA 승인·학습/배포 준비로 확대하지 않는다. 후속 143 후보는 caller가 명시적으로 요청하는 CLI 진입점이며 운영 자동 호출은 별도다.
