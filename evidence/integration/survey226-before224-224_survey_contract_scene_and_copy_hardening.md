# 224 — SURVEY 장면 결속과 안전한 입력 복사 보완

상태: **IMPLEMENTED / TESTED_SYNTHETIC**, 실제 실행 연결은 **PLANNED**다. [221 독립 정적 리뷰](221_survey_contract_independent_review.md)의F1/F2를 같은220제품·시험파일에서 보완했다. 운영 원본/원장 읽기·HTTP·collector·raster/native·실행은0이다. Root223core는수정하지않았다. 기존220문서/freeze/로그와221리뷰는그시점기록으로보존했고이번문서가수정판의계약차이를설명한다.

## 수정 전 판본의 보존

수정 전에220제품·시험·문서 bytes를각각220freeze SHA와대조하고원바이트로새archive에썼다. 역재구성이나역사파일발견이아니라이번수정직전에검산한정확사본이다.

| 원판 | 보존SHA | archive |
|---|---|---|
| bare_label_survey_contract.py | `a0470b489db19a9c4ccafcada3374e87675e116af3a592068b7dfcda64cf9096` | `evidence/integration/survey224-before220-bare_label_survey_contract.py` |
| test_bare_label_survey_contract.py | `a1b2b913c7e225d9225833923d697af7c9866db142933e8d1b1b3104f953251e` | `evidence/integration/survey224-before220-test_bare_label_survey_contract.py` |
| 220구현문서 | `b7e3a2fc9096fa09758cb441e5d853b2a2d78c2e45d997b8f9f6ea962b739a65` | `evidence/integration/survey224-before220-220_bare_label_survey_pure_contract.md` |

목록/검산방법은[archive기록](../../evidence/integration/survey224-before220-archives-20261018.json)에있다.220freeze를수정판SHA로덮어쓰지않는다.

## F1 — 완전한 L2A ID와 관측시각 선언 결속

기존시작부분정규식과MGRS부분검색만으로는불가능한달력·잘못된ID후미·동년다른관측시각을막지못했다. 이제`_scene()`이compact Sentinel-2 L2A ID **전체를fullmatch**한다. 허용형식은다음으로좁게정의한다.

```text
S2[A|B|C]_MSIL2A_<YYYYMMDDThhmmss>_N<4 ASCII digits>_R<3 ASCII digits>_T<UTM zone><latitude band><square letters>_<YYYYMMDDThhmmss>
```

실제정규식은센서A/B/C, orbit001..143, zone01..60, latitude band C..X중I/O제외, square첫글자A..Z중I/O제외·둘째A..V중I/O제외를검사한다. `_suffix`, `.SAFE`, prefix·불완전ID·MSIL1C·다른센서·Unicode숫자는거부한다. 이는정의한compact ID문법의검증이며실제catalog의모든ID변형을지원한다는주장은아니다. zone별실제tile존재/위치·sensor운용시점·scene진실은확인하지않는다.

관측과제작timestamp모두`datetime.strptime`로실달력을파싱한다. 관측연도는seed연도와같아야하고제작시각은관측보다앞설수없다. 제작연도는관측연도다음해여도유효한달력/순서를충족하면허용한다. baseline은정확4자리선언검사이며실제processing baseline이나calibration검증은아니다.

`selected_scene.datetime`은관측ID의acquisition시각과**datetime값이정확히같아야한다**. 같은해의다른날·1초차이·다른연도·ID관측일만기간밖인모순을거부한다. source_group=`province/id`와Esri v003동년MGRS출처결속도유지했다. 기간비교는문자열순서대신파싱한datetime으로실행한다.

UTC입력문법은`YYYY-MM-DDTHH:MM:SS[.1..6 digits]Z`다. `.0Z/.000Z/.000000Z`는초정밀도ID와같은값이므로허용한다. 1마이크로초라도nonzero면ID와정확히같지않아`SURVEY_SCENE_TIME_MISMATCH`다. 오프셋표현·7자리이상분수는`SURVEY_TIME_INVALID`다. **반올림/초잘라내기/허용오차를발명하지않는다.** 실제STAC의nonzero초이하관측표현을연결하려면실제의미와정밀도/ID결속을별도버전으로설계해야한다. 현재순수계약만으로실자료전체호환을보장하지않는다.

220합성fixture의R000은엄격문법에서유효하지않아R001로고쳤다. 기존다른collector시험의R000fixture나타모듈장면검사는편집하지않았다. 정상S2A/S2B및허용S2C·orbit경계·윤년과실패경계를검사했다.

## F2 — 검사하면서 분리 복사한 primitive만 직렬화

`_copy()`는원dict/list를훑고같은원객체를다시직렬화하던방식을바꿨다. 이제제한을검사하면서새dict/list를만들고,분리된사본만canonical JSON으로직렬화한다. 문자열과숫자는immutable primitive만허용한다. 임의사용자객체/서브클래스의메서드를호출해복사하지않는다.

