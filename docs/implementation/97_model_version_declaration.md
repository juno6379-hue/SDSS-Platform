# 97. 내부 실험 등록의 선택적 모델 버전 선언 보존

## 후속 연결 상태 — 98/99 (2026-10-17)

97의 내부 함수·충돌·쓰기 계약을 변경하지 않고 기존 등록 API와 ModelReview에 선택적 전달을 연결했다. `POST /api/models/register-experiment`는 `model_version` 키가 있을 때만 원형 keyword를 전달하며, 부재는 기존 두 인자 호출 그대로다. null은 생략으로 바꾸지 않는다. 기존 인증·lock·201/422·추가 필드 무시·Draft/중복 거부를 보존한다. [API98](98_model_version_registration_api.md), [UI99](99_model_version_registration_ui.md)를 참조한다.

기존 등록 details에 기본 off 선택란과 빈 버전 입력을 추가했다. 자동 POST·자동 채움·dataset_version 추정은 없다. 등록 busy 동안 입력·모델 선택을 막고 이동/unmount 후 과거 선택·오류 표시를 폐기한다. 성공한 등록의 목록 refresh는 화면 세대와 별도로 수행하며, 201 뒤 refresh 실패는 등록 실패와 구별한다. 표시 폐기는 서버 등록 취소나 rollback이 아니다. 선언의 키·shape·source만으로 caller 진정성·기관 권위·승인을 인증할 수 없다는 아래 한계는 그대로다.

후속 API 관련 48 PASS/독립 11 PASS, UI 관련 16 PASS/독립 16 PASS/전체 153 PASS·89 modules build가 근거다. 실제 API는 없는 report 경로 4회 422와 catalog 14행 불변만 확인했다([실제 API 기록](../../evidence/integration/model-version-api-live-api-20261017.json)). 성공 등록은 TempStore/mock 시험이며 운영 성공 등록은 없다. Root의 브라우저 오류 입력·뒤로가기 및 layout 최종 근거는 아직 정리 중이므로 최종 화면 완료를 주장하지 않는다. 아래 상태와 API/UI 미연결 문장은 97 단독 구현 당시의 범위를 보존한 이력이다.

상태: **TESTED_SYNTHETIC**. 작은 합성 checkpoint/report 파일과 임시 Store로 검증했다. 실제 학습, 운영 등록·카탈로그 변경, API 호출, 모델 실행·배포는 수행하지 않았다. 기관 권위·모델 불변 버전 등록·독립 평가·승인을 구현한 것이 아니다.

## 목적과 범위

내부 함수 [register_experiment](../../backend/app/experiment_registry.py)에 keyword-only 인자 `model_version`을 추가했다. 호출자가 미래 등록에서 직접 선언한 모델 버전 원문을 기존에 검증한 checkpoint와 훈련 report SHA-256에 연결해 보존한다. dataset_version을 model version으로 추정하지 않는다.

```python
register_experiment(store, report_path)  # 기존 동작 그대로
register_experiment(store, report_path, model_version='model-v2')
```

`_OMITTED` sentinel로 생략과 명시적 `None`을 구별한다. 생략하면 이전 응답과 모델·데이터 레코드의 직렬화 바이트가 같고 새 필드가 생기지 않는다. 기존 함수가 복사하던 raw training의 임의 필드도 그대로 복사한다. 생략 호출의 raw `model_version`이나 `model_version_declaration`은 새 명시 선언으로 소급 승격하지 않는다.

기존 main/API 호출은 인자를 생략한 상태 그대로다. API 입력 스키마, 훈련 producer, 모델 resolver, UI에는 연결하지 않았다. 새 UI에 표시할 API·상태·오류 계약이 없으므로 이 내부 단위는 직접 프론트 수정·build·브라우저 재시험이 필요하지 않다.

## 명시 호출의 계약

모델/데이터 ID·중복 ID·완료 상태·파일 경로·checkpoint SHA·훈련 보고서·dataset manifest 일치 등 기존 검사를 먼저 수행한다. 기존 lineage 계산 직후, 첫 `Store.put` 전에 [96의 model_reference_issue](../../backend/app/model_reference_contract.py)에 검증된 model ID와 caller version을 전달한다.

