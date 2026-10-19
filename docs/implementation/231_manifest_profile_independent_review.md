# 231 — 격리228 manifest profile 독립 정적 검토

상태: **STATIC_REVIEW_COMPLETED / CHANGES_REQUIRED_BEFORE_SHARED_APPLICATION**. 격리 구현과 저장된 시험 증거를 읽고 자원 보호 계약의 결함4개를 확인했다. 공유 제품 적용·운영128MiB 성공·다음 수집 재개를 승인하는 문서가 아니다. 코드 수정·추가 시험·운영 source/원장/실제 QA 재읽기·native·HTTP는 모두0이다.

## 쉽게 설명

228은 큰 JSON 문서를 처리할 때 명시적으로128MiB 경로를 선택하게 하는 격리 구현이다. 기본64MiB 경로와 v1 영수증을 보존하고 새 경로에는 v2 표시를 붙이는 방향은 코드에 연결됐다. 다만 처리비용 장부에서 후보 복사가 빠지고, 일부 파일은 크기를 거부하기 전에 끝까지 해시한다. 그래서 현재16GiB 계측값을 실제 전체 JSON I/O의 강제 상한이라고 믿을 수 없다.

또 공개 helper에 더 큰 사용자 정책을 주면 descriptor의128MiB/깊이32가 항상 강제되지는 않는다. 행 안의 자원 오류가 전체 작업 실패 대신 해당 행의 QA 오류가 되는 경로도 있다. 이 네 가지를 수정하거나 계약을 명확히 제한하기 전에는 공유 운영 적용 준비 완료로 보고하지 않는다.

## 읽은 범위와 지문 확인

기준은 [228 구현 설명](228_explicit_manifest_profile_isolated.md), `evidence/integration/preprocess228-workspace-20261018/`의 freeze/patch manifest/diff, 신규 `manifest_resource_profile.py`, 변경 reader/CLI와 `test_manifest_profile228.py`다. 코드 실행으로 재현하지 않고 분기와 호출 순서를 읽었다.

| 대조 항목 | 실제 정적 확인 |
|---|---|
| freeze228 SHA | `377f8112c0b503a24bc15556bad24b7e1eb75dd1a82465d76ada05ecaa21fc67` |
| patch228.diff SHA | `64238b9f52d4526b44bd4ccfa2c40b46d8443973ecd4bb238d6f8ff8e04c19ba` |
| patch228-manifest SHA | `4b739df89075c0823eee276471522198862bcf30194a65c40b7be883c532c35f` |
| 수정/신규 파일 | 11개 SHA/bytes 일치 |
| freeze의 evidence | 10개 SHA/bytes 일치 |
| 기존 변경 대상9개의 원판과 공유판 | 각9개, 합18개 before SHA 일치 |
| profile descriptor SHA | `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4` |

지문 불일치는0이다. 이는 읽은 파일이 동결판과 같다는 뜻이며 기능 성공 시험을 새로 했다는 뜻이 아니다. main 기존9개가 그대로인 사실도 확인했고 신규 helper/시험은 격리판만 읽었다. 운영 DATA는 읽지 않았다.

## 수정이 필요한 구체적 사항

### 1. [P2] staging 복사 read/write가 JSON I/O budget에서 빠짐

격리 `backend/app/ml/candidate_staging.py:45~56`의 `_copy_bytes`는 원본 후보를 chunk로 읽고 새 DATA 후보에 쓰지만 `profile_charge`와 `require_io_room`을 호출하지 않는다. 같은 함수의 SHA·stat·최대 파일 크기 검산은 남아 있으므로 복사 정확성 결함으로 표현하지 않는다. 문제는 **실제 JSON I/O가 발생해도16GiB 작업 계측이 늘지 않는 것**이다.

128MiB 후보라면 읽기128MiB+쓰기128MiB, 최대256MiB가 누락된다. 뒤에서 같은 후보를 BoundedJSONIO로 읽는 비용이 계상돼도 앞의 복사 비용이 대체되는 것은 아니다. 남은 budget이 복사 비용보다 작아도 복사를 시작할 수 있다.

권고: 새 파일을 열기 전에 읽기+쓰기 잔여량을 확인하고 실제 chunk별 read/write를 계상한다. 기본None에서는 기존 바이트/동작을 유지한다. 향후 Temp 시험은 복사비용보다 작은 잔여량으로 destination 생성 전 실패 및 충분한 budget에서 정확한 누적량을 확인해야 한다. 이 리뷰에서는 시험하지 않았다.

### 2. [P2] 해시 reader가 cap 검사 전에 파일을 읽거나 suffix에 따라 계측을 생략함

