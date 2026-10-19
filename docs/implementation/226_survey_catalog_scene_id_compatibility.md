# 226 — SURVEY 카탈로그 장면 ID 호환 보완

상태: **IMPLEMENTED / TESTED_SYNTHETIC**, 실운영 소비/실제 출처검증은 **PLANNED**다. source/test와이문서만수정했다. 225UI/223core/collector/원장/173·175소비자연결은변경하지않았고운영추가읽기·HTTP·native·수집은0이다.

## 보완 이유와 실제 증거의 범위

Root는219저장report에서아래selected scene ID를확인해문자열로전달했다.

```text
S2A_MSIL2A_20240619T021351_R060_T51MUR_20240619T061603
```

Root는대응SCL sourceURL에는baseline `_N0510_`와`.SAFE`가있다고보고했다. 이번담당은report/STAC/SCL/URL을추가로읽지않았고이문자열만합성fixture로사용했다. 두표현이실제로같은영상이라는진실검증을수행한것도아니다.

[224](224_survey_contract_scene_and_copy_hardening.md)는명시한baseline필수문법에는맞았지만프로젝트카탈로그의baseline없는ID를직접소비할수없었다. 이번보완은누락baseline을추정하거나원ID를고치는대신두전체형식을명시적으로허용한다.

## accepted profiles와 API

`validate_survey_request(dict)` / `validate_survey_receipt(receipt_dict,request_dict)` API와typed결과/오류계약은그대로다. `_scene()`은다음두profile의**전체ID**만허용한다.

| profile | 전체형식 |
|---|---|
| `CATALOG_L2A_NO_BASELINE` | `S2A_MSIL2A_<acquisition>_R060_T51MUR_<production>` |
| `COMPACT_L2A_WITH_BASELINE` | `S2A_MSIL2A_<acquisition>_N0510_R060_T51MUR_<production>` |

표의sensor/orbit/tile/baseline숫자는형식예시다. 실제허용범위는224와동일하게sensorS2A/B/C·MSIL2A·ASCII timestamp·baseline있으면정확N+4자리·orbit001..143·UTMzone01..60·허용MGRS문자다. 정규식에서baseline블록전체`(?:_N[0-9]{4})?`만선택적으로하고fullmatch·나머지검사는유지했다. baseline중복/반쪽/다른위치·두orbit·후미/prefix·`.SAFE`는허용하지않는다. `.SAFE`가포함된asset URL은sceneID입력과다른역할이다.

ID는입력그대로보존한다. baseline없는ID에`N0510`을보충하지않고, baseline있는ID에서baseline을제거하지도않는다. `source_group`은**입력원ID**와정확히`province/id`여야한다. 두profile을같은장면alias로정규화하지않으므로canonical requestdigest도서로다르다. 실제scene중복/alias판정은후속registry/liveguard의출처검증책임이다.

관측/제작실달력·제작≥관측·관측연도=seed연도·기간안관측시각·선언datetime=IDacquisition exact결속을모두유지한다. 이번문법허용이날짜오류나시각불일치를완화하지않는다. 예시ID의선택scene **선언시각**은`2024-06-19T02:13:51Z`다. 원rawSTAC의datetime이같은값인지/초이하정밀도가어떤지검증하거나변환하는연결은없다. rawSTAC값을반올림/삭제해맞췄다고표현하지않는다. 224의분수zero동일값허용·nonzero exact거부정책도그대로다.

Esri v003동년supercell계획은원카탈로그ID의MGRS부분으로생성한다. SHA형식/선언source/scene/ref결속통과는실제SCL URL·STAC·영상이동일장면임을증명하지않는다. 나중에실제고정stac_ref/SCL sourceURL·product identity와sceneID두표현을결속하는명시검증이필요하다. baseline이나product경로를상상해채우는예외를추가하지않았다.

실행·품질·학습·source/header/ledger진실·registry/target소비자연결flags는전부false다. 64MiBCOG+1MiBmetadata/4GiB전역선언·미정산전액보존·split/SCL역할·F2분리복사/고정오류가드는변경하지않았다. source_group을legacy완료행으로위장하는경로도없다.

## 원판보존·시험·인계

수정전224제품/시험/문서3개의원바이트를224freezeSHA와대조한뒤새archive로저장했다. [목록/검산기록](../../evidence/integration/survey226-before224-archives-20261018.json)의각항목은`EXACT_PRE_EDIT_BYTES_MATCH_224_FREEZE`다. 제품SHA`ea60acf759c7437e70646f3ac5ce4ec6c929af2c5b9c920a5ecfe7a744bfe3a0`, 시험`57a27c762d5bc9db83739119037f2ba49df93d787c945672627f8f9cfb564289`, 문서`f1888e3f02a0d68e37b76e0a4cb15ca252963f4eec6c4cd172ce47b5cea486e4`와일치한다. 기존224freeze/로그/문서는덮어쓰지않았다.

추가합성시험은제공된219ID그대로request/receipt통과·baseline미삽입·정확source_group보존·두profile×정상2A/2B·서로다른digest·불완전/partial/날짜/센서/orbit/tile/후미/중복baseline·source_group과시각변조를검사한다. 기존224 F1/F2와budget·승인false회귀도유지한다. 실제219report를다시읽거나원래수집을재현한시험은아니다.

최종판 **74PASS/18.601초·skip0**(순수계약32+기존173/175/198관련42)은[시험로그](../../evidence/integration/survey226-final-20261018.log)에있다. 제품/시험/문서/archive핀은[226freeze](../../evidence/integration/survey226-freeze-20261018.json)에기록한다. 이번은내부Python계약의입력호환보완이므로UI/API서버/브라우저변경이필요없다. Root독립검토후이해담당에두profile과실제URL/scene바인딩미검증·실행PLANNED를구분해인계한다.
