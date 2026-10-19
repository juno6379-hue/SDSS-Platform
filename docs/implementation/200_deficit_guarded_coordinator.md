# 200 — 부족 셀 추가1024 후보를 실제 수집기에 연결하는 단일 coordinator

상태: **TESTED_SYNTHETIC / 운영 실행 미실시**. 신규 `scripts/collect_deficit_guarded.py`가199의 읽기 전용 검증을 기존 계측 수집기·원장·2worker에 연결한다. 이번 담당은 운영 후보/지원 fullscan·collector·STAC·HTTP·native 재검사를 실행하지 않았다. 운영 실행은 Root의 별도 검토·고정 소스/요청·단일 프로세스 인계 후에만 수행한다.

## 쉬운 설명

새 장소를 찾아 놓아도 그 후보 파일을 그대로 수집기에 넘기면 과거 사진과 중복되거나, 이미 다른 작업이 쓰는 예산/장소를 다시 사용할 수 있다.199는 선택한 장소가 현재 자료·원장·경계·기존 장소·부분 산출물과 모순되지 않는지 검사한다.200은 그 검사를 실제 실행 잠금 안에서 다시 수행하고, 통과한1024창만 최대2개 받도록 연결한다.

199의 결과가 `EXECUTION_BLOCKED/execution_supported=false`인 것은199 자체가 수집기를 실행하지 않는다는 뜻이다.200은 그 flag를true로 바꾸거나 외부 검토 JSON을 승인서처럼 읽지 않는다. 명시 요청의 전체 digest를 확인하고 내부199 함수를 fresh 호출하여, source pin·full support/pending proof·실제 물리 용량·생성 job/target binding을 별도로 검산한 뒤 자신의 단일 실행 경로로 넘긴다.

1024창은256 패치16개로 나뉠 수 있다. 실제 유효/행정경계 기준을 통과하는 개수와 부족 셀 개선량은 수집 후 별도 native 검증으로 확인해야 한다. 새로운 장소가 로컬 검사를 통과한 사실을 실제 사진 확보·나지 존재·학습 준비 완료로 표현하지 않는다.

## 입력과 호출

Python API:

```python
run_deficit_guarded(project_root, request, expected_sha256, execute=False)
```

request는199의 exact `GUARDED_DEFICIT_1024_REQUEST` 그대로다. proposal/current_manifest/ledger/boundary/config/prior_plan의 path+SHA, root가 명시 선택한 spatial_window_id+year1~2개, maximum_batches1~2가 필요하다.200은 후보/연도/우선순위/새 예산을 자동 생성하지 않는다. 고정 digest는 sorted strict JSON canonical SHA256이며 파일 원바이트 SHA와 구분한다.

```powershell
# 읽기 전용 검증: 원장 생성/예약/실행 lock/산출물 생성/네트워크 없음
python scripts/collect_deficit_guarded.py --request evidence/integration/explicit-request.json --expected-request-sha256 <canonical_sha256>

# 실제 실행은 Root만 고정 요청과 현재 프로세스/잠금을 확인한 뒤 수행
python scripts/collect_deficit_guarded.py --request evidence/integration/explicit-request.json --expected-request-sha256 <canonical_sha256> --execute
```

CLI request는 workspace `evidence/integration` 아래 상대경로·2MiB 이하 strict JSON으로 읽는다. 중복키/비유한 수는 기존 `_json`에서 거부하고 bounded 입력 사본을 고정한다. `--execute`는 기본off다. 성공 결과는 stdout JSON이며 worker 시작/완료 이벤트도 같은 stdout에 별도 JSON 줄로 기록한다. 검증 오류는BLOCKED/exit2, 예약 시도 이후 오류는 `DEFICIT_EXECUTION_FAILED`/exit2와 phase progress를 반환한다. `executed=null`은 실제 전송/정산을 단일 오류 메시지로 확정할 수 없다는 뜻이다.

## 고정 요청·잠금·199 proof의 독립 소비

1. execute에서는 기존 `global-ledger.execution.lock`을 `O_CREAT|O_EXCL`로 먼저 취득하고 PID와 파일 identity를 기록한다. 기존 잠금이 있으면199 검사나 예약 전에 거부한다. 자동 stale lock 삭제·우회는 없다.
2. lock 안에서199 `prepare_deficit_candidate_jobs`를1회 호출한다. dry-run은 lock 없이 읽기만 하므로 원자 snapshot이 아니며 실행 시 fresh 재검사가 필요하다.
3. helper의 local_checks/source_pins/request digest와 inventory의 inventory/pending/source flags를 검산한다. job1024/16패치·정확한 config SHA·target/province/year/fixed split·bbox/footprint binding·요청 선택 목록과 생성 key까지 재검산한다. `execution_supported=false`와 helper writes/network0을 보존한다.
4. 현재 active aggregate/ledger를 별도로 읽고 요청 SHA와 같은지 확인한다. 요청 ref가 `data/.../source.json` 같은 고정 DATA 사본이어도 허용한다.199가 그 사본을 읽어 검증하고 현재 active의 SHA가 같아야 한다. 실제 쓰기는 항상 고정 active 원장·aggregate에만 한다. 과거 snapshot을 현재 자료인 것처럼 허용하지 않는다.
5. historical/미등재/부분 패치를 포함한199 physical inventory의 상한3000을 확인한다. 실행 동안에도 `physical_before + 16*(완료한 source 수 + 현재 inflight + 새예약1)`을 확인한다. 최초 최대2개/32패치의 보수적 여유를 유지한다.

