# 228 — 명시 128MiB manifest profile 격리 구현

상태: **IMPLEMENTED_IN_ISOLATED_COPY / TESTED_SYNTHETIC**. 공유 제품 반영과 실제128MiB 운영 QA는 **PLANNED**다. Root227 실제 QA와 충돌하지 않도록 `evidence/integration/preprocess228-workspace-20261018/` 안의 코드 사본만 수정했다. 실제 운영source/원장/raster/model을 읽거나 복사하지 않았고, 실제 QA·native·HTTP·collector 재실행은0이다. 공유backend/scripts/tests/configs 제품은 수정하지 않았다. 실root에서는 이 문서만 새로 작성한다.

## 목적과 입력 시점

Root 전달 현재source는66,826,849바이트이며64MiB(67,108,864)까지282,015바이트 여유다. 이 숫자는 운영파일을 이번 담당이 다시 읽어 얻은 결과가 아니다. [217 검토](217_manifest_budget_and_preprocessing_scale_review.md)의 후속으로 다음 수집 이후 전처리가 여러64MiB cap에서 막히는 위험을 미리 검증했다. 현재source에128MiB 옵션을 적용해 통과시켰다는 주장은 하지 않는다.

격리폴더의 `input-source-manifest.json`은 backend/scripts/tests/configs의 필요한 코드·정적설정 사본별 경로/바이트/SHA다. 운영data/node_modules/model/원장실물은 복사하지 않았다. `backend/app/data`는 이름이data여도 제품Python소스이므로 포함한다. Temp시험을 위한 격리 빈data/evidence 디렉터리는 운영자료 사본이 아니다. 변경한 기존코드는 입력SHA와 일치하는 `baseline-code/`에도 보존했다. 코드복사는 순차 snapshot이며 다중파일 원자 snapshot으로 표현하지 않는다.

의존성은 격리 `.runtime/sitecustomize.py`가 기존 설치 `.runtime` 라이브러리 경로를 연결한다. 라이브러리를 복제하거나 모델을 읽지 않는다. 시험cwd와 모듈`__file__`이 격리루트 안임을 확인했다. 최초cwd/import 경로가 불명확한 시험은 중단해 성공 근거에서 제외했고 원로그를 남겼다.

## 선택 방법과 고정 profile

격리사본의164 CLI에만 다음 선택지가 있다.

```text
python scripts/prepare_priority_candidate164.py ... --manifest-profile bounded128m-3000-v1
```

공유실행중서버/원래164에는 아직 이 옵션이 적용되지 않았다. 운영명령으로 그대로 실행하지 않는다. 미지정이면 기존64MiB 정책·v1 영수증·기존 산출을 유지한다. 임의 이름·bool·수치·빈profile은 거부한다. 옵션이source byte 한계를 만났다고 자동선택/상향/재시도되지 않는다.

명시 profile descriptor는 읽기전용으로 고정했다.

| 항목 | 고정값 |
|---|---:|
| profile name | `bounded128m-3000-v1` |
| source/candidate JSON 입력·candidate 출력 | 134,217,728바이트 |
| source scenes+historical_noneligible_patches / candidate 총행 | 3000 |
| JSON 깊이 | 32 |
| `_tree` 검사 방문노드 상한 | 4,000,000 |
| 한 명시 작업의 누적 계측 JSON I/O | 17,179,869,184바이트(16GiB) |

노드값과16GiB는 이번 격리 profile의 **명시 prototype 상한**이다. 실제 rich3000행 cohort의 충분성을 측정해 승인한 값이 아니다. byte/row/node/누적I/O 어느 한계를 만나도 중단하고, 동적으로 더 올리지 않는다. 다른 상한이 필요하면 새profile version·독립검토가 필요하다.

128MiB와16GiB는 **로컬 JSON 소비/반복검증 비용**이다. label/raster 개별64MiB, 원격COG64MiB+metadata1MiB/batch, 원격추가전역4GiB, 실제물리3000, 최종80%/95%·나지/분할/모델 gate,2초/첫429는 수정하지 않았다. readiness16MiB·plan4MiB·작은receipt64KiB도 그대로다. 기본모드의source64MiB를 전역상수 치환으로 올리지 않았다.

## 구현 연결과 범위

신규격리 `backend/app/ml/manifest_resource_profile.py`는 정확profile명·descriptor digest·ContextVar 작업scope·누적JSON I/O계측·receipt v2 binding을 제공한다. 164에서 명시선택한 scope가 snapshot→계획→strict materialization→staging→QA까지 이어진다. 중첩호출의옵션미지정은이미명시선택된상위scope를계승하며, scope밖의기본None은64MiB다. finally에서scope를되돌려다음작업에profile이남지않는다.

