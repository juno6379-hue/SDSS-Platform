# 174. 6개 주 고정 분할 표적 실행 확장 명세

## 후속175 구현 상태 — A만 완료

아래설계의A(localplan)는 [175](175_six_province_local_target_plan.md)에서구현·집중16/관련77PASS·독립소스검토blocking0으로검증했다.6주고정split/주별경계/AOI/실제미터10m격자와기존반텐계약을검사하지만executionfalse를유지한다. B(liveguard)/C(consumer통합)와실제다른주표적수집은여전히PLANNED/BLOCKED다.촬영UTC연도및최종유효mask기준나지255/256경계는B/C에서명시·검증할권고사항이며A완료로해결했다고표현하지않는다.아래의초기설계상태/인용핀은이력으로보존한다.

**PLANNED — 설계·차단 분석만 완료. 범용 표적 실행은 구현·시험·승인하지 않았다.** 이번 작업은 제품 소스·원장·모델·173 proposal을 수정하지 않고 HTTP·실제 preflight·수집·학습을 호출하지 않았다.170의F2/F3 보강은 다른 담당의 동시 작업이므로 이 문서는 그 구현을 대신하거나 마감됐다고 인증하지 않는다.

근거는 `evidence/integration/bare174-gap-review-20261018.json`이다. 검토한 제품 소스11개 각각의 원바이트SHA·읽은 시점의 정확한 인용 줄·읽기 직후 안정성을 기록했다. 아래 줄 번호는 해당 증거의 source SHA에만 대응하며170 담당의 후속 편집으로 바뀔 수 있다. 구현 착수 전 최신 SHA·diff·줄 번호와F2/F3 시험을 다시 확인해야 한다.

## 1. 결론과 현재 차단

173에서 동년 로컬라벨104개/정렬256창6,404개를 읽어 나지256픽셀 이상·주내95% 후보50개를 발견했다. 그중 train29/test6은 현재157/170의 반텐 전용 경로와 연결되지 않는다. 반텐val15개도 실제 영상/SCL/B02/미정산/지원 inventory/겹침 검사를 통과한 실행계획이 아니다.

현재 반텐 제한은 한 곳이 아니다. province/split·공식 경계·CRS·baseAOI·job내용·key·실시간 selected scene 검사에 중복되어 있다. `banten`을 일괄 문자열 치환하거나 EPSG 제한만 없애면 같은 고정 split과 실제 native AOI를 보장하지 못한다.

| 현재 제약 | 정확한 소스 지점 | 다음 변경 계약 |
|---|---|---|
| 반텐/val만 target 허용 | `backend/app/data/targeted_bare_plan.py:88` | 고정6주 map의 province와 정확히 일치하는 split만 허용 |
| 반텐 경계1개 선택 | `backend/app/data/targeted_bare_plan.py:107` | target province별 경계 정확1개, 누락/중복 거부 |
| label CRS EPSG32748만 허용 | `backend/app/data/targeted_bare_plan.py:147` | 실제 pinned라벨과 native target/선정B02의 정합을 검사하는 10m·미터단위 투영계 계약 |
| 반텐 baseAOI 복사/고정 province_id | `backend/app/data/targeted_bare_plan.py:172`, `:173` | 해당 province baseAOI 정확1개를 복사하고 target bbox·province_id를 일치시킴 |
| job province/split 고정 | `backend/app/data/targeted_bare_plan.py:179` | 검증된 target에서 province/year/split 파생, caller 재배정 금지 |
| batch key에 반텐 literal | `backend/app/data/targeted_bare_plan.py:183` | 검증된 province+year+targetID+검증plan digest로 key 생성 |
| live selected scene에 val/Banten 고정 | `backend/app/data/targeted_live_guards.py:67`, `:68` | 같은 고정map으로 job province/split, target, 선정scene연도/AOI를 재대조 |

모든 target의2020~2025년 범위·int year·동년ESRI 출처·현재 source/ledger SHA·고정6주 map·기존 정확한 스키마는 유지한다. 확장은 새로운 caller-controlled split map이나 느슨한 동년 판단을 허용하는 기능이 아니다.

## 2. 173 후보별 현재 연결 가능성

