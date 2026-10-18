# 168 — 패치 품질과 분할 집계 클래스 균형의 범위 표시

상태: **IMPLEMENTED_UNVERIFIED(실브라우저 연결 복구 후 최종 표시 확인 필요)** / **TESTED_SYNTHETIC — 집중9 PASS**. 실제 자료 재분류·QA정책 변경이 아니다.

## 문제와 변경

165의 실제6차24패치 검사에서3패치의 최대 클래스 비중이90%를 넘는 것을 관측했다. 그러나 기존 `collect_training_grid.materialize_patches`의 개별 패치 `quality_eligible`는 유효80%·주 내부95% 판정이다. `collect_training_parallel.balanced_coverage` 및 ML `readiness._class_balance`의 최대 단일 클래스90%는 **학습 후보 분할(split) 전체의 집계** 기준이다. 개별 순림 패치를90% 때문에 자동 제외하는 기준이 아니다.3개는 원래 적격 상태 그대로이며 원본/분할/라벨을 수정하지 않는다.

기존 CollectionProgress 정책 문장이80/95/90을 모두 '패치 기준'으로 묶어 범위가 혼동될 수 있었다. `frontend/src/CollectionProgress.tsx`의 한 문장만 다음처럼 명확히 했다.

> 패치 기준: 유효 비율 ≥ 80% · 주 경계 내부 ≥ 95%. 학습 후보의 분할(split) 집계 기준: 최대 단일 클래스 비중 ≤ 90%. 개별 순림 패치의 클래스 비율만으로 자동 탈락시키지 않습니다.

실제 화면 숫자는 계속 기존 API 응답의 정책 값을 쓰며80/95/90을 새 하드코딩하지 않았다. 원본 현황의 `quality_status`는 저장 집계이고 즉석 native 재QA 결과가 아니라는 설명도 유지했다. 등록/학습/평가/승인/수집·API 동선과 숫자 계산은 변경하지 않았다. 다른 Toolbox/App/main/API/공통 CSS는 편집하지 않았다.

## 검증·보존

원 component/test를 `priority168-original-CollectionProgress.tsx`, `priority168-original-collectionProgressAdapter.test.mjs`로 원바이트 복사·SHA 대조했다. component는1행 문구 변경이고 기존 adapter시험에는 별도 범위 문구 검증1건을 추가했다. 종전8개 시험의 응답 집계·후보 분리·flags/타입·stream·stale·인증·실API GET 재사용 검증도 그대로다.

`priority168-focused-20261018.log`: 초기 **9 PASS/0 SKIP/2.956097초**. `priority168-build-20261018.log`: **123 modules/1분20초/exit0**, 기존 대용량 chunk 경고가 있어 성능 SLA를 인증하지 않는다. 이 빌드는 다른 담당 Toolbox가 포함된 공동 작업공간 범위이며154의 격리120modules 빌드와 다른 실행이다. 시험 파일의 기존 LF 형식을 유지한 뒤 최종 `priority168-focused-final-20261018.log`에서도 **9 PASS/0 SKIP/1.2915933초**를 확인했다. 문구/실행 소스는 초기 집중 이후 그대로다. 단순 문구/시험 변경으로 전체 backend나 수집을 재실행하지 않았다.

실제 브라우저 확인은 전용 Chrome 탭 생성30초 timeout 후 연결 자체가 없어 현재 차단됐다. `cua.listTabs(browser1)`은 Browser unavailable, 이어 `cua.getState()`는 apps[]/browsers[]였다. 이는 아직 수정 문구가 실화면에서 보였다는 증거가 아니다. 사용자 창을 강제로 열거나 native 도구로 우회하지 않았다. 기존154의 실제 화면 증거는 수정 전 문구의 이력으로만 남기고, 연결 복구 후 실제5174→기존API GET에서 새 문구·범위·줄바꿈/넘침을 확인할 후속을 Root에 인계한다.

UI 소스/시험 핀과 이 차단은 `priority168-freeze-20261018.json`에 기록한다. Root/이해 담당이 정책의 수준(패치 대 split 집계)과 실브라우저 미완료 범위를 공통 자료에 반영하도록 전달한다. 자료/원장/예약/모델 쓰기0이며 기존 QA 규칙을 완화하지 않았다.

## Root의 실제 브라우저 확인 완료

앞선 Chrome 연결 실패는 당시 시도의 이력이다. 이후 Root가 별도 숨김 IAB 탭에서 실제5174 화면과 기존 API 응답을 확인했다. `priority168-root-browser-20261018.json` 및 최종 `priority170-final-ui-20261018.json/txt/png`에 새 split 집계90% 문구와 개별 순림 패치 자동 탈락 방지 설명이 실제 렌더링됐음을 기록했다. 최종 관측02:38:58UTC: 원본1569물리/1260적격·셀 부족54, 고정후보1219·차단3·미준비·원본SHA불일치, 콘솔 경고/오류0·화면가로폭1265=scrollWidth1265다. 당시 원본 나지 수치는 저장 선언 집계이며 독립 native 검사 결과와 구분한다. 학습·등록·배포 버튼은 실행하지 않았다.

추가로 공개기준8cf7b94의 frontend를 별도 디렉터리에 내보내고168 소유 component/test 두 파일만 덮어써 다른 채팅 Toolbox WIP를 제외했다(`priority170-isolated-frontend-20261018.json`). 해당 범위의 집중9시험 PASS/0SKIP/1.894초와 **120 modules/build39.58초/exit0**를 확인했다. 기존 큰 chunk 경고는 남아 있다. 최초 내보내기 명령은 파일 준비를 마친 뒤 CP949 터미널 경로 출력에서 UnicodeEncodeError가 났으므로 재내보내기로 덮어쓰지 않고 준비된 지문/파일을 확인해 시험했다. UI 전체 회귀나 성능 SLA 통과로 확대하지 않는다.
