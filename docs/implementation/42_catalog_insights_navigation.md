# 카탈로그 활용 인사이트와 안전한 화면 복귀

상태: VERIFIED_REAL(라이브 Registry 기반 UI·탐색 동작), 어댑터의 경계·경합 시험은 TESTED_SYNTHETIC. 과학 성과·모델 준비도·이용 권한 승인을 뜻하지 않는다.

## 참조와 메뉴 결정

`UI/catalogu_insite/`의 PNG 5개를 모두 직접 열어 확인했다. 파일명 끝 `25-1`, `27-2`, `28-3`, `32-4`, `33-5`이며 모두 1448×1086이다. 전역 7개 메뉴는 유지하고 데이터 카탈로그 아래에 데이터 검색과 다음 5개 세부 목적을 배치했다. 원래 Dashboard/Data Catalog와 6모델 Workspace의 레이아웃은 보존한다. 카탈로그 하단의 기존 활용 인사이트 5버튼이 이제 실제 목적별 화면으로 연결된다.

| 화면 | 직접 URL hash | 구현한 검토·이동 |
|---|---|---|
| 모델 입력자료 | `#/catalog/insights/inputs` | 실제 등록 자료 목록, 공개 6주 지도, 6모델 입력 검토표 |
| 다운로드 이용조건 | `#/catalog/insights/terms` | 접근 분류·라이선스·제공기관 기록, 이용조건 체크리스트, 원본값 표 |
| 메타데이터·품질 | `#/catalog/insights/metadata` | 명시 선택 자료의 8메타 카드·고정 버전/해시·품질 근거, 기존 읽기 계보 진단 |
| Toolbox 전환 | `#/catalog/insights/toolbox` | 카탈로그 체크선택 자료, 호환성 미검증 안내, 실제 6모델 선택·Workspace 열기 |
| WebGIS 공간연계 | `#/catalog/insights/webgis` | 공개 경계 탐색, 선택 자료 공간 메타 기록, 기존 WebGIS 이동 |

전체 PNG를 배경 UI로 사용하지 않는다. 실제 DOM/SVG·표·선택 제어·MapLibre 지도를 구성했다. 공유 sidebar의 기존 작은 브랜드/해안 사진 자산만 재사용한다. PNG의 128/108/20건, 품질 82점, 99.2% 공간 일치율, 준비 완료 비율을 실제 값으로 복제하지 않는다. 6건의 레거시 등록은 고정 버전과 SHA 조합·ACL·기관·기간·품질 근거가 부족하므로 호환성·권한·과학 승인으로 승격하지 않는다. `SEE_COLLECTION_TERMS`는 약관 검토 지시이며 공개 다운로드 허가가 아니다.

## 이동·복귀 계약

- `catalogNavigation.ts`는 허용된 5개 slug와 기존 step 0..25, 모델/탭 allowlist만 해석한다. 알 수 없는 URL은 `replaceState`로 카탈로그에 정규화한다. hash 방식이므로 직접 URL·새로고침에 별도 웹서버 rewrite가 필요 없다.
- 선택 상세는 `?dataset=<명시 ID>`로 기록한다. Dataset 객체를 저장하지 않고 매 렌더 최신 Registry rows에서 다시 조회한다. 아직 응답이 없으면 대기, 오류면 미확인, 성공한 최신 목록에 ID가 없으면 선택 query를 replace로 제거한다. 원본을 생성·등록하거나 ID를 추정하지 않는다.
- 카탈로그 검색 초안·적용 필터·선택 ID는 `sessionStorage`의 `greenblue.catalog.navigation.v1`에 보관한다. JSON·필드 타입·길이·중복을 제한하고 저장소 예외를 처리한다. 저장이 차단되면 현재 화면 동작을 유지하되 페이지 간 저장은 보장되지 않는다. 선택 ID는 최신 성공 rows와 교집합으로 정리한다. Registry 오류 때 오래된 객체를 현재 자료로 표시하지 않는다.
- 앱 내부 이동은 `greenblue.navigation.v1` 표식과 유한한 0 이상 정수 depth를 기록한다. 앱의 이전 버튼은 검증된 내부 depth가 있는 경우에만 `history.back()`을 쓰며, 직접 진입/오염된 표식이면 카탈로그로 replace한다. `history.length`로 외부 페이지 이동을 승인하지 않는다. 브라우저 뒤로/앞으로는 popstate/hashchange에서 URL을 다시 해석한다.
- 내부 이동·브라우저 이동은 이전 전역 결과/오류/busy 표시를 초기화한다. 전역 action은 요청 세대와 시작 URL이 모두 일치할 때만 응답·오류·지도 결과를 반영한다. 서버 작업을 취소하거나 저장 결과를 삭제하는 동작이 아니다. Registry 재조회도 refresh 세대가 일치한 응답만 반영하여 이전 조회가 최신 자료를 덮어쓰지 않는다.
- Toolbox 모델과 지도 참조지역은 별도 `greenblue.catalog.insights.v1` key에 저장한다. 모델 6개와 공개 참조지역 6개 ID만 허용하고 이벤트 시 즉시 저장한다. 따라서 Climate 선택 → Workspace → 브라우저 뒤로에서도 Climate/지역을 복구한다. 기존 카탈로그 필터 저장이 이 key를 덮어쓰지 않는다. 저장 차단 시 같은 앱 실행 동안은 허용목록 검증을 거친 메모리 fallback으로 복귀를 지원하며 차단 환경의 새로고침 간 보존은 보장하지 않는다.
- 인사이트 진입 context는 명시 상세 ID를 우선하고, 없으면 정확히 1개인 실제 체크선택만 전달한다. 무선택·다중선택에서 임의 첫 자료를 추정하지 않는다. 상세의 전용 메타데이터·품질 CTA와 기존 원본 메타데이터 링크를 함께 보존한다.
- 각 인사이트에 이전 화면·카탈로그 복귀·다음 단계·기존 관리 도구 링크를 둔다. 선택 데이터 없이도 화면은 열리지만 개별 품질·조건 판정은 하지 않는다. Workspace 이동은 모델 선택 화면을 여는 기능이며 데이터 자동 주입이나 Job 실행이 아니다.

