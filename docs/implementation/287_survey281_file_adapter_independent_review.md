# 287 — 281 로컬 STAC 파일 어댑터 독립 정적 검토

판정: **STATIC_REVIEW_COMPLETED / 공유 검증 전 필수 제품 수정 결함 미발견**. 이는 main 적용 승인·운영 수집 승인이나 실제 공급자 호환성 PASS가 아니다. **실공급자 호환성·실제 Windows junction·전체 coordinator 연결은 미검증**, 226/246의 엄격 시각 조건에 어긋나는 자료는 계속 BLOCKED다.

검토 대상은 격리 `evidence/integration/survey281-workspace-20261018`의 최종 불변판이다. 이 담당은 새 시험·어댑터 호출·운영 source/원장/model/래스터·HTTP/native QA를 실행하지 않았다. 코드·격리 증거·로그의 읽기와 지문 대조만 수행했다. Root의285 실행과 별개이며 공유 제품 수정0이다. 소유 산출은 이 문서와 `evidence/integration/survey287-static-review-20261018.json`뿐이다.

## 불변판과 적용 범위

| 입력 | SHA256 |
|---|---|
| freeze281-20261018.json | `42bae67521fbd160506c89cf45aac255567260e1c2203d22c530fd9b55a271f4` |
| patch-manifest281.json | `ab164cec389ed53dc0949bb37661395170a8e05701667dd45faed479a7fd4353` |
| 신규 runtime,6746B | `542c418f2fb7ed47c4e03a9fa9fad73bc2c4effcc5f95aaac27209792dac468c` |
| 신규 시험,10001B | `57eb43e36dc44d0bebc2f64040bef28daedf3ffe3179bd023407d379bf60e31d` |
| doc281,10944B | `c98e6e82bae39912ccb9893de7515541f7172908091ad860873aa571215ca6a4` |

freeze에 열거된15파일을 실제 크기/SHA로 재검산해 불일치0을 확인했다. baseline8개는 main과 격리 사본 모두 기록 지문과 같았다. 신규 main 대상 `backend/app/data/bare_survey_stac_file.py`와 `tests/test_bare_survey_stac_file281.py`는 검토 시 미존재였다. 적용 검토 대상은 신규2개뿐이며 baseline8개·로그·fixture를 새 제품으로 덮어쓸 필요가 없다. 별도 baseline 폴더가 있다는 주장을 하지 않으며 여기서 baseline은 원바이트 main/격리 사본과 입력 manifest를 뜻한다.

핵심 부모226 `e035cc1a…f8dd60`와246 `16a1d868…e788b4a`도 그대로였다. 이번 정적 검토는 부모를 고치거나 엄격한 선언 조건을 완화하는 근거를 제공하지 않는다.

## 직접 코드 근거

다음 line은 격리판 `backend/app/data/bare_survey_stac_file.py`의 고정 runtime SHA 기준이다.

| 위치 | 확인 내용 | 판정 범위 |
|---|---|---|
| 63–81 | 기존 request 검증 후 분리된 plan·primitive asset 사본 사용; 최대 read는 exact int0..1MiB | bool/상향 거부, 원입력 alias 보관 없음 |
| 82–91 | 절대 Path·canonical data 상대 ref, 다른 ref와 casefold alias 거부, 부모 및 resolve 검산 | 다른 ref를 실제 열거나 그 SHA를 확인하지 않음 |
| 28–45,92–96 | dev/inode/mode/size/mtime/ctime/nlink, 모든 부모의 symlink/reparse·directory, 파일 regular/nlink1·크기2B..1MiB와 호출 예산 | payload os.open 전에 거부 |
| 97–110 | O_RDONLY/O_BINARY/지원 시 O_NOFOLLOW, 단일 fd, 최초fstat identity, 최대64KiB씩 처음 크기만 읽기, 후fstat, finally close | payload 두 번째 open·추가 EOF read 없음 |
| 103–107,132–135 | 반환받은 bytes만 누적; 실패에도 observed를 고정 오류에 전달 | 실제 부분 read를0 또는 환불로 바꾸지 않음 |
| 111–118 | close 뒤 logical path/부모 재검산, raw SHA 일치 뒤 기존246 호출 | SHA 불일치면 pure binding 호출 없음 |
| 119–121 | pure binding 뒤 파일·부모 identity 재확인 | 검증 중 변화를 성공으로 반환하지 않음 |
| 49–60,122–131 | frozen 결과·canonical JSON/to_dict 새 사본·명시 false gate | 함수 산출물의 관측 범위만 보장 |

symlink/reparse 방어는 lstat의 mode/Windows attribute0x400와 path resolve를 병행한다. hardlink는 st_nlink!=1이면 보수적으로 거부한다. 디렉터리 identity에 size/mtime/ctime도 들어가므로 무관한 부모 변경에도 실패할 수 있다. 불필요한 통과 예외나 자동 재시도는 없다.

초기 before size를 넘겨 읽지 않고 post-fstat로 성장을 탐지한다. maximum_read_bytes가 처음 크기보다 작으면 payload open/read0이다. cap+1 EOF 확인을 하지 않아 읽기 한도를 늘리지 않는다. close나 stat가 실패하면 고정 INPUT_OR_IO_INVALID로 닫히며 관측 bytes를 유지한다. `actual_read_bytes`는 Python으로 반환된 payload 양이고 디스크 물리 I/O·stat 비용·원격 전송량이 아니다.

## 보장하지 않는 경계

