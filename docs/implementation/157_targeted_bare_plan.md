# 157 — 반텐 256 나지 표적창의 로컬 계획 검증

## 2026-10-18 후속175 — 로컬 계획 범위 확장

아래157본문은초기반텐판본의구현/시험이력이다. [175](175_six_province_local_target_plan.md)에서같은helper의로컬검사를6주고정split·각주경계/AOI·실제미터10m격자로확장하고기존반텐job/key/config계약을보존했다.집중16/관련77PASS이며성공도execution_supported=false다.다른주train/test실제실행은174 B/C의liveguard/consumer검증이남아있다. 175의합성검사를157의과거실자료관측으로확대하지않는다.

상태: `TESTED_SYNTHETIC` 및 `VERIFIED_REAL_LOCAL` 읽기 관측. 신규 `backend/app/data/targeted_bare_plan.py`는 명시한 로컬 계획을 실제 저장 라벨과 영상 헤더에 대조하고 **실행할 수 없는 job 제안**을 반환한다. 기존 collector·1024 후보 validator·원장·API/UI를 변경하지 않았다. 이 단위의 실제 HTTP·학습·추론·Registry 쓰기는 0이다. 일반 부족 셀 수집은 Root의 별도152 실행이다.

## 목적과 입력

[152 표적 수집 RFC](152_targeted_bare_collection_rfc.md)의 라벨 crop17개/256창10개는 독립된10개 공간이나 실제 Sentinel 품질 적격 패치가 아니다. 같은 중심1024창은 기존 영상과 겹친다. 기존1024 validator를 바꾸거나 window_size를 속이지 않는다.157은 첫 단계인 명시 계획·라벨 바이트/헤더·동년 출처 선언·좌표·현재 목록 영상과의 겹침을 검사한다. 계획만으로 나지 수집 전체를 완료했다고 보고하지 않는다.

`prepare_targeted_bare_jobs(project_root, plan, base_config)`가 내부 진입점이다. 입력 dict는138의 strict builtin bounded JSON 사본을 사용한다. cycle·surrogate·비유한 수·53bit 밖 정수·깊이16·8192노드/256KiB 범위 초과 등을 거부한다. 전체 upstream 스키마나 RFC의 모든 미래 실행 조건을 구현한 것은 아니다.

plan은 RFC exact7 키 `schema_version/kind/proposal_ref/current_manifest_ref/boundary_ref/policy/targets`, 정확한 int1, kind `TARGETED_BARE_256_COLLECTION_PLAN`을 요구한다. targets는 caller가 선택한1~2개이며 target_id 중복·반텐/val 이외·2020~2025 이외·bool 연도를 거부한다. target exact12와 policy exact6, window256/source code8/minimum bare256/valid0.8/inside0.95를 검사한다.

각 `{path,sha256}`는 프로젝트 상대경로와 lowercase64 SHA다. proposal만 `evidence/integration`, 나머지는 `data` 아래에서 읽는다. root/상대경로/링크·변경 감시·stream 상한은123 내부 reader를 재사용한다. source label·목록 영상·aggregate는 각각64MiB, proposal/경계2MiB, source annual report8MiB 상한이다. 전체 영상 목록의 누적 I/O·JSON/RSS/CPU 비용을 제한하는 sandbox는 아니다. 실패 출력에 원문 경로/예외를 넣지 않는다.

## 실제 로컬 검산

제안 JSON의 명시 ranked index와 주/split/연도·crop 경로/SHA·window offset·bare 개수를 교차대조한다. source annual report의 같은 crop 경로/SHA, year, 정확한 정수 label_year, label source URL의 동년 `/lcYEAR/` 선언도 검사한다. URL 조회나 기관·촬영 진실 인증은 아니다.

