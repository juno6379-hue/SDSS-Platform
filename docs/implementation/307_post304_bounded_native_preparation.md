# 307 — 304 동자바2025 종료 관측·증분 감사 준비

상태: **VERIFIED_REAL / 단1 native 완료 / 신규16·적격16·셀부족0·나지0**. 아래 준비 절은 당시 기록이며 실제 완료 결과는 마지막 절에 추가했다. 이 담당은304 수집의 단일 종료 관측과 신규 최대16개 감사 준비를 소유한다. Root가 추가 collector를 보류하고 종료 후 원본을 고정한다. 운영 source/원장/래스터/모델 읽기0, HTTP0, collector 시작0, native helper0이다.1763등록/1391적격/gap1은 Root 전달 수집 전 값이며 미래 성과가 아니다.

## 원판 보존과 최소 변경

검증된299 runner `deficit297-native-runner-root-20261018.py`15973B/SHA `a8a9ed9fcdbb0fafb60c3c71f028f188b6f855ccc5f7c6768a328c327da608ca`를 원바이트 `deficit307-before299-native-runner-20261018.py`에 보존했다. 새 runner는 `deficit304-native-runner-root-20261018.py`이며 SHA `36a6cf451a86e0b3f0f963e689f732b4228f73d03f21e20687a08582ec141e8f`다. 최소 diff는 `deficit307-native-runner-vs299-20261018.diff`에 남겼다. 변화는297→304 경로/GO status/대상 job·province·config·request/old1747→1763뿐이다. shared 제품·299 원판·완료 증거를 수정하지 않았다. compile만 수행했고 import/실행/운영 검산은 하지 않았다.

대상은 `centers182-east_java-5141c64815b2`/2025/train, key `center1024-east_java-2025-981abcd9b78b-9c40f177`, request canonical `981abcd9b78b6eaa94dcb48a2f2bc62346ac939967076490b41c0c10e03f0987`, config semantic SHA `31044c97e5dd1cf84648eec174975eacd9b5f8e1eacfcbf50e355bc0bb7d657a`다. native CRS를 고론32651로 고정하지 않았다. 실제 선택 source의 CRS/transform을 따라 rawB02/source/quality/256patch 일치를 비교하며10m/1024/6band 등 기존 조건을 유지한다.

## 관측 시작

22:17:46.597291 KST launch/pid33032를 확인했다. 실제 OS는 supervisor43984(parent6376)→collector33032이며 execution lock이 존재했다. 최초 stdout/stderr0B, terminal없음은 fresh 전검사만 의미한다. 아직 worker/전송/신규 patch·적격·나지·정산은 미확정이다. 현재source/ledger를 추가 읽지 않았다. 이후 launch→worker→실종료·정산/OSlock해제를 구분하여 Root에 보고한다. ACTIVE 예약을 실전송·최종정산으로 바꾸어 보고하지 않는다.

## 실행 전 승인 계약

Root가304 실제 terminal exit0·정산 완료·OS collector와 중복감사 부재·lock해제를 확인하고, 종료 후 source/ledger 실제 SHA와 source bytes≤128MiB·실제 신규 개수0–16·launch/terminal SHA를 고정한 뒤 새 GO를 발급해야 한다. 수집 전 source9e635/ledger574d를 미래 postsource로 재사용하지 않는다. runner는 GO의 선언/lock을 대조하지만 OS 전역 탐지를 하지 않으므로 Root 관측 근거가 필요하다.

계약 예시이며 아직 승인 파일이 아니다. null 미래값은 발명하지 않았다.

```json
{
 "status":"GO_304_BOUNDED_NEW_MAX16_NATIVE_AUDIT",
 "runner_sha256":"36a6cf451a86e0b3f0f963e689f732b4228f73d03f21e20687a08582ec141e8f",
 "audit165_code_sha256":"ba4da0b03bd19a0d327200a49eb5c75b28a1f42620be43c84826092c50c661ba",
 "no_active_collector_or_duplicate_audit":true,
 "collector_terminated_and_settled":true,
 "launch_sha256":null,"terminal_sha256":null,
 "source_sha256":null,"source_bytes":null,"ledger_sha256":null,
 "expected_new_patch_count":null
}
```

