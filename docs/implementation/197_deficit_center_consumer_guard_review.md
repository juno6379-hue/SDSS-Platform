# 197 — 추가1024 공간후보의 소비 전 보호 연결 검토

상태: **VERIFIED_CODE_REVIEW / VERIFIED_REAL_METADATA_ONLY / 구현·집행 미승인**.196 native-ready 후 최신 셀·미예약 job 계수를 실제 읽기 전용으로 확인했다. 이번 작업은 구현 변경이나 수집 실행이 아니다. Root만196 실제 표적 수집을, toolbox_review만 종료 native 감사를 소유한다. 같은 collector·native·full167/179 지원 스캔을 추가하지 않는다.

## 쉽게 설명

지역·연도별 자료를28개씩 모으는 계획에는 두 문제가 따로 있다. 이미 정해 둔 네 장소의 작업을 모두 사용했다면 우선순위만 바꾸어도 새 사진을 받을 장소가 생기지 않는다.182는 새 장소를 제안했지만, 그 장소를 실제 수집기에 전달할 때 최신 원장·지원영상·실제 위성장면까지 연결하는 보호는 아직 완성되지 않았다.

그러므로 “후보 파일이 기존 형식검사를 통과한다”는 사실과 “현재 상태에서 그 후보를 수집해도 된다”는 판정을 나누어야 한다. 기존 후보의 승인flag를true로 바꾸거나 새ID만 붙여 같은 장소를 다시 독립 표본으로 세지 않는다.

## 코드에서 확인한 현재 연결

| 단계 | 구현과 확인 범위 | 남은 공백 |
|---|---|---|
| 182 제안 생성 | `propose_deficit_centers182.py:28`에서 source/경계/config/prior SHA·107개 당시source header·기하를 고정 | 당시 전체pending/SCL/B02/support 미검사; 현재 source가 바뀐 뒤의 실행 승인 아님 |
| 일반 extra job 생성 | `collect_training_parallel.py:52`의 `extra_jobs`가 기존 candidate validator를 호출하고 job/config 생성 | 182의 source/config/prior SHA를 현재 입력과 결합하지 않음; fullsupport/pending 결과를 요구하지 않음 |
| 기존 validator | `candidates.py:21`에서 경계SHA·중심·1024크기·기존center/상호기하·연도를 확인 | `collector_consumption_approved`는 반환 선언일 뿐 차단조건이 아님; source snapshot·추가proof 미검사 |
| 부족 우선순위 | `collect_training_priority.py:32`의 `_ranked`가 원장에 없는 job·현재부족만 선택 | 존재하는 장소를 순위화할 뿐 새 장소를 만들거나 지원재고를 검증하지 않음 |
| 일반 worker | `collect_training_parallel.py:248`에서 `collect_windows(...selection_context=...)` 호출 | `collection_guard` 미지정이라 선택scene/B02/window 실검사 callback이 연결되지 않음 |
| 기존 targeted guard | `targeted_live_guards.py:64`의 선택scene/split/AOI/asset/window 보호 | B02 크기가 `:128`에서256으로 고정;1024 job에 그대로 넣을 수 없음 |
| 일반 물리상한 | `collect_training_parallel.py:217`에서 현재 aggregate행+16×진행중 원본창≤3000 | history/미등재·부분 디스크패치까지 확인하는 targeted physical inventory와 다름 |

`collect_samples.py:234`는 선택적 `collection_guard`를 받는다. `:369`에서 선택scene을 알려주고 `:301`~`:306`에서 window hook을 전달하지만, 일반 worker는 그 인자를 주지 않는다. `service.py:392`~`:405`의 window guard는 COG header 이후·픽셀 `src.read` 이전에 호출된다. 이것이 실제 선택B02와계획창을 대조할 적절한 연결점이다. header/SAS/범위 확인까지의 메타/소량 HTTP가 이미 발생할 수 있으므로 픽셀 전 차단을 network0으로 확대하지 않는다.

일반 `candidate_coverage`의 scene-split 충돌 확인은 이미 받은 적격행의 종료판정이다. 원격 선택scene을 수집 전에 거부하는 공유 `SceneClaimRegistry`와 다르다. targeted 경로는 `collect_targeted_bare.py:200`/`:229`에서 registry와guard를 연결하지만 일반 extra job은 연결하지 않는다.

## 기존182 후보와 최신 부족의 불일치

182의 실제 제안은12:10 당시 source `03c58af…dd367`에서 만든4개다. 남동2024 두 장소, 고론탈로2024 한 장소, 고론탈로2025 한 장소이며 proposal SHA는 `e9dcd4a9c6ae994c9cb48fb7acbce3b217494279edfc0076b540e3860b88c565`다. `collector_consumption_approved=false`, `full_pending_support_inventory_verified=false`를 유지한다.

