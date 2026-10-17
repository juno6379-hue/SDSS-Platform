# 58. 향후 적격 scene 메타데이터 연결 근거 helper

## 쉬운 설명과 상태

이 순수 함수는 **caller가 적격이라고 주장한 scene 메타데이터를 향후 명시적으로 공급할 때** 토큰 공유와 bbox 겹침의 연결 근거를 남긴다. 기존 readiness를 실행하거나 적격성을 다시 판정하지 않는다. 과거 저장 readiness에 scene별 근거가 없다는 사실을 채우기 위해 장면을 추측·복원하지 않는다.

구현 및 작은 합성 입력 검증은 `TESTED_SYNTHETIC`이다. `None`을 받으면 `UNKNOWN_NOT_PERSISTED`를 반환한다. 현재 실제 saved report의 eligible scene 부재와 helper(None)의 연결 확인은 Root의 별도 읽기 증거로 기록한다. 모든 결과는 진단용 `BLOCKED`, ready/scientific/실행·정산·자동재개 승인 false, 환불 0, exactly-once UNKNOWN이다.

## 배경과 기존 코드 범위

현재 `backend/app/ml/readiness.py`는 적격 scenes가 구성된 다음 두 종류의 연결을 여섯 주 전체에 union한다.

1. source_group과 scene_id는 **같은 문자열 namespace**를 사용한다. 역할별 prefix를 붙이지 않는다. 각 token 조회 뒤 마지막 주 소유자를 갱신한다. 같은 행의 두 token 값이 같아도 두 번째 no-op 연결 및 마지막 역할 갱신은 존재한다.
2. 모든 `j < i` bbox 쌍에서 두 축의 교차 길이가 모두 엄격히 양수이면 연결한다. 선·점 접촉은 제외하며 within-split 주 사이도 연결한다. 따라서 transitive 연결이 고정 split 충돌을 만들 수 있다.

각 union의 root는 기존과 같이 두 component root의 사전순 작은 주 이름이다. source_group이 빈 문자열이면 그 행의 source_group·scene_id **두 역할 모두** token 처리에서 제외하지만 bbox 단계에는 계속 참여한다. helper는 이 metadata 규칙만 보존한다. readiness의 eligibility, reference/class 검사, 파일/픽셀 검사, gate 또는 fixed split policy를 호출·수정하지 않는다.

## 함수와 입력 계약

```python
diagnose_readiness_connectivity(
    eligible_scenes,
    province_splits=None,
    *,
    max_scenes=2000,
    max_bbox_pairs=1000000,
    max_witness_edges=10000,
)
```

`eligible_scenes=None`이면 scene 근거가 저장되지 않았다는 뜻이다. 이 경우 policy 생략이 가능하다. 명시 리스트 입력에는 caller가 고정 six-province mapping을 제공해야 한다. 이 단위의 지원 범위는 south_sulawesi/gorontalo/southeast_sulawesi/east_java=train, banten=val, west_java=test의 기존 4/1/1 mapping이다. 다른 정책을 임의로 고치거나 기본 정책을 import/call하지 않는다.

각 scene은 다음 필드를 가진 dict이다.

| 필드 | 계약 |
|---|---|
| `scene_index` | caller가 준 유일한 비음수 signed-64-bit int 식별자. bool/float 금지. 원본 manifest index라는 보증은 없다. |
| `province` | 명시적인 기존 여섯 주 이름. 추정·fallback 없음. |
| `source_group` | 최대 4096 code point의 literal str. 빈 문자열 지원. 공백을 제거하거나 문자열을 정규화하지 않음. |
| `scene_id` | 최대 4096 code point의 literal str. 중복 및 빈 문자열 허용. 중복은 token 연결의 대상이다. |
| `bounds_wgs84` | `[xmin,ymin,xmax,ymax]` list. bool 제외 유한 int/float, 경도 -180..180·위도 -90..90, xmin<xmax/ymin<ymax. wrapped·퇴화 bbox는 지원하지 않고 거부. |

입력의 리스트 순서가 token last-owner와 bbox 순서를 결정한다. witness는 caller `scene_index`와 리스트상의 `eligible_position`을 함께 기록한다. 사용하지 않는 추가 dict 필드에서 데이터를 읽거나 eligible 여부를 추정하지 않는다. 입력을 변형하지 않고 사용하는 필드만 복사한다.

모든 scene의 타입·문자열·좌표와 전체 bbox 쌍 수를 **token/union/bbox 진단 전에** 검증한다. 잘못된 입력은 `ValueError`이며 부분 성공 결과를 반환하지 않는다. NaN/Infinity와 `math.isfinite` 변환을 넘는 거대 정수도 안전하게 거부한다. JSON parser는 이 helper의 책임이 아니며 caller는 저장/전송 경계를 별도로 검증해야 한다.

