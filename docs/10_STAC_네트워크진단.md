# 10. STAC 네트워크 진단 및 로컬 재실행

**최신2worker성공:** 실제South Sulawesi2020/Gorontalo2021동시수집이429없이끝났다. 새32물리패치중적격13개추가로누적112물리/90적격이며7/36셀이다. HTTP본문계상은신규153,106,741B/과거포함2,314,943,200B이고종합상한6,456,803,755B/신규4GiB를유지한다. old실패예약을환불하지않았다. 아직1000개미달이라재학습하지않는다. 다음은기존성공창과겹치지않는laneB24후보를동일2worker/원장으로확대한다. 후보pool4608은계획수이며실제파일생성상한은3000개,실적격은QA후에만집계한다.

**앞선v1완료:** 정상root환경Esri연차실제픽셀수집에서2020년5주1024원본창5개를받아256패치80개(적격77개)를만들었다. South Sulawesi는원본SCL83.7%가v1예비85%에미달해미확보였다. HTTP429없음,신규전역계상113,114,808B/이전포함2,274,951,267B이며과거원장은보존했다. 아직2020년5셀/77개뿐이며1000패치/36셀목표/학습준비미달이다. 다음v2는2worker를공통2초간격·즉시429중단회로로묶고,source65%/최종patch80%를분리한다. v2실행결과는 `data/first-group-training-esri-v1/run-result.json`의policy/worker상태를따르며0네트워크모의시험과실제실행을구분한다.

**앞선4주smoke:** 정상root환경의신규4GiB공통원장/단일process/2초간격실험에서Southeast Sulawesi2021/East Java2021의6밴드·동년WC라벨2쌍을추가확보했다. South Sulawesi/Gorontalo는선정SCL품질부족으로6밴드수집을생략했다(네트워크실패와구분). 현재신규계상16,142,440B는공식출처조사3,675,728B를포함하며총합2,177,978,899B/상한6,456,803,755B다. 기존실패/보충원장SHA는보존했고429없음이다. 증거는 `data/first-group-training-v1/run-result.json`이다. 2021소수창성공은36셀/1000패치달성이아니다.

**이전32MiB보충실험성공:** 정상root환경에서요청2초간격/단일process로 Banten2021/WestJava2021의6밴드영상·동년WC라벨2쌍을확보했다. COG14,090,240 B+JSON/XML262,573 B=신규14,352,813 B(<32MiB), HTTP429없음, 기존원장불변이다. 새자료는2021년2패치이며36셀/1000패치/정식학습완료는아니다。data/first-group-recovery32/run-result.json과annual-window-report.json을보존한다.

새32MiB 보충실험의 최초하위환경probe는 DNS11001/HTTP없음/COG·메타0 B로 실패했다. 동일예산을정상root환경에1회인계한 뒤 STAC루트JSON2,135 B를 수신했다. 이는 서버상태확인 성공이며 새6밴드/라벨 확보와다르다. 기존429실패원장은삭제·환불하지않았다. 상세보충한도/첫429중단/순차요청/원래DNS결과해시보존은 문서15와 data/first-group-recovery32의실행기록을따른다.

**과거3worker 실패기록:** 해당36셀실행은 완성0개/HTTP429 27행/예약예산소진8행/장면없음1행이었다. 그예산차감상한2,147,483,646 B는 실제수신2GiB가아니다. 새보충실험성공이이과거실패를소급해서바꾸지는않는다. 정상데이터셋기준미달로재학습은하지않았다.

재현성 보완: 새출력은STAC JSON/보간전native각밴드/원본SCL/원본WC/품질마스크/XML/해시를보존한다. 기존역사적원본라벨창부재는별도한계다. 보충실험에서최대5후보의SCL85%예비선정과최종80%QA를구현·실행했으며 최종유효비율은Banten99.6033%/WestJava99.9634%였다. 정상데이터셋/독립라벨/충분량미달로재학습승인과구분한다.

