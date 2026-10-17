# 62. 실제 연결 진단 1회 실행과 저장 근거 검증

## 확인한 결과

**VERIFIED_REAL — 현재 실행 보고서와 JSON 메타데이터에 한정.** Root가 기존 saved policy를 복사한 새 plan과 고정 manifest로 CLI를 1회 실행했다. non-execute/non-resume이며 새 readiness 파일만 생성했다. 종료0, 70.437초, gate는 계속 blocked/ready=false·blocker5다. current capture는 CAPTURED_COMPONENTS_MATCH다.

현재 진단은 **1384 scene / eligible patches1111**을 구별해서 기록했다. 273개 scene의 eligible_patches가 0이어도 기존 union에 참여했다. 저장 witness 전체는 15019개이며 반환 목록은 10000개라 TRUNCATED_UNION_COMPLETE다. 현재 cross-split token 연결 한 건과 helper/gate component 일치를 확인했다. 기존 차단 해제·기하 독립·정확도·학습/정산/자동재개 승인을 뜻하지 않는다.

## 실행과 입력 고정

- 기존 saved readiness: `data/first-group/readiness-resume-20261017.json`, SHA `6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db`.
- 고정 manifest: `data/first-group-training-esri-v1/annual-window-report.json`, SHA `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`.
- 새 policy: `evidence/integration/readiness-connectivity-real-policy-20261017.json`. saved policy와 typed JSON 전체가 같다. current default와는 label_source=esri_io 명시가 추가된 차이만 있으며 required_provinces 순서·4/1/1 mapping은 adapter 지원 범위와 일치한다.
- 새 보고서: `data/first-group/readiness-connectivity-20261017.json`, **11132483 bytes**, SHA `95f7622ac72ef6a3d43aafc35a3607a4e9f39ed2912ac01280a07cc62c854e35`.

실제 명령의 argv·환경·자원 관측은 `evidence/integration/readiness-connectivity-real-execution-20261017.json`에 있다. --connectivity-diagnostics와 새 --readiness-output/복사한 --plan을 사용했고 --execute/--resume/다운로드를 요청하지 않았다. Root만 실행했다. 구현·문서 담당은 CLI/assess/helper를 다시 실행하지 않고 JSON 보고서만 읽었다.

Root는 기존 assess의 파일 hash·픽셀 QA를 수행했다. adapter의 source_files_read=0·pixel_arrays_read=false는 **추가 진단 처리의 범위**이며 전체 실제 CLI가 파일/픽셀을 전혀 읽지 않았다는 뜻은 아니다. 실제 assess 입력 4335개 참조의 존재/stat 계획 총합은1269465244B였다. timeout600초·관측 RSS 기준2GiB를 모니터했고 135회 표본에서 peak observed tree RSS214724608B, 강제중지는 없었다. 표본 RSS 감시는 hard memory cap 또는 순간 최대 메모리 보증이 아니다. PROJ_NETWORK OFF/PAM NO/READDIR EMPTY_DIR/VRT PYTHON NO를 설정했다.

## 기존 보고서와의 동등성

새 JSON과 과거 saved JSON은 **connectivity_diagnostics 추가 및 assessed_at 시각 차이 이외 모든 기존 key·typed 값이 같다**. verified_files4335개, policy, group_splits, province_groups, coverage, class/reference 통계·input signature·payloadnull도 포함한다. 기존 파일을 덮어쓰거나 과거 내용을 새 진단으로 채우지 않았다.

기존 5개 blocker의 순서와 내용은 그대로다.

1. SHARED_SOURCE_CROSSES_FIXED_SPLIT — west_java.
2. REFERENCE_CLASS_IMBALANCE — train의 class7 pixel ratio/patch representation.
3. REFERENCE_CLASS_IMBALANCE — val의 class7 pixel ratio/patch representation.
4. CLASS_COVERAGE — val/class7:209 pixels.
5. REFERENCE_CLASS_IMBALANCE — test의 class7 pixel ratio/patch representation.

| 고정 split | 현재 appended scene | eligible patches | 0patch scene |
|---|---:|---:|---:|
| train |848|628|220|
| val |272|233|39|
| test |264|250|14|
| 합계 |1384|1111|273|

