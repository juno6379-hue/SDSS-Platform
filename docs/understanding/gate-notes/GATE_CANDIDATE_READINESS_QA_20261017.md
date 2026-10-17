# Gate Candidate Readiness QA 20261017 — 동일 정책·고정 후보의 학습 없는 준비성 검사

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | d474d5bce6c2a6c4bd8ba141c9256d15f6004631 (108까지 구현 검토 기준; 이 메타데이터 정리는 후속 문서 커밋) |
| evidence_paths | `backend/app/ml/candidate_readiness_qa.py`; `scripts/assess_staged_candidate.py`; `tests/test_candidate_readiness_qa.py`; `docs/implementation/73_candidate_readiness_qa.md`; `evidence/integration/candidate-readiness-qa-related-20261017.log`; `evidence/integration/candidate-readiness-qa-independent-20261017.log`; `evidence/integration/candidate-readiness-qa-live-cli-20261017.log`; `evidence/integration/candidate-readiness-qa-live-execution-20261017.json`; `evidence/integration/candidate-readiness-qa-live-validation-20261017.json`; `evidence/integration/candidate-readiness-qa-full-tests-20261017.log`; `evidence/integration/candidate-readiness-qa-live-integrity-20261017.json`; `data/first-group-candidate-readiness-qa-20261017/readiness.json`; `data/first-group-candidate-readiness-qa-20261017/qa-receipt.json` |
| confidence | 코드·관련/독립/전체로그·실제QA/독립대조/보존근거; 과학·운영승인아님 |
| status | TESTED_SYNTHETIC: guard·전체회귀; VERIFIED_REAL: 후보QA완료/4차단 BLOCKED; 과학/실행승인false |

## 쉬운 설명

같은 채점기준표인지 확인한 뒤 준비된 후보 자료를 기존 검사실에 넣어 검사만 한다. 합격이든 차단이든 검사결과를 정확히 기록하고 마지막에 검사완료 확인증을 남긴다. 검사를 끝냈다는 사실과 학습·운영 승인은 다르다. 검사도구가 ‘준비됨’을 관측하더라도 이 호출에서는 학습을 시작하지 않는다.

## 이론적 배경

72가 같은 바이트의 후보JSON을 DATA에준비했다면73은 candidate/stagingreceipt/policy/oldreadiness 네외부핀으로 입력과동일정책을고정하고기존 run을 재사용한다. metadata왕복일치와 실제raster/라벨 준비성QA는 다른검사다. oldreadiness는 동일정책/source/signature의 필요한 참조만 확인하며 과거전체QA를 소급재검증하지 않는다.

## 실제 코드·입력 계약

`assess_staged_candidate`는 DATA안의서로다른4일반JSON과 명시새DATA출력디렉터리를받는다. 한도는 candidate64MiB/stagingreceipt64KiB/policy1MiB/oldreadiness16MiB·깊이32다. 각역할별context로 strictUTF8/중복키/비유한수/typed값·최초/최종pin/stat/target을확인하고기존/링크/경합/원격·ADS·장치·scope이탈을거부한다.

staging v1 schema·17false·candidateSHA/size/path/version·고정6주map/projected/rowlineage를검사한다. oldreadiness핀은stage의readiness핀, old의원본source참조는stage원본핀/candidate원본lineage와같아야한다. 반면새QA보고서의manifest는현재stagedcandidate여야한다. 원본과후보의출처역할을뒤바꾸지않는다.71package/sourcemanifest를다시따라가거나72fullplan재계산을반복하지않는다.

`effective_policy={**default_policy(), **caller_policy}` 전체가oldpolicy와typed같아야한다. 고정6주/기간/밴드/클래스/분할/patch256·범위와실자료바닥을완화하지않는다. 기존esri정책은default에없는label_source키를가지므로지원enum과oldsignature일치를검사해허용한다. 초기base키만허용하던거부문제를Root가발견해수정·회귀했으며원정책파일을바꿔우회하지않았다.

기존 run 호출은 literal execute=False/resume=False/connectivity_diagnostics=True로고정한다. caller가execute/resume를전달하는CLI옵션은없다. 기존run은notexecute에서prepare/train/infer앞에반환하므로readyTrue도학습으로진행하지않는다.

## 결과·완료 receipt

