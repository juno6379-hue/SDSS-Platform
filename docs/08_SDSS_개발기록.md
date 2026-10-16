# SDSS WebGIS 개발 기록

## 1. 범위와 원칙

2026-10-15~16에 초기 프런트엔드를 구현했다. `frontend/`의 React·TypeScript·Vite 앱이 FastAPI `/api`를 호출한다. MapLibre는 OpenStreetMap 기저지도와 실제 입력 AOI를 표시한다. 모든 등록 건수·작업 결과·모델 지표는 서버 응답에서 가져오며 데모 지표나 임의 분석 결과를 만들지 않는다.

초기 프로젝트에 기존 프런트엔드나 디자인 시스템이 없어 NUSANTARA 워크스페이스를 만들었다. 좌측 단계 내비게이션, 관측 조건, 지도, 작업 이력, 원본 응답을 한글로 제공한다. 화면에는 초록 계열의 기후·토지 시스템 테마를 적용했고 750px 이하에서는 가로 내비게이션과 한 열 레이아웃으로 전환한다.

## 2. 개발 순서

1. **실제 API 경계 구성**: `src/api.ts`에 기본 주소, JSON 요청, HTTP 오류, 일반 텍스트 보고서 처리와 선택적 Bearer 인증을 구현했다. 기본 주소는 `http://localhost:8000/api`이며 `.env`의 `VITE_API_BASE`로 바꾼다.
2. **기본 화면과 운영 상태**: health/dashboard/datasets/models/jobs/tools/analyses를 병렬 조회한다. 실패한 자원은 오류를 표시하고 실패를 0건으로 바꾸지 않는다. 새로고침으로 현재 카탈로그를 다시 읽는다.
3. **AOI 지도와 데이터 수집**: 경위도 bbox의 유한성, 범위, 서<동·남<북을 검사한다. 지도에서 AOI를 맞추고 실제 위성 카탈로그 검색·다운로드 API를 연결했다. 자카르타 bbox와 날짜는 사용자가 바꾸는 입력 예시다.
4. **LCLUC 처리 흐름**: 데이터 준비 → 모델 학습 → 배포 모델 추론 → 두 시점 변화 분석에 편집 가능한 JSON 요청과 서버 작업 ID 폴링을 연결했다.
5. **모델 검토와 의사결정**: 독립 참조자료 평가 요청, 근거를 포함한 상태 전이, 배포, 분석 보고서, 제한된 자연어 질의를 연결했다. 평가가 독립성을 자동 인증한다고 표현하지 않는다.
6. **연차별 수집과 시계열**: Planetary Computer를 기본 STAC endpoint로 지정하고 Earth Search 선택지를 추가했다. 2020~2025 기간 선택과 `/timeseries` 입력을 추가했다. 후속 사용자 지시에 따라 첫 번째 그룹의 6개 주 × 6년 = **36개 연차 셀**을 우선 범위로 갱신했다. 화면에서 수집 계획을 다운로드 완료로 표시하지 않는다.

## 3. 화면별 계약

| 화면 | 실제 API | 사용자 입력/출력 |
|---|---|---|
| 현황 대시보드 | GET health, dashboard, datasets, models, analyses | 실제 목록 건수·서버 상태와 원본 현황 |
| 위성 데이터 | POST data/search | bbox, 날짜, endpoint, collection, 운량, limit |
| 영상 다운로드 | POST data/download | URL, filename, max_bytes; 비동기 작업 상태 |
| WorldCover | POST data/worldcover/plan | bbox; 계획 응답을 실제 수집과 구분 |
| Dynamic World | POST data/dynamic-world/export | bbox, 날짜; 인증·도구 오류 그대로 표시 |
| 학습 데이터셋 | POST datasets/prepare | scenes의 image_path/label_path/group/label_source, bands, scale, offset |
| 모델 학습 | POST training | dataset_path, model_id, epochs, batch_size, lr, seed, device |
| 공간 추론 | POST inference | 배포 model_id, image_path, output_id |
| 두 시점 변화 | POST change | t1_path, t2_path, output_id, num_classes |
| 연차 시계열 | POST timeseries | model_id, images[{year,image_path,source,license,date}], output_id |
| 독립평가 | POST models/{id}/evaluate | image_path, label_path, reference_kind, label_provenance, reviewer, group |
| 검토와 배포 | POST models/{id}/transition, deploy | Validated/Approved/Draft/Retired, reason |
| 의사결정 | POST query, GET analyses/{id}/report | question, 선택 analysis_id; 실제 증거와 텍스트 보고서 |