같은 고정 라벨 바이트를 GTiff로 열어 EPSG:32748·north-up10m·1band 정수형·원래 grid·256×256 범위를 확인한다. 실제256창의 source code8을 세어 caller/제안과 정확히 맞으며256 이상인지 본다. model class7과 혼동하지 않는다. 원래 affine의4corner와 caller native polygon, 해당 corner의 lon/lat envelope와 caller bbox를1e-8도 이내로 대조하고 반텐 경계 inside 면적 비율0.95 이상을 요구한다.

고정 aggregate의 `scenes`와 `historical_noneligible_patches`에서 patch `image_path`/SHA 및 `source_window.path`/SHA를 중복 제거한다. 고정 파일 SHA와 실제 GTiff 헤더를 읽고 target CRS로 변환한 polygon과 양성 면적 겹침을 거부한다. 적격 여부·연도·province와 무관하고 새 targets 서로도 적용한다. cross-year 거부는 반복 위치를 독립 공간으로 부풀리지 않는 보수적 정책이며 scene split 누출 검사와 다르다. 접촉 면적0은 허용한다.

이는 **해당 aggregate에 명시된 patch/source 영상만** 포함한다. 별도 report만 있고 목록에 빠진 영상·합산 전 영상·pending 전체 예정 footprint·SWIR/SCL 보조 원본·실제 선택될 Sentinel grid는 검증하지 않는다. `listed_image_overlap_checked`를 모든 과거/예약 자료와 겹침0 또는 실행 안전성으로 확대하지 않는다.

## 출력과 실행 차단

출력 exact16, scope `LOCAL_TARGETED_BARE_256_PLAN_ONLY`다. 로컬 성공도 `LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED`, issue `EXECUTION_GUARDS_NOT_CONNECTED`다. 라벨 바이트/현재 목록 겹침 검산만 true가 될 수 있다. `execution_supported`, `actual_quality_eligible`, `scientifically_verified_bare`, `pending_footprints_verified`, `source_scene_split_verified`, `training_ready`는 항상 false다.

`job_proposals`는 고정 plan SHA 기반 key, 반텐 val, nominal_patches1, window256·6논리밴드·동년 Esri·기존 유효율/예산/재시도0 설정과 source priority8을 담는다. 정책명도 `PLAN-ONLY`이며 기존 coordinator에 전달하거나 호출하지 않는다. 후속 구현은 실행 guard를 확정한 뒤 이 제안을 재검증해야 한다. 실패는 고정 issue·빈 targets/jobs·false 관측으로 닫고 부분 성공 job을 노출하지 않는다.

## 시험과 실제 로컬 근거

```text
set PYTHONPATH=.runtime;.;backend;tests&&python -m unittest test_targeted_bare_plan -v
```

최종 `targeted-bare-plan-agent-final2-20261018.log`: **8 PASS / 6.799초 / exit0**. 실제 Temp GTiff256창의65,536개 code8, native/WGS 좌표·경계·동년 lineage·job 제안·입력/파일 불변을 확인했다. bool/여분키/수량/1024/grid 선차단, SHA 변경, 다른 연도의 비적격 영상과 실제 겹침, 동일 위치 두 연도 target 겹침, bbox/window/count/year 불일치, 경로 탈출·출력 비누출, 다른 CRS·VRT/opaque 라벨의 새 pin을 거부했다. 첫7 PASS/6.331초 및 guard7 로그는 별도 보존하며 합산하지 않는다.

실제 저장 라벨 첫 target 검증은 별도 `targeted-bare-plan-local-20261018.py/json/log`로 완료했다. 변경 중 aggregate는 원본을 고치지 않고 신규 `data/targeted-bare-plan-157/annual-window-report-snapshot.json` 55,742,976B로 한 번 고정했다. SHA는 `7eac5a54cce152f1f3163e35e8565217b6cbef61b86068150209bb39fa3a9bbe`이며 검색 당시 historical aggregate `cdc374…`와152 round1 완료 시점 `fd00a2…`를 구분한다. 새 request JSON은 `targeted-bare-plan-local-20261018-request.json`이다.