199는 기존 full inventory와 physical 안정성 검사를 포함하므로 실행 전 비용이 들 수 있다.200은 이전205 결과 파일을 재사용하거나 full proof를 생략하지 않는다. 이번 시험에서는 실제199 제안/기하/요청 검증을 실행하되 full inventory 및 physical 스캔만 명시 Mock했다. 운영 fullscan0과 구분한다.

## 실제 collector 경로와 보존 계약

- 기존 `CollectionLedger`를 같은 global 원장과 과거 원장2개에 연결한다. COG64MiB+metadata1MiB를 먼저 예약하고 같은4GiB 신규 상한을 쓴다. 기존 batch record는 모두 보존하며 finalization 전 원장 snapshot에서 다시 대조한다. 기존미정산2건136,314,880B를 정산/환불/재실행하지 않는다.
- source/patch 부모는 alias 없는 고정 workspace 경로다. 새 key는199가 만든 canonical key와 정확히 같아야 하며 두 leaf를exclusive mkdir로 예약하고 identity를 worker에서 다시 확인한다. 기존 leaf는 빈 디렉터리라도 재사용/덮어쓰지 않는다. 별칭·원본/모델 경로로 caller가 output을 바꿀 옵션은 없다.
- 같은 `scene_registry`와 `TargetedWindowClaims`를 두worker가 공유한다.199의 `DeficitCandidateLiveGuard`를 실제 `collect_windows(...,collection_guard=...)`에 전달하여 동년/고정 split·선택 B02 URL·native10m1024×1024·계획 오차·기존 support/pending/상호창을 검사한다.
- `balanced_coverage`에서 현재 부족 클래스·기여 패치 수를 계산해 `selection_context`를 구성하고 파일/collector에 전달한다. 충분한 기존 지역 자료가 있는 경우의 숲 우세 보류도 기존 일반 정책을 유지한다.1024 일반 자료 수집은 나지256 표적 수집과 다르며 나지 최소256을 새로 강제하지 않는다.
- 실제 선택 B02 witness가 있어야 materialization을 호출한다. 완료 source는 최대1개, 실제 image는 reserved source 디렉터리 안의6밴드1024×1024이어야 한다.256/truncated/초과 source는 materialization 전 거부한다. 기존 materializer가 최대16개256 패치를 만들고 province/year/split/spatial prefix를 검산한다.
- 기존2worker 실행기·전역 최소2초 요청간격·첫429 공유 중단·자산 재시도0을 그대로 쓴다. 이미 시작한 작업은 계측/정산을 마치되 새 제출·HTTP 회로를 우회하지 않는다.

worker finally는 COG state와 thread-local metadata를 읽고 새worker terminal에 계수를 남긴다. 중앙 finalize만 settle을 호출하고 기존 aggregate rows/history를 보존한 채 새 rows/source manifest/error를 append한다. 기존 비적격 row를 교체하거나 분할을 옮기지 않는다. active aggregate SHA는 reserve/finalize 전에 다시 대조하고 자신의 게시 SHA로 갱신한다. run-result에는 현재 예산/요청/회로를 기록하며 최종 submitted/finalized/phase summary는 CLI 반환 JSON에서 확인한다.

## 실패를 완료나 환불로 만들지 않는다

예약 시도 뒤 `selection_context` 구성에서 오류가 나면 새 pending 전액을 보존하고 `execution_progress`를 포함한 미확정 오류로 보고한다. 이를 일반 예산 부족 ValueError로 삼켜 성공0건처럼 보고하지 않는다. reserve가 쓰기 후 예외를 낸 경우도 결과를 지어내지 않는다.

worker finally/terminal 자체가 실패하여 전송량이 확인되지 않으면 중앙정산을 하지 않고 새 pending 예약 전액을 남긴다. 측정0/정상완료/환불을 발명하지 않는다. settle이 성공한 뒤 aggregate/run-result 저장이 실패하면 `settled_batches`와 `published_batches`를 나누어 기록한다. cleanup 실패도 phase에 별도로 표시한다. 잠금은 자신이 취득한 identity가 같은 경우에만 해제하며 다른 소유자 파일로 바뀌면 지우지 않는다.