서버 저장 파일의 경로는 서버 데이터 루트 안의 실제 경로여야 한다. 브라우저의 로컬 파일 입력만으로 서버에 영상이 업로드되지는 않는다. 대용량 래스터 업로드·COG 직접 렌더링은 현재 화면에 구현하지 않았다.

## 4. 비동기 작업과 실패 표시

실행 요청이 반환한 `id`를 `/jobs/{id}`로 2.5초마다 조회한다. succeeded/completed/failed/cancelled면 조회를 중단하며 화면 해제 시 타이머를 정리한다. 작업 결과·오류는 접힌 상세 패널에서 확인한다. 서버 요청 오류와 지도 기저지도 오류는 각각 별도로 표시한다. 세션 작업 목록은 현재 브라우저 앱 실행 중 기록이며 영구 작업 기록은 서버의 GET jobs가 관리한다.

서버 결과에 `geojson` 또는 `change_geojson` 객체가 존재하면 지도에 표시할 수 있다. 현재 분석 서버가 래스터·CSV만 반환한 경우 임의 폴리곤을 생성하지 않는다. 지도는 AOI를 보여주고 실제 산출물 경로·전이 면적·시계열 값은 서버 응답 패널에서 확인한다.

모델 독립평가의 `expert_independent` 값은 사용자의 자료 출처·검토자 진술이다. 서버는 학습 장면 그룹과 파일 해시 중복을 확인한다. 화면은 이 제한을 고지한다. 평가·Validated·Approved·배포는 서버의 상태 검증을 통과해야 하며 프런트엔드가 우회하지 않는다.

## 5. 실행

```powershell
cd 'E:\GeoAI–MLOps–SDSS\frontend'
npm.cmd install
Copy-Item .env.example .env
npm.cmd run dev
# 배포용 정적 파일
npm.cmd run build
```

개발 서버는 기본 `127.0.0.1:5173`에 바인딩한다. API 기본 CORS는 localhost/127.0.0.1의 5173을 허용한다. 공유 API가 토큰을 요구하면 화면 하단 서버 연결 설정에서 입력한다. 토큰은 `sessionStorage`에 현재 탭 세션 동안 보관하며 새 탭·영구 저장소에 저장하지 않는다. 원본 응답 패널에는 토큰을 출력하지 않는다.

## 6. 검증 기록과 범위

- 첫 `npm install`은 제한된 네트워크에서 registry.npmjs.org DNS ENOTFOUND로 실패했다. 정상 승인 경로의 설치를 다시 요청했으며 최초 서브에이전트 승인 호출은 장시간 대기 후 중단되었다. 이 실패를 설치 완료로 보고하지 않았다.
- 정상 승인 설치가 완료되어 npm 10.9.3/Node 22.18.0 환경에서 95개 패키지가 설치되었다. `npm.cmd run build`의 `tsc -b`와 Vite 6.4.4 정적 빌드가 성공했다. 최소 3개 지역 그룹 예시를 반영한 초기 빌드는 **20.86초, 34 모듈, 종료 코드 0**이었다. 후속 첫 번째 그룹 변경의 최종 빌드 수치는 아래 8절에 기록한다. 출력은 `frontend/dist/`다. 지도 라이브러리 포함 번들의 500kB 초과 경고가 발생했으며 초기 로딩 최적화는 후속 과제다.
- 브라우저에서 지도 타일·실제 데이터 흐름의 종단 검증은 별도로 기록해야 한다. 정적 빌드 성공을 실자료 모델 성능 또는 정책 운영 승인으로 표현하지 않는다.
- 대시보드 GET·빈 상태·오류·JSON 입력은 실제 API 계약을 기준으로 구현했다. 핵심 필드와 상태 명칭은 백엔드 담당자와 확인했다.
- 지도 기저지도·Google Fonts는 외부 네트워크에 의존한다. 글꼴 로드 실패 시 시스템 sans-serif가 사용된다. 지도 타일 실패는 사용자에게 표시된다.
- 확장 AI 모델군은 구현되지 않았다. 실제 지원 도구와 interface-only 상태는 서버 tools 응답을 조회한다.
- 사용자에게 표시하는 한글 설명, 핵심 비동기 처리·지도·인증 경계의 한글 코드 주석을 작성했다.

