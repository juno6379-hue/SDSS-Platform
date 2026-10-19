# 249 — 남동술라웨시 새 위치 단일 수집과 기록 실패 보호

상태: **VERIFIED_REAL — 실행·좁은 감사 완료 / 신규 패치0**. 2026-10-18 17:19:08 KST 시작,17:21:19 종료했다. 아래 시작 관측은 당시 기록이며 현재 실행 중이 아니다.

## 실행 근거와 한도

235는 후보 SCL5개 모두 예비 유효65% 미달로 신규 자료0이었다. 239 좁은 감사 뒤245는 기존44개 제안을 원순서로 보존·제외하고 명시 profile 아래 로컬182 CLI를 단1회 실행했다. 59.109초/115header·새4위치·입력 source/ledger 안정성을 확인했지만 full support/pending과 실제 영상품질 검증은 아직 하지 않았다.

Root는245의 새 고정 source 사본을 재사용해 남동술라웨시2024 `centers182-southeast_sulawesi-f5fa8f8ccc4f` 한 곳만 골랐다. `deficit249-prepared-request-root-20261018.json` canonical SHA는 `7fdcb4d284c64d884e5aec55a4e739dd509afd6762965877cf7d2f1531060a0e`다. 최대1batch·16물리, 시작 전 source4f8f…d3e8/원장9c452…6c86/잔여1,895,530,489B/기존pending2 전액136,314,880B를 고정했다.

Root `deficit249-reviewed-code-pins-root-20261018.json`은 현재 코드31개,235 감사,245 입력, 실제247 API·248 브라우저 근거를 묶는다. 205 과거 proof는 같은 config에서 AOI id/bbox만 바꾸는 예상 config 계산용이다. 실제 전체 inventory 증거로 사용하지 않으며 result/request 지문을 승인 파일과 비교한다.

## 기록 오류에서도 자식 소유 유지

독립 정적 검토에서 spawn 후 launch JSON 쓰기가 실패하면 자식이 실행 중인데 supervisor 추적이 종료될 수 있는 공백을 발견했다. Root는 새249 supervisor에만 `launch_and_wait`를 추가했다. launch 기록 또는 stdout 알림이 실패하면 오류 종류를 보존하고 **finally에서 자식 종료를 기다려 실제 exit를 받는다**. 이후 terminal 근거를 남긴다. 과거235 코드·산출물은 수정하지 않았다. 저장 매체 자체가 전부 실패하는 경우 terminal 기록을 보장한다고 주장하지 않는다.

`deficit249-supervisor-final-failure-tests-root-20261018.json`은 실제 Temp 자식3경로(정상/기존 launch 파일로 쓰기 실패/launch+stdout BrokenPipe 동시 실패)를 검사했다. 각 자식이 marker를 쓰고 exit7로 종료한 뒤에만 함수가 반환했다. 이는 작은 supervisor 오류 처리 시험이며 실제 collector·네트워크·원장 시험이 아니다. 앞선 두 경로 시험 증거도 역사로 보존했다. 최종 supervisor SHA는 `3506f3f9baacb83c4d984582fdc2dd6ca906e50bd6a0ee5c5e5e5d14368b374d`이며 독립 정적 재검토에서 지적 범위의 미해결 차단은 없었다.

## 실제 시작과 다음 검증

Root는 다른 채팅 notLoaded/interrupted, 활성 collector/QA와 잠금 부재를 확인한 뒤 실행했다. exec session50744, supervisor33072/collector33696이다. 17:19:38 독립 관측은 프로세스·lock 존재, stdout 비어 있음·terminal 없음으로 사전 검사만 확인했다. 실제 상호배제는 OS 목록 관측이 아니라 코어의 O_EXCL execution lock이 수행한다.

기존4GiB 추가 총한도·2worker·공유2초·첫429 공동 중단·물리3000·batch64MiB COG+1MiB metadata·고정 split·원본·모델·oldpending·187잠금 archive를 유지한다. 예산 증가·임의 환불·gate 우회·학습은 없다.

종료·실정산·lock/OS종료를 확인한 뒤 Root가 원본 고정과 감사 GO를 별도로 내린다. toolbox_review만 신규 최대16개를 단1회 bounded 감사하며, 새patch0이면 native0 좁은 감사만 한다. 새자료가 있을 때만238 고정 후보 QA를 Root 승인 후 수행한다. API profile source 결속과 후보·나지 검토의 시점 차이를 정직하게 표시하고 실API/브라우저·문서·이해자료까지 이어간다. 현재1358/셀21·게시1342/차단3에 미래249 성과를 더하지 않는다.

## 실제 종료·정산·차단 원인

249는 exit0/129.110초·worker1/최종patch0/eligible0/liveB02false/429false다. 정상 프로세스 종료는 수집 성공이 아니다. 후보는4개였으며 SCL 예비율10.772705/54.079437/46.969604%는65% 미달,2024-08-13 후보81.554794%는 통과했다. 선택scene S2B_MSIL2A_20240813T021349_R060_T51MUR_20240813T055551의 STAC SHA/id/datetime 연결을 감사했다.

이후 window_geometry_guard 단계에서 CENTER_B02_ALIGNMENT_SHORTFALL로 차단됐다. 기존 가드는 계획1024 native rectangle과 실제 B02 각 경계 차이가10.000001m 이내인지 비교하며, 통과한 뒤에만 b02_checked를true로 만든다. 이번 actual failed B02 bounds/window_transform은 저장되지 않아 어느 변이 몇m 어긋났는지 미확정이다. 저장된 SCL·Esri bounds를 실패 B02 bounds라고 대체하지 않는다. 235의 후보5개 모두 SCL 미달 종료와 원인이 다르다.

COG1,310,720 + metadata269,558 =1,580,278B 실제정산·settle/finalize/publish 각1이다. 기존1,715행·history·oldpending2전액136,314,880B·적격1358/셀21을 보존했다. 새patch경로가 비어 있어 native검사0/같은후보QA반복0이다. 실물1716은 collector전검사값과 신규0에서 유지로 해석했으며 전체실물재스캔은 하지 않았다.

source_manifests 참조만1개 늘어 현재 source6899f9019670e9eff3e40cd9e5441a91bbaf11fae236cbbc8c2eac27ffa31e15/66,827,175B, ledgerc7ef4985a0c7f55a4a0a48c1db2b8ab4bef8d87be3a91e5175a948f56d613f4f,잔여1,893,950,211B다. 시점불일치를 숨기지 않고 profile의 명시 source 재결속·실API/UI를 별도253/254후속으로 검증한다. 게시1342/50검토 pointer는 그대로 보존한다.

초기 좁은감사의 ‘5개 모두SCL탈락’ 가정이 실제4개후보·후속기하실패와 달라 assert실패한 INCOMPLETE JSON/log를 보존했다. 근거를 맞춰 쓰거나 기존파일을 덮지 않고 새 run2 감사로 원인을 정정했다. 최종 근거 deficit249-native-root-20261018-run2.json SHA6beed046a69e8cddce35df65fa2ea1ae6c16199dd42808d71a3045d7ef64146c의 체크와 launch코드핀은 모두true,9개파일SHA재검산/원본원장두읽기안정이다.

다음255는 실패시 안전한 경계·차이 수치를 보존하는 관측 개선을 별도 구현한다. 기존10m 허용치·격자·품질·예산을 완화하지 않으며 이번249에 없던 값을 복원하는 기능이 아니다. 252는 저장235근거·코드/고정249후속으로 선택정책을 조사한다. 완료 전 다음collector를 중복 시작하지 않는다.
