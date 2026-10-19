# 325 명시 source profile 로컬 사전검사 독립 정적 검토

## 결론과 고정판

상태는 **IMPLEMENTED_UNVERIFIED — 독립 정적 검토**,구현자의 시험 근거는 **TESTED_SYNTHETIC / ISOLATED_ONLY**다.격리325의4개 runtime·최소diff·시험/로그·문서를 읽었고 현재 로컬 사전검사 범위에서 실행 전 필수 수정 결함을 발견하지 못했다.공유 적용·운영 source/ledger/label 읽기·HTTP·실fullnative·새 시험·코드편집은0이다.main source64MiB 집행 차단과170 worker 전체 연결은 해결됐다고 보고하지 않는다.

freeze325.json SHAc908ea546e8029dfc669fd716a34def18eb932e612922e33bf6381603cf6ee4e의20파일 byte/SHA가 모두 일치했다.patch325-manifest9d49a9f19dac1c861974716eb89a5ba7f68d26016a76ddeb8a0a348307955910,doc3259d5c2bcbf0d31aa144d3589c829835b5ca3f856746eae0947edb7400e70a53d4를 확인했다.runtime union은profile73c9ba94cda1722ae87e7729ecd655ba5e9584fcb735c8c1f0e06734f8357d01,1750577de883385f71d2007d2d2a043d683a8a78bf13b98f984e310546997aa2d2c,319pure8e347589d802d22f89354b176d81da9ebdde27607986355ce3212ac4981493d9,newsourceIOc4854dc5887f83d1536e9741bf6f5f3cafc283cc704662c102e8a22bf8c78f6f다.경로는 evidence/integration/target325-workspace-20261018 아래다.

## 정확한 opt-in과 기존 경로 보존

새 prepare_explicit_targeted_bare_jobs만 sourceIO를 호출한다.먼저319 validate_request_v3가 정확 outerv3/planv2·양쪽manifest marker·3GiB support marker를 검증하고 분리본을 만든다.공통 profile descriptor/MARKER와 같음을 확인한 다음에야 scope·root/path/stat/open으로 간다.원v3 SHA는 유지하고 내부v2 envelope를 과거 실행 승인으로 취급하지 않는다.불변/사본·UTF8/형식 계약은319와 같은 원판이다.

기존 prepare_targeted_bare_jobs는 _metadata_reader를 전달하지 않아 원래 _pinned/_json의v1·source64MiB 경로를 유지한다.ambient128 scope가 있어도 이 legacy 진입점의 source64를 자동 승격하지 않는다.default profile API/maximum_bytes=None도 기존 역할상한을 유지한다.새175 내부의 planv2 marker 허용은 reader가 있는 명시 분기만이다.개별 marker가 맞는다는 이유로 기존170 CLI·worker를 새경로로 자동 전환하지 않는다.

## 좁은 cap과 같은 fd의 실제 바이트

profile의 maximum_bytes는 선택한 원래 rolecap 이하의 정확한 양수정수만 허용하고 bool·상향·오염값은 path stat/open 전에 거부한다.ledger는 status_report16MiB 역할에8MiB를, lineage는 readiness16MiB 역할에8MiB를 좁혀 전달한다.source128MiB,proposal/boundary2MiB는 고정 table에서 온다.파일명이나 현재size로 역할을 추정하지 않는다.

좁힌 cap은 사전 파일크기 검사뿐 아니라 bounded_json_digest의 실제read·capture·SHA와 read_metadata의 parser treecap까지 전달된다.동일file descriptor의 fstat을 읽기 전후 검사하고,실제 읽은 길이를 charge·hash하며,논리경로의 최종 identity도 맞춰야 한다.8MiB stat만 검사하고 내부16MiB reader를 쓰는 빈틈을 발견하지 못했다.원래 경로·reparse/symlink 검사와 rolecap을 유지한다.이것은 순차 파일 관측이며 파일시스템 전역의 원자 snapshot은 아니다.

source는 dict/scenes list 형식과 scenes+historical_noneligible≤3000,depth32,node4M,SHA를 기존 구조검사로 확인한다.실라벨/image/support는 원래64MiB pinned GTiff·175 공간검산 경로이며128 sourceJSON으로 분류하지 않는다.ledgerJSON을 읽었다는 사실만으로 reservation/pending/집행 안전성이 검증되는 것은 아니다.그 책임은 후속 coordinator/fresh inventory에 남는다.

