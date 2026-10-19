# 231 후속 — 230 최종 동결판 독립 정적 검토

상태: **STATIC_REVIEW_COMPLETED / CHANGES_REQUIRED_BEFORE_SHARED_APPLICATION**. 230 최종 동결판을 수신한 뒤 정적 검토했다. 기존 F1~F4 핵심 경로의 보완은 확인했지만, 동일 명시 scope 안의 JSON 읽기 누락5범주가 남아 **전체 metadata I/O16GiB 계약은 아직 불완전**하다. 계약 범위를 축소해 통과시키지 않는다. 현재 freeze230은 그대로 보존하고, 수정은 Root가 별도로 배정한237 후속이다.

## 범위와 실행 경계

검토 대상은 231의 F1~F4 보완과173/182 source JSON·225 예산 reader/API의 명시 profile/config 연결이다. Root234는 별도 단일 full179 검사를 실행 중이므로 이 담당은 운영 data/원장/모델·실제 QA·native·HTTP·수집을 읽거나 실행하지 않는다. 공유 코드 편집·추가 시험도0이다. 완료한232 main 파일4개는230 적용 목록에서 제외되어야 한다.

230 담당의 최종 동결 경로는 `evidence/integration/preprocess230-workspace-20261018/`다. 수정 중에는 대기했고 최종 SHA 수신 이후에만 판정했다. 아래의 모든 경로·라인은 이 불변 사본을 기준으로 한다. 공유 main 적용은0이다.

## 최종 정적 검토 결과

| 항목 | 정적 검토 기준 | 현재 결과 |
|---|---|---|
| freeze/patch 일치 | 정확한 최종 SHA·bytes·기준 사본·수정파일 목록·시험로그 핀 대조 | 14파일·6증거·3로그 일치 |
| F1 staging 복사 | destination 생성 전 read+write 잔여량, 실제 chunk별 계상, 부분 실패·기본None 보존 | 핵심 수정 확인 |
| F2 JSON 해시 | suffix 대신 역할에 바인딩, 첫 읽기 전 cap/regular/identity 검사, 증가 파일·실제 읽은 byte 계상 | 기존 지적 경로 수정, 후속 누락 별도 |
| F3 고정 descriptor 상한 | caller256MiB/depth64 거부/축소, 더 작은 cap 보존, 작은 receipt/readiness는 확장하지 않음 | 강제 거부 확인 |
| F4 자원 실패 | 전용 자원 예외가 per-scene catch를 통과해 작업 중단, 일반 품질 오류와 구분 | readiness 재전파 확인 |
| 명시 선택·기본 호환 | 미지정64/v1·명시128/v2 일관, 자동 상향/재시도 없음 | 코드/저장시험 확인 |
| ContextVar | dual import 동일 작업예산·scope reset, 새thread/async 보증 범위와 시험 범위 구분 | 공유 예외/RLock/독립 scope 확인 |
| 173·182 source | source JSON에만 명시128 연결, 개별label/header64와 기존한도 유지 | 연결 확인, 기타 JSON I/O 누락 |
| 225 config/API | 고정 config 핀·source 핀/전후identity 확인·명시선택·read-only, 별도 원격4GiB·pending 산식 불변 | 선택/핀/전후 대조 확인 |
| v2 조회 reader | 현재상태/비교 경로가 같은 profile을 명시 선택하고 과거v1도 유지하는지 | v1 게시 reader와 v2 비교 query 분리 |
| gate·출력 | typedfalse·학습/과학/집행 승인 불변·strict receipt/profile marker·신규 출력 배타성 | true 승격/기준 완화 발견 없음 |
| 232 제외 |179·170·targeted_inventory_profile·test232가 patch/apply 목록에 없음 | 목록 교집합0·main4 SHA 불변 |
| 검증 한계 | 합성/Mock·whitespace 벤치와 실제 rich128 QA를 구분 | 실제 운영 검증0 유지 |

추가 시험을 실행하지 않고 저장된 시험의 입력·assert·Mock 범위와 로그를 읽었다. 운영 source/원장/모델·실제 QA·native·HTTP 읽기0, 공유 편집0이다. 이 문서의 결론은 정적 분석이며 실제 rich128 QA 성능이나 공유 적용 승인이 아니다.

## 동결판 대조 근거

| 파일 | 직접 확인한 SHA256 |
|---|---|
| freeze230.json | `e92b962361def809675bbfa498c44b7ede2953cb1e263bc30cd991eaf6f92401` |
| patch230-manifest.json | `ee6432ac6e1fcade043257f3b234be71bb7741b4797bbd9917c795b2c249a3e6` |
| patch230.diff | `6f3d14efaba86bdaaf112e029b76b5e348fab9a40667c4d11150e29471fbd089` |
| doc230 | `e04244d1d8287b4739fe7d66e54f96087ae207a39bbeb9092a119e6e8f4b0fc4` |

