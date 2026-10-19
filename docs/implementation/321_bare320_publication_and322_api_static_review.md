# 321 — 320 나지 검토 게시·322 API 준비 독립 정적검토

판정: **고정 코드 범위에서 실행 전 필수 수정 발견 없음 / 실제 게시·API·브라우저 미검증**. 이번 검토는320/322 코드·freeze/doc/archive/최소diff와관련reader/profile코드만읽었다. 운영source/ledger/pointer/profile/316원report/result·라벨·모델 읽기0, 시험/import/승계/HTTP/native/공유코드편집0이다.319격리코드는동시에수정하지않았다.

## 고정 지문과 범위

320 runner `b88345551a7e3dc817418965752c4ba62c0e5612f287d97981dffacf4968f957`/8548B, freeze `21a844646c2158a1cdd5940132f11fd7480eb140af3e49510b893d4b94d49108`;322 runner `8a8344dfb7d27a9f82cfc16f1b541c6f8a498884e282b3d518ac4de0b24ffd6b`/4672B, freeze `27f3f79b022048b4ff2f107df9fb7caa6850f5895eb1115fabf3698025adf8f5`를대조했다. 두freeze 참조6파일의bytes/SHA가모두일치했다.320의234원판archive도e71591…927f0 지문으로고정됐다. 단순번호교체만이아니라unboundedread를명시profile로바꾼강화diff다.

실제316report `16b923a42c28d89e26b2003c24ab4ca46e9bb9b28e95f2d8a1e8d3f25b1f9093`, result `aaa97f9b64fca9e6a11d8fe9f07a4e649c224ed69fbae599605d28f49490887e`는Root고정기대값으로코드에있다. 이번검토자가실운영결과파일을다시읽어인증한것은아니다. Root가실행전정확지문/실상태를확인해야한다.

## 320 입력 검증·BLOCKED 의미

`bare320-publish-root-20261018.py:26–49`에서단일scope(NAME) 안 exactGO키/값·approved is True·절대evidence승인경로를검증한다. fixedresult/report를역할별expectedpin으로읽고exit0/완료status·한번inventoryscan·세verifiedflag true·4입력stabletrue를요구한다.

result.inventory_status BLOCKED/issue EXISTING_SUPPORT_OVERLAP와 inventory_verified/pending_footprints_verified/source_pins_verified true는서로다른의미다. 전자는첫target의support겹침관측,후자는전체자산/pending/핀검산완료다. 세flag가false인불완전재고를승인하지않는다. report50/35겹침·15clear/56상호겹침쌍·false실행/품질/과학검증·native라벨재검산·source/ledger/ui_summarysource핀을확인하고실취득/원격품질로변환하지않는다. clear15가서로독립15곳이라는검사는하지않으며56쌍을publication에도남긴다.

소스128MiB/status_report16MiB/local_plan2MiB/pointer64KiB역할을고정하고동일누적16GiB scope 안입력read·hash·파일write/stdout을계상한다. source파일은digest검산이며전체nativeQA를다시하지않는다. read_metadata 내부는cap-before-open/실read계상/identity/SHA를결속한다. 실제source1779행이나report원문shape를본검토에서읽지않았으므로실행시검증통과는미확정이다.

## 320 원판 보존과 교체 경계

52–59행은current source0c/ledgerd5/candidate1391 pointer25d7 및lock부재·oldbarepointer1018와참조reportc936를대조한다. oldreport는대체하지않는다. 새DATAreport는316원바이트707005B를exclusive복사해REPORT핀을확인하고oldpointer원바이트archive/새receipt/tmp/publication미존재를요구한다.

61–72행은reportcopy→oldpointerarchive→새receipt→tmp기록/flush/fsync→tmp/oldpointer·current3핀·원report/DATAcopyreport재핀·lock부재→os.replace순서다. scope내boundedwriter를사용하며상한밖fallback·기존파일덮어쓰기·원본/원장/후보pointer갱신은없다. report입력read는expectedpin을받고복사바이트도같은raw다. 교체직전의검산은순차대조이며원자적다중파일snapshot을보장하지않는다.

73–79행후reader `collection_priority_status.bare_target_review`는active profile에서pointer64KiB/report evidence2MiB를읽고report원문bytes의SHA를receipt참조와즉시대조한다. sourcecurrent/50개/REPORT핀/6주35·15·localinvalid0/실행·품질·과학false를요구하고pointer=receipt핀·old/newreport·currentsource/ledger/candidate핀을다시대조한다. 기존reader함수를사용하므로임의latestglob를선택하지않는다.

publication status는 `LOCAL_ONLY_REVIEW_PUBLISHED_READER_VERIFIED`, report_sha256/pointer_sha256/source_sha256/ledger_sha256/candidate_pointer_sha256/manifest_profile/view 등을기록한다. 이field들은322의소비이름과일치한다. old50제안을current309source에서다시검토했다는provenance가포함돼새50확보로오해하지않게한다.

## 322 정확 publication·5운영핀·단1 API

`bare322-api-root-20261018.py:14–23`은전달된실publication SHA로320출력을읽고status/정확profilemarker/source0c/ledgerd5/candidate25d7·remote0/수집false를확인한다. current source/ledger/candidate/barepointer/profilee63f **5개핀**을각각역할별digest로검사하고barepointer는publication의새pointer지문과같아야한다. profile은수정하지않는다. 잠금부재/새response/checks부재를요구한다.

25–32행은localhost8002·Origin5174/timeout150초/응답최대2MiB+1의단1GET이며retry/restart가없다. 응답원문은새localplan증거에보존한다. HTTP응답읽기는2MiB전송상한,로컬JSON쓰기·앞뒤운영파일읽기는profile누적budget이라는범위를구분하며이를원격위성COG예산검증으로해석하지않는다. runtimeAPI의read-only성공과운영file핀보존을검사하되실브라우저는포함하지않는다.

11checks는raw1407/gap0·candidate1391/current/3차단false·bare50/current/reportpin/6주35+15·나지실행/품질/과학false·잔여1799757940/oldpending136314880·운영5핀보존을확인한다. 후보1391 source핀은별도고정publication과currentpins에결속돼있고bareREPORT핀도동일publication에서받는다. result에재고/예산/나지검토관측시각을분리하며GET시간을SLA나병목진단으로확대하지않는다. 본검토는실응답field가현재이값이라는검증이아니다.

## 실패·실행 소유·후속

320의pointer replace이후reader/결과파일/stdout계측실패가나면적용이이미일어났을수있다. 자동rollback/retry는없으므로archive/receipt/report/pointer와실패위치를Root가좁게확인해야한다.322는파일게시/설정을바꾸지않으나response/checks가부분기록일수있다. checks전부true/완료status전에는API검증완료가아니며재시도하지않는다.

Root의전체코드/current핀·OScollector/QA/native부재/lock/sourcehold·실316결과확인·별도GO후320단1게시,정확실publication지문후322단1API,이후323실브라우저의콘솔/overflow/시점표시를따로확인해야한다. 이정적검토는그후속을승인하거나수행한것이아니다.

319순수계약helper는격리상태이며175/170source64MiB차단은계속남아있다. bare검토current게시나API성공이실target수집연결완료/remote품질/실나지/학습승인으로바뀌지않는다. 실제의미있는게시결과는Root가이해자료·대본FAQINDEX이력에인계한다. 전체개발은미완료다.