Root가 전체 runner/최소 diff/최종지문을 검토하고 별도 GO를 준 뒤에만 아래 명령을 한 번 실행한다.

```powershell
python -X utf8 -u evidence/integration/deficit304-native-runner-root-20261018.py --root-go E:/GeoAI–MLOps–SDSS/evidence/integration/deficit304-native-go-root-20261018.json
```

독점 x 생성 출력은 `deficit304-native-root-20261018.json`, `.log`, `-stderr.log`다. 기존 파일 부재는 실행 전 다시 확인하며 이미 있으면 자동재시도하지 않는다. 실패시 부분결과·issue_type/trace를 보존하고 exit2이며 상한 상향/자동복구0이다. 저장장치 오류·강제 종료까지 부분 결과를 보장하지 않는다.

## 유지하는 검산과 분기

old1763행 prefix·history 원문을 고정 prior와 대조하고 신규 수를 GO와 exact 대조한다.0개면 helper0/래스터0으로 `ZERO_PATCH_REQUIRES_SEPARATE_ROOT_AUDIT`, nativecomplete=false/exit2다. 이 분기는 정산/pending/신규파일 부재 감사가 끝났다는 뜻이 아니며 Root의 별도 좁은0개 감사가 필요하다. terminal 실패/사전차단도 helper 이전에 막히고 Root가 별도 판단한다.

양수1–16개일 때만 기존 helper165를1회 실행한다. 한 batch·rgb_window_downloaded scene1·하나의1024source라는 기존299 가정을 유지하므로 여러 source/미등록 신규 파일을 성공으로 축약하지 않는다. oldhistory/pending2 exact·reserved136314880B 보존, worker=ledger=COG+metadata 정산·finalize/settle/publish 각각[key]를 검산한다. 원본/원장/launch 두 읽기와 개별 파일 SHA를 확인한다. 전체 이전 래스터는 재감사하지 않는다.

신규N의 이미지/라벨/마스크3N개와 선택 STAC raw SHA/sceneID/원 datetime/2025/collection/AOI metadata bbox/B02 저장참조를 대조한다. 실제 MemoryFile에서 rawB02↔1024source첫band,10m/CRS/transform/shape/quality grid 및256patch첫band/window를 검산한다. GDAL aux 쓰기 비활성/PROJ_NETWORK=OFF·로컬 TIFF magic 확인을 유지한다. HTTP/원격 데이터셋 열기/collector/원장 쓰기는 하지 않는다. metadata 일치는 독립 정답이나 원격 권위·학습 품질 검증이 아니다.

16개가 실제 등록되면 helper52 unique SHA/trace21 중patchimage16중복·신규48래스터라는 과거 구조가 가능하지만 이번 개수는 실제 결과에서 확정한다. 원시 label nearest 정렬→source quality→최종support→eligible 나지와기여를 분리하며 부적격 나지를 eligible에 더하지 않는다. 기여는 eligible이면서final bare≥256이다.새자료·나지 성과는 미확정이다.

파일별source128MiB/ledger16MiB/TIFF64MiB 등 cap을 유지한다.이 증분 runner는 별도128profile 후보QA의 누적16GiB 계측을 새로 구현한 것이 아니다. 기존4GiB/2worker/2초/첫429/물리3000/5SCL/20search/COG64+metadata1/품질/split/support/모델gate를 완화하지 않는다. `learning_ready=false`, 과학적 정확도 검증false·학습0이다.

## 다음 인계

준비freeze는 원판/runner/diff/doc/165코드·304준비freeze 지문을 고정한다. 최종 결과 뒤 실제 source/ledger/정산·old행historypending·파일SHA·나지단계와 실행 횟수를 Root에 전달한다. 이후 새후보QA/게시/API/실브라우저는 별도 배정이며 현재 게시값을 바꾸지 않는다. 내부 감사 준비이므로 UI 코드/실API/브라우저 작업0이다. 완료 결과의 이해자료·발표대본/FAQ/INDEX/이력은 Root가 이해 담당에 별도 인계해야 한다. 전체 개발/나지·독립정답·다른 모델 요구는 미완료다.


## 실제 완료 — Root 별도 GO 후 단1 감사

