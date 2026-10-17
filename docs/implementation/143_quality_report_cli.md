# 143 — 품질 보고서 점검과 등록을 위한 명시 CLI

상태: **TESTED_SYNTHETIC**. 신규 `scripts/quality_report_cli.py`는 기존 141의 읽기 전용 `inspect`와 142의 명시 `register`를 연결한다. 기본 명령이나 root, 환경변수·stdin에서의 JSON 입력을 제공하지 않는다. 등록은 사용자가 `register` subcommand를 선택해야만 시도한다. 신규 script·집중 시험·이 문서만 추가하며 기존 142 이하, Store, main/API/UI는 수정하지 않는다. 운영 root에서 inspect/register를 실행하지 않았으며 실제 실행 시험은 Temp fixture뿐이다.

## 명령과 public 함수

두 명령 모두 다음 여섯 옵션을 명시해야 한다.

- `--data-root ABS`: 이미 존재하는 절대 root
- `--image-manifest FILE`, `--mask-manifest FILE`
- `--report-identity FILE`, `--report-metadata FILE`
- `--manifest-output-uri URI`: root 상대의 저장된 sidecar URI

입력 FILE은 호출자가 명시한 파일이며 data_root 안에 있어야 한다고 추정하지 않는다. 각 파일과 부모 경계는 별도로 검증한다. `--help`는 정적 도움말을 출력하고 exit 0이다. 다른 경로에서는 stdout에 UTF-8 JSON wrapper 하나만 출력한다. raw argv·파일명·예외 문자열을 argparse 오류나 traceback으로 출력하지 않는다. 명령 부재·알 수 없는 명령/옵션·누락 옵션은 ARGUMENTS_INVALID, 같은 옵션의 반복은 CLI_ARGUMENT_INVALID다. `--flag value`와 `--flag=value`를 섞은 중복도 거부한다. 옵션 약칭은 허용하지 않는다. builtin str 인자 최대 32개, 인자당 최대 4096자로 제한한다.

`run(argv)`는 `(exit_code, wrapper)`를 반환한다. `--help`만 `(0, None)`이며 정적 도움말을 출력한다. `main(argv=None)`은 생략 시 sys.argv를 사용하고 wrapper가 있으면 한 줄 JSON을 출력한 뒤 int exit code를 반환한다. 자동 등록·재시도·삭제·복구 명령은 없다.

## JSON 파일 4개의 읽기 경계

네 JSON 파일은 각각 **256 KiB** 상한이다. 명시 경로를 절대 경로로 해석하고 기존 부모·조상의 일반 디렉터리/reparse/resolve/identity를 검사한다. 파일은 일반 파일이어야 하고 링크/reparse를 거부한다. O_RDONLY와 제공되는 BINARY/NOFOLLOW를 사용하며 누적 읽기 상한과 fd/lstat identity·크기·mtime/ctime, 전후 부모 상태를 확인한다. 입력 파일을 쓰거나 부모를 만들지 않는다.

UTF-8을 strict decode하고 duplicate key, NaN/Infinity, float overflow, lone surrogate를 거부한다. 파싱 전 문자열 escape를 구분하는 depth scanner로 16단계를 제한한다. 정수는 변환 전 16자리, 변환 후 53-bit 안전 정수 범위를 제한한다. 이후 기존 bounded builtin 사본 검사를 적용해 깊이·노드·문자열·dict/list 크기·finite float·canonical JSON 크기를 검사한다. top-level은 dict여야 한다. 예외 원문 대신 INPUT_FILE_INVALID/LIMIT/CHANGED 또는 INPUT_JSON_INVALID로 닫는다.

이 상한은 직접 입력 JSON과 CLI 출력 사본의 범위다. source 파일 전체 해시·기존 Store의 DB 원문 json.loads·SQLite/GDAL/Torch 전체 실행 자원에 새 hard cap을 제공한다는 뜻이 아니다. 입력 선언의 source/spatial/temporal·품질/access·고정 identity를 추정하지 않는다.

## inspect: Store 및 SQL 없이 읽기

