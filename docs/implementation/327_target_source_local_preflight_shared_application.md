# 327 — 명시 로컬 사전검사의 공유 코드 적용

## 변경과 적용 근거

325 격리 구현과 326 독립 정적 검토 뒤 Root가 원본 기준 9개 파일 지문을 대조하고 소유 범위만 공유 코드에 적용했다. 기존 런타임 2개는 수정 전 원바이트를 보관했고, 새 계약·I/O 모듈 2개를 추가했다. 기존 `test_targeted_bare_plan.py`는 지문이 같아 덮어쓰지 않았다. 최초 적용 증거는 `evidence/integration/target327-application-root-20261018/application.json`이며 적용 시점의 TESTS_PENDING 상태를 보존한다.

`manifest_resource_profile.read_metadata`와 `bounded_json_digest`의 선택 키워드 `maximum_bytes=None`은 기본 동작을 유지한다. 명시하면 정확한 양의 정수이며 기존 역할 상한 이하일 때만 허용하므로 상한을 좁힐 수만 있다. 파일을 열기 전에 크기를 검사하고 같은 파일 핸들에서 실제 읽기·SHA·identity·트리 제한을 검증한다.

새 `prepare_explicit_targeted_bare_jobs(root, request, base_config)`는 exact v3 요청/plan v2 및 정확한 128MiB·3GiB 마커를 경로 접근 전에 검증한다. source 128MiB, ledger/lineage 8MiB 등 고정 역할 상한과 행·history 합계 3000/depth32/node4M/한 사전검사 누적 JSON I/O 16GiB를 적용한다. 같은 참조의 캐시 사용과 최종 지문 재검사를 포함한다. 기존 공개 함수와 v1/v2 경로의 64MiB 동작은 유지한다.

## 시험 격리 수정과 원 실패 보존

공유 회귀 최초 실행은 145건 중 144건 통과·1건 실패였다(45.592초, wrapper 53.734초). 전체 시험 로더가 수집 모듈을 먼저 import한 상태에서 로컬 시험이 전역 모듈 부재를 단정한 시험 격리 결함이다. `main-regression.log`와 `test-result.json`을 그대로 보존했다. 제품 런타임은 수정하지 않았다.

원 시험 SHA aed230f74a4056b8064f6e7289cb07b5c4ae88bd4e79fd0162584ee52d417e44는 `test_target325_before_import_isolation_fix.py`에 원바이트 보관했다. 수정 시험 SHA c9ad67980cc054a3fbeea940317f2232a5e58ecd0e236dd69a70b1e8d1d72209는 새 coordinator import와 소켓 사용을 실제로 차단하고 기존 모듈 객체 identity를 보존 검사한다. 별도 새 프로세스 시험 1건은 초기 coordinator 부재와 호출 뒤 부재를 검증한다. 독립 정적 검토에서 추가 차단 결함이 없었다. 325 격리 원판·freeze·원 시험 결과는 바꾸지 않았다.

수정 후 같은 9개 모듈 회귀 결과는 `test-result-corrected.json`과 `main-regression-corrected.log`에 별도 보관한다. 325의 큰 파일 합성 벤치마크와 운영 native/QA는 반복하지 않는다. 격리 63건과 portable 65건은 겹치는 사례이므로 합산하지 않는다.

## 상태와 실제 연결 범위

이 단위는 내부 로컬 사전검사 함수의 코드 적용이다. 170 CLI/coordinator, 작업자 ContextVar 전파, 전체 정산·상태·report JSON I/O 계측과 원격 예약에는 연결하지 않았다. 실제 64MiB 수집 차단은 여전히 BLOCKED이며 328에서 연결 설계를 별도로 검토한다. 원격 수집·학습·운영 승인 또는 실제 source 128 경로의 취득 성공을 의미하지 않는다.

새 API route나 화면 계약은 없다. 실행 중 서버를 재시작하지 않았고 새 함수를 서버에 적용했다고 주장하지 않는다. 기존 기본 함수 동작은 회귀로 검증한다. 따라서 이번 내부 기능은 추가 브라우저 조회가 필요하지 않으며 마지막 실화면 323 증거를 보존한다.

원본·원장·모델·고정 split·187 보존 잠금·old pending 전액을 유지한다. 추가 4GiB/2worker/공유2초/첫429/물리3000/batch64MiB COG+1MiB metadata 한도를 변경하지 않는다. 수량 충족과 나지·독립 정답·학습 승인을 구별하며 전체 개발은 미완료다.

## 최종 검증 결과

수정 후 같은 9개 모듈의 146건이 모두 통과했다. unittest 93.214초, wrapper 103.610초이며 원 실패 145건과 서로 다른 결과로 보존한다. 수정 로그 SHA b5f72c0810d4c95aae590dff56e481def546d75d39f511a06485166715627598. `completion.json`은 적용 런타임 4개 지문과 원본·원장·후보·나지검토·선택프로필 5개 운영 지문의 불변을 확인한다. 운영 파일을 해시로 읽었으며 수정·전체 물리 재스캔·운영 사전검사 실행은 하지 않았다. 별도 이해자료는 이 최종 근거로 후속 갱신한다.
