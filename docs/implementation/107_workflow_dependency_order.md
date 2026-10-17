# 107. Workflow 의존 순서의 공통 정렬 계층 검사

상태: **TESTED_SYNTHETIC**. 기존 세 호출부의 Kahn 순서 계산만 공유 함수로 추출했다. 합성 graph와 SHA 고정 원문 모듈·TempStore로 기존 응답·오류·접근 순서 동등을 검증했다. 운영 Job/Workflow 제출·수집·학습·배포와 실행 중 서버 동작 확인은 수행하지 않았다.

## 변경 이유와 정렬 계약

[topological_order(validated_dependency_map)](../../backend/app/workflow_dependency_order.py)는 **이미 검증된** 노드→의존 노드 map을 받아 원래 세 구현과 동일하게 정렬된 ready 계층을 순서대로 처리한다. 각 단계의 ready 노드를 모두 정렬해 결과에 넣고, 그 계층 전체를 제거한 뒤 다음 계층을 구한다. 전역 최소 노드를 하나씩 고르는 heap 방식으로 바꾸지 않는다.

```python
topological_order({'a': set(), 'b': {'a'}, 'z': set()})
# ['a', 'z', 'b']
```

처음 준비된 a/z가 모두 나온 뒤 b가 나온다. heap 방식의 `['a', 'b', 'z']`와 구별한다. UI가 소비하는 기존 `topological_order`의 표시 순서를 그대로 보존한다. 이 계층은 정렬 계산의 단계일 뿐 실제 병렬 실행이나 스케줄러 시작을 뜻하지 않는다.

함수는 노드별 dependency를 새로운 set으로 복사해 입력을 변경하지 않는다. 결과는 순서 목록 또는 진행 불가능한 경우 `None`이다. 빈 map은 `[]`이며 `None`과 구별한다. 세 caller는 모두 `ordered is None`일 때만 기존 cycle 오류를 반환한다.

helper는 외부 요청 schema·ID·중복·unknown/self edge를 새로 검증하지 않는다. 이 조건은 기존 caller가 먼저 확인한다. 검증되지 않은 unknown edge를 helper에 직접 주면 미충족 간선 때문에 `None`일 수 있으므로 helper의 None만으로 입력의 모든 오류 원인을 판정하지 않는다. 파일·Store·network·실행 I/O는 없다.

## 세 호출부의 최소 치환과 오류 순서

각 파일에는 import 하나와 기존 반복문 치환만 적용했다. 기존 dependency map 구성과 사전/후속 검사·응답 필드는 그대로다.

| 호출부 | 보존한 순서와 동작 |
|---|---|
| [gmais_api.plan_workflow](../../backend/app/gmais_api.py) | schema→duplicate→unknown/self→cycle→manifest→Store factory. cycle은 기존400/메시지 유지. 원 응답/headers·정렬 순서·PLAN_ONLY/실행 false 유지 |
| [workflow_lineage.validate_workflow_lineage](../../backend/app/workflow_lineage.py) | schema→limits(int만, bool 제외)→max_workflow_nodes 조기차단→duplicate→unknown/self→cycle→input limit→unique root limit→asset 진단. 기존 예외 종류/문구·차단 결과·읽기 순서 유지 |
| [workflow_policy.diagnose_workflow_blocking](../../backend/app/workflow_policy.py) | policy/node/blocker 검증과 deepcopy/JSON 오류가 graph 검사보다 먼저. unknown/self 뒤 cycle, 이후 기존 ancestor/STOP_DEPENDENTS/FAIL_ALL 전파·결과 순서 유지 |

반복 dependency를 한 간선으로 다루는 기존 set 의미와 caller별 ID 허용 범위도 바꾸지 않는다. 알려지지 않은 노드를 새로 생성하거나 순환을 무시하지 않는다. schema·model_ref·Agent/capability 검사·등록 gate·Store/manifest 접근 시점·실제 lineage 자산 검증 정책은 그대로다.

## 원문 대조와 시험 근거

[신규 시험](../../tests/test_workflow_dependency_order.py)은 다음 사전 byte 사본을 SHA 확인 후 별도 `app` 패키지 모듈로 cold import한다. schema loader는 evidence 경로의 부모를 따라 같은 프로젝트 root의 원 vendored schema를 찾는다. 신규 시험은 운영 `app.main`을 import하지 않는다.

| 원문 사본 | SHA-256 |
|---|---|
| [gmais 원문](../../evidence/integration/workflow-dependency-order-original-gmais_api-20261017.py) | `18f1b7185a4d458d968b0c484f22ae29233cb6617aeb3f63f14ec1e9054f6aed` |
| [lineage 원문](../../evidence/integration/workflow-dependency-order-original-workflow_lineage-20261017.py) | `26230f2619ed32442b9dfb2187ae8972d74d3a260e6b7d018ed4a859236c56bf` |
| [policy 원문](../../evidence/integration/workflow-dependency-order-original-workflow_policy-20261017.py) | `c75e8e5e46e71a42f6e15c290f51c9c5ad08b3219bc825b7b598520e8f999205` |

검증 항목은 다음과 같다.

- sorted-ready-layer와 heap의 차이, 입력 map 순서 독립, empty/diamond/disconnected/repeated-edge/cycle, shared set alias 불변과 helper I/O0.
- GMAIS 격리 FastAPI에서 원/신규 전체 body/headers·schema/manifest/factory/Store 접근 순서·임시 DB 미변경. 두 정책 모드와 동일 계층 순서를 비교하며 실제 Job은 만들지 않는다. clock은 고정했다.
- schema/duplicate/unknown/self/cycle 오류가 manifest/Store 전에 발생하는 순서와 원문 메시지 보존.
- lineage 실제 TempStore에서 원 응답/오류·verify/Store 순서를 비교하고, limits bool·최대 node 조기차단·duplicate/edge/cycle·input/서로 다른 root의 한도 우선순위와 비실행을 확인한다. 합성 미등록 참조이며 운영 자산을 조회하지 않는다.
- policy의 두 모드·layer 순서·blocker 복사 불변과 NaN/잘못된 JSON blocker 오류가 cycle보다 먼저 발생하는 기존 순서를 대조한다.

