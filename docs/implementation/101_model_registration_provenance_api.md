# 101. 모델 등록 메타데이터 관측의 읽기 전용 API

상태: **TESTED_SYNTHETIC**. 실제 main 소스의 route/auth/record 조각을 AST로 추출해 격리 FastAPI·TempStore에서 시험했다. 운영 main을 import하거나 운영 모델을 등록하지 않았다. 실행 중 서버의 실제 GET·UI 적용 여부는 Root의 별도 근거로 구분한다.

## endpoint와 관측 범위

```http
GET /api/models/{identifier}/registration-provenance
```

[main.py](../../backend/app/main.py)에 읽기 전용 route만 추가했다. 기존 `record('models', identifier)`로 모델을 한 번 읽고 [100의 inspect_model_registration_provenance](100_model_registration_provenance_observation.md) 결과 **exact 10키를 그대로** HTTP200으로 반환한다. 추가 wrapper·타임스탬프·원문 모델 ID/버전/hash/경로를 응답에 넣지 않는다. 100 core와 기존 다른 route/auth/record는 변경하지 않았다.

100의 다섯 상태는 모두 정상 관측 결과이므로 HTTP200이다.

| status | 의미 |
|---|---|
| `ABSENT` | 유효한 ID의 레코드에 선언 키가 없음 |
| `INVALID` | 관측할 선언/존재하는 부모 값 등의 형식이 잘못됨 |
| `RECORD_CONFLICT` | 유효한 필드끼리 원형 값이 다름 |
| `PARENT_BINDING_UNKNOWN` | 알려진 충돌은 없으나 부모 hash가 빠짐 |
| `CONSISTENT_UNVERIFIED` | 메타데이터끼리 일치하나 권위·원본/실파일은 미검증 |

성공 예시는 선언 부재 관측이다.

```json
{
  "schema_version": 1,
  "scope": "LOCAL_MODEL_REGISTRATION_METADATA_OBSERVATION_ONLY",
  "status": "ABSENT",
  "declaration_present": false,
  "bindings": {
    "checkpoint_sha256": "NOT_CHECKED",
    "training_report_sha256": "NOT_CHECKED",
    "model_version": "NOT_CHECKED"
  },
  "issue": null,
  "authority_verified": false,
  "artifact_bytes_verified": false,
  "execution_authorized": false,
  "scientific_accuracy_validated": false
}
```

binding·issue의 고정 코드와 형식 우선/충돌 우선 규칙은 [100 계약](100_model_registration_provenance_observation.md)을 그대로 따른다. `INVALID`는 API 장애가 아니라 저장된 메타데이터의 관측 상태다.

## 읽기·승인·오류 계약

API에는 모델 조회 **Store.get 1회**의 DB 읽기가 있다. helper 자체의 I/O0과 구분한다. Store.put·등록·파일/체크포인트/report 읽기·rehash·network·resolver 호출은 없다. 모델 원문과 승인 상태를 변경하지 않는다. 추가 registry lock이나 transaction을 넣지 않는다.

`authority_verified`, `artifact_bytes_verified`, `execution_authorized`, `scientific_accuracy_validated`는 모든 관측 상태에서 항상 false다. 이 진단이 그 검증을 하지 않았다는 뜻이며 기존 모델의 실제 승인 필드를 false로 덮어쓰거나 독립 평가 결과를 무효화하는 것이 아니다. 정합한 위조/복사 메타데이터도 `CONSISTENT_UNVERIFIED`일 수 있으므로 기관 권위·등록 원본 인증·실제 파일 일치·모델 사용 승인을 추정하지 않는다. dataset_version으로 모델 버전을 채우거나 기존 레코드를 역채움하지 않는다.

| HTTP | 동작 |
|---|---|
| 200 | 위 다섯 관측 상태의 exact 10키 |
| 401 | 기존 전역 `Depends(authorized)`의 Bearer 검사; Store 읽기 전 거부 |
| 404 | 기존 record helper의 `{"detail":"항목이 없습니다."}` |
| 503 | 새 진단 route의 예상하지 못한 조회·import·helper 예외에 고정 메시지 |

