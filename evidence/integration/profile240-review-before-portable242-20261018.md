# 240 — 237 metadata profile 최종 독립 정적 재검토

판정: **STATIC_REVIEW_COMPLETED / NO_REQUIRED_FIX_FOUND_BEFORE_ROOT_SHARED_VERIFICATION**. 237 동결판에서 앞서 지적한 JSON I/O 누락5범주의 연결을 확인했다. 이번 검토 범위에서 공유 적용 검증 전에 반드시 수정해야 할 새 결함은 발견하지 못했다. **공유 적용·실제 rich128 QA·수집·학습/운영 승인을 완료했다는 뜻은 아니다.** 적용은 Root만 결정한다.

## 검토 범위와 금지 경계

Root가 지정한237 최종 freeze/manifest/diff, 소유 제품6개·신규 시험1개, 관련 문서와 저장 로그를 읽었다. 독립 검토자가 실행한 추가 시험·운영 data/원장/모델·실QA/native·HTTP·collector·공유 편집은0이다. 기존238 준비 문서도 수정하지 않았다.235 실제 수집 여부를 관측하거나 미래 source 지문/수량을 만들지 않았다.

모든 코드 경로·라인은 `evidence/integration/preprocess237-workspace-20261018/`의 동결 사본 기준이다. 상대 경로는 아래 표와 본문에서 이 격리 root를 기준으로 한다.

## 지문·기준판·소유 보존

| 확인 항목 | 직접 대조 결과 |
|---|---|
| freeze237.json | `56c9f57bf4929338835170e48d15495385e48cf58140f7ca396bdbbf4a07ceb6` |
| patch237-manifest.json | `234d3876fab0e1ce04c77c9f227314120c68818f3be354fb98e3a74a41a33ddc` |
| patch237.diff | `3ac0e7abe78783dd3f45f09150d41fe158910a50e55c22b0033a11d935169989` |
| doc237 | `5935e229897d96fd823c79b0d073a45d3f1ca1617afe594660d67510bb28ec68` |
| 부모230 freeze | `e92b962361def809675bbfa498c44b7ede2953cb1e263bc30cd991eaf6f92401` |
| final109 로그 | `df7a4c75b09eae1dfa2f7f79d5bc575ad2ac4e50283209bd3257e5c8803d8c68` |

237의7개 제품/시험 파일과13개 증거의 SHA·bytes 불일치는0이다. 부모230의14개 제품/시험 및9개 evidence/log 지문도 그대로다. 별도 main232 코드·시험4개는 freeze232와 일치했다.237 변경 목록과232 네 파일·공용167·199의 교집합은0이다. 격리 디렉터리를 통째로 공유 제품 위에 복사하면 구179/170 사본이232를 덮을 수 있으므로 **검토된 명시 적용 목록만** 사용해야 한다.

## 누락5범주의 수정 확인

| 기존 지적 | 직접 확인한 연결 | 정적 결과 |
|---|---|---|
|173 boundary/proposal pin | `scripts/find_bare_targets173.py:23~31,68,203` | boundary2MiB의 공통 read_metadata·pin, 최종 proposal2MiB bounded hash. label 읽기119는 binary로 명시 분리 |
|182 초기/반복 입력·최종 hash | `scripts/propose_deficit_centers182.py:22~31,52,151,159~163` | source/boundary/local_config/local_plan 역할을 tuple에 결속, 반복 대조 모두 계상. 신규안은 proposal 역할·최종 bounded hash |
|182 하위 validator | `backend/app/data/candidates.py:22,31~40,65~67` | 경계와 prior/proposal을 제한 읽기, parse digest와 최종 hash 일치·경계도 최종 재검산. None에서는 구 직접 reader 분기 유지 |
|status 보고서·hash cache | `backend/app/collection_status.py:16~31,50~59,108~116,227~233` | 명시 role별 read_metadata, cache miss actual read 계상, hit stat-only 검산. unknown role는 읽기 전에 자원 오류 |
|게시 candidate/bare reader | `backend/app/collection_priority_status.py:14~58,60~152` | pointer·QA/bare report 공통 읽기, 고정3파일은 source/candidate/readiness 순서 바인딩, 자원 예외는 일반 unavailable 처리 전에 재전파 |

공통 `manifest_resource_profile.py:124~145`는 파일을 열기 전에 regular/path·개별 cap·잔여량을 검사하고 최초 stat 크기만 읽는다. 실제 chunk 바이트를 같은 scope에 계상하며 descriptor/path/stat 전후 변경을 검사한다. `read_metadata:204~217`는 이 digest/capture를 한 번 읽어 재사용하고 strict UTF8·중복키·유한숫자·깊이·node·행 검사를 적용한다. 명시 expected pin이 다르면 canonical 자원 예외로 중단한다.

### 역할별 제한의 구분

`JSON_ROLE_CAPS`122행에서 source/candidate128MiB, boundary/local_config/local_plan/proposal/evidence2MiB, readiness16MiB, pointer64KiB를 확인했다. 기존 saved_plan4MiB·policy1MiB·receipt64KiB도 별도다. 모든 작은 JSON을 source128MiB로 넓힌 변경이 아니다.

**status_report16MiB는 명시 profile에서만 적용되는 새 제한**이다. 기존 unbounded status 경로는 default None에서 보존되므로 기존 모든 status 응답을 새로 제한했다고 표현하지 않는다. 과거 annual은 알려진 source 보고서 호출 위치에서 source로, readiness 보고서는 readiness로 지정한다. 크기나 확장자를 보고 역할을 자동 선택하지 않는다.

### 현재 원본과 고정 후보의 분리

