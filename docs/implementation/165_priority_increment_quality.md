# 165 — 고정 launch 수집 증분의 읽기 전용 native 품질 감사

상태: **VERIFIED_REAL — 6차 완료 증분24패치의72래스터 검사** / **TESTED_SYNTHETIC — 임시 GeoTIFF 및 실패 경계10시험**. 전체 원본 재QA·학습 승인·독립 정확도 검증은 아니다.

## 구현과 읽기 계약

신규 `scripts/audit_priority_increment165.py`는 `audit_increment(data_root, launch_path, boundary_path)`와 명시 CLI를 제공한다. 필수 입력은 기존 data root, 이미 발행된 수집 launch JSON, 기존 주 경계 GeoJSON이다. launch의 selected_jobs만 감사한다. collector, Store, 원장 객체를 만들거나 HTTP에 접근하지 않는다. source·ledger·예약·lock·모델·원본 파일을 쓰지 않는다. stdout JSON은 호출자가 새 evidence 파일에 보존한다.

입력 metadata를 한도 안에서 복사하고 중복 JSON 키/비유한 수를 거부한다. aggregate128MiB, ledger16MiB, launch1MiB, 경계16MiB, terminal/config/report16MiB; 각 image64MiB/label2MiB/quality2MiB를 제한한다. 상대 또는 data root 안의 절대 로컬 파일만 허용하며 HTTP/경로 탈출/링크·junction을 거부한다. 검사 전후 파일 identity/크기/mtime 및 최종 SHA 재검사를 한다. 이는 OS sandbox·완전한 TOCTOU 방지·GDAL RSS/시간 격리 보장은 아니다.

launch의 이전 행 prefix를 기존 `json.dumps(sort_keys=True)` 규칙 SHA와 비교하고 pending 원장 행은 모든 필드 원형을 대조한다. 선택 batch가 모두 settled가 아니면 **INCOMPLETE**, 완료라도 worker/report/state/config가 없으면 **INCOMPLETE**이며 파일 생성을 기다리거나 수집을 재개하지 않는다. 다른 후속 batch 실행 lock의 존재만으로 선택된 완료6차를 실행 중이라고 표현하지 않는다.

저장 config.json SHA는 launch·ledger와 결합한다. `collect_samples.load_config`가 years를 periods로 변환한 실행 사본의 SHA는 window-state와 **별도로** 결합한다. 이를 위해 신규 감사 함수는 해당 JSON 변환만 순수 사본에서 재현하며 collector/service를 호출하지 않는다. 두 범위의 SHA를 같다고 가정하지 않는다. worker charged는 ledger·COG·metadata·window-state 기록과 검산한다.

## native 검사와 결과

선택 batch의 patch_id별 image/label/quality 원bytes를 SHA와 먼저 결합하고 같은 복사 bytes를 MemoryFile GTiff로 연다. 256×256 영상6밴드와 label/quality1밴드 uint8, 동일 CRS·transform·크기를 검사한다. 실제 image 유한/nonzero, label!=0, 이진 support mask, 요청 주 경계 내부를 교차 검산한다. 경계의 실제 SHA/경로도 각 patch의 source_window 핀과 결합한다. 유효 비율80%·주 내부95%를 기존 materialize 규칙과 동일하게 재계산하고 저장 quality_status·비율·클래스 histogram과 대조한다. label의 support 밖0도 확인한다.

**품질 범위:** 개별 patch의 `quality_eligible`는80%/95% 판정이다. split 집계 최대 단일 클래스90%는 `balanced_coverage`/ML readiness의 별도 클래스 균형 기준이다. 본 도구는 개별 patch의 최대 클래스 비율을 관측 정보로 추가하되,90%를 넘는 순림 패치 등을 새 비적격으로 변경하거나 제거하지 않는다. 나지 기여/비율 및 누출 gate도 이 감사만으로 해소되지 않는다.

결과는 `COMPLETED_NATIVE_CHECKED`, `COMPLETED_WITH_SOURCE_FAILURES`, `COMPLETED_ZERO_PATCHES`, `INCOMPLETE`, `INTEGRITY_BLOCKED`를 구분한다. worker error·report scene별 status/실패 수·자료 결과를 따로 기록한다. settled와0패치는 자료 확보 성공이 아니다. CLI exit0은 native 완료, exit2는 미완료/무결성 차단, exit3은 완료됐으나0패치 또는 source 실패가 있는 관측이다. 항상 learning_ready/scientific_accuracy_validated false, source_or_ledger_writes0이다.

## 실제 6차 관측

