# 217 — manifest 용량과 전처리 규모 제한 검토

상태: **VERIFIED_CODE_REVIEW / 확장안 PLANNED**. 현재 제품 소스코드만 읽었다. 실데이터 JSON·래스터·원장·로그 재독, native/전체 스캔, profiling, HTTP, 테스트 실행, 제품 수정은 모두 0이다. 아래 현재 파일 크기는 Root가 전달한 66,166,696바이트를 사용했다. 207의 실제 지연 원인을 확정하는 문서가 아니다.

## 현재 왜 살펴봐야 하나

source JSON 66,166,696바이트는 64MiB=67,108,864바이트 제한의 약 98.60%다. 여유는 **942,168바이트**뿐이다. 새 패치마다 반복되는 source/window/품질/정규화 metadata의 크기가 달라 한 batch를 더 받아도 안전하다고 보장할 수 없다. 파일 크기만큼만 데이터를 보유한다는 뜻도 아니다. JSON decode와 Python 객체·복사·직렬화는 별도의 메모리/시간을 소비한다.

이 제한은 다운로드 제한과 별개다.

| 제한 | 대상 | 이번 검토의 처리 |
|---|---|---|
| JSON source/candidate 64MiB | 로컬 manifest를 복사·검증·계획·게시·QA할 수 있는 크기 | 향후 명시 128MiB profile 검토 대상 |
| COG 64MiB + metadata HTTP 1MiB | 한 수집 batch의 원격 본문 전송/예약 | 그대로 유지 |
| 추가 전역 예산 4GiB | 여러 실행이 공유하는 원장 누적 예약/사용 | 그대로 유지 |
| 물리 patch 3000 | 등록·미등재·비적격·부분실물을 포함하는 실제 수집 상한 | 그대로 유지 |

`64MiB`라는 숫자가 같아도 서로 다른 계약이다. JSON을 128MiB로 허용해도 새 다운로드 권한·전송량·물리 patch 수는 늘어나지 않는다.

## 코드에서 확인한 cap 경로

아래 행 번호는 검토 당시 코드 기준이며 실제 소비 함수/상수가 판단 근거다.

