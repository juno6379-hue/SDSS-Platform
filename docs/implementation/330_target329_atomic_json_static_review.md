# 329 고정 역할 atomic JSON 저장기 독립 정적 검토

## 판정과 검토 범위

상태는 **IMPLEMENTED_UNVERIFIED — 독립 정적 검토**,구현자의 시험 근거는 **TESTED_SYNTHETIC / ISOLATED_ONLY**다.기존 로컬 JSON 교체라는 범위에서 필수 수정 차단 결함은 발견하지 못했다.아래 결과표현·입력 선행검증·업무의미 한계를 후속 caller에 그대로 전달해야 한다.운영 source/ledger/pending·래스터 읽기,HTTP·새 시험·실QA·collector·제품편집·공유 적용은0이다.코드 검토를 실제 정산/170 연결 완료로 확대하지 않는다.

freeze329.json SHA1daf49fe9fd9053e707131c4d94fbed18b160d29f10403a1f22fecfdded2510c의15파일과 별도 document 참조의 byte/SHA를 확인했다.patch329-manifest71228fa052210bc30d8a136ac1165e76cfb2f8137b766c89266ff12e350d2bc8,runtime targeted_atomic_json.py11ea4b0956468045bdd27f7dd605f0d61508fd3846000dba001ef9b4a87aaa66,doc3294b75dbda713f632a650cc738e188b3c98caddd6ed2c8fc68983461b14f45f11b가 일치했다.격리 경로는 evidence/integration/target329-workspace-20261018 아래다.기존 profile/split I/O는 사본 의존성이고 새 runtime은 저장기1개다.현재main의 적용/부재는 Root가 별도로 확인하며 이 담당자는 운영파일에 접근하지 않았다.

## 역할·핀·동일 budget

역할은 config2MiB,ledger8MiB,source128MiB의 불변표이며 기존 rolecap보다 넓힐 수 없다.expected old SHA는 소문자64hex가 필수이고 exact profile marker를 요구한다.payload bytes를 먼저검증해 중복키/BOM/NUL/비유한/UTF8·depth/node·source scenes/history3000한도를 파일open 전에 검사한다.없는 destination을 새로 만드는 API가 아니다.

기존 profile scope와 io_transaction을 재진입해 같은 ContextVar Budget/RLock을 사용한다.중첩호출이16GiB를 새로 지급하지 않는다.기존파일 최초/교체직전 read/hash,temp hash,교체후 hash와 실제 write를 같은budget에 계상한다.실제 파일 읽기는 역할별 narrow cap과 동일fd 전후 fstat/논리identity검사를 재사용한다.메모리 JSON 직렬화·hash·stat/fsync 자체는 body I/O바이트가 아니며 메모리peak 상한을 보장하지 않는다.

## 임시파일·실부분쓰기·교체

부모 dev/inode와 regular file identity를 고정하고 symlink/reparse/hardlink를 거부한다.같은폴더의 deterministic temp를 exclusive/unbuffered 생성하며 이미 있는 temp를 지우지 않는다.청크마다 예산을 선확인하고 append offset과 누적size·regularfd를 검사한다.write 반환과 실제size차가 맞을 때만 실제 바이트를 계상한다.known partial은 실제량만 계상하고 실패하며,측정불명은 시도청크 전체를 보수계상해 중단·temp보존으로 닫는다.원destination overwrite의 size차를0바이트 쓰기로 잘못 계상하는 경로는 없다.

flush/fsync 후 temp SHA/owner/size와 기존파일 SHA/identity·부모identity를 다시 확인하고 교체후 읽을 예산도 선확인한다.os.replace는1회이며 반환뒤 새파일 실제 SHA를검산한다.협력 writer는 같은 exclusive temp로 경쟁한다.최종검사와replace 사이를 임의 외부writer에 대한 원자CAS로 잠그는 것은 아니며,dirfd고정·directory fsync·전원차단 영속·다중파일 트랜잭션은 보장하지 않는다.

## 실패·취소 결과의 정확한 해석

temp생성 이후 오류는 원예외클래스를 가능한 한 유지하고 commit outcome을 구분한다.NOT_ATTEMPTED는 replace전 실패,APPLIED는 os.replace가 정상반환한 뒤 후검실패,UNKNOWN은 replace호출이 예외를 내 적용여부를 확정하지 못한 상태다.예외가 실제replace 뒤 발생하면 committed=False여도 새내용이 이미 적용됐을 수 있다.따라서 UNKNOWN/False를 미적용으로 간주하거나 자동 rollback/retry하지 않는다.그보다 앞선 잘못된 계약/없는 파일/최초핀실패 등은 temp구간 밖이라 이 속성들이 없는 예외일 수도 있다.

