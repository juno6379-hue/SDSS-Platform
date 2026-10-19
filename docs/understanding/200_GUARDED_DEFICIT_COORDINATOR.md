# 200 — 추가1024 후보의 검사를 계측 수집·정산에 연결하는 실행 조정기

- updated_at: 2026-10-18 13:50 KST 최종동결 근거 기준
- source_commit: 공유HEAD 대신 개별 완료파일 SHA 기준
- source_sha256: `scripts/collect_deficit_guarded.py` = `9797930f8ad04728af5f2f2fb4e49218dbf1f046f9c47c78b7a6e675821c627b`
- evidence_paths: `docs/implementation/200_deficit_guarded_coordinator.md`, `tests/test_collect_deficit_guarded.py`, `evidence/integration/deficit200-freeze-20261018.json`, `deficit200-related-final2-20261018.log`
- confidence: 완료코드·임시 원장/격자/파일·모의provider 회귀는 높음.실제 원격수집·품질성과는 이단위에서 미검증.
- status: `TESTED_SYNTHETIC` 최종77 PASS / `IMPLEMENTED_UNVERIFIED` 실제 운영 원격성과 / `BLOCKED` 잘못된요청·pin·proof·잠금·상한

## 1. 쉬운 설명

**200은 새 촬영 주소의 검사를 실제 수집 절차와 비용 정산에 연결한 실행 조정기다.**199가 검사 부품이라면200은 단일 작업 열쇠를 잡고 그 부품을 다시 검사한 뒤,두 작업자가 같은 장소·장면·예산을 공유하게 관리한다.이제 코드와 시험의 연결은 완료됐지만,시험 통과가 실제 위성사진 확보를 뜻하지는 않는다.

205의검토결과파일을 승인서처럼 재사용하거나199의실행false를true로 바꾸지 않는다.실행 잠금 안에서199를 새로 호출해 현재 원본과 원장을 다시 확인한다.실제 수집206은 별도 실행과 실자료 증거로 보고해야 한다.199·205 문서의 “200 연결 미완료”는 그 관측 당시 기록이며,이번200은 연결 코드와 시험의 후속 완료다.운영성과 미검증과 구분한다.

## 2. 이론적 배경

검토 후 실행 전까지 다른 작업이 자료를 추가하면 이전 검토는 오래된 결과가 된다.이를 줄이기 위해 배타적 잠금을 먼저 잡고 고정요청·활성원본·원장·지원범위·실물 용량을 다시 확인한다.잠금이 있으면 자동삭제하지 않고 중단한다.

두worker가 각각 별도 장소/scene 사용표를 가지면 상대작업과의 중복을 놓칠 수 있다.200은 하나의scene registry와 하나의window claims를 공유한다.최종256패치가16개 나올 수 있는1024창을 최대2개 요청하므로,실물상한은 명목32개까지 보수적으로 계산한다.명목수와 최종 적격수·나지수는 다르다.

요청의canonical JSON SHA는 정렬된내용의지문이며,파일바이트SHA와 다를 수 있다.서명·기관승인이 아니다.DATA 고정사본도 활성원본과SHA가 같으면 검토입력으로 허용하지만 실제쓰기는 고정운영경로에만 한다.

## 3. 실제 코드·입력·동작

`run_deficit_guarded(project_root,request,expected_sha256,execute=False)`가 진입점이다.199의명시요청과예상canonical SHA를 그대로 받으며 기본execute는false다.후보·연도·우선순위·새예산을 자동생성하지 않는다.CLI는 workspace의 `evidence/integration` 아래2MiB 이하strict JSON을 읽는다.

```mermaid
flowchart LR
  A[고정요청·digest·명시execute] --> B[배타execution lock]
  B --> C[199 fresh검사·활성pin·job/target 재검산]
  C --> D[공유scene/window·selection context]
  D --> E[출력배타예약·예산예약·최대2worker]
  E --> F[실B02 callback·1024수집·최대16분할]
  F --> G[측정terminal·중앙settle·원본append·진행기록]
```

주요 연결은 다음과 같다.