격리 `backend/app/ml/readiness.py:144~153`은 JSON의 stat 크기를 선계상하고 `dataset.file_digest`로 EOF까지 읽은 뒤 `profile_read_json`으로128MiB cap을 검사한다. 같은 순서는 normalization evidence에도 적용된다(`readiness.py:202~203`). 기존 `dataset.py:11~16`의 digest에는 byte cap·descriptor identity 대조·chunk 계측이 없다.

예를 들어128MiB를 초과하지만16GiB 잔여량 안인 JSON은 bounded parser에서 거부되기 전에 해시가 전체를 읽는다. 해시 도중 파일이 커지면 선계상한 stat 크기와 실제 읽은 양도 달라질 수 있다. 164의 고정 snapshot 경로가 대부분 정상이라고 해서 독립 readiness reader의 자원 경계까지 보장되지는 않는다.

추가로 격리 `scripts/prepare_priority_candidate164.py:25~42`의 digest는 `path.suffix == '.json'`일 때만 bounded/profile 계측 분기로 간다. CLI source는 `.JSON`이나 확장자 없는 파일도 입력 계약상 가능하며 `prepare:100`의 첫 digest는 `copy_pinned`의 크기 검사를 앞선다. 이때 실제 JSON이 기존 무제한 hash 분기로 간다. 따라서 파일 확장자와 자원 역할을 같게 취급하면 안 된다.

권고: JSON 역할에 바인딩된 공통 bounded digest를 사용하고 cap/regular file/identity·잔여량을 읽기 전에 검사하며 실제 chunk를 계상한다. raster hash는 JSON 예산과 계속 구분한다. 향후 시험은 과대 source의 첫 읽기 차단, `.JSON`/무확장자 동일 계측, 해시 중 증가 파일을 포함해야 한다.

### 3. [P2] descriptor의128MiB/깊이32가 공개 IO policy 전체의 상한은 아님

격리 `manifest_resource_profile.py:42~49`는 source/candidate의 **기존 값이 정확히64MiB일 때만**128MiB로 바꾼다. 더 큰 caller cap은 낮추지 않고 `max_depth`도 변경하지 않는다. `split_json_io.py`의 constructor는 기존처럼 cap최대256MiB·깊이최대64를 허용한다.

정적 반례는 명시 scope 안에서 source/candidate cap256MiB 또는 depth64인 BoundedJSONIO 정책을 전달하는 경우다. 이는 profile descriptor의128MiB/32보다 큰 정책으로 남는다. 현재164의 고정 POLICY 경로는128MiB/32이므로 그 CLI가 즉시 큰 파일을 허용한다고 주장하지 않는다. 문제는 **공개 helper의 고정 descriptor 보증 범위**다.

권고: 명시 profile에서는 source/candidate cap과 depth에 descriptor 상한을 적용하거나 더 큰 정책을 거부한다. 더 작은 역할별 제한은 유지해야 하며 readiness/receipt까지128MiB로 넓히면 안 된다. 향후 시험은 source/candidate256MiB·depth64·더 작은 cap 보존을 직접 검증해야 한다.

### 4. [P2] 행 안의 자원 초과가 전체 작업 중단 대신 SCENE_QA_ERROR가 될 수 있음

격리 `readiness.py:203`의 normalization evidence 읽기는 profile의 byte/depth/node 검사로 ValueError를 낼 수 있다. 그러나 그 범위는 `readiness.py:249~250`의 `except Exception`에 잡혀 `SCENE_QA_ERROR`를 추가하고 다음 행을 처리한다.

따라서 작은 원본이 한 행에서 과대/과노드 metadata를 참조하면, 작업 전체가 `MANIFEST_*` 자원 실패로 끝나는 대신 일부 행을 제외한 blocked readiness 보고서로 완료될 수 있다. 학습 승인을 true로 올리는 결함은 아니지만, 228 문서의 “어느 자원 한계를 만나도 중단”과 다른 완료 의미다. 누적 I/O를 일부 소비했더라도 잔여량이 충분하면 뒤의 보고서 저장이 반드시 실패하는 것은 아니다.

권고: 별도 자원 제한 예외 형식을 사용해 이 오류는 per-scene QA catch에서 재전파한다. 기존 데이터 품질 오류의 blocker 처리는 유지한다. 향후 시험은 첫 장면 metadata의 자원 초과 후 다음 장면/raster read·완료 영수증이 생기지 않는 것을 확인해야 한다.

## 연결된 부분과 허용 가능한 한계

