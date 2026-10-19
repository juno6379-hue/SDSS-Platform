# 242 manifest profile 시험 배치 이동성 보완

상태: TEST_ONLY_IMPLEMENTATION / TESTED_SYNTHETIC. 제품237 runtime18개를 변경하지 않았다. 228/230/237 동결판도 보존했다. 이 담당의 main 쓰기·운영data/원장/model 읽기·복사·HTTP·collector·운영QA는0이다.

## 쉬운 설명

기존 시험은 격리 개발 폴더 옆의 이전 workspace와 baseline-code 디렉터리를 찾았다. 코드를 main tests에 옮기면 그 이웃 폴더가 없어져 시험이 깨질 수 있었다.242는 시험에 실제로 필요한 구 코드4개만 tests/fixtures에 넣어 경로와 SHA를 고정한다. 현재 제품 코드를 대신 정답으로 쓰거나 기준 파일이 없을 때 통과시키지 않는다.

## 소유·변경

수정 대상은 test_manifest_profile228.py와 test_manifest_profile237.py의 기준 코드 로딩뿐이다. test_manifest_profile230.py는 외부 baseline 경로가 없어 원바이트를 유지했다. 신규 `tests/manifest_profile_baseline_fixtures.py`, 고정 fixture4개·manifest, 포장회귀 test_manifest_profile242_portability.py를 추가했다. backend/scripts/runtime18개는237과 exact SHA가 같다.

| 기준 코드 | 역사 원본 | SHA256 |
|---|---|---|
| candidate_materialization_pre228.py |228 baseline-code의 pre228 materialization|6caec21389aa68472a50097f6f5d70d1554f17a8cda67b85e9d1e21f8a32f37b|
| candidate_qa_comparison_pre228.py |228 baseline-code의 pre228 comparison|7c472e37a5df7a56a6935adeff991a966d90ce9fd4337c3326777b00be57f18e|
| centers230.py |동결230 propose_deficit_centers182.py|c67e868ac693d62f5384c84c173d6e9fea7a221f56df8bade9140eca4be09f8d|
| status230.py |동결230 collection_status.py|bacd9f17a1b256b51752e639a02458f623286506aba2bc59664f3153513ddce4|

원코드는 가공하지 않고 원바이트 복사했다. full baseline 디렉터리나 운영 데이터를 복사하지 않았다. 자세한 source/provenance/bytes는 tests/fixtures/manifest_profile_baselines/manifest.json에 있다.

## 로더·오류 계약

로더는 자신의 __file__에서 tests/fixtures/manifest_profile_baselines 경로를 결정한다. 고정 manifest SHA와 선택한 코드 SHA를 모두 검산한 뒤 기존 package 문맥으로 코드를 로딩한다. historical script가 sys.path를 바꾸더라도 finally에서 원래 목록으로 복구한다. mutable 현재 제품 파일, 부모230 workspace, 환경 변수나 cwd에 따른 fallback은 없다.

fixture 누락은 FileNotFoundError로 실패하고, 코드/manifest 변조는 AssertionError로 실패한다. skip·누락시pass·없는 기준의 재생성은 하지 않는다. 포장시험4개가 정확한 pin/provenance, 누락, 변조, sys.path 복구를 검증한다.

## 두 배치 검증

1. 새 격리 preprocess242-test-workspace에서3개 profile 시험과 포장4개,182/status/priority/budget 관련 회귀를 실행했다.93 PASS /30.768초다.
2. 같은 고정 code/config/tests만 별도 shared-layout242/project에 배치한다. 그 project에는 baseline-code가 없고, ROOT.parent/preprocess230-workspace도 없으며 조상 이름에도230 workspace가 없다. 따라서 과거 이웃 경로로 몰래 통과하는 조건이 없다. 같은93개가48.384초에 모두 통과했다. 최종 log SHA는 freeze242에 고정한다.

두 배치 모두 runtime18개와 test230 SHA를 따로 검산한다. data/evidence는 시험용 빈 디렉터리로 시작하고 Temp 합성 파일만 생성한다. 기존173 standalone의214 archive 비교는 이번 변경 범위가 아니므로 재실행 목록에서 제외했고,173 profile 소비·CLI 연결은3개 profile 시험에 포함된다. 제품237의 기존109 결과를242 새93과 합산하지 않는다. 추가128MiB 부하·실제 rich3000행 QA·수집은 실행하지 않는다.

## 반영 구분과 인계

Root는 제품18개를237 동결판 기준으로 별도 적용·검증할 수 있다.242 patch는 시험 전용이며 runtime 변경이 없다. main 시험 bundle은3개 profile 시험(그중230은 원바이트)+고정 로더+fixture4개/manifest+포장시험을 함께 복사해야 한다. 테스트만 옮기고 fixture를 생략하면 정상적으로 실패한다. 전체242 디렉터리 복사는 하지 않는다.

UI/API 동작 변경은 없다. 시험 배치 보완이며 실제 서버/브라우저/운영QA 적용의 성공을 의미하지 않는다. 완료 시험·고정 파일 목록·상한·한계를 Root와 이해 담당에게 인계해 기존 시험 포장 BLOCKED와 제품237 검토 결과를 구분한다. 최종242 freeze는 별도이며237/230/228 freeze나 고정 문서를 수정하지 않는다.

최종 결과는 격리93 PASS/30.768초와 shared-layout93 PASS/48.384초다. 같은 회귀 집합을 두 위치에서 검증한 것이므로186개의 서로 다른 요구조건으로 합산하지 않는다. 실행 뒤에도 두 배치 runtime18개와 test230이237 SHA 그대로임을 재검산했다.

이 이동성 검증은 기준 코드와 프로젝트 배치 경로의 독립성이다. Python 의존 라이브러리는 기존 .runtime 환경을 사용했고 새 의존성 배포나 다른 컴퓨터의 환경 설치까지 검증한 것은 아니다.