이 함수는 Windows 커널 수준의 부모 디렉터리를 고정하거나 파일시스템 전체 transaction을 만들지 않는다. path/부모 검사 사이 변경됐다가 복원되는 모든 적대적 경합·검사 후 caller 소비까지의 변경을 검출한다는 보장은 없다. doc281도 이를 명시한다. 최종 reparse 검사는 그 시점의 관측과 identity 비교이며 지속적인 경로 권한을 부여하는 토큰이 아니다. 실제 coordinator의 단일 lock·고정 입력·실행 소유권·변경 검산은 여전히 필요하다.

다른 manifest/ledger/config/seed ref는 열지 않는다. 따라서 lexical alias 거부와 선택 STAC 파일의 hardlink 거부를 넘어, 다른 ref의 실제 파일 정체성·내용 SHA·동일 파일로 향하는 symlink 관계를 검증했다고 말할 수 없다. 결과 ledger_verified=false와 일관된 제한이다.

maximum_read_bytes는 **독립 호출 하나**의 allowance다. 병렬2호출의 합계를1MiB로 제한하거나 global budget/원격 예약·정산에 연결하지 않는다. parts join·UTF8 decode·JSON tree를 포함한 전체 RAM/RSS를1MiB로 제한하는 것도 아니다. inherited246의 1MiB/depth32/node25000 제한은 그대로이며 node 검사는 decode 뒤다. manifest용128MiB/16GiB profile이나 실제 원격1MiB+COG64MiB 예산과 혼동하지 않는다.

## 부모 계약과 false gate

226의 `_scene`135–152는 원문 ID의 관측시각과 선언 datetime을 정확히 비교한다.246은149행에서 raw STAC datetime과 선언 datetime의 정확 시각 일치를 요구한다. adapter116행은 그 불변246을 호출하고 예외를 고정 METADATA_BINDING_INVALID로 바꿀 뿐이다. `.024000Z`를 초 단위 선언에 맞춰 반올림/삭제하지 않는다. 현재 PC 자료에서 관측된 그런 패턴은 요청 단계 또는 binding 단계에서 **여전히 BLOCKED일 수 있으며 실제 호환성 PASS는 아니다**. baseline 누락 ID를 수정하거나 제품 baseline을 추정하지도 않는다.

어댑터는 local_file_pin_and_identity_verified=true와 내부 metadata_consistency_verified=true만 관측한다. outer source_authenticity/remote_asset/raster_header/ledger/quality/training/execution/collection/registry/target_consumer는 false이며, inner246의 독립정답·scientific accuracy gate도 false다. 단순 dataclass 직접 생성은 검증 호출이 아니고 결과 객체 자체도 실행 capability가 아니다. app/backend import의 canonical 결과가 같다는 시험은 예외 클래스의 Python identity가 동일하거나 두 호출이 공유 budget이라는 뜻이 아니다.

## 시험 증거의 정확한 해석

검토자가 읽은 final281.log는61 PASS/3.963초/skip0이며 신규16+기존226/24645의 관련 합성 실행이다. 이 담당은 재실행하지 않았다. 단일fd/정확bytes·immutable사본, cap/예산 before-open, 정확1MiB whitespace, hash 실패 시 binding0, ref alias, 실제 hardlink, 모의 reparse·부모교체, 성장/close후 실제 교체, 부분 read/짧은 EOF, 엄격 시각/제품, validator 중 변경, app/backend 결과·병렬 독립 allowance를 확인하는 assertion을 읽었다.

focused281.log의 최초16개 중1FAIL/1.714초도 원판 SHA로 보존돼 있다. 열린 fd 교체를 Windows가 먼저 OSError로 막아 INPUT_OR_IO_INVALID가 되었고 fixture가 원했던 REPLACED 분기에 도달하지 못한 실패다. 최종 시험은 실제 close 직후 os.replace하도록 고쳐 후경로 identity 검사를 검사한다. runtime을 완화하거나 기대 코드를 generic으로 바꿔 숨긴 수정은 아니다. 최초/최종 시험 수를 합산하지 않는다.

실제 junction 생성·악의적 실시간 부모교체·모든 플랫폼의 O_NOFOLLOW·실공급자 STAC·최대 RSS·원격 자산 인증/영상 품질/실학습은 검증하지 않았다. 부모 교체 시험은 반환 identity를 모의 변경하는 시험이지 실제 디렉터리 경합 실험이 아니다. 이 한계는 코드 오류 발견과 구분한다.

## 결론과 인계

고정판에 대해 **필수 제품 수정 결함은 발견하지 않았다**. Root가 별도 독립 적용 검산을 할 수 있는 상태라는 정적 의견이며 신규2파일 main 적용을 이 담당이 승인·수행한 것은 아니다. 운영 source/원장/model·HTTP/native·새 시험·공유 편집은0이다. Root285의 원본/코드핀 고정과도 충돌하지 않는다.

실제 SURVEY coordinator와 global lock/누적 예산·실정산·173/175 명시 lineage·실라벨/native support 검사는 여전히 후속이다. 파일 pin 일치를 실제 나지 확보·독립정답·학습 준비·원격 진위로 확대하지 않는다. 이 순수 내부 입력 어댑터는 API/UI를 바꾸지 않으며 화면/서버 적용을 확인한 작업도 아니다. Root의 적용 여부 결정 뒤 이해 담당이 이 범위와 미완료를 쉬운 설명·발표·FAQ·INDEX/이력에 반영해야 한다.
