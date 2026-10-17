# Gate Stored Current Binding 20261017 — 저장 pin과 현재 직접 입력의 비실행 대조

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | d474d5bce6c2a6c4bd8ba141c9256d15f6004631 (108까지 구현 검토 기준; 이 메타데이터 정리는 후속 문서 커밋) |
| evidence_paths | `backend/app/stored_current_binding_preflight.py`; `tests/test_stored_current_binding_preflight.py`; `docs/implementation/83_stored_current_binding_preflight.md`; `evidence/integration/stored-current-binding-preflight-related-20261017.log`; `evidence/integration/stored-current-binding-independent-20261017.log`; `evidence/integration/stored-current-binding-live-validation-20261017.json`; `evidence/integration/stored-current-binding-live-check-20261017.py`; `evidence/integration/stored-current-binding-full-tests-20261017.log`; `evidence/integration/stored-current-binding-live-integrity-20261017.json` |
| confidence | 완료 코드·격리 합성 검증·실제 legacy 읽기; 운영 current MATCH는 미관측 |
| status | TESTED_SYNTHETIC: 현재 입력 positive 검사; VERIFIED_REAL: 기존 legacy 조회 범위; 실행 BLOCKED |

## 쉬운 설명

주문할 때 남긴 재료 목록과 지금 창고에 있는 재료를 비교한다. 질문은 세 가지다. 옛 주문 목록이 남아 있는가? 지금 재료의 지문과 품질 표시가 맞는가? 두 목록이 같은가? 목록이 같아도 품질이 부족하면 출고하지 않는다. 옛 목록이 없으면 현재 재료를 보고 과거 목록을 만들어 채우지도 않는다.

## 이론적 배경

82는 보관함에서 읽은 Job과 호출자가 준 전달 선언을 비교했다. 83은 호출자가 전달 선언을 만들지 않는다. 저장 RECORDED를 먼저 검증한 뒤 기존 resolver가 현재 직접 입력을 검사하고 만든 capture를 대조한다. 저장 기준, 현재 진단, 선언 일치를 분리해 하나의 성공이 다른 실패를 덮지 않게 한다.

| 축 | 확인하는 것 | 성공만으로 보장하지 않는 것 |
|---|---|---|
| 저장 근거 | Job/request 연결, capture 형식·hash·고정 pin | 보관함의 암호학적 출처 인증 |
| 현재 직접 입력 | 기존 resolver의 자산 지문·URI·quality/PUBLIC 진단 | 기관 ACL·모델 준비도·전이 계보·과학 승인 |
| 저장 대비 현재 | Job/Agent/Trace와 ordered binding 선언 | 실제 실행기에 전달된 목록·TOCTOU 보호 |

## 코드와 데이터 흐름

`inspect_stored_current_binding_preflight(store, requested_job_id)`는 외부 Job·expected·supplied·경로 인자를 받지 않는다. 유효한 요청은 Store의 Job을 한 번 읽는다. 잘못된 요청은 읽지 않는다. 79 projection이 저장 기록을 검증하고, LEGACY/UNAVAILABLE이면 UNKNOWN·현재 NOT_RUN으로 끝낸다. INVALID는 BLOCKED다.

RECORDED일 때만 저장된 모든 URI를 길이·타입·제어문자 기준으로 먼저 검사한다. 한 항목이라도 지원 범위를 벗어나면 현재 resolver를 호출하지 않는다. 이후 `resolve_job_inputs_with_capture`를 한 pass 호출한다. 같은 검증 record에서 얻은 current envelope를 81 guard에 넘기므로 비교용 Registry 추가 조회는 없다. pass 1회는 입력 전체 처리 1회이며 Registry get 1회라는 뜻은 아니다.

현재 응답은 정확한 기본 키 10개, 타입·상태·배열·안전 코드 상한을 검사한 뒤 snapshot projector로 대조한다. 특히 원 응답의 authorization_verified가 true이면 INVALID다. 기존 helper가 이를 false로 재투영하는 과정에서 잘못된 승인 값을 정상으로 바꾸지 못하게 선검사를 추가했다.

현재 resolution이 BLOCKED면 binding MATCH여도 전체 BLOCKED다. 현재 INTEGRITY_VERIFIED, capture RECORDED, binding MATCH가 모두 성립할 때만 전체 MATCH다. id/version/asset SHA가 같더라도 canonical manifest metadata와 digest가 바뀌면 저장 manifest pin과 달라 BLOCKED다. 이 시뮬레이션은 격리 fixture에서만 수행했다.

## 시험 증거

관련 12 PASS/4.402초, 독립 12 PASS/3.119초다. 격리 TempStore에서 현재 자산 hash와 MATCH, manifest metadata 변경, 품질 부족·RESTRICTED와 binding MATCH의 병존, 자산·URI 변경, 일부 입력 부재, legacy skip, 거대/잘못된 current 응답 선검사, 쓰기·학습 trap을 확인했다. 반복 시험 수는 전체 회귀에 더하지 않는다.

실제 읽기 전용 Store에서는 기존 legacy Job 두 건이 UNKNOWN/current NOT_RUN이었다. 없는 Job과 잘못된 요청을 포함해 Store.get 총 3회, resolver 0회·Registry get 0회였다. 카탈로그 14기록과 기존 Job 본문은 같고 역채움도 없었다. 실제 current MATCH나 운영 자산 hash 검증을 관측한 것은 아니다. 최종 전체 회귀는 856건 중 855 PASS·기존 Windows symlink 권한 제약 1 SKIP, 343.921초·종료 0이다. 관련·독립 시험과 실제 조회 횟수는 전체에 더하지 않는다.

