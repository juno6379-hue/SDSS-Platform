# 319 — 격리된 target256 명시 profile 순수 계약 helper

상태: **TESTED_SYNTHETIC / ISOLATED_ONLY / 운영 소비 BLOCKED**.318 설계의 첫 작은 단위인 stdlib 계약 helper·합성시험만 구현했다. main 적용0, 파일 I/O/operation scope/175·176·170 연결0, 운영 source/proposal/원장/모델/label 읽기·복사0, HTTP/native/수집/학습0이다. 실제64MiB source 차단은 그대로다.

격리 위치는 `evidence/integration/target319-workspace-20261018/`다. runtime 신규1개 `backend/app/data/targeted_source_profile.py`, 시험1개와 SHA고정 legacy232 test-only fixture1개를 만들었다. 기존7코드 baseline을 원바이트 archive하고 main과archive SHA/bytes가 종료 때도 정확히 같음을 검산했다.318 doc도 원SHA로 보존했다. baseline은 코드뿐이며 운영data는 복사하지 않았다.

## 제공 API와 exact 버전

- `upgrade_plan_v1(plan, marker)`: 원 dict를 먼저 bounded detach하여 기존schema1 계획 선언을 검증하고, 새schema2+정확128marker를 넣은 독립 사본을 반환한다. 원 plan/marker/target/ref는 변하지 않는다. 이미 marker가 끼어든 v1·bool version·알 수 없는 필드는 거부한다.
- `validate_request_v3(request)`: exact outerv3와내부planv2/양쪽동일128marker·기존232정확3GiBmarker·고정target256정책/기본선언·refs/batch수를 검증하고 frozen 결과를 반환한다. v1/v2를 받아 자동선택/변환하지 않는다.
- `inventory_envelope_v3(request)`: 매번 raw declaration을 재검증하여232 `inventory_kwargs`용 정확outerv2 keyset의독립 사본을 반환한다. 이 투영은3GiB옵션선택용이며 내부plan은v2를유지한다. 기존170실행계약으로downgrade한요청이아니다.

marker는 기존 `bounded128m-3000-v1` descriptor의SHA `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`와일치한다. local support marker는 `TARGETED_LOCAL_SUPPORT_3G_V1`/`062bf36199ee4e0f142cb117cad2f0c5b25411eb3ddd43ed37b30ca3b7a75a7a`다. 두descriptor/marker/role한도표는MappingProxyType로불변이다. ROLE_LIMITS_SHA256도 canonical표에서계산한다.

ROLE_LIMITS는source/candidate128MiB,ledger/lineage8MiB,request/plan/proposal/boundary/baseconfig2MiB,image/label/support파일64MiB의**선언표**다. 이 helper는 파일을 열지 않아 상한을실제file read에적용한것이아니다.128source·3000scenes+history/depth32/node4M/누적16GiB는descriptor선언으로고정됐지만실source/tree/I/O를검사·계측하지않는다. 라벨/원격budget을128로늘리지않는다.

## 출력과 canonical 결속

결과에는 canonical_json/request_sha256/inventory_envelope_json과 고정status `DECLARED_CONTRACT_VALID_EXECUTION_BLOCKED`가 있다. execution_supported/source_bytes_verified/source_profile_connected/training_ready는 init=False인false필드라일반생성인자로true를주입할수없고frozen변경도거부한다. to_dict()/inventory_envelope()는매번새사본이다. dataclass직접생성이나Python내부우회는입력검증/운영권한을대신하지않으며어느API도이결과를승인token으로받지않는다.

request_sha256는 **검증된분리본의원v3전체**를sort_keys/compact separators/ensure_ascii=False/allow_nan=False의UTF8로canonical화한지문이다. outermarker와planmarker가모두포함되고내부v2envelope의SHA와다르다. 원v3request/approval/향후receipt의핀은이digest를써야한다. envelope를원요청처럼재해시해과거승인과혼합하면안된다.

refs는정확path/sha256이며상대forward-slash경로·허용prefix·소문자64hex를검사한다. 이는실파일존재/alias/reparse/hardlink/지문을검사한것이아니다. 실제경계95%·라벨픽셀/grid실진실·같은source/년/scene·품질·support는기존175/176/170의미연결후속에남아있다. 도형field를형식검사했다고실도형일치를인증하지않는다.

## 220 유형의 mutable/canonical 오류 방지