이 실제 실행에서는 1111개 scene이 각1 patch, 나머지273개 scene이0 patch였다. 일반적으로 patch count와 scene count가 같다는 계약은 아니다. 과거 saved report에는 eligible scene별 witness가 없으므로 1111이라는 patch 합계로 과거 scene 집합·순서를 복원하지 않는다.

## 현재 token 연결 근거

현재 저장된 직접 cross-split 연결은 TOKEN_SHARED_NAMESPACE 한 건이다. source_group의 주별 prefix가 달라도 scene_id는 동일 namespace의 literal 문자열로 비교하는 기존 알고리즘이 유지되었다.

```text
shared scene_id:
S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431

right: scene_index303 / banten / val / token_role=scene_id / eligible_patches1
left:  scene_index1096 / west_java / test / token_role=scene_id / eligible_patches0
component_union_changed=true
```

현재 source_group은 각각 `banten/<동일 scene_id>`, `west_java/<동일 scene_id>`로 다르다. 이번 직접 event는 scene_id 역할끼리 일어났다. 결과 component에서 west_java와 banten의 root는 banten이며 helper province_components와 gate province_groups가 일치한다. fixed conflict event는 west_java, previous val→current test다.

scene_index/eligible_position은 **이번 assess 내부 scenes 순서**다. 원본 manifest row index와 같다고 가정하지 않았다. 같은 product의 다른 장면 회원 여부와 원본 행 binding은 다음 읽기 추적 범위다. 1096 장면의 0patch 참여는 이번 event의 관측 사실이다. 해당 장면 하나 또는 모든0patch 장면을 제거한 뒤의 연결·차단 결과는 시험하지 않았으며 정책/장면 삭제·필터 변경을 승인하지 않는다.

이것은 **현재 실행에서 새로 기록한 event 근거**다. 과거 saved report가 같은5blocker를 가졌다는 이유만으로 과거 생성 시점의 token/bbox 분기·장면 집합·runtime 원인을 인증하지 않는다. 과거 source report의 부재한 scene witness 상태는 계속 UNKNOWN_NOT_PERSISTED다.

## bbox와 truncation의 구분

현재 helper는 957036개 bbox 쌍을 처리하고 2768 token occurrence를 처리했다고 기록했다. 전체 event 수는 token2595+bbox12424=15019다. 반환 prefix10000에는 token2595개 전부와 bbox7405개가 있다. bbox5019개 기록은 저장 목록에서 생략되었다. union 계산은 끝났으며 union_change_count=1이다.

문서 담당의 metadata 검증은 저장 token2595개를 literal token/역할/last-owner scene 참조와 대조했고, 저장 bbox7405개의 양 끝 scene/bounds·strict positive 두축 교차·순서를 확인했다. 예를 들어 gorontalo scene1과0의 bbox는 경도122.22207270858415..122.22207648846185, 위도0.6817419771473051..0.704900916989313에서 AABB 교차를 기록한다. 이는 bbox 메타데이터 교차이며 정확 영상 footprint/픽셀 교차 면적을 검증한 것이 아니다.

**저장 prefix만으로 cross-split bbox가0이라고 추정하지 않았다.** 독립 검토 담당이 현재 새 JSON의 전체 projected metadata로957036쌍·2768token을 별도 graph/BFS 방식으로 확인해 전체 event 수/저장 prefix/최종 components 일치를 검증했다. 그 별도 exhaustive JSON 검토에서 cross-split bbox0·token1을 확인했다. 근거는 `evidence/integration/readiness-connectivity-real-independent-20261017.log`다. 이 관측도 현재 report의 supplied bounds/token 범위이며 현재 영상의 독립 기하·실제 과학적 누출 판정이나 과거 생성 원인 인증은 아니다.

## 검증 산출물과 시험 구분

문서 담당의 `evidence/integration/readiness-connectivity-real-validation-20261017.json`은 **20개 metadata 검증 항목 PASS**다. 이것은 새 unittest20개가 아니다. 새 보고서 caller SHA, old/new 전필드 동등성, policy copy·input manifest hash 참조, success adapter/witness 전체 key schema·typed 승인 flags, scene index/mapping·0patch·counts, limits/좌표 범위, component map, token last-owner 근거, 저장 bbox 참조/교차, 실행 no-training 기록을 확인했다. 처음/끝의 제한된 JSON byte 읽기 및 SHA/stat 안정성을 확인했고 원본 보고서는 수정하지 않았다. 생성 중인 자신의 새 validation artifact만 완성했다.

