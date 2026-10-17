# 135 — 사용자가 명시한 연차 유효 픽셀 비율 정책의 정수 평가

상태: **TESTED_SYNTHETIC**. 신규 `inspect_annual_mask_policy(store, model_ref, training_report_sha256, requested_years, policy)`는 134의 전체 연차 읽기·값 계수·Registry manifest 결합이 끝난 뒤 caller가 명시한 최소 유효 비율을 평가한다. 신규 `backend/app/ml/annual_mask_policy.py`, 집중 시험, 본 문서만 추가한다. 기존 소스·134·115 실행 gate·API/UI는 변경하지 않는다. 내부134 연결은 수행하지만 운영 실행이나 품질 승인을 허용하지 않는다.

## 기본값 없는 명시 정책과 선검사

policy는 필수 인자이며 정확히 다음 네 키를 가진다. 기본 비율이나 기관 기준을 추정하지 않는다.

```json
{"schema_version":1,"minimum_valid_numerator":1,"minimum_valid_denominator":2,"comparison":"greater_than_or_equal"}
```

schema_version은 정확한 int1, denominator는 정확한 int1~1000000, numerator는 정확한 int0~denominator, comparison은 정확한 문자열 greater_than_or_equal이어야 한다. bool·float·숫자 문자열·누락·추가 키·다른 비교 연산을 거부한다. 정책과134의 전체 2~6행 요청을 Store I/O 전에 검증하고 사본으로 만든다. 잘못된 정책 또는 여섯 번째 행의 잘못된 참조도 INVALID_INPUT이며 annual_observation_calls와 Store get은0이다.

유효 요청은134를 정확히 한 번 호출한다. 추가 Store.get·모델 load·파일 열기·영상/마스크 pixel read는 없다. 정상2/6행은 기존134와 같은13/37 get, 모델 load1회다.134가 성공하지 못하면 원형 관측을 남기고 ANNUAL_DIAGNOSTICS_BLOCKED로 종료한다.134의 full 성공 뒤에만 정책용 counts 검사를 시작한다.

## 모든 counts의 선검사와 정수 비교

parent의 artifact_bytes_verified·mask_values_verified·registry_manifest_join_verified는 정확한 bool True여야 한다. 행 목록의 수와 순서가 요청에 대응하고 각 행은 원134의 exact5 shape, 요청과 같은 exact int year, MATCHED_UNVERIFIED, null issue, 정확한 join True여야 한다.133의 status와 선언·값·artifact flags도 성공해야 한다. parent와 mask 결과의 dict/key 수를 제한하고 임의 대형 tree를 재귀 순회하지 않는다.

각 nested133 counts는 exact3 `{valid_pixels,invalid_pixels,total_pixels}`다. 세 값은 bool을 제외한 정확한 builtin int여야 하며 total은1~1024², valid와 invalid는 각각0~total, valid+invalid=total이어야 한다.0/0·음수·잘못된 합·초과 크기·float/string·추가 키는 차단한다. **모든 연도의 counts를 먼저 검산하고 복사한 다음** 정책 계산을 시작한다. 뒤 행이 잘못됐다고 앞 행만 정책 성공으로 남기지 않는다.

평가는 다음 정수식뿐이다.

`valid_pixels * minimum_valid_denominator >= total_pixels * minimum_valid_numerator`

나눗셈·소수 반올림·유효 숫자 근사 없이 정확한 경계를 판정한다. 모든 연도를 평가하므로 정책 미달 행 뒤의 행도 MET/NOT_MET 결과를 가진다. 전체 상태의 issue는 첫 미달 연도다. all0은 numerator0 정책에서 통과하고 양수 정책에서는 미달이다. 이는 caller가 선택한 수학적 기준일 뿐 구름/센서 QA·기관의 정책 채택·최소 학습 자료 충분성을 인증하지 않는다.

## exact20 결과와 I/O 이력

반환 필드는 schema_version:1, scope:`CALLER_EXPLICIT_ANNUAL_MASK_POLICY_READ_ONLY`, status, issue, parent_annual_observation, policy, per_year_observations, annual_observation_calls, caller_policy_evaluated, caller_policy_met, artifact_bytes_verified와 다음9개 false다.

- quality_report_verified / quality_mask_verified / mask_semantics_verified
- registry_aoi_verified / source_authority_verified / scientific_accuracy_validated
- execution_authorized / state_dict_verified / workflow_supported

status는 INVALID_INPUT / ANNUAL_DIAGNOSTICS_BLOCKED / POLICY_INPUT_BLOCKED / CALLER_POLICY_NOT_MET / CALLER_POLICY_MET_UNVERIFIED다. issue는 null 또는 안전한 고정 `{code,field,year}`다. stage 예외 원문이나 raw 경로를 노출하지 않는다. 잘못된 counts 또는 parent 성공 경계는 POLICY_COUNTS_INVALID/counts로 차단하며 해당 요청 연도 또는 전체 경계의 null year를 기록한다.

parent_annual_observation은 원134 결과를 그대로 보존한다. policy는 검증한 detached 사본이며 invalid 입력에서는 null이다. per_year_observations는 exact4 `{year,status,counts,policy_met}`다. 상태는 NOT_CHECKED/MET/NOT_MET이고 미평가 행의 counts와 policy_met는 null이다. 평가한 counts도 parent와 별도 사본이다.

caller_policy_evaluated는 모든 counts 선검사 뒤 모든 연도를 평가했을 때 true다. caller_policy_met는 그 중 모든 연도가 기준을 충족할 때만 true다. 상위 artifact_bytes_verified도 **모든 연도가 정책을 충족한 때만** true이며, 미달이라도 nested134의 바이트/계수 성공은 변경하지 않는다. 이 상위 flag는 정책을 포함한 전체 단위 성공 범위이지 하위 파일 바이트가 변조됐다는 역추론 근거가 아니다.