현재 source의 실제 경로는 config 선택과 current source reader에 바인딩된다. status의 `known_source_paths`와 `manifest_role`은 현재/명시 source 보고서 경로일 때만 source를 선택한다. QA의 `collection_manifest` kind가 staged candidate를 가리킬 수도 있으므로 kind 하나만 보고 모두 source로 분류하지 않는다. 미확정 kind/경로는 명시 scope에서 무계측 hash로 빠지지 않는다.

게시 candidate는 기존 v1 pointer의 고정3파일 순서에 source/candidate/readiness를 바인딩한다. 저장 QA report를 다시 파싱할 때도 앞선 receipt의 pin을 전달하고 실제 재읽기 비용을 다시 계상한다. 과거 게시 cohort가 유효하면 available이면서 `source_matches_current_manifest=false`일 수 있다. 이를 현재 원본 QA 성공으로 해석하지 않는다. 이 v1 UI reader를228의 v2 comparison query/영수증 검증으로 대체하지 않았다.

## 캐시·실제 읽기·오류 전파

metadata cache key는 profile 전용 prefix·논리경로·role·size/mtime/ctime/device/inode를 포함한다. 이전 legacy cache를 명시 profile cache로 무계측 재사용하지 않는다. hit에서도 논리경로/identity를 다시 검사하며 실제 read가 없으면0바이트를 계상한다. role·inode가 바뀌면 새 read가 필요하다. 이는 metadata identity 기반 캐시이고 외부 행위자가 모든 identity 필드를 완벽히 위조하는 경우까지 탐지한다는 보장은 아니다.

`read_report`, `candidate_quality`, `bare_target_review`와 current source 관측은 canonical ProfileResourceError/SourceProfileError를 일반 데이터 오류 catch보다 먼저 재전파한다. 상위 configured wrapper는 전체 UNCONFIRMED·학습 false로 마감한다. 일부 입력의 자원 오류를 빈 재고로 대체하고 정상 관측을 이어가는 기존 공백을 보완했다. 일반 legacy malformed/missing 보고서의 기존 unknown/unavailable 동작은 유지한다.

알려진 동기 I/O는 같은 Budget/RLock 안에서 잔여량 검사와 실제 read/계상을 수행한다. dual import의 공유 ContextVar/예외와 독립 UI scope 계약은 부모230을 유지한다. 임의 async await나 외부 I/O 전체의 안전성을 보증하는 변경은 아니다.

## 저장 시험 근거와 실제 검증의 한계

최종 로그에서 **109PASS/39.174초**를 읽었다. 신규237 집중19개가 포함된 수치이며 별도 수로 더하지 않는다. 이 검토자가 재실행한 시험은0이다. 앞선108회귀의1오류는214 구 source 코드 fixture 누락이었고, 부모230 코드의 원바이트·지문을 보충한 이력을 supplement manifest와 보존 실패 로그로 확인했다. 제품 cap/오류를 완화해 시험을 통과시킨 것으로 표현하지 않는다.

신규 시험의 assert는 다음을 확인한다.

- 낮춘 누적 예산과 개별 cap 초과에서 파일 open 전 실패, 같은 파일의 반복 read 실제 바이트와 계상량 일치
- 173 CLI의 JSON read/write 계상과 label binary 분리,182 전체 경로의 source3/boundary7/config3/prior5/proposal3 실제 읽기 횟수
- validator parse 뒤 교체된 boundary/plan의 최종 hash 거부, 성장 파일의 최초 크기 제한 읽기 뒤 중단
- cache hit 실제 read0, role 변경/교체 시 재읽기, logical path 변경 중단
- v1 게시/182 proposal/status 결과의 부모판과 exact 동등, dual import 공유 budget/예외
- unknown verified kind와 staged candidate를 source로 오인하는 경우 읽기 전 실패, 상위 status 전체 UNCONFIRMED 전파

이것은 작은 Temp·Mock/관측 wrapper 시험이다. sparse cap+1 파일은 읽기 전 거부 시험이며 실제128MiB rich JSON 처리 성능이 아니다. 저장된 RSS106,172,416B·그 시점 peak108,896,256B는 시험 프로세스 중간 표본으로 전체 종료 peak가 아니다. 역사228 whitespace31.148초406MiB를237 성능으로 재사용하지 않는다. 현재 실제 원본의 구조 숫자는 Root의 별도 관측이며 이 검토자가 운영 파일을 읽어 검증한 것이 아니다.

## Root 적용 검증 전 남은 일

정적 재검토 범위에서는 **필수 수정 없음**으로 인계한다. Root는228→230→237의 정확한 누적 파일판과 공유 baseline drift를 대조하고,232/167/199를 제외한 명시 목록만 적용할지 결정해야 한다. 적용 코드 지문·import/CLI/API 계약·Root 내부 config와 현재 source pin의 연결 검증은 별도다. 실제 서버·API·브라우저 적용, 실제 rich128 QA의 wall/RSS 및 자원 충분성도 이 문서가 통과시킨 항목이 아니다.

한도/자동 선택·재시도·원격 예산·기존 pending·품질/분할/학습 기준을 완화한 diff는 발견하지 못했다. 프로세스 시작이나 게이트 완료를 프로젝트 완료로 확대하지 않는다.238은 준비 상태를 유지하고235 실제 종료·정산·bounded native와 Root GO가 필요하다. 이해 담당은 “격리 합성시험+정적검토 완료 / 공유 검증 전 / 실제 수집·QA·UI·학습 승인 별도”를 구분해 설명·대본·FAQ·INDEX·이력을 갱신해야 한다.
