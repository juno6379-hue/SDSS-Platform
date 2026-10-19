# 289 RFC — SURVEY의 원문 관측시각과 ID 명목시각을 분리하는 명시 v2

상태: **PLANNED / RFC_ONLY**. 제품·시험코드·runner·예약·소비자 연결을 구현하지 않았다. 운영 data/source/ledger/model 읽기/복사·HTTP·수집0, 실제 나지 취득/품질/학습 승인0이다. 읽은 것은 현재 개발 원장, 아래 고정 메타 evidence와 완료된226/246·260/265 문서다. 기존289 문서 충돌이 없음을 확인했으며 이 문서만 새로 작성한다.

## 쉬운 설명과 실제 공백

장면 ID에는 datatake 시작의 명목시각이 초 단위로 들어가지만 저장 STAC에는 소수초까지 적힌 시각이 있을 수 있다. 현재226은 요청 시각이 ID의 초 단위 시각과 같은 순간이어야 하고,246은 그 요청 시각과 STAC 시각도 같은 순간이어야 한다. 따라서 `.024000Z`처럼0이 아닌 소수초가 있으면 기존 계약이 차단한다. 원문에서 소수초를 지워 통과시키면 검증 대상 사실을 바꾸는 셈이다.

필요한 것은 기존 검사를 몰래 느슨하게 만드는 예외가 아니라, **ID가 명목상 표현한 시각과 공급자 문서가 관측값으로 선언한 시각을 별도로 보존하는 새 계약**이다. 이 문서는 그 작은 v2의 입력·실패 경계와 추가 증거 요구를 제안한다. 새 형식 자체가 PC 공급자의 모든 시각 의미를 증명하지는 않는다.

## 이번에 실제 확인한 증거의 범위

`evidence/integration/selection262-observed-stac-shape-root-20261018.json`의 SHA는 `ff402556624fd5c260b106739445769ff833dca8c1cf6e12fa33593c13195cfb`다. 완료249 저장 메타를 Root가 관측한 이 evidence에는 다음 두 원문이 있다.

```text
scene_id: S2B_MSIL2A_20240813T021349_R060_T51MUR_20240813T055551
raw_datetime: 2024-08-13T02:13:49.024000Z
```

이 evidence가 가리키는 저장 STAC SHA는 `b59e97e567c54aecd2709291487b0cf352ae2e1f5c05932a4993c53de1e5b2e6`다.289에서는 그 운영 STAC 파일을 다시 열지 않았다. evidence 상태도 `OBSERVED_STORED_METADATA_ONLY_NOT_260_VALIDATION`이다. 즉 문자열의 공존은 확인되지만 공급자 원응답 인증, PC self/asset URL·제품 결속, 시각 의미의 공식 정의, 실제 파일/픽셀/권한 검증은 이 근거로 확인되지 않는다.

특히 collection=`sentinel-2-l2a`만 같다고 PC 출처라고 판정하면 안 된다.262는246의 전체 PC 정책 합격 증거가 아니다. 기존 수집기는 저장 시 서명 query를 제거할 수도 있으므로 저장 bytes와 원격 전송 당시 bytes도 구분해야 한다.289는 지워진 원문이나 서명을 복원하지 않는다.

완료246 문서 SHA는 `f86f51c4ac6638e06938dbac3ee7992ea7a6c999c8f012c43be3540bd9e54154`,226 문서 SHA는 `d5ac5d436343e03401907b88f217a24404eff385e4362b4bf3c8ae2097d7b432`다. 기존 v1은 분수0의 동시각 표현을 허용하고 nonzero 소수초 불일치를 거부한다. 이번 RFC에서는 이 동작과 기존 canonical digest/출력을 보존한다.

## Root가 확인한 1차 규격과 적용 한계

Root가 공개 문서를 직접 확인해 전달한 근거를 추가한다.289 담당은 해당 페이지를 별도로 HTTP 조회하지 않았으며, 운영 데이터 원격 요청도 하지 않았다.