**atomic_json_temporary_preserved=True는 실제 temp경로가 존재한다는 검증결과가 아니다.**코드는 owner가 있었고 committed=False이며 안전한 cleanup을 확인하지 못하면True를 붙인다.특히 실제replace 뒤 예외를 낸 UNKNOWN에서는 temp이름이 이미 destination으로 이동해 없어도True가 될 수 있다.이 플래그는 ‘안전한 삭제를 확인하지 못함/잔여물 가능성’으로 읽고 실제존재·현재identity를 Root가 별도 bounded 관측해야 한다.없는 temp를 보존했다고 확정하거나 플래그만으로삭제·정산복구를 진행하면 안 된다.향후 더명확한 tri-state/cleanup-confirmed 명칭은 개선가능하지만 현재 primary outcome UNKNOWN이 실제 적용불명을 보수적으로 보존하므로 이 격리단위의 권한우회로 판단하지 않는다.

cleanup은 부모·소유inode·known length/prefix SHA·예산여유가 모두 맞을 때만 우리temp를 지운다.외부temp·부모이동·측정불명·예산소진은 지우지 않는다.취소/KeyboardInterrupt도 성공으로 삼키지 않는다.이 보호가 모든 외부경쟁을 막거나 OS별복구를 자동완료하는 것은 아니다.

## value API의 선행검증 한계

replace_json_value는 role만 먼저검증하고 scope안에서 exact builtin tree를 detach·직렬화한 뒤 replace_json을 호출한다.marker와 expected pin 검증은 그 안에서 나중에 수행한다.따라서 잘못된 marker/pin도 최대4Mnodes·역할bytecap 내 메모리분리/직렬화 작업과 관련오류를 먼저 겪을 수 있다.불필요한 자원소비와 오류우선순위의 한계이며,marker/pin 오류가 항상 detach보다 먼저 나온다고 주장하면 안 된다.

파일open/실쓰기/replace 전에 marker/pin 검증을 통과해야 하고 scope도 기존budget을 재사용하므로 현재 이를 파일권한우회·I/O예산초기화로 판단하지 않는다.추후 비신뢰 대용량 caller를 받는다면 공통순수 계약검증을 detach 앞에 배치하는 개선과 해당오류우선순위 시험을 별도 검토할 수 있다.현재 검토에서 제품수정·추가재현은 하지 않았다.분리본은 이후 caller변경과 공유하지 않지만 원객체 원자snapshot/ABA방어/임시encoder할당의peakRSS는 보장하지 않는다.

## ledger와 원pending 의미 보존

role='ledger'는8MiB JSON object의 안전한 byte교체를 뜻하며 CollectionLedger의 업무스키마·예약상태·기존pending행 보존을 자동검증하지 않는다.유효JSON payload에서 pending을 빼는행위 자체를 이 genericwriter가 알아낼 수 없다.**caller는 별도로 기존pending2행/전액136,314,880바이트와 기존기록exact,새예약/실정산·429·원격예산·배타성·권한을검증해야 한다.**그 검증이 없는 ledger사용을 승인하지 않는다.이 단위에 운영ledger 연결이나 쓰기가 없다는 점과 분리해보고한다.

## 읽은 시험 근거와 인계

기존 최종집중30PASS/4.878초(wrapper6.819954),외부baseline 없는Temp의동일30PASS/4.437초(wrapper7.202484),skip0를 읽었다.고유60사례로 합산하지 않는다.실부분/unknown 계상·취소·temp/parent/destination교체·hardlink·동일pin경쟁·postcommit/unknown·예산·역할/JSON/구조·분리직렬화를 다룬다.최초확장29PASS1ERROR는 Windows 열린fd부모rename fixture시점 문제이며 원로그/수정전시험을보존하고 제품변경없이tempclose후검사hook으로수정했다.이번독립검토는 재시험0이며 실제128MiB rich/4M성능·RSS·운영native를확인하지않았다.

Root는 공유적용을한다면 baseline·정확새2파일·같은시험포장/문서와이한계를검토하고,후속caller정산계약·170/worker별scope 및 모든metadata writer연결을 별도구현해야 한다.UI/API 변경은 현재없고,기능완료를원pending정산완료·표적수집성공·나지/학습승인으로바꾸지 않는다.331후속문서와이해자료에 적용/검증실패분리·temporarycleanup미확인·value선행검증·callersemantic책임을그대로인계한다.
