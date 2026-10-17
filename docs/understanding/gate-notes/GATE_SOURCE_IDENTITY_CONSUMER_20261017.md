# Gate Source Identity Consumer 20261017 — 선언 경로·지문으로 후보를 좁히는 읽기 진단

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/data/readiness_connectivity_lineage.py`; `tests/test_readiness_connectivity_lineage.py`; `tests/test_readiness_connectivity_adapter.py`; `evidence/integration/readiness-source-identity-consumer-related-20261017.log`; `docs/implementation/65_readiness_source_identity_consumer.md`; `evidence/integration/readiness-source-identity-consumer-independent-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-cli-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-legacy-20261017.json`; `evidence/integration/readiness-source-identity-consumer-live-legacy-validation-20261017.json`; `evidence/integration/readiness-source-identity-consumer-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-consumer-live-integrity-20261017.json` |
| confidence | 코드·합성시험 기반; 실자료 identity 소비 미검증 |
| status | TESTED_SYNTHETIC: 선언 소비·전체회귀; VERIFIED_REAL: legacy 바이트 동일; 학습 BLOCKED·새 진단 PLANNED |

## 쉬운 설명

이름이 같은 물품의 넓은 후보 목록을 그대로 두고, 보관 경로와 지문 메모가 모두 있으면 별도 후보표를 좁힌다. 비교할 수 없는 메모가 하나라도 있으면 그 항목을 몰래 지워 정답처럼 만들지 않고 원래 후보를 보존한다. 후보가 하나가 되어도 물품을 실제로 확인한 인증은 아니다.

## 이론적 배경

63의 주·제품 토큰 후보는 넓은 metadata 일치이고64의 source_identity는 선택적 선언 단서다. 이번 소비자는 완전한 선언만 읽어 별도의 refinement 결과를 만든다. 넓은 후보의 회원 수·연결 수를 그대로 유지하면 기존 의미를 바꾸지 않고 단서의 효과를 구별할 수 있다. 불완전한 근거를 제외해 인위적으로 유일성을 만드는 일을 피하도록 비교 불가 상태를 보존한다.

## 실제 코드·계약

`inspect_readiness_connectivity_lineage`는 optional source_identity가 있을 때 `_validate_source_identity`로 version1·정확한 타입/키·상태 조합·장면 순서·개수/coverage·false flags를 검사한다. 잘못된 optional 객체는 정상 단서로 소비하지 않고 오류로 거부한다. 객체가 없으면63의 기존 출력 구조·후보 의미가 그대로다. 유효한 NOT_CAPTURED_ERROR는 단서 부재로 다룬다.

`_refine_identity_members`는 원래 후보·회원 계수를 변경하지 않고 source_identity_refinement 영역을 별도로 추가한다. 완전한 DECLARED_PATH_AND_SHA256만 `_lexical_identity_path`의 문자열 경로 성분과 선언 SHA 쌍으로 대조한다. Windows data root는 성분 casefold, POSIX는 대소문자를 구분하며 실제 경로 resolve/stat/open/hash를 하지 않는다. 상대 경로와 root 아래 절대 경로의 문자열 성분을 비교하되 URL·UNC·상위/현재경로 성분·장치/ADS·모호한 경로는 비교하지 않는다. 파일시스템의 동일 파일 여부 인증이 아니다.

| 조건 | 결과·보존 |
|---|---|
| legacy 객체 부재 | 기존63 출력 유지; refinement 영역 없음 |
| identity 미포착/부재/부분·무효 상태 | 넓은 원후보 보존 |
| raw metadata 불완전·경로 비교 불가 | 넓은 원후보 보존 |
| raw 후보 중 하나라도 경로/SHA 비교 불가 | 해당 넓은 후보 집합 전체 보존 |
| 모든 선언 비교 가능 | 경로·SHA 일치 후보만 별도 refinement |
| 일치0/1/여러 개 | NO_DECLARED_METADATA_MATCH / UNIQUE_DECLARED_METADATA_CANDIDATE / AMBIGUOUS_DECLARED_METADATA_MATCH_SET |

단일 후보라도 status는 DECLARED_METADATA_ONLY이고 exact row binding·원본/제품 진실·파일시스템 identity·학습/과학승인은 false다. 같은 선언을 가진 중복 원본행은 여러 후보로 유지한다. 출력 한도는 저장 목록만 자르고 전체 연결/고유 후보 계수와 절단 여부를 구분한다.

## 시험 증거

관련 lineage24 PASS/8.893초(기존16+신규8)와 adapter compatibility1 PASS/0.579초를 읽었다. 두 실행을 임의로 합쳐 전체 회귀 숫자로 발표하지 않는다. legacy 부재/선언 singleton/중복모호성/불완전 raw·경로/typed 변조/한도·순서/추가 IO 없음과 adapter의 optional 객체 호환을 합성 fixture로 확인한다. 최종 전체 `scripts/test.ps1`은 **638건 중637 PASS·1 SKIP/190.384초/종료0**다. SKIP은 기존 Windows symlink 생성권한이며 deterministic 경계 시험은 통과했다. 관련 lineage24 PASS/8.893초·호환1 PASS/0.579초, 독립24 PASS/8.200초·호환1 PASS/0.419초는 전체638에 중복 합산하지 않는다. 보호133참조·lineage 외24계약SHA·manifest/current report 핀과 다섯 차단·패치628/233/250은 불변이다. 이전 추적 파일 중 의도한 lineage 코어·그 시험·adapter 호환시험3개만 변경됐고 producer adapter/readiness/CLI는 유지했다.

Root의 CP949 실제 legacy CLI1회는 종료0이며 결과57,548bytes·SHA `cff1fb4b566cb8d9be4625df253411d3776ae1f0e485854798ac36673aac2a8e`로63 출력과 바이트 동일했다. 현재 report에 identity가 없어 refinement도 없고28전원 AMBIGUOUS·400연결/고유raw28·exact binding false가 그대로다. 이는 하위호환 관측이며 새 identity의 실자료 소비 검증은 아니다. 두 고정 JSON만 조회했고 영상 IO·assess 재실행·새 readiness 보고서 생성은 없었다. 이해 에이전트는 실행하지 않았다.

## 현재 실자료·한계·UI

현재 고정된 실제 보고서에는 source_identity가 없다. 새 assess나 실자료 보고서 생성 없이 소비자 코드를 바꿨으므로28장면 전원 모호성·400연결/고유raw28이 해결된 것은 아니다. 실제 legacy CLI 확인은 기존 두 JSON의 하위호환 관측이며 새 단서로 후보를 좁힌 실증이 아니다.

이 진단은 영상 파일·113개 원본 manifest·픽셀/기하·출처 진실을 재검사하지 않는다. 현재5차단·패치628/233/250·원본 분할·baseline Draft·terminal2missing·예약136,314,880B·환불0을 유지한다. 기존 API/UI 계약 변경 없는 내부 읽기 CLI라 화면 변경은 필요 없다. 전체 개발과10분 보고는 계속한다.

## 발표 1분

“이름이 같은 원본 후보 목록에 이미 기록한 경로와 지문 단서를 대조하는 기능을 추가했습니다. 넓은 원래 목록을 바꾸지 않고 별도 후보표를 좁히며, 비교할 수 없는 후보가 있으면 전체 목록을 보존합니다. 하나만 남아도 선언 일치일 뿐 실제 파일이나 원본행 인증은 아닙니다. 현재 실제 보고서에는 이 단서가 없어28장면의 모호성은 그대로입니다. 다음에는 고정 입력과 자원 범위 안에서 학습 없는 새 진단 보고서로 계약을 관측할 계획이며, 아직 실행하거나 다섯 학습 차단을 바꾸지 않았습니다.”

## 발표 5분·10분

1. **0~1분:** 물품 목록과 보관 경로·지문 메모 비유를 설명한다.
2. **1~2분:** 원래 후보와 별도 refinement·선택적 version1 계약을 구분한다.
3. **2~3분:** 비교 불가 시 전체 보존·중복 후보 유지·singleton 미인증을 보여준다.
4. **3~4분:** 관련24/호환1·독립/전체·실제 legacy 확인의 범위를 구분한다.
5. **4~5분:** 현재 보고서 단서 부재·28모호성 보존과 다음 새 보고서 PLANNED를 설명한다.

10분 확장에서는 Windows/POSIX 문자열 경로 규약·유효 NOT_CAPTURED_ERROR·typed key/count/order/flags 검증·후보 목록 절단과 전수 계수 차이를 설명한다.

## Q&A

**후보가 하나면 원본행 확정인가?** 선언 경로·SHA가 유일하게 맞는 후보일 뿐 파일 진실·정확 binding은 false다.

**비교 불가한 raw 후보를 버리나?** 하나라도 있으면 해당 원래 후보 집합을 보존한다.

**기존 도구 출력은 달라지나?** optional 객체가 없는 legacy는 이전 출력과 같고, 있을 때도 넓은 후보와 계수는 유지하며 별도 영역을 추가한다.

**현재28모호성이 해결됐나?** 실제 보고서에 단서가 없어 그대로다. 합성 성공을 실제 후보 축소로 발표하지 않는다.

**다음은?** 고정 입력·정책과 자원 범위에서 noexecute 새 진단 보고서로64/65를 관측하는 작업이다. 현재 PLANNED이며 학습·분할 변경은 아니다.

## 이후 갱신

최종 전체/실제 legacy·보존 근거를 읽고 INDEX·변경 이력·해설/구조/용어/대본/FAQ를 함께 갱신했다. 새 실자료 진단은 아직 PLANNED다.
