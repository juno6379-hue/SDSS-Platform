# 235 — 현재 부족 주·연도의 새 위치 제안

상태: **VERIFIED_REAL — 로컬 위치 제안 / 수집·품질 승인 미완료**.

234 검토에서 남동술라웨시와 고론탈로의 기존 나지 후보가 모두 지원 영상과 겹쳤다. 별도로 일반 부족량을 보완할 위치를 현재 원본에서 다시 제안했다. 나지 밀집 여부를 검증한 제안은 아니다.

## 실제 실행과 결과

`centers235-prepare-root-20261018.py`가 기존 182 CLI를 한 번 호출했다. 2026-10-18 16:23:20 KST 종료, exit0, 124.875초. 기존 36개와 222의 4개 제안을 원배열 그대로 합쳐 **이전 40개 위치를 보존·제외**했다. 현재와 동일한 227 source 고정 사본을 재사용하여 중복 원본 사본은 만들지 않았다.

115개 header를 확인하고 새 위치 4개를 제안했다.

| 우선순서 | 주·연도 | 현재 적격 | 28개까지 부족 | 새 제안 |
|---|---|---:|---:|---:|
| 1 | 남동술라웨시 2024 | 22 | 6 | 2 |
| 2 | 고론탈로 2025 | 18 | 10 | 1 |
| 3 | 고론탈로 2022 | 24 | 4 | 1 |

동자바 2025의 부족 1개를 합치면 전체 부족량은 여전히 21개다. 제안 4개를 확보한 자료나 부족량 감소로 더하지 않는다. 원격 요청·수집·원본/원장 쓰기는 0이며 전체 pending/support 소비 검산과 실제 영상 품질검사는 수행하지 않았다.

## 출처·사용법·차단 조건

원본 SHA `9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987`, 원장 SHA `61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7`를 포함한 7개 입력·코드 지문이 전후 같았다. 새 proposal은 `data/centers235-fresh-20261018/proposal.json`, SHA `87e6f5f157d940e00c624f46821d30329135ef9182a0acb1db248bfb59a712da`다.

근거는 `evidence/integration/centers235-{preflight,result,cli}-root-20261018` 접두사 파일이다. `centers235-request-prepare-root-20261018.py`는 첫 남동 2024 위치의 최대 1batch·16물리 요청만 준비하며 실행하지 않는다. 원본 JSON 크기 보호의 230 최종 검토·적용 검증 전 실제 수집은 차단 상태다. 실행 전에 최신 source/ledger/code pin·실제 프로세스·단일 잠금·전체 지원과 겹침을 다시 검증한다.

기존 4GiB 총예산·2worker·공유 2초·첫 429 중단·물리 3000·64MiB COG+1MiB metadata/batch·고정 split·미정산 2건 전액은 유지한다. 화면 재고나 게시 후보를 바꿀 신규 실자료가 없어 UI 데이터 수치는 갱신하지 않는다. 별도 이해자료에 제안과 확보량의 차이를 설명한다.

## 고정234 지원 목록의 수치 사전계산

16:54:40 KST Root는 234가 실제 검산한 1,292개 asset의 CRS/bounds만 재사용해 새235 네 위치를 수치 대조했다. 199와 같은 native 중심±5,120m 도형을 쓰며 네 위치 모두 그 고정 asset 목록과 비겹침이었다. 20.141초/새 inventory scan0/raster 읽기0/HTTP0/수집0이고, source·원장·proposal·234report·199·liveguard 지문은 같았다.

`centers235-cached234-support-precheck-root-20261018.json`은 **고정 목록에 대한 수치 사전계산**이다. 새 support 파일이나 변경을 다시 검산한 증거가 아니며, 실행 전200의 잠금 안 fresh 전체검산을 대체하지 않는다. 실행 요청의 선별 참고이며 품질·독립성·나지 확보 승인이 아니다.

## 보호 반영 후 실제 coordinator 시작

237 제품·242 시험 배치 보완과243 실제API·244 브라우저 확인 뒤 Root가 최대1batch·16물리를 승인했다. `deficit235-reviewed-code-pins-root-20261018.json`은 현재 코드30개 지문, 예산증가0, 기존pending전액 보존, fresh200 잠금 안 검산 필요를 고정한다. 과거223의 collector dependency 중 변경된 것은 검증된 runtime18 및232 소유 변경뿐인지 대조했다.

`deficit235-supervisor-root-20261018.py`를 실제 실행했다. exec session34361, supervisor28276/collector16868이다.17:03:07 관측은 실행 프로세스·global execution lock 존재, stdout 비어 있음·terminal 미확인으로 **전검사 시작만 확인**했다. worker/HTTP/새패치·적격·나지 성과는 아직 확정하지 않았다.

launch/terminal/stdout/stderr는 `evidence/integration/deficit235-` 접두사다. 종료·실정산·잠금해제·OS종료와 Root source 고정 확인 뒤239 담당만 신규 최대16개를 단1회 bounded 감사한다. 감사 중 새 collector를 시작하지 않는다. 신규patch0이면 같은후보QA를 반복하지 않고, 신규자료가 있으면238 준비계약에 따라 별도 고정QA를 한다. 실행·종료 상태와 수집 성공을 혼동하지 않는다.

## 17:13 실제 종료 후 관측

235 exit0/263.407초, worker1·patch0·eligible0·liveB02false·429false. 실제 정산 1,414,466B이고 잔여 1,895,530,489B, 기존 pending2 전액 136,314,880B는 보존됐다. Root는 source를 고정하고239에 새SCL/원행/history/정산 좁은 감사만 GO했다. native raster/기존후보QA 반복0이며 원인 최종 감사는 대기다. 등록행1715는 그대로이나 현재source SHA는4f8fcaff71868539aff16b3c351992696a6464b9cb229a5ff0f243778b7cd3e8로 달라졌다. profile 설정·게시후보의 시점 불일치를 자동 일치 처리하지 않는다.