## 7. 후속 구현 대상

실제 래스터 지도 레이어, 로그인·권한 관리, 대용량 업로드, 전문가 라벨 작성 도구, 대시보드 차트와 시계열 비교, RDTR 정책 레이어, MLflow·PostGIS 통합은 별도 검증과 개발이 필요하다. 현재 화면은 API의 실제 데이터와 작업을 조작하는 초기 실증 UI다.

## 8. 첫 번째 프로젝트 그룹 범위 변경

2026-10-16 사용자 지시에 따라 우선 수집 범위를 South Sulawesi, Gorontalo, Southeast Sulawesi, Banten, West Java, East Java의 6개 주로 갱신했다. 비교 연차는 2020~2025년으로 총 36개 주·연도 조합이다. 이 숫자는 목표 범위이며 다운로드 완료 건수 또는 실제 확보 장면 수가 아니다.

프로젝트 범위 선택은 검색 AOI 후보를 설정하는 기능이다. 데이터 담당자가 `configs/first-group.collection.json`에 공개 ADM1 참조자료 기반 내부점과 작은 검색 bbox를 생성했으며 프런트엔드도 동일한 6개 bbox를 사용한다. 주를 고르고 후보 bbox 적용 버튼을 누르면 실제 검색 입력과 지도 `fitBounds`가 함께 갱신된다. 주 이름을 선택한 것만으로 해당 주 전체의 영상을 수집했다거나 주 경계를 적용했다는 의미가 아니다. 검색 전 bbox와 지도 범위를 확인하며 동일 계절·동일 밴드 조건을 유지한다.

경계 상태는 **공개 ADM1 참조자료 확보·사업 경계 미확정**으로 표시한다. 경계 참조자료는 geoBoundaries의 인도네시아 ADM1, 2017년 기준, 원 출처 OpenStreetMap·Wambacher, 실제 라이선스 ODbL 1.0이다. 전체 주의 `province_bbox`와 내부의 작은 표본 검색 `bbox`를 구분한다.

`frontend/public/first-group-provinces.geojson`은 데이터 담당자가 검증한 6개 주의 실제 GeoJSON을 복사한 정적 자산이다. 원본 URL·라이선스·선택 파일 해시는 인접한 `first-group-provinces.source.json`에 기록했다. `FirstGroupScope`는 이 파일을 fetch하고 `province_id`로 실제 feature를 고른다. JS 번들 안에 경계 좌표를 인라인으로 넣지 않는다.

주 적용 시 지도는 실제 `province_bbox` 전체를 보여주고 공개 경계는 진한 실선, 소규모 검색 bbox는 점선으로 구분한다. API 검색에는 작은 후보 bbox를 보낸다. 관측 조건의 ‘지도에서 영역 확인’ 또는 검색 실행 시에는 작은 bbox로 확대한다. 경계 폴리곤이나 완료 통계를 임의 생성하지 않는다. `src/provinces.ts`는 수집 설정의 id·bbox·province_bbox 스냅샷이므로 수집 설정 변경 시 함께 갱신한다.

36개 셀의 일괄 수집을 실행하는 가상의 API나 완료 지표는 추가하지 않았다. 선택 후 기존 실제 `/data/search`와 `/data/download` 흐름을 사용한다. 전체 주 폴리곤 기반 수집의 진행 상태·완료 여부는 서버 및 수집 파이프라인의 실제 기록으로 확인한다.

