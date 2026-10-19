# 192 — 190의 고론탈로·서자바37창 실제 지원영상 겹침 검토

상태: **VERIFIED_REAL_LOCAL_NATIVE_AND_SUPPORT_REVIEW / EXECUTION_UNAPPROVED**. 고정37후보 중 과거 지원과 겹치지 않는 후보4개를 확인했다. 실제 취득·Sentinel 품질·독립 정답·학습 준비 승인은 아니다. 기존50후보의 검토/게시 파일을 대체하지 않았다.

## 쉽게 설명

190은 이미 받은 토지피복 라벨에서 나지가 충분히 들어 있는 작은 창37개를 찾았다.192는 그 창이 과거에 받은 영상/SCL/B02·원본 지원범위나 미정산 작업과 겹치는지 실제 로컬 자료로 확인했다. 결과는 **고론탈로2개·서자바2개**가 과거 지원과 비겹침이다.

그러나 네 창이 모두 서로 독립인 것은 아니다. 고론탈로의 두 후보는 같은 위치의2024/2021년이고, 서자바의 두 후보는128픽셀 차이로 서로 겹친다. 따라서 고론탈로에서하나·서자바에서하나를 고를 수 있는 검토 근거가 생겼다고 설명해야 한다. 나지4패치 확보 또는4곳 독립 확보라고 설명하지 않는다.

## 소유·시작 조건

Root는191 고론탈로2024g03 수집을, toolbox_review는 그 종료 후165 native 감사를 소유했다. 이 작업자는191 종료와 명시 Root ready를 기다리며 계약만 읽었다. Root가191 native 완료와 source/ledger 핀을 승인하고 추가 collector를 보류한 뒤192를 시작했다.165 감사나179 전체 inventory를 중복 실행하지 않았다. 별도193 고정 후보QA의 로컬 읽기/새 출력과 역할을 구분한다.

제품 소스는 변경하지 않고 기존 `scripts/review_bare_targets179.py` CLI를 **딱1회**, 그 내부167 full support inventory를 **1회** 실행했다. `evidence/integration/bare192-review-20261018/run.py`는 새 사본·request·로그·최종 증거·미게시 UI 인계자료만 만든다.

## 입력 사본과 SHA

191 native 후 원본 **1,666행 / 저장 적격1,333 / 지역연도 계획부족33** 시점에 한정한다. 원본과 원장을 원바이트로 새 `data/bare192-review-20261018/source.json`, `ledger.json`에 exclusive 복사했다. 실제 제품검토는 이 두 사본을 읽고 끝에서 원운영 핀도 유지됨을 확인했다.

| 입력 | SHA256 |
|---|---|
| 원본/고정 source | `ab745b908e2e0adce80907554216c0529e950c7e0123a7f85ee664cf26d50d0f` |
| 원장/고정 ledger | `7839929111f3e70e8b9ba2bda3eb0972bc8c0055bb8c03b9273f4c0b381e353f` |
| 190의37창 proposal | `1cda6dd428dfffcca9df4ac690d9f79ca2187fdc953de0dd3b67d0d1226dce92` |
| 기존6주 경계 | `de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909` |
| 새 request | `1afc3efe28eb008f88567d68e43d34610ec67e871b856c0fbe810e9c18f9f935` |

190 proposal의 최초 source는188 후1,649/1,321 시점이다.192는 그 후보 위치를191 후 최신 고정1,666/1,333 지원재고와 비교했다. 두 시점을 섞거나190이 이후 수집분을 탐색했다고 표시하지 않는다. 이후 collector가 원본을 갱신하면192도 당시 검토일 뿐 현재 실행 권한이 아니다.

## 실제 실행과 검증