| 소비 경로 | 현재 제한과 처리 | 후속 증가 시 충돌 |
|---|---|---|
| `scripts/prepare_priority_candidate164.py:copy_pinned` | 기본 cap64MiB. 복사 전 stat/hash, 1MiB chunk 독점 생성, 복사중 크기·identity·SHA 및 전후핀 검산 | source가 초과하면 첫 snapshot 복사에서 중단. `prepare()`는 이 기본값을 사용한다. source QA 전 새 작업 폴더가 남을 수 있다. |
| 같은164 `prepare` | snapshot을 `read_text/json.loads`하고 source `assess`→split plan→strict materialization→stage→candidate QA 순서. 단독 JSON parse 자체의 row/node 상한은 없다. | 복사 cap만 바꾸면 이후 source/candidate cap에서 다시 막힌다. 최상위 prepare에 총행/노드 경계도 필요하다. |
| `scripts/find_bare_targets173.py:discover`, CLI `main` | manifest64MiB, boundary2MiB. scenes+historical 합3000행. 라벨 개별64MiB/누적768MiB, 최대256파일·32768창·128후보. CLI와 함수 각각 source 전후핀 검산 | selectedrefs로 2라벨만 읽어도 전체 source64MiB 입력은 필요. 라벨별64MiB를 JSON확장과 함께 올리면 안 된다. |
| `scripts/propose_deficit_centers182.py:propose` | source64MiB, boundary/config/prior 각각2MiB, 합산3000 source행. 최대256 header파일·header payload2GiB·주당100000 grid·최대4후보/주당2 | source 초과가 header/공간검사보다 먼저 차단. header 처리에는 `_snapshot(...,copy_bytes=True)`로 실제 bounded 파일바이트를 읽는 비용도 있다. header-only 목적이 곧 최소I/O는 아니다. |
| `backend/app/data/deficit_candidate_guard.py` | current source는 이미128MiB, scenes+history≤3000. active pins·물리 cap과 pending/support 검사 | 182의64MiB와199의128MiB가 이미 다르다.199가128을 읽을 수 있어도 제안 생산/164후처리가64로 막힐 수 있다.200은199를 소비하므로 일관된 profile을 함께 검토한다. |
| `backend/app/data/targeted_bare_plan.py:prepare_targeted_bare_jobs` | current manifest64MiB, proposal2MiB, lineage8MiB, label/raster 개별64MiB. strict TOP/target/window/geometry/declared count 검사 | 원격 표적도 source JSON 한계를 통과해야 한다. lineage/래스터 cap은 source와 분리해야 한다. |
| `backend/app/ml/candidate_materialization.py:POLICY` | source/candidate 입력64MiB, candidate 출력64MiB, readiness16MiB, saved_plan/plan4MiB, depth32. 입력읽기→계획 재계산→쓰기→candidate exact roundtrip→receipt | source가64미만이어도 생성 candidate가 output64를 넘으면 실패. 신규 partial 산출물 보존, receipt 미완료를 성공으로 취급하지 않는다. |
| `candidate_staging.py:stage_split_candidate` | materialization POLICY를 가져온다. receipt64KiB·declared row≤100000. package입력/출력 pins·재검증→독점복사→roundtrip | package와 staging profile이 다르면 유효 package를 다음 단계가 거부한다. |
| `candidate_readiness_qa.py:CAPS`, `_stage`, `_report` | candidate64MiB, old_readiness16MiB, policy1MiB, stage receipt64KiB. 선언 source/candidate≤100000행, 적격 count≤3000, verified_files≤10000, blocker≤10000 | stage를 올려도 candidate QA 입구와 package output byte검사가 남는다. 100000 metadata행 허용과3000 실제수집 cap은 동일하지 않다. |
| `candidate_qa_comparison.py:_ref` 및 output 검증 | 실제 읽기는 저장 QA report2개 각16MiB/receipt2개 각64KiB뿐. 그 안의 manifest 참조 bytes는64MiB 이하로 검증. capture scene≤2000 | manifest를 읽지 않는 reader도128MiB 참조를 거부할 수 있다. `_ref`만 고치면 output byte검사 등 다른 literal이 남는다. |
| `candidate_qa_comparison_api.py` | response schema의 source/candidate 선언행100000·candidate capture scene2000; 동시 요청 semaphore1 | reader와 응답 schema가 함께 맞아야 한다. 이번 설계로UI/schema가 바뀐 것은 아니다. |
| `readiness_connectivity_lineage.py` | manifest64MiB, report16MiB, depth32, raw row100000·capture scene2000·string4096 | source핀 기반 출처 진단도 별도 cap을 가진다. |
| `recovery_boundary.py:MAX_MANIFEST_BYTES` 및 그 importer | manifest64MiB; `_read_bounded`는64KiB chunk/stat/전후 안정성·depth검사 | 이 공용상수의 일괄 변경은 recovery 전체 의미를 넓힌다. profile을 전달하는 소비별 변경이 필요하다. |

일반 `readiness.assess()`는 inventory SHA 뒤 `json.loads(path.read_text())`로 manifest 전체를 읽으며 이 지점에 source byte/row/node preflight가 없다. 상위164/QA wrapper가 cap을 제공한다. 단독 실행 경로까지 안전하다고 간주해서는 안 된다. `scripts/run_experiment.py`를 통한 candidate QA도 wrapper와 gate의 역할을 구분해야 한다.

## 노드·깊이·I/O 제한은 서로 다르다

`split_json_io.BoundedJSONIO`는 role별 byte cap·UTF8/BOM/NUL·중복키·비유한 숫자·depth를 검사한다. 허용되는 policy 최대 byte값은256MiB, depth는1..64이며 materialization은32를 쓴다. **현재 JSON 전체 노드 수나 여러 read의 누적 I/O 바이트 상한은 없다.** `_tree()`가 트리를 순회하고 `read()`는 chunks→joined bytes→text→객체를 만든다. `verify()`는 이전 모든 입력을 `read()`로 다시 읽고 파싱한다. 복수 검증단계의 총 작업량이 단일파일 cap보다 클 수 있다.

`per_scene_normalization_files.MAX_JSON_NODES=65536`은 그 모듈의 JSON 검증 helper가 사용하는 제한이다. `_snapshot(...,copy_bytes=True)`만 가져와 쓰는173/182/175/199의 `_json()`에 자동으로 적용되는 제한이 아니다. 같은64MiB snapshot이라는 이유로 전체 manifest 노드가65536으로 제한된다고 표현하면 잘못이다.

