# 246 — SURVEY 고정 STAC 메타데이터의 출처 선언 결속

상태: **IMPLEMENTED / TESTED_SYNTHETIC**. 실제 운영 STAC 문서와의 호환성, 원격 자산의 진위·접근 권한·영상 품질은 **IMPLEMENTED_UNVERIFIED**다. 실제 SURVEY 소비자 연결은 **PLANNED**이며 집행 권한은 없다.

## 쉬운 설명과 범위

226 계약은 장면 이름과 수집 의도를 보존한다. 이번 단위는 여기에 “검토 대상으로 고정한 STAC 원문 바이트가 그 장면·관측시각·제품·SCL 주소를 실제로 함께 선언하는가”라는 순수 검사를 추가한다. 장면 이름만 그럴듯한 경우와 원문 SHA가 다른 경우를 거부한다. 입력끼리 일치한다는 결과이며, 공식 서버에서 받은 진짜 문서라는 인증은 아니다. 호출자가 모든 입력을 함께 위조할 가능성을 이 함수가 없애지 않는다.

변경은 신규 모듈 `backend/app/data/bare_survey_stac_binding.py`, 신규 시험 `tests/test_bare_survey_stac_binding.py`, 이 문서 3개뿐이다. 기존 226 계약·ID 원문·기본 출력·모델 승인 조건과 collector/173/175/170은 수정하거나 연결하지 않았다. 운영 자료·원장·모델·원격 STAC·래스터를 읽지 않았고 HTTP·수집·실제 QA는 실행하지 않았다.

## API와 입력 소유권

```python
from app.data.bare_survey_stac_binding import validate_survey_stac_binding

bound = validate_survey_stac_binding(
    request,                 # 기존 validate_survey_request에 합격하는 226 요청
    raw_stac,                # 선택 stac_ref SHA에 고정된 immutable bytes
    {"key": "SCL", "source_url": exact_url, "product_uri": exact_safe_uri},
)
report = bound.to_dict()
```

모듈은 경로를 열지 않는다. `stac_ref`의 경로는 요청 선언으로만 읽고, SHA는 전달받은 바이트와 직접 대조한다. 호출자가 파일 읽기·파일 정체성/성장/교체 검사·전체 실행 I/O 예산을 별도로 책임져야 한다. 현재 그런 소비자 연결은 없다. 검증 결과는 frozen dataclass와 canonical JSON이며 `to_dict()`는 매번 분리된 사본을 반환한다. 입력 dict를 보관하지 않으며 외부 수정이 결과를 바꾸지 않는다. STAC 경로가 manifest/boundary/ledger/base_config/seed 근거 경로와 대소문자만 다른 별칭이어도 거부한다. 실파일 symlink·hardlink 동일성까지 검사하는 기능은 없다.

## 고정 지원 정책

정책 이름은 `PC_SENTINEL2_L2A_SCL20_V1`이다. 저장소 `backend/app/data/service.py:24`의 PC 카탈로그와 `:26`의 Sentinel 호스트를 기준으로, 이 helper의 허용 범위를 더 좁게 고정했다. 이번 작업에서 공식 웹 문서를 조회하거나 공급자 실응답을 확인하지 않았다. 따라서 아래는 구현의 정적 수락 정책이며 공급자 전체 현재 스키마를 보증하는 표현이 아니다.