기존프로젝트는`app.ml`과`backend.app.ml`두import표기를쓴다. 같은작업의budget이갈라지지않도록프로세스내단일ContextVar를두표기에서공유한다. profile을전역으로활성화하는것이아니다. 독립요청/작업scope는서로다르고thread/request간기본profile도바뀌지않는다.

| 격리 변경파일 | 연결 내용 |
|---|---|
| `scripts/prepare_priority_candidate164.py` | 명시CLI선택, snapshot128cap, boundedJSON읽기/계획I/O context, JSONdigest·copy·write계측, summary에선택profile/summary쓰기직전I/O값 |
| `backend/app/ml/split_json_io.py` | source/candidate 역할의기존64cap만profile128로치환. depth/typedstrictparser·row/node검사, read/write/verify누적I/O검산 |
| `candidate_materialization.py` | profile input/outputcap과strict roundtrip 유지, package receipt v2 |
| `candidate_staging.py` | 정확v2/profile검증→원바이트copy/strict검증→v2 staging receipt, 선언행3000검사 |
| `candidate_readiness_qa.py` | candidate128/작은refcap구분, v2 stage/행선언검사→기존QA전용실행→v2 QA receipt |
| `readiness.py` 및 `scripts/run_experiment.py` | 명시scope의JSON manifest/metadata 읽기·보고서쓰기 계측/자원검사. 실제raster/class/품질판단알고리즘은그대로 |
| `candidate_qa_comparison.py` | 비교참조의candidate128허용은명시scope만. 작은보고서/receipt만읽는기존scope유지, 정확v2profile/행선언검증 |
| `backend/app/candidate_qa_comparison_api.py` | 기존pins body/응답은그대로. 새명시query `manifest_profile=bounded128m-3000-v1`만선택적으로허용. 미선택v2거부 |

173/182/175/199 및 실제collector는 이번격리patch에서 수정하지 않았다. Root가추가확인한225 `collection_budget_status`의`SOURCE_LIMIT=64MiB` stream과173 manifest pin64MiB·182 source64MiB도남아있다. **전처리profile만통과해도source가64MiB를넘으면예산카드·나지탐색·다음proposal은차단될수있다.** 이경로들의라벨개별64MiB/header개별64MiB는sourceJSON cap과별개이며그대로보존해야한다. 후속229격리보완에서sourceJSON입구만같은명시profile로연결할예정이며이번단위에는포함하지않는다.225main은편집하지않았다. 이단위는164 전처리와그candidate 소비경로의확장이며전체프로젝트의모든64MiB 소비자가확장됐다고표현하지않는다.227은기존공유판으로실행됐고이사본을소비하지않았다.

## 영수증 버전·과거호환·오류 계약

기본None은 package/stage/QA receipt v1을기존필드그대로출력한다. 같은Temp입력에서원판materialization과새기본모드의 `plan.json/candidate.json/receipt.json` 바이트전체동등을검증했다.

명시profile은세receipt를`schema_version:2`로만들고 `manifest_profile:{name,sha256}`를추가한다. sha는고정descriptor의canonicalSHA다. receipt 소비자는같은명시profile에서만v2를받고marker이름/SHA·버전·추가필드/typedfalse계약을검사한다. 계획/candidate의기존metadata 의미/false승인은그대로다.

- 새reader의기본None은기존64MiB/v1을계속받는다.
- 명시128scope는v2/동일profile만받으며v1과묵시적으로혼용하지않는다.
- 구reader는알수없는v2/새필드로실패폐쇄한다. 구reader가128입력을받도록속여v1로표기하지않는다.
- 비교API는query미선택일때v2를503 `RESOURCE_UNAVAILABLE`로거부한다. 잘못된profile명은400이다. 직접Python실패는고정`MANIFEST_PROFILE_*`, `MANIFEST_ROW_LIMIT`, `MANIFEST_NODE_LIMIT`, `MANIFEST_JSON_IO_LIMIT`와기존strictJSON오류다.

새profile을선택해도blocked QA가학습준비/과학검증/실행승인으로바뀌지않는다. comparison은계속저장보고서4개만읽고manifest/raster를다시읽지않는다. API schema는명시query선택지만추가하며응답값의기존false계약을유지한다. 공유API/UI에적용하지않았으므로실서버반영·브라우저확인은0이다. 향후반영승인후에는UI담당에게query/오류계약을인계해야한다.

## 자원검사의 정확한 의미

source/candidate를읽거나출력을measure할때scenes+history를합산한다. 기본모드의과거artifact 의미를바꾸지않기위해새3000행구조제한은명시profile에만적용한다. derivedcandidate는기존split계획이선택한scenes를유지하며history를새학습행으로삽입하지않는다.