## IO와 승인 한계

이 기능 전체는 IO 0이 아니다. RECORDED 경로에서는 기존 resolver가 Registry와 현재 자산을 읽고 hash한다. 내부 81 guard의 DB 0과 current_files_revalidated=false는 순수 비교 부분의 범위다. top에는 current_files_revalidated를 복사하지 않는다. 추가 공통 승인 12개와 executor·origin·transitive 3개, 총 15개 false를 유지한다.

직접 입력만 대상이며 전이 계보, 기관 승인, 모델 준비도, 나지 부족, 과학 성능, 실제 실행기 전달과 TOCTOU는 검증하지 않는다. 기존 Store의 전체 JSON 파싱과 resolver의 파일 읽기는 그대로라 RAM·CPU·누적 IO·개별 파일 byte hard cap도 제공하지 않는다. 알려진 자원 오류는 안전 코드로 표시하고 프로그래밍 오류나 종료 신호는 전파한다.

공개 API·UI·Workflow·실행 체인에는 연결하지 않았다. 기존 79/80 응답과 카드는 같으므로 직접 UI 수정·프론트 재시험·브라우저 검사는 하지 않는다. 원본 5차단과 후보 QA 4차단, 예약 136,314,880B·환불 0도 유지한다.

## 1분 발표

“저장된 제출 목록과 현재 입력을 비교하는 내부 검사를 추가했습니다. 먼저 옛 목록이 유효한지 보고, 현재 파일의 지문과 품질 표시를 검사한 뒤 두 선언을 대조합니다. 목록이 같아도 품질이 부족하면 차단합니다. 옛 기록이 없으면 현재 목록으로 역채우지 않습니다. 현재 입력이 정상인 경우는 격리 시험으로 검증했고 실제 기존 두 Job은 미기록이라 현재 검사를 건너뛰었습니다. 실제 실행기나 새 화면에 연결한 기능은 아니며, 일치해도 실행·학습·과학 승인은 아닙니다.”

## 5분 발표 순서

1. **0~1분:** 옛 주문 목록과 현재 창고 재료의 비유를 말한다.
2. **1~2분:** 저장 근거·현재 진단·선언 대조의 세 축을 보여준다.
3. **2~3분:** 품질 차단과 pin 일치가 함께 가능하고, manifest metadata 변경도 차단하는 이유를 설명한다.
4. **3~4분:** 합성 현재 검사와 실제 legacy 조회, 전체 회귀의 범위를 나눈다.
5. **4~5분:** 실제 IO와 내부 순수 비교, 승인·실행기·UI 미연결을 구분한다.

10분 설명에서는 authorization true 선검사, URI 전체 선검사, null과 0의 차이, same-pass capture, resource/형식/프로그래밍 오류의 경계를 추가한다.

## Q&A

**MATCH면 실행해도 되나?** 직접 입력의 제한된 현재 진단과 선언이 맞았다는 뜻이다. 모델·기관·과학 승인과 실행기 전달은 별도다.

**옛 기록이 없으면 지금 파일로 채우나?** 채우지 않는다. UNKNOWN이며 현재 resolver도 실행하지 않는다.

**파일 지문이 같아도 차단되나?** 품질·PUBLIC 조건이 부족하거나 저장 manifest pin이 다르면 차단한다.

**실제 현재 자산 검증에 성공했나?** 성공 경로는 격리 합성 환경에서 확인했다. 실제 기존 두 Job은 legacy여서 현재 검사를 하지 않았다.

**기존 화면에서 바로 쓸 수 있나?** 내부 함수다. 공개 API와 화면에는 아직 연결하지 않았다.

## 이후 갱신

최종 전체 회귀·보존 근거를 읽고 INDEX·변경 이력·계약·구조·발표·FAQ를 함께 갱신했다. 다음 작업은 PLANNED다. GET /v1/jobs/{job_id}/input-preflight companion과 기존 카드의 “현재 직접 입력 다시 검증” 명시 버튼, 세 축의 독립 결과를 한 단위로 연결할 계획이다. 기존 저장 조회 응답은 유지하고 현재 Registry·자산 hash의 IO와 시간 비용을 안내한다. worker 1 lock은 실제 작업 종료까지 유지하며 안전 오류·no-store·권한·stale 결과 제거를 검증할 예정이다. 표시 중단은 서버 취소가 아니고 전체 파일 byte·시간·RAM 상한도 보장하지 않는다. 아직 API·UI·실행기 구현이나 실제 관측은 없다. 전체 개발과 10분 보고는 계속된다.


## 최종 보존과 적용 범위

시험 종료 후 보호 참조 141개, 기존 코어 45개, 카탈로그 14기록과 기존 Job 본문 SHA가 같음을 확인했다. 이전에 추적한 코드·데이터·시험·프론트 변경 목록도 비어 있다. 이는 지정한 보호 범위의 비교이며 전체 워크스페이스나 원자적 snapshot 보장은 아니다.

최종 전체는 856건 중 855 PASS·기존 Windows symlink 권한 제약 1 SKIP/343.921초·종료 0이다. 기존 deterministic 경계시험은 통과했다. 현재 positive 검증은 합성 환경이며 실제 legacy 두 건은 UNKNOWN/NOT_RUN이다. 운영 POST·역채움·새 QA·학습·실행기 연결은 0이다. 공개 API·기존 화면 계약은 같고 이번 직접 브라우저 검사는 없다.
