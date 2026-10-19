# 310 — PC Sentinel-2 STAC 시각의 공개 생성 근거 조사

상태: **공개 생성 경로 확인 / 현재 운영 동일성 미확보 / SURVEY v2 운영 BLOCKED**

조사일: 2026-10-18 KST. 이 단위는289 RFC의 시각 의미 공백을 보완하는 문서 조사다. 제품 구현, 기존 v1/default 변경, SURVEY 실행, 나지 취득은 하지 않았다. CONTINUOUS_DEVELOPMENT.md와289 RFC를 읽었으며304 종료·307 감사 소유와 분리했다.

## 쉽게 설명하면

Microsoft의 공개 작업 코드와 그 코드가 지정한 원제작 라이브러리를 이어 읽으면, STAC datetime을 제품 XML의 `PRODUCT_START_TIME`에서 가져오는 경로가 나온다. 반면 장면 ID는 별도 `PRODUCT_URI`에서 만든다. 따라서 이름을 잘라 만든 시각으로 원문 STAC 시각을 대체하면 두 근거를 섞게 된다.

이번에 찾은 것은 **공개 코드의 생성 방식**이다. 해당 코드가 현재 PC 카탈로그의 모든 자료를 생성한 실제 배포판인지, 프로젝트의 특정2024 자료도 같은 경로로 만들어졌는지는 확인하지 못했다. 공개 코드 발견을 공급자 운영 인증으로 승격하지 않는다.

## 확인한 공개 코드와 버전

아래 줄 번호는 GitHub 소스의1부터 시작하는 실제 줄 기준이다. 조회 도구의0부터 시작하는 표시와 구분했다. Microsoft `main`은 조회 당시 공개 내용이며 commit 고정판을 확보하지 못했다. 원제작 stactools는 v0.2.1 태그가 가리키는 commit까지 확인했다.