입력 사본에서 독립 expected141을 준비하고 별도 자식 인자 사본으로 141을 한 번 호출한다. 보고서·sidecar의 두 파일과 기존 로컬 schema 읽기만 수행한다. Store를 생성하거나 catalog를 조회하지 않으므로 **catalog.sqlite3가 없는 정상 fixture에서도 inspect가 가능**하다. 원본 영상/마스크·픽셀을 열거나 Registry를 등록하지 않는다. 141의 순차 snapshot/최종 stat·각 2 MiB·schema/checker 한계를 그대로 따른다.

성공 child는 expected141 exact23 전체와 typed 동등해야 한다. 차단 child는 고정 scope/status·빈 payload·false flags·두 files 관측과 allowlist issue를 가진 정확한 141 실패 결과여야 한다. 원문 private code/field나 오염된 flags/payload를 허용하지 않는다. 잘못된 반환이나 예외는 wrapper BLOCKED, result=null, exit 2다.

## register: 기존 catalog 사전 확인 후 정상 Store 생성

register는 명시 root와 `root/catalog.sqlite3`가 이미 존재하는 일반 파일인지 확인한다. 부모 identity와 링크/reparse 경계를 검사한 뒤 **SQLite URI `mode=ro`** 연결로 sqlite_master에서 records가 실제 table인지, PRAGMA에서 kind/id/body TEXT와 복합 PK kind/id 형태인지 확인한다. 연결은 finally에서 명시적으로 닫는다. 부적합·없는 DB 또는 table은 Store constructor 전에 차단한다. 이 사전 확인이 새 DB·테이블을 준비하지 않는다.

DB/부모 identity를 다시 확인한 뒤 기존 정상 `Store(root, recover_jobs=False)`를 호출한다. object.__new__로 constructor를 우회하지 않는다. 기존 constructor의 root.mkdir와 CREATE TABLE IF NOT EXISTS 메서드는 **실제 실행**되지만 이미 존재하는 root와 확인한 table에서는 정상적으로 no-op다. jobs 복구는 꺼진다. constructor 뒤와 142 호출 뒤에도 같은 DB dev/ino·부모를 확인한다. SQLite 정상 쓰기의 크기/mtime 변경은 허용한다.

이것은 모든 race에서 무생성·물리 쓰기 0을 보장하는 SQLite sandbox가 아니다. 검산 뒤 DB/부모가 교체될 수 있고 SQLite 자체의 journal/복구 동작은 기존 구현을 따른다. constructor 시작 뒤의 예외는 DB에 영향이 있었을 수 있으므로 보수적으로 결과 미확정으로 분류한다. 운영 root에서 이 경계를 실행한 적은 없다.

Store 생성 뒤 142를 한 번 호출한다. 실제 기존 source 두 버전을 읽고 전체 파일 SHA를 재확인하며 보고서 한 버전만 명시 등록한다. 142의 source raw manifest 동등성·보고서 저장 점검·immutable version·등록 반환/readback·결과 미확정 정책을 그대로 유지한다. source 자동 등록/patch, 원본 파일 쓰기, 보고서 생성은 하지 않는다. 142의 legacy source hash는 읽기 크기/시간 상한이 없고 Store DB body decode도 기존 한계를 유지한다.

## 자식 결과 검산과 exact6 wrapper

자식의 가변 결과를 stdout에 그대로 전달하지 않는다. bounded builtin 사본으로 만들고 정확한 keys/types/scope/status, 기존 false flags, 단계 flags의 bool 타입과 연관성, 고정 refs/manifest digest를 독립 계획과 대조한다. 142 성공은 정확한 record6의 manifest/digest/id·UTC registered_at·science/deploy false를 다시 검사한다. 등록 결과와 flags가 모순되면 거부한다. 예외 code도 고정 CLI allowlist 이외의 값을 출력하지 않는다. 검산한 사본만 반환하므로 자식이 다른 인자나 원래 dict를 바꿔도 계획을 대체하지 못한다.

