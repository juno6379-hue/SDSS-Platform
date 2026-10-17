# Gate Candidate Plan Lineage 20261017 — 후보 계획과 선언 계보의 참조 연결

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/ml/candidate_plan_lineage.py`; `scripts/inspect_candidate_plan_lineage.py`; `tests/test_candidate_plan_lineage.py`; `docs/implementation/69_candidate_plan_lineage.md`; `evidence/integration/candidate-plan-lineage-related-20261017.log`; `evidence/integration/candidate-plan-lineage-independent-20261017.log`; `evidence/integration/candidate-plan-lineage-live-20261017.json`; `evidence/integration/candidate-plan-lineage-live-cli-20261017.log`; `evidence/integration/candidate-plan-lineage-full-tests-20261017.log`; `evidence/integration/candidate-plan-lineage-live-integrity-20261017.json` |
| confidence | 코드·합성시험 기반; 선택 metadata 참조 연결이며 전체 planner 재현/정확 클래스·독립성 인증 미검증 |
| status | TESTED_SYNTHETIC: 관련/독립19·전체회귀; VERIFIED_REAL: 다섯JSON 선택metadata; PLAN_ONLY/BLOCKED |

## 쉬운 설명

후보 계획서와 최신 검사표·제품 대조표를 하나의 참조 묶음으로 연결한다. 제품 대조표의 선언 후보가 계획서의 ‘유지 예정’과 ‘새 후보에서 제외 예정’ 중 어디에 있는지 읽어 설명한다. 실제 원본행을 삭제하거나 새 목록을 발행하지 않는다. 다섯 문서의 일부 숫자와 참조를 확인하는 일은 계획 알고리즘 전체를 다시 돌리는 일과도 다르다.

## 이론적 배경

기존 split repair 계획은 고정 test→val→train 우선순위와 retained/excluded 행을 저장한다. 최신 선언 계보는 내부 장면과 원본 manifest 후보를 경로·SHA 선언으로 연결한다. 두 정보를 결합하면 ‘이 선언 후보가 저장 계획에서 어떻게 취급되는가’를 추적할 수 있다. 기존 행 번호끼리 같다고 연결하지 않고 선언 후보를 먼저 확인한다. 이것은 metadata 연결이며 정확 원본행·출처 인증은 아니다.

## 코드·입력·검증 범위

순수 `build_candidate_plan_lineage`는 plan/source/old_readiness/new_report/lineage 정확히 다섯 문서와 호출자 선언 참조를 받는다. 순수 코어의 pin_validation은 CALLER_DECLARED_REFERENCES_ONLY다. `inspect_candidate_plan_lineage`와 CLI wrapper만 실제 다섯 JSON의 최초/최종 bytes SHA·stat·논리 대상 재대조를 수행한다. 순수 함수가 실제 파일 지문을 인증하는 것으로 설명하지 않는다.

| 입력 | 역할·상한 |
|---|---|
| plan | 기존 PLAN_ONLY 저장계획·4MiB |
| source | 고정 aggregate·64MiB |
| old_readiness | 계획이 참조한 저장 gate·16MiB |
| new_report | 최신 identity 준비성 관측·16MiB |
| lineage | 최신 token 선언 계보·4MiB |

각 입력을 두 번 읽는 총 JSON 상한208MiB이며 깊이32/엄격UTF8·중복키/NaN·대상/별칭·전후변경을 검사한다. 새 evidence 출력은 DATA밖 exclusive 새파일이며 입력/기존파일/장치/ADS·모호경로를 거부한다. 부분 새파일을 임의 정리하지 않고 다중파일 원자 snapshot이나 hard CPU/memory를 보장하지 않는다.

저장계획의 전체행 partition·정렬/중복없는 uint index, source/oldreport 참조·정책 map, quality_eligible metadata의 before/projected_after 계수를 검사한다. old/new gate의 정책·5차단·패치/클래스계수는 typed 같아야 한다. 최신 장면은0patch를 포함한 전체 순서·선언 coverage를 유지한다. token회원의 넓은 후보는 최대2000연결로 사전 한정하고 저장 lineage와 비교한다. 완전/비절단 유일선언 후보가 있는 경우만 그 raw 후보행이 retained/excluded 어느 집합에 있는지 연결한다.

`internal_scene_index`와 `raw_manifest_candidate_row_index`는 다른 필드다. 원본 행 순서가 바뀐 합성 사례에서도 선언 경로·SHA로 연결한다. 기존 순수 refinement를 metadata로 재대조하지만 assess/58 witness/기존 planner는 호출하지 않는다. full_planner_recomputation과 full_witness_replay는 NOT_PERFORMED이며 우선순위는 저장 정책의 선언이다.

## 클래스·학습 한계

class_impact는 CONSERVATIVE_BOUNDS_ONLY다. 제외 eligible수×patch_size²를 이용한 픽셀 하한·기존 클래스/패치 상한·bare비율 상한의 산술만 확인한다. 새 라벨 픽셀이나 정확한 후보 클래스 통계를 읽어 계산하지 않는다. 따라서 val bare부족·정확한 독립성·누출 해소를 승인하지 않는다. 메타데이터상1111→1095 예상치는 후보 발행/학습 준비 완료가 아니다.

candidate manifest 생성·원본행 제외/재배정·Registry등록·분할/정책/gate변경·원본 raster/read/hash·assess/helper·정확 클래스·학습/정산/자동재개는 모두 수행하지 않는다. BLOCKED/PLAN_ONLY·exact binding/source authenticityfalse·refund0·exactlyonceUNKNOWN을 유지한다.

## 시험 증거

관련19 PASS/9.466초·독립19 PASS/9.834초는 작은 다섯 JSON 합성 검증이다. partition/typed계수·참조·old/newgate·클래스보수 bounds·선언/계보·행순서/0patch·사전예산·strictJSON/retarget/stale·새 evidence/CP949·추가IO없음/기존planner·assess 미호출을 다룬다. 두 반복을 전체시험에 더하지 않는다. 최종 전체 scripts/test.ps1은 **671건 중670 PASS·1 SKIP/246.659초/종료0**다. SKIP은 기존 Windows symlink 생성권한 제약이며 deterministic 경계 시험은 통과했다. 관련19 PASS/9.466초·독립19 PASS/9.834초를 전체671에 중복 합산하지 않는다. 보호134참조·26기존 계약SHA·다섯 입력핀·카탈로그14기록의 canonicalSHA가 불변이고 이전 snapshot 추적 backend/scripts/data/tests/frontend 변경은0이다. 새 구현 파일과 evidence가 존재하므로 전체workspace변경0으로 해석하지 않는다. 원자 snapshot/전체workspace inventory 보장은 아니다. 이해 에이전트는 실행하지 않는다.

## UI·발표 한계

공개 API/UI 계약이 없는 내부 참조 CLI라 이번 화면 변경은 필요 없다. 직전 저장조회 UI완성과 이번 후보계획 설명을 구분한다. 기존 실제 원본·원장·lock·예약136,314,880B·terminal2missing·5차단·baselineDraft는 유지한다. 전체 개발과10분 보고는 계속한다.

## 발표 1분

“저장된 후보 계획과 최신 선언 대조를 다섯 문서의 참조 묶음으로 연결했습니다. 어떤 선언 후보가 새 후보 계획에서 유지 또는 제외 예정인지 읽어 설명하는 도구입니다. 원래 장면번호와 원본행번호가 같다고 연결하지 않고 선언 경로와 지문으로 확인합니다. 기존 계획의 선택 숫자와 보수적 클래스 상한을 대조하지만 계획 알고리즘 전체나 정확한 후보 클래스 통계를 다시 계산하지 않습니다. 후보 목록을 만들거나 원본행을 삭제·재배정하지 않았고 학습 차단도 그대로입니다.”

## 발표 5분·10분

1. **0~1분:** 계획서/검사표/제품대조표를 묶는 비유를 말한다.
2. **1~2분:** 다섯 고정 문서와 순수 선언참조/CLI 바이트핀 차이를 설명한다.
3. **2~3분:** 유일선언후보→계획의 유지/제외 예정 연결·0patch/다른index를 설명한다.
4. **3~4분:** 관련/독립·실제/전체·보존 근거와 NOT_PERFORMED범위를 구분한다.
5. **4~5분:** 보수 클래스 bounds·실제발행/원본제외/등록/훈련0·BLOCKED를 설명한다.

10분 확장에서는 엄격 partition·행순서 변경 회귀·208MiB/새 evidence·전수witness미재생·원자snapshot미보장·원본인증false를 다룬다.

## Q&A

**새 Dataset 버전을 발행했나?** 참조 패키지만 만들고 후보 manifest/Registry등록은 하지 않는다.

**행16개를 원본에서 지웠나?** 저장 계획의 제외 예정 집합과 연결할 뿐 원본 삭제/제외/재배정은 없다.

**계획이 다시 계산돼 검증됐나?** 선택 metadata와 partition/계수를 대조하며 전체 planner재계산은 NOT_PERFORMED다.

**클래스 부족이 해결됐나?** 보수 상하한만 대조하며 정확 클래스·bare부족 해소는 false다.

**유일선언후보를 연결하면 원본행 인증인가?** metadata-only이며 exact binding/source authenticityfalse다.

## 이후 갱신

Root 실제 다섯JSON 실행·전체/보존 최종근거를 읽고 INDEX·변경이력·해설/구조/용어·대본/FAQ/시연을 함께 갱신했다. 새 공개 API/UI·학습/발행은 없다.

## 실제 다섯JSON CLI 관측

Root의 CP949 CLI1회는 종료0이며 새evidence19,766bytes·SHA `ee49f84c2b1e4a0aff72db321185b4d6d442f9878cca138dd7af116a0bf1760c`를 만들었다. 다섯 입력바이트 핀을 최초/최종 안정성 재대조했고 pin_validation은 FIVE_INPUT_BYTE_SHA256_VERIFIED_WITH_STABILITY_RECHECK다. full_planner_recomputation은 여전히 NOT_PERFORMED이며 PLAN_ONLY/BLOCKED다.

| 선택 metadata | 실제 관측·해석 |
|---|---|
| source |1,384행 원형 유지 |
| 저장계획 partition |1,368행 유지예정/16행 새후보에서 제외예정 |
| projected eligible |1,095=628train/217val/250test 예상 |
| 현재 원본 적격 |1,111=628/233/250 불변 |
| query |28유일선언후보·400넓은연결·0patch3/patch25 |
| query의 계획 연결 |16선언후보 제외예정/12유지예정; 실제 원본제외0 |
| val bare 한계 |픽셀상한209·하한0·bare패치상한0·부족해결false |

val bare비율의 보수상한은 약0.001837%이며 새 라벨 픽셀 실측 비율이 아니다. 제외계획이 클래스 대표성을 더 악화시킬 수 있다는 저장 한계를 그대로 둔다. 최신 선언유일성과 계획행 연결이 현재 학습차단5를 없애거나 후보 발행을 승인하지 않는다. CLI는 JSON만 읽고 기존 planner/writer를 실행하거나 영상을 읽지 않았다.
