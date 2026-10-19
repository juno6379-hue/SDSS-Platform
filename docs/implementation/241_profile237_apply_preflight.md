# 241 profile237 합성 적용 전 읽기 전용 준비

상태: **PREFLIGHT_RECORDED / 공유 적용 미승인**. 240 독립 리뷰 완료 뒤 Root가 exact baseline archive·적용·검증을 결정한다. 운영data/원장/model 읽기, main 쓰기, 추가 시험, HTTP, 수집, 실QA는0이다.

## 합성 목록과 main 대조

228·230·237 patch manifest의 실제 합집합은 **21파일**이다. 기존236의18개에서237이 새로 만진 `backend/app/data/candidates.py`, `backend/app/collection_priority_status.py`, 신규 `tests/test_manifest_profile237.py`가 더해졌다. 숫자를 코드 변경 수로 추정하지 않고 manifest 경로 union으로 계산했다.

| 구분 | 수 |
|---|---:|
| runtime 제품 코드 |18|
| 합성 검증 시험 소스 |3|
| 현재 main과 pre228(또는 최초 revision 전) baseline SHA 일치 |16|
| 신규 경로가 아직 없음 |5|
| 충돌 또는 이미 최종판인 경로 |0|

각 파일에는 earliest-before SHA/원바이트 baseline archive/현재 main SHA/final237 SHA/해당 revision을 기록했다. 최초228에 없던 파일은 해당 최초 revision이 고정한 before가 기준이며,228 도입 전 baseline부터237 최종까지 직접 비교한다. 현재 main 파일은 비교 전후 동일했고 덮어쓰지 않았다. SHA 일치는 실행 승인이나 운영 성공을 뜻하지 않는다.

## 동결판과 타 담당 보호

228/230/237의 알려진 freeze SHA와 제품·문서·로그·evidence 선언핀 **68건**을 확인했고 불일치0이다. freeze/patch/doc230/doc237/log는 수정하지 않았다. 232의179·170·new helper·test4파일 및 공용167/199는 합성 목록에 포함되지 않는다. 파일별 제외와 현재 code SHA도 증거에 기록했다.

`baseline-code`, `baseline230-code`, `baseline237-code`는 정확 before 코드 보관소다.214 구 source archive와237 input-test-code-supplement는 시험 보조입력이며 운영 제품 copy 목록이 아니다. 전체 workspace 디렉터리 복사는 금지한다. runtime18개와 검증용 test3개를 구분해 Root가 명시 목록만 적용해야 한다.

## 활성 프로세스 관측의 의미

Python 명령행 관측에서 인식되는 collector CLI0 / QA CLI0 / unittest0을 확인했다. uvicorn API 프로세스는3개이며 그중 project8002 서버는 별도로 존재한다. API server 존재를 QA/collector 실행으로 세지 않았다. 이 관측은 서버에 적재된 소스판이나 숨은 in-process 작업의 부재를 보증하지 않는다. 운영 lock 파일/원장/데이터는 읽지 않았으므로 lock 상태를 이 문서에서 확정하지 않는다.

## 이후 Root 절차

1.240 독립 검토 결론을 확인한다.
2.적용 직전21경로의 baseline SHA/신규 부재를 다시 검사하고, 충돌이면 덮어쓰지 않는다.
3.정확 원바이트 baseline archive를 만든 뒤 승인한 합성 목록의 최종237 bytes만 최소 적용한다.230 뒤237 patch를 순서만 믿고 덮어쓰지 않는다.
4.해당 판의 필요한 검증/서버 적용/실UI 여부는 별도 근거로 기록한다.이 준비에서 추가 시험이나 재시작을 수행하지 않았다.

증거: `evidence/integration/preprocess237-workspace-20261018/apply-preflight237.json`, SHA `6236751af0da68ee128548b5878e522a9392a1f4c5cd401ceee3c87c6268b771`. 이 문서는 새 준비 기록이며 고정237/230 문서에 후속 절을 추가하지 않았다.