304 terminal22:24:54.378141 KST/exit0/424.657초, collector33032·supervisor43984 부재/lock해제를 실제 관측했다. stdout 프로그램 신규16/적격16·finalize/settle/publish 각[key]를 독립감사 전 보고값으로 구분했다. Root 요청으로 window-state/worker의 전후 identity 및두read원문 일치를 대조했고, 종료관측 JSON에는 명시1MiB cap-before-open/limit+1 재검산 근거를 남겼다. 예약68157440B를 전송량으로 세지 않았다. 별도 종료관측 SHA는 `44541e07ec8d693ca6ec482f1c17b8f979bed8078ce35b7c40b6d87a6d786c78`다.

Root가 종료·실정산·OS중복부재·postsource/ledger/pending을 확인하고 GO SHA `4d76b1211f730055417dfb126d8661e6f972cf00d1cedf10c3d825b191d4d452`를 발급했다. 이 담당이 GO와 동결runner SHA를 직접 대조한 뒤 승인 명령을 한 번 실행했다. exec session64841, 실제PID43896(parent20200), exit0/helper1/native_validation_complete=true다. helper 자체6.3469994초는 전체 trace wall이 아니며 전체 감사 wall/RSS는 별도로 측정하지 않았다.

최종 `deficit304-native-root-20261018.json`은34588B/SHA `7e933d923f6a7507a878f66bd7fea391b7b181779746f175567f0febdf8c884c`, status `COMPLETED_BOUNDED_NATIVE_AND_TRACE_CHECKED`다. 신규16 모두 적격, helper52고유 파일 SHA 검산통과/새48래스터/trace21중patchimage16중복/새미참조래스터0이다. old1763행 prefix·history·pending2 exact/136314880B 전액 보존, source/ledger 두읽기 driftfalse/false다. 예외·자동retry·추가native0이다.

현재source `0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658`/69564847B, ledger `d5ee31ff7970adaaa6b166805c240616efa8e9af713bb8394c7a166346f21c91`를 GO와 exact 검산했다. 등록1779/적격1407/전체cellgap0/대상gap0을 확인했다. 실물은 시작전검증1764+새16=1780 추론이며 운영 전체 재스캔은 하지 않았다. 등록1779와 실물1780을 구분한다.

선택source `S2C_MSIL2A_20250606T023551_R089_T49MFM_20250606T065914`, 원datetime `2025-06-06T02:35:51.025000Z`를 저장STAC/scene/row 간 원문 그대로 대조했다. .025를 반올림하거나246 strict정책을 변경하지 않았다. 실제EPSG:32749/1024×1024/6band/transform `[10,0,618880,0,-10,9146730]`에서 rawB02↔source 첫band 및16patch grid/픽셀 일치를 검산했다. 고론의32651 CRS를 하드코딩하지 않았다. 전체20원시feature 재생은 하지 않았으며 selectedmetadata 일치가 원격진실·독립정답이라는 뜻은 아니다.

실나지는 raw정렬0→sourcequality0→finalsupport0→eligible0/기여0이다. 수량상 지역·연도 최소량은 모두 채웠지만 나지 대표성3차단과 학습false가 해소됐다는 근거는 없다. 약한 참조라벨은 독립정답/과학적 정확도 검증이 아니며 새로운 전체 후보QA도 아직 수행하지 않았다.

COG22478848B+metadata367038B=22845886B 정산을 실제 worker/state/ledger와 대조했고 잔여1799757940B를 확인했다. finalize/settled/published 각각1key를 유지했으며 oldpending을 환불하지 않았다. 원본/원장/모델/split/pointer 쓰기0·HTTP/수집/학습/registry0이다.

Root에 결과·실제핀·floor0·정산·나지0을 전달했고 다음309 guarded309-20261018 고정후보QA는 준비만 이어간다. 별도 Root QA GO 전 실제QA0이다. 기존290원판/현재1360 pointer·receipt293를 보존한다. 게시/API/실브라우저와 이해자료·대본FAQINDEX이력은 Root 별도 인계이며 이 담당은 UI/전체개발 완료를 주장하지 않는다. 준비doc 원문은 archive에 원SHA로 보존하고 준비freeze/runner/299원판은 수정하지 않았다.