관측 시작 `2026-10-18T02:11:32.140495+00:00`, 소요 **17.1528011초**. 고정 launch SHA `de8e975c63f29bffffef23da11a9e68eac5eeab61475dc05bb1fcc73523ca7be`, aggregate SHA `0f04a075a599f4ff74f111652c070c33c817ce668ffba2b7fde1df000731d2cf`, ledger SHA `07be5cce634f896feb6b1c1868382c4ff9a590c1c541cfb59ee1a1fc465a4153`다.

| 6차 선택 batch | 실제 patch | 80/95 적격 | 적격 나지 픽셀 | worker/scene 실패 |
|---|---:|---:|---:|---:|
| east_java 2024 g01 |16|16|0|0/0|
| east_java 2024 g02 |8|7|0|0/0|
| 합계 |24|23|0|0/0|

image/label/quality **72파일**과 config/worker/state/report **8파일**, 총 **80개 SHA 재검사**가 일치했다. 이전1512행 canonical과 기존 pending2행 전액 **136,314,880B**를 보존했다. 당시 총 **1536물리/1235적격**, 전체1200 부족0, 주×연도 셀 바닥28 부족 **73**이다. 전체 적격 수는 저장 metadata 범위이며 전체1536개의 native 재검사가 아니다.

신규24개 중3개는 개별 클래스 최대 비중이90%를 넘지만 모두 원래80/95 적격이다(0.9964447021484375,0.928802490234375,0.9747089460784314). 이것을 split 집계90% 실패로 단정하거나3개를 자동 제외하지 않는다. 고정6차 추가 나지는0이어서 나지 보완 성과로 표시하지 않는다. 원본 metadata scene 교차분할1건도 남았다. 약한 Esri 참조라벨은 독립 현장 정답이 아니다.

최초 실제 프로세스 조사 때6차 PID8688/30492는 없었고 stdout 두 worker 종료·ledger settled2·lock 없음이었다. native 감사 시작 때는 후속 수집 lock이 있었으며 선택6차 settled와 구분한다. 감사 동안 aggregate/ledger SHA 변화는 false였다. 향후7차 이상은 이 보고서의 native 범위가 아니다.

근거: `priority165-round6-native-final-20261018.json`/`.log`, `priority165-live-processes-20261018.json`. CLI는 명시 data/launch/boundary 경로만 사용해 실행했으며 수집/HTTP/Store/학습은0이다.

## 시험·초기 근거와 한계

집중 최종 **10 PASS/0 SKIP/17.607초**, `priority165-focused-final2-20261018.log`. 실제 임시 GeoTIFF native 통과·입력파일 전후 SHA 동일, pending/missing terminal의 native 접근0, 이전 행/예약/config 핀·ratio bool·SHA/grid/histogram·NaN·255 mask·0패치/scene failure/worker failure 구분·검사 후 파일 변조·HTTP 경로 거부·JSON 중복/크기·두 config SHA 범위의 순수 변환을 검사했다. 의도적 파일 변조는 임시 fixture에만 수행했다.

최초9 PASS17.284초와 경계 보강 뒤9 PASS18.195초는 각각 initial/final 로그로 보존한다. 첫 실제 감사는 감사 코드가 저장 config SHA와 실행 periods 사본 SHA를 같다고 가정해 CONFIG_PIN_MISMATCH로 native 전 차단됐다. 이는 collector/데이터 결함이 아니었다. 초기 JSON/log를 `priority165-round6-native-initial-20261018.*`로 원바이트 복사·SHA 확인해 보존한 뒤, 두 SHA 범위를 분리하고 신규 회귀를 추가해 최종 실제 감사가 통과했다. 초기 `priority165-round6-native-20261018.*`도 덮지 않았다.

metadata/파일은 순차 관측이고 원자 snapshot이 아니다. SHA 확인은 읽은 바이트 범위이며 기관 권위·취득 진실·대표성·과학 정확도를 인증하지 않는다. native 원천 source crops 전체 재유도·전체기존 raster 재검사·공간 누출 완전 제거·모델 학습/배포 승인은 범위 밖이다. chunk 상한은 TIFF parser 자원 격리가 아니다.

## UI/API와 인계

신규 명시 CLI 감사이며 기존 API/UI/QA 규칙에 연결하지 않았다. 새 화면이나 endpoint가 불필요하고, 현재 CollectionProgress는 저장 manifest 상태를 표시하는 별도 계약이다. 개별 patch80/95와 split90% 범위 문구 명확화는 Root 승인 후속168로 분리하며 이번165가 기존 UI 소스를 바꾸지 않는다. Root에 구현·시험·실제 증거와 한계를 전달해 공통 인계/이해자료 갱신을 맡긴다. 본 역할은 공통 문서나 이해자료를 직접 편집하지 않는다.

## 최종 오염 입력 방어와 재검증