새readiness.json의정확status/ready/blockers·동일policy·candidate참조pin/verifiedmanifest·signature·split계수·capture상태/비승인flags를확인한다. 반환객체와저장JSON이typed같고16MiB안으로읽혀야완료처리한다.4입력/report와경로를최종재확인한뒤64KiB이하 qa-receipt.json을마지막에exclusive쓴다.

| 상태 | 해석 |
|---|---|
| QA_COMPLETED | 검사완료; 결과가BLOCKED여도정상완료가능 |
| observed_gate_ready_for_training | 기존gate관측값이며receipt권한과분리 |
| receipt ready_for_trainingfalse | 실행/학습/과학/운영권한을부여하지않음 |
| capture실패/미포착 | gate를바꾸지않는상태면QA완료에기록가능; capture성공아님 |
| receipt부재/부분/무효 | 미완료; 새report존재만완료인증아님 |

## IO·한계

기존assess는영상/라벨을실제로읽고hash/QA하며guard가이를JSON-only로바꾸지않는다. 입력의bounded한도와후단report16MiB는guard의읽기·신뢰범위다. run내부read_text/원본IO/report쓰기·누적IO/RAM/CPU하드상한이아니고큰report쓰기자체를막는출력cap도아니다. Root실제runner의600초/표본RSS2GiB감시·GDALnetwork/PAMoff는별도관측이며OS하드cap은아니다.

예외/입력변경/report불일치·초과면새report/부분파일을보존하고유효완료receipt를남기지않는다. 원자snapshot/정확히한번은보장하지않는다. 기존원본/보고서/원장/lock·분할/모델/Registry는수정하지않는다. 과학적정확도·원본출처/정확행인증·누출완전해소·학습/운영승인은별도다.

## 시험 증거·현재성

관련19 PASS/12.065초·독립19 PASS/12.236초다. 네핀/동일정책/바닥/labelsignature·stage계약·report동등/status/capture·부분파일·경합/CP949·실행옵션금지를작은합성JSON/모의QA로확인했다. 실제run에모의assess가readyTrue를반환해도prepare/train/infer trap이호출되지않았다. 최종 전체 scripts/test.ps1은 **744건 중743 PASS·1 SKIP/356.067초/종료0**다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었고 deterministic 경계 시험은 통과했다. 관련19 PASS/12.065초·독립19 PASS/12.236초를 전체744에 중복 합산하지 않는다. 보호139참조·31기존 코어·네입력핀SHA와 카탈로그14기록 canonicalSHA가 불변이고 이전 snapshot 추적 backend/scripts/tests/data/frontend 변경은0이다. 신규코드/문서·QA파일은 있으므로 전체workspace변경0은 아니다. 원자snapshot/전체inventory를 보장하지 않는다. 이해에이전트는실제명령/시험을실행하지않는다.

72의QA NOT_PERFORMED/후보NOT_ASSESSED는당시이력이다.73실제후보QA는4차단BLOCKED로확인했고원본저장5차단은불변이다. 차단항목미관측을완전한누출해소/독립성승인으로추정하지않는다. 새API/UI/자동Dataset등록이없는내부QA-onlyCLI라이번화면변경은없고전체개발/10분보고는계속한다.

## 발표 1분

“후보와 staging확인증, 같은 정책과 과거 참조를 네지문으로 고정해 기존 준비성검사를 학습 없이 호출하도록 했습니다. 같은 채점표인지 먼저 확인하고 새 검사결과와 마지막 확인증을 남깁니다. 차단결과도 정상 검사완료이며 학습승인은 아닙니다. 검사도구가 준비됨을 관측해도 이 호출은 자료준비·학습·추론으로 넘어가지 않습니다. 실제 검사에서는 영상과 라벨을 읽고 품질을 확인하며, metadata일치만 본 이전 단계와 구분합니다.”

## 발표 5분·10분

1. **0~1분:** 같은채점표·검사실·완료확인증비유를말한다.
2. **1~2분:** 네외부핀·동일effectivepolicy·원본source와candidate참조를구분한다.
3. **2~3분:** literal noexecute/noresume/diagTrue·새report/receipt-last를설명한다.
4. **3~4분:** 합성readyTruetrap·실제QA/전체/보존근거를구분한다.
5. **4~5분:** BLOCKED도완료·영상IO/guard한도·승인false/새UI없음을말한다.

10분확장에서는label_source호환수정·oldreadiness부분참조검증·후단reportcap한계·capture미포착과QA완료·부분파일/원자성한계를설명한다.

## Q&A

