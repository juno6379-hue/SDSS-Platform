# ML 고정 split 복구 파생 계획 — 2026-10-17

## 상태와 범위

**VERIFIED_REAL(메타데이터만):** 기존 원본 manifest와 고정된 readiness의 SHA·원본 scene 식별자·고정 지역 split·수집 적격 계수를 읽어 계획을 생성했다. **TESTED_SYNTHETIC:** 격리된 임시 JSON으로 8개 회귀시험을 통과했다. **PLANNED:** 실제 파생 manifest 발행·전체 raster QA·후속 학습이다. **BLOCKED:** bare 대표성·공간누출 재검증·독립 현장 검증·승인이다.

기본 실행은 새 evidence JSON 하나만 만든다. 기존 원본/라벨/분할/모델/수집 원장/기존 readiness를 수정하지 않았으며, 4,335파일 전체 재감사·수집·학습을 실행하지 않았다. 새 후보 manifest의 누출 해결을 과학적 독립 검증이나 모델 성능 승인으로 표시하지 않는다.

## 구현과 선택 정책

### 선택적 JSON 입출력 제한 — 후속 구현 70

`plan_split_repair`, `digest`, `write_plan`에 `io_policy=None` 선택 키워드를 추가했다. 생략하면 기존 경로를 유지한다. 명시하면 source/readiness 등 역할별 바이트 제한과 깊이 제한, strict JSON, 명시 SHA 및 재읽기 안정성 검사를 사용한다. writer는 plan/candidate 두 출력 크기를 디렉터리·파일 생성 전에 모두 측정하고 새 파일만 제한된 스트림으로 기록한다. Windows 줄바꿈을 포함한 기존 writer 바이트 형식도 회귀 확인했다. 정책 구조·사용 예·검증 근거는 [70 입출력 계약](70_split_bounded_io.md)을 참조한다.

이 선택 정책은 기존 CLI에 자동 활성화되지 않는다. 각 읽기/출력 제한은 누적 IO·프로세스 메모리 상한 또는 원자적 파일 거래를 보장하지 않는다. 쓰기 오류나 최종 입력 대조 실패로 남은 새 파일을 완료 후보로 사용하면 안 된다. 완료 receipt·evidence 경로 제한·생성 후 validator 연결은 다음 조정 단위이며, 이번 실제 후보 생성은 없다.

- `backend/app/ml/split_planning.py`의 `plan_split_repair`: 입력 manifest를 명시한 SHA로 고정하고 `scene_id`, `source_group`, 기록된 영상 SHA가 연결하는 전이적 component를 찾는다. 각 행의 기존 split이 고정 province split과 다르면 거부한다. 식별자/품질 상태가 없는 입력도 추측하지 않고 거부한다.
- 여러 split에 걸친 component는 **test → val → train**의 사전 고정 우선순위로 한 split만 남긴다. 우선순위는 평가 결과·라벨·클래스 분포를 보지 않는다. test를 보존하는 보수적 정책이며, 더 많은 행을 남기는 최적화 정책은 아니다. 다른 split의 충돌 행은 새 후보에서만 제외하며 split을 다시 배정하지 않는다.
- source identity 충돌이 없는 행은 그대로 보존한다. 원본 scene과 무관한 **기하학적 공간 중첩은 재검사하지 않는다**. 따라서 `remaining_source_identity_conflicts=0`은 이 메타데이터 동치관계에만 해당한다.
- `write_plan`: 출력 직전 원본/readiness SHA를 재확인한다. 기존 파일 및 원본/readiness 경로를 덮어쓰지 않으며 서로 다른 새 경로만 허용한다. `--derived-manifest`를 명시하면 원본 행을 그대로 복사한 `PLANNED_DERIVED_CANDIDATE`를 별도 생성할 수 있다. 기본 실행에서는 생성하지 않는다.
- 후보 버전은 원본 SHA, 고정 province split, 우선순위, 보존 row index, planner 버전으로 결정한다. 후보의 `lineage`는 원본 SHA·경로·선택 정책·원본 row index를 기록한다. `learning_ready=false`, `executed=false`를 유지한다. 기존 수집 총계/ready 플래그를 복사하지 않는다.

## 실제 계획 결과

입력 SHA는 `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`, readiness SHA는 `6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db`다. 두 자료의 원본 참조·split 계수가 일치하는 것을 확인했다. 결과는 [ml-split-repair-plan-20261017.json](../../evidence/integration/ml-split-repair-plan-20261017.json)이다.

충돌은 `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431` 한 component다. test인 West Java12행(적격9)을 보존하고 val인 Banten16행(모두 적격)을 후보에서 제외하는 계획이다. 원본 행 index288~303이 제외 목록에 기록됐다. 후보 예정 버전은 `split-repair-v1-754e7a5a0569eb9b`다.

