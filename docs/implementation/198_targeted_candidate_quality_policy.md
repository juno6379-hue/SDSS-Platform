# 198 — 표적 수집의 명시적인 SCL 후보 품질 선별 강화

## 상태와 쉬운 설명

**TESTED_SYNTHETIC:** 표적 계획에 선택 필드 `policy.minimum_candidate_valid_fraction`를 추가했다. 사용자가 `.8`을 명시하면 SCL 예비검사에서 유효 픽셀80% 이상인 영상만 다음 단계로 고른다. 필드가 없으면 기존65%를 그대로 쓴다. 이는 자료를 받은 후 합격 기준을 낮추는 기능이 아니라, 여섯 밴드 전체를 받기 전에 낮은 품질 후보를 더 일찍 제외하도록 요청하는 기능이다.

**운영 미실행:** 이번 단위는 새 collector·STAC 조회·native 재검사·로컬 후보 스캔을 시작하지 않았다. 실제 파일 생성과 픽셀 계산은 임시 합성 자료에서 수행했고 원격 전송은 Mock이다. 새로운 원격 영상의 품질 향상이나 적격 나지 확보를 아직 확인한 것은 아니다.

Root는196 실행 종료·독립 native 검증 및 기존 source pin 일치를 확인한 뒤13:28 KST에 이 source 편집을 허용했다. Root가 운영 수집기·원장·잠금의 단일 소유자다. 이 담당은 운영 원장·잠금·기존 영상/라벨·197 ML 결과·UI를 수정하지 않았다.

## 196 사례의 세 가지 수치를 구분한다

기존196 남동술라웨시2025 표적의 저장된 source annual report와 독립 native JSON을 읽었다. 다시 검사하거나 다운로드한 것이 아니다.

| 검사 단계 | 관측값 | 의미 |
|---|---:|---|
| 첫 후보의20m SCL 예비검사 | 41.3024902% | 기존65% 미달로 제외 |
| 두 번째 후보의20m SCL 예비검사 | 69.1467285% | 기존65% 이상이므로 선택 |
| 조립 source 영상의 유효 비율 | 68.4097290% |10m 영상·SCL/finite/nonzero를 결합한 source 결과 |
| 독립256 patch의 최종 유효 비율 | 67.6437378% | 행정경계·라벨 등 학습 지원 마스크를 포함한 결과 |

마지막 patch는 나지840픽셀이 있어도 전체 유효 비율80%를 충족하지 못해 `quality_insufficient`였다. 예비 SCL69.15%와 최종 patch67.64%는 서로 다른 계산이다. 새 `.8` 요청은 그 두 번째 SCL 후보도 제외하고 기존 후보 pool의 다음 영상을 살펴보게 한다. 다음 후보가 없거나 모든 후보가 미달하면 기존 `quality_insufficient` 경로로 끝난다.

근거: `evidence/integration/target196-native-root-20261018.json`과 `data/first-group-training-esri-v1/sources/target256-bare-southeast_sulawesi-2025-local-rank1-2025-a40b24388dbd/annual-window-report.json`.

## 입력·출력과 호환 계약

기존 표적 계획의 `policy` 필수 키는 그대로다. 선택 필드 하나만 허용한다.

```json
{
  "window_size": 256,
  "source_taxonomy_code": 8,
  "minimum_declared_bare_pixels": 256,
  "minimum_valid_fraction": 0.8,
  "minimum_inside_fraction": 0.95,
  "maximum_new_batches": 1,
  "minimum_candidate_valid_fraction": 0.8
}
```

- 선택값은 정확한 builtin int 또는 float, 유한한 수, `.8 ≤ 값 ≤ 1`이어야 한다. bool·문자열·null·NaN/Infinity·범위 밖 값은 거부한다. unknown policy 키도 계속 거부한다.
- 잘못된 선택값은 pin 파일을 읽기 전에 BLOCKED로 거부하며 job을 반환하지 않는다. 비유한 수는 기존 bounded JSON 복사 단계에서 `PLAN_INVALID`가 될 수 있고, 일반 범위/타입 오류는 `POLICY_INVALID`다.
- 필드가 없으면 generated config의 `candidate_valid_fraction=.65`가 그대로 유지된다. 기존 반텐의 전체 job/config·config SHA·plan SHA에서 만든 key가 바뀌지 않는 것을 기존175 계약 시험으로 확인한다.
- 필드가 있으면 generated config의 `candidate_valid_fraction`에 그 값만 전달한다. 기존 전체 plan canonical SHA에는 새 필드가 포함되므로 명시 정책이 다른 계획은 별도 plan/key를 갖는다. 기존 실행 결과를 새 정책으로 재해석하거나 덮어쓰지 않는다.
- 내부 결과 schema/status·실행 승인 flag·미검증 경계는 기존과 같다. 이 옵션을 쓴 local plan 준비 성공도 `execution_supported=false`이며170의 실제 실행 전검사를 거쳐야 한다.

