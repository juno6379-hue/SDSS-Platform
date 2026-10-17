# 111 — 수집 자료를 공통 Metadata/Lineage Registry에 연결

상태: **TESTED_SYNTHETIC — 실제 등록 CLI 연결 완료 / 실자료 등록 미실행**. 6개 주×2020~2025 로컬 재고를 metadata로 확인하고, 기존 수집 등록 CLI에 공통 `dataset_versions` 등록 경로를 연결했다. Data Pipeline 전체 완료나 AI-ready 품질 Gate 통과는 아니다.

## 실제 연결한 공백

기존 `scripts/register_collection.py`는 수집 파일 SHA를 검증해 legacy `datasets`의 `source-crop-collection`에 기록했지만 고정 Dataset ID/version/SHA/lineage를 사용하는 공통 Registry에는 기록하지 않았다. 현재 읽기 전용 SQLite 관측에서도 legacy datasets 6개, 공통 dataset_versions 0개였다.

새 `--registry-manifest` 선택 시 `backend/app/data/collection_registration.py`의 `register_collection_version`을 호출한다. 실제 image/label/quality 파일과 source report를 검증한 뒤 기존 `dataset_registry.register_version`의 immutable version transaction에 연결한다. 같은 CLI의 옵션 없는 경로는 기존 원문과 동등하게 유지한다. GMAIS 원 schema·공통 Registry 코어·API·Job/학습 Gate는 변경하지 않았다.

새 모드는 **legacy datasets 쓰기 없이 공통 dataset_versions에만** 등록한다. 두 namespace 동시 쓰기나 한쪽만 성공하는 이중 등록을 추가하지 않았다. 필요하면 두 작업을 별도로 실행해야 하며 그 두 호출의 원자성은 제공하지 않는다. 공통 버전의 같은 내용 재등록은 최초 기록을 반환하고 같은 ID/version의 다른 내용은 기존 코어가 거부한다.

## 호출 계약과 품질 제한

```powershell
$env:PYTHONPATH = '.runtime;backend;tests;.'
python scripts/register_collection.py --data-root <별도_등록_루트> --manifest <해당루트의_annual-window-report.json> --id <명시적_dataset_id> --registry-manifest <GMAIS_Dataset_Manifest.json>
```

위는 사용법이며 운영 data에 실행하지 않았다. 기존 명령에서 `--registry-manifest`만 생략하면 기존 source-crop 등록 방식이다. 새 모드는 source report 한 개만 허용한다. Dataset Manifest JSON은 호출자가 schema/version/source 기관·product·license/access/spatial/temporal/lineage를 명시해야 하며 자동 생성·추정하지 않는다. `--id`는 manifest의 dataset_id와 정확히 같아야 한다.

Dataset Manifest는 기존 vendored GMAIS v0.2 schema를 통과해야 한다. artifact_uri는 선택한 source report와 정확히 같은 로컬 파일이어야 하고 SHA도 원문 바이트에 일치해야 한다. 자료형은 `document`, quality_status는 **RAW 또는 STAGED만** 허용한다. 수집 보고서 등록이 raster의 STANDARDIZED/VALIDATED 품질을 인증하는 경로가 되지 않도록 제한했다. 상향된 품질 등록은 별도 검증 절차의 책임이며 이 CLI가 수행하지 않는다. 사용자가 적은 기관·공간 범위·관측 기간·라이선스의 업무적 진실성을 인증하지 않는다.

보고서의 `rgb_window_downloaded` 행을 대상으로 image/label/quality 세 파일 경로와 SHA를 모두 요구한다. grid의 patch_sha256 또는 명시된 기존 window-state cells 근거를 사용하고 source row가 가리키는 파일과 동일한지 확인한다. 완료 행은 6개 주 중 하나와 정확한 2020~2025 연도를 식별해야 한다. 모든 완료 행의 무결성이 확인되어야 등록하고, 실패/no-scene 행을 성공 개수로 올리지 않는다. 부분 연도/지역 보고서도 RAW/STAGED 출처 자료로 등록할 수 있지만 36셀 확보나 학습 승인을 부여하지 않는다.

