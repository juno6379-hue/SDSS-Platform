# Gate Execution Input Binding 20261017 — 실행 전달 입력 선언의 순서 대조

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/execution_input_binding.py`; `tests/test_execution_input_binding.py`; `docs/implementation/77_execution_input_binding.md`; `evidence/integration/execution-input-binding-related-20261017.log`; `evidence/integration/execution-input-binding-independent-20261017.log`; `evidence/integration/execution-input-binding-live-validation-20261017.json`; `evidence/integration/execution-input-binding-live-replay-20261017.py`; `evidence/integration/execution-input-binding-full-tests-20261017.log`; `evidence/integration/execution-input-binding-live-integrity-20261017.json` |
| confidence | 코드·합성/독립검산·저장요청의로컬선언재생; 실제executor전달/파일검증 미확인 |
| status | TESTED_SYNTHETIC: guard/전체회귀; 실제저장참조+로컬재생 UNKNOWN/BLOCKED의혼합근거; 실행미연결 |

## 쉬운 설명

주문서에적힌물품의순서·버전·지문과배달직전에전달하려는목록을나란히읽는다. 목록이같아도실제상자속물품을검사하거나배달승인을한것은아니다. 옛주문서에중요한검수지문이없으면배달목록에새지문을적었다고옛주문서를채워주지않고‘모름’으로남긴다.

## 이론적 배경

Registry등록/현재resolve·제출snapshot·현재lineage는각각다른기능이다. 새순수helper는두ordered선언이그대로전달되는지에만집중한다. expected를신뢰할수있는제출기록에서구성하고실제executor에넘기는supplied를포착하는adapter는아직없다. caller가두값을같게만들어MATCH를얻는것만으로출처·실행신원·권한/파일진실을증명할수없다.

## 입력·실제함수

`compare_execution_input_bindings(expected, supplied)`는양쪽exactdict의job_id/agent_id/trace_id/bindings 정확히4키를받는다. bindings는1..64개의ordered list이며각row필수키input_index/id/version/sha256·선택role/manifest_sha256만허용한다. input_index는exactint로목록위치와같아야하고bool/float는거부한다. 문자열은exactstr1..256자·공백만/C0/C1/DEL/surrogate를거부하며trim/대소문자변환/강제변환/기본role주입은없다. latest/current는고정version이아니므로거부한다.

sha256는assetbytes에대한선언pin, manifest_sha256는Registrycanonicalmanifest의선언pin이다. helper가실제asset/manifestbytes·Registry를읽는것은아니다. 같은id의서로다른version은허용하고같은id/version반복도pin이같으면허용한다. 같은id/version의자산SHA나명시manifestSHA끼리상충하면차단한다. role은용도별로달라도되지만position별expected/suppliedpresence/값이같아야한다.

URI/AOI/model/params·Jobrequest전체·ACL/현재readiness/실제bytes/TOCTOU는scope밖이다. 기존upstreamJobschema를수정하지않은내부RFCv1이며선택manifestpin을원래schema에생긴필드처럼설명하지않는다.

## 상태우선순위·legacy

| 조건 | 결과 |
|---|---|
| schema/type/순서·내부pin충돌·Job/Agent/Trace/개수/id/version/SHA/role불일치 | BLOCKED |
| expected명시manifestpin의supplied누락/변조 | BLOCKED |
| 다른차단없지만expectedmanifestpin미기록 | UNKNOWN |
| 명시된expectedpin이모두있고선언전체같음 | MATCH |

BLOCKED > UNKNOWN > MATCH다. expected미기록인데supplied에새pin을더해도UNKNOWN이며동일id/version다른row의pin을현재row로소급전파하지않는다. role양쪽부재는같은미기록으로대조하지만한쪽만있으면차단하고null/빈값/defaultrole은정상부재로간주하지않는다.

## 출력·hash·승인한계

issues는side/input_index/code만반환하고rawid/version/role/SHA/URI·예외원문을노출하지않는다. expected_bindings_sha256는유효expected의bindings배열만Python sort_keys/compact UTF8로hash한값이며RFC8785나Job/Agent/Trace전체digest가아니다. 순서/index/optionalkeypresence·role/pin을포함한다. expectedinvalid면digestnull이고suppliedinvalid여도expectedvalid면digest가남을수있다.

declarations_match는MATCH에만true지만실행승인이아니다.12approvalfalse·network/source쓰기/database/resolver/executor5종호출0이며입력객체불변이다. 실제executor/Job경로에미통합이고futuretrustedexpectedadapter·현재resolver/bytes확인·ACL/READYgate가필수후속이다. 기존gate를우회하지않는다.

## 시험증거

관련14 PASS/0.037초·독립14 PASS/0.014초다. 별도oracle648조합은MATCH6/UNKNOWN9/BLOCKED633으로모두같았으며단위/전체회귀에합산하지않는다. schema/type/상한·legacy·순서/rolepresence·pin누락/변조/상충·텍스트/버전·canonicalhashscope·원문비노출/입력불변·무IO를합성검증했다. 초기privacy시험의짧은id부분문자열이training키에도일치하던assert를quotedJSONscalar기준으로고친것은시험가정수정이며생산데이터누출재현이아니다.

## 실제저장기록과로컬재생의혼합근거

Root가readonlySQLite에서실제legacyJob2개를읽었다. 각각request ref1개·제출snapshot없음·manifestpin미기록이다. expected를저장request의선택선언으로구성하고supplied도같은선언으로로컬재생했으므로신뢰된제출capture나실제executor전달capture가아니다.

같은선언replay와supplied에fakepin추가replay는UNKNOWN, version/trace변조replay는BLOCKED여서총8관측중UNKNOWN4/BLOCKED4였다. 실제MATCH/실행연결성공을주장하지않는다. 별도replay8도시험건수에더하지않는다. Rootharness가DB를읽은것과순수helper database_calls0을구분한다. 카탈로그14recordbody/원문hash는전후같았고자산검증/Job실행은없다. 최종 전체 scripts/test.ps1은 **789건 중788 PASS·1 SKIP/346.172초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련14 PASS/0.037초·독립14 PASS/0.014초, 별도oracle648조합과Root로컬replay8관측은전체789에합산하지않는다. 보호141참조·35기존코어SHA와카탈로그14기록canonicalSHA/기존Job body가불변이고이전snapshot추적code/data/tests/frontend변경은0이다. 신규코드/문서/evidence는있으므로전체workspace변경0/원자snapshot보장이아니다. 이해에이전트는DB나replay를실행하지않고증거만읽었다.

## UI·현재성

공개API/UI/CLI를추가하지않은순수내부경계라직접화면변경/프론트재시험/브라우저확인은없다. 기존저장비교카드·후보4차단/원본5차단·나지부족·terminal2missing/예약136,314,880B·모델/분할은유지한다. 전체개발과10분보고는계속하며단일guard구현을실행기완성/전체프로젝트완료로보지않는다.

## 발표1분

“제출 입력과 실행기에 전달할 입력의 순서·버전·지문을 대조하는 순수 기능을 만들었습니다. 두 목록이 같아도 실제 파일이나 실행 승인을 확인한 것은 아닙니다. 옛 기록에 manifest 지문이 없으면 새 전달 목록에 지문을 추가해도 ‘모름’을 유지합니다. 실제 legacy Job 두 개의 선언을 로컬에서 재생했을 때도 모름과 차단만 관측했습니다. 실제 실행기를 포착하거나 Job을 실행하지 않았습니다. 신뢰된 제출 기록과 실행 경계를 연결하고 현재 파일·권한·준비도를 별도로 확인하는 일은 다음 과제입니다.”

## 발표5분·10분

1. **0~1분:** 주문서/전달목록/실제상자검사차이를말한다.
2. **1~2분:** 네envelope키·orderedrefs·asset/manifest선언pin을설명한다.
3. **2~3분:** BLOCKED/UNKNOWN/MATCH와legacypin역채움금지를설명한다.
4. **3~4분:** 합성14·oracle648·실제2기록/로컬8replay·전체/보존근거를구분한다.
5. **4~5분:** 실제executor미연결·파일/ACL/READY검사후속·12false·UI없음을말한다.

10분확장에서는role부재/null·row간pin비전파·서로다른version허용·bindings만hash·safeissues/원문비노출·harnessDB읽기/helper무IO차이를설명한다.

## Q&A

**MATCH면바로실행하나?** 선언일치일뿐executionauthorizedfalse·실제executor미연결이다.

**같은legacy기록인데왜UNKNOWN인가?** expectedmanifestpin이없으며supplied추가pin이나다른row로옛기록을채우지않는다.

**실제Job2개를실행했나?** readonly저장선언조회/로컬재생이며Job/실행기를호출하지않았다.

**hash에Job/Trace도포함되나?** expectedbindings배열만이고Job/Agent/Trace는별도대조한다.

**기존resolver와무엇이다른가?** 전달선언을순수비교하며현재Registry/자산bytes/URI/권한확인은기존기능의후속책임이다.

## 이후갱신

전체/보존최종근거를읽고INDEX·변경이력·계약/Orchestrator/구조/용어·대본/FAQ/시연을함께갱신했다. trustedadapter/실행연결은아직후속미구현이다.

## 다음78의 선택적 제출 capture — PLANNED

다음 검토 방향은 기존 resolver 응답을 유지하면서 같은 resolve_version 검증 pass의 record로 비공개 capture를 함께 만드는 내부 pair 함수와 공통 private pass다. 새 Job에만 versioned execution_input_binding_capture 별도 확장을 저장하는 방안이며 기존 input_resolution/HTTP/schema/replay 호환이 목표다. legacy·같은 멱등 replay는 재조회나 역채움하지 않고 추가 Registry 조회도 하지 않는다. 초과·해석 실패는 capture UNAVAILABLE로 기존 gate를 유지하는 방안이다. 현재는 설계 대기·route/저장 변경0이고 상세 schema는78에서 검증한다.77은 실제 실행 경로 미연결 그대로다.
