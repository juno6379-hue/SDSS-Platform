# 98. 기존 Draft 등록 API의 선택적 모델 버전 전달

상태: **TESTED_SYNTHETIC**. 실제 소스에서 추출한 route/auth 조각을 격리 FastAPI와 작은 합성 report/checkpoint·TempStore로 시험했다. 운영 등록 성공·운영 카탈로그 변경·실제 학습·배포는 수행하지 않았다.

## 변경과 요청 계약

기존 `POST /api/models/register-experiment`에서 `report_path` 외에 선택적 `model_version`을 내부 [97 등록 함수](97_model_version_declaration.md)에 전달한다. [main.py](../../backend/app/main.py)의 기존 `with registry_lock` 안에 조건 분기만 추가했다. 원 schema·훈련 producer·97 본체·GMAIS/Workflow/수동 초안 API를 변경하지 않는다.

```json
{"report_path": "experiments/example.json"}
```

키가 **없으면** 원래의 두 인자 호출을 그대로 사용한다. 따라서 기존 생략 요청은 응답·레코드와 새로운 선언 필드 부재가 유지된다. 다음과 같이 키가 있으면 값을 보정하지 않고 keyword 인자로 전달한다.

```json
{"report_path": "experiments/example.json", "model_version": " caller-model-v2 "}
```

`null`, bool, 빈 값도 생략으로 바꾸지 않는다. 실제 report·파일 등 기존 검사가 통과한 뒤 97의 문자/별칭 검증과 충돌 검사를 거치며 잘못된 값은 기존 예외 처리에서 HTTP422로 변환한다. 기존 파일·완료·SHA·중복 ID 오류가 먼저 있으면 그 오류가 우선한다. 없는 report 경로로 받은 운영 422는 파일 경계 확인이며 version 검증을 직접 실행한 증거가 아니다.

기존 unknown extra key 무시 정책을 유지한다. 새 strict JSON schema를 넣지 않았고 `status`, `approval_ref`, `independent_evaluation`, `dataset_version`, `overwrite` 등을 등록 인자로 읽지 않는다. 요청으로 승인 상태를 변경하거나 dataset version으로 모델 버전을 추정할 수 없다.

## 응답·인증·잠금

- 성공은 기존 **201**이며 `model`, `dataset`, `claim` 응답 구조를 유지한다. 명시 성공에서만 모델의 `model_version_declaration`에 exact 5키를 추가한다. top-level `model_version`이나 dataset 새 필드를 만들지 않는다. raw training에 기존 같은 값이 있으면 그 필드는 원래 복사 동작으로 남을 수 있다.
- 기존 `ValueError`, `OSError`, `KeyError`, `TypeError`는 **422**와 `{"detail": "<기존 예외 메시지>"}`를 유지한다. body 타입/부재 오류도 FastAPI의 기존 422다.
- 기존 전역 `Depends(authorized)`를 유지한다. 토큰을 설정한 경우 기존 Bearer 검사로 거부하며 등록 함수·registry_lock 진입 전에 401이다. 새로운 인증·기관 권한 정책을 추가하지 않는다.
- 기존 registry_lock 안에서 생략/명시 호출 모두 실행하며 예외 때 잠금을 해제한다. 잠금을 추가하거나 등록 내부의 dataset→model 두 번 쓰기를 하나의 DB transaction으로 바꾸지 않는다.

97의 모델 상태 `Draft`, 독립 평가·과학 검증 false, checkpoint/report/manifest 일치·중복 model/dataset ID 거부를 그대로 사용한다. 같은 ID 재등록·overwrite·모델 실행 승인 기능은 없다.

## caller 선언의 한계

명시 선언은 caller 메타데이터다. 연결한 SHA는 기존 검증 파일의 hash이며 기관 권위·원본 인증·불변 버전 등록 영수증이 아니다. 생략 경로는 이전 raw training의 임의 필드도 복사하므로 동일한 `model_version_declaration` shape/source가 있다고 실제 명시 호출 생성이나 인증을 판정할 수 없다. resolver 신뢰 증거·권위 모델 version·전역 immutable 정책은 별도 검토가 필요하다.

