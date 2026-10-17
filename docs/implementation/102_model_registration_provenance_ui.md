# 102. 선택 모델의 등록 선언 관측 UI

상태: **TESTED_SYNTHETIC** — 신규 adapter·비동기 생명주기·Python helper 교차 시험을 완료했다. 실제 브라우저와 운영 API의 읽기 결과는 Root의 별도 관측 근거로 구분한다. 운영 성공 등록·역채움·학습·승인·배포는 이 기능에 포함되지 않는다.

## 사용자 흐름과 연결

등록 모델을 선택하면 기존 ModelReview 안에 전용 ‘모델 등록 선언 관측’ 패널을 표시한다. 선택하지 않았으면 패널도 표시하지 않는다. 패널 열기·모델 선택·렌더만으로 조회하지 않고 ‘등록 선언 관측 조회’ 버튼을 클릭할 때만 기존 인증을 쓰는 `GET /api/models/{id}/registration-provenance`를 호출한다. 모델 ID는 URL encode하며 요청 body는 없다. 기존 api.ts·등록 adapter·등록/평가/승인/readiness 흐름은 바꾸지 않았다.

[ModelReview](../../frontend/src/ModelReview.tsx)는 import와 선택 모델 하위의 keyed component만 추가했다. [전용 component](../../frontend/src/ModelRegistrationProvenance.tsx)·[adapter](../../frontend/src/modelRegistrationProvenanceAdapter.ts)·[전용 CSS](../../frontend/src/model-registration-provenance.css)를 분리했다. SVG는 기존 공통 Icon을 사용한다. 제목/도움말 간격과 버튼·관계표는 처음부터 scoped CSS로 지정해 전역 `.help` 음수 margin의 영향을 피한다.

## 응답 검증과 표시 의미

200 응답은 [100의 순수 helper](100_model_registration_provenance_observation.md)가 반환하는 exact 10키 객체다. 3개 binding의 exact 키/문자 타입, 4개의 정확한 bool false, schema/scope, 5상태와 issue의 fixed code/field를 검사한다. 응답 원문에 임의 값·추가 키·알 수 없는 코드가 섞이면 안전한 오류만 표시한다.

| 상태 | 화면 설명 | 검증 경계 |
|---|---|---|
| ABSENT | 등록 선언 없음 | present false, 세 관계 NOT_CHECKED, issue null |
| INVALID | 등록 선언 형식 확인 필요 | 모두 NOT_CHECKED, 허용 code/field. RECORD_INVALID만 present null이며 id 오류 외의 선언 오류는 present true |
| RECORD_CONFLICT | 레코드 선언 충돌 | present true, 실제 불일치가 존재하며 checkpoint→report→version 첫 불일치 issue |
| PARENT_BINDING_UNKNOWN | 부모 해시 근거 부족 | 불일치 없음, 부모 해시 MISSING 존재, checkpoint→report 첫 누락 issue |
| CONSISTENT_UNVERIFIED | 메타데이터 일치 · 인증 미검증 | 부모 두 hash MATCH, version MATCH 또는 NOT_RECORDED, issue null |

관계는 ‘검사하지 않음/메타데이터 일치/메타데이터 불일치/부모 해시 없음/선택 버전 기록 없음’으로 표시한다. 오류 code/field는 검증한 고정 문자열만 표시하며 선언 원문·경로·hash를 응답에서 추출해 노출하지 않는다. 401/403·404·503/기타 전송 오류도 raw 서버 메시지를 출력하지 않고 고정 한국어 안내로 변환한다.

기관 권위·실제 파일 바이트·실행 승인·과학 정확도는 **이 진단에서 항상 미검증**이다. 이는 기존 모델 레코드의 네 승인 필드 값을 false로 판정하거나 수정한 결과가 아니다. 레코드 메타데이터가 일치하더라도 원본 인증·실파일 재검증·명시 API 호출의 진정성·기관 권위·과학 또는 실행 승인이 되지 않는다.

## 선택과 늦은 응답 방어

새 수동 조회를 시작할 때 이전 결과와 오류를 먼저 제거한다. 모델 변경은 `key={id}`로 이전 component를 폐기하고 새 component에서 빈 상태를 시작한다. 별도 flight의 동기 pending은 React busy 렌더 전 이중 클릭도 GET 1회로 제한한다. 요청의 모델 ID·화면 hash·generation을 함께 고정하고 선택 변경·popstate/hashchange·unmount 이후 도착한 결과/오류/busy 해제는 버린다. 서버 읽기 실패나 응답 형식 오염 뒤 이전 성공 결과를 재사용하지 않는다.

응답에는 모델 ID wrapper가 없다. 이 client 검사는 잘못된 화면에 늦은 결과를 붙이지 않기 위한 표시 방어이며 서버 응답의 모델 신원을 인증하는 계약이 아니다. 화면 이동이 이미 보낸 서버 읽기를 취소한다는 의미도 아니다. 모델 목록 갱신만으로 자동 재조회하지 않는다.

## 시험 근거

[신규 시험](../../frontend/src/modelRegistrationProvenanceAdapter.test.mjs) **19 PASS / 705.4679ms**: exact 10/3키·4false·stage별 presence/issue/binding·충돌/부재 우선순위·문자 coercion 거부·실제 Python100 15개 입력/5상태 교차·수동 GET 1회·선택/route/back/unmount stale·오염 응답·안전한 HTTP 안내를 검증했다. 비동기 성공/지연/실패는 mock 시험이며 운영 모델을 바꾼 증거가 아니다.

- [관련 로그](../../evidence/integration/model-provenance-ui-related-20261017.log)
- [전체 프론트 로그](../../evidence/integration/model-provenance-ui-tests-20261017.log): **172 PASS / 7657.7741ms**.
- [빌드 로그](../../evidence/integration/model-provenance-ui-build-20261017.log): tsc·Vite 성공(exit 0), **93 modules / 28.54초**. 기존 500kB chunk 경고는 유지한다.

실제 서버 적용·브라우저 수동 조회·가로 넘침/간격 관측은 Root가 별도 근거로 보충한다. 시험 코드의 성공을 운영 UI 적용으로 표현하지 않는다.

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
