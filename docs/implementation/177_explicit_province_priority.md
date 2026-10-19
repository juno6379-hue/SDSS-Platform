# 177. 명시 주 순서에 따른 부족 셀 우선 수집 계획

## 목적과 상태

사용자가 남동술라웨시와 고론탈로를 먼저 보완하도록 지시했다. 기존 우선계획은 전체 주·연도를 부족량 내림차순으로 정렬하므로 반텐 등 다른 셀이 먼저 선택될 수 있었다. 새 **명시 옵션**은 선택 가능한 부족 작업을 남동술라웨시 → 고론탈로 → 나머지 기존 정렬 순서로 배치하고 그 순서 자체를 계획SHA에 묶는다.

**TESTED_SYNTHETIC:** 최종 집중19PASS/2.485초·종료0. 실제 운영 수집은 시작하지 않았고 진행 중인8차 반텐을 중단·재시작하지 않았다. 이번 담당의 운영source/원장/예약/모델/계정/UI변경·HTTP·학습은0이다. 실제 적용계획·원본/원장 최신pin·8차 정산 검증은 Root 후속이며 이 문서는 실행 완료를 뜻하지 않는다.

소유 소스는 `scripts/collect_training_priority.py`, 기존 정확 시험파일은 `tests/test_training_priority.py`다. `scripts/collect_training_parallel.py`의 CLI 전달/재검증은 Root가 따로 편집했고 이 담당은 해당 소스를 수정하지 않았다. 공동 계약을 집중시험에서 함께 검증했다.

## 사용법과 계획 계약

```powershell
python scripts/collect_training_priority.py `
  --max-batches 2 --continue-unrelated-pending `
  --priority-province southeast_sulawesi `
  --priority-province gorontalo