모든 직접 lineage 부모를 기존 `resolve_version`으로 현재 asset SHA까지 재검증한다. self/동일 ID-version 중복 참조는 거부한다. 이는 **직접 부모의 고정 참조** 검사이며 전이적 전체 DAG 검사·자료 ACL·기관 권위 검증은 아니다. 전체 lineage의 cycle/깊이/권한 검토는 기존 별도 `verify_dataset_lineage`의 책임이며 이번에 그 응답을 승인으로 바꾸지 않는다.

파일은 data root 내부로 제한하고 remote/UNC/탈출 경로를 거부한다. JSON은 duplicate key·비유한 수·비객체를 거부하며 registry manifest 1MiB/source report·window-state 64MiB, scenes 최대20,000행을 제한한다. source 파일 SHA는 streaming으로 계산한다. 검사 전후 stat과 등록 직전 logical 경로/파일 stat/report SHA를 다시 확인한다. 원본을 복사·수정하지 않는다.

반환은 기존 DatasetVersion record를 `dataset_version`에 담고 downloaded_windows·중복 파일을 제외한 verified_file_count·quality_gate=`SOURCE_FILE_HASHES_ONLY`를 제공한다. training_ready/scientific_accuracy_validated/deployment_approval는 항상 false다. source report artifact만 Registry의 지속 hash 대상이며 검사된 이미지/라벨/품질 파일 전체의 불변 복사본을 저장하지 않는다. legacy window-state 내용 자체를 새 lineage로 자동 추가하지 않는다. 파일 검증 후 교체 가능성까지 없애는 DB/파일 간 원자 snapshot·전역 lock·불변 object store는 미구현이다. 출력은 등록 당시의 검증 범위다.

CLI는 기존처럼 `Store(..., recover_jobs=False)`를 열며 대상 DB가 없다면 테이블 초기화가 일어날 수 있다. 실패 시 새 DatasetVersion/legacy dataset record를 등록하지 않지만 Store 생성까지 읽기 전용이라고 표현하지 않는다. 함수 시험은 이미 생성한 격리 Store를 사용하며, 잘못된 파일/manifest는 첫 등록 transaction 전에 차단한다. 등록 호출은 명시적 로컬 작업이고 자동 수집·다운로드·QA·훈련을 실행하지 않는다.

## 6개 주×6개 연도 실제 확보 현황

2026-10-18 00:15 KST의 로컬 metadata 관측이다. 원본 aggregate source report 53,868,103B/SHA `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`를 한번 읽어 읽기 전후 stat 동일을 확인했다. config SHA `8b0c1b2aad13a3344200998ec62a18853c5308adf4ec57b1af835333845fd7e3`, ledger SHA `154004a2527c7ef6e93bec0c8a3ebf00a2af8e0683a1d4ed5252d59769da74a8`다. SQLite는 URI mode=ro로 조회했다.

표의 값은 원본 manifest의 `quality_status=quality_eligible` 행 수이며 새로운 raster QA 결과가 아니다.

| 주 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| South Sulawesi | 53 | 32 | 29 | 36 | 36 | 30 |
| Gorontalo | 46 | 31 | 14 | 30 | 25 | 8 |
| Southeast Sulawesi | 41 | 18 | 26 | 18 | 1 | 23 |
| Banten | 53 | 58 | 51 | 32 | 23 | 16 |
| West Java | 57 | 41 | 56 | 32 | 32 | 32 |
| East Java | 23 | 16 | 34 | 28 | 16 | 14 |

물리1384/manifest 적격1111, split628/233/250, 적격행이 있는 셀36/36이다. 이는 부분 창/patch 재고이며 주 전체 공간 coverage·연도별 대표성·독립 정확도·AI-ready 완료를 뜻하지 않는다. 특히 Southeast Sulawesi2024는 적격1개다. staging 후보 QA의1368/1095·628/217/250과 원본 재고를 섞지 않는다. 기존 후보 차단4/학습 BLOCKED는 유지한다.