기존최대10000방문노드·깊이24·container128·값문자열4096·key128·canonical UTF8 64KiB제한은유지한다. list가복사중커져도각추가요소의container/노드검사를적용한다. 순환입력은depth제한으로닫힌다. 검사한원객체가나중에변경돼도반환canonical 문자열과typed객체에는가변참조가남지않는다.

key와value의UTF8인코딩을검사하며lone surrogate는`SurveyContractError('SURVEY_UTF8_INVALID')`로변환한다. dict순회중크기변경등복사/직렬화경계의`RuntimeError`는`SURVEY_INPUT_CHANGED`로변환한다. 기존의구체`SurveyContractError`는그대로보존하고원값·path·원예외문을오류에포함하지않는다. `raise ... from None`으로원예외trace연결의자동표시도억제한다.

이것은**동시변경에대한원자snapshot보장이아니다**. dict의같은크기치환/다른타이밍변경이항상탐지되는것은아니며,그경우에도실제로분리복사된트리에제한/계약을적용한다. 호출자는입력을변경하지않는소유권을지켜야한다. 원자적인다중입력/운영파일snapshot은별도runner책임이다.

유지보수권고도작게반영했다. `SPLITS`중복literal을없애고기존순수stdlib모듈의`FIXED_PROVINCE_SPLITS`에서복사한`MappingProxyType`으로노출한다. 새모듈에서split을변경할수없고canonical원dict에도가변참조를노출하지않는다. 상위canonical값이실행중변경되면자동추종하는구조가아니라import시점의읽기전용사본이다. split값과실행/품질정책은바뀌지않았다.

## API·오류와 호환성

공개API는동일하다: `validate_survey_request(dict)`, `validate_survey_receipt(receipt_dict,request_dict)`→frozen `ValidatedSurveyContract`; `to_dict()`는새사본이다. 모든실행/품질/출처승인false, receipt measured선언과미정산전액보존, source/config/scene/ref결속·65MiB/4GiB선언검사는그대로다.

추가오류는`SURVEY_SCENE_TIME_MISMATCH`, `SURVEY_UTF8_INVALID`, `SURVEY_INPUT_CHANGED`다. `SURVEY_SCENE_INVALID`, 기존TIME/YEAR/STRUCTURE등fixedcode는유지한다. UTF8코드에숫자8이있으므로시험의고정코드문법은`SURVEY_[A-Z0-9_]+`를쓴다. 실제I/O실패·HTTP오류·원장실행오류를처리하는API는새로만들지않았다.

의도적으로과거잘못된ID/불일치시각은이제거부된다. 정상220요청의필드schema·canonical화규칙은같지만fractional-zero UTC표현을추가로허용한다. 서로다른문자열표현은여전히다른canonical requestdigest를만든다. 실제STAC/file참조를읽은것이아니며typed통과는여전히선언일관성만뜻한다. 173/175/registry/runner연결이나SCL지원영역예외도없다. UI/API서버변경이필요없는내부Python검증기다.

## 합성 검증과 인계

추가시험은실달력/윤년·제작순서·전체ID후미/접두부·잘못된센서/orbit/zone/tile·정상2A/2B·관측시각1초/다른날·다른연도경계·정확분수0/nonzero·기간경계를다룬다. key/value/receipt의surrogate·고정오류비누출·실패후정상요청회복·원dict가복사중커져발생하는실제RuntimeError·분리복사후원입력변경·list성장/노드cap·immutable split을검사했다.

동시변경시험은타이밍이불안정한실thread스트레스가아니다. 순수숫자검사hook에서실dict를재진입변경해Python dictiterator의실제RuntimeError를결정적으로만들었다. 분리복사완료후원입력을바꿔직렬화대상이원객체가아님도검증했다. 새typed결과가원자snapshot을보장한다고해석하지않는다.

초집중28건은27PASS/1FAIL이었다. 실패는새UTF8 fixedcode의숫자8을옛시험정규식이허용하지않은시험문제였고제품실패가아니다. 원로그[focused](../../evidence/integration/survey224-focused-20261018.log)를보존하고시험regex만바로잡았다. 최종판 **70PASS/20.164초·skip0**는[final로그](../../evidence/integration/survey224-final-20261018.log), 제품/시험/문서와archive핀은[224freeze](../../evidence/integration/survey224-freeze-20261018.json)에기록한다. 관련173/175/198회귀는그제품의기존동작유지를검증하며SURVEY소비연결성공을뜻하지않는다.

Root독립검토뒤이해담당에게F1/F2보완코드·시험과실행연결PLANNED경계를인계한다. 새수집/학습/예산권한·실파일품질검증은없으며기존219/223운영원장·core·수집기에변경을가하지않았다.