**QA완료면학습가능한가?** 검사완료와gate관측/실행승인은별개다. literal executeFalse로학습하지않는다.

**이번도JSON만읽나?** guard입력/결과검증은JSON이지만기존assess는영상/라벨read/hash/QA를한다.

**같은정책은어떻게확인하나?** default와명시정책merge결과전체를oldpolicy와typed대조하고실자료바닥·signature를지킨다.

**과거QA전체를다시인증하나?** oldreadiness의필요한정책/source/signature부분을확인할뿐과거전체QA/생성원인을복원하지않는다.

**후보차단수는?** 실제73보고서는class7관련4개BLOCKED다. 원본저장5개와구분하며누출완전해소승인은아니다.

## 이후 갱신

실제QA/전체·보존최종근거를읽고INDEX·변경이력·해설/구조/용어·대본/FAQ/시연을함께갱신했다. 새QA결과를운영등록/학습승인이나전체프로젝트완료로보지않는다.

## 실제 후보 QA 관측 — 최종 전체/보존 확인

Root wrapper의 실제CLI1회는 종료0/202.344초·RSS표본197회최대532,074,496B·중지없음이었다.600초/2GiB표본중지기준이며OS하드cap/순간peak전수관측은아니다. PROJ networkOFF/GDAL PAMoff 등환경에서실제영상/라벨을읽고hash/QA했다. purediagnostic의추가IO0을전체QA의영상IO0으로설명하지않는다.

새readiness.json은11,842,410bytes·SHA `847343e1aa4ab9b67fd3bba36a2a9f91d716c2fd411af244e55bbfe1a8414019`, qa-receipt는3,030bytes·SHA `7b5ea8bba57bfc359076a0db27adce554b28c7d1796ae352b82ef9d94d79e38d`다. receipt는QA_COMPLETED, 관측gate는blocked/readyfalse다.1,368장면/적격1,095=628/217/250·verified_files4,285·capture CAPTURED_COMPONENTS_MATCH를기록했다.

현재후보차단은4개다. train/val/test의REFERENCE_CLASS_IMBALANCE(class7)3개와val/class7의CLASS_COVERAGE209픽셀1개다. 원본5차단에있던SHARED_SOURCE_CROSSES_FIXED_SPLIT항목은이번후보보고서에없다. 이것을모든분할누출해소·정확공간/표본독립성·원본출처/과학성능승인으로확대하지않는다. 원본보고서의5차단은보존하며후보의4차단과구분한다.

bare픽셀은원본/후보모두train1418/val209/test1025이며각bare기여patch0이다. 참조클래스대표성부족은남아학습BLOCKED다. 정식Dataset준비/등록·학습/추론·정산/재개는없고receipt ready/science/authfalse·refund0을유지한다. Root JSON독립대조에서동일policy/signature·원본class관련4차단과후보차단전체typed일치·공통verified4284개SHA/kind동일을확인했다. 새verified1개는stagedcandidate이고기존기록51개는후보목록에없다. bbox935028쌍/관측fixedsplit conflict0·완전선언identity1368은현재diagnostic범위다. bare픽셀train1418/val209/test1025와bare기여patch각0은그대로라클래스대표성부족이남는다. 실제assess는영상/라벨read/hash/QA를했고purediagnostic추가IO0과구분한다. 정식Dataset준비/Registry·학습/추론·정산/재개는0이며receipt권한false다.

최종 전체 scripts/test.ps1은 **744건 중743 PASS·1 SKIP/356.067초/종료0**다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었고 deterministic 경계 시험은 통과했다. 관련19 PASS/12.065초·독립19 PASS/12.236초를 전체744에 중복 합산하지 않는다. 보호139참조·31기존 코어·네입력핀SHA와 카탈로그14기록 canonicalSHA가 불변이고 이전 snapshot 추적 backend/scripts/tests/data/frontend 변경은0이다. 신규코드/문서·QA파일은 있으므로 전체workspace변경0은 아니다. 원자snapshot/전체inventory를 보장하지 않는다.

다음74는PLANNED다. old/newQA·qaReceipt·stageReceipt 네JSON/네callerSHA의읽기전용비교projection/API계약과web_ui수동비교카드·실제브라우저확인을검토한다. 자동assess·자동POST는없다. old보고서미저장physical장면수는null로두고stage선언1384/1368·newdiag관측1368을각각구분하며patch1111로장면수를추정하지않는다.