명시적 null·bool·숫자·비문자·빈 문자열·공백뿐인 값·제어문자·surrogate·257자 이상을 거부한다. `latest/current`는 strip/lower 비교로 거부한다. 정상 `" v1 "` 같은 패딩은 원문 그대로 보존한다. 검사 실패는 `ValueError`이며 dataset/model 쓰기는 모두 0이다. 기존 오류 조건이 함께 있으면 기존 검사 오류가 먼저 나온다.

- raw training에 `model_version`이 있으면 정확한 문자열 타입이고 caller 값과 **원문까지 동일**해야 한다. null·bool·다른 값·패딩 차이는 충돌이다.
- raw training에 `model_version_declaration` 키가 이미 있으면 값이나 모양과 관계없이 명시 호출을 거부한다. null이나 동일한 선언도 덮어쓰지 않는다.
- 검증 성공 시 **모델 레코드에만** 다음 exact 5키 객체를 추가한다. 별도 top-level `model_version`을 만들지 않고 dataset에도 새 필드를 추가하지 않는다. 기존 raw training에 같은 `model_version`이 있었으면 원래 복사 동작으로 그대로 남는다.

```json
{
  "model_version_declaration": {
    "schema_version": 1,
    "source": "CALLER_EXPLICIT_REGISTRATION",
    "version": "model-v2",
    "checkpoint_sha256": "<기존에 검증한 checkpoint SHA-256>",
    "training_report_sha256": "<기존 lineage의 훈련 report SHA-256>"
  }
}
```

선언 추가를 위해 파일을 다시 읽거나 hash를 새로 계산하지 않는다. 기존 checkpoint hash와 lineage 값을 재사용한다. 모델은 기존대로 `Draft`, `independent_evaluation=false`, `scientific_accuracy_validated=false`이며 등록 응답의 기존 claim도 유지한다.

## 신뢰·불변성 한계

이 객체는 caller 메타데이터이며 원본 인증·서명·권위 있는 등록 영수증이 아니다. **객체의 모양과 `source` 값만으로 실제 명시 호출이 생성했다고 판정할 수 없다.** 생략 경로는 이전과 같이 raw training의 임의 필드를 복사하므로 같은 모양의 선언도 복사될 수 있다. 명시 호출에서 충돌을 거부하는 것은 이 경로의 덮어쓰기를 막을 뿐, 생략 경로나 다른 Store 쓰기를 인증하지 않는다.

실제 모델 resolver는 신뢰할 등록 증거·권위 모델 버전·immutable 정책이 별도로 필요하다. 현재 선언을 즉시 실행 권위로 사용하거나 `dataset_version`과 대체하지 않는다. 기존 레코드 역채움·재등록·model family/복합키 정책은 추가하지 않았다.

모델 ID 또는 dataset ID가 이미 있으면 기존대로 거부한다. 하지만 `Store.put` 자체는 `INSERT OR REPLACE`이고 중복 확인과 쓰기가 원자적으로 묶이지 않았다. 기존 dataset→model 두 번 쓰기도 별도 transaction이다. 두 번째 쓰기 실패 시 dataset만 남을 수 있으며 동시 등록 경쟁을 전역 차단하지 않는다. 이번 구현을 트랜잭션 등록이나 전역 불변성 보장으로 표현하지 않는다.

## 시험과 근거

[신규 시험](../../tests/test_model_version_declaration.py)은 원 [register_experiment 소스](../../evidence/integration/model-version-original-registry-20261017.py)의 SHA `a20468f121900094808112b9c8e783bf2a0ce59f520ff0bffbbcf2438bd12548`를 확인하고 import해 비교한다. 임시 파일은 직렬화 계약용 작은 바이트이며 학습·성능 시험 데이터가 아니다.

```powershell
# 프로젝트 루트, PYTHONPATH=.runtime;backend;tests
python -m unittest test_model_version_declaration test_experiment_registry test_model_reference_contract test_registry_collection test_dataset_registry_versions -v
```

