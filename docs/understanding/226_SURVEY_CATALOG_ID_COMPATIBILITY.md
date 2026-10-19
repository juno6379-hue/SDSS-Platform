# 226 — 원catalog ID를 보존하는 두 장면 형식의 선언 호환

- updated_at: 2026-10-18 15:15 KST 동결 근거 기준
- source_commit: `bare_label_survey_contract.py` SHA `e035cc1afb77b9461f1e5df1256dcf58bf82199e4dbb5fdba4af6e1518f8dd60`
- evidence_paths: `docs/implementation/226_survey_catalog_scene_id_compatibility.md`,제품/test, `evidence/integration/survey226-freeze-20261018.json`,final로그/preedit archive기록
- confidence: 두전체ID형식과합성회귀는확인.실STAC/SCL URL출처결속·시간변환·실행연결은미검증.
- status: `TESTED_SYNTHETIC` 선언ID호환/74 PASS / `PLANNED` 실증거·runner·registry·소비연결;출처·집행권한false

## 1. 쉬운 설명

**226은 catalog가 실제로 쓰는 baseline 없는 ID를,그 문자열 그대로 순수 계약에 넣을 수 있게 했다.**224는baseline이들어있는compact형식만허용해219에저장된catalog ID를그대로넣으면거부했다.이번은그형식을명시적으로추가했다.

누락된번호를상상해채우지않는다.주소에아파트동번호가없다고옆영수증에서추정해서써넣는대신,허용하는두주소양식을각각정확히검사하고원문을보존하는방식이다.이는신청서형식호환이며실제두주소가같은물건을가리킨다는검증은아니다.

## 2. 이론과실제형식

| profile | 예시의중간부분 | 의미 |
|---|---|---|
| CATALOG_L2A_NO_BASELINE | acquisition_R060_T51MUR_production | 원catalog형식 |
| COMPACT_L2A_WITH_BASELINE | acquisition_N0510_R060_T51MUR_production | baseline포함compact형식 |

예시의R060/N0510은그값만허용한다는뜻이아니다.센서A/B/C·baseline있으면N+ASCII4자리·orbit001~143·zone01~60·tile문자·실달력/제작순서등224조건은같다.정규식에서 **baseline블록전체만선택적**으로하고fullmatch를유지했다.반쪽/중복baseline·잘못된위치·두orbit·prefix/후미·`.SAFE`는거부한다.

`.SAFE`가있는asset URL은scene ID와다른역할이다.문자열두형식을허용했다고SCL실URL과catalog ID의물리적출처가같다는검증을수행한것은아니다.

## 3. 코드·입력과불변경계

```mermaid
flowchart LR
  A[원catalog/compact ID] --> B[두전체형식중하나 fullmatch]
  B --> C[달력·orbit/tile·동년·UTC exact]
  C --> D[입력ID/source_group그대로보존]
  D --> E[typed선언객체·출처/실행false]
  E --> F[실STAC/URL결속·runner는후속]
```

공개API/typed결과는같다.`_scene()`의`(?:_N[0-9]{4})?`만선택블록으로넓혔다.다른검증기·core/UI·collector·원장·173/175소비자는변경하지않았다.

원catalog ID `S2A_MSIL2A_20240619T021351_R060_T51MUR_20240619T061603`는그대로보존되고N0510을삽입하지않는다.기존compact ID에서는baseline을삭제하지않는다.source_group은입력원ID와정확히`province/id`여야한다.두형식을같은scene alias로정규화하지않아각requestdigest는다르다.실중복/alias판정은후속registry/liveguard책임이다.

관측/제작달력·제작≥관측·관측연도=seed·기간내·선언datetime=ID관측시각exact를유지한다.예시의선언시각은02:13:51Z이지만raw STAC값을읽어검산하거나그정밀도를변환한것은아니다.224의fractional-zero허용/nonzero거부도그대로다.초이하를반올림/삭제해현재자료를맞췄다고설명하지않는다.

계상선언65MiB/4GiB·미정산전액·split/SCL역할·F2분리복사/고정오류·11개false도같다.실파일SHA·header·품질·원장settled·출처진실·집행권한은검증하지않는다.