First Group 최초6주 실행은5개 주 RGB/WorldCover 창 성공, Gorontalo1개 실패였다. 상위CPL오류 뒤의 실제 원인은 HTTP Range 기대 범위와 Content-Range 응답 범위의 불일치였다. 좌표계/북반구 문제라고 추정하지 않는다. HEAD/GET에 Cache-Control:no-cache 및 Pragma:no-cache를 추가하고 expected/actual/status를 기록해 재시도한다. 범위 검증을 완화하거나 잘못된 바이트를 정상 영상으로 처리하지 않는다. 오류는 HTTPS URL/SAS query를 제거한500자 이내 메시지와 최대5단계 원인 체인을 남긴다. 최신 재시도 결과는 실행 manifest를 따른다.

현재 새 수집 범위는 **First Group 6개 주×2020~2025년36개 셀**이다. 실제 공개 ADM1경계6개는 내려받았고, 새2021년6주 픽셀 창은 `data/first-group-2021/annual-window-report.json`에서 진행/실패/완료를 분리한다. 아래의 기존3지역 시험과18건 거절 기록은 역사적 작업이다. 새6주 작업은 별도 사용자 요청의 정상 승인으로 이어받아 실행하며 이전 거절을 우회한 것으로 취급하지 않는다.

## 최신 확인 상태 (2026-10-16, Asia/Seoul)

| 카탈로그/자료 | 서버 연결 | 실제 STAC 검색 | 실제 영상 바이트 |
|---|---|---|---|
| Earth Search | 샌드박스 DNS 실패; 호스트 재실행 거절 | 미검증 | 미검증 |
| Planetary Computer | 승인된 호스트에서 DNS/HTTP 200 성공 | 인도네시아 실제 장면 검색 성공 | B04 64×64 실제 GeoTIFF 6,479 B, HTTP 본문 458,966 B 성공 |
| PC/ESA 2021 연구 후보 3지역 | 실제 원격 접근 성공 | 지역별 2021년 실제 장면 3개 | 각 256×256 RGB + SCL 마스크 + 정합 WorldCover 라벨 성공; 총 HTTP 본문 8,912,896 B |
| PC 2021 서부 자바 B04 원본 파일 | 실제 SAS/Blob 접근 성공 | 기존 실제 장면 ID 일치 확인 | **단일 밴드 전체 파일 221,758,050 B** 다운로드/SHA256 성공 |

`data/baseline2021/annual-window-report.json`: 3개 RGB 창과 라벨 3개를 확보했다. 유효 픽셀 비율은 서부 자바 후보 95.6299%, 중부 자바 후보 99.6399%, 남부 술라웨시 후보 98.2239%다. 이는 소규모 파이프라인 검증용 원본 해상도 창이며, 1000~3000개 학습 패치/18개 연차 전체장면/물리 반사도 검증 완료를 뜻하지 않는다. 현재 반사도 scale/offset 원문은 기존 수집 프로세스에 보존되지 않아 미검증이며, 이후 검색 코드는 원본 properties와 raster:bands를 보존한다.

2020~2025×3 AOI의 18건 추가 메타데이터 검색 실행은 별도 승인 요청이 거절되어 실행하지 않았다. 기본 계획과 실제 확보 결과를 혼동하지 않는다. 아래 초기 미검증 기록은 그 당시 관찰 이력이며 위 표가 최신 상태다.

원본 전체 B04의 증거는 `data/raw-reference/reference-report.json`이다. SHA256은 `ee3979574239b669bdccc4b571623ddb02be484c0b9c29179fd627a4071a1453`이며, 221,758,050 B 전체를 저장했다. 2021 소규모 창의 HTTP 본문과 합한 집계 230,670,946 B는 2 GiB 제한 안이다. **한 밴드 파일 전체**와 **장면의 모든 밴드 전체**는 다른 완료 기준이며 후자는 완료되지 않았다. 확보한 item 원문에서 서부 자바 장면의 `s2:processing_baseline=03.00` 및 N0300 제품을 확인했다. 해당 자산 `raster:bands`는 없으므로 scale/offset의 명시적 숫자 근거는 여전히 부족하다.

