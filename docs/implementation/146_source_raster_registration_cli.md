# 146 — 명시 source raster 버전 한 건의 등록 CLI

상태: **TESTED_SYNTHETIC**. 신규 `scripts/register_dataset_version.py`는 호출자가 이미 완성한 GMAIS raster manifest 한 개를 **기존 catalog에 명시 등록**한다. `--data-root ABS`와 `--manifest FILE` 두 옵션이 필수이며 기본 운영 root·manifest·metadata를 선택하지 않는다. 신규 script·집중 시험·이 문서만 추가하고 기존 96/142/143·Store·API/UI는 수정하지 않는다. 운영 Store나 원본에 이 CLI를 실행하지 않았으며 모든 등록 시험은 Temp fixture다.

## 명시 입력과 사용법

등록 대상은 RAW 또는 STAGED의 data_type=raster 선언 한 건이다. dataset_id/version/SHA, source 기관·제품·license, 공간/시간, band 이름·mask 의미, lineage와 선택 metadata는 호출자가 제공한다. 이 CLI가 기관·밴드·semantics·보고서·버전을 추정하거나 품질 status를 올리지 않는다. document나 VALIDATED/STANDARDIZED 등은 등록 호출 전에 거부한다. 같은 version의 immutable 정책은 기존 96을 따른다.

`run(argv)`는 `(exit_code, exact20_result)`를 반환한다. `main(argv=None)`은 sys.argv 또는 주어진 목록을 처리해 UTF-8 JSON 하나를 stdout에 출력하고 int exit code를 반환한다. `--help`만 정적 도움말과 exit 0이며 JSON 결과는 None이다. builtin str 인자 최대 8개·각 4096자, 정확한 옵션만 허용한다. 약칭·중복 옵션(분리 값과 `--flag=value` 혼합 포함)·알 수 없는 인자는 고정 오류로 닫고 원문 인자나 traceback을 출력하지 않는다.

모듈 import는 script의 `__file__` 기준 project/backend/.runtime 경로를 명시 사용한다. 이는 **코드 의존성 경로**이며 자료 root 자동 선택이 아니다. 프로젝트 밖 cwd와 PYTHONPATH 없는 환경에서도 저장소의 로컬 의존성을 찾도록 했으며 설치 명령이나 네트워크 다운로드는 수행하지 않는다. 저장소 코드·로컬 dependency는 신뢰하는 실행 환경이다.

다음은 호출자가 준비한 임시 자료에 대한 사용 예시이며 운영 root에서 실행한 명령이 아니다.

```powershell
python 'E:\GeoAI–MLOps–SDSS\scripts\register_dataset_version.py' --help
python 'E:\GeoAI–MLOps–SDSS\scripts\register_dataset_version.py' --data-root 'C:\caller-prepared-temp-root' --manifest 'C:\caller-inputs\source-manifest.json'
```

입력 manifest JSON은 최대 256 KiB다. 기존 143의 `_input_file`을 재사용하여 strict UTF-8, duplicate key·NaN/Infinity/overflow·lone surrogate·안전 정수 범위·depth와 bounded builtin 사본을 검사한다. 파일/부모의 링크·reparse·identity·전후 stat 및 누적 읽기 크기를 확인한다. 명시 FILE은 root 밖에 있어도 별도 경계를 검사하며 stdin/env JSON이나 기본값을 사용하지 않는다.

## 선언·schema·바이트 검산

138의 pure `_manifest`로 고정 문자열·raster·RAW/STAGED·상대 artifact URI와 제한된 전체 선언 subset을 검사한다. 이어 기존 96 `canonical_manifest`로 전체 schema/기존 공간·시간·버전 계약을 검산한다. 따라서 **일반적인 모든 GMAIS manifest를 수용하는 범용 CLI가 아니라** 명시 source raster용 내부 subset과 기존 schema의 교집합이다. Windows 금지 문자·예약명·ADS 등 140 `_safe_uri`의 보수적 artifact 경로 정책도 적용한다.

schema 함수에는 별도 manifest 사본을 전달한다. 반환 tuple·manifest·digest를 원래 고정 expected와 typed 동등하게 대조하고, schema의 가변 반환을 나중에 등록 자료로 다시 읽지 않는다. manifest_sha256은 이 expected canonical UTF-8 JSON의 SHA다. 실패한 schema나 오염 결과는 constructor 전에 차단한다. cold local schema 파일 읽기와 설치 FormatChecker 한계는 기존 96/141과 같다.