기존 config는 여섯 주의 representative bbox와 province_bbox를 따로 둔다. `collect_first_group_annual.build_plan`은 36셀·고정6밴드·작업별 예산을 계획하고 execute 선택과 분리한다. 이번에 실제 수집 계획/원본 config를 바꾸거나 실행하지 않았다. 공적 경계·대표성·다운로드 예산을 확인하지 않고 전체 주 수집으로 확대하지 않는다.

pending은 기존 Banten/West Java2023 두 batch이고 예약합136,314,880B를 보존했다. terminal/전송완전성·원자적 복구를 확인하지 않아 정산/환불/재개하지 않는다. source inventory 근거는 `evidence/integration/data-pipeline-inventory-20261018.json`이며 raster0/candidate QA읽기0/network0/catalog writes0이다. 읽기 시점의 Python 수집/훈련 프로세스 후보는0, uvicorn8000/8001/8002만 관측했다. 숨은/원격 프로세스까지 단정하지 않는다.

## 수락 조건: 이번 완료와 잔여 차단

| 항목 | 이번 수락 근거 | 남은 조건 |
| --- | --- | --- |
| 6주 AOI별 계획/연차 기록 | 기존 plan·bbox·36셀 metadata와 SHA 확인 | 대표점/부분 patch를 주 전체로 확장할 수 없음. 정당한 경계·공간/계절 대표성·예산 필요 |
| 공통 Metadata Registry 연결 | 새 CLI에서 실제 파일 SHA→고정 GMAIS manifest→기존 단일 immutable version 등록·resolve 합성 E2E | 운영 자료 등록은 미실행. caller의 출처·라이선스·기관 권한 검토 필요 |
| Lineage 연결 | 직접 부모 고정version/SHA의 기존 resolver 재검증과 자기/중복 참조 거부 | 전이적 DAG·ACL/기관 승인·지속 자산 불변성은 별도 |
| 품질 Gate | 해시/경로/상태/연도/완료 source 행 검증 실패 시 등록 거부, RAW/STAGED 외 거부 | SCL/정규화·라벨 연도/분류체계·class7·누출/독립성·공간대표성·과학 검증. 해시 통과로 Gate READY 변경 불가 |
| 실제 수집 복구 | 원장/예약/lock/원본/분할/모델 불변 | missing terminal2와 전송계측·durable journal/coordinator 미완료.110 선언 검사는 실제 적용 증거 아님 |

## 시험·증거·관련 문서 인계

수정 기존 파일은 `scripts/register_collection.py`의 선택 옵션/새 branch뿐이다. 원문 사본 `evidence/integration/data-pipeline-original-register-collection-20261018.py` SHA `2d99a02d6227060c47b22e8d1b99c41db0b171a3fe030e1853551053fe23e26b`를 시험에서 고정한다. legacy 경로는 같은 합성 자료·고정 clock에서 원본 코드와 레코드 동등성을 검사했다.

최초 신규11 PASS/4.844초·관련37 PASS/8.291초 로그를 보존했다. logical path 재해석 보강 후 최종 신규 **12 PASS/4.114초/exit0**, `evidence/integration/data-pipeline-focused-final-20261018.log`다. 최종 관련은 **51 PASS/10.453초/exit0**, `evidence/integration/data-pipeline-related-final-20261018.log`다. 실제 TempStore 공통 등록/resolve·동일 재등록·다른 version 내용 거부·명시 부모·누락/자가/중복 lineage·변조·missing 품질·경로/row binding·strict JSON/size·report 변경·logical retarget·기존 CLI 동등을 시험했다. 신규/관련 중복 시험을 합산하지 않는다. 독립 검토·최종 보존은 Root 통합 근거를 따른다.

새 CLI와 helper는 운영 서버 route를 바꾸지 않으며 사용자 화면의 새 endpoint가 없어 UI 수정은 필요 없다. 테스트 반영과 운영 자료 등록·실제 서버 적용을 구분한다. Root는 관련 설계/인계/원장과 이해 에이전트의 해설·발표 대본·FAQ·INDEX·변경 이력을 통합한다. 이 단위만으로 사용자가 요청한 Data Pipeline 전체 완료를 선언하지 않는다.