이 파일은 로컬에서 GeoTIFF로 재개방해 EPSG:32748, 10 m, 10980×10980, uint16, 1밴드 및 NoData0을 확인했다. 실제 바이트 전송·로컬 해시·공간 메타데이터 확인은 완료됐지만, 클래스 정답 검증/연차 전체 자료/충분한 패치 수는 별개의 미완료 항목이다.

## 실제 관찰 결과 (2026-10-15)

- 표준 라이브러리 urllib로 Earth Search `https://earth-search.aws.element84.com/v1/search`에 실제 검색을 시도했다. bbox `[106.75, -6.75, 106.80, -6.70]`, 기간 2023-06-01~2023-09-30, 구름량 10% 이하, limit=1을 요청했다.
- 샌드박스에서 `socket.gaierror [Errno 11001] getaddrinfo failed`가 발생했으며 urllib의 URLError를 거쳐 검색 함수가 RuntimeError로 전달했다. 이 결과는 DNS/네트워크 단계 실패다. STAC 서버가 반환한 HTTP 4xx/5xx 응답이 아니므로 검색 JSON이나 컬렉션 ID가 잘못됐다는 결론을 내릴 근거가 없다.
- 지침에 따라 같은 실검색을 `require_escalated`로 요청했으나 실행 도구가 `rejected by user`를 반환했다. 승인 우회 또는 다른 도구를 통한 대체 네트워크 실행은 하지 않았다. 이는 자동 승인 검토의 거절이라고 추정하지 않고 도구가 반환한 사용자 거절로 기록한다.
- 이 초기 Earth Search 시도 시점에는 실제 Sentinel-2 검색/다운로드가 미검증이었다. 이후 PC 실제 검색/픽셀 창과 WorldCover 부분 창을 확보했으므로 최신 상태는 위 표를 따른다. EE 실제 제출은 계속 미실행이다.
- 초기 `test_data_service.py`의 12개 테스트는 외부 네트워크를 mock 처리했다. 최초 테스트는 Windows 샌드박스의 임시파일 rename PermissionError 때문에 실패했다. 동일 테스트를 정상 승인 경로로 재실행하여 12개 모두 통과했고, 설치된 rasterio/numpy로 임시 테스트 GeoTIFF 등록·정렬도 통과했다. 이후 진단 판정 3개 및 불완전 Range 거부 1개를 추가한 최종 수집/진단 테스트는 16개다. 이 임시 테스트 파일은 실 위성자료가 아니다.

## 네트워크 가능 로컬에서 재실행

프로젝트 루트 PowerShell에서 실행한다.

```powershell
# mock 계약 테스트 후 DNS/HTTPS GET/STAC POST를 단계별 기록
.\scripts\test-stac-local.ps1

# 검색 성공 뒤 실제 COG의 작은 64×64 픽셀 창을 추가 확인
.\scripts\test-stac-local.ps1 -Sample -WindowSize 64

# 특정 Python을 지정할 경우
.\scripts\test-stac-local.ps1 -Python 'C:\path\to\python.exe' -Sample

# 네트워크 호출 없이 진단 스크립트/보고서 저장만 확인
.\scripts\test-stac-local.ps1 -Offline
```

일반 진단에는 Python 표준 라이브러리만 필요하다. `-Sample`에는 rasterio/numpy가 필요하며 미설치는 별도 단계 실패로 기록한다. COG 창은 최대 512×512 픽셀로 제한한다. urllib RangeReader는 압축 블록·메타데이터를 포함한 단일 자산의 HTTP 응답 본문 합계를 최대 32 MiB로 제한한다. 전체 자산 다운로드의 바이트 제한은 download_asset에서 적용한다.

## 단계별 판단 기준