기존 root/catalog를 검사한 뒤 96의 `verify_artifact`로 실제 source 파일 SHA를 읽어 확인하고, 등록 단계의 `register_version`에서도 기존 artifact 검산을 다시 수행한다. source 파일은 **읽기만** 한다. 실제 GeoTIFF header·pixel·band 의미·물리 보정·mask truth·AOI·lineage 부모 자산·기관 ACL을 검사하는 단계는 아니다. GDAL/Torch를 호출하지 않는다.

예외적으로 **catalog 자체를 source로 등록하지 못하도록 새 CLI에서 경계를 추가**했다. root의 catalog.sqlite3 및 직접 sidecar -wal/-shm/-journal과 같은 상대 URI·정규 경로·실제 file identity를 갖는 artifact는 CATALOG_ARTIFACT_ALIAS로 차단한다. NFC+casefold 이름 비교와 resolve/동일 dev·ino 비교를 사용해 직접 대소문자 alias 및 기존 DB family의 hardlink/symlink alias도 검사한다. 최초 검사는 SQLite 조회와 Store 생성 전이며 constructor 전·등록 전·등록 후에도 다시 확인한다. alias 파일을 쓰거나 삭제하지 않는다. **nested/catalog.sqlite3 같은 정상 하위 동명 파일이나 별도 inode의 복사본은 금지하지 않는다.** 이 내부 경계도 모든 동시 경로 치환을 OS 차원에서 봉쇄하는 보장은 아니다.

중요한 반례로, 호출자가 opaque bytes를 raster로 선언하고 SHA를 맞추면 기존 96 코어는 등록을 수용할 수 있다. 이번에도 이를 차단하는 새 native gate를 추가하지 않았다. 등록 성공의 artifact_bytes_verified·품질/기관/과학/실행 flags는 계속 false이며 이 성공을 “실제 영상 검증 통과”로 표현하지 않는다. 기존 129/131/132/133 consumer는 그대로여서 필요한 header·고정 선언·PUBLIC·품질 mask 경계에서 별도로 차단할 수 있다.

## 기존 catalog와 정상 constructor

143의 `_existing_catalog`로 이미 존재하는 root/catalog.sqlite3와 부모를 검사한다. SQLite URI mode=ro에서 records가 실제 table인지, kind/id/body TEXT와 PK(kind,id) 형태인지 확인하고 connection을 finally에서 닫는다. 누락·잘못된 DB는 Store 생성 전에 거부하며 새 DB나 table을 미리 준비하지 않는다.

같은 DB dev/ino·regular/reparse/resolve·부모 identity를 재확인한 뒤 정상 `Store(root, recover_jobs=False)` constructor를 사용한다. object.__new__나 별도 우회 Store를 만들지 않는다. 기존 mkdir/CREATE TABLE IF NOT EXISTS 메서드는 실제 실행되며 정상 기존 root/table에서 no-op인 의도다. 이를 모든 race의 파일 생성/물리 쓰기 0 보장으로 확대하지 않는다. SQLite journal/복구와 외부 동시 프로세스에 대한 OS sandbox가 아니며, constructor 뒤·등록 뒤·readback 뒤에도 같은 DB/부모 경계를 확인한다. 정상 DB 크기/mtime 변경은 허용한다.

register_version에는 fixed expected manifest의 별도 사본을 한 번 전달한다. 기존 버전을 덮어쓰지 않고 동일 manifest의 재호출은 기존 record를 다시 확인할 수 있다. 반환 record는 142 `_record`의 bounded exact6 검사를 거쳐 id·manifest/digest·UTC registered_at·science/deploy의 정확한 false를 검사한다. Store.get readback도 같은 고정 expected로 검산하고 반환 사본 전체와 typed 동등해야 한다. stdout에는 가변 원래 반환이 아닌 검증된 detached record를 사용한다.

기존 96의 local_asset/전체 source hash는 새 읽기 크기·시간 상한을 추가한 것이 아니다. root containment 정책이 모든 내부 링크·부모 동시 교체·TOCTOU를 막는 OS sandbox라는 뜻도 아니다. 기존 Store.get의 DB 원문 json.loads는 사본 검사 이전에 이루어지므로 전체 RSS 한도를 보장하지 않는다. 순차 파일 확인·DB 등록/readback은 원자 snapshot이나 반환 후 불변·CPU/RSS/시간 SLA를 제공하지 않는다.

## exact20 결과와 미확정 상태