제안기의 기본 `TARGETS`는 `propose_deficit_centers182.py:16`의 남동2024·고론2024·고론2025다. 현재 조사 요청인 **남동2021·고론2022·동자바2025**는 이 기존 제안의 연도/주에 없다. 이미 제안된 고론2024의 부족이 해소됐다면 자동으로 고론2022용으로 바꾸어 소비하면 안 된다. 새 명시 셀과 새 source pin에서 별도 제안/검토해야 한다.

## 최신 metadata dryrun —196 native-ready 후 완료

196 실행 중에는 metadata job dryrun과 새 수량 확정도 하지 않았다.196 native 완료·Root ready와 현재source/ledger SHA를 받은 뒤에만 다음 읽기를 수행한다.

- 기존 `v2_jobs(base,4)`의 순수 job 생성과 원본/원장 JSON 계수만 읽는다. `collect_training_parallel.main`은 dryrun이라도 계획파일을 쓰므로 실행하지 않는다.
- 남동2024/2021·고론2022/2025·동자바2025 각각에 대해 g00~g03 네 key의 settled/pending/미예약 수와 이미적격 공간prefix를 구분한다. 미예약이어도 기존적격 공간이면 신규작업으로 세지 않는다.
- 182 proposal/config/prior/경계의 지문과 선언을 읽고 기존 `extra_jobs`가 false 승인 상태에서 job shape를 만들 수 있는지만 로컬 관측한다. 실제 소비·예약·HTTP·지원/native스캔은 하지 않는다.

위 순수 함수와 metadata 읽기를 실제 실행했고 source/ledger/config/proposal/경계/prior 지문이 전후 같다. `evidence/center197-contract-review-20261018.json`에 코드8개 지문·20개 기본job 상태·기존lane-B·182 후보의 실제 job shape와 판단을 기록했다.

고정 source SHA는 `1a12b7bca384dd09d73a04cc31df21f75377fc34c332b501a6ee37508dd46fb5`, ledger SHA는 `f49d7e778359c1f60743f617edb599fe2ba3170e9e9243a3459211aa4bc9b0fe`다.196 후 **manifest1,667행 / 저장 적격1,333 / 부족33**에 한정한다. 별도196 native 인계의 실물1,668과 manifest행수를 구분하며,197은 디스크 물리패치를 재감사하지 않았다.

| 부족 셀 | 적격 /28 | 부족 | 기본4개 settled | 기본 미예약·가용 | 기존lane-B 미예약·가용 | 기존182 해당 후보 |
|---|---:|---:|---:|---:|---:|---:|
| 남동2024 | 11 /28 | 17 | 4 | 0 | 0 | 2 |
| 남동2021 | 27 /28 | 1 | 4 | 0 | 0 | 0 |
| 고론2022 | 24 /28 | 4 | 4 | 0 | 0 | 0 |
| 고론2025 | 18 /28 | 10 | 4 | 0 | 0 | 1 |
| 동자바2025 | 27 /28 | 1 | 4 | 0 | **7** | 0 |
| 합계 | | **33** | **20** | **0** | **7** | **3** |

기본 v2는6주×6년×4장소인144job이다. 요청한5개 부족셀의 g00~g03 총20key는 전부settled이며 pending/미예약0이다. 남동·고론만 명시 우선으로 둔 순수177 기본job preview는 각각 `BLOCKED_NO_AVAILABLE_DEFICIT_JOB`, 선택0을 반환했다. 우선순위 변경만으로는 장소가 생기지 않는다.

단, 동자바2025에는 기존lane-B8장소 중1settled·7미예약 후보가 남는다. 기본job만 소진됐다는 이유로 이 셀에도 새182 장소가 꼭 필요하다고 설명하면 안 된다. 기존lane-B를 포함한 순수177 preview는 동자바2025 `boundary-01`/`boundary-02`를 선택한다. 이것도 후보 순위일 뿐 현재 support·실B02·품질 검증이나 실행 승인이 아니다. 남동·고론은 기존lane-B 자체가0이므로 새로운 공간계획이 필요하다.

182의4job은 모두 미예약이지만 그중고론2024는 현재36적격으로28바닥을 이미 넘겼다. 남은3개는남동2024 두 장소·고론2025 한 장소이며, 남동2021/고론2022에는제안이없다. 당시182 source와현재 source SHA는 다르다. config/prior SHA는현재와같았고경계도일치했다. 실제로순수 `extra_jobs`는 **source불일치·collector_consumption_approved=false·full_pending_support_inventory_verified=false 상태에서도4job을생성**했다. 이것은예약/집행0의계약 관측이며 안전한소비가완료됐다는뜻이아니다.

기존pending2개/계상136,314,880바이트는보존했다. 새예산·원본·원장·lock쓰기0,네트워크·collector main·수집·native·전체167스캔0이다. 일반parallel main은 dryrun도계획파일을쓰므로호출하지않았고순수함수만사용했다. 실제셀/미예약계수의새시험을제품회귀시험PASS건수로세지않는다.