`readiness_connectivity_envelope`에는 별도16MiB·300000노드·깊이 제한이 있다. 이는 순수 진단 envelope 계약이며 source JSON budget과 다르다. source를128MiB로 올린다고 envelope까지 올릴 이유가 없다.

connectivity adapter의 기본은2000scene·1000000 bbox쌍·10000저장 edge다. 실제로 `n(n-1)/2`가 쌍 예산을 넘으면 `NOT_CAPTURED_BUDGET`를 반환한다. 모든 scene이 쌍 계산 대상이면1414개는998991쌍,1415개는1000405쌍이므로 **기본 쌍 cap은2000scene보다 먼저 작동할 수 있다.** witness hard cap은2000000쌍이라2000개1999000쌍은 들어가지만3000개4498500쌍은 들어가지 않는다. QA적격 patch수와 capture에 전달되는 appended scene수는 구분해야 한다. 지금207의 실제 capture 상태나 지연 원인을 이 산술로 추정하지 않았다.

`readiness.assess`에는 raster/hash/정렬·품질·클래스·연결성 계산이 있고164는 원본 QA와 후보 QA 둘 다 수행한다. strict metadata 단계도 plan 재계산·내용 완전동등 비교·후보 직렬화·반복핀 검사·복사를 수행한다. 이들은 **측정할 후보 구간**일 뿐이다. 207이 어느 구간 때문에 오래 걸렸는지는 profiling/단계 실측 없이 단정할 수 없다. 반복 검산을 제거하면 빨라질 것이라는 추측만으로 안전성 검사를 생략하지 않는다.

## 향후128MiB / 3000행 확장안

제안은 기본 동작을 유지하고 명시 `MANIFEST_JSON_128M_3000_V1` resource profile을 새로 도입하는 것이다. source/candidate metadata 역할만134,217,728바이트로 확장하고 scenes+historical 총3000행을 엄격히 검사한다. physical cap3000과 최종 적격 gate는 그대로다. profile/digest를 plan·package·stage·QA receipt에 고정해 다른 profile이 섞이면 중단한다. 무조건 global 상수64→128 치환을 하지 않는다.

1. **같은 profile을 끝까지 전달:**164 snapshot/strict parser→split planning/validation `io_policy`→materialization input/output→stage→candidate QA→저장 reader 참조/schema까지 전파한다. 173·182·175·199는 같은 resource helper의 source-role만 opt-in 사용한다. 모든 TIFF/label/support64MiB, readiness16MiB, plan4MiB, 작은receipt64KiB, metadata HTTP1MiB는 유지한다.
2. **추가 구조 budget:**3000행만으로 한 행의 거대한 nested metadata를 막지 못한다. source/candidate별 max_nodes·max_depth32·bounded key/string/container를 profile에 수치화해야 한다. 적절한 노드값을 여기서 임의 확정하지 않는다. 합성 최대형과 승인된 실제 cohort의 저장 통계로 node/row/string/serialized 바이트를 측정한 뒤 명시 상한을 정한다. 너무 작은 기존65536을 단순 재사용하거나 무한값으로 설정하지 않는다.
3. **공용 primitive 계약:**`BoundedJSONIO` profile schema 확장은 max_nodes/max_rows/누적 read bytes 또는 검증된 목적별 budget을 명시한다. parse 전 token/깊이/바이트 제한과 parse 후 strict 구조 검사를 연결한다. 현재256MiB primitive ceiling은128허용에 충분하지만 그것만으로128 profile 지원 완료가 아니다. 작은 receipt와 모델/보안 helper의 범위를 넓히지 않는다.
4. **반복I/O 보존과 계측:**context별 read/verify 횟수·입력/출력 누적바이트·parse/plan/compare/encode/copy/hash 시간·peak RSS·asset 수를 계측한다. read cache를 제안한다면 immutable raw/digest/stat/descriptor binding·mutation detection을 보존하고 순차 스냅샷을 다중파일 원자 snapshot이라 주장하지 않는다. 검산 횟수 변경은 별도 검토한다.
5. **QA 진단 한계 유지:**3000행 허용이3000scene connectivity pair 진단의 완전 캡처를 의미하지 않는다. 첫 확장은 기존 진단 budget 초과를 정직하게 NOT_CAPTURED로 유지할 수 있다. 완전 캡처가 요구되면 spatial index/연결성 동등성·메모리·최대4498500쌍의 비용을 별도 설계/측정하고 adapter/witness/lineage/comparison/API를 함께 수정한다. 품질 gate 자체를 diagnostic 결과로 우회하지 않는다.
6. **collector 게시 전 규모 검산:**새 물리 수집이JSON으로 소비되지 못하는 상태를 피하려면 Root collector가 예약 전 현재 profile/행수 및 신규metadata 직렬화의 보수적 여유를 확인하고, 실제 게시 직전 exact serialization을 검산해야 한다. 가변 원격 metadata의 완전한 크기 예측은 불가능하므로 초과 시 새 source/result를 보존하고 aggregate 미게시 상태를 별도 terminal로 남긴다. 기존 aggregate 삭제·행잘라내기·과거pending환불은 하지 않는다. 이 추가 collector 연결은 별도 소유/시험이며 이번문서에서 구현하지 않았다.