기본 10키는 schema_version:1, scope:`EXPLICIT_SOURCE_RASTER_REGISTRATION_CLI_ONLY`, status, issue, dataset_ref, manifest_sha256, registration_record, store_initialization_started, registration_attempted, registry_outcome_verified다. 기존 10개 flag를 더해 exact20이다. 성공 때 registry_registered만 true이고 나머지 artifact/refs/품질/기관/과학/실행/모델·workflow flags는 항상 false다. stage의 세 bool은 구체적 관측만 나타낸다.

| 결과 | status | exit |
| --- | --- | --- |
| 입력·schema·파일/기존 DB 검사 차단 | BLOCKED | 2 |
| 정상 등록과 exact readback 확인 | SOURCE_RASTER_REGISTERED_UNAPPROVED | 0 |
| constructor 시작 뒤 예외·등록/반환/읽기 결과 불확실 | REGISTRATION_OUTCOME_UNCONFIRMED | 3 |

store_initialization_started는 constructor 직전에 true, registration_attempted는 register_version 직전에 true다. constructor가 시작된 뒤의 오류는 이미 DB에 영향이 있을 수 있으므로 register가 아직 호출되지 않았어도 미확정이다. commit 뒤 예외나 위조 반환/readback 실패도 같은 상태이며 registration_record는 null이다. 자동 retry·rollback·삭제·기존 버전 보정은 하지 않는다. registry_registered=false는 이 경우 행의 부재를 증명하지 않는다. dataset_ref와 manifest_sha256이 실패 때 남아 있으면 검증한 선언/계획값일 뿐 등록 확정 증거가 아니다.

issue는 고정 `{code}`만 반환한다. RAW/STAGED·RESTRICTED 같은 caller 선언을 그대로 보존하지만 기관의 품질·ACL·공개 승인이라고 인증하지 않는다. 성공 record에는 호출자가 명시한 manifest metadata와 상대 artifact URI가 포함되므로, 자동 비식별화가 아니라 명시 호출자의 정보 취급 범위다. 원문 input FILE/root 인자·exception은 오류에 넣지 않는다.

## 실제 Temp 검증과 인계

최종 집중은 **13 실행 / 12 PASS / 1 SKIP / 10.075초 / exit 0**, `evidence/integration/source-raster-registration-cli-agent-20261018.log`다. 실제 symlink 생성은 Windows 권한 오류 1314로 한 건 제외했고 실제 DB hardlink 차단은 통과했다. 실제 Temp GeoTIFF와 초기 catalog를 준비한 뒤 **프로젝트 밖 cwd·PYTHONPATH 제거·절대 script 경로** subprocess로 Unicode manifest 등록과 동일 replay를 검증했다. source 파일/manifest 불변, report 생성 0, 같은 id/version 충돌 때 기존 record/파일 보존을 확인했다.

strict JSON·256 KiB 정확 경계/초과·약칭/중복/secret 인자, data_type=document·품질 상향·alias version·잘못된 파일 SHA를 constructor 전에 차단했다. schema 반환·검산 직후 가변 결과·등록 반환/readback 오염과 constructor/commit 전후 예외는 별도 inprocess mock이다. 실제 commit 전 오류는 0행, commit 뒤 오류는 1행이 잔존하며 둘 다 미확정으로 반환했다. native raster open을 금지한 opaque bytes 반례에서 등록만 true이고 과학/영상 flags는 false임도 확인했다. 이 명시 fault를 실제 운영 동시성 시험으로 표현하지 않는다.

초기 집중 **9 PASS / 9.491초**는 `source-raster-registration-cli-agent-initial-20261018.log`로 보존했다. 초기 관련 123 PASS / 36.632초와 독립 9 실행 / 8 PASS / 1 SKIP / 21.7476992초도 DB 자기참조 검사가 없던 범위의 근거로 분리한다. 이 통과 결과를 새 경계까지 검증한 것처럼 표현하지 않는다. Root 검토 뒤 당시 source SHA 897750a4의 CLI를 Temp에서 실행해 artifact_uri=catalog.sqlite3 및 현재 DB SHA를 명시하면 등록이 성공하지만 그 등록 때문에 DB 바이트가 바뀌어 반환 ref SHA가 즉시 맞지 않게 되는 **실제 내부 결함**을 재현했다. 운영에 이 CLI를 호출하거나 기존 96을 변경한 것은 아니다.