| 단계 | 확인 항목 | 실패 시 해석 |
|---|---|---|
| DNS | 카탈로그 호스트 `getaddrinfo` | DNS 정책, 샌드박스, 로컬 네트워크를 점검. API 동작은 미검증 |
| HTTPS GET | `/v1` 루트 JSON 응답 | DNS 성공 후 TLS 인증서, 방화벽, 프록시, 연결 제한 등을 구분 |
| STAC POST | 실제 AOI 검색, 필터, 응답 | HTTP 400이면 요청/서버 계약, 401/403이면 권한, 429이면 제한, 5xx이면 원격 장애 가능성 |
| COG 창 | 실제 GeoTIFF 한 밴드 읽기 및 로컬 SHA256/manifest | 자산 호스트 접근, Range/COG 지원, rasterio 의존성 등을 확인 |

`diagnosis.json`은 카테고리/에러타입/상태코드만 저장하여 자격증명이나 서명 URL query 노출을 피한다. 검색 성공은 0건 응답일 수도 있으므로 `real_search_verified=true`만으로 샘플 확보를 주장하면 안 된다. `real_download_verified=true`와 `cog_window.status=downloaded_window`가 있어야 작은 실제 창 확보로 판정한다. 단일 밴드 64×64 검증 창은 다중밴드 학습 데이터 또는 독립 holdout 검증 세트가 아니다.

## 생성되는 증거

- `data/validation/diagnosis.json`: UTC 실행시각, 단계별 결과, 실제 검색/다운로드 검증 플래그.
- `data/validation/stac-search.json`: 실제 검색 성공 시에만 저장한 STAC 응답과 조건.
- `data/validation/sentinel2-red-window.tif`: 선택적 샘플 읽기가 성공할 때만 저장.
- `data/validation/manifests/*.json`: 샘플 등록의 SHA256, 공간 메타데이터, 출처, 라이선스 선언.

이 보고서의 2026-10-15 관찰과 이후 로컬 재실행 결과를 혼동하지 않는다. 정상화 후 보고서 파일의 실제 상태를 근거로 갱신하고, 동적 결과가 없으면 미검증 표시를 유지한다.

## 충분한 자료 확보로 이어지는 다음 실행

진단이 정상화되면 `python scripts/collect_samples.py`로 연구 후보 3 AOI×T1/T2의 계획을 확인하고, 로컬에서 `--execute`를 명시하여 수집한다. 기본 예산은 전체 2 GiB/자산 256 MiB이며, 이 예산이 최소 6개 다중밴드 장면의 충분한 수집을 보장하지 않는다. 원본이 크면 예산·자산 제한 실패가 정상적으로 보고된다. 더 큰 예산은 사용자가 설정 파일을 수정해야 한다. 예산 우회나 원본 해상도에 근거 없는 패치 수 추정을 수행하지 않는다.

수집 보고서는 전체 장면 원본 밴드 확보, 제한된 픽셀 창 확보, 라벨 후보 확보, 실제 유효 픽셀/클래스/1000~3000 패치 검증 여부를 구분한다. 최신 실제 확보량은 **2021년 RGB 창 3개 / 정합 약지도 라벨 창 3개 / 충분한 학습 패치 미확보**다. 파일 존재·SHA256만으로 학습 준비를 판정하지 않는다. 상세 요건과 재개 방식은 [06 데이터수집 개발기록](06_데이터수집_개발기록.md)을 따른다.

## Planetary Computer 대체 카탈로그 검증 추가

사용자가 별도로 요청한 `https://planetarycomputer.microsoft.com/api/stac/v1`은 샌드박스에서 DNS 11001 실패였으나, 이후 **새로 승인된 호스트 실행에서 DNS 및 HTTP 200/STAC 1.0.0**이 확인되었다. 이 새 승인은 앞선 Earth Search 재실행 거절과 다른 요청이다. 허용을 우회하여 접근한 것으로 기록하지 않는다. 이후 승인된 PC 실제 검색은 다음 장면을 반환했다.

