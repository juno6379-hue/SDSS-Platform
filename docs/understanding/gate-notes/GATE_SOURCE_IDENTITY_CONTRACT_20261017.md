# Gate Source Identity Contract 20261017 — 확인된 경로·지문의 선언 단서 전달

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/ml/readiness_connectivity_adapter.py`; `tests/test_readiness_connectivity_adapter.py`; `evidence/integration/readiness-source-identity-related-20261017.log`; `docs/implementation/64_readiness_source_identity_contract.md`; `evidence/integration/readiness-source-identity-independent-20261017.log`; `evidence/integration/readiness-source-identity-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-live-integrity-20261017.json` |
| confidence | 실제 코드·합성시험 기반; 실자료 새 보고서/원본행 인증 미검증 |
| status | TESTED_SYNTHETIC: 관련23 PASS; 기존 실자료 학습 BLOCKED; 소비자 연결 PLANNED |

## 쉬운 설명

물품 목록의 이름만으로 같은 항목을 구분하기 어려워, 이미 담당자가 확인한 보관 경로와 지문을 별도 메모칸에 전달한다. 메모를 옮기는 작업 자체가 물품을 다시 검사하거나 원본 항목을 인증하지는 않는다. 이번 변경은 그런 메모칸을 선택적 객체로 추가한 것이다.

## 이론적 배경

기존 연결 진단은 주·제품 토큰·경계 상자만으로 그룹을 관측한다. 원본행 후보를 좁히는 단서와 연결 판정의 입력을 분리하면 기존 판정 계약을 유지하면서 후속 추적을 준비할 수 있다. 선언값의 형식·존재 여부와 실제 파일의 진실성은 다른 계층이다. source_identity는 경로 정규화나 파일 읽기·해시를 하지 않는다.

## 코드·상태·데이터 동작

`capture_readiness_connectivity`는 기존 helper 관측을 마친 뒤 `_source_identity_metadata`를 별도 예외 경계에서 호출한다. 지원하지 않는 정책·메타데이터·예산 초과처럼 기존 조기 미포착 결과에는 optional 객체가 없을 수 있다. 최상위 schema_version1, projected_scene_metadata의 기존5키, helper 입력/결과와 gate 판정은 그대로다. 각 행의 scene_index/eligible_position은 원래 목록 순서이며 원본 manifest 행 인증으로 승격하지 않는다. 0patch 장면도 임의로 제외하지 않는다.

새 객체의 identity_schema_version은1이다. image_path와 image_sha256는 assess가 이미 계산한 장면 메타데이터에서 복사한 선언이다. 경로는 비어 있지 않은 UTF8 문자열·길이/제어문자, SHA는 소문자16진수64자 형식을 검사한다. 경로 해석·정규화·실제 파일 접근은 하지 않는다.

| 입력 상태 | identity_status | 해석 |
|---|---|---|
| 두 키 모두 없음 | UNKNOWN_NOT_PROVIDED | 과거/선택적 입력 부재 |
| 경로와 SHA가 형식상 유효 | DECLARED_PATH_AND_SHA256 | 선언 전달 성공, 파일 인증 아님 |
| 한 키가 없음 | PARTIAL_DECLARATION | 불완전한 단서 |
| null/잘못된 타입·형식 등 | INVALID_DECLARATION | 사용할 수 없는 선언 |

객체 coverage는 NO_SCENES / COMPLETE_DECLARED_METADATA / UNKNOWN_NOT_PROVIDED / PARTIAL_OR_INVALID_DECLARED_METADATA로 구분한다. 일부 필드가 잘못되어도 기존 연결 진단 결과를 바꾸지 않는다. 단서 생성에서 예외가 발생하면 NOT_CAPTURED_ERROR와 오류 타입을 별도 객체에 남기며 gate나 helper를 변경하지 않는다.

## 시험 증거

관련23 PASS/6.047초는 기존17+신규6개 합성시험이다. 선언 전체/부재/부분/잘못된 값·예외 격리·원본 불변과 구63 reader의 하위호환을 다룬다. 독립23 PASS/5.827초도 확인했다. 최종 전체 `scripts/test.ps1`은 **630건 중629 PASS·1 SKIP/192.060초/종료0**다. 기존 Windows symlink 생성권한 제약1개를 건너뛰었으며 deterministic 경계 시험은 통과했다. 관련23 PASS/6.047초와 독립23 PASS/5.827초는 전체630에 중복 합산하지 않는다. 보호133참조와 adapter 외24기존 계약SHA, 입력 manifest/current report 핀, 다섯 차단·패치628/233/250은 불변이다. 이전 추적 코드·데이터·시험에서 의도한 adapter와 그 시험2개만 변경됐고 readiness assess/CLI는 그대로다. 기존 실제 보고서에는 source_identity가 없는 상태를 유지하며 실자료 assess 재실행·새 실자료 보고서 생성은 없었다. 이해 에이전트는 코드와 로그만 읽었으며 시험·assess를 실행하지 않았다.

## 한계·현재 실자료 상태

실자료 assess를 다시 실행하지 않았고 새 실자료 보고서도 없다. 기존63 reader는 새 단서를 사용하지 않으므로 현재28장면 모두 AMBIGUOUS_MATCH_SET, 후보연결400·고유raw28과 exact binding false는 그대로다. 이미 기록된28명의 회원 사실과 원본행 인증을 혼동하지 않는다. 이 객체가 있다고 출처·적격성·실제 실행 코드·파일 내용·정확한 원본행을 인증하지 않는다.

기존5차단·패치1,111(628/233/250)·원본 분할·baseline Draft·terminal2missing·예약136,314,880B·환불0을 유지한다. 학습/실행/자동재개/정산/과학승인은 false다. 새 API/UI 계약 없는 내부 진단 객체 확장이므로 이번 화면 변경과 브라우저 재검사는 필요 없다. 전체 개발과10분 보고는 지속한다.

## 발표 1분

“제품 이름이 같아 원본행을 하나로 찾을 수 없는 문제를 해결할 준비로, 이미 검사 과정에서 계산한 이미지 경로와 지문을 별도 단서 객체에 전달하도록 했습니다. 이 과정에서 파일을 다시 읽지 않고 기존 연결 판정도 바꾸지 않습니다. 값이 없거나 일부만 있거나 잘못된 경우를 구분하고, 단서 생성 실패가 판정을 바꾸지 않게 격리했습니다. 아직 실제 자료를 재검사하거나 소비자가 새 단서를 사용하는 단계는 아닙니다. 따라서 현재28장면의 원본행 모호성과 다섯 학습 차단은 그대로입니다.”

## 발표 5분·10분

1. **0~1분:** 물품 이름과 보관 경로·지문 메모의 차이를 설명한다.
2. **1~2분:** 연결 판정 입력과 source identity 보조 객체를 분리한 이유를 말한다.
3. **2~3분:** 존재/부분/무효 상태와 선언 형식 검사·예외 격리를 보여준다.
4. **3~4분:** 합성시험·구63 reader 호환과 실제 재assess 미실행을 구분한다.
5. **4~5분:** 현재28모호성/5차단 보존, 다음 소비자 설계와 원본 인증 한계를 말한다.

10분 확장에서는 projected5키 유지·0patch 포함·경로 정규화false·예외 후 helper 불변·선언 SHA와 파일 해시 검증의 차이를 설명한다.

## Q&A

**원본행을 찾았나?** 아니다. 현재 보고서를 새로 만들거나 소비자가 단서를 사용하지 않았으며 전원 모호성은 그대로다.

**파일을 다시 읽었나?** 단서 객체를 만드는 adapter의 추가 IO는0이다. 과거 실제 assess의 영상·라벨 읽기까지 없었다는 뜻은 아니다.

**SHA 문자열이 있으니 인증인가?** 형식상 선언만 전달하며 실제 파일·경로·출처·원본행 진실을 인증하지 않는다.

**기존 도구가 깨지나?** 기존 schema1/projected5키·helper/gate를 유지하고 구63 reader 하위호환을 합성시험했다.

**다음 단계는?** 단서를 읽는 소비자와 versioned 계약/하위호환을 설계·합성 검증하는 단계다. 현재 PLANNED이며 실자료 재assess나 자동 판정 변경은 아니다.

## 이후 갱신

최종 독립/전체/보존 근거를 읽고 INDEX·변경 이력·해설/대본/FAQ를 함께 갱신했다. 다음 소비자 구현은 아직 PLANNED다.