caller tree를검증한뒤원caller를다시serialize하지않는다. 정확built-in dict/list/str/int/float/bool/None만받아bounded deep copy하고 **그분리본만검증·canonical화**한다. dict/list subclass의items/iterator/prototype hook은실행하지않고거부한다. output사본이나원caller를나중에바꿔도저장canonical/digest는변하지않는다.

사본복사상한은5만nodes/depth32/container256/문자열4096·UTF8canonical2MiB다. 이것은source4Mnodes상한의실제구현이아니라작은계약dict복사에만적용하는더좁은한도다. cyclic/deep/거대container·비유한/범위밖숫자·surrogate·NUL·타입오염은고정 TARGET_SOURCE_* 오류로거부한다. 불완전UTF8원바이트나중복JSON키를parse하는API는이번범위에없어bytes입력자체를거부하며후속byte/fileadapter가별도검사해야한다.

dict크기변경처럼관측가능한동시iteration변경은 TARGET_SOURCE_INPUT_CHANGED로거부한다. 임의동시caller변경의원자snapshot/ABA검출을보장하지않는다. 복사도중얻은분리본을완전히재검증해그분리본과digest를일치시키는보장이다. 검증후caller mutation을유도하는시험과copy중iteration mutation을유도하는시험으로이경계를구분했다.

## 합성시험과 실패 이력

최종runtime/시험판에서 **격리27 PASS/0.232초(wrapper2.328초)**, 외부baseline폴더없이runtime/test/SHA고정fixture3파일만복사한 **Temp배치27 PASS/0.146초(wrapper1.828초)** 다. 두실행모두exit0/skip0이다. `focused-final319.log`, `portable-final319.log`, `test-results319.json`을고정한다. 시간은시험runner와wrapper범위를구분하며운영성능이나RSS보장이아니다.

시험은exactmarker/outerv3-planv2양방향·unknown/bool/key/cap오염·원v3canonical과내부v2투영분리·deepcopy/불변/falsegate·batch/ref/target선언·UTF8surrogate/nonfinite/거대정수·순환/depth/node/canonicalbyte상한·prototype·mutation·open/Path.open/socket차단을확인했다.232 원판파서의v1(default2GiB)/v2(명시3GiB)출력/오류와새v3거부도합성검증했다. default175source64는코드원바이트불변으로보존확인했으며175파일I/O·실native회귀를새로실행했다고주장하지않는다.

최초26시험중1FAIL/0.629초는시험오류코드정규식 `[A-Z_]+`가정상거부코드UTF8의숫자8을허용하지않은문제였다. 제품은부적절surrogate를거부했다. 수정전시험소스와 `initial-failure319.json`에원관측을보존했다. 최초도구출력은chat에있고완전rawlog파일은당시capture하지못했음을명시한다. regex를숫자허용으로바꿨고오류를정상통과로바꾸지않았다. 이후권한field생성자주입을추가방지한최종판27PASS가위로그다. 이전27PASS로그도별도보존했다.

legacyfixture1900B/SHA `dc947980dc4fe69930ebd1bbd66a2b0e32f99432749754c55b27327ed78d8c6d`는tests/fixtures아래만둔다. loader가bytes/SHA를먼저검사하고누락·변조는실패하며fallback/skip0이다. baseline-code/외부workspace/main데이터폴더없는Temp배치로확인했다. testimport는코드fixture실행뿐이며운영collector를import하지않는다.

## 동결·적용·다음 소유

patch319.diff/patch319-manifest.json/freeze319.json에신규runtime1+test2와baseline7·시험로그·문서지문을구분해고정한다. 공유main새helper부재와기존baselineexact를끝에검산했다. 아직Root의독립리뷰/적용승인이없어main반영0이다. 다음321은별도320게시준비정적검토이며319제품과동시편집하지않는다.

다음작은단위는명시profile의실fileadapter·같은scope/read/hash/depth/node/3000행/누적16GiB연결이다.175/170의source64차단·170lock내재검산/worker ContextVar·전체metadatawriter와176source핀전파·legacyexact시험은아직미구현이다. 이helper단독으로source대파일을읽거나3GiBinventory를실행하거나수집을승인할수없다. 기존256/scene/window/split/B02/SCL·품질/4GiB/2worker/2초/첫429/3000/oldpending/모델gate를바꾸지않았다.

내부typed계약이므로현재API/UI코드변경·실브라우저검증은필요하지않고운영기능연결이라고게시하지않는다. Root에완료코드/시험/설계·계약·사용법·한계를인계하여독립리뷰후이해담당의쉬운설명·대본FAQINDEX이력에반영하도록요청한다. 이해자료·운영연결은이담당이완료했다고표현하지않는다.
