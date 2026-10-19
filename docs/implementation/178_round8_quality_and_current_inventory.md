# 178 — 8차 독립 품질 감사와 고정 현황

- 상태: **VERIFIED_REAL** — 2026-10-18 11:54 KST 관측의 완료된 8차 증분. 이후 수집은 이 고정 수치 밖이다.
- 소유 범위: 읽기 전용 감사·신규 증거·이 문서. 수집 재실행, 원본·원장·잠금·모델·제품 코드 변경은 없다.

## 실제 완료 증분

반텐 2024년 g01/g02 두 배치를 기존 `scripts/audit_priority_increment165.py`와 실제 `data/first-group-boundaries/selected-six.geojson`으로 독립 검사했다. 새 32패치의 영상·참조라벨·품질 배열에서 26적격, 적격 나지 199픽셀을 확인했다. 96래스터와 8설정·종료문서의 SHA를 재검산했으며 22.9645378초가 걸렸다. 이 시간은 단일 로컬 관측이고 SLA가 아니다.

| 항목 | 확정 결과 |
|---|---:|
| g01 물리 / 적격 | 16 / 11 |
| g02 물리 / 적격 | 16 / 15 |
| 전체 원본 물리 / 적격 / 적격 외 | 1,601 / 1,286 / 315 |
| 기존 원본 canonical 행 보존 | 1,569행 |
| 기존 pending 보존 | 2건·136,314,880B |
| 새 2건 정산 | 45,131,651B |
| 누적 추가 계상 / 기존 4GiB 한도 잔여 | 2,221,278,493B / 2,073,688,803B |
| worker 오류 / scene 실패 / 429 | 모두 0 / false |
| 감사 중 원본·원장 변경 / 실행 잠금 | 모두 없음 |

보존 검사는 기존 행의 canonical 내용과 pending 문서를 대상으로 했다. 이번 감사가 기존 모든 래스터를 다시 읽었다는 뜻은 아니다. 종료된 collector는 실제 프로세스 목록에서도 발견되지 않았다. `parallel_collecting`이라는 원본의 마지막 상태 문구만으로 실행 중이라고 판단하지 않는다.

## 주·연도별 적격 패치

계획의 28개는 각 셀의 **최소 확보량**이다. 연도별 동일 개수로 맞춘 학습 표본과 전체 확보 자료는 다른 개념이다. 초과 확보분을 삭제하거나 부족 셀의 충족으로 대체하지 않는다.

| 주 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 합계 | 최소28 대비 부족 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 남술라웨시 | 53 | 32 | 40 | 36 | 36 | 30 | 227 | 0 |
| 고론탈로 | 46 | 31 | 24 | 30 | 25 | 18 | 174 | 17 |
| 남동술라웨시 | 41 | 27 | 26 | 33 | 10 | 23 | 160 | 26 |
| 동자바 | 23 | 32 | 34 | 28 | 39 | 27 | 183 | 6 |
| 반텐 | 54 | 58 | 51 | 32 | 49 | 48 | 292 | 0 |
| 서자바 | 57 | 41 | 56 | 32 | 32 | 32 | 250 | 0 |

셀 부족은 **54→49개 패치**로 감소했다. 부족 49개 중 남동술라웨시 26개·고론탈로 17개를 사용자의 지시에 따라 우선한다. 이 문서는 다음 수집을 시작하거나 실행 순서를 바꾸지 않으며 Root 단일 coordinator가 담당한다.

## 나지와 승인 한계

| 분할 | 원본 적격 | 나지 참조 픽셀 | 나지 비율 | 256픽셀 이상 기여 패치 |
|---|---:|---:|---:|---:|
| train | 744 | 1,586 | 0.003335% | 0 |
| val | 292 | 2,998 | 0.015926% | 2 |
| test | 250 | 1,025 | 0.006307% | 0 |

이번 실제 증분의 199픽셀 외 기존 수치는 원본 메타데이터 집계다. 각 split의 나지 비율 0.5%·기여 패치 5개 조건은 미달이다. ESRI 약한 참조라벨은 독립 정답이 아니다. 원본의 기존 교차 split 장면은 별도의 고정 학습 후보에서 제외되어 있으며, 고정 후보 **1,219개**에 이후 원본 수집이 자동 편입되지는 않는다. 학습 준비·독립 정확도·모델 승인은 모두 완료로 표시하지 않는다.

## 증거와 재현

- [native 감사](../../evidence/integration/priority178-round8-native-20261018.json), [로그](../../evidence/integration/priority178-round8-native-20261018.log)
- [최종 고정 현황](../../evidence/integration/priority178-round8-final-20261018.json), [재현 코드](../../evidence/integration/priority178-round8-final-20261018.py), [최종 실행 로그](../../evidence/integration/priority178-round8-final-20261018.log)
- [시작 증거](../../evidence/integration/priority-collection-round8-launch-20261018.json), [collector 종료 로그](../../evidence/integration/priority-collection-round8-live-20261018-stdout.log)
- [최초 입력경로 차단 보존](../../evidence/integration/priority178-round8-native-initial-relative-boundary-20261018.json): 첫 CLI 입력에 boundary의 `data/`를 중복 지정하여 `FILE_UNAVAILABLE`로 즉시 차단됐다. data-root 상대경로로 바로잡아 위 최종 검사를 실행했다. 제품 코드나 데이터 교정은 없었다.

```powershell
$env:PYTHONPATH='.;backend;scripts;tests;.runtime'
python scripts/audit_priority_increment165.py --data-root data --launch evidence/integration/priority-collection-round8-launch-20261018.json --boundary first-group-boundaries/selected-six.geojson
```

후속 수집이 시작되면 원본·원장 SHA는 바뀌므로 위 고정 현황 재현 코드의 SHA assertion은 의도적으로 거부한다. 증거를 덮어쓰거나 현재 수치로 과거 고정 근거를 수정하지 않는다. UI 변경은 이 감사의 소유 범위 밖이며, Root가 API 동적 현황·실제 화면과 이해자료에 이 검증 결과를 인계한다.
