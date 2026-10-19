# 309 — 지역·연도 최소량 충족 후 새 고정 후보 QA 준비



상태: **VERIFIED_REAL / 단1 실제 QA·인계 검산 완료 / 후보1391·학습준비false**. 아래 준비 계약은 당시 기록이다. 원문은 `priority309-preparation-doc-before-start-20261018.md`에 원SHA로 보존하고 실제 시작을 마지막 절에 추가했다. 304 단1 native 성공 뒤 준비만 진행했다. 실제 후보QA·학습·registry·HTTP·게시/API/UI0이며 운영 제품/원본/원장/모델/split 쓰기0이다. 공유 적용이나 미래 성공을 의미하지 않는다. Root가 sourcehold/추가 collector 금지를 유지한다.



## 실제 준비 입력과 보호



| 역할 | bytes | 직접 metadata SHA256 |

|---|---:|---|

| post304 source |69564847|`0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658`|

| ledger provenance |68395|`d5ee31ff7970adaaa6b166805c240616efa8e9af713bb8394c7a166346f21c91`|

| 고정 policy |1306|`01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7`|

| 단1 native304 |34588|`7e933d923f6a7507a878f66bd7fea391b7b181779746f175567f0febdf8c884c`|



파일별 cap-before-read/streaming hash/전후identity/정확 bytes를 확인했다. source 전체 JSON parse나 래스터 읽기는 준비에서 하지 않았다. source는 default64MiB보다2455983B 크다. 크기로 자동 상향하지 않고 Root가 정확128을 명시 승인해야 한다. 현재source 등록1779/적격1407/cellgap0은 완료native 근거다. split865/292/250은 이전834/292/250에 신규train15+16을 더한 기록상 산술이며 새 전체source QA의 결과가 아니다. history 수/새후보 수/제외량/최종gate는 아직 null·미확정이다.



기존1360 pointer와 `candidate-receipt293-20261018.json`은 각각1211B/동일SHA `996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0`를 직접 확인했다. runner가 시작 전 exact protected_expected 및 종료 뒤 보존을 확인한다. 이전290 원판/prep/완료증거는 보존했고 새 준비 archive2개에 runner/prep 원바이트를 고정했다. receipt275나 과거1348을 현재 보호 대상으로 잘못 사용하지 않는다.



실제 OS 조회에서 해당 QA/collector/native Python0과 execution lock 부재를 확인했다. Root GO 직전 다시 확인해야 하며 준비 관측이 미래 동시성 보장은 아니다. 새 run-id `guarded309-20261018`의 work/evidence/log/launch/terminal 모두 미존재를 확인했다.



## 새 runner 계약과 최소 diff



runner `priority309-runner-20261018.py` SHA `922e70584c51ac0c9cd247bc22d49be4bdf9936c8fcdb3b800be5b5874ea4e83`, prep `priority309-preparation-20261018.json` SHA `698bb2a02155de2027d138d65820e836767f6475003f57301cc0f1a5de73fd33`다. 기존290과 차이는309 식별자/새준비 지문뿐이며 실제 코드16개 SHA/bytes는 현재도290과 exact 일치한다. `.diff`와 archive를 보존했고 AST compile만 수행했다. runner import/CLI 실행/실QA0이다.



한 ContextVar scope에서 정확 `bounded128m-3000-v1` descriptor SHA `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`를 확인한다. source/candidate128MiB/scene+history3000/depth32/node4000000/누적JSON IO17179869184B를 유지한다. 역할별 policy1MiB/receipt64KiB/readiness16MiB/saved_plan4MiB 등 개별cap은 그대로다.128MiB가 최대 RAM/RSS/시간 보장은 아니고 depth/node검사는 decode 후다.



준비JSON2회 bootstrap의 실제읽기·GO·native proof·보호pointer 전후와 source snapshot→source QA→split plan/validation→package/stage→후보QA→실파일SHA→summary·log/launch/terminal까지 동일 budget을 사용한다. 중첩 @profile_entry는 기존 scope를 재사용하며 기존164 CLI main 호출 지점은 정확1곳이다. source/policy는 기존164가 출력 전/각QA 뒤/최종 직접 검산한다. ledger 준비핀은 별도 provenance이며 QA입력으로 추가하지 않는다. 준비단계hash를 실제QA 계측값으로 소급하지 않는다.



Root GO schema는 runner의 exact set과 일치해야 한다. 미래 GO는 아직 생성하지 않았다.



```json

{

 "kind":"PINNED_CANDIDATE_QA_309_GO","approved":true,"run_id":"guarded309-20261018",

 "preparation_sha256":"698bb2a02155de2027d138d65820e836767f6475003f57301cc0f1a5de73fd33",

 "native_audit_sha256":"7e933d923f6a7507a878f66bd7fea391b7b181779746f175567f0febdf8c884c",

 "source_sha256":"0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658","source_bytes":69564847,

 "manifest_profile":{"name":"bounded128m-3000-v1","sha256":"db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4"},

 "no_active_collector":true,"execution_lock_absent":true

}

```



