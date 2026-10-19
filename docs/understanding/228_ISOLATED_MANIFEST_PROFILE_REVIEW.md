# 228 — 격리128MiB profile 구현과 독립리뷰의 적용 차단

> **현재결론:BLOCKED/수정필요.** 완료231 정적리뷰는①staging 복사 I/O 누락 ②상한검사 전 hash·suffix 휴리스틱 ③큰 caller cap/depth 허용 ④자원 오류의 행별 catch를 확인했다.아래88 PASS·합성bench는그판본의시험사실이며완전한자원안전성/운영적용승인이아니다.230은새격리사본에서수정중이며main적용0이다.

- updated_at: 2026-10-18,228완료격리증거와Root231리뷰후속 기준
- source_commit: 격리사본내patch11파일의before/afterpin;공유제품변경0
- evidence_paths: `docs/implementation/228_explicit_manifest_profile_isolated.md`, `evidence/integration/preprocess228-workspace-20261018/freeze228.json`,patch228-manifest,benchmark228-result,최종회귀로그, `docs/implementation/231_manifest_profile_independent_review.md`
- confidence: 격리파일/저장합성시험·bench값은확인.현재rich source/3000행·모든I/O보호/운영성과는미검증.
- status: `TESTED_SYNTHETIC` 격리88시험이력 / `BLOCKED` 231발견결함의보완필요 / `PLANNED` 공유제품적용·실원본QA

## 1. 쉬운 설명

**228은 운영코드와 떨어진 실험용 사본에서 큰 자료목록을 처리하는 명시profile을 만들었다.하지만 독립검토에서 빠진 경로가 발견돼 그대로 적용하면 안 된다.**시험책상에서큰서류를처리해봤다는것과모든입구의검사가완성됐다는것은다르다.

sourceJSON이64MiB에가까워후처리공백을줄이는목적이다.원격영상을더받는예산을늘리는기능이아니다.227실QA는기존공유판에서실행돼228사본을소비하지않았다.

## 2. 격리범위와계약

`preprocess228-workspace-20261018/`에는필요한backend/scripts/tests/configs 코드사본만있다.운영source·원장·래스터·모델은읽거나복사하지않았다.입력코드manifest와baseline-code에원판pin을보존했다.코드복사는순차관측이며다중파일원자snapshot이아니다.

| 격리profile값 | 내용 |
|---|---|
| 이름 | bounded128m-3000-v1 |
| source/candidate입출력 | 128MiB=134,217,728B |
| 합산행 | 3000 |
| 깊이/검사방문노드 | 32/4,000,000 |
| 명시작업누적JSON I/O | 16GiB |

노드4M/누적16GiB는prototype값이며실rich3000행을측정해충분성을승인한숫자가아니다.기본None의64MiB/v1artifact를유지하고명시scope에서만128/v2receipt+profiledigest를전파하려는구현이다.잘못된profile/v1-v2혼용은닫혀야한다.

COG64+metadata1MiB·원격추가4GiB·개별TIFF64MiB·readiness16MiB·plan4MiB·작은receipt64KiB·실물3000·split/품질/나지·2초/첫429는확대하지않는다.16GiB는반복로컬JSON검증의회계값이지원장예약이아니다.

## 3. 연결한사본과미연결소비자

```mermaid
flowchart LR
  A[격리164명시profile] --> B[snapshot·계획·materialize]
  B --> C[v2package/stage/QA·비교reader/API]
  C --> D[격리시험·합성cap bench]
  D --> E[231리뷰결함→적용BLOCKED]
  E --> F[230새격리사본수정중]
```

신규manifest resource helper·164·strictJSONIO·materialize/stage/QA·readiness/experiment·comparison/API사본에scope/marker/회계를연결했다.두import표기의ContextVar를공유해작업회계가갈라지지않도록한회귀도있다.scope종료후기본값복원을검사했다.

그러나173나지탐색·182공간제안·225예산sourcehash는기존64MiB입구가남는다.전처리만통과해도다음소비자가막힐수있다.전체제품의모든경로가128로확장됐다는표현은틀리다.230이별도새격리사본에서이소비자들의명시profile연결과231결함을보완중이며공유main/서버적용은0이다.

## 4. 시험과bench가확인한것

최종격리 **88 PASS/74.061초·0 SKIP**는새9+기존관련79이며실원본QA가아니다.명시profile·v2marker/기본artifact바이트동등·구reader거부·metadata단계연결과낮춘budget으로guard경로를시험했다.실raster/sourceQA는Mock했다.개발중cwd/import/fixture오류기록은보존하고최종에합산하지않는다.

child1회의whitespace padding합성JSON bench는64MiB정확통과/기본64+1거부·명시64+1/128통과·128+1읽기전거부·출력초과쓰기가드를관측했다.child wall31.148초/CPU24.391초/peak426,115,072B(약406MiB)·exit0이었다.이는단순작은scenes뒤공백으로채운파일이며현재rich source나3000행최대중첩형태가아니다.

