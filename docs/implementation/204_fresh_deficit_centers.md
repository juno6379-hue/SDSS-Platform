# 204 — 최신 고정 재고와 명시 부족셀의 새1024 공간후보4개

상태: **VERIFIED_REAL_LOCAL_GEOMETRY_ONLY / LOCAL_PROPOSAL_COMPLETE_UNAPPROVED**. Root가202의 고정 producer를 실제로컬자료에한번실행해새후보4개를생성했다. 후보발견은실제위성영상취득·품질적격증가·나지기여·전체pending/support검사·실행승인이아니다. 별도205의199제품검토결과와구분한다.

## 쉽게 설명

197에서남동·고론탈로의기본 g00~g03 작업은모두소진됐지만부족한지역·연도가남아있음을확인했다.182의옛제안은이전재고에서만든것이고남동2021·고론2022도없었다.202가새로지원한명시셀목록으로현재재고를고정해다른촬영장소를찾은것이204다.

새장소를찾을때아직사용하지않은옛후보도제외해야한다. 따라서기존lane-B24개와옛182의4개를합본28개로보존하고, 그자리와기존원본지원창을피해새4개를제안했다. 네장소에맑은영상이나나지가실제로있다는뜻은아니다.

## 실행·소유와 입력 고정

Root가실제로컬제안실행과새DATA 산출물을소유했다. 이문서담당은완료된preflight/result/runner/CLI와작은JSON메타데이터만읽었고추가운영스캔·HTTP·native검사·코드수정은0이다. 실제205소비전검토는Root의별도소유다.

`centers204-fresh-preflight-20261018.json`의시작시각은 **2026-10-18 13:42:22 KST**,완료result는 **13:42:55 KST**다. 실제product PID12140, **32.922초·종료0**으로 `LOCAL_PROPOSAL_COMPLETE_UNAPPROVED`를기록했다. Root가고정한producer SHA는 `c8ab85d7e3f39cda8a0c5a8259bf212a5bf9bc699e7f7b17652a90cfdacd6cf9`다.

원본은 **1,667행 /64,879,690바이트**이며 새 `data/centers204-fresh-20261018/source.json`에같은바이트로복사했다. 당시운영원본을다른SHA로자동재핀하거나기존원본·원장을다시쓰지않았다.

| 입력 | SHA256 |
|---|---|
| source와새source 사본 | `39bb0245e586342bd116f5b052428fcf857fb26eae0ee1413c9c5f5275c40ba9` |
| ledger 관측핀 | `024f5eabb2cadf88af4f34661fab6e6c209bf9aa8d105c2d1fbadf10f1c0dae3` |
| 공식6주경계 | `de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909` |
| 기존공식config | `8b0c1b2aad13a3344200998ec62a18853c5308adf4ec57b1af835333845fd7e3` |
| 새prior 합본 | `453ec964247ae87d61ddc035348a984b7f6c10a5ef699c6236fbebb10441867f` |

wrapper는각입력의stat/SHA를사전에고정하고반초간격으로metadata drift를감시했다. 변화하면소유한제안process만중단하고부분결과를보존하는계약이다. 실제결과는 drift목록이비었고 source/ledger/경계/config/prior **5개핀전후모두stable=true**다. 이는순차관측이며OS 원자snapshot 보증은아니다.

## prior28개를 보존한 방법

새 `prior-merged.json`의후보배열은다음두원배열을순서대로복사한것이며, 문서담당의JSON비교에서도 `기존24배열+옛4배열`과타입/값이같았다. 기존원파일을변경하거나이전미집행후보를현재실행승인으로바꾸지않았다.

| 원후보 | 수 | 보존된출처SHA |
|---|---:|---|
| 기존lane-B | 24 | `2920786dfcd5dfd5ec955eccc659192e9eb729cb45788b1a7fb052862f7f3b8d` |
| 옛182 proposal | 4 | `e9dcd4a9c6ae994c9cb48fb7acbce3b217494279edfc0076b540e3860b88c565` |

합본은 **31,509바이트 /28후보**이며위두ref를provenance로기록한다.28개는실제취득수나독립공간확보수가아니다. 새source만바뀌었다는이유로옛미집행장소를새후보로다시선정하지않는제외근거다.

## 명시한 순서와 실제4개

product CLI의반복인자는다음순서였다. 기존182의기본TARGETS를바꾸지않고202의명시선택옵션을썼다.

```text
--target southeast_sulawesi:2024
--target southeast_sulawesi:2021
--target gorontalo:2025
--target gorontalo:2022
```

각후보는고정 train split·동년ESRI·1024창·native주내면적1.0을기록한다. 좌표는아래표에서반올림했고정확bbox/CRS/좌표는proposal을따른다.

