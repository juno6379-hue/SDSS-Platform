# 319 순수 표적 source profile 계약 독립 정적 검토

## 결론과 범위

상태는 **IMPLEMENTED_UNVERIFIED — 독립 정적 검토**,구현자의 기존 시험 근거는 **TESTED_SYNTHETIC / ISOLATED_ONLY**다. 격리319 코드·시험·문서·동결 로그를 읽어 순수 선언 계약 범위에서 추가 적용 차단 결함을 발견하지 못했다.시험을 다시 실행하거나 운영 source/원장/래스터를 읽지 않았고 HTTP·실QA·collector·공유제품 적용·코드수정은0이다.이 검토가 target256의 실제64MiB source 차단 해결이나 집행 연결을 뜻하지 않는다.

freeze319.json SHAe9db5b2c0b4efd9025427adacfd440c0eb60b92a6c9925b7bcafa057abb7d09b에 포함된15파일의 byte/SHA가 모두 일치했다. patch319-manifest.json SHA613a8861c36f7d47bffd7fc1521ea8231d0e1912977b6203ca6cb1f3a1e8a56b,runtime targeted_source_profile.py8e347589d802d22f89354b176d81da9ebdde27607986355ce3212ac4981493d9,doc3198a7faf431c4a5b9eb262a993fd920cf162b99d790eb6526f610aec1a55050097를 확인했다. 경로는 evidence/integration/target319-workspace-20261018 아래이며 doc319는 docs/implementation 아래다.

## 정확한 버전·지문·고정 한도

validate_request_v3는 정확한 outerv3 키와 내부 planv2 키를 요구한다.양쪽 manifest marker는 고정128 descriptor의 name/SHA와 정확히 같아야 하고 local support marker도 고정232의3GiB와 같아야 한다.임의cap/unknown키/bool·float버전·marker 누락이나 오염은 실패한다.upgrade_plan_v1만 명시적 v1→v2 사본 변환을 제공하며 기본 입력을 자동승격하지 않는다.

canonical은 복사된 원v3 전체를 sort_keys·compact separators·ensure_ascii=False·allow_nan=False·UTF8로 직렬화한다.원v3 SHA에 outer/plan marker 모두 포함된다.inventory_envelope는 outer만v2로 투영해232의3GiB 옵션 선택에 쓰고 내부 plan은v2를 유지한다.원v3 요청 SHA를 내부v2 투영 SHA로 대체하거나 실행가능 legacy planv1로 해석하지 않는다.inventory_envelope_v3는 raw 선언을 매번 재검증하며 사전생성 token을 검증된 요청으로 받지 않는다.

descriptor/marker/role table은 MappingProxyType 고정이며 source/candidate128MiB,ledger/lineage8MiB,request/plan/proposal/boundary/base config2MiB,image/label/support64MiB의 선언이다.3000행/depth32/node4M/누적16GiB도 descriptor 선언으로 고정된다.실파일이나source tree를 이 helper가 읽어 한도를 적용·계측한 것은 아니다.별도 caller 계약 복사는 더 좁은50,000nodes/depth32/container256/문자열4096/canonical2MiB를 적용하며 source4Mnodes 검사를 구현했다고 말하지 않는다.

## mutable 입력·반환과 고정 오류

정확한 built-in dict/list/str/int/float/bool/None만 bounded deep detach하고 그 사본만 검증·직렬화한다.dict/list subclass의items/iterator hook은 호출 전에 거부한다.따라서 caller를 검증한 뒤 다시 caller를 serialize하는 mutable canonical 불일치를 만들지 않는다.출력 accessor는 JSON문자열에서 매번 새 dict/list를 생성하고 canonical/digest는 문자열로 보관한다.일반 frozen attribute 변경과 authority 인자 주입도 거부하며 권한 필드는 init=False false다.

frozen dataclass와 MappingProxyType는 정상API 사용의 불변 계약이며 Python 내부 우회에 대한 보안 경계가 아니다.직접 dataclass 생성·내부 dictionary 변경을 운영 승인 token으로 인정하지 않는 전제를 유지해야 한다.현재 어떤 API도 그 객체를 실제 실행 권한으로 소비하지 않고,source_bytes_verified/source_profile_connected/execution_supported/training_ready는 모두 false다.

UTF8 surrogate·비유한/거대숫자·순환/depth/container/node/byte초과는 고정 TARGET_SOURCE_* 코드로 거부한다.복사 도중 dict iteration 크기변화로 관측되는 RuntimeError는 INPUT_CHANGED로 닫고 경로·원예외 원문을 노출하지 않는다.그러나 같은크기 변경/ABA 등 임의 동시수정의 원자snapshot까지 보장하지 않는다.얻은 분리본을 다시 완전히 검증해 그 사본과 canonical을 맞추는 보장이다.상세 CRS 실해석·affine/라벨grid실정합·bbox 실제커버·같은연도/scene·지원/품질은 선언형식 검사를 넘는 후속175/176/170 책임이다.

## 기존 시험과 legacy 경계

기존27시험·외부baseline 없는 Temp portable27의 최종로그와 fixture SHA 고정을 읽었다.이번 독립 담당자는 시험0이다.합성시험은 marker/version/key/cap·bool/타입오염·사본/고정지문·원v3/투영v2 구별·프로토타입·동시변경 유도·UTF8/숫자/구조한도·open/socket차단을 다룬다.legacy232 fixture는1900바이트/SHA dc947980dc4fe69930ebd1bbd66a2b0e32f99432749754c55b27327ed78d8c6d를 고정하고 누락/변조 시 fallback/skip 없이 실패한다.외부 baseline 폴더에 의존하는 시험 포장으로 돌아가지 않았다.

legacy v1 기본2GiB/v2 명시3GiB 출력·오류는 고정fixture를 통해 비교하고 새v3를 legacy parser가 거부함을 확인한 범위다.175 source 기본64MiB는 기존코드 불변 지문 보존의 범위이며175 실제 파일I/O/native 회귀를 새로 돌린 근거가 아니다.초기 surrogate 오류코드 시험 regex 문제와 이전 로그는 보존돼 있으며 최초 실패를 최종 통과로 덮어쓰지 않았다.

## 다음 단계와 보고

이 코드에는 실제file I/O·profile.scope 활성화·실SHA 확인·175/170 dispatch/worker 연결이 없다.후속 adapter가 정확 역할별128 source 읽기·구조/행상한·누적 JSON 계상·원본핀 전파·lock 안 재검산·worker ContextVar·기존 legacy동작/정산 보호를 별도 구현하고 시험해야 한다.현재 source64 차단은 유지하며 이미 해결됐다고 UI/사용자에게 보고하지 않는다.원격4GiB/2worker/2초/첫429/물리3000/원pending·품질·모델 gate 변경권한도 없다.

현재는 내부 격리 선언 계약이라 API/UI 제품변경·브라우저 검증을 이 단위에 붙이지 않는다.Root가 공유적용 여부를 별도 판단하고 의미있는 후속 구현의 이해자료·설명/대본FAQINDEX와 실제 UI 소비를 각각 인계해야 한다.323 실제 UI는320/322 운영 게시의 별도 GO 작업이며319 코드 완성을 실수집 승인으로 확대하지 않는다.