14개 after 파일·6개 evidence·3개 시험로그의 SHA/bytes 불일치는0이다. 부모228 freeze SHA `377f8112c0b503a24bc15556bad24b7e1eb75dd1a82465d76ada05ecaa21fc67`와 그11개 제품/시험 파일도 변하지 않았다.230 delta와232 네 파일/167/199의 교집합은0이다. main232 코드·시험4개는 freeze232 지문과 그대로다. 격리판의 구179/170 파일을 디렉터리 통째로 복사하면232를 덮을 수 있으므로 **manifest의 명시 적용 목록만** 써야 한다.

## 기존 F1~F4에서 확인한 보완

`candidate_staging.py:44~71`은 공유 예산 잠금 안에서 destination 생성 전 양방향 잔여량을 검사하고 chunk 읽기/쓰기·부분 실패를 계상한다. `manifest_resource_profile.bounded_json_digest:124~145`는 역할별 cap·regular/identity·처음 크기의 제한 읽기·전후 변경 검산을 수행한다.164 digest도 역할 기반으로 바뀌었으며 기존 source/normalization evidence의 readiness 해시가 이 경로를 쓴다.

profile policy는 source/candidate의 caller256MiB와 depth64를 거부한다. 더 작은 role 제한을 보존하며 descriptor128MiB/32를 전체 JSON에 무차별 적용하지 않는다. source/candidate의 scenes+history3000, node4M 제한도 유지한다. `readiness.py:249~250`은 공유 `ProfileResourceError`를 일반 scene 오류 앞에서 재전파한다.

dual import가 같은 ContextVar와 전용 예외를 공유하고, 알려진 동기 I/O는 RLock으로 보호한다. `independent_operation`이 UI 요청의 외부 scope 상속을 끊는다. 임의 await를 RLock 안에서 쓰는 것까지 지원하지 않으며 실제 rich128/3000행 메모리 검증은 없다. node 검사가 decode 이후라는 한계도 그대로다.

## 남은 단일 보완 목록 — 전체 JSON I/O 계측 누락5범주

아래는 모두 **명시 profile이 활성화된 같은 작업 scope에 들어와도** 공통 계측을 거치지 않는 직접 읽기다. 개별 cap이 있는 경우에도 누적16GiB와는 별개다. 수정은237에서 명시 profile일 때만 역할별 bounded reader/공통 scope를 주입하고, legacy 동작·오류·출력은 보존해야 한다. 새 숫자 cap을 임의로 만들거나 모든 JSON에 source128MiB를 쓰지 않는다.

| 범주 | 경로·라인·호출 근거 | 현재 개별 cap | 의미 기반 역할 제안 |
|---|---|---|---|
| 1.173 boundary/proposal | `scripts/find_bare_targets173.py:23~26` pin; boundary 호출63/146/183/193, proposal 최종 `_snapshot`198 | 각 `_snapshot`2MiB는 있음, 누적 계상 없음 | boundary는 현재2MiB의 boundary/evidence, proposal은 현재2MiB의 proposal/evidence. TIFF label 호출은 이 수정에서 제외 |
| 2.182 직접 JSON | `scripts/propose_deficit_centers182.py:22~28` pinned;49~50 입력목록,148/158 반복 대조;159 output.read_bytes hash | boundary/config/prior 각2MiB snapshot. 최종 output 직접 read에는 cap 없음 | boundary/config/prior/proposal 각각 호출 의미와 기존2MiB 결속. source만 기존 명시128 경로 유지 |
| 3.182 하위 validator | `backend/app/data/candidates.py:21~33,58` boundary.read_bytes+read_text, plan.read_text+read_bytes;182의81/156에서 prior/output 각각 호출 | validator 직접 read에는 cap 없음. 앞선 pinned 검산은 뒤의 read를 제한하지 못함 | 호출자가 이미 고정한 boundary/prior/proposal의2MiB 역할·핀·snapshot을 재사용하거나 명시 reader 주입. 기본 validator 동작 보존 |
| 4.status 공통 scope | `backend/app/collection_status.py:37~45` read_report,95에서 current 이외 보고서로 진입;14~29 same_hash 및134/205의 호출 | read_report/해시 cache-miss에 자체 byte cap 없음. 보고서 개수 제한은 개별 byte 제한이 아님 | historical annual/run/readiness/metadata를 의미에 따라 기존 한도로 분류. 기존 cap 없는 유형은 Root의 명시 계약 확인 없이 source128로 확대하지 말 것. JSON hash cache-miss만 실제 읽기를 계상하고 raster hash는 분리 |
| 5.게시 후보/나지 reader | `backend/app/collection_priority_status.py:20,26,36` pointer/report read_text와 same_hash;64~65 bounded read. status260~261이 같은 scope 안에서 호출 | candidate pointer64KiB/report16MiB는 stat 검사만; hash의 source/candidate는 자체 cap 없음. bare receipt64KiB/report2MiB는 read(limit+1) 있음 | 게시 pointer=receipt64KiB, 저장 QA=readiness16MiB, bare report=기존2MiB. 고정3파일은 source/candidate/readiness의 의미로 제한/계상. v1 UI 게시 reader와 v2 comparison은 섞지 말 것 |

