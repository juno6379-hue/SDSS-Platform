# 205 — 새 남동2024·2021 두 장소의 실제 소비 전 보호 검토

상태: **VERIFIED_REAL_LOCAL_SUPPORT_AND_PHYSICAL_CHECK / EXECUTION_BLOCKED**. Root가 199 helper를 운영 로컬 자료에 **단 1회** 호출했고, 두 장소의 현재 전체 지원 범위·미정산 예약·물리 상한 검사가 통과했다. **실제 B02 선택·원격 품질 검사·수집·신규 예약·정산은 0회**이며, 200 coordinator 연결은 미완료다.

## 쉽게 설명

204는 사진을 찍을 새 장소를 찾은 단계였다. 205는 그중 남동술라웨시 2024·2021 두 장소의 영상을 실제로 받기 전에 현재 원장과 지원 파일을 검사한 것이다. 과거 영상이나 미정산 작업과 겹치지 않고, 두 원본 창에서 명목 32패치가 생겨도 전체 3,000개를 넘지 않는 조건을 확인했다.

아직 위성 서버에서 어떤 장면을 받을지 선택하지 않았다. 따라서 맑은 영상·실제 나지·적격 패치가 늘었다고 말할 수 없다. `local_checks_passed=true`는 로컬 사전 조건 통과이며, `execution_supported=false`와 함께 읽어야 한다.

## 소유·실행 기록

Root가실제검토와그결과를소유했다. 이문서담당은완료된request/result/runner/log의JSON proof만읽고대조했다. 동일199 호출·full167·native·HTTP를추가실행하지않았고소스/시험을수정하지않았다.

`centers205-review-root-20261018.py`는다음조건을확인한뒤함수를한번호출했다.

- 199 helper SHA가 동결판 `c8eece7cbb0d3fed77f704b65eda9e51fe2e300ea56fdfd4aa020d9c9653204f`와 같다.
- 전역 execution lock이 없고 대상 collector Python process가 없다.
- 활성 source/ledger의 SHA가 request의 두 핀과 같다.

실제 `prepare_deficit_candidate_jobs` 호출은 **129.516초**이며,완료기록은 **2026-10-18 13:46:09 KST**다. runner는결과를새JSON에exclusive저장하고운영source/ledger의전후SHA불변을다시확인했다. `operating_inputs_unchanged=true`,로그의job수2·inventory_scan_count1과결과가일치한다.

함수호출은1회,그안의전체167 support inventory도 **1회**다. 물리관측은199 계약대로첫계수와끝안정성대조를수행한것이며별도두번째전체support감사를추가한것은아니다.

## 고정 요청과 핀

request는204의fresh proposal4개중남동의첫두장소만선택했다. 고론탈로두후보는이번205선택범위가아니다. 최대2batch이고두job 모두고정 train split이다.

| 입력 | SHA256 |
|---|---|
| 204 proposal | `0755f8cf2c7b210cb989b817b003e394e9ab7208400fa6b40551c26053d598f0` |
| source사본과활성source | `39bb0245e586342bd116f5b052428fcf857fb26eae0ee1413c9c5f5275c40ba9` |
| 현재ledger | `024f5eabb2cadf88af4f34661fab6e6c209bf9aa8d105c2d1fbadf10f1c0dae3` |
| 공식6주경계 | `de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909` |
| config | `8b0c1b2aad13a3344200998ec62a18853c5308adf4ec57b1af835333845fd7e3` |
| 기존28후보prior 합본 | `453ec964247ae87d61ddc035348a984b7f6c10a5ef699c6236fbebb10441867f` |

request파일은1,365바이트·원바이트SHA **`26577411c419cfcd2ce47e768cab3a788d26b37208569536dc2c274f20c9c996`**다. helper의 `request_sha256` **`c28a69f1093e935523227e6d4021c18856e3457a29fd78bf241a7e8b2eeebabc`**는sorted canonical JSON SHA이므로파일원바이트SHA와다르다. 서명·기관승인·집행권한이아니다.

## 선택한 두job

| 대상 | 공간ID | 계획key | 명목패치 |
|---|---|---|---:|
| 남동2024 | centers182-southeast_sulawesi-bd99d40b7b68 | center1024-southeast_sulawesi-2024-c28a69f1093e-7158f440 | 16 |
| 남동2021 | centers182-southeast_sulawesi-6ad43e34c63c | center1024-southeast_sulawesi-2021-c28a69f1093e-2ce2bf2f | 16 |

