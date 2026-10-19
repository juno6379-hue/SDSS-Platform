# 10:25 보고 주기 독립 통합 감사

관측 기준: 2026-10-18 10:26–10:29 KST. 기존 개발 채팅은 active이며 수집 coordinator·후보 게시·현황 UI를 소유한다. 이번 Root와 별도 data/UI 검토는 운영 소스·원장·수집을 중복 변경하지 않았다.

## 새로 확정된 결과

동자바2025 g01/g02는 장부 정산2건·worker 종료2건이나 source scene은 모두 실패했다. 오류는 ‘AOI 중심점이 COG 범위 밖입니다’이며 신규 물리/적격 증가0이다. 현재1432물리/1141적격/291부적격,1200목표 잔여59, 셀당28개 기준 주×연도 부족합132다. 이번 계상1325635B·잔여2296542772B, 기존 pending2/136314880B와 기존행 보존,429비활성·lock없음을 독립 확인했다. round2-final의 stdout-empty 설명은 과거 문구이며 실제 stdout에는 시작2/종료2행이 있다. 원문 증거는 고치지 않았다.

새 고정 후보 실제 QA가10:26:57 완료됐다. 원본1400행/1122적격에서 검증·평가 split의 같은 source scene 중복16행을 후보에서 제외해1384행/1106적격(train639/val217/test250)이다. source QA230.906초·candidate QA239.188초, 후보 차단4건·학습false다. 후속 검증은4335 파일 기록의 불일치0이며 Root도 summary에 명시된9개 출력 bytes/SHA를 독립 재계산해 모두 일치했다. Root가 실제 raster QA를 중복 실행한 것은 아니다. 이 고정 후보는 현재1432행 원본과 sourceSHA가 다르다.

10:28:04 실제 Vite 경유 GET `/api/data/collection-status`는 current1141과 candidate_quality.available=false를 반환했다. QA 완료와 API/브라우저 게시 완료를 구분해야 한다. 최초 잘못된 `/api/collection-status` 탐색의404는 정확한 소스 경로 확인 후 바로잡았으며 서버 결함으로 집계하지 않는다.

## 재발 방지 후속 — 기존 개발 담당 소유

SCL만 통과한 후보가 선택된 뒤, label_first 경로의 Esri 참조라벨 읽기가 B02보다 먼저 실행된다. 빈 source_crops/labelpreview와 카탈로그 B02 범위를 대조하면 early label 읽기 실패 가능성이 높다. 그러나 실제 실패 Esri header가 없어 확정 인과는 아니다. 실제 좌표 범위 guard는 잘못된 입력을 거부한 것이다.157의 B02 geometry guard 미연결 자체를 이번 오류의 확정 원인으로 삼지 않는다.

선택 후보별 영상과 동년 참조라벨의 실제 CRS/affine/shape 및 전체 요청창 포함을 검사하고, 실패 자산 역할과 검사 단계를 남겨야 한다. 후보 전환은 명시적·제한적으로 하고429/예산/동일scene split보호를 유지해야 한다. 독립 감사에는 scene경계·SCL성공/라벨범위밖·센터안/전체창밖·메타데이터/실제격자불일치·제한후보전환/429 시험 제안을 남겼다. 기존 담당이 같은 원인을 조사 중이므로 다른 collector를 만들거나 재시작하지 않았다.

후보 UI는 명시 latest-candidate receipt의 source/candidate/QA 지문을 검증한 뒤 별도 상자에 원본1400→후보1384→적격1106·제외16·차단4를 표시해야 한다. 현재 재고/나지 표를 덮어쓰지 않고, 현재 manifest와 sourceSHA가 다르면 후속 수집분 미포함을 명시한다. API 조회시각·receipt기록시각·QA완료시각도 구분한다. 최신 mtime 파일을 임의 선택하거나 문서 숫자를 frontend에 고정하지 않는다.

## 인계 및 상태

근거: `heartbeat-1025-data-audit-20261018.json`, `heartbeat-1025-root-status-20261018.py/json`, `priority-ml-20261018-summary.json`, `priority-ml-20261018-final-verifier.log`. 쉬운 해설·대본·FAQ: `docs/understanding/10min_20261018_1025.md`.

10:27 OS 관측에서 API PID8564·Vite34484는 실행 중이며 collector/ML QA process는 종료됐다. 이는 계속 개발 중인 채팅/검토 agent와 별개다. 보고 예약geoai-2는ACTIVE/10분이다. 전체개발·나지 보완·학습준비는 미완료다.

### 10:29:39 재관측 — 별도 round3 실행 중

기존 담당이10:27:58에 다음 미예약 두 작업을 시작한 것을 뒤이어 확인했다. wrapper PID33868와 단일collector child5892가 실제 실행 중이다. `priority-collection-round3-launch-20261018.json`의 상태는 STARTED_NOT_COMPLETED이며 최대2batch·동일 잔여예산·기존pending보존이다. 이는 종료된 round2의 재실행이 아니며 새 종료성과를 계상하지 않았다. 위10:27의 collector없음 관측을 현재 상태로 확대하지 않는다. ML QA process는 종료이며 API/Vite는 계속 실행 중이다.