## 한도와 저장 근거

- scene limit: 1..2000, 실제 입력은 빈 리스트도 가능.
- bbox pair limit: 1..2,000,000, 기본 1,000,000. `n*(n-1)//2` 전수 계획이 넘으면 계산을 시작하지 않는다.
- witness edge 저장 limit: 0..10,000, 기본 10,000. 0도 허용한다. bool/float/음수/고정 최대값 초과 금지.

이 단위의 저장은 반환값 메모리 목록에 근거를 유지한다는 뜻이며 파일/DB 영속 저장을 구현하지 않는다. 저장 edge 한도에 도달해도 token last-owner 갱신, 모든 bbox 비교, 전체 union, component/split 충돌 계산은 계속한다. `union_complete`는 지원한 입력에 대해 규정된 계산을 끝냈다는 뜻이다. token 근거 누락이 없다는 뜻이 아니다. `witness_edges_truncated`와 `witness_edge_coverage=TRUNCATED_UNION_COMPLETE`는 전체 계산과 저장 근거 일부 생략을 구분한다. witness를 일부만 저장한 결과에서 edge 배열만으로 전체 연결 경로를 복원할 수 있다고 주장하지 않는다. 이 한도는 프로세스의 hard CPU/time 한도 보증이 아니다.

TOKEN edge는 문자열과 양 끝 scene index/list position/province/token_role, union 변경 여부를 기록한다. BBOX edge는 양 끝 scene 식별자, 각각의 bbox, strict positive overlap bbox 및 union 변경 여부를 기록한다. 같은 scene의 no-op 및 같은 주/같은 split 연결도 생략하지 않는다.

## 출력 계약

공통 key는 입력 부재에서도 유지한다.

- `diagnostic_status`: `UNKNOWN_NOT_PERSISTED` / `NO_SUPPLIED_ELIGIBLE_SCENES` / `SUPPLIED_METADATA_DIAGNOSED`.
- `input_eligibility`: `CALLER_ASSERTED_NOT_VERIFIED`, 또는 None 입력의 `UNKNOWN_NOT_PERSISTED`. `eligibility_verified`는 항상 false.
- `scene_count`, `bbox_pair_plan_count`, `bbox_pairs_evaluated`, `token_occurrences_processed`, `union_change_count`, `union_complete`.
- `witness_edges`, `witness_edge_count_total/stored`, `witness_edge_counts_by_kind`, `witness_edges_truncated`, `witness_edge_coverage`.
- `province_components`, `components`, `fixed_split_conflicts`, `fixed_split_conflict_events`. component 충돌은 여러 고정 split이 연결되었다는 supplied-metadata 진단이다. events는 기존 고정 주 순서에서 마지막 component split을 갱신하는 순서도 보존한다. 고정 split assignments는 변경하지 않는다.
- `input_token_metadata_complete`: 빈 group이 있으면 false. `SOURCE_GROUP_MISSING`에는 양 token 역할 skip 및 bbox 참여 유지가 기록된다.
- `no_cross_split_connectivity_found_in_supplied_metadata`: 공급된 metadata에서 충돌이 있으면 false, 충돌·빈group이 없는 비어있지 않은 입력이면 true, None/빈 입력/빈group이 있고 충돌이 없으면 null. **이는 caller가 공급한 규칙·메타데이터 범위의 관측이며 전체 독립성이나 실제 적격 장면 집합의 완전성을 뜻하지 않는다.**
- `complete_spatial_separation_claimed`, `historical_readiness_cause_reconstructed`, `training_split_leakage_resolved`는 항상 false.

None 결과에서 component·conflict·plan 수 등 알 수 없는 값은 null이다. 수행한 작업 수는 0이고 `union_complete=false`, 저장 coverage는 NOT_STARTED다. 빈 리스트는 명시적 0개 supplied scene이므로 union 계산 자체는 완료하되 전체 분리를 주장하지 않는다.

## 시험 증거와 다음 연결

관련 시험: `tests/test_readiness_connectivity_witness.py`, **16 PASS / 0.006초**, 로그 `evidence/integration/readiness-connectivity-witness-related-20261017.log`.

합성 시험은 None/empty 구분, cross-role namespace/last owner, 동일 행 token no-op, 중복 scene_id, 빈group skip+bbox 참여, literal 공백/빈 scene_id, bbox 접촉과 미세 양수, within-split transitive 연결, lexical root·fixed split conflict events, witness 저장 0/부분에서도 전체 union 동일, 전수 pair 한도, bool/큰 정수/NaN/Infinity/좌표·문자열·식별자 오류, 입력 불변·file-open trap을 확인했다. 1..24개의 seeded 작은 입력에 대해 기존 metadata union 부분을 별도로 표현한 reference와 모든 province component가 일치했다. 이 합성 비교는 과거 실제 차단 원인의 복구나 운영 gate 통과 증명이 아니다. 독립 시험 및 전체 회귀는 Root 증거로 덧붙이고 중복 합산하지 않는다.