1·2의 작은 입력도 전후 반복 검산에서 실제 JSON 바이트를 읽으므로 빠뜨리면 안 된다.3·4·5 일부는 앞선 stat/pin 뒤에 파일이 커졌을 때 cap 없이 다시 읽는 문제도 있다. cap 검사→open descriptor identity→제한된 실제 chunk 계상→전후 path/stat/pin 확인을 한 공통 transaction에서 처리해야 한다. 기존 원본을 여러 번 읽으면 그 실제 횟수대로 계상한다.

4·5의 hash cache hit는 실제 파일을 읽지 않으므로 과거 파일 크기를 다시 계상할 필요가 없다. 반대로 cache miss나 candidate/bare report를 실제 읽는 비용은 제외할 수 없다. 공통 reader 주입 시 `ProfileResourceError`가 read_report·candidate_quality·bare_target_review의 ValueError catch에 삼켜져 계속 처리되지 않도록, 명시 작업의 자원 실패 경계도 함께 연결해야 한다. source pin 불일치와 resource 오류의 응답은 단순히 빈 재고로 성공한 것으로 표현하지 않는다.

### 237의 좁은 소유·수락 제안

공통 profile helper와173/182,182가 호출하는 candidates validator, status/priority reader의 위 입구만 보완한다. 수집기·232179/170·167/199·원격 원장·raster/label/header 처리와 품질 gate는 바꾸지 않는다. 새 독립 수집이나 실제 QA도 실행하지 않는다.

합성 수락은 작은 Temp JSON과 낮춘 잔여 예산으로 각 입구가 실제 read 전에 거부되는지, 성공한 read/재해시의 정확한 계상, 이전 pin 뒤 성장/교체 파일 중단, 중간 자원 오류의 전체 작업 전파, v1 결과 동등, v1 게시 reader/v2 비교 선택 분리를 검증해야 한다.16GiB나128MiB까지 실제 부하를 반복하는 시험은 이 결함을 검증하는 데 필요하지 않다.

## 173/182/225 연결에서 유지되는 사실과 한계

173 discover/182 propose의 keyword/CLI 명시 profile 선택은 source에 연결됐다.225의 `collection_source_profile.py`는 DATA 안의4096B·깊이8 strict config에서 정확한 marker와 source SHA를 읽고 전후 config/identity/SHA를 대조한다. source는 선택된64/128 상한에서 읽고 선택 source SHA를 확인한다. budget의 원장8MiB·pending 포함 산식·전역 원격4GiB는 바뀌지 않았다. config 경로는 `app.state.collection_source_profile_path`에서 두 API가 공유하며 브라우저가 상한을 자동 선택하지 않는다.

다만 이 연결이 위 모든 하위 JSON 읽기를 자동으로 계측하지는 않는다.현재상태의 v1 게시 후보 포인터와 과거 코호트 관측은 기존 독립 경로이고,228의 v2 comparison query와 동일한 영수증 schema가 아니다. false gate를 true로 올리는 변경은 발견하지 못했지만 JSON 자원 보호가 완료됐다고 주장할 수는 없다.

readiness의 official product metadata 경로는 XML을 참조하는 기존 수집 코드임을 확인했다. XML/TIFF/hash 전체를 JSON 누락으로 무조건 포함하지 않는다. execute=False 이후의 모델 학습·추론 경로도 이번 정적 보완 목록으로 확장하지 않는다.

## 저장 시험의 시점과 최종 인계

관련176PASS/181.901초는 마지막173/182 출력 계측 연결 **직전** 판이다. 최종60PASS/31.711초는 그 출력 연결·공통 profile·230/228/173/182 회귀를 포함한다. 집중27PASS/17.138초와 역사228 88PASS·whitespace31.148초406MiB를 합산하지 않는다. 이전 fixture 경로 실패와 수정 로그도 보존됐다. 추가 시험을 이 검토자가 실행한 수는0이다.

현재 판정은 **기존 F1~F4 핵심 수정 확인 / 누락5범주로 전체 JSON I/O 계약 BLOCKED / 공유 적용0**이다. Root는237 revision을 별도 소유로 배정하고 현재230 freeze를 덮어쓰지 않는다. 보완 완료 후 새 freeze/독립 대조와 Root 판단이 필요하며, 실제 rich128 QA·서버/UI 적용·수집·학습/운영 승인은 별도 증거로 남는다. Root와 이해 담당에 이 구분과 구체 경로를 전달한다.