97의 비트랜잭션 한계도 유지한다. 두 번째 model 쓰기가 실패하면 dataset만 남을 수 있고 다른 Store 쓰기·다른 프로세스와의 동시 경쟁을 전역 차단하지 않는다. 요청 화면을 떠나거나 표시를 취소해도 이미 처리 중인 서버 등록이 취소되는 계약은 없다.

## 검증 방법과 근거

[신규 시험](../../tests/test_model_version_registration_api.py)은 운영 `app.main`을 import하지 않는다. 원문 [main 사전 사본](../../evidence/integration/model-version-api-original-main-20261017.py)의 SHA `11dfe9aafe9c419381650349eb2572b9625e5a243ec07f76a28e5ad79a639be9`를 고정한 뒤 원/current 소스의 AST에서 `authorized`, `app = FastAPI(...)`, 실제 decorator가 붙은 `register_completed_experiment`만 추출해 실행한다. Store·registry_lock은 격리 시험 객체다.

이는 실제 route 코드·인증 dependency·201/422·kwargs 배선 시험이다. 전체 main 초기화, CORS/middleware, 실행 중 서버 적용·재시작, 운영 카탈로그 성공 등록을 검증한 것은 아니다. 관련 기존 `test_api`는 import 전 임시 `GEOAI_DATA_ROOT`를 설정하는 기존 안전 fixture를 사용한다.

```powershell
# 프로젝트 루트, PYTHONPATH=.runtime;backend;tests
python -m unittest test_model_version_registration_api -v
python -m unittest test_model_version_registration_api test_model_version_declaration test_experiment_registry test_model_reference_contract test_api -v
```

- 집중 신규 **11 PASS / 4.881초**: [집중 시험 로그](../../evidence/integration/model-version-api-focused-20261017.log).
- 관련 최종 **48 PASS / 19.174초**: [관련 시험 로그](../../evidence/integration/model-version-api-related-20261017.log). 신규 11개는 관련 묶음에 포함되므로 별도 합산하지 않는다. 전체 회귀·독립 검토·보존은 Root 인계/closeout에서 기록한다.
- 원/current auth 함수·app 선언·route decorator·인자·기존 except tuple AST 동등을 확인했다. 생략 요청의 전체 응답/헤더, raw SQLite record body, put 순서도 원문과 동일하다.
- present null·패딩 원형 kwargs 전달은 격리 mock으로 확인했다. mock 201은 실제 등록 성공 증거로 계산하지 않는다.
- 97 본체를 호출한 TempStore 성공은 exact5/hash·Draft/false·model-only·원 파일 hash 불변과 기존 두 번 쓰기를 확인했다. 잘못된 문자/alias/null·충돌·중복은 422/첫 put0, 원 파일/SHA 오류 우선순위도 유지한다.
- 기존 Bearer 거부 401이 잠금/등록 이전에 발생하고 정상 인증 후 기존 배선이 동작함을 확인했다. 예외 4종의 422 변환과 잠금 해제, unknown extra key 미전달도 검증했다.

## UI 인계

UI 담당에게 키 생략/존재의 차이, 원형 패딩 보존, 201/422·오류 우선순위, Draft/false, 선언의 비인증 한계를 인계한다. 화면 연결·프론트 시험·실제 브라우저 확인은 별도 UI 구현 문서와 Root 증거로 보고한다. 이 문서의 API 합성 성공을 운영 브라우저 성공 등록으로 표시하지 않는다.

## 통합 실제 검증·전체 회귀

### Draft 등록 API·UI의 명시 모델 버전 선택 연결 검증 완료 (98/99)