이 순서는 다중 파일 원자 commit·durable journal·exactly-once 복구를 제공하지 않는다. 실패 후 자동 retry/rollback·기존 pending 재정산·누락 terminal 보충도 없다. 운영 복구는 Root가 실제 기록과 phase를 읽어 별도 판단해야 한다. 원장/aggregate/run-result가 순서대로 갱신되는 한계는170과 같다.

## 시험 근거와 한계

신규 집중 최종3차는 **22 PASS /17.678초**다. `evidence/integration/deficit200-focused-final3-20261018.log`에 보존했다. 실제 Temp 원장·exclusive lock·2worker·기하·native raster·materializer와 명시 Mock provider/inventory의 경계를 나누었다.

- digest/기존잠금/오염proof/잘못된job규격·config digest·active drift·physical2985+16을 예약 전에 차단.
- active SHA와 같은 DATA snapshot source/ledger refs 허용, snapshot 바이트 불변과 실제 원장만 갱신.
- 잠금 안에서199를 다시 호출하고 shared scene/window 객체·2초 설정·2worker 실행을 확인.
- Temp 모델/부분 파일 및 기존pending2 record·원본row prefix 보존, 실제 원장에 측정97B만 새정산.
- 실제 Temp1024×1024×6 영상·라벨·품질과 기존 materializer로16개 패치 파일을 생성하고 append 확인. provider/guard witness는 Mock이며 원격 선정/픽셀 취득 성공 시험이 아니다.
- B02 witness 없음·256/truncated 영상은 materializer 호출을 막음.
- first429/circuit 반영, post-reserve selection 실패·finally/terminal 실패·settle 실패·publication 실패·cleanup 실패를 구분. 미계측 새예약 전액 보존.
- CLI `--execute` 미지정의 HTTP/예약/원장구성/실행lock/출력 생성0.

초기 집중13건 중1ERROR는 시험 집계의 Windows 기본cp949 읽기로 생겼다. 시험 read_text에UTF8을 명시하고 fixture의 `doCleanups`를 호출하도록 수정했다. 초기 로그 `deficit200-focused-initial-20261018.log`, 중간18/20PASS 로그도 보존하며 최종22건과 합산하지 않는다. 실제 collector/운영 원장 오류가 아니다.

최종 관련 회귀는 **77 PASS /28.002초**다. 신규22개와199 helper·기존170 dispatch·parallel 실패 drain/429 시험을 함께 실행했다. `evidence/integration/deficit200-related-final2-20261018.log`가 최종 소스 기준이며 이전77PASS/24.882초 로그는 이전 실행 이력이다. 마지막 보강은 worker 오류가 있어도 이미 검산한 B02 witness의 관측 사실을 finally에서 보존하는1행과 대응 시험이며, witness=true가 최종 품질 합격을 뜻하지 않는다. 집중22개는 관련77개에 포함되므로 합산하지 않는다.

운영 지원 스캔·전송·새 패치 품질·원격 B02 검증은 이번 단위에서0이며 독립 과학 검증·학습·배포를 수행하지 않았다. Root의 별도 운영 실행과 후속 native 검증 결과를 제품 시험과 구별한다. 최종 소스/시험/문서와199/170/기존collector 의존 pin은 `evidence/integration/deficit200-freeze-20261018.json`에 고정한다.

내부CLI 추가라 기존 API/UI 화면 계약 변경은 없다. 브라우저 재검증은 이 단위에 필요하지 않다. Root는 완료 코드·시험·한계를 이해 담당에게 전달해 해설·발표·FAQ·INDEX·변경 이력을 같은 작업 단위로 갱신하고 공통 원장/인계에 반영한다.

## 208 후속 — 실제 CLI bootstrap 보강

구판200의206 실제 전검사는81.265초/exit2·예약/worker 전에 `DEFICIT_LOCAL_PROOF_INVALID`로 차단됐다.208의 수정 전 격리 subprocess에서 workspace ROOT가 sys.path에 없어199의 `scripts.collect_targeted_bare` 지연 import가 실패하는 것을 재현했다.200 bootstrap에 ROOT를 추가했고199 로컬 검사false의 제한된 대문자 고정코드를 진단에 전달한다. true 검사 뒤 proof 오염과 경로/민감 문자열은 generic으로 유지한다.199/170/기존 collector 소스와200의 실행/정산 보호는 바꾸지 않았다.

실제 CLI 파일을 직접 호출하는 Temp subprocess 회귀를 추가했다. 요청 reader/199 orchestration만 Mock하고 지연 import와 빈 Temp 물리 inventory를 실제로 실행했다. 이 수정 자체는 운영 fullscan·재수집·native 검사를 하지 않았다. 구판 source freeze와206 로그는 보존하며 수정판은 별도208 pin/Root209 실행으로 관리한다. 자세한 재현·시험 경계는 [208 문서](208_deficit_cli_bootstrap.md)를 따른다.