- `validate_request`:199proof의localchecks·입력지문·inventory3flag·실물3000·job크기1024/명목16·config SHA·주/연도/고정split·bbox/target·key를 재검산한다.이전205 proof파일을 읽는 경로가 아니다.
- 실행잠금:기존global lock을O_EXCL로 취득한다.기존파일이 있으면 검사/예약전에 거부하고,끝에는 자신이 취득한identity와같을 때만 해제한다.
- 예약:새sources/patches leaf를배타생성하고batch당COG64MiB+metadata1MiB를같은4GiB 원장에예약한다.기존빈디렉터리도재사용하지 않는다.
- context:현재split의부족클래스비율·기여패치수에서`selection_context`를만들어파일과collector에전달한다.기존충분한자료의숲우세보류정책도유지한다.
- 실제수집연결:같은registry/claims와199의1024 guard를 `collect_windows(...,collection_guard=...)`에전달한다.2worker·전역최소2초·첫429회로·재시도0을유지한다.
- 분할:검산한B02 witness가있어야materializer를호출한다.새source는최대1개이고예약폴더안의6밴드1024×1024여야한다.잘린창/256/잘못된출처는분할전에차단한다.
- 정산:worker의COG·thread-local metadata 측정을terminal로남기고중앙finalize가settle한다.기존행/history/pending을보존해새행·report/error만append한다.

일반1024자료수집은나지256표적수집과다르다.나지256픽셀을신규최소조건으로추가하지않는다.최종유효80%·행정경계등실품질과나지기여는별도확인해야한다.B02 witness=true도기하콜백통과사실이며최종품질합격이아니다.

## 4. 실패를 숨기지 않는 계약

예약이후context구성·worker finally·terminal측정이실패하면전송량을0으로만들거나자동환불하지않는다.미계측새pending은예약전액을보존하고실행진행단계와함께미확정실패로반환한다.기존pending2 전액136,314,880B를재정산/환불/재실행하지않는다.

settle뒤원본게시나run-result저장에실패할수있으므로 `settled_batches`와`published_batches`를나눈다.cleanup실패도구분한다.실패응답의 `executed=null`은실제전송/정산을한줄오류로확정하지못한다는뜻이다.

**원장·aggregate·run-result의다중파일원자commit이나영속journal,exactly-once복구는보장하지않는다.**자동retry/rollback·누락terminal보충도없다.복구담당은실제원장·파일·phase를읽어판단해야하며기존잠금이나예약을임의로지우지않는다.

## 5. 시험 증거·한계

최종소스기준 **관련77 PASS/28.002초/0 SKIP**다.신규22개를포함하므로집중22 PASS/17.678초와합산하지않는다.최종freeze는13:50:47 KST,시험SHA는 `db76f1929586d3fdbb1eca40119533e20d25c39faf4b56221c016b126fe1086a`다.기존199/170/collector/parallel 파일수정0은freeze의read_only_dependencies로구분한다.

직접읽은시험은실제Temp원장·exclusive lock·두worker·기하·native raster와materializer를사용했다.특히Temp1024×1024×6 영상과단일밴드라벨·품질파일을만들어실제materializer로16패치파일을생성하고기존prefix보존/append를검사했다.**provider·B02 witness·fullinventory/physical스캔은명시Mock이므로실제위성장면선정이나원격다운로드증거가아니다.**

다른시험은digest/기존lock/proof변조/active drift/물리상한예약전차단,동일SHA DATA사본허용·사본불변,공유registry/context,Temp97B실정산,256/잘린source거부,예약후실패·미계측pending보존·settle/게시/cleanup단계분리,429회로와기본dryrun의HTTP/예약/원장/lock/출력0을확인했다.

초기13시험중1ERROR는시험집계의Windows cp949 읽기문제였다.UTF8명시와fixture cleanup수정후최종회귀를통과했다.초기·중간로그를보존하며최종건수에중복합산하지않는다.실제운영collector/원장장애로해석하지않는다.최종1행보강은worker오류가있어도이미확인한B02 witness를finally에보존하는것이며77최종회귀에포함된다.

freeze상 운영inventory스캔0·HTTP0·collector시작0·native재검사0·운영원본/원장쓰기0이다.신규내부CLI라API/UI계약은변경없고이단위의실브라우저/build는추가하지않았다.206의실제실행·성과는향후별도근거로추가해야하며여기서예측하지않는다.

## 6. 발표 대본

### 1분

