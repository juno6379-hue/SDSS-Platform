# 325 — 격리된 target256 명시 source local preflight

상태: **TESTED_SYNTHETIC / ISOLATED_ONLY / main 미적용 / 실coordinator BLOCKED**.319/324 원판을 보존하고325 격리workspace에서만 공용JSON reader의 좁은상한과새 명시175 localpreflight를 연결했다. 운영 source/원장/proposal/label/모델 읽기·복사0, HTTP/native운영검사/collector/예약0, main공유제품 편집0이다. 시험에서만합성TempJSON/작은GTiff를생성·검증했다.

위치: `evidence/integration/target325-workspace-20261018/`. runtime union은공용profile reader·targeted_bare_plan 수정2개,319순수helper 원판1개,신규targeted_source_io1개다. 관련9개main Python기반을원바이트baseline에보존하고종료시main/archive bytes·SHA exact를검산했다.319freeze의모든참조파일과324문서도보존했다. main에새helper2개는여전히없다. patch325.diff/patch325-manifest.json/freeze325.json이최종목록이다.

## 공용 API: 기본동작 불변인 좁은 cap만

격리 `manifest_resource_profile.py`의API는 다음과같다.

```python
bounded_json_digest(path, role, *, _capture=False, maximum_bytes=None)
read_metadata(path, role, expected=None, *, maximum_bytes=None)
```

maximum_bytes=None이면기존role한도·반환·예외를유지한다. 명시값은exactint/bool제외/0<값≤기존rolecap일때만받는다. source128MiB cap을256MiB로올리거나pointer64KiB를늘리는값은입력path stat/open이전 MANIFEST_JSON_NARROW_CAP_INVALID로거부한다. 알려지지않은role도원래오류로거부한다.

효과cap은파일stat/동일fd fstat/실read횟수·SHA/전후identity와parser `_tree`의cap까지전달된다. JSONdepth/node/row검사는기존공통parser/profile를재사용한다. 사전stat만8MiB확인한뒤16MiBreader를호출하는구멍을만들지않았다. default/None은고정원판profile의실제read/hash반환과합성대조했고legacy쪽호출은좁은cap인자를전달하지않는다.

## 새 명시 localpreflight 경로

새 `prepare_explicit_targeted_bare_jobs(project_root, request, base_config)`만325adapter를호출한다. **기존 `prepare_targeted_bare_jobs(root, plan, base)`는원v1/source64MiB경로**를유지하며ambient128scope가있어도자동상향하지않는다. 기존outerv1/v2/default동작을새v3로fallback하지않는다.170CLI/worker/registry는이새entry를아직호출하지않는다.

adapter의순서는319 validate_request_v3로exactouterv3/planv2·양쪽128marker·3GiBmarker를먼저검증→공통descriptor/marker정확일치확인→한operation128scope→root/path→fixedrole pinnedJSONread→기존175핵심의새명시경로→마지막모든JSONref identity/SHA재핀이다. 알수없는marker/변경descriptor는root/open이전에실패한다. 원v3canonical/requestSHA·planv2marker를유지하고232용내부envelope를과거approval로사용하지않는다.

JSON역할은source128MiB,proposal/boundary2MiB,ledger/lineage8MiB다. ledger는status_report16cap에서maximum_bytes8로, lineage는readiness16cap에서maximum_bytes8로좁힌다. source는실제scenes+historical_noneligible≤3000/depth32/node4M/SHA를확인한다. 원본JSON형식의scenes가없거나list가아니면실패한다. rawlabel/image/support TIFF는기존64MiB·MemoryFile/공간조건으로만읽고sourceJSON128로분류하지않는다.

175핵심에서proposal/source/boundary/lineage의JSON만새reader로보내고legacy분기에서는기존_pinned/_json을그대로사용한다. 실제local라벨픽셀/grid/boundary/listedimageoverlap검산은원래175와같다. planv2marker가canonicalplan에포함되므로새planSHA/jobkey가생길수있다.기존v1 job/config 결과는원판과exact대조했다.

cache는path/role·첫identity/expectedSHA를결속하며cachehit은stat/핀만확인하고실read0이다. 마지막재핀은같은내용으로교체된파일도첫identity와달라지면거부하고,actualhash/후identity를다시대조한다. 성장·교체·pin불일치를성공으로바꾸지않는다. ProfileResourceError는새175경로의일반ValueError/Exception처리에삼키지않고상위로전파한다. legacy경로의기존오류형식/반환은유지한다.

