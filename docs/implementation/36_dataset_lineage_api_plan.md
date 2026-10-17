# Dataset 계보 읽기 API 최소 연결 계획과 구현

작성·소스 확인: 2026-10-17, Asia/Seoul. 담당: data_pipeline. 최초 사전 검토는 **PLANNED** 문서 단위였다. 이후 root가 같은 최소안을 내부 구현 단위로 배정하여 별도 RFC router와 API 시험을 추가했다. 현재 상태는 **TESTED_SYNTHETIC / 내부 RFC 구현 완료**, **운영 자료 HTTP 검증·기관 ACL·서비스 인수는 미검증**이다. 실자료·카탈로그·원장·lock은 변경하지 않았다.

먼저 `AGENTS.md`, `CONTINUOUS_DEVELOPMENT.md`, 최신 재개 인계서를 확인했다. 개별 읽기 코어·UI 단위 완료를 전체 개발 완료로 보지 않으며 진행·보고 예약을 변경하지 않았다. 구현 담당은 `dataset_lineage_api.py`와 별도 시험을 소유하고, root가 `main.py`의 import/include_router만 연결했다. 기존 GMAIS router·upstream 계약·Dataset 목록/등록 경로는 보존했다.

## 현재 구현·검증 요약

- 코드: `backend/app/dataset_lineage_api.py:create_dataset_lineage_router(get_store)`.
- 연결: root가 기존 app에 새 router를 추가했다. 실제 `main.app` TestClient에서 인증 의존성 상속과 기존 `/api/datasets` 응답 보존을 검증했다.
- 관련 API 시험: **11 PASS / 3.668초**, [dataset-lineage-api-tests-20261017.log](../../evidence/integration/dataset-lineage-api-tests-20261017.log). 아래 코어13시험과 별도다.
- 보존: 요청·임시 원본·SQLite 바이트 불변, Store.put/Job queue 미호출, 새 Job/Result/Trace/등록 없음. HTTP 어댑터가 raw manifest·URI·경로·자격정보를 투영하지 않는다.
- 독립 검토: **11 PASS / 4.302초**, [독립 로그](../../evidence/integration/dataset-lineage-api-independent-tests-20261017.log). 추가로 현재 hash가 event loop 밖 worker thread에서 실행되고 임시 파일이 불변임을 실제 재현했다. 재현 결함은 발견되지 않았다. 전체 통합/live 근거는 root 인계 후 별도 확정한다.
- 미검증: 이 문서를 작성하는 시점에 새 endpoint의 실제 운영 자료 HTTP 호출·UI 계보 조회를 수행하지 않았다. 개발 서버 자동 reload 설정만으로 새 기능의 실제 HTTP 검증 완료를 주장하지 않는다.

## 실제 존재하는 경로와 코어

| 대상 | 현재 확인된 동작 | 이번 제안과의 경계 |
|---|---|---|
| `GET /api/datasets` | `backend/app/main.py`의 기존 `datasets` namespace 목록 | UI의 실제 6개 legacy 등록행. 고정 버전 Registry의 조회 API가 아님 |
| `POST /api/data/register`, `/api/datasets/prepare` | 기존 로컬 등록·준비 흐름 | 쓰기/작업 제출 경로이므로 이번 연결에서 호출하지 않음 |
| `dataset_registry.register_version/resolve_version` | `dataset_versions` namespace의 Python 불변 버전 코어 | ID/version·canonical manifest SHA·실제 artifact SHA를 구분하고 현재 로컬 자산 검증 |
| `dataset_lineage.verify_dataset_lineage` | root·transitive 부모의 읽기 검증 코어 | 13시험 PASS. [구현 기록35](35_dataset_lineage_verification.md) 참조 |
| GMAIS `/v1/datasets...` | 최초 조사 때 로컬·upstream 모두 경로가 없었고, 이번에 로컬 RFC 1개만 추가 | upstream v0.2에는 여전히 Dataset HTTP 경로가 없음 |

원문 [`api/openapi.yaml`](../../contracts/upstream/GMAIS-v0.2/api/openapi.yaml)은 Agent·Job·Result·모델 Update Ticket 경로를 제공하며 Dataset HTTP 조회 경로는 정의하지 않는다. Dataset Manifest schema가 존재한다는 사실은 Dataset HTTP API의 존재를 뜻하지 않는다. 기존 `/api/datasets` 응답·저장 namespace나 upstream 원문은 그대로 둔다.

## 구현한 endpoint와 요청

**내부 검토 RFC:** `POST /v1/datasets/lineage/verify`.

