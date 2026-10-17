# Job 입력의 현재 전이 계보 진단

작성: 2026-10-17, Asia/Seoul. 담당: data_pipeline. 코어 `job_lineage.py`, 별도 RFC router `job_lineage_api.py`, 시험 `test_job_lineage.py`를 추가했다. root가 main router를 연결했다. 기존 GMAIS router·job_inputs·job_snapshot·Dataset 코어·원문 schema는 변경하지 않았다.

## 상태와 경계

- **TESTED_SYNTHETIC:** 임시 Job/Registry의 현재 계보 검사, 예산, 신원 대조, 비쓰기/API 인증 회귀 12 PASS.
- **VERIFIED_REAL:** root가 기존 Job의 루프백 HTTP 요청에서 미등록 고정 입력에 대한 200/BLOCKED, 없는 Job404, no-store 및 보호 SHA·기존 Job 불변을 확인했다. 성공한 과학 실행이나 승인 자료 계보를 검증한 것은 아니다.
- **BLOCKED/미구현:** 과학·기관 권한·모델/배포 승인, 실제 Job executor, Job/Trace 기록 변경, 불변 파일 snapshot. 모든 승인 플래그는 false다.

새 `GET /v1/jobs/{job_id}/lineage-validation`은 요청할 때 현재 파일을 다시 검사한다. 기존 `/input-resolution`은 제출 시점 저장 진단을 재생한다. 두 기능을 서로 대체하거나 같은 시점의 검사로 표시하지 않는다. 저장 `input_resolution`은 이번 진단의 입력으로 사용하거나 갱신하지 않는다.

## 요청과 응답 계약

Job ID는 기존 `gmais_jobs` namespace에서 한 번 읽는다. 현재 Job ID·Agent ID·Trace ID와 저장된 원 요청의 Agent/Trace를 비교하고, 원 요청의 input_refs를 고정 id/version/sha256으로 확인한다. 원문의 URI/role·parameters·자격정보·제출 snapshot은 투영하지 않는다. URI hint로 등록 artifact 경로를 교체하지 않는다. 따라서 이 기능은 현재 고정 참조의 계보 진단이며 원 요청의 모든 의미·URI·품질·실행 요건을 재검증한 결과가 아니다.

응답의 기본 필드는 다음과 같다.

| 필드 | 의미 |
|---|---|
| `extension` | `greenblue.job-lineage-validation.rfc1` |
| `approval_status` | `INTERNAL_REVIEW` |
| `evaluation_scope` | `CURRENT_TRANSITIVE_LINEAGE_NOT_SUBMISSION_SNAPSHOT` |
| `job_id`, `trace_id` | 저장 Job/요청에 대조한 신원. 신원 오염이면 잘못된 값을 노출하지 않음 |
| `assessment_started_at`, `assessment_finished_at` | UTC 검사 시작/종료. 데이터 취득·업데이트 시각이 아님 |
| `available` | 현재 진단 보고서를 제공할 수 있는지. 파일 검증 성공과 다름 |
| `reason` | `CURRENT_LINEAGE_CHECKED`, `LEGACY_REQUEST_NOT_RECORDED`, `JOB_REQUEST_INVALID`, `CHECK_LIMIT_REACHED` |
| `status` | 현재 입력 계보 진단의 `INTEGRITY_VERIFIED` 또는 `BLOCKED`. 저장 Job 상태를 변경하지 않음 |
| `bindings` | `{input_index, ref:{id,version,sha256}, diagnostic_index, reused, checked}` |
| `diagnostics` | 기존 Dataset HTTP allowlist projection을 재사용한 개별 계보 진단 배열 |
| `blockers` | `{input_index,code}`. 민감 원문·URI·role·내부 예외 미포함 |
| `limits` | 아래 서버 한도와 실제 검사량 |

`checked=true`는 해당 고정 root의 진단을 수행하거나 같은 요청의 캐시를 재사용했다는 뜻이다. 성공을 의미하지 않는다. `diagnostic_index`가 실제 root_ref와 연결된다. 검사하지 않은 binding은 `checked=false`, `diagnostic_index=null`이다. 동일 root 재사용은 `reused=true`로 구별한다.

