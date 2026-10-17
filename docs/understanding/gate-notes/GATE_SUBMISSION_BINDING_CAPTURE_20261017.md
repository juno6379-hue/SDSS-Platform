# Gate Submission Binding Capture 20261017 — 같은 입력 점검에서 새 Job의 기대 선언 기록

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/execution_binding_capture.py`; `backend/app/job_inputs.py`; `backend/app/gmais_api.py`; `tests/test_execution_binding_capture.py`; `docs/implementation/78_submission_binding_capture.md`; `evidence/integration/submission-binding-capture-related-20261017.log`; `evidence/integration/submission-binding-capture-independent-20261017.log`; `evidence/integration/submission-binding-capture-compat-before-20261017.json`; `evidence/integration/submission-binding-capture-compat-after-20261017.json`; `evidence/integration/submission-binding-capture-compat-runner-20261017.py`; `evidence/integration/submission-binding-capture-live-legacy-20261017.json`; `evidence/integration/submission-binding-capture-full-tests-20261017.log`; `evidence/integration/submission-binding-capture-live-integrity-20261017.json` |
| confidence | 코드·전체/독립/TempStore호환·실제legacyGET/보존근거; 운영신규capture/실제executor미확인 |
| status | TESTED_SYNTHETIC: 새capture/TempStore호환·전체회귀; VERIFIED_REAL: legacyGET호환; 실제executor미연결 |

## 쉬운 설명

주문 입력을 확인하던 담당자가 같은 확인 과정에서 받은 지문을 새 주문의 내부 메모에 같이 남긴다. 다시 창고를 방문하거나 상자를 한 번 더 열지 않는다. 예전 주문서를 고쳐 채우거나 같은 주문 재요청 때 새로 확인하지 않는다. 메모를 남겼다는 사실은 품질·권한·배달 승인이 아니다.

## 이론적 배경

77은expected/supplied선언대조만있어신뢰된expected구성경계가후속이었다.78은새Job제출의기존resolve_version검증record에서선택한metadata로expected를기록한다. 실제executor에전달된supplied를포착하거나실행전에77을연결한것은아니다. Registry등록/resolve·제출input_resolution·현재lineage와역할을구분한다.

## 실제 함수·같은 pass

기존루프를private `_resolve_job_inputs(store,input_refs,capture_rows=None)`로공유하고기존 `resolve_job_inputs`는capture없이기존반환을유지한다. 새 `resolve_job_inputs_with_capture`는기존pass를한번실행해같은resolve_version반환record의canonicalmanifestSHA와localrefsnapshot의index/id/version/assetSHA·optionalrole만선택한다. 추가Registry조회/자산읽기·별도DB쓰기는없다.

`build_submission_binding_capture`는선택rows를받는순수builder다. timezone있는ISO시각·exactlist1..64·integrity_verifiedtrue인전체rows·77envelope계약을확인한다.77guard의envelope selfcompare MATCH는shape/pin/순서일관성을확인한것이지실제supplied전달MATCH나실행승인이아니다. capture상한64/text256은선택기능범위이며기존resolver전체IO/RAM/CPU한도가아니다.

## 저장 extension·공개호환

새Job에만execution_input_binding_capture를기존Job레코드의같은store.put에추가한다. 기존HTTP/JobStatus/upstreamschema/input_resolution은변하지않는다. 멱등분기는pair호출전에반환하므로같은재요청과legacyJob에재조회/역채움은없다. 기존Job+멱등record의put2회는그대로이며capture전용쓰기를추가하지않는다.

| 내부 필드·상태 | 의미 |
|---|---|
| schema1·내부RFC·INTERNAL_REVIEW | 운영/기관승인이아닌내부저장확장 |
| captured_at | timezone ISO문자열; 실패/무효면null가능 |
| RECORDED | 모든선택row의기대선언/hash가형식검사를통과해기록됨 |
| UNAVAILABLE | 전체expected_envelope/hash는null·안전code/index만남김 |
| SAME_RESOLVE_VERSION_RETURN | 같은검증record에서pin선택; 추가Registry조회아님 |
| additional_* 0 | capture때문에추가된Registry/자산읽기/DB쓰기0 |

expected_envelope에는Job/Agent/Trace와orderedid/version/assetSHA/index·manifestSHA/role를의도적으로내부저장한다. URI·asset경로·manifest원문·품질보고서경로·예외원문은없고공개HTTP/Status에노출하지않는다. expected_bindings_sha256는배열만hash하며Job/Agent/Trace전체digest가아니다.

quality RAW/REJECTED·제한ACL로기존resolution이BLOCKED여도integritytrue면RECORDED가능하다. 이는검증된metadata를기록할수있다는뜻이지quality/ACL/실행gate통과가아니다. URI불일치/상충pin/resolve실패/일부row누락·상한/무효shape는wholeUNAVAILABLE이며부분envelope를주지않는다.

## 오류 격리·IO 범위

optional선택복사/import/builder의Exception만UNAVAILABLE로격리한다. 기존resolverpass는이경계밖이라예전unexpectederror를새로삼키지않고KeyboardInterrupt/SystemExit도그대로전파한다. 선택snapshot/caller/Registryrecord/반환resolution을분리해builder가변조후raise해도기존결과는유지한다.

builder만pure이며전체pair는기존Registry/asset/URI검사를실행한다.12false는capture가승인을부여하지않는뜻이지원래resolver가자산hash를확인하지않았다는뜻이아니다. additionalIO0을전체resolverIO0이나운영Job쓰기0과혼동하지않는다. 실제Job제출경로의기존put에선택필드만함께저장한다.

## 시험·TempStore 호환 근거

관련50 PASS/15.440초는신규16+기존34, 독립신규16 PASS/6.243초다. samepass/manifestpin·assetpin분리·기존wrapper·ACL/quality차단RECORDED·wholeUNAVAILABLE·상한/예외격리·기존예외전파·분리/무추가IO·내부저장/공개응답/멱등보존을확인했다. 반복시험을전체에중복합산하지않는다.

Root의before/afterTempStore3사례는PUBLIC등록/RESTRICTED등록/미등록입력이다. 전체기존resolver/HTTP/JobStatus와capture제외저장Job·resolve각1/put2·멱등추가조회/쓰기없음이deepEqual이었다. 이것은임시합성Store호환근거이며운영POST/실제신규Job/capture생성증거가아니다. fixture시각차이로실패하던초기assert는Store.now도고정해수정했고생산응답변경/결함재현으로보고하지않는다.

Root실제API8002의legacyJob2건에서status와input-resolution GET각2회·총4회200을확인했다. Status는기존BLOCKED원문과같고snapshot은LEGACY_SNAPSHOT_NOT_RECORDED/availablefalse다. 기존capture부재/역채움없음·catalog14/Job body동일·운영POST0을관측했다. 이실제GET호환은새productioncapture생성관측과다르다. 최종 전체 scripts/test.ps1은 **805건 중804 PASS·1 SKIP/327.813초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. 관련50 PASS/15.440초(신규16+기존34)·독립신규16 PASS/6.243초·TempStore3호환사례/실제GET4회를전체805에중복합산하지않는다. 종료후보호141참조·36기존코어SHA·카탈로그14기록canonicalSHA/기존Jobbody불변을재확인했다. 이전추적코드/데이터/프론트중의도한job_inputs.py/gmais_api.py두파일만변경됐고신규파일도있으므로전체workspace변경2개/원자snapshot보장은아니다. 이해에이전트는시험/HTTP/DB를실행하지않고코드/증거만읽었다.

## 현재성·UI·한계

과거운영legacyJob에는capture를역채우지않고실제executor/공급전달capture는미연결이다. 형식상RECORDED도현재/미래bytes·TOCTOU·ACL·과학/실행승인을인증하지않는다. 현재resolver·권한/READY·파일확인은실행시별도필수다. 기존모델/데이터준비도와원본5/후보4차단·나지부족·terminal2missing/예약136,314,880B·refund0은유지한다.

공개응답/화면변경없는내부저장단위라이번직접UI/프론트재시험/브라우저검사는없다. 향후조회/노출에는별도안전projection계약이필요하다. 전체개발과10분보고는계속한다.

## 발표1분

“새 Job의 입력을 확인할 때 같은 검증 과정에서 얻은 manifest 지문을 내부 기대선언으로 함께 기록하도록 했습니다. 추가로 Registry를 조회하거나 파일을 다시 읽지 않고 기존 공개 응답도 유지합니다. 예전 Job이나 같은 재요청은 다시 확인하거나 역채우지 않습니다. 품질이나 권한 때문에 차단돼도 입력 지문 메모가 기록될 수 있지만 이것은 실행 승인이 아닙니다. 실제 실행기에 전달된 입력을 포착하고 대조하는 경계는 아직 연결 전입니다.”

## 발표5분·10분

1. **0~1분:** 같은입력검사에서새주문메모를남기는비유를말한다.
2. **1~2분:** private공통pass/기존wrapper·새pair·같은recordpin을설명한다.
3. **2~3분:** 새Job별도extension/공개응답불변/legacy·멱등역채움없음을보여준다.
4. **3~4분:** RECORDED vs gate/ACL·UNAVAILABLE·TempStore/실제legacy/전체/보존근거를구분한다.
5. **4~5분:** additionalIO0 vs 기존IO·예외격리/전파·실제executor미연결을말한다.

10분확장에서는selfcompareMATCH·timezone/상한·배열hash·원문/URI비저장·mutate-then-raise·기존put2/현재bytes확인후속을설명한다.

## Q&A

**RECORDED면실행가능한가?** 기대선언metadata기록이며quality/ACL/READY·과학/실행승인은false다.

**파일을안읽나?** capture추가읽기는없지만기존resolver는Registry/자산검사를한다. builder만pure다.

**옛Job도채워졌나?** legacy/동일멱등replay에는조회/역채움없다.

**실제executor의전달값인가?** 제출expected기록단계이며supplied포착/실행전77대조는미연결이다.

**화면에새필드가생겼나?** 내부Job저장확장만있고HTTP/JobStatus/UI는같다. 후속공개조회는안전projection이필요하다.

## 이후갱신

실제legacy·전체/보존최종근거를읽고INDEX·변경이력·계약/Orchestrator/구조/용어·대본/FAQ/시연을함께갱신했다. 신규등록/학습이나전체프로젝트완료를뜻하지않는다.

## 다음저장capture조회 — PLANNED

다음79는PLANNED다. storedcapture의exact형식/hash/Job-request연결을검사하는safeprojection/API와같은단위의수동UI를검토한다. RECORDED/UNAVAILABLE/LEGACY/INVALID를구분하고raw식별자/manifestpin/URI를노출하지않으며현재Registry/bytes/executor승인을부여하지않는다. RECORDED시각은timezoneaware필수·UNAVAILABLEfallbackNone허용을설계때검증한다. 현재79코드/API/UI는미구현이다.