| 순서 | 후보ID 끝12자리 | 주 /연도 | snapshot 적격 /부족 | 중심 lon,lat | native CRS |
|---:|---|---|---|---|---|
| 1 | bd99d40b7b68 | 남동술라웨시2024 | 11 /17 | 121.86897122,-3.71947531 | EPSG:32751 |
| 2 | 6ad43e34c63c | 남동술라웨시2021 | 27 /1 | 121.77506670,-3.90748233 | EPSG:32751 |
| 3 | 359af9381159 | 고론탈로2025 | 18 /10 | 122.15162657,0.65857146 | EPSG:32651 |
| 4 | 032f179511c6 | 고론탈로2022 | 24 /4 | 122.24509880,0.56450286 | EPSG:32651 |

전체ID는 `centers182-<province>-<끝12자리>`다. 이명시4셀의부족합은32이며동자바2025의별도1부족은포함하지않는다. 동자바에는197에서확인한기존lane-B 미예약7후보가있으므로새204제안에임의추가하지않았다.

1024 원본창은명목상256패치16개로나눌수있지만그16개가모두적격인것은아니다. 새4후보를64적격패치로계상하거나남동2024의17부족이하나의원본창으로해결됐다고표시하지않는다.

## 실제로 확인한 것과 남은 검사

Root실행은고유 `source_window` GTiff **112파일**의원바이트SHA/native header·CRS/bounds와기본v2/합본prior센터를대조했다.112는독립위치112곳이나새취득영상112개가아니다. 기존center 또는source와겹친격자후보 **6개**를제외하고새4개를생성했다. 이미선정한새후보도다음후보의제외목록에추가하는기존정책을유지했다.

선정한도는전체4·주별2, header파일256개·파일당64MiB·최초payload합2GiB, 주별미터격자최대100,000점이다. source/경계/config/prior SHA·source header 지문은product의끝에서도확인한다. 이는GTiff header와기하제안이며픽셀배열/맑음/나지클래스재계수나모든지원파일검사가아니다.

특히 **현재pending config/B02·전체SCL/SWIR/support·source목록밖의과거report·live scene/split·실제선택B02·물리미등재패치·출력배타성·실제예약/정산**은204완료의범위가아니다. 결과의 `collector_consumption_approved`, `full_pending_support_inventory_verified`, `execution_supported`,각후보의class/quality flag는모두false다.205가199 helper로별도검토하고200계열실coordinator의fresh guards를연결해야한다.

실제운영collector시작·원장쓰기·원원본쓰기·HTTP·학습은모두0이다. 새source사본/합본/후보파일생성과기존자료수정을구분한다. 4GiB/2worker/전역2초/첫429/3000/고정split를우회하거나실행승인을추가한작업이아니다.

## 산출물·시험·문서 인계

새proposal은 `data/centers204-fresh-20261018/proposal.json`, **46,678바이트**, SHA256 **`0755f8cf2c7b210cb989b817b003e394e9ab7208400fa6b40551c26053d598f0`**다. 새source 사본과prior 합본은같은DATA 디렉터리에있다.

직접확인한Root증거는다음과같다.

- `evidence/integration/centers204-fresh-preflight-20261018.json`
- `evidence/integration/centers204-fresh-result-20261018.json`
- `evidence/integration/centers204-fresh-runner-20261018.py`
- `evidence/integration/centers204-fresh-cli-20261018.log`

CLI 로그는후보4개·정확명시셀·snapshot부족·proposalSHA와실행미승인을기록한다. 이문서담당은112header나동일제안process를재실행하지않았다.202의합성12PASS와199 관련55PASS는각기능의시험근거이며204의실제제안4개에시험건수로합산하지않는다.

새웹API나화면계약을바꾸지않는내부로컬제안이므로이번직접UI수정/build/브라우저시험은없다. 실제소비·확보·native QA·화면반영은Root/후속담당이별도로완료하고,205검토문서는그결과에맞춰분리한다. Root/understanding담당에게고정SHA·실제결과·미검증범위를전달해설명/대본/FAQ/INDEX/변경이력을갱신한다. 전체개발과10분보고는계속된다.

## 별도205 실제검토 후속

204결과의fullsupport미완료는제안생성당시범위다. 이후Root가[205](205_fresh_southeast_guard_review.md)에서남동2024/2021 두곳만199 helper로단1회검토했다.129.516초·1,254assets·pending보존·physical1,668+32capacity와입력불변이통과했지만 `COORDINATOR_NOT_CONNECTED`이며실B02/품질/수집/예약/정산0이다. 고론두후보의205통과로확대하지않으며204의새4개를취득성과로바꾸지않는다.