“200은 새1024 촬영 후보의 검사를 실제 수집과 정산에 연결한 실행 조정기입니다. 단일 잠금을 잡은 뒤199 검사를 새로 수행하고,두 작업자가 같은 장면과 공간 사용표를 공유하도록 했습니다. 실제 임시1024 영상·라벨·품질파일을16패치로 나누고 원장을 정산하는 시험까지 포함해 관련77개를 통과했습니다. 하지만 위성 서버와 지원재고는 모의 처리했으므로 실제 사진 확보 성과는 아닙니다. 측정이 끊긴 경우에는 비용을0으로 만들지 않고 예약을 보존하며,다중파일 전체를 한 번에 복구하는 보장은 없습니다. 별도206의 실제 실행과 native 검증을 확인해야 적격 증가를 말할 수 있습니다.”

### 5분

1.199검사부품→205실제검토→200실행연결의차이를설명한다(1분).
2.잠금안fresh proof·활성pin·공유scene/window를설명한다(1분).
3.context·B02 witness·1024/16분할과실정산을설명한다(1분).
4.77시험의실제Temp/Mock경계·초기cp949수정이력을설명한다(1분).
5.미계측pending·settled/published분리·206실자료후속을설명한다(1분).

10분발표는실패phase/복구한계2분,DATA사본과활성원본1분,질의응답2분을더한다.슬라이드는‘검사를실행에연결’,‘공유열쇠와현재지문’,‘측정·정산·게시’,‘시험과실수집의경계’다.시연은코드/보존시험로그읽기이며새dryrun/fullscan/수집도추가하지않는다.

## 7. FAQ

- **199flag를true로바꿨나요?** 아니다.199의실행false를유지하고200이fresh검증한명시요청으로별도실행경로를관리한다.
- **205검토파일을그대로쓰나요?** 아니다.실행lock안에서199를새로호출한다.
- **77 PASS면위성영상16개를받았나요?** 아니다.Temp1024한창을16패치로나눈시험이며provider/원격자료는Mock이다.
- **나지부족이해결되나요?** 일반자료수집이다.실제나지기여·품질·학습준비는후속증거가필요하다.
- **실패하면예약이자동환불되나요?** 측정미확정이면전액pending을보존한다.완료나측정0을발명하지않는다.
- **정산했는데화면에없을수있나요?** settle후aggregate게시가실패할수있어phase를나눈다.전체원자commit보장은없다.
- **기존잠금은자동복구하나요?** 아니다.기존lock은거부하며자신의identity가같은잠금만해제한다.
- **206이완료됐나요?** 이문서의200시험범위밖이다.실제실행·terminal·native/UI근거로별도보고해야한다.

관련: [200 구현/실패계약](../implementation/200_deficit_guarded_coordinator.md),[199 검사부품](199_DEFICIT_CANDIDATE_GUARDS.md),[204·205 실제로컬제안/검토](204_205_FRESH_CENTERS_AND_REVIEW.md).

## 8. 후속206·208 — 실제 CLI 차단과 격리환경 보완

위200 구판979793…의77 PASS는당시시험기록으로보존한다.실제206은proof검사에서worker/예약전차단됐고신규출력0·원본/원장불변이었다.208은구판bootstrap과199지연import를프로젝트밖Temp subprocess에서연결해루트sys.path누락으로scripts패키지를못찾는결함을독립재현했다.원206로그에는그최초예외가직접기록되지않았다는한계를유지한다.

ROOT경로명시와제한된대문자issue진단을보완한최종source는6e41c4…f112a이며관련79 PASS/33.288초다.199/170/collector가드와206원기록을바꾸지않았다.신규2시험은79에포함되며실원격수집은미검증이다.[206·208 전용해설](206_208_CLI_BOOTSTRAP_RECOVERY.md)에실차단·독립재현·시험·구판SHA역적용보존출처를정리했다.209실제성과는별도증거로보고한다.

## 후속209 — 수정판의 별도 실제 수집 완료

위코드/시험완료와운영미검증은당시기록이다.이후별도209에서수정판6e41c4…로실제32패치/22적격·셀부족33→24·나지0을확인했다.독립native1회9.115초/104SHA와별도B02출처연결검사를완료하고기존예약/원본을보존했다.[209 전용해설](209_REAL_GUARDED_COLLECTION.md)에계수/예산·감사준비실패·임시launch변환·추가38참조중복한계를정리했다.207최신후보QA와최종실UI승계는별도미완이며206원실패나200/208시험의성격을소급변경하지않는다.