형식·신원이 정상이어도 같은(id,version)에 다른 SHA가 나오면 `JOB_INPUT_REFERENCE_CONFLICT`로 차단하고 파일을 검사하지 않는다. 이런 구조 진단은 `available=true`, `diagnostics=[]`, `current_assets_revalidated=false`일 수 있다. 이 조합을 성공이나 잘못된 서버 응답으로 추정하지 않는다. 같은 Dataset의 서로 다른 고정 version은 정상 입력으로 허용한다.

`authorization_verified`, `execution_authorized`, `scientific_approval`는 코어·HTTP 모두 false다. `network_requests=0`, `source_files_written=0`. 현재 검사 성공이 기존 BLOCKED Job의 실행 gate를 해제하지 않는다.

## 합산 한도와 재사용

HTTP 서버의 기본 한도는 깊이32, 고유 root당64 node, 요청 전체256 node 검사, 입력64개, 고유 root32개다. 임의 query parameter로 확장하지 않는다. Python 함수의 keyword 한도는 시험·내부 호출에서 기본값보다 낮게만 설정할 수 있으며 bool과 범위 밖 값을 거부한다.

입력64개 초과는 개별 ref를 복제하거나 해시하기 전에 거절한다. 먼저 상수 시간으로 Job/status/request의 Agent/Trace를 확인해 정상 한도 응답의 Trace를 유지한다. 고유 root32개 초과도 계보 코어를 호출하기 전에 거절한다. 이 경우 `available=false`, `reason=CHECK_LIMIT_REACHED`, 빈 bindings/diagnostics와 `JOB_INPUT_REF_LIMIT` 또는 `JOB_UNIQUE_ROOT_LIMIT`을 반환한다.

각 root의 실제 반환 nodes 수를 `node_checks_performed`에 더하고 총 예산에서 차감한다. 서로 다른 root가 공통 조상을 다시 검사하면 그 검사도 비용에 포함한다. 같은 id/version/SHA root는 요청 내에서 결과를 재사용해 다시 해시하거나 예산을 차감하지 않는다. 캐시는 요청 사이에 유지하지 않는다.

새 root의 `max_nodes`는 root당 한도와 전체 잔여 예산 중 작은 값이다. 전체 잔여량이0이면 더 이상 새 root 코어를 호출하지 않고 `JOB_TOTAL_NODE_CHECK_LIMIT`을 기록한다. 이미 검사한 동일 root는 그 뒤에도 캐시를 재사용할 수 있다. 일부 진단이 있는 총 예산 차단은 `available=true`, `reason=CHECK_LIMIT_REACHED`이며 미검사 binding을 명시한다. 마지막 root 내부에서 전역 잔여 한도가 소진돼도 전체 성공으로 표시하지 않는다.

`unique_roots_checked`는 수행한 서로 다른 root 진단 수이며, 동적 버전처럼 자산 해석에 도달하지 못한 진단도 포함한다. `current_assets_revalidated`는 하나 이상의 개별 진단에서 실제 resolve 시도를 했는지다. 전체 조상 검증 완료를 뜻하지 않는다. 전체 true는 모든 binding의 진단이 성공하고 blocker가 없을 때만 반환한다.

## 오류·정보 최소화·검사 시점

- 없는 Job은 기존 GMAIS error 형태의404 `JOB_NOT_FOUND`다.
- 원 요청 자체가 없는 레거시는200/`available=false`/`LEGACY_REQUEST_NOT_RECORDED`다. 저장 제출 snapshot이 없다는 뜻과 다르다.
- 요청이 null·잘못된 객체·빈 refs·잘못된 SHA·신원 불일치면200/`JOB_REQUEST_INVALID`다. 검사·임의 데이터 등록을 하지 않는다.
- 미등록/동적 버전/계보 SHA 오류·cycle·깊이·ACL 차단은 개별 진단과 index별 blocker로 반환한다. 제한자료 상위 lineage는 기존 코어 정책대로 조회·출력하지 않는다.
- 예상하지 못한 내부 오류는503 `RESOURCE_UNAVAILABLE`의 고정 메시지다. 내부 KeyError를 모두 없는 Job404로 오인하지 않는다.
- 실제 main app의 기존 token 의존성을 상속한다. 인증 실패는 기존401이며 기관별 자료 열람 권한 구현을 뜻하지 않는다.

