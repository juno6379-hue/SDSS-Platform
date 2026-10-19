# 186 — 고론탈로·서자바 나지 공백 보완용 128픽셀 간격 로컬 탐색

상태: **TESTED_SYNTHETIC / 운영 실행은 미실시**. 179 고정50후보에서 고론탈로·서자바의 과거지원 겹침 없는 후보가0이어서, 같은 로컬 약한 라벨을 128픽셀 간격으로 다시 살펴볼 수 있도록 했다. 새 후보의 실제 발견·겹침 없음·수집·품질 승인은 아직 확인하지 않았다. 기존50 proposal/report와 그 SHA는 덮어쓰지 않는다.

## 변경과 기본 동작 보존

`scripts/find_bare_targets173.py`의 `discover(..., window_stride=256, provinces=None)`에 두 선택 인자를 추가했다. 인자를 생략하면 기존처럼 256×256 창을256픽셀 간격으로 찾으며 기존 기본 proposal에 새로운 stride/scope 필드를 넣지 않는다. CLI도 기본값256을 유지한다.

선택 `window_stride=128`은 **창 크기256을 유지하고 이동 간격만128**로 한다. `provinces=['gorontalo','west_java']`처럼 기존6주 고정 이름만 중복 없이 선택한다. 임의 주·빈 선택·중복·문자열 대신 잘못된 목록·bool/64/512 등 간격은 거부한다. 전체 원본의3000행 제한과6주 경계·연도 유효성은 필터를 써도 유지한다.

선택 탐색 결과에는 `window_stride`와 `province_filter`가 명시된다. 128픽셀 간격이면 전체 주를 선택했어도 해당 scope 목록을 넣는다. 179 검토기는 명시된128/256 중 정확한 간격의 좌표만 허용한다. stride 필드가 없는 과거 proposal은256으로 취급한다. 128인데 scope가 없거나, 후보 주가 scope 밖이면 차단한다. 179의 실제 라벨 SHA·동년 lineage·256창·나지·경계·과거 및 상호 겹침 검사는 그대로다.

6주 범용 최종 수집기는175/176/170의 별도 가드를 통과해야 한다. 신규 선택 탐색의 `consumer_scope`는 `SIX_PROVINCE_175_176_REVALIDATION_REQUIRED`로 명시한다. 기존173 기본 proposal의 역사적 `consumer_scope` 문구는 그대로 보존하지만 새 집행 권한을 주지 않으며, offset 탐색 성공 역시 수집 승인이 아니다.

## 한도와 품질 기준

- 단일 정수 band·10m **미터 단위** 투영격자, 같은 연도 ESRI raw 라벨 SHA, native256×256, 주 경계 안쪽 면적95% 이상, 코드8 나지256픽셀 이상을 유지한다.
- 최대32768창·128개 순위 후보·768MiB 전체 라벨·256라벨 파일·개별64MiB·원본3000행 한도를 유지한다. 실제 창 수를128간격으로 재계산해 초과 시 실패한다. 후보는 기존 순위 정책으로 최대128개를 반환하며 전체 발견 수와 구분한다.
- `(라벨 SHA,x,y)` 중복 제거는128에서도 같다. 겹치는128창끼리는 별도179 상호 겹침 검토 대상이며, 발견 수를 독립 패치 수로 합산하지 않는다.
- HTTP·원장·원본·잠금·모델·UI/API 변경은 없다. 모든 탐색 결과의 execution/actual_quality/science/training 플래그는 false다.

CLI 선택 옵션은 `--window-stride 128 --province gorontalo --province west_java`다. 기존 명시 source/boundary SHA·새 run-id·exclusive 출력 규칙은 유지한다. 운영 sourcecopy와 실제 탐색은 Root가 현재 수집 종료·metadata 안정 및 새 핀을 확인한 후 별도로 지시한다. 179의1193지원자산 고정 결과를 현재 운영 검토의 새 inventory 검사 대신 쓰지 않는다.

## 실제 배열을 사용한 합성 시험

임시512×256 GTiff에 나지400픽셀을 x=206~305에 배치했다. 기본256격자에서는 왼쪽200·오른쪽200으로 둘 다 기준 미달이라 후보0이다. 128간격으로 이동하면 x=128의256창에서400을 직접 계산하여 후보1을 찾는다. 이 예시는 로컬 탐색 공백 보완 가능성을 입증하며 실제 고론탈로·서자바에서 새 clear 후보를 찾았다는 증거는 아니다.

179 시험도 native x=128 창을 명시128/scope에서만 허용하고 과거256 계약에서는 거부한다. 불법stride·scope누락/범위/중복·창수한도·라벨 SHA 창 중복·기본회귀·실제 plan shape 연결을 함께 확인한다. 전체167 운영 inventory는 fixture에서 mock이며 실제 전체운영 검토를 재실행하지 않았다.

집중 **26PASS·8.107초**: [bare186-focused 로그](../../evidence/integration/bare186-focused-20261018.log). 관련167/170 포함 회귀 **59PASS·21.748초**: [bare186-related 로그](../../evidence/integration/bare186-related-20261018.log). 이후 신규 선택 mode의 consumer_scope 설명만 정정하고 **최종26PASS·18.288초**로 [최종 집중 로그](../../evidence/integration/bare186-focused-final-20261018.log)에서 재확인했다. rasterio/affine의 기존 `PendingDeprecationWarning`은 보존하며 실패로 숨기지 않는다.

## 다음 단계와 인계

Root는 현재 source·ledger·경계의 새 SHA와 업무 소유를 고정한 뒤 고론탈로·서자바 필터128 탐색을 별도 새 경로에 실행할 수 있다. 실제 후보가 생겨도 원본50과 분리하며179의 전체 support inventory·native 라벨·과거 겹침·상호 겹침·source lineage를 새로 검증한다. clear0이면 그대로 차단을 기록하고 다른 연도/새 라벨 범위가 필요하다는 근거를 남긴다. 원격 표적 수집·예산 증액·학습·등록·배포를 자동으로 실행하지 않는다.