128MiB에서도 3000행의 모든 상세 원본 metadata가 항상 들어간다는 보장은 없다. 장기적으로 반복 source metadata를 SHA고정 sidecar로 정규화하고 patch행에는 참조를 두는 schema 변경을 검토할 수 있다. 이는 manifest exact-row 동등·lineage·reader·package 계약을 바꾸므로 이번 cap확장과 함께 즉흥 적용하지 않는다. 먼저128MiB profile의 실제 상한과 사용자 설명을 정한다.

## 필요한 시험·실측·운영 인계

**합성/Temp 회귀:**64MiB−1/정확64/64+1,128−1/정확128/128+1을 실제 UTF8 바이트로 검사한다. 기본모드는64+1 거부, 명시 profile은128까지 허용,128+1은 큰 read/출력 전 거부해야 한다. 멀티바이트·CRLF/직렬화 증가·output cap·3000/3001 합산행·깊이/노드·중복키·NaN/bool·큰 string/단일행·alias/reparse·grow/truncate/mutation·partial쓰기·기존 receipt 재사용을 시험한다. threshold fixture가 크므로 필요한 boundary test만 제한된 subprocess로 실행하고 무의미한 전체 반복을 하지 않는다.

**의미 있는 연결 시험:**164 snapshot→plan→materialize strict roundtrip→stage→candidate QA(Mock gate)→reader/API schema까지같은 profile을 유지한다. old default의 plan/key/metadata와 false authorization flags는 동등해야 한다.173 selectedrefs/182/199/175의 source-role profile 검증도 포함한다. JSON확장으로 COG/metadata/4GiB/2초/첫429/physical3000/pending/모델split 상수가 바뀌지 않았음을 시험한다.

**대표 성능 실측:**우선 합성1699/3000행의 최소·중간·최대metadata를 새Temp 파일로 만들어 parse/strict 단계별 wall/CPU·peak RSS·누적I/O와 산출bytes를 기록한다. native를 Mock한 metadata 비용과 별도 승인된 실제 QA의 raster 비용을 분리한다. 실제 데이터 실측은 Root가 고정 source/reader 시점·단일 담당·상한/timeout·중단/부분보존 정책을 승인한 뒤만 수행한다. 이번 검토는 현재207를 재실행하지 않았다. 특정 목표초/메모리 수치는 측정 전 성공 보장으로 제시하지 않는다.

**운영 전 수락:**소유 source freeze·집중/관련회귀·bounded subprocess 결과와 profile전파 evidence가 갖춰지고, Root가 단일 실제 전처리 실행을 별도 승인해야 한다. 기존207/1317/pointer/후보 source와 현재원장은 그대로 보존한다. source cap을 만났다고 자동상향·자동재시도·새수집 또는 QA 반복을 하지 않는다. 새profile은 저장 QA reader/UI 표시를 바꿀 수 있으므로 구현 완료 시API/schema/오류계약을 web_ui와 이해담당에 인계하고 실제서버 반영·브라우저 확인을 별도 보고한다. 이번은 내부 설계문서만이어서 UI/API 변경은 없다.

이 문서는 Root에 전달한 cap위험과 확장 설계다. 현재 처리 지연·프로세스 생존·QA 성과·운영 실행 승인을 새로 판정하지 않는다.
