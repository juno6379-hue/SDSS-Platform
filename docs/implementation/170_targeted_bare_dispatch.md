# 170 — 기존 계측 수집 경로를 이용하는 명시적 나지256 집행 entry

- updated_at: 2026-10-18 KST
- source_commit: Root 소유 신규 `scripts/collect_targeted_bare.py` 작업 트리
- evidence_paths: `evidence/integration/targeted-bare-dispatch-agent-final3-20261018.log`, `evidence/integration/targeted-live-guards-agent-final-20261018.log`, `evidence/integration/targeted-collection-hooks-related-20261018.log`
- confidence: 독립 검토·임시 원장/실제 두 worker 실행기와 mock 수집의 경계 검증
- status: TESTED_SYNTHETIC / 실제 표적 원격 수집 성공 미검증

## 11:38 이후 후속 — F2 실행 실패 표현·F3 실제 물리 상한

이 후속은 `scripts/collect_targeted_bare.py`·해당 시험·이 문서만 수정했다. 171 담당의 `parallel.py`/`test_data_parallel.py` F1 정산 보완은 수정하지 않고 재사용한다. 시작 관측에서 실제 execution lock과 targeted/일반 수집 Python 프로세스는 없었다. 기존 반텐 실제 실행·QA의 성과는 Root의 별도 native 감사 근거이며 아래 합성 시험으로 대신하지 않는다. 실제 원본·원장·pending·모델 변경과 원격 HTTP는0이다.

### F2 — CLI 오류는 무조건 미실행이 아니다

예전 main의 모든 예외 `executed:false` 표시는 제거했다. 새 `execution_progress`는 예약 시도·예약 확정·collector 진입·정산 시도·정산 확정·aggregate 게시 batch 키를 분리한다. 예약을 시도한 뒤 예외가 발생하면 `TargetedExecutionFailure`에 해당 진행 상태를 싣고 CLI가 exit2, `status:TARGETED_EXECUTION_FAILED`, **`executed:null`**, `execution_started:true`를 출력한다. 예약 전 요청 pin·기존 lock·출력 충돌 차단은 `BLOCKED/executed:false`다. `execute_requested`와 실제 경계를 구분한다.

원장 저장 후 reserve가 예외를 낼 수도 있으므로 “예약 시도”를 함수 호출 전에 기록한다. 확인하지 못한 예약 결과·정산은 `INCOMPLETE_OR_UNVERIFIED`다. `transfer_status:NOT_INDEPENDENTLY_VERIFIED`는 collector 진입이 확인되어도 실제 원격 바이트 수신을 이 진단만으로 단정하지 않는다는 뜻이다. `settlement_status:ALL_RESERVED_SETTLED`와 `publication_status:ALL_RESERVED_PUBLISHED`는 모두 해당 callback이 성공 반환한 batch 집합에 근거한다. 정산 후 aggregate 쓰기 실패를 정산 실패로 혼동하지 않는다. lock 정리 실패도 진행 상태를 보존하며 `cleanup_status:INCOMPLETE_OR_UNVERIFIED`로 보고한다. 금융 정산 재시도·pending 환불·원장 초기화는 하지 않는다.

### F3 — 등록되지 않은 물리 패치도 상한을 쓴다

`physical_patch_inventory()`는 다음의 합집합을 실제 로컬 경로/파일 identity로 검사한다.

- aggregate `scenes`와 `historical_noneligible_patches`의 image/label/quality 참조.
- 기존 source worker-result의 `targeted_unenrolled_patches` 참조.
- 고정 `patches/` 아래 실제 image/label/quality 파일이 하나라도 있는 디렉터리. 중단·미등록·부분 출력도 최소1칸을 사용한다.

명시 참조는 canonical `image.tif`·`label.tif`·`quality.tif` 세 실제 regular 파일과 동일 parent가 있어야 한다. 유실 참조, 중복 image 경로/동일 inode alias, 경로 link/reparse, 이미 aggregate에 포함된 unenrolled 참조의 중복 등록은 차단한다. 기존 원장의 `target256-` batch는 source worker receipt가 없으면 보수적으로 차단한다. 누락된 receipt를 자동 재구성하거나 부분 파일을 삭제하지 않는다. 3000개를 넘으면 즉시 거절하고 12단계/디렉터리20000개/파일30000개/receipt8MiB 제한으로 탐색을 제한한다.

