# Gate Candidate Staging 20261017 — 검증된 후보 metadata를 DATA에 같은 바이트로 준비

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/ml/candidate_staging.py`; `scripts/stage_split_candidate.py`; `tests/test_candidate_staging.py`; `docs/implementation/72_candidate_staging.md`; `evidence/integration/candidate-staging-related-20261017.log`; `evidence/integration/candidate-staging-independent-20261017.log`; `evidence/integration/candidate-staging-live-cli-20261017.log`; `evidence/integration/candidate-staging-live-validation-20261017.json`; `evidence/integration/candidate-staging-full-tests-20261017.log`; `evidence/integration/candidate-staging-live-integrity-20261017.json`; `data/first-group-candidate-qa-stage-20261017/candidate.json`; `data/first-group-candidate-qa-stage-20261017/staging-receipt.json` |
| confidence | 코드·실제staging/독립대조·전체/보존근거; 준비성QA/영상복사/승인 아님 |
| status | TESTED_SYNTHETIC: 관련/독립19·전체회귀; VERIFIED_REAL: metadata staging; QA NOT_PERFORMED |

## 쉬운 설명

검수증이 있는 후보 문서를 다시 확인하고, 다음 검사가 읽을 수 있는 새 책상에 같은 문서만 복사한다. 사진 원본을 복사하거나 내용을 고치지 않는다. 새 책상에 놓았다는 확인증을 마지막에 남기지만 실제 검사를 끝냈다는 뜻은 아니다.

## 이론적 배경

71의 evidence 후보는 DATA밖이라 기존 assess에 직접 입력할 수 없다. DATA root를 repository 전체로 넓히는 대신, 엄격히 검증한 후보 JSON만 DATA의 새metadata경로로 옮긴다. 입력·출력 scope를 유지하고 동일 바이트·SHA를 보존하면 다음 QA의 입력을 명시적으로 고정할 수 있다. staging완료·QA완료·학습준비·Dataset등록은 각각 다른 상태다.

## 함수·검증·복사 흐름

`stage_split_candidate`는 caller가 명시한71 receiptSHA와 source/readiness/saved_plan 외부3pin을 받는다. receipt에적힌SHA만신뢰하지않고외부핀과일치해야한다. DATA/evidence 양방향중첩을거부하고기존패키지·3입력·새DATA디렉터리/부모의경로/파일identity를검사한다. 새디렉터리의부모는이미존재해야하며기존/링크/ADS·장치·모호경로를덮어쓰지않는다.

receipt는64KiB 별도 BoundedJSONIO로읽고 정확한schema/key/type/status·15falseflags·size/name·고정6주map·partition·projected계수/lineage를검사한다. maincontext는source/readiness/saved_plan/new_plan/candidate 다섯JSON을각역할한도내에서핀대조한다. 원래plan과패키지plan이typed같아야하고source/candidate물리행수·계획/receipt계수가맞아야한다.

기존 fullcandidate validator를1회 호출해 저장계획 재계산·candidate EXACT_METADATA_MATCH를확인한다. 최초/최종입력핀/경로를재대조한뒤 새DATA디렉터리를exclusive생성하고 `_copy_bytes`로candidate원본JSON바이트만64KiB청크로복사한다. 복사중descriptor/stat·성장/earlyEOF·길이·SHA를검사한다. 새파일을엄격JSON으로읽어같은SHA/size/typed문서인지확인한뒤최종검사직후작은staging-receipt.json을마지막에쓴다.

| 상태 | 의미 |
|---|---|
| METADATA_STAGED_FOR_QA | 같은바이트metadata를다음QA입력으로준비 |
| qa_status NOT_PERFORMED | 아직후보준비성검사미실행 |
| NEXT_QA_NOT_PERFORMED | 다음단계가남아있음 |
| ready/executed/registeredfalse | 학습/실행/운영등록승인없음 |
| receipt부재/부분/무효 | staging미완료; 파일존재만으로완료아님 |

전후핀/대상검사는OS원자snapshot·하드RAM/CPU/누적IO보장이아니다. 복사중실패하면부분새파일을보존하고자동삭제하지않는다. source/readiness원본·71패키지·원장/lock/분할/모델을바꾸지않는다. 원본raster/label/픽셀파일을복사하거나읽지않고JSON바이트만다룬다.

## 시험 증거

최종관련19 PASS/23.740초다. 중간17/22.010은이력으로구분한다. receipt/외부핀·exacttyped상태/size/name·고정map·fullcandidate검증·변조/성장/earlyEOF·scope양방향중첩·partial/nooverwrite/CP949·원본불변·QA/영상/등록미호출을작은합성JSON으로확인한다. 최종독립19 PASS/25.510초도확인했다. receipt성장시64KiB+1=65,537바이트차단과별도context·동일바이트/루트분리·변조/부분파일/QA미호출을재검증했다. 최종 전체 scripts/test.ps1은 **725건 중724 PASS·1 SKIP/338.008초/종료0**다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었고 deterministic 경계 시험은 통과했다. 관련19 PASS/23.740초·독립19 PASS/25.510초는 전체725에 중복 합산하지 않는다. 보호137참조(이전134+71패키지3)·30기존 코어SHA와 카탈로그14기록 canonicalSHA가 불변이며 이전 snapshot 추적 backend/scripts/tests/data/frontend 변경은0이다. 신규코드/문서·staging파일은 있으므로 전체workspace변경0은 아니며 원자snapshot/전체inventory 보장도 아니다. 이해에이전트는실행하지않는다.

## 현재성과 한계·UI

실제metadata staging/receipt성공을Root근거로확인했다. 후보QA는NOT_PERFORMED이며후보의실제차단수/누출해소는모른다. 기존원본readiness5차단·원본적격1111·계획후보1095·terminal2missing·예약136,314,880B·환불0은유지한다. metadata완전성은원본진실·정확행인증·과학/운영승인이아니다.

새API/UI/Registry계약이없는내부CLI이므로이번화면변경은없다. 기존저장출처조회카드의원본5차단과새후보QA미실행을구분한다. 전체개발과10분보고는지속한다.

## 발표 1분

“후보 검수증과 세 입력 지문을 다시 확인하고, 후보 JSON만 같은 바이트로 DATA의 새 경로에 준비하는 기능을 만들었습니다. 사진이나 라벨 원본을 복사하지 않고 기존 입력범위를 넓히지도 않습니다. 기존 전체후보 검증을 통과한 뒤 복사한 문서의 지문과 크기를 확인하고 마지막에 staging확인증을 남깁니다. 이는 다음 검사입력을 준비한 것이며 실제 준비성 QA·학습·Dataset등록은 아직 아닙니다. 부분파일이나 무효확인증을 성공으로 표시하지 않습니다.”

## 발표 5분·10분

1. **0~1분:** 검수된문서를새검사책상에옮기는비유를말한다.
2. **1~2분:** evidence/DATA분리·receipt핀/외부3핀·strict15false를설명한다.
3. **2~3분:** 기존fullcandidatevalidator→rawJSON복사→동일SHA/size→receipt-last를보여준다.
4. **3~4분:** 합성/독립·실제/전체/보존근거와staging/QA시점을구분한다.
5. **4~5분:** 영상복사0·QA/학습/등록0·다음73계획과한계를말한다.

10분확장에서는receipt64KiB별도context·다섯JSONmaincontext·scope양방향중첩·복사성장/earlyEOF/부분파일·원자성한계를설명한다.

## Q&A

**사진원본을DATA에복사했나?** 후보JSONmetadata만같은바이트로복사하며영상/라벨파일은아니다.

**QA를완료했나?** staging은QA입력준비이며qa_status NOT_PERFORMED다.

**receipt만믿나?** caller의receiptSHA와외부3핀·정확schema/size/flags·fullcandidate를검증한다.

**후보차단은몇개인가?** 실제QA미실행이라아직모르며원본보고서5차단과구분한다.

**다음은?** stagingreceipt/핀검증후동일정책·기존run_experiment noexecute/noresume+diagnostics·새readiness출력으로후보QA1회를계획한다. 아직실행하지않았다.

## 이후 갱신

실제/독립/전체/보존최종근거를읽고INDEX·변경이력·해설/구조/용어·대본/FAQ/시연을함께갱신했다. 다음73의후보QA는PLANNED이며현재실행하지않았다.

## 다음73의 고정 QA 호출 설계 — PLANNED

사전읽기에서 남은 재사용 공백은 staged candidate·작은 stagingreceipt·정책파일의 외부SHA와새QA출력을 확인해 기존 run(...execute=False, resume=False, connectivity_diagnostics=True)을 고정 호출하는 작은 guard다.72의 fullplan재계산을 다시 필수 중복하지 않고 candidate/receipt 외부핀으로 metadata범위를 고정하며 실제raster QA는 assess가 수행하도록 한다.

동일한 역사정책을 자동확인하려면 oldreadiness가 네번째 고정JSON으로 필요하다. 원설정파일에는 defaults필드가 없을 수 있어 effectivepolicy={**default_policy(), **policy}를 oldpolicy와 typed대조하는 설계다. QA결과 BLOCKED여도 검사완료일 수 있으며 예외/입력변경 시 새report는 보존하고 완료receipt는 남기지 않는다. guard/실제후보QA 모두 아직 미구현·미실행이고 다음Gate에서 별도 검증한다.

## 실제 metadata staging 관측

Root CP949 CLI1회는종료0으로 `data/first-group-candidate-qa-stage-20261017/candidate.json`과stagingreceipt를생성했다. candidate는53,247,999bytes·SHA `2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158`로71evidence후보와같다. stagingreceipt는3,675bytes·SHA `b8224cb3eb5c5ef0accf0cab10359401d792719e6fd8cae0b610279e759404dd`다. Root가코어를재호출하지않고stream SHA·size/외부핀·패키지참조/17false를독립대조했다.

후보1368행·원본1384행·projected적격1095이며원본적격1111은변경하지않았다. status METADATA_STAGED_FOR_QA와qa_status NOT_PERFORMED/후보준비성NOT_ASSESSED를함께확인했다. 영상/라벨복사·assess·QA·등록·훈련은없다. 실제runtime은별도계측하지않아초수를주장하지않는다.

독립검증보조스크립트의초기relativepath slash가정은Windows기본backslash와맞지않아assert가실패했다. 기대값을nativepath기준으로고쳐같은산출물을다시대조해통과했으며생산코드변경이나실제CLI재실행은없었다. 이보조검증실패를staging코드결함이나중복생성으로보고하지않는다.
