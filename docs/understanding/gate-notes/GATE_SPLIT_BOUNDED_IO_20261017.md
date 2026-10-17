# Gate Split Bounded IO 20261017 — 분할 계획·검증의 선택적 JSON 한도

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/ml/split_planning.py`; `backend/app/ml/split_validation.py`; `backend/app/ml/split_json_io.py`; `tests/test_split_bounded_io.py`; `evidence/integration/split-bounded-io-related-20261017.log`; `docs/implementation/70_split_bounded_io.md`; `evidence/integration/split-bounded-io-independent-20261017.log`; `evidence/integration/split-bounded-io-live-20261017.json`; `evidence/integration/split-bounded-io-live-run-20261017.log`; `evidence/integration/split-bounded-io-full-tests-20261017.log`; `evidence/integration/split-bounded-io-live-integrity-20261017.json` |
| confidence | 코드·전체/독립로그·실제3JSON validator/보존근거; CPU/RAM·원자성·과학승인 보장 아님 |
| status | TESTED_SYNTHETIC: opt-in IO·전체회귀; VERIFIED_REAL: 3JSON readonly validator; 후보발행/학습 BLOCKED |

## 쉬운 설명

기존 계획·검증 작업에 선택적으로 문서 크기와 깊이를 재는 자를 붙였다. 읽는 문서가 정한 크기를 넘으면 거부하고, 다시 읽을 때 같은 문서인지 지문을 확인한다. 두 결과를 쓸 경우 둘 다 쓰기 전에 크기를 잰다. 크기 제한은 한 번의 문서 읽기·출력에 대한 것이며 컴퓨터 전체 메모리나 실행시간의 상한은 아니다.

## 이론적 배경

기존 metadata planner/validator/writer를 새로 복제하지 않고 선택적 IO context를 공통화했다. 입력마다 역할별 byte cap을 두고 최초 논리경로→대상·파일상태·SHA를 기록해 재읽기 때 보존한다. JSON의 크기·깊이·UTF8·중복키/비유한 수 경계를 검사해 제한 없는 파싱/출력을 줄인다. 이 기술적 IO 경계가 자료 적격성·원본 진실·과학적 승인 판단을 바꾸지는 않는다.

## 실제 함수·정책

`plan_split_repair`, `write_plan`, `validate_split_repair_plan`의 새 `io_policy=None` 기본값은 기존 경로를 유지한다. 명시 정책 또는 공유 `BoundedJSONIO` 객체를 전달할 때만 새 제한을 적용한다. CLI/API/UI 플래그나 새 orchestrator는 추가하지 않았다.

정책은 정확한 input_caps/output_caps/max_depth 세 키다. 입력 역할은 source/readiness/saved_plan/candidate, 출력 역할은 plan/candidate이며 역할별 byte cap은 정확한 int1..256MiB·깊이는 정확한 int1..64다. bool을 정수로 허용하지 않고 정책 복사/읽기전용 map으로 호출자 변경 영향을 줄인다.

`BoundedJSONIO.read`는 local 일반파일만 다루고 사전크기·descriptor stat·읽기 중/후 상태·논리대상·바이트수·SHA를 확인한다. UTF8 BOM/NUL·중복key·NaN/Infinity·깊이 초과를 거부한다. 같은 context의 모든 후속 읽기는 최초 대상/stat/SHA와 같아야 하며 verify도 bounded 경로로 재읽는다. source/readiness 등 명시 pin이 필요한 상위 `_load_bound`는 None/잘못된 SHA를 거부한다. 하위 일반 read의 첫 SHA발견 기능을 상위 필수 pin 우회로 사용하지 않는다.

`measure`는 지원 JSON tree·깊이·문자열/UTF8·순환참조·숫자를 확인하고 encoder 청크의 UTF8 바이트를 합산한다. writer는 plan과 요청한 candidate를 모두 사전측정한 뒤 입력 재검사·새 target/parent 확인을 거쳐 exclusive binary stream으로 쓴다. candidate를 먼저 쓰고 plan을 쓰므로 둘 중 일부 새파일만 남는 실패도 가능하며 자동삭제/트랜잭션을 보장하지 않는다. 실제 전송바이트가 상한/측정값과 같은지 확인하고 입력도 다시 검사한다.

## 한계·현재 상태

각 cap은 각 읽기/출력의 byte 상한이다. 여러 번 읽는 누적 IO·process RAM·CPU시간·단계 전체 hard budget이 아니다. JSON파싱/후보 deepcopy 등 메모리 작업은 남아 있다. 경로의 일반 local/장치/ADS·논리대상 검사는 있으나 DATA/evidence 역할별 scope 강제와 상위 후보 orchestrator는 다음 단계다. 다중파일 원자 snapshot·OS parent교체의 원자 방어도 보장하지 않는다.

이번 실제 후보생성·Registry등록·원본제외/재배정·분할/정책/gate변경·새assess/학습은 없다. 후보 미지정은 NOT_REQUESTED/null로 남기며 존재/부재를 추정하는 검사가 아니다. 원본1,111적격과 계획1,095, 기존5차단·terminal2missing·예약136,314,880B·환불0·모델Draft를 유지한다. 새 API/UI 계약이 없어 이번 화면변경은 필요 없다.

## 시험 증거

최종 관련45 PASS/15.560초는 신규20+기존25이며 작은 합성자료로 제한·동등성·pin/재읽기·새출력·사전측정/부분실패를 확인했다. 독립검토에서 상위 필수SHA에 None이 전달될 때 우회할 수 있는 문제를 발견해 수정·회귀시험을 추가했다. 독립 최종은 신규20 PASS/5.243초와 기존25 PASS/11.972초로 나눠 확인했다. 깊이 기준 불일치와 필수SHA 누락 우회를 수정했으며 Windows CRLF를 포함한 기본/opt-in writer 바이트 동일성도 합성 회귀로 확인했다. 최종 전체 scripts/test.ps1은 **691건 중690 PASS·1 SKIP/298.655초/종료0**다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었고 deterministic 경계 시험은 통과했다. 관련45 PASS/15.560초(신규20+기존25)와 독립 신규20 PASS/5.243초·기존25 PASS/11.972초를 전체691에 중복 합산하지 않는다. 보호134참조·26기존 계약SHA·세 고정입력과 카탈로그14기록 canonicalSHA가 불변이다. 이전 추적 코드/데이터/프론트 중 바뀐 기존파일은 의도한 split_planning.py/split_validation.py 두 개이며 변경0이 아니다. 신규파일/문서/evidence도 있으므로 전체workspace변경2개라는 주장도 하지 않는다. 이해 에이전트는 시험·실제명령을 실행하지 않았다.

## 발표 1분

“기존 분할 계획·검증에 선택적으로 JSON 크기와 깊이를 제한하는 경로를 추가했습니다. 기본 동작은 유지하고, 새 경로를 요청할 때만 역할별 한도를 적용합니다. 문서를 다시 읽을 때 최초 지문·대상이 같은지 확인하고 두 결과를 쓸 때는 둘 모두 쓰기 전에 크기를 잽니다. 필수 지문 누락을 통한 우회도 독립검토에서 찾아 막았습니다. 다만 한 번의 문서 바이트 제한이지 전체 메모리나 시간 보장은 아닙니다. 이번에 후보를 생성·발행하거나 원본 분할과 학습 차단을 바꾸지 않았습니다.”

## 발표 5분·10분

1. **0~1분:** 문서 크기/깊이를 재는 자 비유를 설명한다.
2. **1~2분:** defaultNone과 opt-in·역할별 정책·공통context를 구분한다.
3. **2~3분:** 재읽기 pin/target·엄격JSON·출력2개 사전측정을 설명한다.
4. **3~4분:** 관련/독립·실제validator/전체·보존과 SHA우회수정 근거를 구분한다.
5. **4~5분:** bytecap≠RAM/CPU/누적IO·부분파일·scope후속·후보미생성을 말한다.

10분 확장에서는 하위SHA발견과 상위필수pin·BOM/NUL/중복key·binary stream과 측정byte·candidate먼저쓰기·동일context verify와 원자성 한계를 설명한다.

## Q&A

**기존 명령이 자동으로 바뀌나?** io_policy None 기본 경로는 유지하며 새 CLI/API/UI옵션은 없다.

**모든 자원을 제한하나?** 읽기/출력 각각 bytecap과 JSON깊이만 제한하며 누적IO·RAM·CPU하드제한은 아니다.

**두 파일이 항상 같이 저장되나?** 둘 다 사전측정하지만 단계별 exclusive쓰기여서 부분새파일이 남을 수 있다.

**후보를 만들었나?** 실제 후보생성/등록/원본제외·학습은 없다. 후보미지정NOT_REQUESTED는 존재검사도 아니다.

**다음은?** 이 opt-in을 호출하는 후보 orchestrator와 DATA/evidence scope·고정입력/새출력 계약이 후속 범위이며 현재 미구현이다.

## 이후 갱신

실제/전체/독립·보존 최종근거를 읽고 INDEX·변경이력·해설/구조/용어·대본/FAQ/시연을 함께 갱신했다. 전체 개발과10분 보고는 지속한다.

## 실제 고정3JSON validator 관측

Root가 opt-in 정책 source64/readiness16/saved_plan4/candidate64MiB·depth32로 기존 plan/source/oldreadiness만 읽어 validator1회·종료0/48.609초를 관측했다. 결과는3,929bytes·SHA `f17695093b5be51cfaa34326a6673e7b0711c158a8d127738cc0da6ec834f36a`이며 METADATA_INTEGRITY_VERIFIED·plan_integrity_validtrue다. 세 입력핀은 전후 불변이었다. 과거44 실제 결과에서 CLI-only caller_policy를 제외하면 typed 결과가 같았고 구버전을 중복 실행한 것은 아니다.

**이번 validator는 기존 full plan을 재계산해 저장계획과 대조했다.**69의 선택metadata 참조와 full_planner_recomputation NOT_PERFORMED는 다른 단위다.70이 새로운 split정책이나 학습gate를 실행한 것은 아니다. 계획excluded16/projected1095는 유지되며 현재 원본1384행·적격1111은 불변이다. candidate_validation은 NOT_REQUESTED/candidate_integrity_validnull/reference null로서 후보파일 존재여부 검증도 아니다.

실제 writer·후보orchestrator·후보manifest생성은 수행하지 않았고 raster/spatial/exactclasses·ready/train/sciencefalse다. opt-in writer의 성공/부분실패와 바이트동일성은 합성시험 근거이며 실자료후보생성 성공으로 발표하지 않는다.

## 다음 후보 orchestrator 설계 — PLANNED

읽기전용 설계 검토의 후속 범위는 caller가 고정한 source/readiness/saved_plan 세핀과 고정6주 split map·새 evidence 디렉터리를 받아 기존 bounded full validator→기존 write_plan→candidate typed roundtrip 검증→성공 receipt를 잇는 것이다.69의 다섯JSON 전체 참조검사를 필수 중복 실행하지 않는다. receipt가 없으면 미완료 candidate로 사용 불가임을 표시하고 부분새파일은 보존한다. 등록·학습·원본제외/분할/gate변경은 없다. 이 설계는 아직 PLANNED이며 구현·실제후보생성은 수행하지 않았다.
