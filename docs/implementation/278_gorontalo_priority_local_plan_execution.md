# 278 실행 후속 — 고론 우선 새 로컬 위치4개

상태: **VERIFIED_REAL_LOCAL_PLAN_COMPLETED / COLLECTION_UNAPPROVED**. 실행 전 준비 문서 `278_gorontalo_priority_local_plan_preparation.md`, prepared JSON, preparation freeze는 원바이트로 보존한다. 준비 freeze를 결과에 맞춰 덮어쓰지 않고 이 문서와 새 execution freeze를 추가한다.

## 실제로 완료한 일

Root의 새 GO 뒤 로컬182 CLI를 **단1회** 실행했다. 기존56개 위치의 순서와 내용을 그대로 보존해 제외하고 고론2025 1개·고론2022 1개·동자바2025 2개를 제안했다. 사진을 내려받거나 품질 적격 자료를 확보한 작업은 아니다. 신규 적격 증가0, 원격/collector/학습0이다.

Root GO는 `evidence/integration/centers278-go-root-20261018.json` SHA `fa159807cc51af1039270f861dc22e5d2a99df1a78ac43c1c61134f0b368f2e4`, runner는 `centers278-prepare-20261018.py` SHA `cbe09f3d190422f3088fa5be030e229765e63dd2c29d750b5e9a01a1b1f7df41`다. 직접 SHA를 확인한 뒤 승인 명령을 실행했다. GO는 현재 code pins와 맞는271 실main96 검증 SHA `24b837029aafa7413a5a31b56ddbf9cdab91a7a6a53155e45b3608820aaaef9d`를 결속한다.268 실패 결과는 이 성공 근거로 바꾸지 않는다.

실행 명령:

```powershell
python -X utf8 evidence/integration/centers278-prepare-20261018.py --run-local-plan --approval evidence/integration/centers278-go-root-20261018.json
```

exec session71159, 자식182 PID13768이다. 이 PID는 로컬 계획/header 검사이며 collector가 아니다. preflight **11:39:59.320500Z(20:39:59 KST)**, 완료11:41:34.776285Z(20:41:34 KST), runner96.578초/exit0/CLI invocations1이다. 재시도하지 않았다. 기존 로컬 이미지 header116개를 검산했다. 이 측정값을 다른 위치·실128MiB 전처리·영상품질 처리의 성능 인증으로 확대하지 않는다.

## 고정 입력과 산출물

새 source snapshot은 `data/centers278-fresh-20261018/source.json`, 67,518,599B, SHA `0f436db2c320ca6a3b54ae265470d7c26e1e9d64fc657d35aa12619c3bb73b2b`다. 원본과 같은 SHA인 새 사본을 한 번 만들었다. 후속 요청 준비는 이 사본을 재사용할 수 있다. 원장·모델·전체data를 복사하지 않았다.

원본 source와 ledger SHA `5d1ef4d2c1b917402ffdda2365c69d81984b1e682bad22a8cc00ad238456e86e`의 전후 SHA/file identity가 모두 같았다. 공유 운영 원본·원장은 쓰지 않았다. CLI에 `--manifest-profile bounded128m-3000-v1`을 명시했고 descriptor는 `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`다. source 크기에 따라 자동 선택한 것이 아니며 기존 raster/header별 cap은 변경하지 않았다.

| 새 산출물 | SHA-256 |
|---|---|
| `data/centers278-fresh-20261018/prior-merged.json` | `9322e05e8ba46b407b6130f7cc161fbd9b3bcd6efbd4d933865347be676dff77` |
| 같은 디렉터리 `proposal.json` | `8f88429c4381ef3d3cfcb363912cc0277b81a112e05f77deaba798ba720f78f9` |

실행 결과는 `evidence/integration/centers278-result-20261018.json`의 `LOCAL_PROPOSAL_COMPLETE_UNAPPROVED`다. `centers278-preservation-20261018.json`에서 원269 prior52/뒤proposal4의 구간별 exact 순서·56개 유일성·새4개ID의 이전56개 제외·코드/boundary/config 후 핀·원 preparation freeze 불변을 모두 true로 확인했다. 과거 proposal의 후보가 실제 집행됐는지 여부에 따라 제외 기록을 지우지 않았다.

## 실제 proposal 배열 순서

| 순서 | 대상 | spatial_window_id | 경도·위도 |
|---|---|---|---|
| 1 | 고론2025/train | `centers182-gorontalo-921d1fd07f85` | 122.05812938800413, 0.8467127710078407 |
| 2 | 고론2022/train | `centers182-gorontalo-e27f44e403e0` | 122.24503408578502, 0.9408375575931044 |
| 3 | 동자바2025/train | `centers182-east_java-daff7cfcb87f` | 112.21882981517928, -7.7639911984687915 |
| 4 | 동자바2025/train | `centers182-east_java-226a7fa921e4` | 112.3128375419827, -7.669660250644265 |

네 계획창 모두 저장 `inside_fraction_native=1.0`이다. 이는 고정 경계를 사용한 계획 기하 조건이며 실제 원격 B02/SCL/label 창 정합이나 유효픽셀 품질이 아니다. target 순서는 고론2025→고론2022→동자바2025로 명시했다. 스냅샷 적격/28부족은 각각18/10,24/4,27/1이다. 동자바 후보2개는 부족2개라는 뜻이 아니라 대체 위치를 포함한 제안2개다. 자동으로 모두 집행하지 않는다.

## 보존과 검증의 범위

준비 중에는 운영 source/ledger를 읽지 않았으며, 이번 승인 실행에서만 전후 검산·고정 source 사본 생성을 수행했다. 준비 freeze SHA `c36968b48366790586bd6b61fd590a432c9187efcb9cd1f552445a04036eca6d`는 그대로다. main 제품·원본 source/ledger·profile·게시 pointer 쓰기0, 원격HTTP0, collector0, 모델/학습0이다.

후속 metadata assertion은56개 exact 보존 및 새ID 제외/작은입력/code 후 핀을 검증했다. 단위/회귀를 추가 실행한 제품 변경은 없고, 실제 QA를 반복하지 않았다. 전체 pending/support inventory·선택 scene/SCL/B02·최종80%·주내95%·공간독립성·독립정답은 후속 수집/QA 가드에서 별도 검증해야 한다. `full_pending_support_inventory_verified=false`, `actual_quality_eligible=false`, `execution_supported=false`, `training=false`를 유지한다.

Root에 새 proposal/source/prior 및 최종 지문을 인계한다. 실제 집행에는 최신 원장·단일 잠금·fresh proof·v2 config/request/선별정책 결속과 Root의 별도 승인이 필요하다. 기존 수집 GO를 재사용하지 않는다. UI/API 보유량과 적격/셀 부족을 바꾸는 작업이 아니므로 화면 수정은 필요 없다. 이해자료 후속에서도 “계획4개”와 “확보0개”를 분리하도록 Root에 인계한다.