proposal SHA는 `63368b398ff02382db10213753fb937a7653b925b912c7c5946a857b2152a0ee`, source는1,569행 SHA `6b74cfda9afd8a9ab238406bbf5007e50a2c1162989e2f8953a13a6289f7950c`다. 아래는 **각 주에서173 순위가 가장 앞선 후보**이며 해당 주의 단순 최대밀도 후보와는 다를 수 있다. 현재 source 이후 수집분을 포함하지 않는다.

| 주 / split | proposal index | 연도 / local x,y | 나지 픽셀 | snapshot 셀 부족 | 관측 라벨 CRS | 현재 정적 차단 |
|---|---:|---|---:|---:|---|---|
| 남동술라웨시 / train | 0 | 2021 /1536,1792 | 1,112 | 1 | EPSG32751 | province/split·EPSG gate |
| 동자바 / train | 3 | 2025 /1280,256 | 620 | 1 | EPSG32749 | province/split·EPSG gate |
| 고론탈로 / train | 11 | 2024 /512,1280 | 271 | 3 | EPSG32651 | province/split·EPSG gate |
| 반텐 / val | 13 | 2020 /0,256 | 3,910 | 0 | EPSG32748 | 위 두 literal gate는 호환하나 전체157계획·167/170 검사는 미수행 |
| 남술라웨시 / train | 21 | 2022 /1792,0 | 961 | 0 | EPSG32750 | province/split·EPSG gate |
| 서자바 / test | 24 | 2024 /256,768 | 802 | 0 | EPSG32748 | EPSG는 같지만 province/split gate |

반텐 index13은 이미 수집한 표적 source crop의 주변창에서 발견됐으므로 기존 영상/지원 범위와 겹칠 가능성을 반드시 검사한다. 이 문서는 실제 overlap을 계산하거나 없다고 확정하지 않는다. 나머지 후보도 새 이름·다른 연도·다른 SHA만으로 독립성을 확보한 것으로 보지 않는다.

관측 CRS를 주별 고정표로 만들어 버리면 안 된다. 주가 UTM 경계·적도를 걸치거나 미래 source가 다른 허용 native 격자를 사용할 수 있다. 검증 기준은 pinned source 라벨·공식 boundary 변환·target footprint·실제 선택B02가 같은 미터단위10m 격자로 정합하는가다. projected=true만으로 feet 단위/비정상 EPSG를 수용하지 않는다.

## 3. 변경할 작은 구현 단위와 의존성

### A. 6주 local plan만 확장 — 첫 구현 후보

변경은 `targeted_bare_plan.py`와 해당 집중 시험에 한정한다. canonical map은 남술라웨시/고론탈로/남동술라웨시/동자바=train, 반텐=val, 서자바=test다. 기존 고정정책의 단일 선언을 재사용하고 호출자가 다른 map을 전달할 수 없게 한다.

target 검증 뒤 같은 province의 boundary/baseAOI를 정확1개 선택한다. 여러 province를 한 plan에 담을 때 기존 overlap 루프가 각 target에 대응하는 geometry를 쓰도록 분리한다. 최종 jobs의 geometry/configAOI/province/year/split/selection_context가 target와 일치해야 한다. job key도 province를 포함하되 검증된 plan digest와 exclusive 신규경로·원장중복거부를 유지한다. 기존 반텐 request/필드 스키마를 조용히 바꾸지 않는다.

라벨 검사는 raw source SHA·source_lineage_ref 내 유일한 해당crop·label_year/URL의 동년 선언·uint8 등 허용정수1밴드·정확 native transform·256창안쪽·code8수·95%주내·유한좌표를 그대로 검산한다. EPSG32748 literal만 제거하지 말고 projected 미터단위·북향10/-10·정확 pinnedgrid와 target 모서리·WGS bbox를 함께 확인한다. source crop의 대체GCP/RPC/subdataset 등 다른 georeferencing을 허용할지는 별도 명시하고 기존167의 거부 범위보다 느슨하게 만들지 않는다.

이 단계의 성공도 `LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED`와 execution_supported=false를 유지한다. 기본 collector 실행·HTTP·reserve를 연결하지 않는다.173의 proposal은 plan이 아니므로 caller는 유효한 source_lineage_ref를 별도로 찾아 명시해야 한다.

### B. live guard의 고정map·AOI binding 확장 — A 검증 후

`TargetedLiveGuard.on_scene`에서 target province/fixed_split과 job/configAOI가 같은 canonical map에 맞는지 재검증한다. selected STAC datetime은 timezone·연도2020~2025·job.year와 정확히 일치해야 한다. baseAOI의명칭만 같고bbox/province가 바뀌는 경우를 거부한다. province를 STAC item의 임의메타데이터에서 추정하지 않는다.