이 관측은 품질/래스터 내용 재검증이 아니다. 경로·identity·크기·mtime/ctime와 receipt pin을 반영한 순차 observation SHA를 로컬 전체검사 전후 비교한다. OS 수준 원자적 snapshot이나 비협조적 외부 writer에 대한 완전한 배타 보장은 아니며 기존 공통 execution lock을 지키는 단일 coordinator 범위다.

각 신규 job은 nominal1·256픽셀·AOI1개·단일 year로 검증한다. `현재 물리 합집합 + 전체 신규 job 최대량 ≤ 3000`이어야 하므로 2999개에서 job1개만 허용하고 job2개는 예약 전에 차단한다. execute 경계에서도 같은 최대량을 재검사한다. 실제 materialize 전에 report의 로컬 영상 header에서 생성 가능한256창 합계가1 이하인지 검사하고, 반환 patch 수도1 이하로 제한한다. output guard/B02 witness와 함께 큰 source가 새 물리 파일 여러 개를 생성하는 것을 사전 차단한다. 성공·dry-run 결과에 `physical_inventory` 또는 `physical_inventory_before`와 `maximum_new_physical_patches`를 포함한다.

### 후속 시험 범위

기존12개 외에 F2/F3 경계11개를 추가하여 집중23개다. 실제 임시 원장/두 worker에서 두 번째 reserve 충돌 후 첫 정산 보존, settle 실패의 pending 전액 유지, reserve 원장 저장 후 예외, 정산 후 게시 실패, lock 정리 실패를 검사한다. main의 JSON과 exit2는 무해한 실제 Python subprocess fixture로 예약 전/후를 비교한다. 이 child는 run_targeted 실패만 주입하므로 원격 실행을 하지 않으며 실제 진행 추적 시험과 구분한다.

실제 임시 파일로 unenrolled·고아/부분 디렉터리 누적, 중복·유실 참조·receipt 부재를 확인한다. 2999+최대 신규량 검사는 native157/167와 physical snapshot을 명시 mock한 계약 경계 시험이다. 실제 로컬512×512 GTiff는 materialize 전에 거절되는지 검사한다. 집중 초기 실패는 mock proof의 `issue` 키 누락이었으며 제품 로컬 검사를 약화하지 않고 fixture를 정정했다. 이전 로그는 `target170-f2f3-focused*`에 보존한다.

관련61개 시험은23 dispatcher+12 live guard+10 hooks+12 기존171 parallel+4 budget이며 `evidence/integration/target170-f2f3-related-final-20261018.log`에서 **61 PASS / 0 SKIP,6.731초**를 확인했다. 이는 임시원장·mock 원격·합성 native 경계의 근거이며 실제 후속 반텐 실행 성공/나지 gate 충족/모델 승인이 아니다. 최종 소스 집중 재시험 근거는 `target170-f2f3-final-20261018.log`다.

최종 소스 집중 결과는 **23 PASS / 0 SKIP,6.357초**다. 관련61개 이후의 추가 변경은 물리 계수가3000을 넘는 즉시 차단하도록 같은 상한 검사를 순회 중에도 적용한 것이며, 최종23개 재시험으로 확인했다.

후속에는 Root의 현재 원본·unenrolled·receipt 실제 inventory 감사와 새로운 pinned request 재생성/읽기전용검사를 수행해야 한다. 오류/null 실행 상태는 CLI 계약이며 UI endpoint는 바뀌지 않는다. 이해자료·공통 인계는 완료 코드/근거를 전달받은 Root가 같은 단위로 갱신한다.

## 왜 별도 entry인가

기존 157 계획 검증기, 160 자산 관측, 162 scene claim, 166 준비 controller와 167 inventory helper는 각각 `execution_supported=false`다. 이 값을 true로 바꾸어 과거 내부 관측을 승인으로 재해석하지 않았다. 새 entry가 명시 요청 SHA·고정 원본/원장·계획/inventory·live scene/window veto·배타 출력·기존 예산/429/최종 정산을 독립적으로 조합한다. 기존 일반 수집 CLI와 기본 호출 경로는 유지한다.

이 구현은 전체 모델 학습·운영 승인이나 나지 정확도 검증을 제공하지 않는다. 지역은 Banten, 고정 split은 val, 동년 Esri 약한 참조의 256 창이라는 좁은 목표다. 실제 요청별 로컬 검증과 원격 결과가 없으면 성공 수집으로 보고하지 않는다.