10:22:24 KST 결과는 **110.0058014초 / exit0 / 로컬 계획 검산 성공·실행 차단**이다. 명시한 반텐 val2020 첫256창에서 실제 약한 라벨 code8 **2,411픽셀**, 경계 inside **1.0**, 고정 목록의 실제 patch/source 영상 **1,526개**를 SHA·헤더로 확인하고 양성 면적 겹침을 발견하지 않았다. source label SHA는 `a18fd0…04541`, plan SHA는 `fec0bbef67763d41072f15f2f835addfac818ced290d2285a9e64aac76948037`이다. source 라벨·source annual report·proposal·boundary는 전후 SHA가 같고 원장/lock/기존 파일 쓰기는0이다. 새 snapshot과 증거만 생성했다. 원본 aggregate는 Root 수집으로 계속 바뀔 수 있으므로 이 결과를 최신 전체 자료의 동시 snapshot으로 표현하지 않는다.

이 성공은 `LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED`이며 issue `EXECUTION_GUARDS_NOT_CONNECTED`가 그대로다. 실제 맑은 Sentinel scene 선택·영상 수신·신규 품질 적격 패치·bare 학습 차단 해소는0건이다.10개 전체 후보의 독립성이나 생존 수량을 검증하지 않았다. 실행 guard가 연결되면 최신 자료와 예약 영역에 다시 대조해야 한다.

## 남은 일과 화면 영향

운영 실행에는 pending/보조 footprint 인벤토리, 다른 split의 새 scene veto·공유 claim, 실제 B02/보조 grid 검사, target 전용 배타적 출력, 최종 quality/AOI 적용 후 bare≥256과 기존 reserve/terminal/finalize 연결이 필요하다.5개 기여 패치·split별 bare0.5%·독립 정답·학습/모델 승인도 별도다.

실제 집행 연결은 다음 순서로 인계한다. 앞 단계가 빠진 채 `job_proposals`를 일반 collector에 전달하지 않는다.

1. 현재 aggregate뿐 아니라 합산되지 않은 source annual report·기존 pending의 전체 예정/부분 영역·SWIR/SCL 보조 영역까지 고정 인벤토리로 만든다. 불명 영역을 안전하다고 추정하지 않고 차단한다.
2. STAC 선택 전에 scene→split 이력을 대조하는 veto와 두 worker의 검사/claim을 하나의 공유 잠금 안에 결합한다. 같은 공간의 연도 반복 거부와 split 누출 veto는 각각 검증한다.
3. 첫 B02 수신 직후 실제 native256 기하·snapping·기존/예약 영역 겹침을 재검산하고 나머지 밴드의 물리 보조 범위도 대조한다. caller bbox와 실제 COG crop을 같은 것으로 간주하지 않는다.
4. target-only 옵션·새 경로 배타적 소유·nominal1 상한·기존 공유 원장 reserve/work/terminal/finalize를 연결한다. 기존1024 모드·같은 예산/429·재시도 금지·미정산 보존을 유지하고 파일쌍 원자성을 주장하지 않는다.
5. 실제256 결과의 동년 라벨·동일 grid·inside≥0.95·valid≥0.8·valid 안 source code8≥256을 검산한 패치만 집계한다. 미달 raw/계측 근거는 보존하고 비용을 지우지 않는다.
6. Temp 실제 GTiff와 명시 Mock HTTP의 전체 CLI 연결·중간 장애·누출·겹침·전송 정산 시험을 마친 뒤 Root가 최신 고정 계획 최대1~2개만 명시 실행한다. 다운로드 시도/영상 수신/표적 적격/학습 차단 해소를 각각 보고한다.

새 내부 계획 helper만 있으므로 HTTP/UI/main과 기존 화면을 변경하지 않았다. frontend/build/browser는 이 단위의 수락 범위가 아니며 Root의 현재 수집/UI와 중복 실행하지 않는다. 완료 코드·시험·차단 범위를 Root가 이해 담당에게 인계하고 공통 원장/설명자료를 갱신한다.