```

이는 읽기 전용 dryrun이며 실행하지 않는다. 출력 priority_plan.plan_sha256을 검토한 뒤 같은 옵션과 `--execute --expected-plan-sha256 <pin>`을 명시해야 wrapper가 기존 parallel collector를 호출한다. source/ledger가 변하면 같은SHA로 실행하지 못한다. 기존 source/후보/원장으로부터 새 계획을 검산해야 하며 이전계획을 임의 재사용하지 않는다.

`--priority-province`는 반복 입력된 **순서**를 의미한다. 공식6주 slug만 허용하고 중복·빈 명시목록·잘못된형식을 거부한다. 생략은None이며 기존 정렬·계획필드·계획SHA를 보존한다. 명시 옵션은 최대6개 공식주를 순서대로 선택할 수 있지만 이번 사용자 요청에 맞는 값은 위 두주다.

내부 함수 `prioritize_jobs`, `build_priority_plan`, `verify_priority_plan`에 선택적 `province_priority=None`을 추가했다. `validate_province_priority`는 공식slug의 고유 순서를 tuple로 반환하고 미지정은None이다. job config·원래객체·고정split·selection_context·source행은 수정하지 않는다.

선택 조건은 여전히 **셀당28개 계획 바닥의 부족이 양수인 기존 신규가용 작업**이다. 기존 settled job은 재시도하지 않고, pending은 기존 명시 continuation이 제거한 뒤에만 소비한다. 같은 해의 적격 성공 spatialwindow도 제외한다. 이미소비한scene/window의기존collector계약을바꾸거나새공간을발명하지않는다.

정렬은 명시주 group순서 → 부족량 내림차순 → 기존 province/year/candidate_rank/key tie-break다. 두 개 모두 남동술라웨시 작업이 가용하면 최대2batch에 둘 다 선택될 수 있다. 이 옵션은 주별1개 round-robin이나 무조건 두주에서 한 개씩 선택하는 규칙이 아니다. 우선주에 양수부족 작업이 없으면 나머지 기존정렬로 넘어간다. 품질기준을낮춰작업을만들지않는다.

명시 옵션일 때만 계획에 다음 필드가 추가되고 모두planSHA에 포함된다.

- `province_priority_order`: 전달된 정확한 주 순서.
- `priority_region_status`: 해당주별 실제 적격합계·2020~2025의셀당28 부족합계·신규가용 deficit job수·실제선택수·상태.

상태는 REGION_TARGET_MET, BLOCKED_NO_AVAILABLE_DEFICIT_JOB, DEFICIT_JOB_SELECTED, AVAILABLE_NOT_SELECTED_BATCH_LIMIT를 구분한다. 적격패치가 있더라도 모든 연차에고르게있다는 뜻은 아니며 이미초과한셀의잉여가다른연도의부족을대신하지않는다. 후보가없는데부족한주는차단사유를표시하고수집완료/적격증가를만들어내지않는다. 명시옵션이없으면이두필드도추가하지않는다.

## wrapper와 실행 중 재검증

priority wrapper는 원래 command의 `--priority-deficit --priority-plan-sha256`과 같은 `--priority-province` 반복값을 정확히 전달한다. parallel collector는 priority mode 없는옵션사용·중복/미등록주를원장접근이전에거부하고, 같은원본/원장 snapshot과 province_priority로 verify_priority_plan을 다시 계산한다. 순서생략/뒤집기/상태변경은pin불일치로reserve·coordinator전에차단한다.

Root의parallel plan에도 명시옵션일때만 `province_priority_order`가 기록된다. 기존기본동작을바꾸지않으며 실제coordinator·reserve/work/finalize callback·2worker·공유2초간격·최초429공유중단·4GiB동일예산·물리3000상한·고정split·최대1~2batch를유지한다. priority옵션은표적256실행지원/sceneclaim범용화/모델승인기능이아니다.

## 검증 근거

`evidence/integration/priority177-focused-final-20261018.log`: **19PASS/2.485초·종료0**. 앞선18PASS/0.922초의로그도보존했으며실제별도Python CLI의early-mode거부시험1개추가뒤19개를재실행했다. 묶음을합산하지않는다.

시험은 명시주순서가더큰다른주부족보다앞서는선택·입력불변·defaultNone의기존planSHA·순서plan핀/순서뒤집기·중복/미등록slug거부·후보없음/실제지역적격/부족표시·기존settled/fullwindow제외·wrapper argv전달·parallel main의동일선택·wrongpin차단/lock해제·wrongmode원장접근전거부를검증했다. 실제Python subprocess에는 `--execute`/유효priority모드없이옵션만전달해초기거부를확인했으며수집기실행/HTTP는0이다.

기존동작회귀의고정fixture plan SHA는 `992b032cc12f740cd852d59d6a48582ab6789c0a404a5581a401f1a72daacded`다. 현재변경전Git HEAD의함수로계산한값과새defaultNone이정확히같다. 기존일반'a/b/c'합성queue·기본plan전체시험도유지했다.

`priority177-contract-20261018.json`의 명시합성사례는 기존선택반텐/고론탈로에서 명시선택남동술라웨시/고론탈로로바뀌는것을보인다. 운영원본의현재셀계수나실제수집성과가아니며테스트용합성상태다. source/test/Rootparallel통합SHA도같이기록했다.

| 완료 소스 | SHA256 |
|---|---|
| priority helper/wrapper | `27a13917bf90941ea68b2400028fe1b1300365ac63721e4ccf0eabd1e004040c` |
| 집중시험 | `75a45c2c45e63fb44313683feebc226cbc66baf0602c0de4ac389d5afc4a4f54` |
| Root parallel 통합 관측 | `5e99234379cd45804d6eaf1b3b349210d5b9f26d5344e8ff6193dd74eb136b0c` |

## 인계와 한계

Root는8차현재작업의실제terminal/원장/source를확인한뒤새명시dryrun을검토한다. 남동술라웨시/고론탈로의가용후보0이면위차단상태를보고하고,새AOI/신규scene/표적계획은기존중복방지·품질·원장계약을보존한별도단위로준비해야한다. 이옵션만으로실제부족셀수나나지균형을해결했다고표시하지않는다.

새API/화면계약은추가하지않았으므로이번담당은UI를직접수정하지않았다. Root가실제수집결과확인후현황API/UI와이해자료·인계서를갱신한다. 담당별10분보고와예약ACTIVE/실제수집상태를계속구분한다.
