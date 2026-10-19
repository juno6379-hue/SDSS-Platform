# 294 게시 후 source profile 재결속 준비

## 현재 상태와 소유

**IMPLEMENTED_UNVERIFIED — 실행 전 준비**다. Root276 검증 원판을 보존하고 새 evidence/integration/profile294-post290-root-20261018.py를 최소 파생했다. 290 QA는 진행 중이며 새 후보 수를 확정하지 않는다. 이 담당자는 현재 운영 source·ledger·profile·pointer나 부분 QA 결과를 읽지 않았고 실제 설정 교체·게시·HTTP·QA·학습·재시작은0이다. 최종 적용은 Root만 수행한다. 새293 게시 성공 산출물과 그 실제 SHA가 있어야 다음 단계로 갈 수 있다.

원판 profile276-post273-root-20261018.py SHA는01cd78fa391a153740b9a29238ec730c5509c9df052051a466190aa46bbde23d다. 원판 수정0이며 최소 diff는 evidence/integration/profile294-vs276-root-20261018.diff에 저장했다. 변경은294/290/293 번호와 현재 고정 지문·정량값, 게시 성공의 profile/분할 보존·미준비3차단 확인, 출력 경로 미존재 선검사다. 실제 후보 수는293 publication의 candidate_view.eligible_total에서 받아 예상 숫자를 코드에 넣지 않는다.

## 실행 전 계약

Root가 최종293 게시를 검산한 뒤 --publication-sha256에 그 SHA를 명시한다. 스크립트는 priority293-publication-root-20261018.json의 기대 SHA를 profile의 bounded read로 확인하고 COMPLETED_QA_PUBLISHED_AND_PROFILE_READER_VERIFIED, 동일 manifest MARKER, exact_retained_rows/partition_complete 정확히 true, file_sha_mismatches=0을 요구한다. candidate_view의 eligible_total은 bool이 아닌0이상 정수, source_matches_current_manifest는 정확히 true, ready_for_training은 정확히 false, blocker_count는 정확한 정수3이어야 한다. 이것은 게시 후 검산 소비이며293의 원본 QA나 정확한 retained partition 검산을 새로 수행하는 기능이 아니다.

source 고정핀은9d491e6ede51cf29407add25b83919cc5d4150576a694c5019814b973d20c2b7, ledger는4a4f4a47b522b9497b944ac00b29d2368a977c1a4eb6dfe972a34959fcc68722다. 현재 latest-candidate 지문이 publication.pointer_sha256과 일치해야 하고 실행 lock이 없어야 한다. source/ledger/latest-candidate/latest-bare-review의4핀을 보존한다. 기존 profile 설정은 SHAef093110c8bc180eddf122b64f831f86278cc3d30731ed98818dbbaf10a85e1e, source_manifest_sha256=9b580b338c8a2bca9b1a65ae5184b05622c457480acfec7ff9ddf169260bf89c여야 한다. 이 준비 문서의 지문은 Root 인계에 따른 기대값이며 준비 담당자가 현재 운영 파일에서 다시 읽은 값이 아니다.

## 변경 순서와 실패의 의미

새294 archive/selection/API response/API checks 파일이 모두 없음을 확인하고, 기존 설정 원바이트를 profile294-before-config-root-20261018.json에 exclusive 보존한다. 설정 객체의 source_manifest_sha256만 새 source로 바꾼다. 기존 descriptor와 나머지 필드의 의미를 바꾸지 않는다. source-profile237-root-20261018.json.root294-new라는 독점 임시파일에 기록·flush·fsync하고, 교체 직전 기존 config SHA와4운영핀을 다시 확인한 뒤 os.replace한다. 임시파일이 이미 있으면 exclusive 생성에서 실패하며 재사용하지 않는다. 새 설정 지문과 적용 사실은 API 호출 전에 profile294-selection-root-20261018.json으로 남긴다.

설정 교체 다음에만 기존8002의 /api/data/collection-status를 단1회 GET한다. 최대2MiB 응답·150초 timeout이며 재시도 루프가 없다. 원본1376·셀 부족11, 실제293 게시 후보 수 및 current source 일치, 미준비false/3차단, 나지50 검토 stale, 남은1,845,284,187바이트·원pending136,314,880바이트,4운영핀과 새 config핀 보존을 검사한다. 후보 receipt/pointer를 다시 게시하거나 QA를 반복하지 않는다. 원pending은 이미 사용액에 포함돼 있으며 다시 차감하지 않는다.

API 실패·timeout·응답 검산 실패 시에도 설정이 이미 적용됐을 수 있다. archive와 selection을 보존하고 실제 적용 완료와 API 검증 미완료를 구분해서 보고한다. 자동 rollback·설정 재교체·GET 재시도·서버 재시작은 없다. selection 자체 쓰기 실패처럼 더 이른 부분 실패도 기존 산출물을 지우거나 성공을 꾸미지 않는다. source/ledger hold와 수집기 부재 확인은 Root의 책임이며 코드의 lock 부재 관측이 collector의 원자 잠금을 대체하지 않는다.

## 산출물과 후속 검증

동결 증거는 evidence/integration/profile294-preparation-freeze-root-20261018.json이다. 코드 문법과 정적 GET callsite1개만 확인했으며 제품/임시 HTTP 시험·실제 실행은 하지 않았다. 293 최종 publication 필드 계약이 위 준비판과 맞는지 Root가 실행 전에 확인해야 한다. 실행 승인·실행 성공·실브라우저 확인은 모두 아직 false다. Root의 최종 코드 검토와293 완료 뒤 실제 결과·지문·시각으로 이 문서에 후속을 추가하고 web_ui 및 이해자료 담당에게 전달한다. 전체 개발 완료나 학습 승인으로 보고하지 않는다.
