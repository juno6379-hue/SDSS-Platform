# 152 — 주·연도별 부족량을 우선하는 제한 수집 진입점

상태: `TESTED_SYNTHETIC` 선택·CLI 경계 검증, `VERIFIED_REAL` 현재 저장 메타데이터의 읽기 전용 계획. 실제 네트워크 수집과 최종 적격 증가량은 Root의 별도 실행 증거로 판단한다. 구현 담당자의 수집·학습·추론·운영 쓰기는 0이며 Root가 명시 실행한 수집과 구분한다.

## 목적과 변경 범위

신규 `scripts/collect_training_priority.py`는 주·연도 셀의 적격 패치 수가 28개에 못 미치는 정도를 기준으로 기존 수집 작업을 최대 두 건 선택한다. `tests/test_training_priority.py`와 이 문서가 담당 변경 범위다. 기존 `collect_training_parallel.py`의 최소 옵션 배선은 Root가 별도로 담당한다. 다른 채팅에서 수정 중인 coordinator와 공통 문서는 이 담당자가 편집하지 않는다.

기존 main은 주별 round-robin을 나중에 적용하므로 `v2_jobs`만 정렬해서는 실행 순서를 바꿀 수 없다. 신규 함수는 그 round-robin 뒤의 실제 작업 목록에 연결한다. 전역 monkeypatch나 작업별 설정 수정 없이 기존 reserve/work/finalize, 같은 원장과 잠금, 최대 두 worker, 전역 2초 요청 간격, 첫 429 공유 중단을 사용한다. 신규 예산을 만들지 않는다.

## 선택과 고정 계획 계약

`prioritize_jobs(jobs, scenes, snapshot, *, limit)`는 원래 job 객체를 변경하지 않고 최대 2개를 반환한다. `limit`는 정확한 정수 1 또는 2이며 bool은 거부한다.

1. 모든 작업 key 중복과 기존 원장의 같은 key 설정 SHA 충돌을 먼저 거부한다. SHA 인코딩은 기존 원장의 `json.dumps(config, sort_keys=True).encode()`와 같다.
2. settled 작업은 다시 실행하지 않는다. 남은 작업 중 pending key가 있으면 거부한다. 기존 `continuation_jobs`가 명시 opt-in으로 같은 설정의 pending을 제외하는 경계를 먼저 유지해야 한다.
3. 같은 주·연도·물리 창에 적격 패치가 이미 있으면 제외한다. 원장 settled만으로 실패 창을 새 key로 바꾸거나 재시도하지 않는다.
4. `quality_status == quality_eligible`인 저장 row의 셀별 개수를 세고 `max(0, 28-count)`를 계산한다. 부족량 0은 선택하지 않는다. 부족량 내림차순 뒤 province, year, candidate_rank, key 순으로 동률을 정리하고 최대 limit개만 남긴다.

`build_priority_plan(...)`은 동일 선택의 상세 key·주·연도·split·공간창·설정 SHA, 셀별 개수, 전체 scenes/원장 snapshot SHA, 기존 pending 예약액과 계상액, `plan_sha256`를 반환한다. timestamp를 넣지 않아 같은 입력의 계획은 고정된다. `verify_priority_plan(..., expected_sha256=...)`은 명시 계획 pin이 다르면 차단한다. 이 pin은 메타데이터 선택 시점의 관측이며 파일 전체 무변경이나 다중 파일 원자 snapshot을 증명하지 않는다.

원래 적격 집계는 수집 계획 지표다. 누출 제외 후보·실제 품질 QA·동년 라벨의 신뢰·bare 기여 패치·0.5% 비율·최종 학습 준비성을 대신하지 않는다. 같은 셀에 28개가 있다고 독립 공간/scene 표본이나 모델 정확도가 성립하지 않는다.

## CLI 사용법

프로젝트 루트의 기존 환경에서 설치나 수집 없이 계획만 확인한다.

```powershell
$env:PYTHONPATH='.runtime;.;backend;tests'
python scripts/collect_training_priority.py --max-batches 2 --continue-unrelated-pending
```

기본은 stdout JSON 계획이며 출력 디렉터리 생성·계획 파일 쓰기·Ledger.snapshot 잠금 생성도 하지 않는다. 기존 config/aggregate/ledger를 읽으며 `extra_jobs`를 통한 명시 `--candidate-plan` 검증도 기존 그대로 사용한다. 호출자가 stdout을 파일로 저장하는 것은 별도 shell 동작이다.

실제 실행은 Root만 작업자·잠금·예산·보존 근거를 재확인한 후 다음처럼 명시한다. 아래 PIN은 직전에 관측한 값이어야 하며 오래된 예시 pin을 재사용하지 않는다.