Root 최종 읽기 검토 후 `worker.error`가 존재하면 exact dict여야 한다는 선검사를 추가했다. string/null/bool/list/int 오염은 native 접근 전에 고정 `INTEGRITY_BLOCKED` / `WORKER_ERROR_SHAPE`가 되며 포괄 AttributeError catch로 다른 결함을 숨기지 않는다. 실제6차에는 error 자체가 없어 이전 성공 관측에 영향이 없었다. 신규 회귀를 포함한 최종 **11 PASS/0 SKIP/12.092초**, `priority165-focused-final3-20261018.log`다. 앞선10건·실제 final 근거는 원바이트 그대로 보존한다.

최종 제품에서 같은6차24패치를 다시 읽어 **24/23적격/추가나지0/80파일 재검사**를 **14.8720509초**에 확인했다. 최종 시작 시각 `2026-10-18T02:18:25.653825+00:00`, 근거 `priority165-round6-native-final2-20261018.json`/`.log`. 이전1512행과 pending2 전액136,314,880B는 계속 일치한다. 이때 후속7차가 정산돼 전체 metadata는 **1568물리/1259적격/셀부족54**로 바뀌었고 lock은 없었다. aggregate SHA `c92a7f73bcbfc461d94750afa3985626f889e729a86e1d72f703e1030e8827ec`, ledger SHA `b9aed796ed11e7c00e62c6ee3078d2d043b72156da0c2b32e254c42bdf727ebb`이며 감사 중 변화false다. **7차 추가 자료는 이6차 native 검사의 범위가 아니다.** 전체 metadata의 시점 변화와 고정6차 native 결과를 분리한다. 최종 소스/시험/문서 SHA는 `priority165-freeze-final-20261018.json`을 따른다.

## 7차 후속 — 동결 도구의 실제 재사용

같은 최종 소스/시험 SHA(추가 코드 수정0)로7차 고정 launch를 명시 조회했다. `priority165-round7-native-20261018.json`/`.log`에서 **32패치·24적격·추가 나지0**, **96래스터+8 terminal/config=104파일 SHA 재검사**가 **13.2535582초**에 통과했다. 시작 관측은 `2026-10-18T02:20:13.843675+00:00`이다. 남동술라웨시2021g03은16개 중9적격,2023g03은16개 중15적격이다. 두 report의 scene 실패0, worker error0이며 settled를 모든 패치 적격으로 혼동하지 않는다.

이전1536행 canonical과 pending2행 전액136,314,880B가 일치했다. actual stdout 시작2/종료2의 신규패치 수·계상량을 native 결과/선택 원장 행과 대조했고 계상 증분 **36,552,191B**와 일치했다. 종합 근거 `priority165-round7-review-20261018.json`에 launch/stdout/native결과 SHA와 동결 코드 핀을 기록했다. 기존11 PASS는 재사용한 도구의 앞선 시험이며 새 시험 실행 수치로 합산하지 않는다.

해당 시점 전체 metadata는1568물리/1259적격/셀 부족54,1200총량 부족0이다. aggregate SHA `c92a7f73bcbfc461d94750afa3985626f889e729a86e1d72f703e1030e8827ec`, ledger SHA `b9aed796ed11e7c00e62c6ee3078d2d043b72156da0c2b32e254c42bdf727ebb`이며 native 감사 동안 변화false/lock 없음이었다. 6차·7차 각각의 관측 범위를 분리하며 전체1568 native 재QA나 나지 보완·누출 해소·학습 승인을 주장하지 않는다. 원본 declared scene 교차분할1건은 남는다. 수집기 실행/중단·원장/lock/예약 쓰기·HTTP0을 유지했다.

### 선택적 표적 라벨 독립 확인 — 반텐2020

추가 제품 수정 없이 기존157 명시 request의 source label/lineage/boundary **3개 SHA**를 실제 원bytes와 대조하고 동일 파일을 재확인했다. 원본 raw Esri 라벨(EPSG32748,2048²)의 명시 window(col1792,row256,256²)를 MemoryFile로 읽어 반텐 경계 내부 비율 **1.0**, code8 나지 **2,411픽셀**을 확인했다. 원본3파일은 검사 전후 같으며 source lineage의2020 표기를 함께 관측했다. `priority165-round7-target-label-review-20261018.json`/`.log`에 request/3ref SHA·격자·histogram을 보존했다.

이것은 이미 존재하는 약한 연간 참조라벨 창의 확인이다. 동일 위치의 새 광학영상·SCL/구름·원본 수신 가능성·센서 정합·실제 bare 정답·독립 정확도·수집/학습 승인을 확인한 것이 아니다. Root167/170의 실행 guard·원본 중복/예산/429/claim 검사를 대신하지 않으며 collector/Store/HTTP/원장/예약 쓰기0을 유지했다.165 제품/시험은 최종 동결 SHA와 동일하다.
