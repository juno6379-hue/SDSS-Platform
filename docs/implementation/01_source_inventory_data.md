# G0 데이터 수집·원본 증거 조사

소유: data_pipeline. 조사일2026-10-16. 새마스터의전체본문을읽고§3/G0/G1에관계된실제코드·원본·보고서만조사했다. 공통inventory는root가이분할문서를연결한다. 수집session89858/원장/원본/수집코드는변경하지않았다.

## 근거 우선순위와 실제발견

| 근거 | 실제경로/확인 | 취급 |
|---|---|---|
| 새개발지시 | `GreenBlue_CODEX_Master_Prompt_GMAIS_Integrated_Platform_v1.0.md` | 내부개발지시이며기술제안·계약상확정규격과구분 |
| 제출TECH-4 | `tmp/proposal/Part4 - Technical Approach, Methodology, and Workplan (Tech-4).pdf` 및동명추출txt | §2.2.5~2.2.8원본/표준화/QC/metadata·lineage,§2.4.1 AI-ready취지를실제텍스트로확인 |
| TECH-5 | `tmp/proposal/Part5 - Work Plan and Schedule (Tech-5).pdf` | 실물존재;사업일정계약승인으로단정하지않음 |
| GMAIS v0.2 | 기준본: `GreenBlue_GMAIS_v0.2/GreenBlue_GMAIS_v0.2_실행형_표준패키지/`; 공유용 복사본: `contracts/upstream/GMAIS-v0.2/` | 사용자가 지정한 워크스페이스 내 실행형 패키지를 기준본으로 확인했다. package_manifest 기준 34개 파일의 SHA-256이 기준본과 공유용 복사본 모두에서 일치한다. 상태는 내부 제안/not consortium approved. 실제 dataset schema/cross-reference profile/README 열람 |
| 서명계약/승인기관데이터/API | 이번데이터영역조사에서검증자료없음 | SOURCE_MISSING/NOT_CONFIGURED,기관endpoint추측안함 |
| Git | E:작업경로에`.git`없음;`git status`가not a git repository | 브랜치/커밋근거SOURCE_MISSING |

초기읽기전용evidence는E:canonical경로에서GMAIS를못찾아`SOURCE_MISSING`으로기록했다. 이후사용자가 알려준 워크스페이스 내 기준본 `GreenBlue_GMAIS_v0.2/GreenBlue_GMAIS_v0.2_실행형_표준패키지/`를 확인했다. 공유용 경로 `contracts/upstream/GMAIS-v0.2/`와 기준본 양쪽의 manifest 34개 SHA-256이 전부 일치한다. 초기G:실물발견evidence와초기증거는보존하고최신교정증거 `evidence/integration/data-g0-g1-20261016T062213202711Z.json`을추가했다. v0.2의실제schema_version0.2.0/required/enum/추가속성제약을읽었으며schema를추측해생성하지않았다.

## 현재구현과데이터경로

| 구성 | 실구현 | 실제기능/한계 |
|---|---|---|
| STAC/자산 | `backend/app/data/service.py` | EarthSearch/PC선택,AOI/날짜/구름/limit검증,응답구름재검증,GeoTIFF자산,HTTPS정확host허용/Range검증/SHA/수동GeoTIFF등록 |
| 제한·실패원장 | `budget.py`, `parallel.py`, `scripts/collect_training_parallel.py` | 2worker,전체2초간격,thread-local메타계측,첫429공유중단,중앙예약/정산. 예약≠실수신. 과거원장SHA고정 |
| 실제정합 | `scripts/collect_samples.py`, `collect_training_grid.py` | B02/03/04/08/11/12;20mSWIR→10m bilinear;범주/SCL nearest;원본crop/STAC/XML보존;1024→비중복256;SCL/NoData/주polygon/라벨QA |
| 보정근거 | `backend/app/data/calibration.py` | 실제제품XML의quant/offset·제품ID검증. PB<04해석근거와PB04이후명시offset구분. 영상은DN,학습변환과별도 |
| 연차약한참조 | `references.py`,WCplan/EEadapter | WC2020/2021만동년;Esri v0032020~25동년;DW9확률mean export계약은있으나`ee`미설치/실행미검증. 다른기관API없음 |
| 현재카탈로그 | `backend/app/store.py`, `data/catalog.sqlite3` | generic JSON SQLite. 원자버전불변DatasetRegistry/GMAISschema준수·전면LineageQuery가이미완성됐다고볼수없음 |
| 기존데이터API | `backend/app/main.py` | `/api/data/search`,download/register/worldcover/plan,dynamic-world/export,collection-status;`/api/datasets`/prepare. 새Agent endpoint와혼동금지 |

COG/GeoTIFF만실제FileImport가구현되어있다. GeoJSON/GPKG/NetCDF/GRIB/CSV/Parquet범용import,OGC/기관/현장자료공통Connector는아직없다. 함수형서비스는동작하지만`discover/search/validate_access/fetch_or_import/inspect/register/get_status`플러그공통인터페이스로추상화된것은아니다.

## 고정된실제스냅샷

증거: `evidence/integration/data-g0-g1-20261016.json`,수집manifest/원장각읽기SHA포함. **2026-10-16 06:18:19 UTC**기준848물리패치/676보고서상적격/172비적격,31/36주-연도셀,split train365/val151/test160이었다. 이는진행중snapshot이며최종충분성검사나독립정확도승인이아니다. 마스터의과거2패치/107시험스냅샷으로현재를덮어쓰지않는다.

- 원장pending batch2개,공유execution lock존재,429=false. 이두지표만으로프로세스건강/완료를확정하지않는다. 실제session89858상태는root가관리한다.
- 신규예약/계측차감상한1,230,033,660B(이중pending예약136,314,880B),신규한도4,294,967,296B,이전계상2,161,836,459B,종합상한6,456,803,755B. 이를실수신네트워크바이트로표시하지않는다.
- 과거연차실패/32MiB보충원장2개의실제SHA가pinnedSHA와일치했다. 예산내부합계도일치했다.
- 적격목록첫2패치의image/label/quality총6파일SHA를실제재계산해manifest와일치했다. 전848개를새로전수검증했다는뜻이아니다. 독립정합감사는기존별도artifact를연결한다.
- catalogue읽기전용SQL집계: datasets6/models1/analyses3. 등록개수는학습적격/모델승인을뜻하지않는다.
- Python3.11.9; numpy/rasterio/pyproj/shapely발견,ee없음. GPU·Kubernetes·기관접근준비는이조사로검증하지않았다.

재현명령: `python scripts/audit_data_g0_g1.py`. HTTP0,원장/수집파일쓰기0,SQLite`mode=ro`. 다시실행하면기존증거를덮지않고시각을붙인새artifact를저장한다. 이번은조사명령실행성공이지전체회귀시험을재실행한것이아니다. 최근데이터시험55PASS는이전구현시점근거이며신규G0Baseline전체시험은root결과를따른다.

## G0/G1 판정

G0데이터현황조사와GMAIS실물열람/정적대조는완료했다. G1은현재로컬RasterPipeline구현만부분충족하며플러그Connector,표준Registry,ISO프로파일,기관권한,공통lineage계약/마이그레이션이남았다. 현재legacy patch row는v0.2필수필드가누락되고추가속성이많아그대로schema에통과하지않는다. jsonschema실행기는하위환경에없어formal검증성공으로표시하지않았다. root의계약시험/스키마freeze/RFC결정을기다리며collector는바꾸지않았다. dataset readiness/scientific validation/deployment approval/integration contract compliance를합쳐READY라고표시하지않는다.