- 생략 시 원문 응답·SQLite record body 바이트·put 인자/순서 동등, raw 임의 version/declaration 필드 복사와 새 필드 부재를 확인한다.
- 명시 선언의 exact5키·정수 schema_version·SHA 일치·원형 패딩·256경계·model-only 보존과 Draft/false를 확인한다.
- invalid 입력·두 종류 충돌·모델/데이터 중복 ID는 첫 put 0을 확인한다. 기존 완료/파일/hash/report/manifest 오류 우선순위도 원문과 비교한다.
- 파일 hash 전후 동일, 추가 digest 읽기 없음, dataset version 추론 없음, keyword-only를 확인한다. 격리된 두 번째 쓰기 실패 시험은 비트랜잭션 한계가 그대로임을 확인한다.
- 초기 10개 중 1개는 Windows 경로 구분자에 대한 **시험 비교 오류**로 실패했다. 시험의 기록 경로를 `as_posix()`로 바꿨고 production 변경은 없었다. [초기 실패 로그](../../evidence/integration/model-version-initial-tests-20261017.log)를 보존한다.
- 최종 관련 결과: **37 PASS / 14.006초**(신규 10개 포함). [관련 시험 로그](../../evidence/integration/model-version-related-20261017.log). 전체 회귀·독립 검토·원본/카탈로그 보존·이해자료 갱신은 Root closeout·인계서에서 구분해 기록한다.

운영 모델/데이터 레코드는 등록하지 않았다. 이번 시험의 TempStore 성공을 실제 모델 등록·과학 검증·실행 성공으로 표시하지 않는다. 실제 사용하려면 향후 별도 API/호출부·신뢰 등록·UI 계약과 권한·오류·부분 실패 처리를 검토해야 한다.

## Root 최종 검증과 인계

최종 독립13 PASS/9.575초, backend전체987건/986 PASS/기존1 SKIP/380.835초/exit0. 보호141·불변core+schema70·catalog14/기존Job본문·이전증거616파일을 보존했다. 기존 snapshot 코드와 별도 사전 SHA핀 원문 기준으로 기존 소스 수정은 experiment_registry.py 한 파일뿐이다. 이전995 snapshot에 없던 이 파일은 사전 원문 보충 기준선으로 검사하고 최종 snapshot에 추가한다. 반복/별도경계 사례를 신규10 시험 수에 합산하지 않는다. 최초 Windows경로 목록비교1실패는 시험 as_posix 처리로 수정했고 initial로그를 보존했다. 원SQLite body/응답/put exact 비교는 그대로 유지한다.

`model-version-catalog-observation-20261017.json`은 운영catalog를 읽기 전용으로 관측한 근거다. 기존모델1 Draft·독립평가false·버전/선언부재와 dataset_version존재를 확인했고 scientific_accuracy_validated는 부재/null로 구별했다. 실제모델 버전 추정·역채움·등록/학습은없다. 새선언 성공/실패는 작은 합성파일과 TempStore 시험이며 운영모델/기관권위/원본인증/실행승인이 아니다.

기존main/API·UI는 옵션생략동등이라 직접frontend/build/브라우저 재시험없다. 새옵션을 운영서버 등록으로검증하지 않았다. 관련계약/사용법·시험·인계서와 이해자료/대본/FAQ·INDEX/변경이력을 같은단위로갱신했고 최종감사/snapshot은 `evidence/integration/model-version-closeout-20261017.json`에 기록한다. 전체개발은미완료다.

## 98/99 최종 통합 검증 보충

최종 전체 회귀는 [corrected 로그](../../evidence/integration/model-version-api-full-tests-corrected-20261017.log)의998건/997 PASS/기존Windows1 SKIP/366.134초다. 최초 PYTHONPATH누락648건/import31오류 로그는 보존하며 통과 근거와 구분한다. [실제 화면](../../evidence/integration/model-version-api-live-ui-20261017.json)8체크·음성등록1회422·뒤로가기복귀·겹침/넘침0을 확인하고 최종layout build90 modules/27.52초를 실제로그로 정정했다(초기89와 구분). [보존 근거](../../evidence/integration/model-version-api-live-integrity-20261017.json)의 보호141·core70·이전증거631·catalog14 변경0이다. 성공등록은 격리시험만이며 운영성공등록0, caller선언≠승인을 유지한다.

## 100 내부 관측 후속

[순수등록선언관측](100_model_registration_provenance_observation.md)은 저장된 metadata의 부재·형식·충돌·근거부족·일치미인증을구분한다. API/UI·등록/승인gate에미연결이며 기존출처검증이나등록동작을대체하지않는다. 동일shape/source의raw복사위조도일치할수있으므로기관권위·실제바이트·과학/실행승인으로해석하지않는다. 이전모델필드도수정하지않는다. [관련/독립시험·보존](../../evidence/integration/model-provenance-live-integrity-20261017.json)과 [실제읽기관측](../../evidence/integration/model-provenance-catalog-observation-20261017.json)을참조한다. 전체회귀와프론트/build/브라우저는이번재실행하지않았고이전증거와구분한다.