새 route는 기존 `HTTPException`을 그대로 전달한다. 그 외 `Exception`은 이 route에서만 HTTP503 `{"detail":"등록 선언 관측을 완료할 수 없습니다."}`로 변환한다. `str(exception)`·파일 경로·ID·DB 오류 상세를 응답하지 않는다. local import도 try 안에 두어 import 실패를 같은 안전 오류로 처리한다. 다른 endpoint의 오류 정책은 변경하지 않는다.

## 시험·범위·실행 이력

[신규 시험](../../tests/test_model_registration_provenance_api.py)은 원 [main 사전 사본](../../evidence/integration/model-provenance-api-original-main-20261017.py)의 SHA `bae2e9d6592054d946a9e90549ee84d154737a8626d16a1b273108eb768c92c8`를 확인한다. 원/current AST에서 `authorized`, `app = FastAPI(...)`, `record`, 기존 models 목록과 새 route만 추출해 TempStore namespace에서 실행한다. 새 route AST를 제외하면 원 main 전체 AST가 같음을 비교한다.

이는 실제 route·인증 dependency·record 코드의 격리 검증이다. 전체 main 초기화·CORS/middleware·운영 process reload·실제 서버 적용·운영 등록 성공 근거가 아니다.

```powershell
# 프로젝트 루트, PYTHONPATH=.runtime;backend;tests
python -m unittest test_model_registration_provenance_api -v
python -m unittest test_model_registration_provenance_api test_model_registration_provenance test_model_version_registration_api test_model_version_declaration test_model_reference_contract test_experiment_registry -v
```

- 최종 집중 신규 **9 PASS / 1.858초**: [최종 집중 로그](../../evidence/integration/model-provenance-api-focused-final-20261017.log).
- 관련 최종 **56 PASS / 17.124초**: [관련 로그](../../evidence/integration/model-provenance-api-related-20261017.log). 신규 9개는 관련 묶음에 포함된다. 전체 회귀·독립 검토·실제 GET·보존은 Root의 최종 근거로 구분한다.
- 다섯 상태 exact body/키·네 bool false, get1/put0·raw SQLite 원문 불변, 기존 모델 목록 body/headers 동등, 401/404·helper 미호출 경계를 검증했다.
- Store/helper의 OSError·ValueError·TypeError·RuntimeError·MemoryError 및 import 오류를 합성해 고정503/상세 불유출을 확인했다. 기존 HTTPException 전달은 별도 시험했다.
- artifact open·digest·register·Store.put을 막고 outbound connection 생성도 금지한 채 GET이 정상 동작함을 확인했다. DB 읽기와 시험 fixture 생성은 이 차단 범위 밖이다.

최초 집중 시험은 `socket.socket` 클래스를 mock해 Windows TestClient의 내부 event-loop socketpair 생성까지 막아 8개 통과/1개 실패했다. [초기 로그](../../evidence/integration/model-provenance-api-focused-20261017.log)를 보존했다. context를 먼저 시작한 중간 재실행에서도 클래스 mock이 Windows loop의 isinstance 검사를 깨뜨려 중지했으며 [중간 로그](../../evidence/integration/model-provenance-api-focused-corrected-20261017.log)를 보존했다. 소유한 시험 프로세스를 확인해 종료했고 제품 코드는 바꾸지 않았다. 시험 guard를 `socket.create_connection` 차단으로 바꿔 TestClient 내부 이벤트 처리와 outbound 연결을 구분한 최종 9개 통과만 성공 수치로 사용한다.

## UI 인계와 남은 범위

UI 담당에게 GET·200의 다섯 상태·exact10와 고정 issue/binding, 401/404/503, 권위·실파일·실행·과학 검증 false의 의미를 인계한다. 화면에 단순한 성공/승인 badge로 바꾸지 않아야 한다. 응답의 관측값은 파일 검증·새 모델 등록·기존 모델 상태 변경이 아니다.

화면 연결·프론트 시험·브라우저 관측은 UI 담당 및 Root의 별도 작업으로 보고한다. 이번 API 격리 시험을 실제 화면 적용으로 표시하지 않는다. 원본 데이터·원장/lock·예약·분할·모델 보존과 실제 catalog 조회 후 불변 여부는 Root의 보존 근거를 따른다.

## Root 통합 최종 검증

## 22:18 KST — 읽기 전용 등록 선언 관측 API·수동 UI 연결 검증 완료 (101/102)