## 요청·사용법 계약

`run_targeted(project_root, request, expected_sha256, execute=False)`와 CLI `scripts/collect_targeted_bare.py --request <evidence/integration 내부 JSON> --expected-request-sha256 <digest> [--execute]`를 제공한다. 이 문서의 CLI는 계약 설명이며 작성 중 실제 원격 실행하지 않았다.

최상위 요청의 정확한 키는 `schema_version:1`, `plan`(157 계약), `ledger_ref:{path,sha256}`, `maximum_batches:1 또는 2`다. SHA는 일반 파일 bytes 해시와 다르며 `digest(request)`의 UTF-8 canonical JSON(sort_keys, ensure_ascii=false, compact separator, NaN 금지) SHA256다. 입력이 바뀌면 pin을 다시 검토해야 한다.

validate_request는 기존 고정 aggregate·실제 global ledger의 파일 pin, 4GiB 한도·429 회로·batch 예약 여유, 157 로컬 표적계획, 167 pending/raw-support inventory, 입력 재검사·기존 batch 키 부재·물리3000 상한을 확인한다. `execute=False`는 이를 읽기 전용으로 검사하고 live scene/window 미검증·학습 false를 반환한다. 누락·변경·겹침·기존 예약은 우회하지 않는다.

`--execute`는 기존 `global-ledger.execution.lock`을 배타 획득한 뒤 다시 검증한다. 출력 sources/patches의 두 batch leaf도 기존 파일이나 빈 디렉터리와 겹치면 거절한다. 배타 directory를 만들고 기존 CollectionLedger에 65MiB(COG64MiB+metadata1MiB) 상한을 먼저 예약한다. 기존 pending을 다시 실행·환불하지 않는다.

## 실제 소비 흐름과 최종 기준

기존 `run_two_workers`로 최대 두 worker, 기존 전역 2초 간격·공유 첫429 중단을 사용한다. worker는 기존 collect_windows에 169 callback을 전달하고, Root live guard가 선택 STAC scene의 연도·고정 split·AOI·공유 claim과 실제 window의 이전 support/다른 worker 겹침 및 B02 256/10m/계획 정합을 검사한다. SCL 사전선별은 scene 선택 전에 가능하며 이를 완전한 사전 네트워크 차단으로 표현하지 않는다. 거부 시 명시적인 src.read가 발생하지 않는 경계는 169 시험 근거다. header Range 비용은 이미 발생할 수 있다.

실제 선택 B02 witness가 있어야 기존 `materialize_patches`를 사용한다. 기존 영상/라벨/quality 정합·유효80%·주내95% 의미를 유지한다. materialized patch의 유효 픽셀 histogram에서 code8이 256개 미만이면 원본 파일과 lineage는 보존하되 `targeted_unenrolled_patches`로 worker receipt에 남기고 aggregate에 신규 등록하지 않는다. 이를 기존 quality_status를 임의로 바꿔 처리하지 않는다. 256개 이상이라는 조건은 나지0.5%·split별 기여5개·전체 과학검증을 충족했다는 뜻이 아니다.

정산은 기존 window-state COG 계상과 thread-local metadata 계상을 합쳐 수행한다. worker finally까지 실패해 실측을 신뢰할 수 없으면 기존 parallel executor의 unmeasured_worker_failure 경로에서 해당 65MiB 예약을 전액 유지해 정산한다. 첫429 회로를 원장에 남기고 새 제출을 중단하며 이미 시작한 worker는 기존 정산 절차를 따른다. 원본 scenes는 유지하고 새 등록 행만 append한다. 학습준비·독립 과학 정확도·전체 목표는 true로 바꾸지 않는다.

## 독립 시험의 정확한 범위

`tests/test_collect_targeted_bare.py`는 12개 시험이다. request SHA·aggregate pin·ledger pin drift 3개는 실제 validate_request의 앞단을 거치며, 원격 호출 없이 차단을 검사한다. execute 경계 시험은 **validate_request 반환값을 명시적으로 mock**하고 임시 data root에서 실제 CollectionLedger·run_two_workers를 실행한다. collect_windows와 materialize 결과도 mock이다. 따라서157/167의 전체 native 검증이나 실제 원격 다운로드 성공으로 확대하면 안 된다.

