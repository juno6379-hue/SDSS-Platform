# Gate Bare Class Requirements 20261017 — 저장 통계의 나지 부족 조건

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/ml/bare_class_requirements.py`; `scripts/inspect_bare_class_requirements.py`; `tests/test_bare_class_requirements.py`; `evidence/integration/bare-class-requirements-related-20261017.log`; `evidence/integration/bare-class-requirements-independent-arithmetic-20261017.json`; `docs/implementation/76_bare_class_requirements.md`; `evidence/integration/bare-class-requirements-independent-20261017.log`; `evidence/integration/bare-class-requirements-live-20261017.json`; `evidence/integration/bare-class-requirements-live-cli-20261017.log`; `evidence/integration/bare-class-requirements-live-validation-20261017.json`; `evidence/integration/bare-class-requirements-full-tests-20261017.log`; `evidence/integration/bare-class-requirements-live-integrity-20261017.json` |
| confidence | 코드·독립/전체로그·실제저장통계출력/보존근거; 현재래스터/정확라벨·미래충족미검증 |
| status | TESTED_SYNTHETIC: 관련/독립14·전체회귀; VERIFIED_REAL: 저장통계산술; 학습 BLOCKED |

## 쉬운 설명

나지 자료가 부족한 이유를 서로 다른 자로 나눠 잰다. 나지 픽셀 총량이 최소바닥을 넘는지, 나지가 충분히 들어간 패치가 여러 개 있는지, 전체 라벨 픽셀 중 비율이 충분한지, 전체 클래스 균형은 어떤지 따로 확인한다. 한 자에서47이 모자란다고47만 더하면 모든 검사를 통과한다는 뜻은 아니다.

## 이론적 배경

나지class7의 split픽셀바닥과기여patch대표성·bare비율·전체balance는별개의조건이다. 기여patch는패치안에최소나지픽셀이들어간경우만세므로작은나지조각이많아도기여patch는0일수있다. bare비율의분모는같은split의저장9클래스픽셀합이며적격patch수나전체영상면적이아니다. 미래자료가추가되면분모도변하므로현재부족분을고정해새장면/다운로드량을계산할수없다.

## 함수·입출력 범위

`build_bare_class_requirements`는메모리에있는blocked후보보고서와호출자선언참조를검사한다. pin_validation은 CALLER_DECLARED_REFERENCE_ONLY다. `inspect_bare_class_requirements`는고정후보QA보고서한개/외부1SHA를16MiB·깊이32/strictUTF8·중복키/비유한수/typed계수·최초/최종핀/대상/stat로검증해 PINNED_REPORT_BYTES_AND_STABILITY_VERIFIED로표시한다. 순수코어의선언pin과reader의실제bytes검증을구분한다.

지원정책은patch256/고정6주분할·bare필수class7·9클래스통계·minsplitpixels256..65536/minclasspatches5..3000/minperpatch256..65536·minratio≥.005/maxdominance≤.9의범위다. 정책파일이나threshold를바꾸지않고지원범위를벗어나면거부한다. 기존순수 `balance_diagnostics`를저장배열/정책으로재계산해저장reference_balance_by_split 전체와typed같아야한다. 이는래스터/라벨재검사나assess호출이아니다.

CLI는명시외부reportSHA와선택적새evidence출력만받는다. 출력64KiB·exclusive/nooverwrite·입력별칭/ADS장치·parent변경검사·부분새파일보존/CP949요약을사용한다. 원본source manifest참조는기록할뿐현재파일을열거나검증하지않는다. 새공개API/UI·QA·수집/Registry/학습은없다.

## 계산식·독립산술

- split픽셀부족 = max(0, 최소split나지픽셀−저장나지픽셀).
- 기여patch부족 = max(0, 최소기여patch−저장기여patch).
- bare비율 = 저장bare픽셀 ÷ 같은split의9클래스저장픽셀합.
- 비율부족 = max(0, 최소비율−현재비율). 이는추가해야할픽셀수계산이아니다.
- dominance = 가장많은클래스픽셀 ÷ 같은분모. 전체balance판정과bare조건을구분한다.

분모0이면이projection은비율/비율부족null·thresholdfalse를명시한다. 기존balance가사용하는zero ratio와의표현차이를설명하며없는자료를비율0의성공으로채우지않는다.

| 저장통계·조건 | train | val | test |
|---|---:|---:|---:|
| 적격patch |628|217|250|
| bare픽셀 |1418|209|1025|
| 최소split픽셀256 대비부족 |0|47|0|
| 기여patch |0|0|0|
| 최소기여patch5 대비부족 |5|5|5|
| 기여patch당최소bare픽셀 |256|256|256|
|9클래스픽셀합분모 |40149113|13989243|16252940|
| bare비율 |0.0035318%|0.0014940%|0.0063066%|

각비율은최소0.5%보다낮다. dominance최대0.9조건은모두충족해도bare비율/patch대표성은미충족이다.47픽셀은val의split바닥에대한산술부족일뿐이며그것만추가해도ratio·기여patch·전체gate가해결되는것은아니다. split별기여5부족을‘새15개patch를수집하면준비완료’로확정하지않는다. 실제새영상/라벨/장면목록이없고기간/품질/경계/정확라벨·독립성을검사하지않았다.

## 시험·현재성

관련14 PASS/5.019초이며작은합성통계로정책/type·전체storedbalance typed일치·분모0·47만추가해도ratio/patch미해결·bounded/stale·새출력/CP949·원본불변·추가QA/픽셀미호출을확인한다. Root별도독립산술은생산helper없이보존된보고서의통계만계산했다. 독립최종14 PASS/5.679초도확인했다. 최종 전체 scripts/test.ps1은 **775건 중774 PASS·1 SKIP/332.522초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련14 PASS/5.019초·독립14 PASS/5.679초와별도독립산술은전체775에중복합산하지않는다. 보호141참조·34기존코어SHA·고정후보QA보고서와카탈로그14기록canonicalSHA가불변이고이전snapshot추적code/data/tests/frontend변경은0이다. 신규코드/문서/evidence는있으므로전체workspace변경0이나원자snapshot보장이아니다. 이해에이전트는실행하지않는다.

출력은BLOCKED·requirements_are_full_gatefalse이며미래scene/download량추정false·adding_pixel_shortfall_alone_guarantees_readyfalse다. 픽셀/기하/독립성/정확라벨/원본인증·학습/수집/정산/자동재개승인은false·refund0/exactlyonceUNKNOWN이다. 기존후보4차단과원본5차단·예약136,314,880B·terminal2missing·모델/분할은유지한다.

## UI·발표 범위

공개API/UI연결없는내부CLI이므로이번화면변경/프론트재시험/브라우저확인은필요없다. 기존수동비교카드의4차단/나지부족은유지되며새데이터요구가화면에추가된것은아니다. 전체개발/10분보고는지속한다.

## 발표 1분

“나지 부족을 픽셀바닥·기여패치·비율·전체균형으로 나눠 읽는 도구를 만들었습니다. 검증분할은 최소256픽셀에서47개가 모자라지만, 그것만 채워도 해결되는 것은 아닙니다. 모든분할에서 나지기여패치는0으로 최소5개에 못미치고, 전체라벨픽셀 중 나지비율도 최소0.5%보다낮습니다. 이 숫자는 저장통계의 조건설명이며 새장면이나다운로드량을정해주지않습니다. 실제 새자료/라벨을검증하지않아 준비완료나학습승인으로말하지않겠습니다.”

## 발표 5분·10분

1. **0~1분:** 서로다른자네개로부족을재는비유를말한다.
2. **1~2분:** 픽셀바닥/기여patch/비율의분모/전체balance를구분한다.
3. **2~3분:**0/47/0과5/5/5·낮은비율/충족된dominance를함께설명한다.
4. **3~4분:** 저장배열재계산·독립산술·실제CLI/전체/보존근거와래스터미검사를구분한다.
5. **4~5분:**47만추가/새15patch확정금지·새자료없음·수집학습승인false를말한다.

10분확장에서는0분모null·순수pin과readerbytes검증·지원정책범위·storedbalance전체typed동일·미래분모변화/기간품질경계독립성미검사를설명한다.

## Q&A

**47픽셀만채우면되나?** val의split바닥부족만47이며ratio와기여patch조건은남는다.

**새patch15개를수집하면되나?** 기여patch부족을합친숫자를새patch/장면수로확정하지않는다. 실제내용/품질·분모변화와다른gate가남는다.

**나지비율분모는patch수인가?** 같은split의9클래스저장픽셀합이다.

**이번에새영상이나라벨을검사했나?** 보존된QA통계만읽고새QA/픽셀/기하/독립성은검사하지않았다.

**요구조건이전체학습gate인가?** requirements_are_full_gatefalse이며원본/후보차단과과학/운영승인을대체하지않는다.

## 이후갱신

독립/실제CLI·전체/보존최종근거를읽고INDEX·변경이력·해설/구조/용어·대본/FAQ/시연을함께갱신했다. 새수집·학습·UI연결은없다.

## 실제 저장통계 CLI 관측

Root CP949 CLI1회는종료0으로5,367bytes·SHA `8a0004aa2d67af8c97e32173f90c56c97449e54317ef86420489eb1bbaee7542`의새evidence를생성했다. 외부보고서pin을전후확인한reader결과이고독립산술JSON의모든split/분모/ratio/dominance/failures필드가타입과값까지같았다. 실제부족0/47/0·기여patch5각·비율세미달/dominance세충족을확인했다.

이는VERIFIED_REAL 저장보고서통계산술범위다. 새영상/라벨·현재source/candidate/raster·새QA/수집/학습은없고requirements_are_full_gatefalse·원본인증/승인false·원본5차단/후보4차단을유지한다. 새데이터요구계획과실제충족자료/정확라벨검증은분리한다.

## 다음77의 executor 경계 대조 — PLANNED

다음대기열은제출때고정한ordered input binding과실행기에전달할binding을id/version/SHA/role/index및Job/Agent/Trace관점에서대조하는순수guard검토다. 기존register_version/resolve·snapshot·현재lineage를복제하지않는executor경계이며아직코드/DB파일/실행변경은없다. 일치하더라도실행승인이아니고현재resolver와실제bytes확인은별도후속이다. 정확schema필드와기존snapshot원문연결은77개시때결정하며지금완료된계약으로확정하지않는다. 나지충족자료/정확라벨·학습차단해결은계속미완료다.