- **API 담당:** 새GET은100helper exact10/5상태200을그대로반환하고 기존auth/404를유지한다. Store.get1회와metadata비교만하며그외예외는원문/경로없는고정503이다. 관련56 PASS/17.124초·독립9 PASS/2.156초다. 초기socket.socket class모킹이Windows시험실행기까지막은실패/중지로그를보존하고,제품변경없이guard만socket.create_connection차단으로바꾼최종focused9 PASS를사용한다.
- **UI 담당:** ModelReview의선택모델아래수동조회전용component를연결했다. 기본자동조회/자동실행없이버튼GET만하며선택변경·route/back/unmount세대보호와동시조회방어를적용했다. exactshape/상태-binding-issue정합·4false를검사하고잘못된응답/오류시이전표시를폐기한다. 관련19/독립19·전체172 PASS, build93 modules/28.54초다. Python100helper15사례교차는19시험안의근거이며별도합산하지않는다.
- **Root 실제 API·브라우저:** direct8002와proxy5174각기존모델200ABSENT/없는모델404를확인했다. 실제화면8체크·수동조회2회·ABSENT/3NOT_CHECKED·선택해제/재선택/뒤로가기정상·양SVG·제목겹침/가로넘침0,시험시작이후수집된최근20warn/error중새오류0이다. 기존선택모델은Draft/독립평가미완료·전이/배포disabled를유지했다. 다른관측상태/auth/503/오염응답/지연동시성은격리합성시험만이다. 실제back은완료응답후복귀이며서버취소증거가아니다.
- **Root 전체·보존:** backend 1019건/1018 PASS/기존Windows symlink 1 SKIP/381.288초/exit0. 보호141·core+10071·기존증거/카탈로그14·기존Job본문변경0,기존제품변경은사전허용main.py/ModelReview.tsx뿐이다. 원본·원장/lock·예약136314880B·분할·모델보존,운영등록/역채움·Job/Workflow·수집/새운영QA/정식학습/배포0이다. 기존QA차단4/학습BLOCKED는유지한다.
- **문서·이해자료:** 신규101/102·관련07/08/100·원장/소유권/인계서를갱신했다. understanding_agent는완료코드와실제·합성근거를읽고쉬운설명·이론·코드데이터·시험·발표대본/FAQ·INDEX·변경이력을갱신했다. 최종감사/rawSHA snapshot은model-provenance-api-closeout-20261017.json을따른다.
- **한계·다음:** 관측4false는이진단의미검증범위이며기존모델필드를false로변경/확정하지않는다. 응답에모델IDwrapper가없어client세대는표시방어이지서버응답신원인증이아니다. 새endpoint는artifact읽기0이나모델선택시기존readiness GET의checkpoint검증은유지한다. caller선언·shape/source·hash값일치는권위/실바이트/과학·실행승인이아니다. 다음은Workflow model_ref와등록관측의읽기전용계약검토(PLANNED)이며resolver/실행승인미구현이다. 전체개발미완료·지속개발/10분보고유지,예약ACTIVE와실제worker상태를구분한다.

근거: `evidence/integration/model-provenance-api-live-integrity-20261017.json`, `evidence/integration/model-provenance-api-live-api-20261017.json`, `evidence/integration/model-provenance-api-live-ui-20261017.json`, `evidence/integration/model-provenance-ui-desktop-20261017.png`.


## 103 별도 내부 identity 비교 후속

[명시 identity 대조](103_model_reference_record_comparison.md)는전체GMAIS model_ref가아닌명시추출exact3 id/version/sha256와호출자가제공한레코드만비교한다. 역할/URI·전체Job검증이나record선택/Registry조회는수행하지않는다. 같은id의100관측이일치미검증인때만버전/SHA를비교하고최고상태도MATCH_UNVERIFIED·권위/실바이트/과학/실행/model_verifiedfalse다. None은RECORD_NOT_PROVIDED이며실DBNotFound조회와다르다. 기존Workflow89·94/등록/관측API/UI호출은미연결·기존출력/falseflags불변이다. [합성시험·보존근거](../../evidence/integration/model-reference-record-live-integrity-20261017.json)를따르며이번전체/frontend/build/browser재시험은없다.