| 항목 | 실제 검색 결과 |
|---|---|
| 영상 ID | S2A_MSIL2A_20230921T025531_R032_T48MXT_20240913T192557 |
| 촬영 일시 | 2023-09-21T02:55:31.024000Z |
| 장면 구름피복률 | 3.829685% |
| GeoTIFF 자산 키 | AOT, B01, B02, B03, B04, B05, B06, B07, B08, B09, B11, B12, B8A, SCL, WVP, visual |

위 자산 키는 카탈로그에서 다운로드 URL을 제공한다는 의미다. 각 자산의 실제 파일 전송 성공을 의미하지 않는다. `data/validation-planetary/stac-search.json` 및 `diagnosis.json`이 원본 증거다. 실제 다운로드 상태는 그 진단의 `real_download_verified`로 확인한다.

```powershell
.\scripts\test-stac-local.ps1 -Endpoint planetary-computer -Sample
python scripts/diagnose_stac.py --endpoint https://planetarycomputer.microsoft.com/api/stac/v1 --sample --output data/validation-planetary
```

STAC endpoint는 Earth Search/PC 두 고정 카탈로그만 허용한다. 일괄 수집 설정의 `endpoint`도 `planetary-computer`로 선택할 수 있다. Sentinel-2의 논리 red/green/blue/nir/swir16/swir22는 PC에서 B04/B03/B02/B08/B11/B12로 매핑한다. PC 공개 자산은 [공식 SAS 문서](https://planetarycomputer.microsoft.com/docs/concepts/sas/)에 따라 `/api/sas/v1/sign?href=...`로 서명하며 반환 호스트/경로가 원본과 일치하는지 확인한다. SAS query는 출처 manifest에 기록하지 않는다. PC STAC 검색 성공과 SAS/Blob 데이터 접근 성공은 별도 단계다.

네트워크 정책 설정이 필요한 경우 관리자는 HTTPS 443에 다음 호스트를 검토하여 허용할 수 있다: `planetarycomputer.microsoft.com`(STAC/SAS), `sentinel2l2a01.blob.core.windows.net`, `sentinel2l2a02.blob.core.windows.net`(Sentinel 자산), `landsateuwest.blob.core.windows.net`(Landsat), `earth-search.aws.element84.com`(기본 카탈로그), `sentinel-cogs.s3.us-west-2.amazonaws.com`/`earthsearch-data.s3.amazonaws.com`(AWS 자산), `esa-worldcover.s3.eu-central-1.amazonaws.com`(라벨 후보). 허용목록 변경은 정책 관리자의 조치이며 코드가 권한 차단을 우회하지 않는다.

PC 원격 COG를 GDAL/libcurl로 읽는 최초 시도는 로컬 UnicodeDecodeError로 실패했다. 동일 승인의 범위에서 표준 urllib 기반 HTTP RangeReader와 rasterio 공식 opener로 수정했다. 이 방식은 원래 HTTPS 검증·고정 호스트·서명 검증을 유지하며 응답 Content-Range/ETag 및 누적 HTTP 본문 32 MiB 상한을 검사한다. 샘플 픽셀 제한 64×64와 원본 전체장면 확보는 구별한다.

원본 한 밴드 파일 전체를 재현하려면 `python scripts/download_reference_asset.py --execute`를 사용한다. 기본 실행은 계획 전용이며 별도 실행 플래그에서만 원격 접근한다. 자산별 최대 256 MiB, 기존 소규모 수집량과 원본 다운로드 디렉터리 누적을 합한 2 GiB 예산을 확인한다. 큰 자산이 제한을 넘으면 정상 실패로 기록한다. 전체 장면의 밴드 전부를 수집하는 기능으로 표시하지 않는다.

## First Group 경계 출처와 실행 구분

공식 geoBoundaries IDN ADM1 API의 실제응답과 simplified GeoJSON(3,397,843 B)을 받아6개 주를 선택했다. 원본은34개 주, 대표연도2017, OpenStreetMap/Wambacher, **ODbL1.0**이다. `data/first-group-boundaries/source-metadata.json`/`boundary-manifest.json`에 실제 라이선스를 보존했다. 주 전체 reference geometry, 전체 주bbox, 내부 대표점, 작은 샘플 검색bbox를 config에 각각 명시했다.

새6개 주 수집은 First Group 요청의 정상 권한 경로로 진행한다. 첫 실행 요청이 오래 대기하여 root가 해당 에이전트를 중단하고 실행을 이어받았다. 이것은 **조정 목적의 중단**이며 `rejected by user`가 반환된 과거18건 검색 요청과 다르다. 실제 상태는 승인/조정/검색/픽셀 전송/동년 라벨 확보를 각각 기록한다. 단순승인 또는 디렉터리 생성만으로6개 주 다운로드가 완료됐다고 보고하지 않는다.

전체36개 셀은 작은 연차 창의 범위다. 256×256 창36개를1000개 패치 확보로 계산하지 않는다. 8×8 확장 공간격자는2304개 명목후보 계획만 있으며 실행기는 아직 미구현이다. 다운로드 예산2 GiB는 기존 원본과 신규 전달량을 차감해 적용한다.6밴드 연차 창 지원은 구현됐지만, 실제 최초2021년6주 실행은 기존 RGB3밴드 설정의 프로토콜 검증이다.

## HTTP429와 예산 상한의 실제 의미

`data/first-group-annual/run-result.json`의 기존자료 차감288,334,563 B와 신규작업 예약을 합한2,147,483,646 B는 예산 상한 기록이다. 자산실패에도 남은 구버전32 MiB예약이 포함되므로 실제수신량을 이 값으로 계산할 수 없다. 해당 old상태를 삭제/환불/성공으로 재분류하지 않았다.

수정된 worker는 최초HTTP429에 즉시 circuit을 열어 후속셀을 deferred_rate_limit로 남긴다. state.last_rate_limit의 request_host/request_path/retry_after를 총괄기에 전달한다. request_path는 query를 포함하지 않는다. provider429를 숨기고 다른 호스트/토큰경로로 재시도하지 않는다. 공식 account/container SAS token을 유효TTL 동안 메모리에 재사용하는 설계로 불필요한 반복서명 요청을 줄이되, 이 변경의 실제공급자 실행은 미검증이다.

새 전송량 계수는 COG Range본문을 실제 Python이 읽은 바이트만 다룬다. 정상caught실패의 측정값은 정확차감하고 현재예약 잔여를 반환한다. 강제중단/정확측정불가 및 old예약은 유지한다. SAS/HEAD실패의 COG본문0은 헤더·TLS·SAS JSON까지 포함한 전체네트워크0이라는 뜻이 아니다. report의 http_body_bytes_measured, http_body_bytes_upper_bound, legacy_charged_bytes_preserved, measurement_scope를 구분한다.

응답 eo:cloud_cover는 요청상한20%와 다시 대조한다. 실제 관찰된20.909931%/20.911454% 조건위반을 이유없이 허용하지 않고 유한숫자/범위/상한 guard와 filtered_count를 추가했다. 조건위반 원격응답의 원인을 단정하지 않는다.35개 data mock 테스트가 통과했으며 추가 네트워크 검증이나 재훈련은 하지 않았다.

## 신규보충실험의확인범위

하위환경DNS0바이트실패는그환경에한정됐고, root에서동일예산을1회인계해STAC루트JSON2,135 B및실픽셀수신에성공했다. 실제새container-token TTL경로도이실행에서작동했다. 이번실행에429가없었다는사실을제공자rate limit이영구해제됐다고해석하지않는다. 첫429중단보호와단일순차요청을유지했고실행완료후추가외부호출을중단했다.

신규실수신14,352,813 B와기존실패원장을합한차감상한2,161,836,459 B는서로다른수치다. 기존미측정예약은그대로있으며실수신총량으로환산하지않는다. 제품XML의PB03.00/quant10000/제품URI일치와공식pre04 no-offset규칙으로scale0.0001/offset0근거를확인했지만 저장영상은아직DN이며실제반사도변환이적용되지않았다. 후속정합/QA/학습계약감사를거치며새정확도실험은하지않는다.