반환은LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED 또는기존차단결과이며execution_supported/coordinator_connected/training_ready=false다. manifest_profile/request_schema_version3/request_sha256와metadata_usage를추가하지만운영권한/실pending지원검증/원격품질승인은아니다.

## scope·I/O 범위

중첩operation은같은ContextVarbudget을재사용해새16GiB로초기화하지않는다. 실제localpreflight의JSONread/hash·마지막재핀만누적하며in-memoryrequest/base_config사본은파일read로세지않는다. 반환dict를caller가나중에직렬화하는I/O는포함하지않는다. 이작업은**LOCAL_PREFLIGHT_JSON_ONLY**이며170lock내재검사/worker context전파·state/report/receiptwriter전체계측이구현된것이아니다.

새local경로에서큰고정source를읽을수있게됐지만maintarget256source64차단은아직그대로다. sourceprofile권한연결·실집행전체16GiB계측완료라고보고하지않는다. 원격COG64MiB+metadata1MiB/4GiB추가예산·2worker/2초/첫429/3000·256/최종80/주내95/scene-split/window/B02/SCL/support/oldpending/학습false는변경하지않았다.

## 실제 합성시험 근거

-첫집중18 PASS/6.195초. 최종전descriptor/128overcap·공용원판대조를추가했다. 처음부터실패0이며PendingDeprecationWarning(Affine연산)은기존fixture/코드의경고로로그에보존했다.
-최종격리 **63 PASS/19.563초(wrapper22.031초)**, 외부baseline폴더없는Temp배치 **65 PASS/46.256초(wrapper51.766초)**/exit0/skip0이다. focused-final325.log/portable-final325.log/test-results325.json을고정한다. 319순수계약27건과기존175회귀·신규cap/adapter검사를포함한다.
-유효64~128MiBJSON 검증은portable에서**단1회**수행했다. 합성source67112960B(64MiB+4096)를새명시175localpreflight로19.5초검증했고작은Temp라벨/도형검산까지완료했다. metadata read134227800B/write0/합134227800B<17179869184B였다. source본문은유효JSON+whitespace이며실rich운영128MiB문서성능/품질을보장하지않는다. sourceSHA는large-once325-observation.json에고정했다.
-같은portable실행에서실제4백만개값을가진합성JSON의node상한초과를차단했다. 나머지시험은source128MiB+1 sparsefile/ledger8MiB+1 사전open차단,오염percall cap·행3000+history1/depth33·pin불일치·fdread중growth/동일내용교체·최종재핀·cache0read·중첩budget소진·resource상위전파·프로토타입/UTF8/분리canonical/falsegate를확인했다.
-legacy175 반환/오류를SHA고정원판fixture와동일Temp입력으로대조했다. ambient128에서도64MiB+1 legacy입력은원래FILE_LIMIT로막혔다. profile default/None도고정원판과동일반환이었다.232v1(default2GiB)/v2(정확3GiB)는319회귀에서보존확인했다.

large검증직후Windows프로세스PeakWorkingSet표본209129472B,뒤node검사중OS별도표본Peak442609664B를관측했다. 이는각시점Windows표본이며전체시험최종peak/상한보장이나LinuxRSS가아니다. RSS미관측을유지하며시험전체wall/helper시간과구분한다. 운영자료/HTTP/모델학습0이다.

portablebundle은관련runtime9기반+새helper/수정사본·시험/엄격SHAfixture만복사하고baseline-folder/main/source/원장/모델이없는임시root에서실행했다. fixture누락/변조는실패하며fallback/skip은없다. self-contained는Python/GIS설치라이브러리까지없어도된다는뜻이아니다. 운영전체native/fullinventory를재실행하지않았다.

## 다음 인계와 남은 차단

별도독립리뷰→Root baseline현재SHA대조/정확공유적용승인전main반영0이다. 이후coordinator소유가170CLI/전역lock안validate·167pending/fullsupport·현재source/ledger·sharedscene/windowregistry·workerthread/전체metadatawriter계측/실정산을연결해야한다. 이번localpreflight성공은그작업을완료하지않는다. 큰source와전체지원영역3GiB·라벨768MiB검토의자원계약도분리한다.

내부격리기능이므로API/UI코드변경·실브라우저는0이며사용자화면에운영가능이라고게시하지않는다. Root에코드·시험·계약/사용법·문서/지문을전달하고독립리뷰뒤이해담당의쉬운설명·대본FAQINDEX이력갱신을요청한다. main변경/실수집·학습승인은아직없고전체개발미완료다.