시험은 기존 execution lock 보존, dry-run 무예약, 빈 기존 출력 재사용 금지, 두 번째 출력 충돌 시 자기 첫 빈 예약만 해제, 기존 pending 전액/내용 유지·기존 scene 행 보존·신규 append, 256 미만 미등록/lineage 보존, B02 witness 없음의 patch0, 미측정 실패 전액65MiB 정산,429의 전역 원장 상태/공유 중단을 확인한다. misaligned B02와 픽셀 read0는 별도의 live guard12개·169 hook10개 근거와 구분한다.

초기 로그의 실패는 synthetic original/new row에서 scene_id가 누락된 fixture와 Windows cp949 기본 read_text를 UTF-8 산출물에 적용한 harness 문제였다. 후속 fixture를 정정했다. 중간에는 Root가 256 미만 처리 계약을 quality_status 변경에서 미등록 receipt 보존으로 개선하여 테스트 기대도 해당 최종 계약으로 수정했다. 초기·중간 로그를 보존하고 최종 근거는 `targeted-bare-dispatch-agent-final3-20261018.log`로 구분한다.

최종 집중 결과는 **12 PASS / 0 SKIP, 4.815초**다. `test_collect_targeted_bare test_targeted_live_guards test_targeted_collection_hooks test_data_parallel test_data_annual_budget` 관련 묶음도 **43 PASS / 0 SKIP, 5.993초**이며 `evidence/integration/targeted-bare-dispatch-related-20261018.log`에 보존했다. 모두 합성/임시원장 범위다.

## 인계와 남은 검증

실제 pinned request dry-run, 고정 예산 내 실제 표적 실행, 원격 선택 scene·B02 witness·header/pixel·품질·histogram·원장·기존 자료 보존을 독립 검산해야 실제 나지 수집 성과로 등록할 수 있다. 실제 확보 여부·분류 정확도·학습 승인·전체 나지 gate는 아직 이 독립 시험에서 검증하지 않았다. HTTP 수행은0이며 프로젝트 원본/모델/실원장은 변경하지 않았다.

새 endpoint나 사용자 클릭 동작을 추가하지 않아 이 단위 자체의 API/UI 연결은 필요 없다. 이후 실제 수집 결과는 기존 collection-status 집계와 검증 후보를 통해 반영하되 cohort 시점과 품질·승인 상태를 구분해야 한다. Root와 이해 에이전트는 “집행 연결은 합성 경계 시험을 통과했으며 실제 수집 성공은 별도 관측”으로 보고한다.

## 실제 단일 표적 실행과 후속 통합 검증

`targeted170-execute-launch-20261018.json`의 최대1batch 실행은 완료됐다. 독립 읽기검사 `targeted170-independent-20261018.json`은442.6789342초에 실제 적격1패치의 유효64908/65536(99.0417%)·주내100%·나지2199를 확인했다. 원래 로컬라벨의2411과 실제 유효 정렬 결과2199는 다른 값이다. 선택 STAC/B02 연결·B02와출력band1 일치·8source crop·기존1568행과4704파일SHA·pending2 전액136314880B 보존·계상3827633B 일치를 검산했다. 지원1162파일 중 자신의 새10개 외 과거 지원겹침0, 새scene 교차split0이다. 나지0.5%/기여5개·독립정답/학습승인은 여전히 미충족이다.

이 실제 실행은 초기entry d81f... 소스이며 이후 F2/F3 수정643a...가 실제 원격 사고에서 검증됐다는 뜻이 아니다. 후속 Root 묶음 `priority170-root-postguards-tests-20261018.log`은 **139실행/138PASS/1SKIP,40.869초**다. F1/173 및 나머지 표적/회계/QA 회귀를 함께 검사했고 symlink 권한1SKIP는 별도 mock 재분석 시험으로 범위를 구분했다. 최초 추가묶음 harness의 모듈명 따옴표 누락 NameError는 `priority170-root-postguards-harness-initial-20261018.log`로 보존하고 harness만 교정했다. 실제 새운영 physical inventory 안정관측은 다음표적 pinnedrequest 전 필요하다. 일반8차 수집은 별도 현재진행 작업이며 이번139시험의 실제 수집 성과에 포함하지 않는다.