200/404/503에 `Cache-Control:no-store`를 적용하고 Job 읽기·계보 해시는 `run_in_threadpool()`에서 처리한다. 새 Job queue·Trace·background 저장을 만들지 않는다. 여러 파일을 순차 검사하는 한 번의 요청이며, 전체 그래프의 원자적 파일 snapshot이나 검사 뒤 불변성을 제공하지 않는다. 입력 ref 개수·고유 root·node 검사량의 상한은 개별 자산 총 바이트나 운영 동시부하 검증을 대체하지 않는다.

## 시험·실제 조회 근거

```powershell
$env:PYTHONPATH = "$PWD/.runtime;$PWD/backend;$PWD/tests"
$env:PYTHONIOENCODING = 'utf-8'
python -m unittest discover -s tests -p test_job_lineage.py -v
```

관련 **12 PASS / 3.188초**, [job-lineage-tests-20261017.log](../../evidence/integration/job-lineage-tests-20261017.log). 동일 root 검사1회·index mapping, 공유 조상의 반복비용, 예산0 이후 캐시 재사용/새 root 미검사, 부분 root 잔여 quota, refs65 개별 deepcopy 금지·Trace 유지, unique33 선차단, 구조 상충 SHA 무해시, dynamic/missing/ACL 비노출, legacy/badrequest/identity, 자산 변경 후 재검사, main token 상속·기존 Status schema·제출 snapshot·SQLite 바이트 불변을 확인했다.

root의 [기존 Job 루프백 조회 증거](../../evidence/integration/job-lineage-live-20261017.json)는 2026-10-17 10:46 KST다. 기존 `job-00893a5fc1014e4db9eea3d8a7fa238f`는200/`CURRENT_LINEAGE_CHECKED`/`BLOCKED`이며 미등록 고정 Dataset을 차단했다. 없는 Job404/no-store와 보호 파일 및 기존 Job의 SHA 불변도 기록했다. 새 Job 실행·원본 자료 등록·실제 성공 계보 승인은 없었다.

독립 담당의 정식 실행도 **12 PASS / 4.430초 / 종료0**이며 [독립 로그](../../evidence/integration/job-lineage-independent-tests-20261017.log)를 따른다. 별도 적대 fixture에서 총 예산·예산 소진 후 캐시·Job1회 읽기·URI/role/snapshot 비노출·공유 조상 비용·SHA 충돌·65refs Trace 유지도 확인했고 추가 재현 결함은 없었다. 전체 회귀는 root의 별도 결과로 확정한다. 관련12시험에 과거 전체 시험 수를 더해 통합 검증 숫자를 만들지 않는다.

## UI 인계와 남은 범위

web_ui에 필드·사유·부분검사·한도 의미를 인계했다. 현재 계보 검사는 명시적 버튼으로 요청하고 저장 snapshot 카드와 분리한다. 자동 폴링·원문 요청 표시·Dataset 자동 등록/추정은 추가하지 않는다. UI 구현과 실제 브라우저의 최종 증거는 담당 문서39 및 root 근거를 따른다.

기관 ACL, 독립 과학 검증, 실제 Job executor, 실행 시점 불변 입력 고정, Workflow 전이계보 연결은 별도 후속 범위다. 이번 companion 완료를 그 기능의 승인이나 전체 개발 완료로 보고하지 않는다.


## Root 최종 통합·실제 읽기 근거

전체 scripts/test.ps1 종료0: **310건/309PASS/1SKIP/101.622초**, evidence/integration/job-lineage-full-tests-20261017.log. 실제UI5174proxy→API8002에서기존Job200 CURRENT_LINEAGE_CHECKED/BLOCKED,없는Job404·no-store확인. 저장snapshotLEGACY와현재BLOCKED표시·명시클릭·ID변경clear·다른Job조회시현재검사자동미실행·desktop/mobile검증은문서39와 job-lineage-live-20261017.json을따른다. 보호5파일SHA·기존Job2건레코드SHA불변/신규실행0이다. 실제성공계보나과학/기관승인증거로보지않으며정상/부분한도/변조성공경로는임시fixture시험이다.