재현 원근거는 `source-raster-registration-cli-self-catalog-reproduction-20261018.py/.json/.log`다. JSON에 이전 source SHA, exit 0·등록 1행과 실제 SHA 불일치를 고정 기록했다. 처음 python -c 명령의 셸 인용 SyntaxError는 별도 `...reproduction-command-initial-20261018.log`로 보존하며 제품/집중 시험 실패와 구분한다. 이후 .py helper로 재현했다. 최종 CLI 회귀는 DB/직접 sidecar/대소문자/hardlink alias를 SQLite 조회·Store 생성 0과 원파일 불변으로 거부하고 정상 nested 동명·별도 복사본을 허용함을 확인했다. 보강 중인 source와 독립 subprocess가 혼합되지 않도록 초기 독립 종료·증거 보존 뒤 패치하고 최종 재동결했다. 초기·최종 묶음은 합산하지 않는다.

최종 동결 source SHA는 `befa11f07709501a10b440409e2dad495a8ee04570f30d9347818522a0511de8`, test SHA는 `1f3b2e82a24accf68a0bc7a4464846ffb3890c61b2b3d1997d46d2e4c65517c4`다. 143 `_Parser`/`_input_file`/`_existing_catalog`, 138 `_manifest`, 140 root/path·부모 검사, 142 `_record`/typed comparison의 **private helper 결합**을 새 CLI에서 사용한다. 기존 파일을 수정하지 않았지만 private 계약이 바뀌면 관련 회귀와 독립 입력/결과 검사가 필요하다.

독립 최종 `source-raster-registration-cli-independent-20261018.py/.json/.log`는 **11 실행 / 10 PASS / 1 SKIP / 실패·오류 0 / 25.6986765초 / exit 0**이다. 최종 source/test SHA와 baseline f4565f5f의 기존 15개 소스 Git·전후 바이트가 같았다. 실제 외부 cwd·PYTHONPATH 없는 subprocess에서 이 CLI 두 호출로 image/mask source를 등록하고, 별도 명시 Python 140 준비 → 143 inspect/register → 131/133 읽기 소비 **128/128/256**을 확인했다. 이 경로의 source를 Python register_version으로 직접 setup한 것이 아니며 report 준비 metadata만 caller가 명시했다. source 동일 replay는 DB/전체 파일이 같았다.

독립의 DB family·대소문자·sidecar 및 실제 hardlink alias는 constructor 전에 차단되고 DB/원파일 bytes가 그대로였다. 실제 symlink는 Windows 권한 오류 1314로 한 건 제외하며 다른 alias 검사 통과와 구분한다. opaque raster 선언·RESTRICTED·미존재 lineage parent가 미승인 등록될 수 있음을 실제 반례로 남겼다. 그 성공을 native/ACL/전체 부모 DAG 검증으로 표현하지 않는다. constructor/실제 commit 뒤 예외·가변 schema/record와 오염 반환은 명시 inprocess fault다. 초기 독립 py/json/log의 8 PASS / 1 SKIP / 21.7476992초 원바이트를 `-initial`로 보존하고 최종과 합산하지 않았다. 운영·네트워크·학습·추론은 0이다.

Root의 최종 관련 회귀는 **127 실행 / 126 PASS / 1 SKIP / 46.970초 / exit 0**, `source-raster-registration-cli-root-related-20261018.log`다. alias 보강 전 관련 123 PASS / 36.632초 원로그는 `-initial`로 보존했고 최종과 합산하지 않는다. 회귀 뒤 **07:37:50**의 `source-raster-registration-cli-live-integrity-final-20261018.json`에서 보호 파일 141개·기존 tracked source 432개·이전 증거 1416개가 모두 변경되지 않았고 catalog 14행 canonical SHA·운영 dataset_versions 0·예약 136314880바이트가 유지됐다. 앞선 07:36:42 관측은 `live-integrity-initial` JSON으로 보존했고 두 관측의 수치는 같다. 최종 07:37:51 프로세스 확인에서 collector/train은 0이며 ACTIVE/10분 예약과 구분한다. 이 신규 CLI와 시험은 기존 소스 변경이 아닌 새 파일이며 운영 수집·학습·등록·배포·Workflow dispatch는 0이다.

Root는 관련 시험·보존·공통 문서/인계·Git과 이해 에이전트 배정을 맡는다. 이해 담당은 완료 코드·Temp 등록과 모의/미확정 한계를 읽고 해설·발표 대본·FAQ·INDEX·변경 이력을 갱신한다. 신규 CLI만의 내부 연결이므로 이번 전체 backend/frontend/build/browser는 재실행하지 않는다. 이전 145 전체 1431 PASS/1 SKIP은 이전 이력이고 이번 시험으로 재사용하지 않는다. main/API/UI나 collector에 자동 연결하지 않았고 운영 원본·원장·lock·분할·모델·예약을 보존한다. source 등록 한 건은 연차별 실자료 확보·독립 라벨·품질/모델 승인·수집/학습 재개가 아니다.