on_window는 selected item이 선언한 정확한 B02 URL,256×256/native10m/같은CRS/계획 footprint 대비 기존1픽셀 정렬 한계를 보존한다(`targeted_live_guards.py:98`의 `TARGET_B02_ALIGNMENT_SHORTFALL`). 10m가 미터단위라는 전제가 명확해야 한다. 선정 전 candidate SCL도 spatial exclusion을 받고, selected의 정확한 동년reference label만 큰 coverage 재사용 예외다. 다른 URL을 label로 위장하거나 임의B02 요청으로 witness를 채우지 못하게 한다.

scene claim은 같은 coordinator 객체의 원자 check+claim을 그대로 사용한다(`targeted_live_guards.py:75`, `targeted_scene_claims.py:27`). 같은 source가 다른 split에 존재하거나 다른owner가 먼저 claim하면 reserve 이후라도 이미지 다운로드로 진행하지 않는다. 실패한 claim/window를 자동해제하거나 다른프로세스에 공유된 것으로 표현하지 않는다. 단일 실행lock과167 재검사가 프로세스 경계를 보완해야 하며162의 메모리 객체만으로 영속/분산 exclusion을 주장하지 않는다.

### C. 기존170과 통합 — F2/F3 소유자 마감 후

새 통합 로직을 별도로 중복 작성하지 않는다. 현재170 담당의 실패 후 progress/정산과 물리patch cap 보강이 소스동결·독립시험을 마친 뒤 A/B와 결합한다. F2/F3가 미완이면 실제 실행 확장을 차단한다. 동결된 실제 source SHA와 test log를 받은 후에만 이 문서의 줄 번호를 최신화한다.

처음에는 명시된 한 target의 읽기 전용 preflight부터 확인한다. 이 문서의50개 후보나36개 셀을 자동 실행하는 fan-out은 만들지 않는다. 실제집행은 기존 사용자 범위·명시 requestSHA·최대1~2batch·기존공유예산 안에서 별도로 판단한다.

## 4. 반드시 보존할 운영 계약

| 계약 | 현재 근거 / 통합 요구 |
|---|---|
| 현재 입력 pin |170은 현재 aggregate/ledger를 독립pin 후 localplan과 inventory를 검증.173의과거sourceSHA를 최신상태 승인으로 전용하지 않음 |
| history 포함 | `targeted_inventory.py:90`, `targeted_live_guards.py:104`,170 physicalinventory는 품질부적격·historical_noneligible도 포함. 학습후보에서제외됐다는이유로수집겹침inventory에서빼지 않음 |
| 과거1152지원자산 | `docs/implementation/167_targeted_inventory.md:19`는 과거dryrun 실측수. 고정한도/현재자산수/전체workspace완전성근거가 아님. 새실행마다 전체관리범위와 원장report부모를 다시열거·검산 |
| 미정산 pending | `targeted_inventory.py:112`: 각pending의config SHA와 실제 raw-B02가 필요. bbox예정값으로대체·누락무시·예약환불금지 |
| 지원자산과 공간 |167의 기존sourcewindow·SCL/SWIR/B02·out-of-aggregate report디렉터리·partial파일과 보수적투영overlap거부 유지. 라벨재사용과영상재사용을구분 |
| exclusive출력/alias |166 신규leaf/identity·alias거부 유지. 기존폴더/부분파일을overwrite/delete하지 않음 |
| 원장/예산 | `budget.py:20`, `:74`, `:104`:4GiB 동일원장·reserve→측정settle·pending자동환불0·최초429 영속회로. batch예약COG64MiB+metadata1MiB(`collect_training_grid.py:25–26`) 유지 |
| 3000물리상한 |170의현재`physical_patch_inventory`:등록행·history·targeted_unenrolled·느슨한partial patch디렉터리까지같은관리범위계수. 적격수/원본행수만으로판단금지. max1patch/target·최대2batch·부모identity/pin재검사 유지 |
| 429/2worker |서비스shared circuit+2초spacing, 새제출중단·기존worker정산drain(`parallel.py:10`) 유지. 범용화가새독립원장/스레드풀을만들면안됨 |
| 실패표현 | reserve/전송/정산/게시progress를구분. 예외발생을executed=false/전송0/정산완료로왜곡금지. 중간실패후실행재시도·환불·삭제자동화없음 |
| native품질/나지 | 유효80%·주내95%·동년라벨·class비율0.5%·기여5패치/256픽셀·지배90% 유지. 표적code8≥256을전체모델준비로승격하지않음 |