## 검증과 제한

`node --experimental-strip-types --test frontend/src/*.test.mjs`: 49 PASS / 0 FAIL / 0 SKIP, 477.5108ms. 새 경로·storage·응답 시험 11개는 5 URL 왕복, 오염 URL/모델/탭, 상세 복귀, 잘못된 저장값, 실제 최신 자료 필터·선택 복구, 저장소 차단, 잘못된 history 표식, 지연 성공·오류 무효화, 명시 상세/단일 선택 context 전달, Climate Workspace 왕복 모델·지역 복구와 독립 필터 저장, 모델·지역 오염값·차단 저장소 복귀를 검증한다. 기존 CSV·진단 어댑터도 포함한다.

증거: `evidence/integration/catalog-insights-navigation-tests-20261017.log`, `evidence/integration/catalog-insights-navigation-build-20261017.log`. 최종 production build: TypeScript + Vite PASS, 69 modules, 18.53s. JS 1,515.80kB / gzip 426.86kB, CSS 167.45kB / gzip 30.78kB이며 기존과 같은 500kB chunk 경고가 있다. root가 별도 QA 탭에서 최종 브라우저 검증을 완료했으며 상세 근거는 다음 절에 기록한다. 라이브 UI는 5174에서 동일 출처 프록시로 API 8002를 사용한다. backend·원본 데이터·승인 gate는 수정하지 않았다. 기저지도는 인터넷 연결이 필요하며 경계는 2017 공개 ADM1 참조/ODbL 1.0이고 공식 사업 경계나 Dataset footprint가 아니다.

관련 파일: `CatalogInsights.tsx`, `catalog-insights.css`, `catalogNavigation.ts/test.mjs`, `DataCatalogReference.tsx`, `App.tsx`, `PlatformShell.tsx`. API/계약 변경 없음. 이해자료·연속개발 원장·인계서는 root가 독립 이해 담당과 통합한다.


## 실제 브라우저 검증 — root 독립 QA

근거는 `evidence/integration/catalog-insights-browser-20261017.json`이다. UI 5174 → 동일 출처 프록시 → API 8002의 실제 등록자료를 사용했다. root가 소스 담당과 분리된 QA 탭에서 다음 동작을 확인했다.

- 실제 검색 6건 → baseline 조건 1건 → 체크선택 1건 → 상세 ID hash를 확인했다. 브라우저 뒤로는 필터·선택을 유지한 목록, 앞으로는 같은 상세로 복귀하고 새로고침에서도 상세를 복구했다. 인사이트의 앱 이전 버튼도 기존 상세로 복귀했다.
- 목적별 인사이트 5개 화면, 상세의 메타데이터·품질 CTA, 정확히 1개인 체크선택의 데이터 ID context를 확인했다.
- Toolbox에서 Climate 선택 → Workspace의 `model=climate` URL → 브라우저 뒤로의 Climate 선택 복구 → 앞으로·새로고침 → 다시 뒤로를 확인했다. 공개 참조지역 Gorontalo 선택도 보존됐다.
- 기존 WebGIS 화면과 인사이트의 왕복을 확인했다. 별도 최초 진입의 앱 이전 버튼은 외부 페이지로 가지 않고 카탈로그로 fallback했다. 없는 Dataset query는 replace로 제거됐고 잘못된 route도 카탈로그로 정규화됐다.
- 모바일 별도 탭 390×845에서 메타데이터·WebGIS 화면의 문서 폭 375px을 확인했다. QA 2개 탭의 콘솔 오류는 0건이었다.

스크린샷은 `evidence/integration/`의 `catalog-insight-inputs-desktop.png`, `catalog-insight-terms-desktop.png`, `catalog-insight-metadata-desktop.png`, `catalog-insight-toolbox-desktop.png`, `catalog-insight-webgis-desktop.png`, `catalog-insight-missing-dataset.png`, `catalog-insight-metadata-mobile.png`, `catalog-insight-webgis-mobile.png`이다. 위 결과는 읽기 UI와 복귀 동작의 검증이며 입력자료의 과학적 품질·모델 호환성·다운로드 승인 검증이 아니다. 이 절 반영 후 소스 수정·재빌드는 하지 않았다.