| 근거 | 확인한 내용 | 검증 범위와 한계 |
|---|---|---|
| [Microsoft requirements.txt, L1](https://github.com/microsoft/planetary-computer-tasks/blob/main/datasets/sentinel-2/requirements.txt#L1) | 짧은 원문: `stactools_sentinel2==0.2.1` | 공개 의존성 선언. 실제 배포 이미지·과거 ingest 작업 증명은 아님 |
| [Microsoft Dockerfile, L67–68](https://github.com/microsoft/planetary-computer-tasks/blob/main/datasets/sentinel-2/Dockerfile#L67-L68) | 해당 requirements를 복사·설치하는 레시피 | 공개 빌드 연결만 확인. 운영 이미지 digest 미확보 |
| [Microsoft sentinel2.py, L48–134](https://github.com/microsoft/planetary-computer-tasks/blob/main/datasets/sentinel-2/sentinel2.py#L48-L134) | SAFE의 product/granule metadata를 확인하고 L79–84에서 stac.create_item 호출. 이후 asset·extension 등을 조정 | 이 함수에 datetime 재지정 없음. 함수 밖 ingest 후처리·backfill 여부 미확보 |
| [stactools v0.2.1 릴리스](https://github.com/stactools-packages/sentinel2/releases/tag/v0.2.1), [commit](https://github.com/stactools-packages/sentinel2/commit/d8200c120491eeffbf5772dbf8b444b0c958ca1f) | 고정 commit `d8200c120491eeffbf5772dbf8b444b0c958ca1f` | 아래 두 코드는 이 commit으로 직접 다시 열어 확인 |
| [고정 stac.py, L49–61](https://github.com/stactools-packages/sentinel2/blob/d8200c120491eeffbf5772dbf8b444b0c958ca1f/src/stactools/sentinel2/stac.py#L49-L61) | SAFE→ProductMetadata/GranuleMetadata. 짧은 원문: `datetime=product_metadata.datetime` | Item의 시각 입력값 경로 확인. JSON 직렬화의 원문 자릿수 보존까지 증명하지 않음 |
| [고정 product_metadata.py, L45 및 L96–138](https://github.com/stactools-packages/sentinel2/blob/d8200c120491eeffbf5772dbf8b444b0c958ca1f/src/stactools/sentinel2/product_metadata.py#L96-L138) | General_Info/Product_Info의 PRODUCT_START_TIME을 읽어 str_to_datetime에 전달. ID는 PRODUCT_URI에서 .SAFE와 baseline 부분을 제거하여 별도로 생성 | 원필드 경로 확인. 이름의 시각과 datetime의 동일 초 검사·반올림·잘라내기는 이 코드에 없음 |

확인한 공개 연결은 다음과 같다.

```text
Microsoft 공개 SAFE 작업
  → 공개 requirements의 stactools_sentinel2 0.2.1
  → SAFE product metadata
  → General_Info/Product_Info/PRODUCT_START_TIME
  → str_to_datetime
  → pystac.Item.datetime

별도 ID 경로:
  PRODUCT_URI → .SAFE / N-baseline 제거 → Item.id
```

이 경로에서 granule XML의 tile sensing 필드를 datetime으로 선택한다고 말할 수 없다. 고정 create_item은 product_metadata.datetime을 사용한다. 또한 원래 XML 문자열을 datetime 객체로 파싱하는 단계가 있으므로 `.024Z`와 `.024000Z` 같은 직렬화 표기까지 원본 그대로라고 주장하지 않는다. 공급자가 실제 반환한 STAC 문자열과 그 bytes SHA를 별도로 보존해야 하는 이유다.

## 같은 calendar-second는 보장되는가

**이번 근거로는 보장되지 않는다.** 코드의 두 독립 입력을 같은 의미라고 묶는 검사나 공급자의 보편 계약을 확보하지 못했다. 반대로 실제 PC의 특정 자료에서 서로 다른 초가 발생했다고 검증한 것도 아니다. 소수초 존재와 서로 다른 초의 발생은 별개의 명제다.

[Copernicus SentiWiki의 Products / Compact Naming](https://sentiwiki.copernicus.eu/web/s2-products)은 이름의 첫 날짜를 짧게 “datatake start sensing time”이라고 정의한다. 같은 페이지는 연속 취득 datatake와 이를 구성하는 datastrip·tile을 구별한다. 따라서 특정 tile/pixel의 실제 취득시각을 datatake 이름으로 자동 대체할 근거가 되지 않는다. 두 번째 날짜도 별도의 product discriminator이며 앞 시각보다 이를 수 있어, 물리적 제작 완료 순서라는 해석을 추가하지 않는다.

일반 STAC의 [Common Metadata / Date and Time](https://github.com/radiantearth/stac-spec/blob/master/commons/common-metadata.md#date-and-time)은 RFC3339 표현과 nominal capture datetime을 설명한다. 이는 날짜 문법의 근거이며, PC 제품 원필드와 이름의 동일 초를 정의하는 공급자 계약은 아니다.

원제작 저장소의 [현재 SAFE 구현](https://github.com/stactools-packages/sentinel2/blob/main/src/stactools/sentinel2/stac.py#L568-L586)과 [tileinfo 구현](https://github.com/stactools-packages/sentinel2/blob/main/src/stactools/sentinel2/tileinfo_metadata.py#L14-L36)은 입력 형식에 따라 metadata 경로가 달라질 수 있음을 보여 준다. 후자의 timestamp를 Microsoft SAFE 경로에 소급 적용하지 않는다. 최신 main이나 다른 입력 분기의 의미를0.2.1·역사 카탈로그 ID와 혼용할 수 없다.

## 공개 예제가 보여 주는 범위

STAC Sentinel-2 extension 원제작 저장소의 [예제 item.json, L699–710](https://github.com/stac-extensions/sentinel-2/blob/main/examples/item.json#L699-L710)에는 다음 문자열이 함께 있다.

```text
id acquisition component: 20231107T144731
properties.datetime: 2023-11-07T14:47:31.024000Z
```

이것은 공개 예제에서도0이 아닌 소수초가 사용된다는 독립적인 문서 근거다. PC endpoint를 조회한 결과가 아니며 현재 운영 전체나 프로젝트249 자료의 생성 경로를 인증하지 않는다. 예제에 적힌 asset/self URL도 따라 요청하지 않았다. 예제 URL 안에는 다른 시각 문자열도 있으나 폴더 이름만 보고 tile의 물리 취득시각이나 차이 초를 확정하지 않는다. 예제는 mutable main이며 고정 운영 관측물로 취급하지 않는다.

289가 인용한 프로젝트 저장 근거의 `.024000Z`를 지우거나 반올림해 옛 gate를 통과시키는 방식은 여전히 허용되지 않는다. 공개 예제 한 건에서 이름과 같은 초였다는 사실도 모든 PC item의 같은 초를 보장하지 않는다.

## 289 후속 계약에 대한 판단

| 항목 | 이번 조사 후 판정 |
|---|---|
| 공개 producer의 원필드 | 위0.2.1 SAFE 경로에서는 PRODUCT_START_TIME 확인 |
| PC 현 운영 배포·과거 ingest 버전 | 미확보 / BLOCKED |
| 프로젝트 저장 item의 원제품 XML과 원응답 직접 결속 | 이번 단위에서 검증하지 않음 |
| ID 명목시각과 observed_raw_datetime 별도 보존 | 필요성이 강화됨. 새 구현 승인과는 별개 |
| 같은 UTC calendar-second를 v2 공통 허용 조건으로 채택 | 공급자 근거가 부족하므로 아직 미확정 |
| 기존226/246 v1/default·260 정책 | 변경0. 어느 경로도 이번 문서로 gate 해제되지 않음 |
| v2 schema/marker·실행 연결 | PLANNED, 제품 구현·예약·runner 연결0 |
| 나지 확보·실품질·독립정답·학습 승인 | 모두 이번 조사 성과에 포함되지 않음 |

## 다음에 필요한 최소 증거

1. 해당 PC ingest의 공개 배포 commit 또는 container digest·실제 의존성 판본과 후처리/재처리 여부를 공급자 근거로 연결한다. 공개 Dockerfile만으로 충족하지 않는다.
2. 별도 승인된 범위에서 동일 item의 원문 STAC, 제품 XML PRODUCT_START_TIME/PRODUCT_URI, 관련 granule metadata를 각각 고정하고 같은 제품이라는 결속을 검증한다. 경로·SHA·출처·관측 시점을 보존한다. 이번 작업에서는 이 원격·운영 자료 취득을 수행하지 않았다.
3. 이 실자료의 관계와 공급자가 보장하는 일반 규칙을 분리한다. 반올림인지 절삭인지 추정하거나 고정 허용 초 차이를 발명하지 않는다. tile sensing 시간 비교가 필요하면 그 필드의 공식 정의부터 확인한다.
4. 근거가 마련된 뒤에만289의 명시 v2 정책·오염/누락/provider/시각 경계 시험 및 후속 독립 검토를 설계한다. 기존 v1 호환이나 SURVEY 예산 집행 보호를 자동 승계하지 않는다.

## 수행과 인계

공개 공식 문서·Microsoft 및 원제작 저장소 소스만 웹에서 읽었다. PC catalog/data/COG HTTP0, 운영 source/ledger/model 읽기·복사0, 배열·native·전체 QA0, collector/SURVEY 실행0, 제품 코드·기존289 문서 수정0이다. 문서 조사이므로 합성 시험과 실서비스/UI 검증도 실행하지 않았다.

Root에 이 문서와 지문을 전달한다. 이해자료에는 공개 생성 경로 확인과 운영 동일성 BLOCKED를 함께 설명해야 한다. UI/API 행위가 바뀌지 않아 화면 연결 작업은 필요하지 않다.304/307 성과·종료 여부는 이 문서에서 새로 관측하거나 판정하지 않는다.
