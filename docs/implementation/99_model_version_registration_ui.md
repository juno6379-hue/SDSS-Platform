# 99. Draft 등록 UI의 선택적 모델 버전 선언

상태: **TESTED_SYNTHETIC** — adapter·비동기 생명주기 시험은 mock 응답과 실제 Python 공통 문자 계약으로 검증했다. 운영 성공 등록·실제 학습·승인·배포를 실행한 증거가 아니다. 실제 브라우저의 기본값·편집·안전한 오류·레이아웃 관측은 Root의 별도 증거로 구분한다.

## 사용자 흐름과 계약

기존 ModelReview의 ‘실제 완료 실험 보고서로 Draft 등록’ 안에 기본 해제된 ‘모델 버전 선언 추가 (선택)’와 빈 ‘명시할 모델 버전’ 입력을 연결했다. 등록 버튼은 기존 수동 버튼 한 개이며 공통 `Icon`의 SVG clipboard를 쓴다. 옵션 해제 시 저장된 입력이 있어도 POST body는 기존 `{report_path}` 그대로다. 선택 시에만 `{report_path, model_version}`으로 입력 원문을 보낸다. 경로·버전을 trim하거나 dataset_version·파일명으로 추정·자동 채움·자동 POST하지 않는다.

기존 `/api/models/register-experiment`와 인증·201/422 처리를 사용한다. 서버의 등록 lock·파일/SHA/출처 검증·같은 model ID 또는 dataset ID의 중복 거부·Draft/독립평가 제한은 UI에서 우회하지 않는다. 새 최상위 model_version을 만들거나 서버 모델 객체를 수정하지 않는다. 모델 원본 JSON에 보이는 nested model_version_declaration도 source/shape만으로 기관 권위·원본 인증·명시 API 호출 이력을 입증하지 않는다. 서버의 선언 보존은 [97](97_model_version_declaration.md)을 따른다.

선택한 버전은 Python `_text`와 같은 Unicode code point 1~256자, 비어 있지 않은 문자, ASCII/C1 제어문자·단독 surrogate 제외 조건을 검사한다. Python strip 집합으로 가장자리 공백을 검사해 대소문자 무관 latest/current를 차단한다. 이 검사용 strip은 전송 값을 바꾸지 않는다. 예를 들어 ` v1 `은 그대로 전송하고, ` CURRENT `는 등록 버튼을 비활성화한다. 보충 평면 문자 256개와 257개, Python/JavaScript의 U+FEFF 차이도 교차 시험했다. 클라이언트 검사는 편집 안내이며 서버 검증을 대체하지 않는다.

## 비동기 결과와 화면 이동

등록 중 보고서 경로·버전 선택·버전 입력·모델 선택을 비활성화한다. React busy 렌더 전 연속 호출은 synchronous in-flight로 막는다. popstate/hashchange·unmount는 generation을 폐기하므로 다른 화면이나 돌아온 폼에 늦은 성공 모델 선택·오류·busy 해제를 붙이지 않는다. 모델 목록 props 전체를 요청 동일성으로 쓰지 않아 자신의 정상 onChanged 갱신을 잘못 폐기하지 않는다. 기존 평가·상태 전이·배포 run 회로는 유지한다.

서버 성공 응답 뒤에는 화면을 떠났어도 onChanged로 목록을 갱신한다. UI 응답 폐기는 서버 취소·rollback이 아니다. 성공 응답 뒤 목록 갱신/화면 반영이 실패하면 ‘서버 등록 응답은 성공했으나 … 등록을 반복하지 말고 목록을 확인하세요’로 안내한다. 자동 재등록하지 않는다. 서버의 두 쓰기 사이 실패·동시 등록·트랜잭션 한계는 기존 동작이며 이 UI가 해결하지 않는다.

## 코드와 시험 증거

- [ModelReview](../../frontend/src/ModelReview.tsx): 기존 등록 폼과 원본 JSON 유지, 선택형 입력·등록 lifecycle 연결.
- [Adapter](../../frontend/src/modelVersionRegistrationAdapter.ts): body·문자 검사·등록 요청 generation·성공 후 refresh 경계.
- [시험](../../frontend/src/modelVersionRegistrationAdapter.test.mjs): 신규 16 PASS, 856.2352ms. omitted exact body/explicit null/원문 보존/Unicode 교차/동시 요청/422/정상 mock/route·back-forward·unmount/refresh 실패를 검증했다. mock 선언·해시는 실제 checkpoint 검증 근거가 아니다.
- [관련 로그](../../evidence/integration/model-version-ui-related-20261017.log), [프론트 전체 로그](../../evidence/integration/model-version-ui-tests-20261017.log): 전체 153 PASS, 6663.9031ms.
- [빌드 로그](../../evidence/integration/model-version-ui-build-20261017.log): tsc 및 Vite 빌드 성공(exit 0), 89 modules/25.41초. 기존 500kB chunk 경고는 남아 있다. 실제 브라우저 관측은 Root가 확인해 인계한다. 테스트 코드 반영과 실행 서버 적용을 구분한다.