Root ready 후13:06:04 KST에 고정 request preflight를 기록했다. wrapper의 명령은 다음과 같으며 이미 쓴 경로에는 다시 쓰지 않는다.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python evidence/integration/bare192-review-20261018/run.py
```

실제 제품 CLI는 `--request <새request> --request-sha256 <위SHA> --output <새report>`를 모두 명시한다. **CLI69.797초·종료0**, wrapper의 사본/사후 검산/인계자료 준비까지 **74.437초**다. 정확한 종료 시각은 receipt의 KST 기록을 따른다.

- 실제 raw ESRI 라벨 **10개 / 압축1,662,885바이트**에서37개 native256창의 나지·동년 lineage·미터계10m격자·기하주내95%를 재검산했다.190의128 간격/scope 선언도 제품179에서 확인했다.
- 전체 **1,233개 support 자산**의 bytes/SHA·GTiff native header·지원범위를 한 번 검사했다. 라벨 자체의 확대 범위는 과거 사용 영상으로 간주하지 않는 기존167 계약을 유지했다.
- `inventory_verified`, `pending_footprints_verified`, `source_pins_verified` 모두true다. 과거 pending2개의 B02 footprint·config를 확인하고 예약 **68,157,440바이트씩 / 합136,314,880바이트**를 보존했다. 환불·정산·재실행0이다.
- 제품검토 후 원운영 source/ledger·고정 사본·proposal·경계 SHA가 유지되었고, 제품179가 읽은 라벨/lineage도 마지막에 재확인했다. 이는 순차 관측이며 OS 원자 snapshot 보증은 아니다.

## 주별 결과

| 주 | 검토 후보 | 과거 support 비겹침 | 과거 support 겹침 | 로컬 오류 |
|---|---:|---:|---:|---:|
| 고론탈로 | 8 | **2** | 6 | 0 |
| 서자바 | 29 | **2** | 27 | 0 |
| 합계 | **37** | **4** | **33** | **0** |

다른4주는 이번 scope에 후보0이며 UI projection에는 고정6주 행을 모두 둔다. 이전179의50후보/23비겹침/27겹침과 이번37/4/33은 시점·후보집합이 다르므로 같은 결과처럼 합치거나 총87개 독립 후보라고 세지 않는다.

전체37후보의 상호 겹침은 **292쌍**이다. 원자료의 동일 SHA/local x/y 중복0과 실제 지리적 겹침292는 다른 검사다.

## 비겹침4개와 선택 시 주의점

| proposal index | target_id | 주 / 연도 | native local x,y | 나지 픽셀 |
|---:|---|---|---|---:|
| 1 | local-rank1-2024 | 고론탈로 /2024 | 1664,640 | 273 |
| 36 | local-rank36-2021 | 고론탈로 /2021 | 1664,640 | 267 |
| 33 | local-rank33-2021 | 서자바 /2021 | 256,1664 | 500 |
| 34 | local-rank34-2021 | 서자바 /2021 | 128,1664 | 498 |

고론탈로 index1/36은 같은 실제 공간이고 서자바 index33/34는 서로 겹친다. 저장된 상호쌍을 대조했을 때 두 개 선택 가능한 조합은 `[1,33]`, `[1,34]`, `[33,36]`, `[34,36]`이다. 이는 report의 겹침 관측 범위이며 집행 승인이나 현장 독립성을 의미하지 않는다. 사용자 우선순위에 따라 Root가 고론탈로2024(index1)와 서자바2021(index33)을 검토할 수 있지만, fresh175/176/170의 전체 입력·live source scene/B02·품질·예산 가드를 다시 통과해야 한다.

## Root 게시와 실제 UI 후속

195scope계약검증/새API20676적용후Root는원본report SHA857b1384…8e2ec0a를보존하고190고정proposal의province_filter만게시사본ui_summary.searched_provinces에추가했다. provenance에는원report/제안SHA와scope주석만추가했음을기록했다. DATA사본SHA6d72cfce…f3009f·이전50pointer원바이트archive·새receipt/reader37·scope2주·현재source일치를 `bare192-publication-root-20261018.json`에검증했다. 실제Chrome응답13:18:35KST에서고론8/clear2/overlap6,서자바29/clear2/overlap27의2행과미탐색범위설명·미검사/집행미승인을확인했다. 전체4clear를독립4곳으로세거나195게시를집행허용으로해석하지않는다.최종실UI근거service193-195-final-ui-20261018.json/PNG/DOM,원래미게시인계단계는아래이력으로보존한다.

## 산출물·보존·UI 인계

| 산출물 | 바이트 | SHA256 |
|---|---:|---|
| report.json | 641,452 | `857b1384c09e3cc8d921ed5a03c445e6464a0805f457cd40bc2a24d1a8e2ec0a` |
| receipt.json | 4,757 | `551eb03ec838e8ac047cd93f8811507db69a1363a9b0adfd951a9e0d46aa79cf` |

새 request/report/preflight/receipt/stdout/stderr와 wrapper·`ui-handoff.json`은 `evidence/integration/bare192-review-20261018/`에 있다. UI 인계자료는 **PREPARED_NOT_PUBLISHED**이며 report의 실제 `ui_summary` projection·source/ledger/request 핀·상호292쌍·실행미승인을 함께 제공한다.

기존173의50 proposal/receipt,179 report, DATA의 게시 report, `latest-bare-review.json` pointer와190 proposal은 전후 SHA가 같다. 따라서 기존 UI는 계속 과거50검토를 가리킨다. 새37검토를 화면에 게시하거나 API/실브라우저에서 확인한 작업은 이번에 수행하지 않았다. Root/UI 담당은 새 immutable DATA report와 명시 pointer 게시 여부를 별도로 결정하고 상태/오류 계약·실제 브라우저 확인까지 기록해야 한다.

실제 network·collector·학습·기관 승인·원운영 source/ledger/lock 쓰기는0이다. 허용된 새 source/ledger 사본2개 생성과 원운영 파일 수정0을 구분한다. 기존 제품 변경이 없으므로 동일 합성/전체 backend/frontend 회귀를 반복하지 않았으며 이번 실제 product/native/support 실행이 새 증거다. 일반화된186/179 기능의 합성 시험 근거는 해당 문서를 따른다.

Root/understanding 담당에게 이 문서·실제 report/receipt·clear4개·상호 겹침 제한·UI 미게시 인계자료를 전달한다. 전체 프로젝트와 나지 학습 준비는 미완료이며 후속 수집·고정 후보 QA·독립 평가·운영 승인은 별도다.