Root 전체runner/최소diff/최종freeze/OS·원본·정책·새경로 검토 뒤 별도 GO를 받아야 아래 명령을 **한 번** 실행한다.



```powershell

python -X utf8 -u evidence/integration/priority309-runner-20261018.py --approval E:/GeoAI–MLOps–SDSS/evidence/integration/priority309-go-root-20261018.json

```



현재는 실행 승인0/launch·source사본·후보·summary0이다. 실패·cap초과 시 부분 보존/exit2, 자동 retry·상한 확대·품질우회0이다. budget소진/쓰기 실패는terminal도 없거나 부분일 수 있어 예산밖 fallback 완료영수증을 쓰지 않는다. 느린 metadata 단계를 이유로 재시작하지 않는다.



## 완료 후 검산 및 해석 경계



성공해도 summary/terminal·11실출력핀·세schema2정확128marker·실파일SHA·정확retained rows/lineage/완전partition·같은scene누출 후보에서만제외를 확인해야 한다. 이전290의1360/16제외/5426파일/3차단은 과거이며 이번 개수로 고정하지 않는다. 원본·운영split을 수정하지 않는다. actualwall/sourceQA/candidateQA 함수시간을 구별하고 RSS를 측정하지 못하면false를 유지한다. OS WorkingSet표본을 Linux RSS/최대peak보장으로 표현하지 않는다.



304 native에서 최소수량floor는0부족이 됐지만 신규나지는raw→quality→final→eligible 모두0이다. 나지 각split0.5%·기여5 미달3차단, 독립정답/정확도/다른모델 요구는 별개다. 새gate는 실제결과로 확정해야 하며 수량충족을학습승인으로확대하지않는다. connectivity의 NOT_CAPTURED_BUDGET도 관측대로남긴다. scientific_accuracy_validated/training/registry false를 유지한다.



완료 후 protected pointer/receipt293·원본/정책/원장보존을 metadata 인계검산하고 Root에 종료신호를 보내야 한다. Root가 그 뒤 old1360원바이트archive→새게시→profile명시재결속→실API→브라우저→문서·이해자료/대본FAQINDEX이력 순서로 별도 근거를 마감한다. 이 준비는 제품/UI 변경이 없어 화면 코드를 수정하지 않았고 실API/브라우저를 수행하지 않았다. 전체개발은미완료다.



## 실제 시작 — 2026-10-18 22:36 KST

Root가 전체runner/최소diff/현재16코드핀·source/policy/native/ledger/pointer·새경로·실OS중복0/lock부재와311독립최종검토를 확인한 뒤 별도GO `priority309-go-root-20261018.json` SHA `45f1ed362a9ff932646deaaafe418c0bbbe800bec54c33d9e95c0ded7bd390d4`를 발급했다. 이 담당이 GO·동결runner SHA를 직접대조하고 승인 명령을 한 번 실행했다. exec session96526/실PID24432, launch22:36:14.301 KST/QA309_STARTED를 확인했다.

22:36:45.719399 KST SNAPSHOT_PINNED 로그에서1779행/source0c149 지문을 실제 확인했다. 아직 sourceQA/candidateQA/summary/terminal은 미완료이며 후보 수·제외량·최종 gate는 미확정이다. Root sourcehold/추가collector0·현재1360pointer보존·모델학습0을 유지한다. 재시작·상한상향·동일QA추가0이다.

초기 Windows WorkingSet311328768B/PeakWorkingSet311336960B 및 snapshot뒤592384000B 표본을 관측했다. 이는OS 표본이며 LinuxRSS/최종peak보장이 아니다. wrapper의RSS미관측 계약을 유지한다. 기존log/receipt메타 단계변화만 관측하고 strict metadata 단계를 우회하지 않는다.


## 실제 최종 완료와 Root 승계 인계 — 2026-10-18 23:04 KST

PID24432/session96526이exit0으로종료했다. terminal23:03:02.849132 KST/전체wall1608.765초, sourceQA314.125초/candidateQA함수343.078초를구분한다. 후보QA함수에는입력증거검산도포함되므로순수래스터처리시간이아니다. strictmetadata구간동안프로세스/로그/receipt메타만관측했고원인프로파일링없이특정병목을단정하지않았다. 재시작·상한상향·추가동일QA0이다.

| 구분 | 등록행 | history | train적격 | val적격 | test적격 | 합계 |
|---|---:|---:|---:|---:|---:|---:|
| 고정source |1779|0|865|292|250|1407|
| 최종고정후보 |1763|0|865|276|250|1391|