```powershell
python scripts/collect_training_priority.py --max-batches 2 --continue-unrelated-pending --execute --expected-plan-sha256 PIN
```

wrapper는 먼저 pin을 비교하고 기존 collector에 `--priority-deficit --priority-plan-sha256 PIN`을 전달한다. collector는 최신 aggregate/원장으로 dispatch 전 다시 검산해야 한다. 해당 기존 파일의 옵션 배선은 Root 변경 범위다. subprocess 실행 오류는 상위 실패 코드로 전달된다. wrapper의 사전 입력/계획 실패는 고정 `PRIORITY_REQUEST_OR_SNAPSHOT_INVALID`, exit 2다. 기존 collector의 계획·로그 파일 작성 및 잠금/원장 처리에는 기존 부작용이 있으므로 실행 후 차단을 모든 파일 쓰기 0으로 설명하지 않는다.

## bare와 기존 보호 정책

기존 reserve가 생성하는 `selection_context.priority_source_classes`, 지배 클래스 보류 조건과 참조 라벨 우선 검토를 바꾸지 않는다. 그 안에서 현재 부족한 bare를 우선하는 기존 맥락은 유지된다. 그러나 로컬 bare 256 표적창은 기존 1024 중복 방지 계약에 바로 들어갈 수 없으며 이번에 지원하지 않는다. 반환의 `bare_targeted_256_supported`와 `learning_ready`는 false다. 부족 셀을 수집했다고 bare 확보·최종 적격 증가를 미리 주장하지 않는다.

기존 pending 두 건의 예약·부분 파일을 정산·환불·삭제하거나 잠금을 자동 해제하지 않는다. settled 기록, 같은 4GiB 신규 예산·3000패치 상한·기존 taxonomy/split/유효율·라벨·AOI·반사도 미인증 정책을 그대로 사용한다.

## 시험과 현재 계획 근거

명령:

```text
set PYTHONPATH=.runtime;.;backend;tests&&python -m unittest test_training_priority -v
```

최종 집중 시험 `evidence/integration/priority-collection-agent-final-20261018.log`: **9 PASS / 1.129초 / exit 0**. 부족량 정렬·최대 두 건·정확 목표 제외·연도 구분·원래 객체/입력 불변·settled/pending/설정 충돌·적격 물리창 재사용 제외·기존 SHA 인코딩·고정 동률·계획 drift·전액 예약 보존·Temp CLI dryrun 파일 불변과 명시 subprocess 인자 검증을 포함한다. 실제 collector main을 Temp에서 호출해 올바른 pin의 최대 두 작업/기존 callback 전달과 잘못된 pin의 reserve·coordinator 미호출/자기 잠금 해제를 추가 확인했다. 이때 원장·작업 coordinator와 subprocess는 Mock이며 실제 HTTP 수집 시험으로 확대하지 않는다. 초기 7 PASS/1.315초 로그는 원래 파일과 `priority-collection-agent-initial-20261018.log`로 보존했고 최종 수치와 합산하지 않는다.

읽기 검토에서 잘못된 pin 분기의 service Event 참조가 같은 Python 프로세스에 남는 경계를 발견했다. 첫 실제 수집 중에는 코드를 동결했고 종료 후 Root가 자기 fd/잠금 정리와 함께 Event를 초기화하도록 보강했다. wrapper subprocess에는 stdout/stderr를 명시 전달해 후속 실행의 로그 전달도 보강했다. 첫 실제 실행에서 child stdout이 비어 있던 사실은 남기며, 실행·정산 근거는 source config/history·수신 파일·원장·최종 JSON으로 구분한다. Root 최종 관련 시험은 `priority-collection-root-tests-final-20261018.log`의 **30 PASS / 1.901초 / exit 0**다. 위 집중9건은 보강 전 관측으로 최종 관련 근거와 구분하며 합산하지 않는다.

읽기 전용 실제 계획 `priority-collection-dryrun-20261018.json`에서는 남동술라웨시 2024년 g03(적격 1, 부족 27)과 고론탈로 2025년 g03(적격 8, 부족 20)을 선택했다. 계획 SHA는 `508b4bad371df668ca06ff737efe55a19429ba67cdd833de0ff4afd4e70ab3fe`다. 이는 이 관측에만 해당하며 실제 실행 전 변경되면 새 계획으로 확인해야 한다. 기존 pending 두 건은 각각 68,157,440B, 합계 136,314,880B를 그대로 표시했다. 이 단계의 네트워크 요청은 0이다.