최종 `npm.cmd run build`는 **TypeScript 통과·35 모듈·16.12초·종료 코드 0**이다. 정적 출력은 HTML 0.42kB, CSS 77.99kB(gzip 12.32kB), JS 1,309.73kB(gzip 365.57kB)이며 지도 라이브러리 번들 크기 경고만 남았다. 복사한 GeoJSON의 SHA-256을 실제 파일에서 확인했고 원본 선택 자료와 동일한 `de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909`였다. 브라우저 상호작용·지도 타일 검증은 정적 빌드와 구분한다.

## 9. 수집 재고·최근 실패·학습 준비 표시

후속 사용자 지시에 따라 `src/CollectionStatus.tsx`를 추가했다. 실제 `GET /api/data/collection-status`만 읽고 대시보드에는 요약, 위성 데이터 화면에는 36개 주·연도 셀의 상세 표를 표시한다. 이 패널의 버튼은 상태 조회만 수행하며 새 수집을 시작하지 않는다. 일반 새로고침과 별도로 현황 조회 버튼을 제공한다.

API는 성공 재고와 최근 시도를 따로 반환한다. 프런트엔드는 2021년에 이미 보관된 3밴드 영상·라벨을 이후 수집의 HTTP 429 실패로 덮어쓰지 않는다. 같은 행에 ‘영상 있음·라벨 있음·B02/B03/B04’와 ‘최근 시도 실패·HTTP 429’를 함께 표시한다. 2020 또는 2022년 이후 자료가 없으면 없음·미확인·참조 계획을 그대로 표시한다. `quality_eligible`의 true/false/null은 각각 기준 충족/기준 미충족/미검증으로 구분한다.

B04 전체 단일 밴드 파일은 크기·픽셀 규격·CRS·실제 파일 존재 여부를 따로 표시한다. 이 파일을 다중 밴드 학습 장면 수로 합산하지 않는다. 예약 예산과 실제 수신량이 다르다는 서버 설명도 표시한다. API 조회가 실패하면 기존 응답을 지워 과거 수치와 ‘미확인’ 메시지를 동시에 보이는 혼동을 피한다.

모델 레지스트리에는 서버의 `independent_evaluation:false` 모델을 ‘독립평가 미완료·실험 모델’로 표시하고 참조 유형을 함께 보여준다. API의 선택적 `training_readiness`가 있으면 입력 해시 일치/변경/미확인, train/val/test 패치 수, 평가 종류, blocker를 표시한다. 약한 라벨 실험 준비 충족을 운영 승인이나 과학적 정확도 검증으로 표현하지 않는다.

실제 Chrome의 localhost 화면을 Computer Use 스킬로 읽기 전용 검증했다. Vite의 이전 transform이 남아 새 패널이 보이지 않아 서버 담당자가 5173을 재시작한 뒤 다시 검증했다. 대시보드에서 목표 36셀·영상 6셀·라벨 6셀·품질 충족 3셀·학습 준비 미충족을 확인했다. 최근 실행은 완료 창 0, HTTP 429 제한 27, 예산 제한 8, 장면 없음 1이었다. 위성 데이터 표에서 기존 2021 재고와 이후 실패가 구분되고, 모델 화면에서 `baseline2021_cpu_v1_model`의 Draft·실험 상태가 표시됨을 확인했다. 이 숫자는 검증 시점의 실제 응답이며 고정 예시 데이터가 아니다.

외부 영상 검색·수집·다운로드·모델 전이·재학습 버튼은 검증 중 누르지 않았다. 수집 담당자가 신규 완성 pair 0건이라고 확인해 동일 자료에 대한 정합 감사를 반복하지 않았다. 기존 감사 결과는 아래 감사 문서의 범위와 한계를 따른다.

후속 복구 실행은 셀 작업을 시작하기 전 카탈로그 점검에서 종료될 수 있다. `rate_limit_active`, `server_http_status`, `error_category`를 선택적으로 표시해 셀별 HTTP 429 건수가 0인 요청 제한 중단과 DNS 연결 실패를 구분한다. `stopped_rate_limit`은 ‘요청 제한으로 중단’으로 표시한다. 원격 서버의 429와 로컬 DNS 오류를 같은 원인으로 합치지 않는다. 이 선택 필드는 API의 최종 재시작 뒤 실제 응답으로 확인하며, 필드가 없으면 값을 만들어 표시하지 않는다.