JSON으로 고정 참조와 작은 검사 한도를 받는 읽기 전용 진단이다. `/v1/workflows/plan`처럼 POST를 사용해도 저장·Job 제출·실행은 하지 않는다. ID/version은 원문 schema에서 경로 구분 문자 등을 금지하지 않는 일반 문자열이므로, 경로 조각으로 임의 제한하지 않고 body에서 정확히 받는다. 다른 URL이나 GET 방식으로 바꾸는 것은 후속 계약 변경 범위다.

```json
{
  "root_ref": {
    "id": "explicit-contract-fixture",
    "version": "1",
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "max_depth": 32,
  "max_nodes": 256
}
```

이 예시는 실제 등록자료나 검증 가능한 SHA를 뜻하지 않는 계약 형태다. `root_ref`는 id/version/sha256 세 필드만 허용하고 URI·파일 경로·manifest 원문·자격정보는 받지 않는다. id/version은 비어 있지 않은 문자열, SHA는 소문자 64자리 hex다. optional 한도는 기본 깊이32/노드256, 코어와 같은 깊이0~64/노드1~1,024로 제한하며 bool을 정수로 허용하지 않는다. 요청의 알 수 없는 필드는 400으로 거절한다.

`latest`/`current`처럼 형식은 문자열이지만 고정 참조가 아닌 버전은 코어의 `LINEAGE_REF_NOT_PINNED` 진단으로 차단한다. 이 경로는 artifact SHA를 요청한다. canonical manifest metadata SHA를 artifact SHA로 대체하거나 legacy Dataset ID에서 고정 버전·SHA를 추정하지 않는다.

## 구현한 응답

구조가 유효한 진단 요청은 통과·차단 모두 HTTP 200으로 반환한다. 이는 계보 진단 보고서를 반환했다는 뜻이며 접근 허가나 실행 성공 응답이 아니다.

```json
{
  "extension": "greenblue.dataset-lineage-verification.rfc1",
  "approval_status": "INTERNAL_REVIEW",
  "present_in_upstream_openapi": false,
  "evaluation_scope": "CURRENT_LOCAL_ASSET_CHECK_NOT_EXECUTION_AUTHORIZATION",
  "assessment_started_at": "2026-10-17T00:00:00Z",
  "assessment_finished_at": "2026-10-17T00:00:01Z",
  "diagnostic": {
    "schema_version": 1,
    "scope": "DATASET_LINEAGE_INTEGRITY_ONLY",
    "status": "BLOCKED",
    "root_ref": {
      "id": "explicit-contract-fixture",
      "version": "1",
      "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    },
    "nodes": [{
      "id": "explicit-contract-fixture",
      "version": "1",
      "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "status": "BLOCKED",
      "integrity_verified": false,
      "expanded": false,
      "authorization_verified": false,
      "blocker_codes": ["DATASET_VERSION_NOT_FOUND"]
    }],
    "edges": [],
    "edge_direction": "PARENT_TO_CHILD",
    "blockers": [{
      "code": "DATASET_VERSION_NOT_FOUND",
      "ref": {
        "id": "explicit-contract-fixture",
        "version": "1",
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      }
    }],
    "limits": {
      "max_depth": 32,
      "max_nodes": 256,
      "root_depth": 0,
      "hard_max_depth": 64,
      "hard_max_nodes": 1024,
      "depth_limit_reached": false,
      "node_limit_reached": false
    },
    "lineage_integrity_verified": false,
    "current_assets_revalidated": true,
    "authorization_verified": false,
    "execution_authorized": false,
    "scientific_approval": false,
    "network_requests": 0,
    "source_files_written": 0
  },
  "authorization_verified": false,
  "execution_authorized": false,
  "scientific_approval": false
}
```

위 JSON은 해당 고정 참조가 미등록인 임시 Registry를 가정한 **계약 예시**이며 실제 운영 호출 증거가 아니다. root 조회를 시도했기 때문에 `current_assets_revalidated=true`여도 자료가 없다는 blocker와 전체 무결성 false가 함께 표시된다. HTTP 어댑터가 core의 차단을 지우거나 승인 플래그를 true로 바꾸지 않는다. 결과·Job·Trace·감사 레코드와 입력 snapshot을 영속 저장하지 않는다.

응답은 코어의 정렬된 고정 참조·진단 allowlist만 투영한다. URI·원본/품질 보고서 경로·source metadata·manifest 원문·등록 record 전체·내부 예외·요청 raw body를 추가하지 않는다. 원문 Dataset Manifest에 RFC 필드를 삽입하지 않는다.

## 오류와 인증·접근 제한