Root는 collector hook을 연결하고 10:10 전후 wrapper PID35472로 위 두 작업의 명시 제한 수집을 시작했다. `priority-collection-final-20261018.json`은 두 건 정산 완료, 신규32개 생성·19개 적격, 누계1,432개 물리/1,141개 적격, 주×연도28개 계획 부족132개를 기록한다. 새32개의 bare는14픽셀로 256픽셀 기여 패치나 bare 학습 차단 해소가 아니다. 이전1,400개와 기존 pending 전액136,314,880B를 보존했고 신규 예산 잔여는2,297,868,407B다. 이 첫 제한 실행의 실제 결과와 후속 round2 시도는 별도 실행 근거로 구분한다. 원장·합산·run-result의 정상 변경은 수집 결과이며 원본 영상·기존 정산 기록·예약 보호와 혼동하지 않는다.

이 CLI는 API/UI 요청·모델·승인 계약을 바꾸지 않으며 별도 화면 연결이 필요하지 않다. 부족 현황 UI는 별도 담당 범위다. 구현과 제한 수집이 작동해도 모든 주×연도 확보·bare 목표·누출 제외 후보의 최종 QA·전체 프로젝트가 완료된 것은 아니다. Root가 공통 문서·이해자료와 실행별 보존 근거를 별도로 마감한다.

## 독립 읽기 감사와 두 번째 제한 실행

`priority-collection-independent-20261018.py/json/log`는 **15.2078273초 / exit0**의 별도 읽기 감사다. 기존1,400개는 launch의 canonical metadata SHA와 대조했으며 과거 전체 raster QA를 다시 한 것은 아니다. 기존 pending2의 exact row·전액136,314,880B, 첫2건의 settled record·config SHA·window-state/worker terminal 계측 비용을 확인했다. 신규32개 실제 patch image/label/quality 배열과3역할 SHA·grid·valid·inside·품질 상태·클래스 계수, source crop SHA를 대조해19적격·bare14와 일치했다. 실제2,097,152 patch픽셀을 검사했으며 감사 중 원본/원장 쓰기·예약·HTTP는0이다. 자체 감사 helper의 초기 scripts import 경로와 quality_mask_path 필드 오기는 원로그를 각각 보존하고 수정했으며 제품 실패가 아니다.

두 번째 제한 실행의 east_java2025-g01/g02는 원장상 모두 settled이지만 실제 자료 수집은 실패했다. 신규 패치0·계상1,325,635B, 누계1,432/1,141·부족132를 유지했고 예산 잔여는2,296,542,772B다.429는 없고 기존 pending은 그대로다. 새 stdout 전달로 worker 시작/종료 각2개가 기록됐으며 첫 실행의 빈 stdout과 구분한다.

`priority-collection-independent-round2-stage-20261018.py/json/log`는 저장된 source metadata와 코드 순서를 읽어 두 실패 모두 SCL 후보 적격·STAC/calibration 저장 뒤 raw crop/label_first_preview가 없는 것을 확인했다. 동년 Esri 약한 라벨의 초기 crop fetch 단계에서 중심 COG 범위 오류가 난 것으로 **코드 순서와 저장 흔적에서 추론**했으며 새 runtime stage 계측이나 HTTP 재현은 아니다. 서명 query/fragment는 출력하지 않았다. guard 완화·재시도·좌표 교정은 하지 않는다.

동일 감사 시점 기본 centers4에서 settled/pending/적격 물리창을 제외하고 부족 셀에 남은 미예약 작업은20개였다. nominal 상한은320패치지만 구름 없는 scene·독립 공간·실제 적격 증가나 실행 가능 수량이 아니다. 다음 순서의 맨 앞은 east_java2025-g03와 gorontalo2022-g03였으며 이 감사는 실행 pin을 발행하지 않았다. centers16 확대는 기존 laneB와 새 기하 중복을 검증하지 않아 권장·실행하지 않는다.

## 세 번째 제한 실행과 누계

Root의 `priority-collection-round3-final-20261018.json`은 east_java2025-g03와 gorontalo2022-g03의 정상 정산·신규32개/적격23개·적격 약한 라벨 bare148픽셀을 기록한다. 주×연도 부족은132→109개, 누계는1,464개 물리/1,164개 적격이며 단순 총 적격 목표1,200까지36개가 남는다. 목표1,200과 셀당28·클래스 기여/비율·누출·독립 정답 조건은 별도다.

152의 세 제한 실행을 합치면6 batch 중4건 자료 수집 성공·2건 COG 범위 실패, 신규64개 물리/42개 적격/적격 bare162픽셀, 셀 부족151→109개, 총계상87,636,806B다. 이전148의 별도 재개 실적과 중복 합산하지 않는다. 세 번째 계상은42,273,334B, 예산 잔여2,254,269,438B이며429없음·실행 잠금 없음·이전1,432 row와 기존 pending2 보존을 Root가 확인했다. bare162는 이64개 전체의 합계이므로 이 새 적격 자료 안에서 bare256 이상 기여 패치를 확보한 것은 아니다.