현황cap 불일치도 별도로 관리한다.157 source manifest read cap64MiB,167 inventory와170 현재aggregate read cap128MiB다.6주 확장이 입력cap을 자동으로128MiB로 높이는 근거는 아니다. 현cap 안에서 먼저 계약을 검증하고, 이후큰aggregate 지원은 bounded parsing/RSS/시험 근거가 있는 별도단위로 설계한다.

## 5. 필수 시험 명세

이 절은 **다음 구현자가 실행할 시험 명세**이며 이번에 통과시킨시험수가 아니다. 합성GTiff/임시원장/Mock STAC로 먼저 검증하고 기본테스트에서 HTTP를 금지한다.

1. 6주×6연도의정상nativefixture,고정split정확일치.서자바를train/반텐을test로바꾸면거부.미등록주·bool/범위밖연도·중복targetID·빈target거부.
2. 주별boundary/baseAOI누락·중복·서로다른주섞임거부.두target서로다른주의geometry가마지막target것으로덮이지않는지확인.반텐기존fixture의job내용/기존batch불변계약회귀.
3. 각주 실제관측CRS fixture와 미터단위다른native허용정책을분리.4326/feet/회전/비유한transform/9m/20m·window밖·wrongCRS/footprint/bbox·라벨SHA/연차URL불일치거부.
4. 실제라벨code8=255거부/256허용,주내.95미만거부.예상픽셀수가있어도라벨변조시거부.같은crop/source_lineage유일성·missing/duplicate lineage거부.
5. live scene datetime timezone/연도·jobprovince/fixedsplit/configAOI/bbox변조거부.같은scene을train/test가동시에claim하면한쪽만허용,기존multi-split history는quarantine,실패후자동release0.
6. B02정확selectedURL·256native10m·원래1픽셀정렬guard.동일owner의여러supportband는정합검사하고다른owner의공간중첩은거부.임의B02·타sceneassets·위조label예외거부.
7. SCL이선정보다먼저읽힐때도현재support/pending공간제약적용.크게확장된동년ESRIlabel만재사용가능하며그예외가SCL/영상에적용되지않음.
8. 미정산2건의config/B02누락·SHA변조·실제지원파일증감·오래된source/ledger핀·symlink/hardlinkalias·out-of-aggregate history overlap이HTTP/reserve전에차단됨을확인.
9. 2999물리+1unenrolled+1newtarget거부.묶음2target의최대생성2를예약전에계상.보고서가1target에서2patch생성을예고하면materialize전차단.품질미달·나지미달파일도물리계수보존.
10. 두번째reserve/submit/finalize오류에도이미실행한worker를각각한번finalize시도하고정산/게시미확정을정확히출력.첫429후대기요청/신규job0·기존worker측정종료·기존pending전액보존.
11. 일반수집기/기본CLI/기존157반텐경로회귀.읽기preflight는HTTP/Store/모델/원장쓰기0.실행옵션없이실제집행금지.
12. 최종새source snapshot→누출제외candidate→nativeQA로cohort SHA·계수·나지차단을검증.새target성공을독립현장정답/승인모델/자동학습으로표현하지않음.

## 6. 다음 Root 인계

A(localplan) → B(liveguard) → C(동결된170통합)로나눠소유자를배정한다.현재170 F2/F3담당파일을동시편집하지않는다.첫A/B는내부로컬함수/집중시험단위로끝내고executionfalse를유지하며,독립검토·관련회귀·원본/원장/예약보존을확인한뒤명시single-target preflight를검토한다.

173 상위후보인남동술라웨시2021/train과서자바2024/test가새split/CRS/sceneclaim회귀fixture로유용하다.실제로집행할후보인지는167/170의현재전체inventory·B02·scene·회계검사가판정한다.반텐index13은기존경로회귀용일뿐겹침없음승인이아니다.

이번 산출물은 이문서와gap-review JSON뿐이며제품소스/원장/HTTP변경0이다.공통문서·이해자료·UI는해당담당이추후검증된구현완료시업데이트한다.범용화구현·실제수집·모델학습은여전히PLANNED/BLOCKED로보고한다.