wrapper exact6은 `{schema_version:1, scope:'EXPLICIT_QUALITY_REPORT_CLI_ONLY', command, status, issue, result}`다. command는 inspect/register 또는 인자 파싱 실패 시 null이다. issue는 null 또는 고정 `{code}`이며 raw argv·절대 입력 파일 경로·원문 예외를 담지 않는다. 정상 자식은 result에 기존 exact23 또는 exact22를 넣고 wrapper issue는 null이다. 자식의 정상 BLOCKED나 UNCONFIRMED 사유는 result.issue에 있다. 성공 payload에는 원래 계약의 명시 상대 URI와 caller report metadata가 포함되므로, 권한 있는 호출자가 이를 취급해야 하며 민감정보의 자동 비식별화를 주장하지 않는다.

| 상황 | wrapper status | result | exit |
| --- | --- | --- | --- |
| inspect 성공 | STORED_REPORT_FILES_VERIFIED_UNREGISTERED | 검산한 141 | 0 |
| register 성공 | REPORT_REGISTERED_UNAPPROVED | 검산한 142 | 0 |
| 입력/사전 DB/정상 child 검증 차단 | BLOCKED | 검산한 child 또는 null | 2 |
| 142의 결과 미확정 | REGISTRATION_OUTCOME_UNCONFIRMED | 검산한 142 | 3 |
| constructor 시작 뒤 예외·오염 child | REGISTRATION_OUTCOME_UNCONFIRMED | null | 3 |

등록 constructor나 자식 호출 뒤 불량 반환이 발생하면 이미 DB 반영이 끝났을 수 있다. result=null이나 registry flag false를 등록 부재·rollback 완료로 해석하지 않는다. 자동 retry/삭제는 없다. 출력 전달 중 프로세스 강제 종료·매체 장애·동시 변조까지 원자 동작이나 SLA를 보장하지 않는다.

## 설치 없이 사용하는 예시

아래는 **호출자가 준비한 임시 디렉터리용 예시**이며 실제 운영 root에 실행한 명령이 아니다. project root의 PowerShell에서 로컬 vendor/backend 모듈 경로만 설정한다. 제품 호출에는 tests 경로가 필요 없다. 시험은 `.runtime;.;backend;tests`를 사용했다. 새 라이브러리 설치나 환경 root 기본값 설정은 하지 않았다.

```powershell
$env:PYTHONPATH = '.runtime;.;backend'
python scripts/quality_report_cli.py --help
python scripts/quality_report_cli.py inspect --data-root 'C:\caller-prepared-temp-root' --image-manifest 'C:\caller-inputs\image.json' --mask-manifest 'C:\caller-inputs\mask.json' --report-identity 'C:\caller-inputs\identity.json' --report-metadata 'C:\caller-inputs\metadata.json' --manifest-output-uri 'quality.manifest.json'
```

등록 의도가 명시된 경우에만 subcommand를 register로 바꾼다. 필요한 source 두 버전과 catalog/records는 미리 준비돼 있어야 한다. source에 quality_report_ref가 없는 기존 버전은 이번 CLI가 바꾸지 않으므로, report 등록이 되더라도 기존 131 소비는 계속 차단될 수 있다. 소비 연결을 위해서는 호출자가 검토한 새 명시 source 버전 등이 필요하며 기존 버전을 자동 수정하지 않는다.

## 검증과 인계

최종 집중은 **11 PASS / 12.558초 / exit 0**, `evidence/integration/quality-report-cli-agent-20261018.log`다. 실제 subprocess에서 Unicode 입력 파일·stdout 한 줄 UTF-8 JSON, DB 없는 inspect와 Store/SQL 호출 0, 명시 register 및 동일 replay의 DB/파일 불변을 확인했다. mode=ro schema 조회와 recover_jobs=False constructor, 없는/잘못된 catalog 차단, 잘못된 JSON·256 KiB 정확 경계/초과, 인자 중복/약칭/secret 비노출, 오염 child·constructor/commit 뒤 예외의 미확정 상태를 검증했다. 명시 inprocess mock과 실제 subprocess 검증을 구분한다.

중복 옵션 사전 거부 보강 전 집중 **10 PASS / 14.882초**는 `quality-report-cli-agent-initial-20261018.log`로 보존했다. 실패를 숨긴 재실행이 아니라 새 입력 경계를 추가한 뒤 최종 11개를 실행한 것이며, 초기·최종을 합산하지 않는다.

