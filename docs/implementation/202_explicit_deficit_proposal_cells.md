# 202 — 부족 주·연도 선택을 명시하는 로컬 공간 제안

상태: TESTED_SYNTHETIC. 운영 제안 생성·수집·전체 지원범위 검사는 아직 수행하지 않았다.

## 필요한 이유와 변경

197에서 남동2021·고론2022의 기본 수집 위치는 모두 정산됐지만 기존182 제안의 기본 연도에는 두 셀이 없음을 확인했다. 다른 연도의 제안을 재해석하지 않고 `propose(..., targets=[(province, year), ...])` 또는 반복 CLI `--target southeast_sulawesi:2021 --target gorontalo:2022`로 대상과 우선순위를 명시한다.

기존 `TARGETS`와 인자 생략 시 후보·출력은 유지한다. 명시 입력에만 `requested_targets`를 출력한다. 공식6주·정수2020~2025·서로 다른1~6셀을 입력 읽기 전에 검증한다. bool·문자열 연도·중복·알 수 없는 주는 거부한다. 최대4후보·주당2후보·1024창·고정split·동일 공간의 연도간 겹침 방지·지문·입력/출력 제한은 유지한다. 셀 목록의 순서로 첫 회차를 돌고 기존 두 번째 회차도 동일 순서로 처리한다.

## 계약과 사용법

기존 필수 source/boundary/config/prior-plan의 절대 DATA/config 경로와 각각의 SHA, 새 DATA output 인자는 그대로 필요하다. 명시 목록은 source 고정 시점의 부족량만 사용하며 부족이 없는 셀은 제안하지 않는다. 원본/원장/예약을 변경하지 않는다. 후보는 여전히 `collector_consumption_approved=false`, `full_pending_support_inventory_verified=false`, `training_ready=false`다. 199의 후속 검토나 실제 집행 승인을 대신하지 않는다. 원격 품질과 나지 존재도 보장하지 않는다.

## 검증 근거

`PYTHONPATH=.runtime;backend;scripts` 환경에서 `python -m unittest discover -s tests -p test_propose_deficit_centers182.py -v` 결과 **12 PASS / 11.581초**. 기존9시험과 신규3시험을 실행했다. 명시 남동2021→고론2022 순서·연도, 명시 기본 목록과 기존 출력의 완전 동등(추가 요청 목록 제외), 잘못된 입력의 파일 읽기 전 거부를 확인했다. 실제 작은 임시 GeoTIFF와 합성 경계만 사용했다. 운영 HTTP·제안 생성·collector 실행·native 감사는0이다.

로그: `evidence/integration/center202-explicit-target-tests-20261018.log`. 최초 `tests.test_...` 모듈 방식은 tests 패키지가 없어 import 실패했으며 discover 방식으로 바로잡았다. 이 실패를 제품 동작 실패나 통과 건수로 세지 않는다. 기존 affine PendingDeprecationWarning은 별도로 남는다.

## 인계와 화면

Root는 producer와 시험·본 문서를 소유한다. ml_pipeline의199 가드 파일이나 실제 수집기와 동시 편집하지 않는다. 운영 제안 생성은 현재 실행/감사 종료 후 고정 원본에서 별도 수행해야 한다. 내부 CLI/Python 계약이므로 API/UI 변경은 필요 없다. 이후 실제 확보 수량과 QA 결과의 화면 반영은 별도 검증한다. 별도 이해 담당에게 이 완료 코드·시험·제한을 전달해 설명/대본/FAQ/INDEX/변경 이력을 마감한다.

## 별도 실제제안·205 소비 전 검토 후속

202시험단계의운영미실행은당시사실로보존한다. 이후Root의[204 실제제안](204_fresh_deficit_centers.md)은남동2024/2021→고론2025/2022에서새4후보를만들었다. 그중남동두곳은[205 실제검토](205_fresh_southeast_guard_review.md)에서129.516초·fullsupport1회/1,254assets·physical1,668+32≤3,000을확인했다. 로컬조건통과와 `COORDINATOR_NOT_CONNECTED`를구분하며실B02/품질/수집/예약/정산0이다. producer/시험소스는이문서후속기록때문에변경하지않았다.