## 캐시·동일 operation·실패 전파

reader cache는 path/role별 최초 identity·expectedSHA·파싱값을 보관한다.cache hit은 같은 identity와 요청핀을 확인하고 실제 파일재읽기0이다.마지막 recheck에서 첫 identity와 다시 대조하고 actual bounded SHA·후 identity를 확인한다.같은내용 교체나변조를 성공으로 돌리지 않는다.캐시 반환값은 내부175가 읽는 trusted 객체이며 전역 불변 token이나 실행 승인물이 아니다.

scope는 이미 active budget이 있으면 재사용해 중첩호출이16GiB를 새로 초기화하지 않는다.프로파일 MARKER/descriptor가 같은 실제 구현과 한 ContextVar operation에서 JSONread/hash·마지막 재핀을 누적한다.반환 dictionary의 나중 직렬화나170 worker metadata writer 전체는 이 범위에 포함되지 않는다.

ProfileResourceError는 명시 _metadata_reader 경로에서 기존175의 일반ValueError/Exception 처리에 삼켜지지 않고 상위로 재전파한다.legacy경로는 기존 blocked 결과/오류규칙을 보존한다.성공 로컬결과에도 execution_supported/coordinator_connected/training_ready=false이며 LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED 및 EXECUTION_GUARDS_NOT_CONNECTED를 유지한다.170 lock·정산·원격품질을 통과했다는 뜻이 아니다.

## 읽은 합성시험 근거와 한계

기존 focused63PASS/19.563초(wrapper22.031),portable65PASS/46.256초(wrapper51.766),skip0·실패0 로그를 읽었다.현재 담당자는 재시험0이다.기존175와319 회귀 및 새로운 좁은cap/default대조·8/128MiB 사전open차단·실read중growth/동일내용교체·핀불일치·3000+history/depth/node·캐시0read·중첩budget·resourceerror전파·legacy ambient64 보존을 시험한 범위다.원판SHA fixture와 필요한 코드/시험만 배치한 외부baseline 없는Temp 검증이며 GIS/Python 설치라이브러리까지 불필요하다는 주장은 아니다.

유효64~128MiB 합성source67112960바이트(64MiB+4096)의 전체 명시로컬 사전검사는portable에서 단1회19.5초 수행됐다.JSONread134227800/write0/합134227800바이트가16GiB 미만이었다.내용은 작은 합성 JSON 뒤 whitespace를 붙인 문서로 실제 rich 운영128MiB의 성능·대표성 보장은 아니다.실4M값을 가진 별도 JSON의 node상한 초과 검사도 같은portable 실행에 포함됐다.새로운 대량시험을 이 검토가 실행하지 않았다.

Windows PeakWorkingSet 표본209129472바이트와 node시험 중 별도442609664바이트 표본은 시점/프로세스 관측값이며 전체시험 최종peak·강제 메모리상한·Linux RSS가 아니다.상한에 가까운문서를 한 번 성공시켰다는 이유로 더큰운영자료/지원inventory 전체를 자동허용하지 않는다.

## 적용과 후속 경계

현재는 격리코드이며 Root의 baseline/union4·시험포장·공유적용 검토가 별도 필요하다.이후170 CLI/lock안fresh source/ledger/fullsupport/pending검산·shared scene/window registry·worker ContextVar·모든metadata writer/실정산에 같은계약을 연결하고 기존legacy동작을 검증해야 한다.이 단위는 실target256 source64 집행차단 해결을 선언하지 않는다.원격4GiB·2worker·공유2초·첫429·물리3000·COG64+metadata1MiB·최종80/95품질·원pending·모델/학습 gate는 그대로다.

내부격리 로컬기능이므로 이 단위의 API/UI 변경과 실브라우저는 없다.실제운영 연결 후에만 사용자화면·이해자료에 검증된 범위로 반영하고,현재323 current나지 검토 게시를325 실집행 성공으로 재명명하지 않는다.전체 개발·나지 준비·독립정확도·학습 승인은 여전히 미완료다.