계약 연결은 `targeted_bare_plan.prepare_targeted_bare_jobs` → generated job.config → 기존170 dispatch의 `collect_windows` → 기존 `select_quality_candidate(..., minimum)`이다. collector는 이미 인자를 받으므로 `scripts/collect_samples.py`와 일반 수집기 코드는 변경하지 않았다.175의6주 고정 split·기존 반텐 호환과174/170 실행·선택 source/자산/기하 계약은 보존한다. 기존 문서의 관련 링크·인계·이해자료 갱신은 Root가 함께 마감한다.

## 그대로 유지한 가드와 한계

최종 유효80%·행정경계95%·나지256픽셀 기준,256 크기·6밴드·동년 라벨·최대2 target·기존 pending2의 전액예약, 물리3000개 상한, 같은4GiB 공유 예산,2worker·전역2초 간격·첫429 중단, 고정 train/val/test와 scene 분리, B02 실제 header/선택 source·보조 footprint·terminal/정산 계약을 바꾸지 않았다.

SCL 예비검사는20m 중심창이고 최종 검사는10m 영상·다른 밴드·마스크·경계·라벨을 포함한다. 예비80%를 넘더라도 최종80%를 보장하지 않는다. 더 많은 후보의 SCL을 검사하면 예비 전송량이 늘 수 있으며 기존 예산과 최초429 회로가 그대로 제한한다. 새 후보 pool 확대·재시도·기존 작업 재수집·품질 라벨 소급변경도 하지 않는다.

## 검증과 소스 동결

신규 집중 시험 `tests/test_targeted_candidate_quality_policy.py`는 **6 PASS / 1.786초**다. 시험은 다음을 확인한다.

1. 필드 미지정의 기존 반텐 job 전체·key·config SHA 완전 동등.
2. 명시 `.8/.9/1.0/1` 전달과 그 외 config·geometry·split·nominal 수량 보존, 전체 plan SHA에 따른 새 key.
3. bool/null/문자열/NaN/Infinity/범위 밖 값·추가 키의 pin 파일 읽기 전 거부와 빈 job.
4. 임시 입력 바이트와 plan/base 객체의 불변.
5. 실제 `collect_windows`가 generated config의 `.8`을 기존 selector의 마지막 인자로 전달. STAC/selector는 Mock이고 원격 raster 호출은0.
6. 실제 selector와 임시20m SCL GeoTIFF writer를 사용해 약67.64% 합성 후보가 `.65`에서는 선택되고 `.8`에서는 제외돼 다음100% 합성 후보를 고르는 동작. fetch는 Mock이며 실제 네트워크는0.

집중 로그는 `evidence/integration/target198-candidate-policy-focused-20261018.log`다.175/170 및 선택 source·실기하·공유 scene 가드 관련 회귀의 최종 결과와 source pin은 아래 후속 절 및 Root 인계서에 기록한다. 집중6건은 관련 회귀와 겹치므로 합산하지 않는다. 기존 affine 곱셈의 PendingDeprecationWarning은 통과 결과와 별개로 남겨두었으며 이 단위에서 기존 라이브러리/기하 코드를 변경하지 않았다.

내부 계획 필드·producer config 추가이므로 새 API/UI 계약이나 화면 변화는 없다. 브라우저 재검증은 이 단위의 필수 범위가 아니다. Root는 검증 완료 코드를 이해 담당에게 전달해 쉬운 설명·이론·동작·시험·대본·FAQ·INDEX·변경 이력을 갱신한다.

### 관련 회귀 최종 결과

관련8개 모듈의 **107건 중106 PASS / 기존 Windows symlink 권한1 SKIP / 19.374초**를 확인했다. 대상은 신규 선별 정책, 기존175 local plan,170 dispatch, 실행·collector hook·live guard·공유 scene claim·실제 자산 기하다. 로그는 `evidence/integration/target198-candidate-policy-related-20261018.log`다. SKIP은 `test_symlink_parent_or_leaf_rejected_without_touching_target`의 기존 OS symlink 생성 권한 제한이며 새선별정책의 미실행 시험이 아니다. 임시 raster/원장과 명시 Mock을 사용한 관련 회귀이며 운영 재수집이나 새 과학 검증은0이다.

동결 source SHA는 `3fe849e76e64a0d64804c76f99f3ca073b2241fa9aa0c6e1fa74412a6845bfa1`이다. `collect_samples.py` SHA `68d4b986b5500cb19eb810c5b086f668fc698d124551a268c190cdf5a5211301`, `collect_targeted_bare.py` SHA `643a3e8327a30ebac671267f451636bf3ce18828cce42855ef643d9945694581`을 함께 기록했다. 전달 인자·실제 selector와 Mock의 경계는 `evidence/integration/target198-candidate-policy-freeze-20261018.json`을 따른다. 최초 freeze의 문서 SHA는 이 회귀 결과 절을 덧붙이기 전 관측이며 최종 문서 SHA는 별도 `target198-candidate-policy-final-freeze-20261018.json`에 남긴다.
