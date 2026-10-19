# 304 동자바2025 준비 supervisor 독립 정적 검토

## 결론과 고정판

상태는 **IMPLEMENTED_UNVERIFIED — 최종 준비판 정적 검토**다. 코드·동결 증거·최소diff·준비 요청/config/review 및302 완료 evidence만 읽어 추가 실행 차단 결함을 발견하지 못했다. 운영 원본·원장·profile/pointer·이미지 읽기,HTTP·실collector·새 시험·실QA 실행은0이다. 제품코드 수정0이며 이 문서만 작성한다. 실제 실행 승인은 Root가 별도 수행한다.

freeze evidence/integration/deficit304-preparation-freeze-20261018.json SHAa6a6a4b996a06c515d53aabadf871932b49e74e3408349d6ab28ccda9e12f9ab의7파일 byte/SHA를 모두 확인했다. supervisor SHAf8d74ec8597f111326db71e2f93ff09516dc3341a06c15cb9f7b30d7a45c26b1,prepared-review1d808ac33bfa301946bad09afdf3b14992a9ad059dab7ff691df51a8ff1cf041,doc304 b9e751453c9637c15a4351198e1103580dc3438d2e0afb91f1fc9ec136327f1d다. 최종297 원판과 archive를 보존하고304 최소diff를 읽었다. launch_and_wait는297과 AST가 완전히 같다. launch 기록/알림 예외가 나도 이미 생성한 자식은 finally에서 wait하며 종료를 버리지 않는다. 새 임시 자식을 실행한 시험은 아니다.

## 새 대상·요청·config

대상은 centers182-east_java-5141c64815b2,동자바2025/train 한곳,최대1batch/16명목패치다. 고론탈로 대상·key를 실수로 재사용하지 않는다. prepared request의 canonical SHA를 직접 계산해981abcd9b78b6eaa94dcb48a2f2bc62346ac939967076490b41c0c10e03f0987과 일치함을 확인했다. schema2 및 정확 DEFICIT_AOI_BBOX_CONTAINS_V1 정책이 config에도 포함된다.

base6주 config에서 aois[].id=='east_java' 정확히1개를 고르고 새 id/province_id/bbox를 덮어써 독립 예상 config를 파생한다.2025·6밴드 blue/green/red/nir/swir16/swir22·1024·COG64MiB·prior0·search20/SCL5·cloud60·sort_by_cloud·최종 유효.8/SCL예비.65·label_first·product metadata 검사·crop 보존·retry0 설정은 현재 guard391–406과 같다. 구 고론 bbox/template을 재사용하지 않는다. config semantic SHA를 직접 계산해31044c97e5dd1cf84648eec174975eacd9b5f8e1eacfcbf50e355bc0bb7d657a와 맞음을 확인했다. 별도 expected config 파일의 raw SHA와 구분하며 .load_config의 periods 변환을 사전 digest에 섞지 않는다.

요청은302 proposal e145e1fc2028bb00c26ceace8f814281fa8c48a9663ea18b1f31548d4eeec842,source사본9e63564c87647a144665bbb6bbe49b4a95d09bbd2c3bc0f3725861c54d5e7109,prior-merged60b748a50f05d847bb1807fa18a763d44e88007c672eb805a52e255d5e5e74fa 및 ledger574d382dd9da51ae56dc8fb135532f8f2e5c542b2c4cafdf73a6ee8dd9c6045f·기존 경계/base config를 결속한다.302 완료 evidence는 prior68 보존·새 동자바2025 후보2·원본원장 핀 안정·118header·원격0을 기록한다. 이 검토에서 실제 source 사본·prior 배열·proposal 본문을 다시 읽거나 full inventory를 실행하지 않았다. Root는 실제 참조 SHA를 실행 직전 재확인해야 한다.

## 직전 감사·게시 context와 운영 보호

직전297 감사 SHAe8c51e5c0afd86d4f0d89a58121103bad76ff3a5e4504079c41217ac08731096에 결속해 실제 native16/적격15,원행/history/pending 보존 및 두읽기 안정 조건을 요구한다.297 감사의 old1747행은 그 실행 전 prefix 범위이고,이번304의 시작 원본은1763행이라는 시점 차이를 유지한다. 고론2025 최소량 충족을 이번 동자바 수집 성공으로 세지 않는다.

별도 approval context 참조는 published1360 pointer996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0 및 source-profile configb9a2cd5cfe20bb570281882adcd1f47b4b81b0be4e69c0f0b91d606f0cd17f9e다. 이 두 핀은 현재 UI/게시 context의 일치 검사이며 fresh collector config·영상 기하·학습 승인 입력이 아니다. 기존1360 후보는9d source의 고정 QA 결과이고 현재9e와 stale 상태를 유지한다. 새 collector 뒤 source가 바뀌면 후속 후보 QA·게시·profile/API/UI 검증이 별도 필요하다.

원pending2행은235의 원형과 정확히 같고 예약합136,314,880바이트여야 한다. source/ledger 기대핀·추가 예산4GiB·rate_limit false·65MiB 이상 예약 여유·새 key 미등록과 자식 시작 직전 원바이트 보존을 검사한다. 원pending은 이미 사용에 포함되며 임의 환불·재차감하지 않는다. prepared-review의42 source_pins를 확인하는 구조지만 목록 완전성·실제 현재42핀·source/ledger/pending·OS/lock은 Root가 새 approval 전에 검산해야 한다. prepared-review는 아직 승인파일이 아니다.

core의 전역 O_EXCL lock 획득 후 fresh validate_request·full inventory·support/scene/geometry 검사를 유지한다. wrapper의 OS/lock 부재는 비원자 사전 관측이며 core 잠금을 대체하지 않는다. 기존2worker·공유2초 요청 간격·첫429 공유 중단·물리3000·COG64MiB+metadata1MiB·중앙 최종화/실정산·원본 분할/모델 보존은 변경되지 않는다. 예상 config 파생 성공은 fresh 전체 보호 통과나 원격 취득 성공을 뜻하지 않는다.

## 후속 실행과 보고 경계

현재 셀 부족1은 동자바2025의 시작 전 값이며 이번 수집이 이미 해결했다고 보고하지 않는다. Root만 정확한 새 request/config SHA·42코드핀·운영원본원장·pending·OS/lock 확인 뒤 단일 collector를 시작한다. 종료·실정산·OS/lock 해제와 원본 hold 뒤 신규가 있으면 별도 GO로 새 최대16개만 단1 bounded native 감사하고,0이면 native0의 좁은 감사로 전환한다. 기존297 native/290 QA 중복 실행은 없다. 마지막 셀 부족 해소 뒤 최종 고정 source QA는 별도 실행 근거로 확인하며 나지 부족·학습false·독립 정확도 미검증과 전체 미완료를 유지한다. 내부 준비 리뷰 자체는 UI 동작을 바꾸지 않으며 실제 완료 뒤 Root의 문서·이해자료·web_ui 인계를 따른다.