현재게시1360대비후보는31개늘었으며train834→865다. 이는297의15개와304의16개적격증가를반영한다. 원본등록행과적격합계는서로다른수치다. 같은원본scene `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`이banten/west_java의고정split을넘는문제는test를유지하고val의source index288–303 총16개를후보에서만제외했다.원본/운영split/모델은변경하지않았다. 후보의잔여sourceidentityconflict0이며원본4차단에서후보3차단으로줄었다.

기존164CLI가실제파일5526기록의SHA를재검산하여불일치0이었다. 이어별도metadata후검산session46853을단한번실행하여11출력실지문불일치0·세schema2정확128marker·typedpartition/exactretainedrows+lineage/historyexact를확인했다. 후보/history는고정source의원문retained/history와정확히같았다. 기존래스터감사/QA를재실행한것이아니다.

후검산checker는290을재사용하되이번candidate/plan/QA및3receipt후속read에summary outputexpectedpin을명시했다. Root가발견한receiptreadpin누락은실행전원바이트archive `priority309-handoff-before-receipt-pin-20261018.py`에보존후한줄수정했다. 최종checkerSHA `1b535829d022884b19bd1cbd50d3016f04e43adff10a98390ba0be57b535c66e`로만실행했고실QA제품/runner는수정하지않았다.

최종summary SHA `1359667f4ef2316b8bfffc52a939cd626ca6b87be10139ec192c0abe5b47ec3b`,terminal SHA `f5fa44070eeb071c7c5cb1105908dd6d6110e335ccda9cab58b47a97957b8a30`,handoff SHA `8c02c1831358e684c6788a8820e79173464a0f47d3d860199ec5b1a97f8831f1`/6685B다.

### 크기·계측·보존 경계

source69564847B/후보68943578B 모두default64MiB를넘었다. 크기기반자동선택이아니라처음부터Root가승인한동일exact128profile을source→계획/package/stage→후보QA/3receipt/후검산까지유지했다.128MiB/3000행/depth32/node4M/역할별개별cap·누적16GiB를완화하지않았다.

terminal쓰기직전read4445908695B/write210381886B/합4656290581B였다. terminal쓰기와후검산/proof까지포함한누적JSONIO는5076287859B<17179869184B다. 후검산은기존QA사용량을debit하고동일잔여16GiB범위안에서만읽고썼다. 이최종문서/완료freeze작성은QA계측완료뒤행정적인계이며이합계에포함한다고주장하지않는다.

후검산시각23:04:01.049395 KST에current source0c149/정책01991/원장d5ee와기존1360pointer·receipt293의996a지문이일치·보존됨을확인했다. Root에후검산종료/승계대기해제신호를전달했고그뒤운영source/ledger/pointer를다시읽지않았다. 이후Root312게시/313profile의의도된변경은별도단위로구분한다.

OS관측PeakWorkingSet최댓값표본1332064256B는Windows표본이며최종peak보장이나LinuxRSS가아니다. wrapper rss_observed=false를유지한다. 전체wall을입출력상한이나SLA보장으로확대하지않는다.

### 학습준비가여전히false인이유

| split | valid label pixels | 나지pixels | 나지비율(%) | 기여patch |
|---|---:|---:|---:|---:|
|train|55132456|2562|0.004646990513174309|1|
|val|17776457|2998|0.01686500296431398|2|
|test|16252940|1025|0.006306551307025068|0|

나지pixels/기여patch는290때와같다. train적격은늘었지만나지가늘지않아분모증가로train비율은0.0048232215%→0.0046469905%로낮아졌다. 각split0.5%/기여5기준미달로REFERENCE_CLASS_IMBALANCE3건이남았다. test나지1025pixels와기여patch0은기여인정256pixel조건을통과한patch가없다는뜻이다. 최소지역·연도수량충족과나지대표성은별개다.

ready_for_training/observed_gate_ready_for_training/scientific_accuracy_validated/training_executed는false,registry/HTTP0이다. connectivity는NOT_CAPTURED_BUDGET로전체공간연결성검증을완료했다고주장하지않는다. 약한라벨검사는독립정답·실영상품질·과학적정확도/다른모델준비를대신하지않는다.

### 다음소유와문서인계

완료freeze에11개인계당시실출력핀과runner/prep/GO/log/launch/terminal/summary/checker/proof/이문서지문을고정한다.기존290원판/309준비freeze/준비문서archive를보존했다. 이단위는게시·profile·실API·브라우저를실행하지않았다. Root312승계→313명시source재결속/실API→web_ui실브라우저는별도증거가필요하다.312/313동결정적검토314는필수코드수정발견없음범위이며실행성공과다르다.

Root에최종결과와문서/완료freeze를전달하여이해담당의쉬운설명·대본FAQINDEX이력갱신을요청했다. 그후속을이담당이완료했다고표현하지않는다. 지역·연도floor0만으로전체개발/학습/운영승인을완료하지않는다.