| 조건 | 제안 HTTP / 결과 | 정보 최소화 |
|---|---|---|
| JSON/필수 필드/타입/허용 필드/SHA 형태/한도 오류 | 400, 기존 GMAIS `INVALID_REQUEST` error 형태 | Registry/자산을 읽기 전에 거절. 원문 입력·스택·파일경로를 오류 메시지에 넣지 않음 |
| 인증 token이 설정돼 있는데 누락·불일치 | 기존 app 인증 의존성의 401 | `/healthz` 등의 예외에 새 경로를 추가하지 않음. 기관 ACL 검증으로 해석하지 않음 |
| 고정 root 미등록 | 200 `BLOCKED` / `DATASET_VERSION_NOT_FOUND` | 진단 RPC이므로 엔티티 GET의 404와 구별. 별도 Dataset을 만들지 않음 |
| root/부모 SHA 불일치·손상·순환·깊이/노드 한도 | 200 `BLOCKED` / 코어의 고정 blocker 코드 | 실패 원문의 경로·URI·DB 내부 오류를 반환하지 않음 |
| 비PUBLIC root/부모 | 200 `BLOCKED` / `LINEAGE_ACL_NOT_IMPLEMENTED` | 해당 비공개 노드의 상위 lineage를 조회하거나 노출하지 않음 |
| 코어가 구조화한 Registry 오류 | 200 `BLOCKED` / `DATASET_REGISTRY_UNAVAILABLE` | 미등록과 시스템 오류를 고정 코드로 구별하되 raw DB 예외 미노출 |
| 어댑터 자체의 예측하지 못한 저장소/런타임 불가 | 503, 기존 `RESOURCE_UNAVAILABLE` error 형태 | 고정된 짧은 메시지만 반환. fallback 통과 응답 금지 |

새 경로는 기존 FastAPI app의 token 의존성을 그대로 상속하는 개발용 진단이다. 현재 기관별 사용자·자료 ACL은 미구현이며 공용 token을 기관 자료 열람권으로 간주하지 않는다. root의 id/version/SHA는 요청자가 지정한 값만 되돌려주고, restricted 부모는 공개 노드에서 이미 참조된 고정 식별자 및 차단 코드 이상의 상세를 추가하지 않는다. 비공개 manifest에만 있는 더 위 조상 식별자·경로·URI는 코어와 어댑터 양쪽에서 계속 숨긴다.

존재 여부와 접근 등급을 구별하는 진단도 운영 환경에서는 정보 노출 정책이 필요하다. 이번 제안은 그 정책이나 실제 기관 RBAC를 해결했다고 주장하지 않는다. 신규 공개 인터넷 서비스로 배포하지 않고 기존 로컬 인증 경계 내 내부 RFC로 제한한다.

## 현재 검사 시점과 성능 경계

- 요청마다 `verify_dataset_lineage()`를 새로 호출한다. Job의 저장된 제출 snapshot을 재생하는 `/v1/jobs/{id}/input-resolution`과 구별한다.
- UTC 시작·종료 시각은 검사 구간이다. 자료 취득 시각·업데이트 시각·독립 정확도 검증 시각이 아니다. UI가 필요하면 KST로 변환하되 원래 시간대를 구별한다.
- `current_assets_revalidated=true`는 코어가 현재 Registry/자산 해석을 한 번 이상 시도했다는 뜻이다. cutoff·실패·비공개 조상까지 전부 검사했다는 뜻은 아니다.
- 여러 파일의 순차 검사이며 그래프 전체의 원자적 snapshot이나 실행 직전 불변성을 보장하지 않는다. 검사 후 자산 변경은 재요청에서 검출한다. 실제 executor는 별도 입력 고정이 필요하다.
- 모든 200/400/503 응답에 `Cache-Control: no-store`를 설정한다. HTTP 캐시·이전 성공 결과를 현재 검증처럼 반환하지 않는다.
- 로컬 파일 해시는 blocking I/O다. async route에서 body를 읽고 검증한 후 `run_in_threadpool()`로 현재 검사·응답 투영을 옮겨 event loop를 막지 않는다. 새 Job queue·자동 retry·background 저장 작업은 만들지 않는다.
- 코어의 깊이/노드 한도를 유지한다. 개별 파일 크기·총 hash 바이트·동시 요청 부하 상한은 현재 코어가 보장하는 항목이 아니며, 이 제한을 운영 성능 검증 완료로 표현하지 않는다.

## 구현 경계와 시험

root의 후속 배정으로 별도 router의 새 진단 경로, 요청/응답 검증, 별도 API 계약시험을 구현했다. upstream 파일·기존 `/api/datasets`·등록 경로·실자료 버전·Job/Workflow gate는 변경하지 않았다. 임시 Store와 합성 파일의 로컬 계약 구현·시험에는 외부 기관 endpoint·자격정보·실자료 등록·추가 사용자 승인이 필요하지 않았다. 운영 자료의 공개·권한 부여·수집/학습/배포처럼 별도 승인 근거가 필요한 행동을 이 범위에 끼워 넣지 않았다.