## 다음 작은 내부 구현 제안 — 아직 PLANNED

첫 단위는 **실행하지 않는 명시 추가center 소비 계약**이다. 예시 파일 소유는 `backend/app/data/deficit_center_consumer.py`, `tests/test_deficit_center_consumer.py`, 별도 구현문서다. 기존185/195/UI 파일과 다른담당 collector 실행코드는 건드리지 않는다.

내부 Python API 예시는 `prepare_deficit_center_consumption(root, request)`다. request에는 schema_version1, proposal/source/ledger/boundary/config/prior의 명시 path+SHA refs, 선택 spatial_window_id+year 목록, maximum_batches1~2를 정확히 둔다. 실제 추가1024창·16개 명목패치·고정split·현재셀 부족·이미예약 key·현재src/config/prior pin을 검산한다. 오래된182 source의 지문을 현재 지문으로 덮어쓰지 않고 `SOURCE_SNAPSHOT_STALE`로 닫는다. 새 proposal/검토 증거가 필요하다.

별도 소단위로182의기존기본 `TARGETS`를보존하면서 **명시 부족셀 목록 선택인자**를추가할수있다. 새소유는 `scripts/propose_deficit_centers182.py`의선택범위·`tests/test_propose_deficit_centers182.py` 추가시험뿐으로제한하고, 기존107header감사를중복실행하거나진행중collector와운영스캔을겹치지않는다. 남동2021·고론2022는명시목록에있어야하며고론2024의장소를다른연도로몰래재해석하지않는다. 실제새제안의fullsupport/라벨/품질은후속승인범위다.

반환은 job shape·고정입력 지문·차단이유·필요 후속proof를 담되 execution_supported/full_support_verified/live_b02_verified/physical_capacity_verified/ready_for_training은 모두false다. 네트워크·Store·원장변경·실행·권한 승인을 하지 않는다. 실제182의 stale/cohort·승인false를 우회해 즉시수집하게 만드는 단위가 아니다.

그 다음 별도 승인받은 단위에서만 다음 보호를 연결한다.

1. fresh 전체167 inventory를1회 확인하고 shared `TargetedWindowClaims`로선택센터와pending/과거지원/상호창을검산한다. 캐시의source/ledger와현재핀을검산하고순차관측한계를보존한다.
2. **1024 전용 live guard**에서 선택scene의동년/고정split·정확선택B02 URL·실제native10m1024×1024·계획bbox/footprint 허용오차를검산한다. 기존256 guard를묵시적으로1024허용으로바꾸지않는다. SWIR의20m/여유픽셀과후보선정SCL·확대라벨의역할을구분한다.
3. physical inventory가 history/미등재패치/부분산출물을포함하고 `physical_count+16*inflight`를3000과대조한후만예약한다. 계획/입력은공유lock안에서다시확인하고출력/기존key충돌은실행전에거부한다.
4. 기존단일coordinator·4GiB·2worker·전역2초·첫429중단·원pending전액보존·고정split·실품질80%/주내95%를유지한다. 새source및job승인결과와테스트/문서/이해자료를같은단위로마감한다.

필요 시험은 stale source/ledger/config/prior·year/split변조·해소된셀·기예약/기존성공공간·출력별칭·false승인보존·pure무IO를첫단위에둔다. 후속guard단위는 실제작은GTiff/모의COG에서1024허용/256및truncated/CRS·URL·AOI변조거부·SCL/라벨역할·서로다른split의scene/동시claim·실제픽셀read전차단·physical2990+16거부·pending보존·429후추가요청0을검증한다. 시험안을실행된시험이나보호연결완료로표시하지않는다.

## 문서·UI·인계

이번은 내부 코드/메타계약 감사라 새화면/API변경이 필요없다. 다음 실제집행은Root의별도명시소유이며197이collector를추가시작하지않는다. 문서·작은JSON·현재미연결범위·구현/시험안을Root에게전달하고공통원장·이해자료/대본/FAQ/INDEX는해당담당이갱신한다. 전체개발·10분보고·나지/독립정답·학습/운영승인후속은계속된다.

최종 JSON은 **20,526바이트 / SHA256 `50837ad8c97203b1d459141ab7e607f4efd499aa3cc6487e555d9998f8ece4fd`**다. 기본grid만읽은최초지문과기존lane-B를추가구분한중간지문은JSON에출처로보존했다. `additional_spatial_candidate_needed_beyond_default_jobs`는기본4장소소진만뜻하고,기존lane-B까지포함한최종신규계획필요여부는 `new_spatial_plan_required_beyond_existing_default_and_lane_B`를따른다. 동자바2025는후자가false이므로기존7미예약후보보호검토가우선이다.
