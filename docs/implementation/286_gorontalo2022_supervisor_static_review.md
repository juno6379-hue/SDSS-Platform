# 285 고론탈로2022 단일 수집 준비 코드 독립 검토

## 상태와 검토 범위

**IMPLEMENTED_UNVERIFIED — 준비 wrapper의 정적 검토**다. evidence/integration/deficit285-supervisor-root-20261018.py의 SHA256 `66fe2ed5b76ed53342ce7cb84617cc500a3bb54c03ece64e65b65249fdee80ed`를 확인하고, 최종279 wrapper와 전체 텍스트 차이 및 launch_and_wait 함수 AST를 대조했다. 이 검토는 운영 자료·원장·실제 요청·승인 JSON 조회, 수집·HTTP·native 감사·제품 시험 실행을 하지 않았다. 새 request와 approval은 아직 준비 전이라는 Root 인계에 따라 실제 지문 결속은 미검증이다. 284 로컬 계획의 실제 결과를 이 담당자가 다시 실행하거나 감사하지 않았다.

## 확인된 변경과 유지된 계약

279 대비 변경은 파일 접두사279→285, 승인 상태와 이전 감사 참조, 고론탈로 연도2025→2022, 해당 year·key·설명 변경으로 한정된다. 이전270의16개 native/6적격 완료 조건 대신,279의 고정 SHA 감사가 COMPLETED_ZERO_PATCH_NARROW_AUDIT이고 신규 파일·적격0, 기존행·pending 보존, 두 읽기 안정 및 lock 해제를 확인하는 조건으로 변경됐다. 이는0패치 작업을 성공 수집량으로 바꾸지 않는다. 다음 실제 수집의 현재 source/ledger 지문은 별도 approval과 요청 참조로 다시 결속한다.

launch_and_wait는279와 AST가 완전히 같다. 자식을 시작한 뒤 launch 기록이나 알림 출력이 예외를 내더라도 finally에서 p.wait를 실행하고 실제 자식 종료 코드를 반환한다. 이 검토에서 새 합성 자식을 실행하지 않았으며, 과거249의 예외경로 시험을 새 실행 근거로 재명명하지 않는다. terminal은 프로세스 종료 관측이며 정산·패치 품질 완료를 뜻하지 않는다.

핀 고정된6주 base config에서 id가 gorontalo인 AOI를 정확히1개 선택하고 새 id·province_id·bbox를 파생한다. 과거 잘못된 province_id 조회를 다시 사용하지 않는다. 현재 deficit_candidate_guard의 job config 파생과 동일한 방식으로2022년·6밴드·1024창·COG64MiB·후보5/검색20·유효80%/SCL65%·구름60·label_first·원본 crop 보존·재시도0·schema2 metadata marker를 설정하고, 최종 config SHA를 approval expected_config_sha256과 비교한다. 고정 split은 train이며 core의 FIXED_PROVINCE_SPLITS 기반 job과 일치해야 한다. 다른 주의 template 재사용은 없다.

최대1batch/16명목패치, 선택 후보1개 및 연도2022 조건, 신규 batch key의 원장 미존재, 모든 요청 참조 SHA와 canonical request SHA 검사를 유지한다. 원pending2행은235의 원형과 정확히 같고 합계136,314,880바이트여야 한다. 추가 예산4GiB, rate_limit 비활성 및 최소 예약 여유를 검사하며 예산을 추가하거나 pending을 환불하지 않는다. 자식 호출 직전 원본·원장 바이트 재확인을 유지한다.

실제 실행 명령은 기존 collect_deficit_guarded.py에 고정 request SHA와 --execute를 전달한다. wrapper가 fresh 전체 재고·support·scene·기하·품질·예산·정산 가드를 대체하지 않으며 기존 core가 lock 안에서 검사해야 한다. wrapper의 OS/lock 부재 검사는 사전 관측일 뿐 원자적 잠금이 아니다. 동시 실행 배타성은 core의 실제 잠금 획득에 의존한다. 동결 코드핀 목록의 모든 항목은 확인하지만 그 목록의 완전성 자체를 wrapper가 고정 집합으로 강제하지는 않으므로 Root 승인 준비 검토가 필요하다.

## 결론과 후속 조건

현재 고정 코드의 정적 범위에서 추가 실행 차단 결함은 발견하지 못했다. 실제 수집을 승인하거나 실행 성공을 확인한 결론은 아니다. Root가 새284 proposal·시작 source/ledger·base config·경계·이전 계획·runtime 검증·코드핀을 새 request/approval에 결속하고, 실제 OS/lock 및 예산을 다시 확인해야 한다. 기존2790패치 감사와273/275 게시1348 후보의 검증 범위는 그대로 보존한다.

실제285 실행 뒤에는 terminal·worker 결과·원장 실정산·lock 해제·OS 종료를 구분해야 한다. 새 패치가 있으면 Root 원본 고정과 별도 GO 후 해당 신규분만 단일 bounded native 감사를 수행한다. 새 패치0이면 배열 native0으로 종료·정산·원행·pending·실제 탈락 사유의 좁은 감사만 수행하며, SCL 실패·기하 실패·참조라벨 편중을 저장 근거 없이 추정하지 않는다. 나지 부족 해결·학습 준비·UI 반영을 미리 선언하지 않는다.

이 단위는 내부 실행 준비 코드 검토라 화면 계약을 바꾸지 않는다. 실제 성과가 생긴 뒤 API·UI와 이해자료 반영은 Root의 별도 소유 인계로 이어져야 한다.