Root 관련 검증은 최종48 PASS/5.326초로 갱신됐으며 collection status의 오래된 기존 native hash 처리 회귀를 포함한다. 이는 전체 backend 재실행 수치가 아니다.

`priority-collection-independent-round3-20261018.py/json/log`의 증분 감사는 **20.6078322초 / exit0 / 초기 오류0**이다. 새32개 실제 배열의3역할 SHA·grid·valid/inside·품질 상태·클래스 계수와 source crop SHA/헤더·config/state/terminal/정산 비용을 대조해23적격·bare148을 확인했다. 첫32개는96개 patch 파일을 재해시하고 첫 source config/report/worker/state의 기존 SHA를 대조했다. 첫32개의 배열 통계를 다시 계산한 것으로 표현하지 않는다. 이전1,432 row와 원래1,400 row는 각각 canonical metadata SHA로 확인했고 미정산2개 전액도 그대로였다. 감사 중 고정 aggregate/ledger는 바뀌지 않았지만 OS 원자 snapshot을 증명하지는 않는다.

이 후속 관측의 기본 centers4 미예약 부족 셀 후보는18개·nominal 상한288패치였다. 앞의20개 관측에서 이번2개가 소비된 결과이며 실제 가용 scene·품질·독립성이나 향후 적격 수율은 아니다. 감사는 실행 pin·예약·HTTP를 만들지 않았다. 이 시점 네 번째 실행은 없으며 다음 수집을 자동 예약하지 않는다.


## 2026-10-18 10:54 KST — 4차 수집 완료·159 후보 UI 승계

앞선1464/1164 관측 이후4차 반텐2025 g01/g02가 정상종료했다. 신규32물리/32적격/나지391픽셀로1496물리/1196적격/300부적격,train681/val265/test250이다. 전체1200 부족4·주연도 셀당28 부족97이다. 최초요청대비96물리/74적격을 추가했고 셀 부족151→97,나지추가553픽셀이다. 4차32개 실제래스터·유효/주내·클래스·SHA 및source/worker/원장 정합성을12.7664229초에 재검증했고 기존1464행과pending2전액136314880B를보존했다. 신규총계상2085380105B/한도잔여2209587191B,429false/실행lock정상해제다. 원본검증분할 나지는209→600픽셀,기여0→1개로 개선됐으나0.5%·기여5패치 기준은미달이다. 1200개충족과학습준비는별개다.

159의1432행고정source→누출16행제외후1416행/1125적격 후보는실제QA·4435파일SHA검증후명시receipt로승계했다. 기존153후보/receipt와교체전pointer원바이트를보존하고,새receipt3핀검산·readyfalse/차단4 검산후pointer원바이트가변하지않았는지비교하고os.replace로교체했다. DatasetRegistry/모델/원장/기존분할/학습상태전이0이다. 부가connectivity NOT_CAPTURED_BUDGET 한계는유지한다. 최신1496원본의55적격(23+32)은새1125후보QA범위밖이며sourceSHA불일치경고를유지한다.

실제API8002/프런트5174 소스변경·재시작 없이기존GET·명시수동새로조회로승계됐다. 브라우저응답01:52:31.145480Z에서원본1196(681/265/250)·후보1125(658/217/250)·차단4/미준비·시점불일치·원본검증나지600/기여1을확인했다. console warning/error0,가로넘침0이며분석/학습/배포/등록버튼을실행하지않았다. 전체페이지스크린샷1회timeout은브라우저캡처한계로기록하고실제viewport PNG/DOM/JSON을보존한다. 제품소스변경없으므로기존48관련backend·288격리frontend·build120근거를유지하며새전체회귀통과를주장하지않는다.

5차동자바2021 g02/g03은plan fe20a0b67e5b6215d3f0e4814a07e48b9645a2fb6ba90893b4c3049cd62b8ade,wrapperPID33756으로시작했고완료는미확인이다. 기존budget/2worker/2초/429중단/3000상한/고정split/품질정책을유지한다. 같은collector중복실행금지.157표적은계속집행차단이며160로컬자산영역검사작업은다른채팅소유기록과중복하지않는다. geoai-2 ACTIVE10분보고지속,전체개발미완료다.

근거:evidence/integration/priority-collection-round4-final-20261018.json,priority-collection-independent-round4-20261018.json,priority-collection-round5-launch-20261018.json,priority-ml-next-ui-promote-20261018.py,priority-ml-next-ui-receipt-20261018.json,priority-ml-next-ui-round4-20261018.json,priority-ml-next-ui-round4-20261018.png 및docs/implementation/159_next_collection_candidate_qa.md.