validation JSON의 독립 검토 절은 별도 graph/BFS 로그의 SHA 및 exhaustive 결과를 인용한다. 문서 담당 자신의 validation_scope는 JSON metadata 검사이며 bbox 전수·union·helper 재계산을 수행했다고 주장하지 않는다. 원본 raster/header/픽셀/hash를 추가로 읽지 않았다.

실제 Root CLI시험은 **1회/종료0/70.437초**다. 이번 단위는 생산코드를 변경하지 않아 전체 회귀를 다시 실행하지 않았다. 직전61단위608건 회귀는 이전 코드 변경의 증거로만 참조하며 이번 실제 실행에서 새로608건을 수행한 것처럼 합산하지 않는다. 독립 JSON graph 검토도 unittest 또는 추가 실제 CLI 실행으로 세지 않는다.

Root 보존 증거 `evidence/integration/readiness-connectivity-real-live-integrity-20261017.json`은132개 보호 참조/24개 코드 계약과 기존 code/data/contract snapshot 무변경·기존 saved SHA 및5blocker 보존을 기록한다. stdout/stderr는 `readiness-connectivity-real-cli-20261017.log` 및 `readiness-connectivity-real-cli-stderr-20261017.log`에 있다. 새 summary는 ASCII이며 기존 main의 stdout UTF8 reconfigure 동작과 구별한다.

## 제한과 다음 내부 단위

- 현재 실제 연결 event 확인이며 과거 생성 원인의 소급 인증은 아니다.
- scene metadata·bbox/토큰 관측이며 정확 footprint·독립 픽셀 중첩·누출 해결·기관 승인 판정은 아니다.
- 전체 gate는 blocked이며 학습·정산·자동재개 승인, 환불 또는 예약 변경을 하지 않았다.
- 생산코드·정책·분할·모델·원장·lock·원본 데이터를 수정하지 않았다. UI/API 변경도 없으므로 UI 적용 작업이 필요 없다.

다음 최소 단위는 현재 event index와 product token을 원본 manifest의 명시적 province/scene_id/source_group 및 기록된 참조 SHA에 연결하는 **읽기 lineage 보고서**다. index를 원본 row 번호로 단정하지 않고 product 전체 회원·중복/모호함을 기록한다. 재assess 없이 수행하며, 원인 행 삭제·필터·gate 우회·임의 정책 변경은 하지 않는다.


## Root 추가 확인: 공유 토큰 전체 회원

[현재 공유 토큰 회원 기록](../../evidence/integration/readiness-connectivity-real-token-membership-20261017.json)은 같은 새 보고서의 literal 공유 namespace를 읽어 해당 토큰의 **28장면**을 확인한다. Banten16장면은 모두1패치(16패치), West Java12장면 중3장면은0패치이고9장면은1패치(9패치)다. 일치 역할은 scene_id이며, 현재 첫 cross event가0패치 장면에서 발생했다는 사실이 충돌이0패치 장면에만 한정된다는 뜻은 아니다. 양쪽 주에 양수 패치 장면도 같은 토큰을 가진다.

이는 현재 보고서 내부의 회원 조회이며 원본 manifest 행 index binding·과거 보고서 회원 복원·장면 삭제 반사실/차단 해소 시험을 수행한 것이 아니다. 다음에는 명시 SHA와 메타데이터 정합으로 원본 manifest 행·동일 제품 전체를 읽기 추적한다. assess 내부 scene_index를 근거 없이 원본 manifest row index로 간주하거나 기존 분할·정책을 바꾸지 않는다.


## 원본 후보 추적 후속

[63 고정 JSON lineage](63_readiness_connectivity_lineage_validation.md)에서 현재 공유 토큰의원본후보28행/보고서28장면과400후보연결을읽기대조했다. 모두모호한후보집합이며원본한행으로확정하지않았다. report에per-scene영상경로/hash식별단서가없는한계를확인했다. 실제assess/영상재읽기·장면삭제·gate변경·기존보고서재기록은없었다.