- STAC `Feature`, `stac_version="1.0.0"`, collection `sentinel-2-l2a`, 요청과 정확히 같은 ID만 허용한다.
- `rel=self` 링크는 정확히 1개이며 `https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/<원문ID>`와 정확히 같아야 한다.
- asset key는 대문자 `SCL`만 허용한다. 선언 URL과 `assets.SCL.href`, 선언 제품과 `properties["s2:product_uri"]`가 각각 정확히 같아야 한다.
- HTTPS의 `sentinel2l2a01.blob.core.windows.net` 또는 `sentinel2l2a02.blob.core.windows.net`만 허용한다. 사용자정보·포트·query·fragment·백슬래시·percent escape·제어문자·비ASCII·빈 경로 구간·`.`/`..`는 거부한다. 서명 query를 제거해 통과시키지 않는다.
- URL은 `sentinel2-l2/<zone>/<latitude-band>/<square>/<YYYY>/<MM>/<DD>/<정확한 product.SAFE>/GRANULE/L2A_T<tile>_A<6자리>_<유효시각>/IMG_DATA/R20m/T<tile>_<관측 compact시각>_SCL_20m.tif` 구조만 허용한다. 월·일은 두 자리로 고정한다. `.SAFE` 구간은 정확히 1개다. 다른 정상 공급자 경로도 지원 범위 밖이면 거부될 수 있다.
- 제품 URI는 baseline `Ndddd`를 포함한 Sentinel-2 L2A `.SAFE` 이름이어야 한다. ID와 위성·관측 compact시각·궤도·tile·생성 compact시각이 모두 같아야 한다. 원문 ID에 baseline이 있으면 그것도 정확히 비교한다. `s2:processing_baseline`이 존재하면 `NN.NN` 문자열과 제품의 baseline이 일치해야 한다.

원문 ID에 baseline이 없어도 원문을 수정하지 않는다. 별도의 원시 제품 URI를 비교할 뿐 새 alias ID를 만들거나 baseline을 추정하여 보충하지 않는다. EarthSearch·Landsat·다른 STAC 버전·다른 밴드·자산 별칭·다른 경로 형식은 미지원이다.

## 시각, 오류, 자원 한계

관측 datetime은 UTC `Z`와 최대 6자리 소수초만 허용하고 실제 달력으로 파싱한다. 요청 선언과 원문 관측시각을 정확히 비교한다. `.000Z`는 같은 시각이지만 두 원문 문자열은 결과에 각각 남는다. `.024Z`를 초 단위 요청 시각에 맞춰 반올림하거나 삭제하지 않는다. 그런 입력은 `SURVEY_STAC_TIME_MISMATCH`로 **BLOCKED**다. 실제 공급자 문서가 그 조합인지 이번에는 읽지 않았으므로 실호환성을 주장하지 않는다.

원문은 immutable `bytes`만 받으며 2바이트 이상 **1MiB 이하**, 깊이 **32 이하**, JSON 키·값·구조 순회 노드 **25,000 이하**로 제한한다. SHA를 JSON 파싱 전에 검사하고 깊이도 decode 전에 스캔한다. UTF-8 BOM/NUL/잘못된 UTF-8/중복 key/NaN·Infinity·overflow/비정상 surrogate는 거부한다. 노드 한도는 파싱 후 순회 검사이므로 파서의 모든 순간 할당을 사전 차단하지 않는다. 입력 bytecap이 먼저 적용되지만 최대 RSS나 모든 악성 JSON에 대한 CPU 시간 상한을 실측·보증한 것은 아니다. 요청 자체의 기존 개별 한도는 226 검증기가 유지한다. 이 1MiB는 메모리에 전달된 한 STAC 문서 한도이며 원격 COG 예산이나 전체 metadata I/O 예산을 대체하지 않는다.

오류는 `SurveyStacBindingError`의 고정 코드다. 대표적으로 REQUEST_INVALID, PIN_MISMATCH, BYTE_LIMIT, DUPLICATE_KEY, TIME_INVALID/TIME_MISMATCH, FEATURE_INVALID, PRODUCT_INVALID/PRODUCT_MISMATCH, SELF_INVALID, ASSET_MISMATCH, URL_INVALID, ASSET_LAYOUT_UNSUPPORTED, REFERENCE_ALIAS가 있으며 모두 `SURVEY_STAC_` 접두사를 쓴다. URL·토큰·입력값·내부 파싱 예외 내용을 오류에 넣지 않는다.

## 기존 수집 근거와 혼동하지 않는 결과