bench는최종dual-import보호추가전동일cap/parser경로의한번실측이고마지막scope보호는회귀로검사했다.최대노드4M/누적16GiB를실제최대부하로소모한시험도아니다.207/227실제지연원인·현재128운영성공·일반성능SLA를이수치로확정하지않는다.

## 5. 231독립리뷰의수정필요와현한계

완료 `231_manifest_profile_independent_review.md`를직접읽어아래네수정사항을반영했다.이것은추가재현시험이아닌정적호출순서검토다.

1. **staging 복사 read/write 누락:** `_copy_bytes`의읽기/쓰기가JSON예산에계상되지않는다.128MiB후보의읽기+쓰기최대256MiB가빠질수있다.복사SHA/정확성검사는남아있으므로파일이잘못복사된결함으로과장하지않는다.
2. **상한보다먼저hash·suffix로역할추정:** readiness의일부JSON은무제한digest가EOF까지읽은뒤boundedparser가거부한다.164digest는`.json`일때만계측해`.JSON`/무확장자실JSON이빠질수있다.역할에결속한boundedhash와읽기전cap/identity·실chunk계상이필요하다.
3. **caller정책이descriptor보다커짐:** source/candidate cap이정확64MiB일때만128로치환하고caller의256MiB/depth64는그대로둘수있다.현재고정164경로가즉시이를허용한다는뜻이아니라공개helper의상한보증공백이다.더작은역할cap은보존해야한다.
4. **자원초과를행QA오류로삼킴:** normalization metadata의자원ValueError가`except Exception`에서SCENE_QA_ERROR로바뀌고다음행으로진행할수있다.학습을true로만드는결함은아니지만‘어떤자원한계든전체작업중단’계약과다르다.자원전용예외재전파와다음read/완료receipt없음시험이필요하다.

따라서현재16GiB계측값을전체JSON I/O의강제상한으로믿을수없다.88 PASS의기존정상/경계시험사실은보존하되위공백을완전검증한것으로확대하지않는다.230은재개확인된새격리사본수정중이고중간결과를최종완료로인정하지않는다.공유main/서버적용0·실rich128운영QA미검증이다.

231은추가로mutable Budget이복사된context의child task/thread와공유될수있음을지적했다.현재직렬CLI/API semaphore1의의도범위이며독립병렬작업격리/thread-safe원자계상을검증했다고쓰지않는다.이해담당은완료리뷰문서를읽었고추가thread/벤치/QA를실행하지않았다.

원본/원장읽기·실QA/native·HTTP·collector·공유제품변경0은228freeze의범위다.현재source를128profile로검사하거나복구한기록이아니다.향후실제적용은독립diff검토·소비경로연결·rich자료한도실측·실행pin·UI/API계약을별도로확인해야한다.이번문서는설명만추가하며core/UI/CONT/raw·운영쓰기0이다.

## 6. 발표대본

### 1분

“228은128MiB 자료목록 profile을 운영과분리된 코드사본에서 구현했습니다.격리88시험과공백으로채운합성JSON의경계부하시험은통과했지만현재실제복잡한원본으로검증한것은아닙니다.독립리뷰에서는JSON I/O복사경로와검사전hash·파일확장자추측에빠진보호가발견돼현재적용은차단상태입니다.230은새격리사본에서그결함과다른소비자연결을보완할예정입니다.공유main은아직변경하지않았고원격예산도늘리지않았습니다.시험통과이력과완전안전·운영적용을구분합니다.”

5분발표는격리/공유범위1분,128/3000/노드/I/O계약1분,88시험/whitespace bench1분,231결함1분,230예정·main0/실자료미검증1분이다.10분은receipt/소비자전파2분,parse/누적I/O와메모리한계1분,Q&A2분을더한다.추가bench/운영QA를시연하지않는다.

## 7. FAQ

- **지금sourcecap이128로바뀌었나요?** 공유판/main미적용이고격리사본뿐이다.
- **88시험으로안전이보장됐나요?** 독립리뷰에서미포착결함이발견돼수정필요/BLOCKED다.
- **406MiB면실자료도그만큼쓰나요?** whitespace합성한번실측이며rich metadata메모리보장이아니다.
- **16GiB를다운로드하나요?** 로컬누적JSON회계prototype이며원격예산은그대로다.
- **173/182/225도확장됐나요?** 228에는남아있는64MiB경로이며230명시연결은예정이다.
- **231을여기서재현했나요?** 완료독립정적리뷰문서를읽었으며추가실행은없다.
- **230이main에반영됐나요?** 새격리사본에서수정중이며공유적용0이다.

관련: [228 격리구현원문](../implementation/228_explicit_manifest_profile_isolated.md),[217 자원계약](217_RESOURCE_CAPS_AND_211_BLOCK.md),[231 완료독립리뷰](../implementation/231_manifest_profile_independent_review.md),[227 실제QA](227_POST223_CANDIDATE_QA.md).
