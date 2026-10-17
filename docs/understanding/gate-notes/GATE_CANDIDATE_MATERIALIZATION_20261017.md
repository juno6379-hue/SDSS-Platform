# Gate Candidate Materialization 20261017 — evidence 전용 후보와 왕복 검증 receipt

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/ml/candidate_materialization.py`; `scripts/materialize_split_candidate.py`; `tests/test_candidate_materialization.py`; `docs/implementation/71_candidate_materialization.md`; `evidence/integration/candidate-materialization-related-20261017.log`; `evidence/integration/candidate-materialization-independent-20261017.log`; `evidence/integration/candidate-materialization-live-cli-20261017.log`; `evidence/integration/candidate-materialization-live-validation-20261017.json`; `evidence/integration/candidate-materialization-full-tests-20261017.log`; `evidence/integration/candidate-materialization-live-integrity-20261017.json`; `evidence/integration/candidate-materialization-live-20261017/plan.json`; `evidence/integration/candidate-materialization-live-20261017/candidate.json`; `evidence/integration/candidate-materialization-live-20261017/receipt.json` |
| confidence | 코드·전체/독립로그·실제metadata생성/독립대조·보존근거; raster준비성/학습승인 아님 |
| status | TESTED_SYNTHETIC: 관련/독립·전체회귀; VERIFIED_REAL: metadata후보/receipt 생성; 후보QA NOT_ASSESSED·BLOCKED |

## 쉬운 설명

기존 계획서를 새 증거 폴더에 옮겨 실제 후보 목록을 만들고, 다시 읽어 계획과 정확히 같은 목록인지 확인한 뒤 마지막에 검수증을 남긴다. 목록 파일이 있다는 것만으로 검수 완료가 아니다. 검수증이 없거나 유효하지 않으면 미완료이며 일부 새 파일은 지우지 않고 남긴다. 이 검수는 metadata 문서에 대한 것이지 영상·라벨의 학습 적합성 검사는 아니다.

## 이론적 배경

70의 개별 JSON IO 한도를 재사용해 full validator→기존 writer→candidate exact typed roundtrip을 순서대로 연결했다. 기존 planner/writer/validator를 복제하지 않는다. 새 evidence 디렉터리와 마지막 receipt가 단계별 성공 범위를 설명한다. receipt의 상태·출력 SHA를 검증해야 하며 파일 존재·파일 이름만 믿어 완료로 취급하지 않는다.

## 코드·입출력 계약

`materialize_split_candidate`는 정확히 source/readiness/saved_plan 세caller SHA와 고정6주 split map을 사용한다. source/readiness는 DATA 아래, saved_plan과 신규 출력 디렉터리는 evidence 아래로 제한하고 evidence는 DATA 밖이어야 한다. 세 일반파일은 경로/파일 identity가 서로 달라야 한다. 원격/장치/ADS·모호경로·기존/링크 출력·입력별칭을 거부한다. 새 디렉터리의 부모는 미리 존재해야 하며 기존 디렉터리를 재사용하지 않는다.

입력한도는 source64/readiness16/saved_plan4MiB, candidate64MiB·깊이32다. 최초 읽기 context로 pin·대상/stat를 유지하고 기존 bounded fullvalidator로 저장계획을 재계산한다. 입력/경로를 재검사한 후 새 디렉터리를 만들고 기존 write_plan으로 plan.json·candidate.json을 생성한다. plan4/candidate64MiB 출력은70의 사전측정·exclusive stream을 사용한다.

생성된 candidate는 PLANNED_DERIVED_CANDIDATE·executedfalse·learning_readyfalse여야 한다. 생성 plan과 candidate를 읽어 새candidate SHA를 고정하고 기존 fullvalidator를 candidate_path와 함께 호출해 EXACT_METADATA_MATCH/candidate_integrity_validtrue를 확인한다. 원본 retained 행의 정확한 typed 복사·lineage·비실행 계약 왕복 검증이다. 최종 입력/경로/대상을 확인한 직후64KiB한도의 receipt.json을 마지막으로 exclusive쓰기한다.

| 파일·상태 | 의미 |
|---|---|
| plan.json | 기존 저장계획 metadata 사본 |
| candidate.json | 원본을 바꾸지 않는 evidence전용 파생 후보 metadata |
| receipt.json | 출력이름/SHA/크기·세입력핀·계수·고정map·비승인상태를 기록 |
| METADATA_ROUNDTRIP_VERIFIED | 후보 문서 왕복 일치; 영상준비성/과학승인 아님 |
| PLANNED_DERIVED_CANDIDATE | 실행/학습준비 false인 후보 |
| receipt 부재/무효 | 미완료 후보이며 사용불가 |

마지막 검사와 receipt쓰기는 OS원자 snapshot이 아니다. receipt를 쓴 뒤 추가입력검사를 두어 실패하면서 성공표시가 남게 만들지 않도록 최종검사를 직전에 배치했다. 디스크오류·중간실패로 부분파일/완료된 형제파일이 남을 수 있고 자동삭제·복구·원장정리를 하지 않는다. 후속 사용자는 strict receipt schema와 출력SHA검사를 해야 하며 이번단위가 별도 검증소비자/등록/배포를 구현한 것은 아니다.

## 시험 증거

관련60 PASS/26.246초는 신규15+기존45다. 독립신규15 PASS/13.445초에서 추가결함이 없었다. 작은합성JSON으로 scope/세핀/고정정책·기존validator/writer호출·exactcandidate왕복·receipt-last/부분파일·경로교체·candidate변조·실행/승인false·원본불변을 확인한다. 최종 전체 scripts/test.ps1은 **706건 중705 PASS·1 SKIP/329.107초/종료0**다. SKIP은 기존 Windows symlink 생성권한 제약이며 deterministic 경계 시험은 통과했다. 관련60 PASS/26.246초(신규15+기존45)·독립신규15 PASS/13.445초를 전체706에 중복 합산하지 않는다. 보호134참조·29기존 코어SHA와 카탈로그14기록 canonicalSHA가 불변이고 이전 snapshot 추적 backend/scripts/tests/data/frontend 변경은0이다. 신규코드/문서·candidate패키지는 있으므로 전체workspace변경0이 아니며 원자snapshot/정확히한번 반영 보장도 아니다. 이해에이전트는 실행하지 않는다.

## 현재성과 한계

Root 실제 CP949 CLI1회는 종료0으로 evidence전용 plan/candidate/receipt 패키지를 생성했다. candidate는53,247,999bytes/SHA2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158, receipt는3,936bytes/SHA889c549d8c8620a33fb90503313157313c520088809f2e16304c1d7fdcc3be51이다. plan22,298bytes는 기존 savedplan과 바이트 동일하다. Root 독립 strictJSON/SHA·size/type 대조로candidate1368행 전체가source1384의retained행과typed일치함을 확인했다.16제외는새candidate에만 적용됐고 원본은불변이다. 후보projected적격1095=628/217/250과 원본1111=628/233/250을 구분한다. 실제명령runtime은 정확히 측정하지 않아 초수를 주장하지 않는다.

receipt는 METADATA_ROUNDTRIP_VERIFIED/candidate PLANNED_DERIVED_CANDIDATE/readiness BLOCKED지만 후보의 실제 준비성 QA는 아직 NOT_ASSESSED다. 기존 원본 저장보고서의5차단은 유지하며 후보의 실제 차단수는 아직 모른다.15개 비승인/비실행 falseflags·refund0·exactlyonceUNKNOWN을 확인했고 Registry등록/훈련·raster/공간/정확클래스/assess는 수행하지 않았다.70까지 미생성은 당시 이력이고71에서 metadata후보가 생성됐다는 현재 사실을 구분한다.

원본 raster/label·113source manifest·기하/정확클래스·누출해소·assess는 검사하지 않는다. 후보문서생성과 원본행제외/재배정은 다르다. ready/science/authenticity/exactrowbinding/execution/Registry/정산/자동재개false·refund0·exactlyonceUNKNOWN, 기존5차단·원본1111·terminal2missing·예약136,314,880B·모델/분할은 유지한다. 새API/UI가 없는 내부CLI라 화면변경대상은 없다.

## 발표 1분

“새 증거 폴더에 기존 계획을 이용한 후보 목록을 만들고, 다시 읽어 계획과 정확히 같은 metadata인지 검증한 뒤 마지막에 검수증을 남기는 흐름을 만들었습니다. 목록이 있다는 것만으로 완료가 아니며 검수증이 없거나 틀리면 미완료입니다. 중간에 남은 파일은 자동으로 지우지 않습니다. 후보를 만들더라도 원본행을 지우거나 Dataset을 운영 등록·학습하는 것은 아닙니다. 검사한 것은 문서 왕복 일치이며 영상·클래스·독립성 재검사와 기존 학습 차단은 별도로 남습니다.”

## 발표 5분·10분

1. **0~1분:** 새폴더·후보목록·마지막검수증 비유를 말한다.
2. **1~2분:** 세callerpin·DATA/evidence scope·기존bounded코어재사용을 설명한다.
3. **2~3분:** fullvalidator→writer→exactroundtrip→receipt순서를 보여준다.
4. **3~4분:** 합성/독립·실제/전체·보존 근거와70의역사시점을 구분한다.
5. **4~5분:** receipt없으면미완료·부분파일보존·Registry/훈련/영상검사없음을 말한다.

10분 확장에서는 파일identity·최종핀검사/receipt-last·출력2개한도·성공receipt와후속strict소비계약·원자snapshot미보장을 설명한다.

## Q&A

**후보파일만 있으면 완료인가?** strict receipt와 출력SHA가 유효해야 하며 없거나 무효면 미완료다.

**운영Dataset이 등록됐나?** evidence전용metadata후보이며 Registry등록/게시없다.

**원본에서16행을 지우나?** 새후보행을 선택할뿐 원본행제외/삭제/재배정은 없다.

**왕복검증이면 학습 가능한가?** metadata일치이며 raster/공간/정확클래스/준비도·과학승인은 false다.

**실패하면 파일은?** 부분새파일을보존하고자동삭제하지않는다. 파일존재를성공으로해석하지않는다.

## 이후 갱신

실제CLI·전체/보존 최종근거를 읽고 INDEX·변경이력·해설/구조/용어·대본/FAQ/시연을 함께 갱신했다. 전체개발/10분보고는 지속한다.

## 다음72 읽기 설계 — PLANNED

기존 assess는 입력 manifest도 DATA안으로 한정하므로 evidence의 candidate를 직접 QA하지 못한다. DATA root를 repository전체로 넓히지 않는다. 후속 최소설계는 먼저 strict receipt consumer로 세입력/두출력 SHA·size·typed false flags/lineage/fullcandidate를 확인한 뒤, 같은 SHA의 candidate JSON만 새 DATA metadata 경로에 exclusive staging하고 기존 run_experiment를 execute/resume없이 diagnostics와 새 readinessoutput으로 재사용하는 것이다.

현재 CLI에 --readiness-only 플래그는 없다. 기존 noexecute 호출을 별도 플래그가 있는 것처럼 설명하지 않는다. 이72는 읽기설계일 뿐 receiptconsumer구현·staging·candidate QA는 아직 수행하지 않았다.71의metadata후보/receipt생성은실제로확인됐지만candidateQA는NOT_ASSESSED다. staging은 원본영상/원본manifest변경이나 Registry등록·학습과 다르며 범위를 별도 Gate로 검증한다.