새 옵션은 caller 메타데이터 선언이다. 기관 권위·과학 정확도·독립 평가·실행 승인·전역 불변 모델 등록으로 표시하지 않는다. 운영 카탈로그에 성공 등록하는 브라우저 시험은 금지 범위로 유지했다.


## 실제 화면 검토 후 간격 보정

최초 1449px 캡처에서 전역 `.help`의 음수 상단 margin 때문에 등록 summary와 첫 도움말이 겹치고, 전역 input의 block 표시 때문에 checkbox와 문구가 나뉘는 문제를 확인했다. 최초 캡처와 시험 로그는 보존했다. 새 [등록 전용 CSS](../../frontend/src/model-version-registration.css)와 해당 details의 scoped class로만 summary·도움말 간격과 checkbox 한 줄 정렬을 보정했다. 다른 전역 CSS나 기존 평가·전이 폼은 바꾸지 않았다.

보정 후 [관련 layout 로그](../../evidence/integration/model-version-ui-related-layout-20261017.log) 16 PASS/2254.1292ms, [전체 layout 로그](../../evidence/integration/model-version-ui-tests-layout-20261017.log) 153 PASS/8686.1211ms. [layout 빌드 로그](../../evidence/integration/model-version-ui-build-layout-20261017.log)는 tsc·Vite 성공(exit 0), 90 modules/27.52초다. 기존 500kB chunk 경고는 유지한다. Root의 최종 reload/브라우저 관측은 별도 확인한다. 편집 중 import와 새 CSS 생성 사이 일시적인 HMR 오류는 최종 적용 여부와 구분해 기록한다.

## Root 최종 실제 브라우저 확인

[실제 UI 근거](../../evidence/integration/model-version-api-live-ui-20261017.json)의 8개 체크를 통과했다. 기본 off/빈값, opt-in 빈 버전과 latest 차단, 패딩 원문 보존, 없는 보고서1회422와 입력 재활성화, 옵션해제, 완료422 뒤 메뉴이동·뒤로가기 정상복귀를 확인했다. 최종 reload 뒤 가로넘침0·SVG·summary/help 약12px 간격·겹침없음을 [최종 화면](../../evidence/integration/model-version-ui-desktop-final-20261017.png)으로 확인했다. 최종 폼은 빈값/off다. 편집중 HMR오류1건을 기록했고 새CSS가 존재한 뒤 reload에서 정상회복했다. 과거 console오류0으로 표현하지 않는다.

[실제 API 근거](../../evidence/integration/model-version-api-live-api-20261017.json)는 없는 보고서4회422와 catalog14 동일만 검증한다. 파일오류가 버전검사보다 앞서므로 버전분기의 성공 증거가 아니다. 성공등록·지연응답/중복동시성·refresh실패는 격리 TempStore/AST/mock 시험만 TESTED_SYNTHETIC이며 운영 성공등록0이다. 실제 back은 완료된422 후의 복귀이지 진행중 서버취소 증거가 아니다.

최종 layout 빌드 모듈 수는 실제 로그의 **90 modules**로 정정했다. 초기 빌드89와 구분하며 새 CSS 추가가 반영된 최종 로그를 근거로 사용한다.

## 100 내부 관측 후속

[순수등록선언관측](100_model_registration_provenance_observation.md)은 저장된 metadata의 부재·형식·충돌·근거부족·일치미인증을구분한다. API/UI·등록/승인gate에미연결이며 기존출처검증이나등록동작을대체하지않는다. 동일shape/source의raw복사위조도일치할수있으므로기관권위·실제바이트·과학/실행승인으로해석하지않는다. 이전모델필드도수정하지않는다. [관련/독립시험·보존](../../evidence/integration/model-provenance-live-integrity-20261017.json)과 [실제읽기관측](../../evidence/integration/model-provenance-catalog-observation-20261017.json)을참조한다. 전체회귀와프론트/build/브라우저는이번재실행하지않았고이전증거와구분한다.