source SHA `a6fb6388674ef41ab30329ff55dcb1291e1221cb7d9d8068c7dd6689f5eed87d`, test SHA `37dd83beb849cc985ce4539d959be88b5de464731c21194816ec7e3cb8f0c3d1`로 Root와 독립 담당에게 동결했다. Root는 관련 회귀·운영 조회/보존·공통 인계/Git과 이해 에이전트 작업을 맡는다. 이해 담당은 검증된 코드·시험으로 해설·발표 대본·FAQ·INDEX·변경 이력을 갱신한다.

Root 관련 회귀는 **90 PASS / 37.707초 / exit 0**, `quality-report-cli-root-related-20261018.log`다. 독립 최종 `quality-report-cli-independent-20261018.py/.json/.log`는 **10 실행 / 9 PASS / 1 SKIP / 실패·오류 0 / 33.0078190초 / exit 0**다. 독립 초기 실패나 cleanup 오류는 없었다. 실제 symlink 생성은 Windows 권한 오류 1314로 한 건 제외했다. source/test 최종 SHA와 baseline e3262a3a의 기존 12개 파일 바이트가 일치했다. 중복된 집중·관련·독립 묶음을 합산하지 않는다.

독립 검증은 실제 subprocess의 DB 없는 inspect와 Store/SQL 0 guard, Unicode 파일명, source 2건 setup에서 report 1건만 추가하는 register와 동일 재호출의 DB/전체 파일 불변, 131/133 소비 **128/128/256**을 확인했다. catalog/schema 부적합·strict JSON/크기·secret 인자·6개 옵션 중복 차단도 검증했다. constructor와 등록 전/실제 commit 뒤의 예외 및 오염 결과는 별도 inprocess fault다. commit 뒤 실패 시 report 행을 포함한 3행이 실제 잔존하고 CLI는 exit 3 미확정으로 반환했으며, 자동 rollback이나 삭제를 수행하지 않았다. 검산 후 가변 child를 바꾸는 시험도 고정 사본만 반환함을 확인했다.

`quality-report-cli-live-integrity-final-20261018.json`은 보호 파일 141개·기존 소스 324개·이전 증거 1366개, catalog 14행 canonical SHA와 예약 136314880바이트의 보존을 기록했다. 운영 dataset_versions는 0이며 운영 수집·학습·등록·배포·Workflow dispatch도 0이다. 보고 예약 ACTIVE와 실제 운영 실행을 구분한다. 이번 임시 등록 성과를 운영 DB 변경이나 전체 연차 자료 확보로 표현하지 않는다.

이번에는 기존 main/HTTP/137 request-response/모델 metadata/UI를 바꾸지 않았으므로 frontend/build/browser 및 전체 backend를 재실행하지 않는다. 이전 전체 시험을 이번 검증으로 확대하지 않는다. CLI 명시 연결은 내부 준비·점검·등록 흐름의 한 단계이며 실제 collector의 band/mask 선언, 원본 nodata·label/AOI 결합·독립 라벨·기관 품질/모델 승인·연차 전체 확보는 별도 후속이다. 다음 144 후보는 collector 산출물의 band/mask 선언 연결을 읽고 검토하는 단계다. 원본·원장·lock·예약·분할·모델을 보존하고 운영 자동 호출은 하지 않는다.

## 별도 상태 문서 검토

별도로 갱신된 docs16/20은06:51 관측 시각과 정체 기간37시간50분 표기만 바뀌었음을 quality-report-cli-separate-status-docs-20261018.json으로 원바이트 검산했다. 누계·manifest/원장 SHA는 그대로이며143의 수집 재개 성과가 아니다.

## 후속144 신규 producer 선언

[144 producer 보강](144_collection_raster_declarations.md)은 앞으로 생성하는 scene 영상의 실제 밴드 설명과 이진 품질 mask/nodata를 기록하고 NaN/Inf를 제외한다. 기존143 CLI·원본 산출물은 그대로이며 새 파일의 caller 명시 manifest/보고서 작성·등록·승인은 별도다.