깊이는decode전스캔과트리검사를유지하고노드는parse후순회에서제한한다. 따라서노드guard가JSONparse전모든메모리할당을예방한다고표현할수는없다. 개별128MiBbyteguard가먼저있고실제메모리비용은별도측정한다. 현재`_tree`는key/value/container닫힘등검사방문수를보수적으로세므로노드상한을정확한데이터셋픽셀/행수와혼동하지않는다.

누적I/O는명시작업의BoundedJSONIO read/verify/write,164 JSON SHA/copy/report쓰기, QA manifest/metadata/보고서경로를계측한다. raster read/hash는이**JSON** 예산에합치지않으며기존별도QA비용이다. 잔여량보다다음허용read상한이클때는보수적으로읽기전거부할수있다. 부분실패에도budget을자동환불/상향하지않는다. 이것은원격원장의예약/정산이아니다. summary는`manifest_resource_usage_before_summary_write`라는이름대로최종summary쓰기직전수치이며전체OS I/O의완전프로파일은아니다.

## 격리 시험과 한 번의 bounded 실측

새시험은명시/미지정/임의profile·정확v2마커·기본artifact바이트동등·구reader거부·package→stage→QA→comparison/APIreader·행3000/초과history합산·깊이/노드/JSONI/O초과를검사했다. node4M·I/O16GiB의실제최대부하를만들지않고시험내낮춘budget으로guard경로를검증했다. productionprofile값을실행중상향하는경로는없다.

실164CLI parser와전체metadata파이프라인도Temp자료로연결했다. sourceQA/candidateQA의native gate만Mock했고실파일raster/원본QA를호출하지않았다. 세receipt가v2+같은profile인것과모든승인false를검사한다. 두import이름이같은명시budget을공유하고scope종료뒤None으로돌아가는회귀도포함했다.

별도부하실측은 **단1개 child process**, wall75초/RSS850MiB상한의monitor로실행했고종료/실패시재시도하지않도록했다. Temp파일하나를재작성하며다음실바이트경계를확인했다.

| 합성JSON 크기 | 기본64 | 명시128 |
|---|---|---|
| 정확64MiB | 통과(3.940초) | 별도반복안함 |
| 64MiB+1 | 읽기전거부(0.001초) | 통과(9.310초) |
| 정확128MiB | 별도반복안함 | 통과(12.515초) |
| 128MiB+1 | 별도반복안함 | 읽기전거부(0.001초) |

candidate출력128MiB+1도쓰기전에거부됐다. 이case는단일문자열자체가cap을넘는경계이며복잡한3000행거대candidate전체직렬화성능측정은아니다. 합성fixture는작은`scenes`구조뒤whitespace padding이며현재실제rich source나최대노드형태가아니다.

child전체wall **31.148초**, CPU **24.391초**, peak working set **426,115,072바이트(약406MiB)**, exit0/stop없음이다. parent관측peak RSS426,110,976바이트·전체31.687초였다. [격리 benchmark 결과](../../evidence/integration/preprocess228-workspace-20261018/benchmark228-result.json)·[감시기록](../../evidence/integration/preprocess228-workspace-20261018/benchmark228-supervision.json)을보존했다. 이실측은마지막dualimport scope공유보호추가전의동일cap/parser경로이며마지막scope보호는회귀시험으로검증했다. 부하child를반복하지않았다. **현재227지연원인이나실제128운영성공을이실측으로판정하지않는다.**

최종동결판 **88PASS/74.061초·skip0**는[격리최종로그](../../evidence/integration/preprocess228-workspace-20261018/profile228-freeze-regression.log)에있다. 새profile9건과기존관련79건이며실원본QA회귀가아니다. 개발중원로그도보존했다: cwd/import불명확실행중단,active이름충돌,격리빈Temp폴더누락,시험fixture의서로겹친evidence루트/갱신누락ref크기,immutable descriptor의옛mock참조등이다. 이들은최종성공시험에합산하지않는다. 코드원판/사본구별·보호원본SHA와最終시험/patch핀은[격리freeze](../../evidence/integration/preprocess228-workspace-20261018/freeze228.json)에기록한다.

## 적용 전 남은 일

Root는227종료후격리patch manifest와원판/수정판diff를독립검토해야한다. 공유제품반영은아직승인/수행하지않았다. 이후고정code/source/profile·한번의실제bounded QA를별도로승인해야현재rich metadata의node/누적I/O/메모리충족을확인할수있다. 실패하면부분산출물을보존하고자동재시도·profile상향·수집반복을하지않는다. 실제3000행rich cohort의충분성,182/173/175/199/225등다른경로확장,API/UI선택연결,전체성능개선은별도후속이다.

완료격리코드·합성시험·실측한계는Root이해담당에인계한다. 설명/대본/FAQ에는“격리구현완료”와“공유운영미적용·실원본128QA미검증”을분리해기록한다. 이것은프로젝트완료나학습/배포승인이아니다.