```powershell
# 프로젝트 루트, PYTHONPATH=.runtime;backend;tests
python -m unittest test_workflow_dependency_order -v
python -m unittest test_workflow_dependency_order test_workflow_policy test_workflow_lineage test_gmais_workflow_extension test_gmais_api -v
```

최초 집중 **9 PASS / 5.997초**의 [원 로그](../../evidence/integration/workflow-dependency-order-focused-20261017.log)를 보존했다. 이후 unique-root limit 사례를 실제 서로 다른 두 root로 강화했고 최종 집중 **9 PASS / 4.453초**의 [최종 로그](../../evidence/integration/workflow-dependency-order-focused-final-20261017.log)를 새로 남겼다. 두 실행 모두 통과했으며 실패를 덮어쓴 이력이 아니다.

관련 최종 **61 PASS / 13.116초**는 [관련 로그](../../evidence/integration/workflow-dependency-order-related-20261017.log)를 따른다. 신규9개는 관련 묶음에 포함되므로 별도 합산하지 않는다. 관련 기존 API 시험은 자체 임시 data root/bootstrap fixture를 사용하며 신규 원문 대조의 운영 main 미import 범위와 구분한다. Root 전체 회귀·독립 검토·원본/카탈로그 보존은 별도 최종 근거로 기록한다.

## UI 영향·실행 한계

API 응답과 topological_order의 원형 순서가 같고 새 endpoint·상태·오류·UI 선택 기능이 없다. UI 담당은 소비 경로를 읽기 검토하며 직접 프론트 수정·build·브라우저 재시험은 필요하지 않다. 원래 계획·진단의 실행/승인 false 및 데이터/모델 gate를 유지한다.

이번 코드 시험을 실행 중 서버의 새 모듈 로딩이나 운영 Workflow 동작 확인으로 표현하지 않는다. 특히 105/106의 이전 실제 UI/API 근거를 107의 live 검증으로 재사용하지 않는다. 실제 자산/권위·모델·과학·실행 승인, 수집·정식 학습·배포는 이번 범위 밖이다.

## Workflow 의존 순서 공통화 검증 완료 (107)

계획 API·현재 계보·차단 전파에 중복되어 있던 Kahn 의존 순서 계산을 순수 `topological_order` 함수로 모았다. 원래처럼 ready 한 계층 전체를 정렬·제거한 뒤 다음 계층을 계산한다. a:[],b:[a],z:[]은[a,z,b]이며 전역 heap 순서[a,b,z]로 바꾸지 않는다. helper는 입력 set을 복사하고 stuck이면None, 빈map이면[]을 반환한다. 기존 caller가 schema/duplicate/self/unknown·한도·오류 우선순위·한국어 오류·Store/manifest 접근 시점을 책임진다.

구현 담당은 helper·세 호출부·동등성 시험·문서107을 완료했다. 검토/UI 담당은 기존 원문과 새 호출부를 독립 검토하고 시험했다. 관련 61 PASS/13.116초, 신규 9 PASS/4.453초, 독립 61 PASS/13.845초다. 묶음 중복을 합산하지 않는다. Root 전체 backend는 1069건/1068 PASS/기존 Windows 1 SKIP/354.65초/exit0이다. 시험은 합성·격리 fixture이며 운영 Workflow 실행이나 과학 검증이 아니다.

이 변경은 기존 응답/오류/승인 제한을 유지하는 내부 공통화다. 신규 API·화면·자동 실행·resolver·동적 predecessor binding은 없다. UI 담당이 영향 읽기와 backend 동등성 근거로 UI 수정이 필요 없음을 확인했고 기존 프론트 byte는 보존했다. 이번 front/build/browser 재시험은 하지 않았다. 이전105/106의191PASS/빌드96modules·28.34초/브라우저11체크는 이전 근거다. 86/89/104의dag_validated=false를 새 공통 함수로 바꾸거나 승인하지 않았다.

보호 대상 141개·이전 증거 771개·catalog14건·기존 Job 본문은 보존했다. 기존 제품의 허용 변경은 세 caller 파일뿐이며 각 원문 사본을 남겼다. 원본/원장/lock/예약136314880B/분할/모델·QA차단4/학습BLOCKED를 유지한다. 운영 Job/모델 등록·수집·새 운영 QA·정식 학습·배포는0이다. 예약 ACTIVE와 실제 worker 상태는 별개이며 로컬 명령 패턴의 수집/학습 후보0은 원격/숨은 worker 부재까지 보장하지 않는다.

완료 코드와 시험 근거를 이해 에이전트에 전달해 쉬운 설명·이론·코드/데이터·시험·발표·FAQ·INDEX·변경 이력을 갱신했다. 다음은 실제 Workflow 입력 연결 대기열 재검토(PLANNED)이며 전체 프로젝트는 미완료다. 지속 개발과10분 담당별 보고를 유지한다.

근거: `evidence/integration/workflow-dependency-order-live-integrity-20261017.json`, `evidence/integration/workflow-dependency-order-runtime-start-20261017.json`. 최종 문서 감사·rawSHA snapshot은 `evidence/integration/workflow-dependency-order-closeout-20261017.json`을 따른다.