| API 회귀 | 필요한 확인 |
|---|---|
| 정상 공개 root/부모와 같은 Dataset의 다른 고정 버전 | wrapper 식별자·시각·고정 참조·정렬 edge·true 무결성과 false 승인 분리 |
| 미등록 root/부모·wrong SHA·손상 record·SQLite 오류 | 표의 status/code, 민감 exception 비노출, fallback 통과 없음 |
| 동적 참조·같은 버전 상충 SHA·cycle·depth/node boundary | 코어의 fail-closed 결과 보존 및 HTTP 요청 한도 검사 |
| 제한 root와 제한 부모·비공개 조상 | ACL blocker, 비공개 상위 store.get 미호출, ID/URI/원문 비노출 |
| JSON/SHA/타입/bool/알 수 없는 필드 오류 | 400 및 Registry/파일해시 함수 미호출 |
| token 누락·정상 token | 기존 인증 경계 상속, 인증 실패 때 진단 body 미노출 |
| 자산 변경 후 같은 요청 반복 | 첫 성공을 재생하지 않고 현재 SHA 불일치를 다시 보고 |
| 모든 조회의 비쓰기 | 임시 원본·SQLite 바이트 전후 일치, Store.put/Job queue 호출 금지, Job/Result/Trace/등록 레코드 증가0 |
| 기존 호환 | `/api/datasets` 내용·Job Status schema·멱등 snapshot·Workflow PLAN_ONLY/gate 보존 |

API 시험은 기존 코어 13시험과 별도인 **11시험 PASS**다. `test_dataset_lineage_api.py`는 실제 main.app에서 token 누락401/정상 token200과 legacy namespace 보존도 검사했다. 형식 오류와 일반 오류는 vendored `error.schema.json`으로 검증했고, 코어의 SQLite 실패는 민감 원문 없는 200/BLOCKED 진단으로 전달했다. 같은 요청으로 자산을 다시 검사하며 SHA 변경을 검출하고, 응답의 중첩 확장 필드는 제거한다. 잘못된 root·상태 모순·승인true·network 계측 이상 등 코어 응답 이상은 일반 503으로 차단한다.

```powershell
$env:PYTHONPATH = "$PWD/.runtime;$PWD/backend;$PWD/tests"
$env:PYTHONIOENCODING = 'utf-8'
python -m unittest discover -s tests -p test_dataset_lineage_api.py -v
```

전체 통합 시험·실제 개발 HTTP 호출·UI 연결 증거는 이 관련 시험의 숫자로 대체하지 않는다. root가 최종 결과를 따로 확정하기 전에는 해당 범위가 완료되었다고 표시하지 않는다.

## UI 인계와 명시적 미구현

현재 카탈로그는 legacy `datasets` 목록을 표시한다. 그 6개 행을 `dataset_versions`로 자동 등록하거나 추정 버전/SHA로 계보 요청을 만들지 않는다. 이번 내부 API 구현은 별도 계보 요청 UI를 아직 추가하지 않았다. web_ui에 계약·상태·오류·검사 시각 의미와 시험 증거를 인계하며, 고정 참조를 명확히 가진 입력의 읽기 진단 UI만 후속 연결 대상으로 삼는다. legacy 미등록/미확인 상태도 실제 데이터로 검증해야 한다.

**완료:** 내부 RFC endpoint·엄격 요청 검사·응답 allowlist·현재 hash thread pool·API11시험. **미구현/미검증:** 운영 자료 HTTP 계보 인수, UI 계보 조회, 기관 ACL, 불변 파일 snapshot, 서명된 lineage event 감사, 운영 성능/보안 검증. 기존 [코어13시험](../../evidence/integration/dataset-lineage-tests-20261017.log)과 [합성 증거](../../evidence/integration/dataset-lineage-synthetic-20261017.json)는 이 HTTP의 실제 운영 실행 증거로 재분류하지 않는다.


## Root 통합·실제 루프백 검증

2026-10-17 KST: main router 배선 후 UI5174 동일출처 proxy→API8002에서 명시 미등록 참조200 BLOCKED/DATASET_VERSION_NOT_FOUND, bool한도400, 양쪽no-store를 확인했다. 실제 브라우저 상세의 빈수동폼·미등록 차단·현재확인시도≠성공/승인구분·latest금지/이전결과제거·고정버전복귀재조회를 확인했다. 모바일390×844에서 dialog351px/문서375px로 전체 가로 넘침없음. 보호5파일SHA불변·기존gmais_jobs2건보존·신규실행0. 성공/자산변조/ACL은 임시fixture시험이며 실자료 성공 진단을 만들지 않았다. 전체 scripts/test.ps1 **298건/297PASS/1SKIP/88.188초·종료0**, evidence/integration/dataset-lineage-api-full-tests-20261017.log. 실제증거 dataset-lineage-api-live-20261017.json·dataset-lineage-*-desktop/mobile.png.
