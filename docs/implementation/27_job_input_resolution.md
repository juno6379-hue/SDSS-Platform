# Job 고정 Dataset 입력 진단 연결

기준: 2026-10-17 KST. 내부 RFC 구현이며 원문 GMAIS 승인 규격이나 실제 과학 실행 완료를 의미하지 않는다.

## 문제와 동작

기존 Job API는 고정 입력 참조의 JSON 형식만 확인했다. 이제 제출한 `input_refs`를 불변 Dataset 코어에 대조하여 등록 누락, 신원·자산 SHA 불일치, URI 충돌, 품질·접근 정책 차단을 진단한다. 임시 fixture로 검사하며 실자료 Registry 등록·수집·학습은 수행하지 않는다.

`backend/app/job_inputs.py:resolve_job_inputs(store, input_refs)`가 `dataset_registry.resolve_version`을 호출한다. 입력 SHA는 manifest metadata SHA가 아니라 실제 artifact SHA다. 요청 URI로 등록 자산을 교체하거나 원격 데이터를 가져오지 않는다. 제한자료는 기관 ACL 미연결을 차단으로 기록하고 경로·URI·원문 manifest·내부 예외문구를 반환하지 않는다.

같은 dataset ID의 서로 다른 고정 version은 T1/T2 시계열 비교에 사용할 수 있다. 충돌은 동일 ID·동일 version에 서로 다른 SHA가 요구된 경우다. 동일 참조를 서로 다른 role로 반복하는 것도 허용한다. 품질·ACL blocker가 있어도 파일 무결성 자체는 true일 수 있으므로 `input_integrity_verified`와 전체 진단 status/blockers를 함께 읽는다. `authorization_verified`는 항상 false이며 PUBLIC도 기관 권한을 검증한 것은 아니다.

`backend/app/gmais_api.py`는 기존 schema·Agent/capability·Idempotency 검사를 통과한 새 요청에서만 진단한다. 결과는 Job record의 `input_resolution`과 기존 409 오류의 `error.details.input_resolution`에 추가한다. 확장 식별자는 `greenblue.job-input-resolution.rfc1`, 승인 상태는 `INTERNAL_REVIEW`다. 원문 Job Status에는 새 필드를 넣지 않으므로 GET Job schema와 기존 UI의 호환을 유지한다.

## 상태와 재생 규칙

- 진단 시각은 `evaluated_at`, 범위는 `SUBMISSION_SNAPSHOT_NOT_EXECUTION_AUTHORIZATION`이다.
- 같은 Idempotency-Key와 같은 요청의 재생은 최초 저장 진단을 반환한다. 이후 파일 변경을 현재 상태로 다시 인증하는 응답이 아니다. 실제 실행기는 실행 직전에 다시 검증해야 한다.
- 같은 키·다른 본문은 기존 SCHEMA_MISMATCH다. 기존 Job의 진단 필드가 없으면 재생에도 추가하지 않는다.
- 입력 대조가 성공해도 `ready_for_execution=false`, `scientific_approval=false`다. PUBLIC+VALIDATED도 과학적 정확성·모델·배포 승인을 뜻하지 않는다.
- 기존 HTTP409, BLOCKED Job, MODEL_NOT_READY/AGENT_NOT_IMPLEMENTED, Location, Job ID/trace, 결과 미생성을 유지한다.

## 검증

단위시험은 임시 fixture 기반이며 실데이터의 모델 정확성 검증과 구별한다.

- `test_job_inputs.py`: 독립 재실행10 PASS/1.663초. `evidence/integration/job-input-core-tests-20261017.log`. 고정 참조·품질·접근 차단·전 입력 점검·원본/카탈로그 불변·서로 다른 버전의 T1/T2 허용·같은 버전의 SHA 충돌 차단을 확인했다.
- `test_gmais_api.py`: 12 PASS/1.987초. `evidence/integration/job-input-api-tests-20261017.log`. 기존8개에 진단 연결·자산 변경 후 재생/새 요청 차이·제한 경로 비노출·과거 진단 없는 Job 재생4개를 추가했다.
- 신규 코드 포함 전체 회귀: `scripts/test.ps1` 종료0, **240건 중239 PASS/1 SKIP,48.174초**. `evidence/integration/job-input-full-tests-20261017.log`. SKIP은 기존 실제 symlink 생성권한 시험이며 deterministic 경계 시험은 통과했다. 이전225건 로그와의 대조에서 신규 입력10개·API4개 및 이전 전체 실행에 아직 포함되지 않았던 복구 CLI 시험1개가 추가됐고 삭제된 시험은 없다. 이 수치는 단위시험을 산술 합산한 것이 아니라 실제 전체 실행 결과다.

기존 로컬 API 프로세스는 자동 reload 없이 실행 중이다. 이 단위의 HTTP 검증은 격리된 임시 Store를 쓰는 TestClient이며 기존 실자료 카탈로그를 재시작·등록·수정하지 않았다. 서버 재시작과 실제 환경 배포 검증은 수행한 것으로 표시하지 않는다.

## 남은 범위

기관별 ACL, 사용자 권한 체계, 실제 Registry 등록 API, lineage 부모 존재, 불변 자산 복제, AOI/기간/제품 의미 적합성, 승인 모델 선택, 실제 executor·DAG 스케줄러 연결은 후속이다. 입력 무결성 진단은 이 요구사항들을 검사한 것으로 확대하지 않는다. Workflow plan endpoint의 입력 바인딩 해석은 이번 변경 범위에 포함하지 않는다.

## 후속 Workflow 연결

같은 입력 진단 코어를 Workflow plan의 각 노드에 연결했다. [문서28](28_workflow_input_resolution.md)을 따른다. Job 제출 진단의 저장/멱등 재생과 Workflow의 매 요청 재검사는 서로 다른 계약이며, 실제 executor·동적 출력 바인딩은 여전히 후속이다.


## 후속 실행 전달 경계의 순수 계약

[문서77](77_execution_input_binding.md)의 새 내부 함수는 제출 고정으로 caller가 제공한 ordered binding과 실행 전달용 선언을 대조한다. 기존 resolve_job_inputs는 현재 Registry/자산/URI 검사이며 이 함수의 선언 일치와 구분한다. 이번에는 resolver·Job 제출 경로·응답이나 실행 승인 gate를 변경하지 않았다. 자산 SHA와 optional manifest SHA는 선언값으로만 비교하고 실제 byte 검사는 하지 않는다. 실사용에는 신뢰할 제출 snapshot의 expected 구성과 현재 resolver/실제 byte 고정·권한/모델 gate가 별도로 필요하다.


## 같은 pass의 선택적 제출 pin capture 연결

[문서78](78_submission_binding_capture.md)은 기존 resolve_job_inputs의 기본 반환을 보존하고 새 내부pair함수에서 같은 resolve_version pass의 canonical manifest pin을 선택 캡처한다. 공개 input_resolution에필드를추가하지않고새Jobrecord에별도extension을같은put로저장한다. 추가Registry/asset조회·추가DB쓰기는없지만기존resolver는현재Registry/asset검사를수행하므로전체IO0이아니다. 제한ACL/quality차단상태에서도무결성선언기록은가능하며모든실행/과학승인false·JobBLOCKED는유지된다.