- 기본None에서 cap64MiB·v1 영수증·기존 false 계약을 유지하는 분기를 확인했다. 저장된 시험은 같은 Temp 입력의 materialization plan/candidate/receipt 바이트 동등을 검증한다. 모든 과거 artifact와 모든 경로의 바이트 동등을 증명한 것은 아니다.
- 명시 profile의 package/staging/QA receipt는 v2+동일 descriptor marker를 쓰고, 소비자는 선택되지 않은 v2와 marker 불일치를 거부한다. profile receipt를 내부 v1 형태로 정규화한 뒤 기존 exact schema·typed false 검사가 이어진다. 학습/과학/집행 false를 true로 바꾸거나 품질80%·주내95%·고정split·나지 기준을 낮추는 diff는 발견하지 못했다.
- source/candidate `scenes+history`의3000행 검사와 node4M 제한이 추가됐다. node 검사는 `json.loads` 이후이며 parser 메모리 할당을 사전에 모두 막지 못한다. `_tree`의 container/닫힘/key 방문수는 데이터셋 행수와 다르다.128MiB whitespace JSON의 메모리 수치로 rich3000행·4M노드 최대 메모리를 보장하지 않는다.
- dual import는 `sys.modules`의 단일 ContextVar를 공유한다. explicit scope의 finally reset과 중첩 호출 예산 공유는 코드·저장된 회귀에 있다. 다만 신규9개 시험에는 실제 thread/async 동시 요청 검사가 없다. ContextVar에 담긴 **Budget은 mutable 객체**이므로 복사된 context의 child task/thread는 같은 객체를 공유할 수 있고 `scope(NAME)`도 기존 객체를 재사용한다. 현재 직렬 CLI/API semaphore1 경로의 의도된 동작으로 한정하며, 독립 병렬 작업 격리나 thread-safe 원자 charge까지 검증됐다고 쓰지 않는다.
- 누적 JSON I/O16GiB는 원격 수집 원장4GiB·COG/metadata batch 예산과 별개다. raster I/O/hash를 이 계측에서 제외한 설계는 허용 가능한 범위 구분이다. summary의 `manifest_resource_usage_before_summary_write`는 이름대로 summary 저장 전 수치이며 전체 OS I/O 통계가 아니다. 단, 앞의 staging/hash 누락은 이 허용 범위와 구분해 수정해야 한다.
- 비교 API에는 명시 `manifest_profile` query 선택과 잘못된 이름400/미선택 v2의503 경로가 있다. reader는 계속 저장 보고서4개만 대조하고 manifest/raster를 재실행하지 않는다. response false 계약도 유지한다. 실제 서버 적용·브라우저 확인은 이 리뷰에서0이다.

## 알려진 후속230 범위 — 이번 신규 결함과 구분

173 source JSON pin·182 proposal source·225 예산카드 source64MiB, `collection_priority_status`의 v2 조회 profile 선택 연결은 별도230 후속이다. 228의 candidate 비교 API query가 생겼다고 실제 UI/현재상태 reader가 v2를 소비하게 된 것은 아니다. 개별 label/raster64MiB와 원격 budget은 그대로 유지해야 한다.

따라서 profile 단위의 시험 통과만으로64MiB 초과 후 다음 수집·예산카드·나지 탐색·새 proposal·게시 후보 조회가 모두 연결됐다고 보고하지 않는다. 이 알려진 공백을228의 새 회귀 결함으로 혼합하지 않는다. Root가 downstream 완료 전 수집을 재개하지 않는 현재 경계를 유지한다.

## 저장된 시험·실측의 정확한 의미와 인계

동결 로그의 **88PASS/74.061초·skip0**를 읽었다. 이는 신규9개+관련79개이며 리뷰가 재실행한 수가 아니다.164 metadata 연결 시험은 실제 source/candidate native gate를 Mock했다. 따라서 실제128MiB rich manifest·현재 source·운영 raster QA 성공 증거가 아니다.

benchmark는 단일 child의 **31.148초·CPU24.391초·peak426,115,072바이트(약406MiB)**이며 whitespace padding으로64/128MiB 바이트 경계를 확인했다. 마지막 dual-import 보강 전 cap/parser 경로의 실측이고 rich3000행·node4M·I/O16GiB 전체 부하 검증이 아니다. 이번 리뷰는 benchmark·시험·운영 QA를 추가 실행하지 않았다.

Root에 네 결함과 known230·시험 한계를 전달했다. 코드 보완·회귀·새 동결판 독립 대조 후에 공유 적용 여부를 판단하고, 실제 rich128 운영 검증은 별도 명시 실행으로 남긴다. 구현 담당 파일을 이 리뷰 담당이 수정하지 않는다. 이해 담당은 “격리 합성시험 완료 / 자원계약 수정필요 / 공유 미적용 / 실제128 운영 미검증”을 분리해 설명·FAQ·INDEX·이력을 갱신해야 한다.1342 후보 게시·실UI 및 원본1358/셀21의 별도 완료 사실은 재검사하지 않았다.