API 재시작 뒤 `training_readiness.blockers`가 `{code,detail,scene}` 객체 배열임을 실제 브라우저에서 확인했다. 초기 string 배열 가정으로 발생한 React 렌더 오류를 수정해 문자열·구조화 객체를 정규화하고 고유 key를 부여했다. 학습 차단 조건 29건은 펼쳐서 읽을 수 있게 표시한다. 수정 후 실제 화면에서 train/val/test 적격 패치 각 0과 RGB 재고 품질 충족 3셀을 별도로 확인했다. 전자는 필수 6밴드 학습 계약 기준이며 후자는 기존 RGB 표본 품질 통계이므로 합산하지 않는다.

다음 실제 조회에서는 복구 실행의 `dns_resolution`과 완료 창 0·셀별 HTTP 429 0을 확인했다. DNS 연결 오류는 제공처 429 제한 경고와 분리한다. 이전 2021 성공 재고는 영상·라벨 각 6셀로 유지되었다. API 응답의 필수 밴드·최소 패치·평가 종류·입력 해시 검증 필드는 선택적으로 표시하고 미응답 값을 지어내지 않는다.

이 후속 UI의 최종 빌드는 `npm.cmd run build` **종료 코드 0, 36모듈, 24.09초**다. CSS 79.41kB(gzip 12.66kB), JS 1,319.46kB(gzip 368.53kB)이며 기존 지도 라이브러리 번들 크기 경고만 남았다. 브라우저에서 학습 차단·실험 모델·수집 상태를 읽기 전용으로 검증했고 신규 학습·배포·수집을 UI로 실행하지 않았다.

이후 Banten/2021·West Java/2021의 한정 복구 수집 2쌍이 실제 완료되어 상태 조회를 다시 확인했다. 기존 6개 주·2021년 셀 수는 유지되면서 두 행의 밴드가 B02/B03/B04/B08/B11/B12의 **6밴드**, 라벨·품질 마스크 보관 있음, 최근 시도 표본 저장으로 갱신되었다. 최근 실행 완료 창은 2, HTTP 429 셀은 0이었다. 기존 실패한 36셀 실행 기록과 복구 실행 기록을 섞지 않았다.

West Java의 99.9634%가 소수 한 자리 반올림으로 100.0%가 되는 오해를 줄이기 위해 유효 비율 표시를 소수 둘째 자리까지 조정했다. 독립 정합 감사는 새 보고서만 읽어 `data/audits/recovery32-alignment.json`에 저장했으며 두 쌍 모두 원본 WorldCover·SCL 재현 픽셀 불일치 0이었다. 상세 근거는 12번 감사 문서 10절을 따른다.

복구 자료 표시까지 반영한 최종 빌드도 **TypeScript 통과·36모듈·24.63초·종료 코드 0**이다. CSS 79.41kB(gzip 12.66kB), JS 1,319.53kB(gzip 368.55kB)로 출력되었고 지도 라이브러리 크기 경고만 남았다.

## MLOps·지도·보고서 실제 연계 후속

모델 검토를 서버 readiness 계약에 연결하고 완료 실험 경로 등록→Draft, 독립 평가 입력, 승인·배포 차단 근거, 실제 per-class 성과 표시를 구현했다. 저장된 분석은 map-data의 실제 GeoJSON·bbox로 지도에 표시하고 인증을 유지하는 보고서 다운로드와 산출물 링크를 제공한다. 패치 검증 재고·split·클래스 비율은 수집 후보 목표와 분리했다. 제품별 반사도 정규화 근거 입력 계약을 안내한다. 상세 개발 순서와 격리 통합 시험·실제 브라우저 증거는 [18번 연계 검증](18_MLOps_SDSS_연계검증.md)에 기록했다.

운영 Draft의 체크포인트 해시 일치와 독립 평가 차단을 최신 8000/5173에서 확인했다. 별도 합성 8001/5174에서는 실제 지도 도형·면적·보고서 다운로드를 검증한 뒤 서버가 정리되었다. 합성 수치와 mock 평가 응답은 운영 모델 성과가 아니다. 최종 빌드는 **38모듈·16.73초·종료 코드 0**이며 TypeScript가 통과했다.
