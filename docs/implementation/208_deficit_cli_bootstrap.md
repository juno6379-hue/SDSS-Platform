# 208 — guarded1024 CLI의 지연 import 경로 보강과 제한된 진단

상태: **수정 전 격리 재현 VERIFIED / 수정 TESTED_SYNTHETIC / 수정판 운영 재검사 미실시**.200 CLI의 bootstrap에 workspace ROOT를 추가하고,199 로컬 검사 실패의 고정 오류 코드를 제한해서 전달한다.199/170/일반 collector·원장·guard 소스는 수정하지 않았다.207 native 검사·운영 fullscan·수집·HTTP·학습0이다. 재실행은 Root의 새209 요청/소스 pin/별도 승인으로 진행한다.

## 왜 실제 CLI는 실패했나

Root의206 실제 CLI는81.265초 후 exit2로 끝났다. stdout은 `DEFICIT_LOCAL_PROOF_INVALID`, `execution_started=false`였고 worker/예약 전에 멈췄다. 잠금은 해제됐다. 그때200 source SHA는 `9797930f8ad04728af5f2f2fb4e49218dbf1f046f9c47c78b7a6e675821c627b`다. 원래206 request·launch·terminal·stdout/stderr·source pin은 그대로 보존한다.

200은 `backend`와 `scripts` 디렉터리를 sys.path에 넣었지만 workspace ROOT를 넣지 않았다.199 `_physical_inventory`는 내부에서 `from scripts.collect_targeted_bare import physical_patch_inventory`를 지연 호출한다. `scripts` 디렉터리 자체가 sys.path에 있어도 부모인 workspace ROOT가 없으면 `scripts` 패키지를 찾지 못한다. 루트 경로를 미리 넣고 검토했던205와, 실제 파일을 실행한206의 차이다.

수정 전에 새로운 subprocess를 Temp 디렉터리에서 시작했다. cwd와 sys.path0는 workspace 밖이고 PYTHONPATH는 `.runtime`만 제공했다. **구판200의 실제 bootstrap을 그대로 실행한 뒤199의 실제 지연 import에서 `ModuleNotFoundError: No module named 'scripts'`를 재현했다.** root_present=false/scripts_directory_present=true였다. import 단계에서 막혔으므로 물리 inventory를 읽기 시작하지 않았고 운영 fullscan/HTTP/원본 쓰기0이었다.

재현 근거는 `evidence/integration/deficit208-bootstrap-before-20261018.json`이다.206의 원문 예외 traceback은 일반 오류로 숨겨져 있어 그 실행 내부에서 동일 ModuleNotFoundError가 났다는 직접 traceback은 없다. 다만 동일 구판 source와 실제 누락 import를 격리 재현했고, 고정 경로를 미리 제공한205와206의 실행 환경 차이에 부합한다. 원격 데이터 품질 문제나 예산 부족이 확인된 것은 아니다.

## 최소 수정과 진단 범위

`scripts/collect_deficit_guarded.py`의 bootstrap 경로 목록에 `ROOT` 하나를 추가했다. backend/scripts의 기존 import 방식은 유지한다.199의 지연 import 및170/수집기 코드는 그대로다. 환경 변수에 우연히 ROOT가 있어야 작동하는 의존을 없앤 것이다.

199가 `local_checks_passed=false`를 반환하면 최대48자의 대문자/밑줄 코드만 `DEFICIT_LOCAL_PROOF_INVALID_<code>`로 전달한다. 예를 들어 `CENTER_INPUT_UNAVAILABLE`은 그 고정 코드까지 볼 수 있다. 경로·예외 원문·소문자/특수문자·길이 초과 문자열은 일반 `DEFICIT_LOCAL_PROOF_INVALID`로 유지한다. 로컬 검사는true인데 다른 proof 필드가 오염된 경우도 일반INVALID로 두어 `COORDINATOR_NOT_CONNECTED`를 실패 원인처럼 표시하지 않는다.

이 진단 확장은 승인·실행 게이트를 바꾸지 않는다. guard/예산/물리 cap·split·pending 전액 보존·정산/게시/cleanup·source prefix 보존과 `--execute` 기본off는200과 같다.

## 실제 CLI를 격리한 회귀

신규2개 시험은 **2 PASS /1.834초**다. `deficit208-bootstrap-focused-final-20261018.log`에 기록했다.

- `test_isolated_cli_bootstrap_reaches_real_delayed_inventory_import`: `python <실제200스크립트> --request ...`를 Temp cwd에서 직접 실행한다. PYTHONPATH에는 Temp hook과 `.runtime`만 주고 workspace ROOT는 넣지 않는다. sitecustomize hook이 요청 파일 reader와199 orchestration 결과만 Mock한다. 실제200 bootstrap/main·199 `_physical_inventory` 지연 import·빈 Temp sources/patches 물리 inventory는 실행한다. 정상적으로 `TEMP_BOOTSTRAP_IMPORT_VERIFIED` 진단까지 도달하며, 의도한 로컬 차단의 CLI exit2/execute_requested=false/execution_started=false를 확인한다. 실제 운영 request/aggregate/원장은 읽지 않는다.
- `test_failed_local_check_only_reports_bounded_uppercase_issue`: false+고정코드 전달, true+오염proof의 generic, 민감 경로/초과 길이의 generic을 확인한다.

이 회귀는 새 전체199 운영 스캔이나 provider 수집 성공을 뜻하지 않는다. Temp hook이 먼저 ROOT를 sys.path에 넣어 결함을 가리는 시험도 아니다. hook은 backend만 제공하며 workspace ROOT는 수정된200 자체 bootstrap으로 들어온다. 수정 전의 지연 import 실패와 수정 후 실제 CLI의 도달 차이를 분리한다.

200/199/170/parallel 관련 최종 회귀는 **79 PASS /33.288초**다. 신규208의2개 시험을 포함한200의24개와199/170/parallel을 함께 확인했다. `evidence/integration/deficit208-related-final-20261018.log`가 최종 근거다. 집중2개는79개에 포함되어 합산하지 않는다. ROOT 보강 후에도 운영 실제 전검사는 Root가 별도209로 수행해야 한다.206 실패를 성공으로 바꾸거나 그 기록/승인 파일을 덮어쓰지 않는다.

구판 source는 작업 파일을 되돌리지 않고208의 최소 diff만 메모리에서 역적용했다. 생성한 바이트가 기존200 freeze/206의 SHA `9797930f8ad04728af5f2f2fb4e49218dbf1f046f9c47c78b7a6e675821c627b`와 정확히 같을 때에만 `evidence/integration/deficit200-before208-20261018.py`를 새파일로 저장했다(19,794B). 별도로 남아 있던 원본 파일을 발견한 것이 아니라 SHA로 검증한 역적용 보존본이며, 작업 중 source는 변경하지 않았다. provenance는 `deficit208-before-source-archive-20261018.json`에 기록했다.

새 source/test/200·208 문서와199의 불변 pin은 `evidence/integration/deficit208-freeze-20261018.json`에 고정한다.208 담당의 운영 fullscan·collector·HTTP·native·운영 원장/원본 쓰기는 모두0이다.

UI/API 계약 변화가 없는 내부 CLI 수정이므로 브라우저 검증은 추가하지 않는다. Root는 완료 코드·구판 재현·수정판 시험·운영 미검증 경계를 이해 담당에게 전달하고200/208 설명·대본·FAQ·INDEX·변경 이력을 함께 갱신한다.