두config는native1024·6밴드·동년ESRI·source후보65%/최종유효80%·재시도0·고정split를유지한다. config SHA는각각 `f5eed40ee3e6ff4cf06ffe2adb38636d95089d58c956779cb58c1c68203465e5`, `780cff23fe343d111ddc00ef99cb871bac32b8c2b868ef384c614557d6cd964a`다. 이계획key를원장에예약하거나32패치를생성한것은아니다.

## 실제 support·pending·물리 proof

| 항목 | 관측 |
|---|---|
| 전체support 검증/asset목록 | **1,254개** |
| inventory_verified | true |
| pending_footprints_verified | true |
| source_pins_verified | true |
| 선택두곳과과거/상호지원창 | 사전claim 통과 |
| 실제물리패치 | **1,668개** |
| 참조된물리패치 | **1,668개** |
| 미참조실물디렉터리 | 0 |
| worker receipt 파일 | 135개 |
| capacity 대조 | **1,668+32=1,700≤3,000** |

물리계수는현재manifest1,667행만쓴것이아니다. manifest밖의worker receipt에보존된미등록패치도포함해1,668로확인했다. 참조된실물이라는뜻이지모두품질적격/학습승인이라는뜻은아니다.135는지원디렉터리의worker receipt 수이며현재에이전트/수집기수와다르다.

물리관측지문은 `d43bb25f0b104fb9c8038a6746f7e112d1995bb0bbf90fc2bc3280b367c0fad8`이며끝관측과같다.1,700은추가두창의최대명목물리수를고려한상한검산이지실제로새패치가늘어난누계가아니다.

기존pending은반텐2023 boundary01·서자바2023 boundary01 두건이다. 각config와실제local B02 footprint1개를확인했고,각예약/계상68,157,440바이트·합 **136,314,880바이트**를보존했다. pending해제·환불·정산·재시도는하지않았다.

199가정확4GiB·현재429비활성·원장합계·최대2batch의65MiB씩잔여계상조건을확인했으나실제CollectionLedger 예약/저장/lock은호출하지않았다. fullsupport는확대SCL/SWIR/B02와이전report/미정산지원까지확인하는로컬검사다. 새원격장면의실격자·선택B02·맑음/픽셀품질은아직검사하지않았다.

## 결과와 미완료 경계

실제반환은다음상태를동시에가진다.

```json
{
  "status": "EXECUTION_BLOCKED",
  "issue": "COORDINATOR_NOT_CONNECTED",
  "local_checks_passed": true,
  "inventory_scan_count": 1,
  "source_pins_verified": true,
  "execution_supported": false,
  "collection_executed": false,
  "actual_quality_eligible": false,
  "scientifically_verified_bare": false,
  "ready_for_training": false,
  "network_requests": 0,
  "source_or_ledger_writes": 0
}
```

200실coordinator는단일execution lock안의fresh pin/물리대조·shared scene_registry/window claims·selection_context·실선택B02 callback·현재장면/고정split·2worker/2초/첫429·원pending전액·새출력배타성·예약/실정산·실품질/등록/중단인계를연결해야한다. 이번검토결과를그계약의완료로쓰지않는다. 이후원본/원장이바뀌면205도당시관측이므로실제집행전에다시검사해야한다.

## 증거·문서 인계

실제result는 `evidence/integration/centers205-review-result-root-20261018.json`, **1,930,666바이트**, SHA256 **`529d6074903cae407bc6c40ef557c052fb1b1bbf77b09afa3fc771f22fe1b916`**다. 두job의공식경계기하와fullasset/proof가포함되어있으므로집계필드와실제목록수를대조해읽었다.

근거는같은접두사의 `centers205-review-request-root-20261018.json`, `centers205-review-root-20261018.py`, `centers205-review-root-20261018.log`다. 문서담당은저장된proof/핀/산술만대조했고동일검사를추가하지않았다. [199 구현](199_guarded_deficit_candidates.md)의담당임시시험과Root205 실제운영로컬1회를시점·소유별로구분한다. [202 명시셀계약](202_explicit_deficit_proposal_cells.md), [204 실제제안](204_fresh_deficit_centers.md)과도연결한다.

직접UI/API 계약/화면을바꾸지않는내부검토라프론트수정·build·실브라우저시험은없다. 실제후속확보와검증을화면에반영하는것은Root/실행/UI담당후속이다. Root/understanding담당에게완료proof·한계·대본/FAQ/INDEX갱신자료를인계하며전체개발·10분보고·독립정답·나지/학습/운영승인과제는계속남는다.