| 항목 | 원본 | 후보 예상 | 해석 |
|---|---:|---:|---|
| 물리 행 | 1,384 | 1,368 | 원본 삭제 없음; 선택 index만 계획 |
| 적격 총량 | 1,111 | 1,095 | 최소1,000 바닥 유지 |
| train | 628 | 628 | 최소600 유지 |
| val | 233 | 217 | 최소100 유지, 대표성 악화 가능 |
| test | 250 | 250 | 최소100 유지 |
| Banten2021 적격 | 58 | 42 | 유일하게 감소한 주·연도 셀, 계획 바닥28보다 많음 |
| 적격 주·연도 | 36 | 36 | 다른 셀 계수 동일; 모든 셀의 충분성 승인을 뜻하지 않음 |

정확한 클래스 통계는 새 후보 raster를 읽지 않았으므로 **미계산**이다. 기존 readiness의 클래스 픽셀/기여 패치 수를 상한으로, 제외 적격 패치당 최대65,536픽셀 제거를 하한으로 표시한다. 남은 적격 패치당 최소80% 유효 픽셀을 분모 하한으로 사용하여 bare 비율 상한도 제시했다. 이는 예측/성과가 아닌 보수적 범위다. val의 다른 클래스 대표성도 악화될 수 있으며 정확한 변화는 후속 QA가 필요하다.

bare 기여 패치의 상한은 여전히 모든 split에서 **0**이다(요구≥5). bare 비율의 보수적 상한도 train0.004307%/val0.001837%/test0.007820%로 요구0.5%보다 작다. **이 제외 계획은 bare 부족을 해결하지 않는다.**

## 재현과 회귀 증거

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_ml_split_planning.py -v
```

**8 PASS, 0.290초.** 전이적 source 누출 제거/test 보존, 무충돌 입력의 재현성, 서로 다른 scene의 동일 영상 SHA, 잘못된 원본 SHA/출처, 계획 후 stale source, stale readiness 원본참조, 클래스 상하한/미해결 표시, 원본·기존 출력·stale readiness 덮어쓰기 방지를 검사했다. 새 후보 행이 원본 행과 같고 원본 bytes가 불변인 것도 검증했다.

실제 dryrun 명령은 다음과 같다. evidence 경로가 이미 있으므로 재현 시 새 `--output`을 지정해야 한다.

```powershell
python scripts/plan_training_split_repair.py `
  --manifest data/first-group-training-esri-v1/annual-window-report.json `
  --expected-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --plan data/first-group/experiment-esri-v003-2020-2025.json `
  --readiness data/first-group/readiness-resume-20261017.json `
  --readiness-sha256 6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db `
  --output evidence/integration/ml-split-repair-plan-20261017.json
```

## 다음 조건

root/data owner가 test 우선의 validation 감소를 검토한 뒤 새 버전 후보를 별도 경로로 발행할 수 있다. 후보는 전체 파일 SHA·기하 중첩·연차/주별 대표성·클래스를 다시 검증해야 하며 기존 readiness를 재사용하지 않는다. bare 관측 보강 계획과 독립 현장 라벨·전문가 승인·운영 인수는 별개로 남는다. 명시적인 후속 작업 없이 수집/학습/모델 등록을 자동 실행하는 기능은 없다.

## 저장 계획의 후속 읽기 검증

[문서44: ML split 복구 계획 검증](44_ml_split_repair_validation.md)의 별도 검증기는 호출자가 고정한 원본/readiness SHA와 province split으로 계획을 재계산해 저장 계획 전체를 타입까지 대조한다. 선택 후보는 이미 존재할 때만 명시 SHA와 원본 행·lineage를 대조한다. 후보를 지정하지 않은 `NOT_REQUESTED/null`은 후보 존재 여부를 확인했다는 뜻이 아니다. 이 검증 성공은 파생 manifest 발행, raster·공간 중첩·정확한 클래스 재검사 또는 학습/운영 승인을 대신하지 않는다. 실제 실행 결과와 최신 회귀는 문서44 및 최신 인계서를 참조한다.

## 후속 실제 후보 패키지 — 구현 71

[71 후보 생성·재검증](71_candidate_materialization.md)에서 기존 bounded writer/validator를 연결하여 새 evidence 후보1368행과 마지막 완료receipt를 실제 생성·대조했다. 원본1384행은 보존하며 후보계획 적격1095는 실제 raster 준비성 결과가 아니다. 후보는 PLANNED_DERIVED_CANDIDATE/learning_ready=false/executed=false, 미등록·readiness NOT_ASSESSED다. 이 문서의 이전 미생성/PLANNED 기록은 해당 단위의 역사이며, 최신 생성 상태는71의 고정 SHA/근거를 참조한다.