## 4. 실제증거의범위와시험

Root가219저장report에서확인해전달한ID문자열을합성fixture에사용했다.226담당이report/STAC/SCL/실URL을새로읽은시험은아니다.원catalog문자열과_N0510_SAFE URL이동일장면인지독립검증한것도아니다.이해담당은완료코드·시험·문서·freeze만읽었다.

최종 **74 PASS/18.601초·0 SKIP**는순수계약32+기존173/175/198관련42다.220의60/224의70과겹치는회귀이므로합산하지않는다.

추가시험은제공ID그대로request/receipt통과·baseline미삽입·원source_group·두profile×정상A/B·서로다른digest를확인했다.불완전/잘못된달력·센서/orbit/tile·suffix·중복baseline·source_group/시각변조는거부했다.실제원격취득이나소비연결시험이아니다.

수정전224제품/test/doc3개는각freezeSHA와같은 **실제편집직전원바이트사본**으로새archive했다.역재구성이아니다.원224freeze/로그/문서는보존했고새source/test/doc핀은226freeze에기록했다.

## 5. 현재한계와후속

운영source/ledger추가읽기·HTTP·collector·native0이다.typed통과만으로actual STAC/SCL URL/제품identity가같음을보장하지않는다.고정stac_ref·실파일/SHA·sourceURL/scene결속,rawSTAC시각정밀도·변환계약은후속검증이필요하다.실행runner/registry/target consumer는PLANNED다.

225의실API/브라우저와223의수집/native는별도운영근거다.그미래성과를이순수계약수정의검증으로섞지않는다.새UI/API서버변경은없고실브라우저도추가하지않았다.다른core/UI/CONT·운영원본원장쓰기는0이다.

## 6. 발표대본

### 1분

“226은219에 저장된 catalog장면 ID를 고치지 않고 계약에 넣도록 호환을 보완했습니다.baseline 없는 catalog형식과 있는 compact형식 두 개만 전체검사하며,누락번호를추정하거나원ID를정규화하지않습니다.날짜·시각·분할과고정오류검사도그대로입니다.최종74시험을통과했지만fixture는Root가전달한문자열이며실제STAC와SCL URL이같은장면이라는검증은아닙니다.raw시각변환이나수집기·소비연결도아직없습니다.형식호환과실자료출처·품질승인을구분합니다.”

### 5분

1.224의실catalog형식공백을설명한다(1분).
2.두전체형식과부분/후미변형거부를설명한다(1분).
3.ID/source_group보존·baseline추정0·다른digest를설명한다(1분).
4.74합성회귀/문자열fixture·preeditarchive를설명한다(1분).
5.실URL/시간변환/runner미연결과225/223별도증거를설명한다(1분).

10분발표는날짜/시각정밀도2분,실scene alias후속책임1분,Q&A2분을더한다.시연은보존code/test읽기로하고실STAC조회·재현시험·운영수집을추가하지않는다.

## 7. FAQ

- **N0510을자동추정하나요?** 아니다.입력ID를그대로두고두문법만허용한다.
- **두ID형식은같은장면으로합치나요?** 정규화/alias판정하지않고각digest가다르다.
- **.SAFE도ID에넣나요?** asset URL역할이며이번scene ID문법은거부한다.
- **rawSTACdatetime도처리하나요?** 실제값읽기/변환연결이없다.exact선언계약만검사한다.
- **74시험이실자료호환전체를뜻하나요?** 합성문자열/선언회귀다.실URL·scene진실·품질은별도다.
- **220/224시험을더하나요?** 겹치는판본별회귀여서최종226은74건이다.
- **SURVEY수집/소비까지완료인가요?** runner/registry/173·175소비는계속PLANNED다.

관련: [226 구현/시험](../implementation/226_survey_catalog_scene_id_compatibility.md),[224 F1/F2보완과호환공백이력](224_SURVEY_SCENE_AND_COPY_HARDENING.md),[220 순수계약](220_PURE_SURVEY_DECLARATION_CONTRACT.md).