POLICY_INPUT_BLOCKED의 NOT_CHECKED는 정책 계산을 하지 않았다는 뜻이다.134가 이미 모든 영상·mask를 읽었을 수 있으므로 파일 미읽음으로 해석하지 않는다. 정책 미달도 모든134 I/O와 모든 연도 평가가 끝난 결과다.134 자체 실패는 partial 원형 관측을 확인해야 한다.

## 한계와 검증 인계

caller 기준 충족은 실제 품질·기관 기준 채택 승인·mask 의미의 정답성·과학 정확도·AOI coverage·state 호환·실행 승인이 아니다.115·API/UI에 연결하지 않고 자료 수정·수집·등록·훈련·추론·배포를 수행하지 않는다. 기존 Store DB predecode·Torch allowlist·GDAL CPU/RSS/시간·다중 관측 비원자성과 TOCTOU 한계를 상속한다. 정책 계산 자체는 추가 파일/DB/pixel I/O를 만들지 않는다.

담당 집중 **8 PASS / 5.938초 / exit 0**는 `evidence/integration/annual-mask-policy-agent-20261018-focused.log`다. 실제 Temp 영상·Registry·미훈련 CPU checkpoint의2/6행을 사용한 통합 시험과 mock134 결과의 순수 경계 시험을 분리했다. 명시 정책 선검사·정확한 정수 경계·all0·전행 평가·counts 오염·year bool/잘못된 join/full flags·detached 결과·caller snapshot·안전 예외를 검증했다. Affine 라이브러리의 PendingDeprecationWarning은 로그에 보존했다.

source SHA `ebf3db476613101732c4b1db0b2c41e45148dc76ebbec078031668d286541b9c`, test SHA `78a42535d9506ddf93e268ae6ec366af80b4f73b8aaa7344da9b165996ea6b26`로 Root와 독립 담당에게 동결했다. 기존 제품 소스는 수정하지 않았다.

Root는 관련 회귀·실제 Temp 대비·보존·공통 인계/Git을, 독립 담당은 별도 fixture 경계를 검증한다. 이해 담당은 완료 코드·검증·한계를 해설/발표/FAQ/INDEX/변경 이력에 반영한다.115/API/UI에 미연결이므로 frontend/build/browser 변경·재실행은 필요하지 않다. 이전 전체 backend/frontend 결과를 이번 제한 시험과 합산하지 않는다.

## Root 실제 파일 대조와 보존

Root 최종 관련 **26 PASS / 42.071초 / exit 0**는 `evidence/integration/mask-policy-root-related-20261018.log`다. 신규135의8개,134의9개,133의9개를 포함하며 집중·독립과 중복 합산하지 않는다.

`evidence/integration/mask-policy-runtime-20261018.py`와 같은 stem `.json`·`.log`는 실제 Temp fixture의 **7개 시나리오 통과**를 기록한다.3년 모두 정확한1/2 경계이면 MET 세 행이고, 두 번째 행의32767/65536이1/2에 미달하면 MET/NOT_MET/MET로 모든 행을 평가했다. 두 경우 get19회·모델 load1회·mask read3회이며 정책 평가는 I/O를 추가하지 않았다. all0은 기준0에서 통과하고1/1000000에서는 미달했다. bool 정책은 Store I/O0으로 차단했다. 부모의 두 번째255 및 Registry manifest 변경은 get16회에서 부모 실패로 차단하고 caller_policy_evaluated=false를 유지했다. DB/전체 파일 불변·영상 픽셀 읽기0·훈련0을 확인했다.

`evidence/integration/mask-policy-live-integrity-20261018.json`은 보호141개·기존 source303개·이전 증거1200개·catalog14행과 SHA·예약136314880바이트 불변을 기록한다. 기존 소스·운영 자료·모델·원장·분할·예약을 변경하지 않았다. 정책 충족이나 실제 Temp 대조를 운영 QA/기관 승인·과학 정확도·실행 허용으로 확대하지 않는다.

## 독립 최종 근거

독립 **7 PASS / 0 SKIP / 28.670307초 / exit 0**는 `evidence/integration/mask-policy-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 실제2/6행의 get13/37회·모델 load1회·mask read N회·영상 픽셀0·추가 I/O0과 DB/전체 파일 불변을 확인했다. 실측 유효 비율0.5에500001/1000000 정책은 모든 행 NOT_MET, caller_policy_evaluated=true, 상위 artifact=false와 nested134 artifact=true를 유지했다. invalid 정책과 여섯 번째 불량 행은 I/O0이었다.

별도 명시 mock에서는349525/1048576과349526/1048576의1/3 경계를 정확한 정수식으로 구별했다. 이 경계는 실측 mask가 아니라 정책 산술의 합성 입력 검증이다. counts exact3의 int/type/합/음수/0/상한과 strictTrue 오염은 모든 정책 행 NOT_CHECKED로 차단했다. all0의 기준0, policy/ref snapshot,134 실패도 검증했다. exact20/9false와 최종 source/test SHA, Git9a14fc6의 기존 핵심8개 source SHA·tracked source 불변이며 제품 지적은 없다. 운영·API/UI/frontend/build/browser 실행 없이 실측·mock과 caller 정책 충족·기관 승인 범위를 구분한다.

집중·관련·독립·실제 Temp 대조와 보존 근거를 반영한 뒤 문서를 동결했다.115/API/UI 미연결과 기관/과학/실행 false 범위는 그대로 유지한다.
