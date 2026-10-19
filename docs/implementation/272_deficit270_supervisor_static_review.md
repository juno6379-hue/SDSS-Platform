# 272 — 270 v2 supervisor 독립 정적 리뷰

## 결론

상태는 **STATIC_REVIEW_COMPLETED / NO_BLOCKING_FINDINGS_IN_REVIEWED_SCOPE**다. 최종 258 wrapper와 비교한 270의 변경은 새 실행 식별자·258 감사 결속·271 검증 근거·명시 v2 정책과 예상 config 지문에 한정된다. 검토 범위에서 신규 차단사항을 발견하지 못했다.

이번 결론은 수집 실행 승인이 아니다. request/approval은 아직 발급되지 않은 준비 단계이며 실제 source·원장·운영 파일·래스터·HTTP·collector·API/브라우저를 읽거나 실행하지 않았다. 추가 시험·원본 코드 수정도 0회다. 공유 적용 및 main96 통과 상태는 Root 인계를 구분하여 적었고, 이번 리뷰가 재실행한 시험으로 합산하지 않는다.

## 검토한 소스 지문과 비교

- 새 파일: `evidence/integration/deficit270-supervisor-root-20261018.py`
- SHA-256: `9a42f1d38a90fe7224599f0bc60ef9d8bb7228b95c81efc22e783a6bf526f9fa`
- 비교 기준: 최종 `deficit258-supervisor-root-20261018.py`

두 파일을 읽어 unified diff와 `launch_and_wait`의 AST를 비교했다. 해당 함수의 AST는 완전히 같았다. AST 비교는 코드 구조 확인이며 supervisor나 collector 실행이 아니다.

249에서 보완한 자식 소유 계약이 유지된다. spawn 후 launch 기록·두 stdout 출력에서 일반 예외가 발생해도 기록용 오류 필드를 남기고, `finally`의 `p.wait()`가 자식 종료를 기다린 뒤 실제 exit를 반환한다. 270은 종료 후 terminal을 별도 exclusive 파일로 기록한다. 프로세스 강제 종료·OS 재부팅·최종 terminal 쓰기 자체의 실패까지 복구하는 영속 coordinator라는 뜻은 아니다.

## v2 정책·예상 config 결속

270 approval 상태는 `ROOT_APPROVED_ONE_SE2024_V2_BATCH_AFTER_AUDITED_ZERO258`로 별도다. 새 prepared request 전체를 canonical SHA로 계산하여 approval의 request SHA와 비교하고, schema_version=2와 정확 marker `DEFICIT_AOI_BBOX_CONTAINS_V1`을 요구한다. 기존 v1 승인 파일을 자동 재사용하지 않는다.

예상 config는 승인 SHA로 확인한 205 역사 template의 사본에 새 AOI id/bbox를 적용하고, **정확 policy marker를 넣은 뒤** 기존 `json.dumps(config, sort_keys=True)` 규칙으로 지문을 계산한다. 그러므로 정책을 빠뜨린 v1 예상 config SHA를 새 marker 설정의 SHA처럼 기록하지 않는다. launch의 expected_config_derivation에도 이 변경을 명시했다. config_template result/request의 승인 SHA 비교는 유지된다.

wrapper가 계산한 예상 config는 실행 설정을 임의 승인하는 기능이 아니다. 실제 coordinator는 새 v2 요청·고정 source·정책/binding·실제 config를 fresh proof에서 다시 검산하고, 정상 worker는 metadata callback을 연결해야 한다. 265에서 보완한 marked config↔callback 차단과 기존 SCL/B02 가드는 이 wrapper의 상태 문자열로 대체되지 않는다.

## 271 실제 프로젝트 검증 근거 결속

270은 approval이 가리키는 `runtime_validation_ref` 파일의 상태가 정확히 `SHARED_PROJECT96_VERIFIED_AFTER_ROOT_ENVIRONMENT_CORRECTION`인지 확인하고, 같은 파일 SHA가 approval에 적힌 값과 같은지 검사한 후 나머지 소스 핀·실행 전 검사를 진행한다.

Root 인계에 따르면 268 공유 배치의 최초 결과는 95 PASS/1 FAIL이며 원 로그를 보존했다. 부모 sys.path만으로는 자식의 app import 경로가 전파되지 않은 실행 환경 문제를, 제품·시험 변경 없이271에서 inherited PYTHONPATH를 명시해 동일96개 141.469초로 통과했다. 이력의 실패를 지우거나 과거 통과로 바꾸지 않는다. wrapper는 그 후속 검증 결과의 상태와 SHA를 요구한다. 이 리뷰에서271 시험이나 자식 환경을 다시 실행하지는 않았다.

## 보존한 실행 전 보호 순서

다음은 소스에서 확인한 검사이며 현재 운영 상태를 실제 확인한 결과가 아니다.

1. 별도 approval 상태·1batch/최대16 선언,271 근거, 실행 소스 핀 검산.
2. 새 launch 부재, 기존 global lock 부재, 관련 collector/후보 QA OS 프로세스 사전 관측.
3. 258 실제 감사 파일 SHA와 신규 확보0·보존 checks 확인.
4. 현재 source/원장 승인 SHA와 원래 pending 두 건의 내용 전체·예약 합136,314,880바이트 확인.
5. 기존 추가4GiB·rate-limit false·65MiB 예약 여유, request 전체 SHA와6개 reference SHA 확인.
6. 선택 target 정확히1개·남동부 술라웨시2024·신규 batch key,205 template SHA와 예상 v2 config SHA 확인.
7. 새 request exclusive 기록 후 source/원장 원바이트를 다시 대조하고 기존 guarded collector를 실행.

원 pending 비교가 계속 `deficit235-terminal`의 `pending_before`를 사용하는 것은 처음 두 미정산 행의 원형을 유지하려는 계약이다. 새 수집의 정산을 과거 pending 환불로 바꾸지 않는다. 사용액에 pending이 이미 포함된 원장 계약도 유지한다.

OS/lock 검사는 비원자적 사전 관측이다. 실제 상호배제는 core의 `O_EXCL` global lock이며, 그 안에서 fresh200 inventory·지원영역·실물3000·scene/split·SCL·B02·품질·실측 정산을 다시 확인해야 한다. wrapper는 실제 worker 결과를 만들거나 임의 환불·정산하지 않는다. 시작 상태도 `STARTED_FRESH_PREFLIGHT_NOT_COLLECTION_SUCCESS`, 종료 상태도 `PROCESS_TERMINATED_REQUIRES_SETTLEMENT_AUDIT`라서 완료 성과를 미리 주장하지 않는다.

## 한계와 인계

새 approval의 실제 필드·지문 완전성, prepared request의 실제 target, 현재 원본·원장·잠금·프로세스는 아직 이번 리뷰의 관측 대상이 아니다. Root가 고정 운영 자료와 코드 핀을 다시 검산하고 명시 승인해야 한다. 실제 공급자 metadata 선별·SCL·정렬·품질·취득량은 새 실행과 종료 후 단일 감사로 확인해야 한다.

Root에 정적 결론과 wrapper 지문을 전달했다. 이번 문서와 `evidence/integration/selection272-static-review-20261018.json`은 내부 준비 근거다. UI 변경은 없고 실제 수집·최신 후보·학습/모델 승인 완료로 표현하지 않는다. 실행 후 source/원장 변화가 생기면 Root가 profile·pointer·실 API/브라우저·공통 이해자료에 해당 시점의 별도 근거를 반영한다.
