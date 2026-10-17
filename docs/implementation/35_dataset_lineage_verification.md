# Dataset 계보의 현재 자산 읽기 검증

작성: 2026-10-17, Asia/Seoul. 담당: data_pipeline. 구현 경로는 `backend/app/dataset_lineage.py`, 독립 시험 경로는 ml_pipeline 소유 `tests/test_dataset_lineage.py`다.

## 범위와 상태

**TESTED_SYNTHETIC:** 임시 Registry의 실제 로컬 파일과 고정 SHA로 계보 검증 코어를 시험했다. **IMPLEMENTED_UNVERIFIED:** 운영 자료의 실제 계보를 등록하거나 인수한 것은 아니다. 기존 Dataset Registry/API·실자료·수집 원장·lock은 변경하지 않았다. 이 단위는 기존 `resolve_version()`을 호출하는 읽기 전용 함수이며 새 HTTP endpoint나 파일 등록 기능을 추가하지 않는다.

현재 자산의 바이트 SHA 확인과 계보 구조 검증은 기관 접근권한·독립 과학 검증·모델 실행 승인과 별개다. 반환의 `authorization_verified`, `execution_authorized`, `scientific_approval`는 모두 false다. `network_requests=0`, `source_files_written=0`이며 Store 쓰기를 호출하지 않는다.

## 호출과 응답

```python
result = verify_dataset_lineage(
    store, dataset_id, version, artifact_sha256,
    max_depth=32, max_nodes=256,
)
```

`store`는 호출자가 이미 보유한 Registry 접근 객체다. 검증 함수가 Store를 새로 만들거나 초기화하지 않는다. 입력 SHA는 canonical manifest 본문의 SHA가 아니라 Dataset Manifest의 `sha256`, 즉 실제 자산 바이트 해시다.

응답 `schema_version=1`, `scope=DATASET_LINEAGE_INTEGRITY_ONLY`이며 다음 필드를 반환한다.

| 필드 | 의미 |
|---|---|
| `root_ref` | 조회한 고정 id/version/sha256. 형식이 틀리면 null |
| `status` | blocker가 없으면 `INTEGRITY_VERIFIED`, 그 밖에는 `BLOCKED` |
| `lineage_integrity_verified` | 조회 범위의 자산·고정 신원·계보 구조·접근 정책 진단을 모두 통과했는지 |
| `current_assets_revalidated` | 이번 호출에서 `resolve_version()`을 한 번 이상 시도했는지. 모든 조상이 성공했다는 뜻은 아님 |
| `nodes` | 정렬된 고정 참조와 노드별 자산 무결성·확장 여부·차단 코드. 알려진 품질/접근 등급 enum만 포함 |
| `edges` | `source=부모`, `target=자식`인 고정 참조 쌍. `edge_direction=PARENT_TO_CHILD` |
| `blockers` | `{code, ref}` 목록. 내부 예외·manifest 원문·파일 경로·URI는 포함하지 않음 |
| `limits` | 적용한 깊이/고유 참조 한도와 한도 도달 여부 |

노드의 `integrity_verified=true`는 그 노드의 실제 자산과 고정 신원을 확인했다는 뜻이다. 부모 누락이나 다른 노드의 차단이 있으면 전체 `lineage_integrity_verified`는 false다. `expanded=true`는 해당 노드의 부모 참조를 검사 순회했다는 뜻이며 전체 부모의 성공·운영 승인을 의미하지 않는다.

## 결정성·한도·접근 제한

참조의 신원은 `(id, version, sha256)`이다. 같은 dataset_id라도 서로 다른 고정 version은 정상 계보로 허용한다. 같은 id/version에 서로 다른 SHA가 나오면 `LINEAGE_REFERENCE_CONFLICT`다. 부모 중복과 diamond의 공유 부모는 하나의 노드와 edge로 정리하고, 각 고유 참조의 `resolve_version()` 호출은 한 번으로 제한한다. 입력 부모의 순서나 임시 저장 경로가 달라도 같은 계보의 응답은 같다.

root 깊이는 0이다. `max_depth=1`이면 직계 부모까지 검사하고 조부모를 읽지 않는다. 먼저 얕은 경로에서 확인한 공유 노드가 더 깊은 경로에서 다시 나타나면, 자산을 다시 읽는 대신 그 경로의 깊이 한도를 다시 평가한다. 기본 한도는 깊이 32, 고유 참조 256개다. 설정 가능한 범위는 깊이 0~64, 고유 참조 1~1,024이며 bool·범위 밖 값은 `INVALID_LIMITS`로 차단한다. 고유 참조 한도는 root 및 실패한 resolve 시도를 포함한다.