이 단위는 파일 읽기·쓰기, source raster·boundary·GEOS, 네트워크, readiness.assess 호출이 없다. CLI/API/UI 연결을 만들지 않았으므로 UI 변경이 필요 없다. caller metadata의 신원·hash, 원본 scene index, eligibility, 저장 report 통합 및 향후 witness 보존 형식 연결은 **PLANNED 후속 범위**이다. 기존 저장 report의 부재한 증거를 신규 helper로 소급 확정하지 않는다. 원본/원장/예약/lock/모델/분할/기존 gate·policy는 변경하지 않는다.


## Root 실제 저장 보고서의 증거 부재 확인

**VERIFIED_REAL은 저장 보고서의 근거 부재 확인 범위만**이다. [실제 읽기 기록](../../evidence/integration/readiness-connectivity-witness-live-absence-20261017.json)과 [실행 로그](../../evidence/integration/readiness-connectivity-witness-live-absence-20261017.log)는 saved readiness의 SHA `6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db`를 먼저 확인한 뒤 prepared_payload=null 및 장면별 연결 근거가 저장되지 않았음을 기록한다. Root는 이를 대신할 장면 메타를 물리 manifest나 corner 보고서에서 추정하지 않고 helper(None)을 한 번 호출했다. 결과는 UNKNOWN_NOT_PERSISTED·union_complete=false·학습 준비 false다. 실제 적격 장면 목록으로 helper를 검증하거나 과거 차단 분기를 복원한 것이 아니다. 저장된 기존 blocker 5개와 eligible 1111(train628/val233/test250)는 원형대로 보존했다.

독립 합성 시험은 **16 PASS / 0.007초**, [독립 로그](../../evidence/integration/readiness-connectivity-witness-independent-20261017.log)에 별도 graph/BFS oracle 300사례·3917 token/bbox 이벤트 일치도 기록했다. 별도 oracle 실험과 독립 반복 시험을 전체 unittest 건수에 중복 합산하지 않는다. 기존 readiness/gate/정책/분할의 변경·실행과 source/래스터 읽기는 없었다.


## Root 전체 회귀·보존 및 후속

[전체 회귀 로그](../../evidence/integration/readiness-connectivity-witness-full-tests-20261017.log): **554건/553 PASS/1 SKIP/197.097초/종료0**. 기존 Windows OS symlink 생성 권한 조건 한 건을 건너뛰었고 deterministic 경계 시험은 통과했다. 관련 16건과 독립 반복 16건·별도 BFS 300사례를 전체 건수에 중복 합산하지 않는다.

[사전 증거](../../evidence/integration/readiness-connectivity-witness-preflight-20261017.json)와 [최종 보존 증거](../../evidence/integration/readiness-connectivity-witness-live-integrity-20261017.json)는 보호132참조·기존19계약 SHA·저장 readiness SHA 불변 및 이전 추적 코드/데이터/계약 변경0, 기존 blocker 5개 원형 완전 보존을 기록한다. 이 증거는 source 래스터 내용의 현재 SHA 재검사나 원자적 snapshot 보장이 아니다. 원본/원장/lock/예약136314880B/분할/모델·terminal 없는2건·BLOCKED/모든 승인false/환불0를 유지했다.

다음 작은 단위는 caller 입력의 provenance·적격 장면 식별 계약과 제한된 witness 반환값의 저장 envelope를 분리해 설계·검증하는 것이다. strict bounded JSON/명시 hash·현재 구현 버전 결합·동일 입력 재현성 및 truncated 의미를 정의하되, 저장 보고서 근거를 소급 복원하지 않는다. 기존 readiness에 실제 통합하거나 gate를 재실행·판정을 변경하는 작업은 별도 후속 PLANNED다. 신규 CLI/API/UI가 없어 이 단위에서 화면 수정·49 UI시험/build·실브라우저 재검증 대상은 없다.


## 직렬화 후속 구현

[59 순수 envelope 계약](59_readiness_connectivity_envelope_validation.md)의 구현·합성 검증을 완료했다. 입력 순서/메타·caller provenance와 helper 선언 SHA·제한된 witness를 canonical bytes에 묶어 외부 pin 및 재계산으로 검증한다. 파일/DB 영속 저장·실제 적격성/출처 인증·readiness 연결은 구현하지 않았다. 이 문서의 실제 scene 근거 부재 및 기존5차단은 유지된다.