`scripts/collect_samples.py:381` 이후 기존 수집기는 `stac_feature` 또는 item을 저장하면서 서명 query를 제거할 수 있고, `:387`에 `raw_feature_available`과 `signed_query_redacted`를 별도로 기록한다. 따라서 기존 `stac-item.json`이 전송 당시 원격 응답 원바이트라고 가정하면 안 된다. 이번 함수는 **호출자가 선택하여 SHA로 고정한 바이트**만 검증하며 제거된 query나 원래 응답을 복원하지 않는다. 기존 수집기의 `:399` 이후 STAC product_uri와 제품 XML PRODUCT_URI 대조도 이 함수가 대신하지 않는다.

성공 상태 `PINNED_STAC_METADATA_BOUND`에서는 `metadata_consistency_verified=true`만 선언한다. source_authenticity/remote_asset/raster_header/quality_eligible/independent_ground_truth/scientific_accuracy/execution/collection/ledger/training/registry/target_consumer에 관한 결과 gate는 전부 false다. SCL 자체도 독립 현장 정답이나 학습 승인 근거가 되지 않는다.

## 시험 증거와 동결

최종 실행:

```powershell
$env:PYTHONPATH="$PWD;$PWD/.runtime;$PWD/backend;$PWD/scripts;$PWD/tests"
$env:PYTHONDONTWRITEBYTECODE='1'
python -X utf8 -m unittest test_bare_survey_stac_binding test_bare_label_survey_contract -q
```

결과 **45 PASS / 0.216초 / skip 0**: 신규 13개와 기존 32개다. Temp 폴더의 합성 바이트, 호출 중 파일/소켓 접근 차단, 입출력 사본 분리, 기존 226 출력 동등, 두 호스트, ID/baseline/제품 결속, 소수초 불일치, 정확한 self·asset·URL, 크기·깊이·노드·엄격 JSON·alias·false gate를 검사했다. 최초 77 PASS 실행은 fixture TestCase 직접 import 때문에 기존 32개가 중복 발견된 수치였다. 모듈 import로 고친 최종 45개를 유효 집합으로 기록하며 두 실행을 합산하지 않는다. 실운영 STAC·영상·인증·성능 최대치 시험은 없다.

최종 코드 지문:

| 파일 | bytes | SHA256 |
|---|---:|---|
| 신규 helper | 9951 | `16a1d8684e47b2d7f1cb63e062f9fe1e2831f10eb4bd68eedae6e6ee7e788b4a` |
| 신규 시험 | 12958 | `1778d168b3ab6914a57a1607a8bab096f4899c7cee688198749ae507287809e2` |
| 읽기만 한 기존 226 helper | 15549 | `e035cc1afb77b9461f1e5df1256dcf58bf82199e4dbb5fdba4af6e1518f8dd60` |
| 읽기만 한 기존 226 시험 | 24593 | `9376b52503f1518617dbd7d8ac08d1e800249c3560e1e586aa78eb2eae99d449` |

기존 두 파일은 이번 작업에서 편집하지 않았다. 위 지문은 최종 관측값이며 옛 226 동결 원바이트와의 독립 비교를 새로 수행했다는 주장은 아니다. 이 문서 자신의 최종 SHA는 자기참조를 피하여 Root 인계에 별도 전달한다. 신규 3파일 외 별도 runner·receipt·동결 JSON은 만들지 않았다.

## 인계와 미완료

Root 독립 코드 검토 뒤 이해 담당에게 쉬운 설명·발표·FAQ·INDEX·이력 반영을 인계한다. 이 내부 순수 함수는 API나 UI에 연결되지 않았으므로 프론트 변경·서버 재시작·실제 브라우저 확인이 필요한 완료 기능은 아직 없다. 향후 소비자 연결은 고정 바이트 획득과 출처 신뢰·전체 자원계측·실파일 변경 방지·공급자 실호환성·정확한 오류 전달·추가 승인 계약을 별도 설계해야 한다. 이 단위 완료는 실제 수집·영상 품질·독립 정답 확보·모델 학습 준비 완료를 뜻하지 않는다.