root나 부모가 `RESTRICTED`/`CONFIDENTIAL`이면 자산 무결성 검사와 별개로 `LINEAGE_ACL_NOT_IMPLEMENTED`를 추가한다. 해당 비공개 노드의 상위 lineage는 확장·조회·출력하지 않는다. 따라서 비공개 manifest에만 있는 더 위 조상의 ID·URI도 반환하지 않는다. 이는 ACL 구현이나 권한 부여가 아니라 권한 미연결 차단이다.

이 함수는 일반 품질 상태를 과학 승인으로 해석하지 않는다. 예를 들어 `RAW` 자체를 독립 정확도 합격이나 불합격으로 판정하지 않고, 현재 파일과 계보가 고정 참조에 맞는지만 검사한다. `VALIDATED`인 자료는 기존 Registry 검증기가 요구하는 로컬 품질 보고서 존재 조건도 유지한다.

## 차단 코드

- 입력/한도: `INVALID_ROOT_REF`, `INVALID_LIMITS`, `LINEAGE_REF_NOT_PINNED`.
- Registry/자산: `DATASET_VERSION_NOT_FOUND`, `DATASET_RECORD_CORRUPT`, `DATASET_REGISTRY_UNAVAILABLE`, `LINEAGE_INTEGRITY_FAILED`.
- 그래프/접근: `LINEAGE_REFERENCE_CONFLICT`, `LINEAGE_CYCLE`, `LINEAGE_DEPTH_LIMIT`, `LINEAGE_NODE_LIMIT`, `LINEAGE_ACL_NOT_IMPLEMENTED`.

기존 Registry의 canonical manifest 검사는 부모 참조의 `latest`/`current`도 먼저 거부한다. 이미 손상된 카탈로그 레코드에 동적 부모 참조가 있는 경우에는 그 상위 manifest의 `LINEAGE_INTEGRITY_FAILED`로 차단될 수 있다. 외부 예외 메시지를 분석해 비공개 경로나 원문을 되돌려주지 않는다.

## 검증과 재현

```powershell
$env:PYTHONPATH = "$PWD/.runtime;$PWD/backend;$PWD/tests"
$env:PYTHONIOENCODING = 'utf-8'
python -m unittest discover -s tests -p test_dataset_lineage.py -v
```

최종 **13시험 PASS**다. ML 담당 실행은 5.842초이며 로그는 [dataset-lineage-tests-20261017.log](../../evidence/integration/dataset-lineage-tests-20261017.log)다. 구현 담당도 최종 13시험을 독립 재실행해 3.317초에 통과했다. 시험은 임시 SQLite·로컬 합성 파일을 사용하며, 각 호출 전후 모든 원본/Registry 파일 바이트가 같은지 확인하고 Store.put을 실패 처리해 쓰기 호출도 차단한다.

시험에는 공개 root→부모→조상, 현재 부모 자산 변경의 재검사, 미등록/wrong SHA, 동적 root, cycle, 같은 Dataset의 정상 연차 버전, 같은 버전의 SHA 충돌, diamond 중복 조회 방지, 깊이/노드 한도 경계, 부모 순서 결정성, 제한 조상의 상위 조회·ID 노출 차단, 선택 URI/role 비노출, 손상 레코드/SQLite 오류의 구조화가 포함된다. 먼저 얕게 검증한 공유 부모가 더 깊은 다른 경로에서 다시 등장할 때도 한도를 우회하지 않고, 각 고유 자산 조회는 한 번임을 추가 확인했다.

별도 [합성 결과 증거](../../evidence/integration/dataset-lineage-synthetic-20261017.json)는 `evidence_scope=TESTED_SYNTHETIC_ONLY`로 표시한다. 공개 계보의 무결성 통과와 제한 계보의 ACL 차단을 함께 담고, 임시 원본/DB 바이트 불변과 비공개 조상 ID 미노출을 확인했다. 실자료 Dataset 등록이나 운영 계보의 인수를 뜻하지 않는다. 독립 소스 검토에서도 추가 재현 결함은 발견되지 않았다.

## 남은 작업

현재 검사는 여러 파일을 순차적으로 읽는 시점 검사다. 전체 그래프에 대한 원자적 파일 snapshot이나 서명된 출처 진위 증명으로 해석하지 않는다. 검증 이후 파일이 바뀌면 다음 호출에서 다시 검사하며, 실제 실행 시점의 불변 입력 고정은 후속 executor 책임이다. 운영 ACL·독립 라벨/과학 검증·기관 승인·HTTP 연계는 별도 후속 작업이다.