- **API 담당:** 기존 endpoint는 model_version 키 존재시에만 원형 keyword를 전달한다. 생략·null 구분, 기존 인증/잠금·201/422·파일 오류 우선순위를 유지했다. 관련48 PASS·독립11 PASS이며 성공 등록은 AST 격리/TempStore/mock 범위다.
- **UI 담당:** 기존 Model Registry 폼에 기본off/빈버전 선택을 연결했다. off는 기존 body, on은 원문 버전만 추가한다. busy·중복 클릭·route/back/unmount 늦은 표시 방어와 서버201 뒤 refresh실패 안내를 분리했다. 관련16·전체153·독립16 PASS, 실제 겹침 발견 후 전용CSS로 보완하고 관련16/전체153 재통과·최종build90 modules/27.52초다. 기존 로그를 덮지 않았다.
- **실제 브라우저/서버:** API의 없는 보고서4회422·브라우저 음성1회422, 실제화면8체크·완료422뒤 back복귀·가로넘침0·SVG·제목겹침0을 확인했다. 편집중 일시 HMR오류1건을 보존하고 reload뒤 정상표시/카탈로그복귀를 확인했다. 최종폼은 빈값/off다. 성공등록·지연동시성·refresh실패는 격리시험만으로 구분한다. 없는파일422는 버전검사 성공경로 증거가 아니다.
- **Root 전체·보존:** backend 998건/997 PASS/기존Windows symlink 1 SKIP/366.134초/exit0. 보호141·불변core+schema70·이전증거·catalog14/기존Job본문 변경0. 기존소스 수정은 사전기준선과 비교한 main.py/ModelReview.tsx뿐이며 신규adapter/CSS/test를 추가했다. 원본·원장/lock·예약136314880B·분할·모델보존, 운영성공등록/Job/Workflow·수집/정식학습/배포0이다.
- **회귀 실행 이력:** 최초 Root 실행은 PYTHONPATH 누락으로648건/327.484초/import errors31이었다. 최초 model-version-api-full-tests-20261017.log를 보존하고 지정 .runtime;backend;tests 환경으로 corrected 로그에 재실행한 최종 결과만 위 통과 수치로 사용한다. 제품 코드를 바꿔 import 오류를 우회하지 않았다.
- **문서·이해자료:** 신규98/99와 관련07/08/97, 원장·소유권·인계서를 갱신했다. understanding_agent가 완료코드·실제/합성시험을 읽고 쉬운설명·이론·코드데이터·시험·발표대본·FAQ·INDEX·변경이력을 갱신했다. 최종문서감사/rawSHA snapshot은 model-version-api-closeout-20261017.json을 따른다.
- **한계·다음:** caller 선언은 기관권위·원본인증·과학/실행승인이 아니며 omitted raw필드도 같은shape를 가질수 있다. 실제model resolver/전역immutable/트랜잭션은 미구현이다. dataset_version 추정·역채움 금지와 기존 QA차단4/학습BLOCKED를 유지한다. 다음은 읽기전용 등록 출처 진단 계약 검토(PLANNED)이며 구현/실행승인0이다. 전체개발 미완료·지속개발/10분보고 유지, 예약ACTIVE와 실제작업을 구분한다.

근거: `evidence/integration/model-version-api-live-integrity-20261017.json`, `evidence/integration/model-version-api-live-api-20261017.json`, `evidence/integration/model-version-api-live-ui-20261017.json`, `evidence/integration/model-version-ui-desktop-final-20261017.png`.


## 100 내부 관측 후속

[순수등록선언관측](100_model_registration_provenance_observation.md)은 저장된 metadata의 부재·형식·충돌·근거부족·일치미인증을구분한다. API/UI·등록/승인gate에미연결이며 기존출처검증이나등록동작을대체하지않는다. 동일shape/source의raw복사위조도일치할수있으므로기관권위·실제바이트·과학/실행승인으로해석하지않는다. 이전모델필드도수정하지않는다. [관련/독립시험·보존](../../evidence/integration/model-provenance-live-integrity-20261017.json)과 [실제읽기관측](../../evidence/integration/model-provenance-catalog-observation-20261017.json)을참조한다. 전체회귀와프론트/build/브라우저는이번재실행하지않았고이전증거와구분한다.