- [STAC Common Metadata — Date and Time](https://github.com/radiantearth/stac-spec/blob/master/commons/common-metadata.md)는 timestamp에 RFC3339 §5.6을 요구하고 `datetime`이 capture의 nominal 시각일 수 있다고 설명한다. STAC `datetime`을 모든 asset/pixel의 정확한 물리 촬영시각으로 단정하지 않는다.
- [Copernicus SentiWiki — Sentinel-2 Products / Compact Naming](https://sentiwiki.copernicus.eu/web/s2-products)은 첫 날짜 구간을 초 단위 datatake start sensing time으로 설명하고, 뒤 날짜 구간은 별도 product discriminator로 설명한다. discriminator는 앞 시각보다 이르거나 늦을 수 있으므로 이름의 뒤 시각을 무조건 실제 제작 완료시각이라고 부르거나 단조 순서의 공식 근거로 쓰면 안 된다.

이 규격은 ID의 초 단위 이름과 STAC 날짜 표현의 역할을 구분하는 근거다. **PC가 properties.datetime을 어느 원필드에서 어떻게 추출하는지 또는 원ID와 항상 같은 calendar-second인지 증명하지 않는다.** 두 nominal 표현이 자동으로 같은 의미라는 뜻도 아니다. 같은초 관계는 아래 v2의 검토 대상이며 provider 근거가 확보되기 전 운영 BLOCKED를 유지한다.

현재226은 뒤 timestamp에 앞 timestamp보다 이르지 않다는 좁은 검사를 적용한다. v1/default는 변경하지 않는다. v2 첫 최소 구현에서 이를 재사용한다면 이름을 `legacy discriminator order constraint`로 명시하고 공식 제품의 물리적 제작 순서를 인증한다고 표현하지 않는다. 공식적으로 가능한 이른 discriminator 사례를 받아들이는 변경은 이번 소수초 공백과 분리한 후속 검토 대상이다.289에서 그 gate를 해제하지 않는다.

또한 이 제안의 UTC Z/소수6자리/초0..59는 지원하는 좁은 문법이다. RFC3339 전체에서 offset·더 긴 소수·leap second 표현이 모두 잘못됐다고 주장하지 않는다. 지원 밖 표현은 이 구현의 BLOCKED 조건으로 명시한다.

## v1과260을 그대로 유지

| 경로 | 시각 계약 | 이번 제안과의 관계 |
|---|---|---|
| 226/246 SURVEY v1/default | 선언 datetime=ID acquisition, 선언과 raw는 같은 순간; nonzero 불일치 차단 | 코드·API·schema1·digest·오류·출력 그대로 |
| 260/265 `DEFICIT_AOI_BBOX_CONTAINS_V1` | normalized item과 raw Feature가 datetime 원문을 정확히 함께 선언하고 유효 UTC/요청 연도인지 확인 | AOI metadata 선별 정책이며 이번 SURVEY v2로 승계하지 않음 |
| 제안 SURVEY v2 | ID 명목 시각과 원문 관측시각을 별도 필드로 결속 | 새 schema/marker/전용API·새 request digest 필요 |

260은 ID의 초 시각과 raw 시각의 의미를 같다고 인증하는 API가 아니다.260의 v2 요청/marker나 실선별 통과를 새 SURVEY v2 승인으로 재사용하지 않는다. 기존281 파일 reader도 v1 validator로 검증하는 한 v2를 실행 전에 거부해야 한다. 신구 입력을 자동 변환하거나 알 수 없는 marker에서 v1로 fallback하지 않는다.

## 제안하는 최소 v2 입력

최상위 기존 요청의 schema1 키/행위를 유지하고 **새 schema2에만** 정확한 `scene_time_policy` 필드를 추가한다. marker는 `PC_RAW_STAC_TIME_EXACT_V2`로 고정한다. 이름에 PC를 넣어 다른 공급자로 확대되지 않게 한다. `selected_scene.datetime`을 두 의미로 재사용하지 않고 v2의 정확 키 집합을 다음으로 바꾼다.

```json
{
  "schema_version": 2,
  "scene_time_policy": "PC_RAW_STAC_TIME_EXACT_V2",
  "selected_scene": {
    "id": "<unchanged full catalog or compact ID>",
    "id_nominal_datetime": "<exact ID acquisition as YYYY-MM-DDTHH:MM:SSZ>",
    "observed_raw_datetime": "<exact raw properties.datetime string>",
    "source_group": "<province>/<unchanged ID>",
    "stac_ref": {"path": "<pinned local STAC>", "sha256": "<raw bytes SHA>"}
  }
}
```

위 예시는 변경되는 부분만 표현한 것이며 단독으로 유효한 전체 요청은 아니다. 기존 seed/고정split/year/bbox/기간/근거·refs·config_sha256·policy·budget_snapshot·output경로·false 권한 필드는 그대로 요구한다. 실제 좌표나 원격 접근 권한을 이 문서에서 새로 발명하지 않는다.

`kind=BARE_LABEL_SURVEY_REQUEST`는 유지하되 schema2와 marker의 조합만 새 전용API가 받는다. schema1+marker, schema2+marker없음, 임의marker, v2에 옛datetime 추가, 둘 중 한 시각 누락, bool/객체대체 등은 모두 거부한다. source_group은 입력 ID와 exact 결속하고 baseline이나 원ID를 삽입·삭제·alias화하지 않는다.

`observed_raw_datetime`의 observed는 “고정 문서에서 관측한 문자열”이라는 뜻이다. 모든 픽셀의 실제 촬영시각이나 정답시각을 계측했다는 뜻으로 해석하지 않는다.

marker와 두 시각은 canonical request digest와 파생 config digest에 포함한다. 같은 순간을 나타내더라도 원문 문자열이 다른 v2 요청은 서로 다른 digest다. 예전 config/request/approval/key를 재사용하지 않는다. digest 변경 전에 provider 시각을 변환하거나, v2 검증 뒤 marker/관측시각을 버리고 v1 승인 자료를 만드는 경로는 금지한다.

## v2에서 허용할 비교와 차단 조건

1. ID는 기존226의 두 전체 문법·실달력·위성/orbit/tile 검사를 재사용한다. 뒤 discriminator의 legacy 순서 제약은 위 한계를 명시해 보존하고 물리적 제작시각으로 재명명하지 않는다. ID 앞 시각을 파싱해 결정되는 nominal 문자열과 요청 `id_nominal_datetime`이 exact여야 한다. nominal은 초 정밀도 표준형만 허용하고 raw에서 유추해 채우지 않는다.
2. `observed_raw_datetime`은 UTC Z·소수초0~6자리·유효 실달력이어야 하고, SHA로 고정한 raw STAC의 `properties.datetime`과 **문자열 exact**여야 한다. `.024Z`와 `.024000Z`를 자동 동등화하지 않는다. 원문이 바뀌면 새 SHA/요청이 필요하다. `start_datetime/end_datetime`이나 제품 생성시각으로 대체하지 않는다.
3. **명시적 새 정책 관계:** raw와 nominal의 연·월·일·시·분·초 구성요소가 같아야 한다. 소수초는 관측시각에 그대로 남는다. 이 검사는 두 입력을 같은 timestamp로 만들거나 ID/원문을 고쳐 쓰는 과정이 아니다. 출력에도 `same_calendar_second_components=true`와 `observed_equals_nominal_instant`를 따로 기록한다. `.024000Z`라면 두 번째 값은false다.
4. 이 관계는 PC의 시각 의미에 대한 **검토 대상 가정**이다.262 한 건만으로 공식 정의가 확인된 것이 아니며, 아래 실provider 근거가 확보되기 전 **운영 사용은 BLOCKED**다. 새로운 수락 관계를 합성으로 구현해도 source authenticity/operational compatibility 플래그를 true로 만들지 않는다. 향후 다른 초·날짜까지 허용하려면 새 별도profile 검토가 필요하고 자동±1초 허용을 추가하지 않는다.
5. nominal과 raw 모두 요청 연도/기간 안이어야 한다. 뒤 discriminator를 실제 제작 완료시각으로 가정해 새 `discriminator>=raw` 검사를 추가하지 않는다. 기존 legacy discriminator 순서 gate의 허용범위를 넓히지도 않는다. 일/연도 경계나 지원 밖 leap second를 관용적으로 보정하지 않는다.
6.246의 정확 ID·collection·PC self endpoint·제품 URI/baseline·SCL href/host/layout·MGRS/관측 compact 시각 결속은 계속 적용한다. 소수초 때문에 제품명이나 URL의 compact 시각을 재작성하지 않는다. 제품/SCL 출처가 다르거나 PC 여부가 불명확하면 시간만 맞아도 BLOCKED다.

새 결과는 두 문자열과 원ID/raw SHA를 모두 보존하고 `time_policy`, `id_nominal_datetime`, `observed_raw_datetime`, `same_calendar_second_components`, `observed_equals_nominal_instant`를 기록한다. nominal은 “공급자가 인증한 실제 시작시각”이라고 명명하지 않는다. source/remote/header/ledger/quality/독립정답/registry/target/실행/학습은 여전히false다.

## 최소 구현 경계 제안 — 아직 미구현

첫 단위는 **순수 v2 검증기만 격리 구현**하는 것을 권장한다. 기존 함수의 default 의미를 바꾸지 않는다.

- `bare_label_survey_contract.py`: 기존 v1 API를 그대로 두고 `validate_survey_request_v2()`/`validate_survey_receipt_v2()`를 추가하는 안. 공통 구조/ID 파싱을 재사용하되 v2 request를 v1로 변환해 호출하지 않는다. receipt2는 schema2/marker/두 시각/원 request digest를 exact 결속한다. 기존 measured선언/미정산전액보존/false 권한을 유지하며 실제 실행 receipt로 위장하지 않는다.
- `bare_survey_stac_binding.py`: 전용 `validate_survey_stac_binding_v2()`에서 v2 raw 문자열 exact와 명시 관계를 검사한다.246 v1의 비교 코드는 그대로 두고 PC product/URL 검사를 공통화할 경우 v1 전체 출력 동등 회귀를 요구한다. 외부에서 생성한 typed 객체만 믿지 않고 요청을 다시 검증한다.
- 전용 합성시험: v1/default와 신규 v2를 구분하는 fixture를 추가한다. 문서/시험/판본 pin과 독립리뷰를 같은 단위로 마감한다.

281 reader의 v2 연결은 그 다음 좁은 단위다. 기존 v1 reader는 계속 v2를 pre-open 거부하고, 새 `read_pinned_survey_stac_v2()` 같은 명시 API에서만 v2 검증기를 선택한다. 단일descriptor·≤1MiB·SHA/alias/reparse/hardlink·file/parent identity·partial read 계측·동일 read 한도를 그대로 재사용한다. reader가 provider profile을 자동 감지해 버전을 올리면 안 된다. Root288의281 main 적용·실배치 검증과도 독립된 후속 승인이다.

coordinator/원장/remote runner/registry/173/175 연결은 이번 또는 순수v2 첫 구현 범위에 넣지 않는다. 이 두 문자열을 허용한다고 예약·quality gate를 통과시킬 수는 없다. 실제 provider profile을 승인한 Root의 고정 근거와 별도 실행 GO가 필요하다.

## 시험 수락안

| 분류 | 반드시 확인할 사례 |
|---|---|
| v1/default 동등 | 기존226/246/281 합격 입력·canonical digest/출력 동일, nonzero분수 기존차단 유지, schema2 자동fallback0 |
| 명시v2 정상 | same-second `.024000Z`·`.000000Z`·분수없음, 두 ID profile, raw 문자열 보존·원ID/source_group 불변·새 digest |
| 문자열/소수 경계 | raw `.024Z` vs 요청`.024000Z`는차단, 1..6자리 허용,7자리·offset·빈값·null/bool/객체·반올림없음; `.999999`를다음초로올리지않음 |
| 시간/기간/달력 | 같은초최대분수, 다음/이전초차단, 초/일/연도 경계·요청기간 끝 초분수·윤년/잘못된날짜·legacy discriminator순서제약보존·지원밖leap-second차단 |
| 오염/누락 | 중복JSON key·UTF8/surrogate·BOM/NUL·NaN/거대JSON·알수없는schema/marker·한시각누락·옛datetime추가·원문SHA변경 |
| provider/제품 | EarthSearch/다른self/collection만같은문서 차단, PC asset host/product/orbit/tile/baseline/생성시각 변조·signedquery·URL alias 차단 |
| request/receipt | marker/두시각/원요청digest/config 불일치 차단, source/refs/split/예산/미정산선언가드·실행false 그대로 |
| 파일 연결 후속 | v1 reader의v2 pre-open0·v2 exactread/SHA/교체/성장/partial계측, 양import·사본불변·임의권한true 거부 |

289에서는 이 시험을 실행하거나 테스트코드를 작성하지 않았다. 표는 후속 수락 조건이며 합성 PASS나 실제운영 PASS를 선포하는 근거가 아니다. 예상 오류는 고정 `SURVEY_*_TIME_POLICY_INVALID`, RAW_TIME_MISMATCH, NOMINAL_TIME_MISMATCH, TIME_COMPONENT_RELATION_INVALID, PROVIDER_UNSUPPORTED 등의 형태로 제안하되 기존 오류코드를 재사용해 의미를 바꾸지 않는다. 민감 URL/원입력/무제한 예외문은 전달하지 않는다.

## 실제 PC 관측과 운영 허용 전 필요 근거

Root가 별도 승인한 read-only/계측 예산 경로로 PC self 원문·동일제품 SCL href·제품 선언을 정확히 고정해야 한다. 원응답/저장 변환 여부·관측시각의 문자열 정밀도·ID/제품 명목 시각과의 공식 의미를 공급자 문서/고정 관측과 함께 검토해야 한다.262의 저장 예시로 이 단계를 대체하지 않는다. 실제 원격 관측은 현재 승인하지 않았다.

검토할 자료는 여러 정상scene/위성·소수0/nonzero·초/일 경계에서 어떤 관계가 선언되는지다. 표본이 정책의 모든 경우를 증명하는 것은 아니므로 지원범위를 좁게 고정하고 미정은차단한다. 지원provider policy·관측 근거 SHA·검토판본·허용범위·실행승인 여부를 Root가 별도 고정해야 한다. profile 근거가 없거나 공급자 정의가 같은초 관계를 지지하지 않으면 자동 예외 없이 **운영 BLOCKED 유지**다.

그 뒤에도 같은global lock/현재원장·65MiB예약·metadata1MiB+COG64MiB 실측·2초/첫429·finally 미계측전액보존·label/SCL/scene/window/split 및 support 겹침·신규파일/registry 진실계약·최종80/95/나지256은 별도 조건이다. 원provider 시각 연결을 고쳤다고 나지획득/독립정답/학습을 승인하지 않는다.

이 RFC는 내부 API 제안이며 UI/API 응답 변화가 없다. 현재 화면 수정·서버 재시작·브라우저 검증은 필요 없다. Root에 문서 지문을 인계하고 최소 순수v2 격리 구현 여부를 결정받는다. 이해자료 갱신은 실제 구현/검증을 완료한 후 담당에 인계하며, 설계만 있는 현재 상태는 PLANNED로 설명한다.
