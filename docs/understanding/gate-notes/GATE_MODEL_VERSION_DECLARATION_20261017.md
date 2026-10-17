# Gate Model Version Declaration 20261017 — 내부 등록의 선택적 버전 메모

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/experiment_registry.py`; `tests/test_model_version_declaration.py`; `docs/implementation/97_model_version_declaration.md`; `evidence/integration/model-version-related-20261017.log`; `evidence/integration/model-version-catalog-observation-20261017.json`; `evidence/integration/model-version-original-registry-20261017.py`; `evidence/integration/model-version-initial-tests-20261017.log`; `evidence/integration/model-version-independent-20261017.log`; `evidence/integration/model-version-full-tests-20261017.log`; `evidence/integration/model-version-live-integrity-20261017.json`; `evidence/integration/model-version-next-review-20261017.json` |
| confidence | 완료 코드·작은합성파일/임시Store·원문핀동등·기존catalog metadata 관측 |
| status | TESTED_SYNTHETIC: 내부선택옵션; 운영등록·실제modelresolver 미연결 |

## 쉬운 설명

완료 실험을 보관할 때 담당자가 직접 적은 모델 버전 메모를 선택적으로 함께 남긴다. 메모는 확인한 checkpoint와 훈련 보고서의 지문을 가리킨다. 적지 않으면 예전 보관 방식 그대로다. 메모가 있다고 공식 기관이 승인한 버전이나 검증된 모델 원본이 되는 것은 아니다. 같은 모양의 메모가 이전 보고서에 들어 있을 수도 있어 모양만으로 작성 경위를 인증하지 않는다.

## 이론적 배경

96은 모델 버전 문자를 검사했지만 실제 등록에는 권위 version 계약이 없었다.97은 미래 내부 호출이 caller version을 명시할 선택 통로만 추가한다. `register_experiment(store, report_path, *, model_version=_OMITTED)`이며 기존 main/API/UI는 report_path만 보내 생략 동작을 유지한다. dataset_version을 model version으로 추정하지 않고 resolver·승인·새 API를 붙이지 않는다.

생략과 명시None을 sentinel로 나눈다. 생략은 원 응답과 rawSQLitebody·put순서, 기존 rawtraining의 임의필드 복사까지 그대로다. 새 필드를 만들지 않는다. 기존 raw field가 같은형태/source값을가져도명시호출이만들었다는인증은아니다.

## 코드와 데이터 동작

기존완료상태·ID/중복·경로·checkpointSHA·훈련report와datasetmanifest출처검사를먼저한다. 기존lineage계산뒤첫put전에96문자helper로명시version을검사한다. invalid/null/bool/공백/control/surrogate/257자/latest/current는거부하며쓰기0이다. 정상패딩은원형그대로다.

rawtrained.model_version이있으면exactstr과caller원문이같아야한다. rawtrained.model_version_declaration키가있으면값이null/동일형태여도명시호출은충돌거부한다. 성공하면modelrecord에만exact5 model_version_declaration을추가한다. schema_version1/sourceCALLER_EXPLICIT_REGISTRATION/version원형/checkpoint_sha256기존검증값/training_report_sha256기존lineage다. 새topmodel_version이나dataset필드는만들지않는다.

추가읽기/hash없이기존값을재사용하지만기존등록은파일을읽고hash한다. 작은추가로직의추가IO0을전체IO0으로확대하지않는다. 성공레코드는기존Draft·independent_evaluationfalse·scientific_accuracy_validatedfalse와claim을유지한다. 이것은새합성성공레코드의계약이며옛모든레코드에sciencefalse가있다는뜻은아니다.

## 시험과 관측 근거

신규10포함관련37 PASS/14.006초다. SHA핀원registry모듈과생략응답·rawSQLitebody·put순서·원파일불변을대조했다. 명시exact5/model-only·추가지문읽기없음·패딩/256·충돌/중복/기존오류우선·keywordonly를확인했다. 두번째put실패fixture는dataset만남을수있는비트랜잭션한계를보였다. 운영실패/복구를실행한것은아니다.

최초시험1개는Windows경로표기비교가틀렸고시험을as_posix로고쳤다. 초기실패로그는보존했고제품결함이나rawSQLite동등실패로설명하지않는다. 독립13 PASS/9.575초와 최종 전체987건/986 PASS/기존1 SKIP/380.835초·종료0,보존근거를확인했다.

읽기전용운영catalog는14기록/models1이었다. 기존CPUbaseline은Draft·independentfalse이며model_version/declaration은둘다부재, dataset_version만있었다. science필드는부재로null관측이며false로채워말하지않는다. 기존모델의실제version은UNKNOWN이고역채움·datasetversion대체·운영등록은0이다.

## 신뢰·원자성·UI 한계

caller메모는기관권위·원본인증·과학·실행승인이아니다. 생략경로가rawtraining임의필드를복사하므로exactshape/source키만보고명시등록호출의출처를인증할수없다. 실제modelresolver는계속BLOCKED다.

기존modelID또는datasetID가있으면거부하지만genericStore.put은replace가능하고중복조회와두put은단일transaction이아니다. datasets→models두쓰기중두번째실패·동시경쟁·전역immutable은해결하지않았다. 부분실패자동정리/운영복구도추가하지않는다.

기존ModelReview/main은옵션을전달하지않아생략동작이다. 공개API/UI·훈련producer·readiness필드는바꾸지않고직접frontend/build/browser시험도없다. 원본·원장/lock·예약136314880B·분할·모델·원본5차단/후보4차단을유지한다. 운영등록·Job/Workflow실행·수집·실자료QA·정식학습·배포는없다.

## 1분 발표

“내부 실험 등록에 담당자가 모델 버전을 직접 적을 선택 옵션을 만들었습니다. 기존 파일 검사 뒤 버전 메모를 확인한 checkpoint와 훈련 보고서 지문에 연결합니다. 생략하면 예전 응답과 기록을 그대로 유지합니다. 메모는 caller의 선언이며 기관 권위나 모델 원본 인증은 아닙니다. 같은 모양의 raw 메모가 복사될 수도 있어 모양만으로 생성 경위를 인증하지 않습니다. 두 번 저장의 부분 실패와 동시 경쟁도 해결한 것은 아닙니다. 기존 화면과 API는 옵션을 쓰지 않고 실제 운영 등록이나 학습은 하지 않았습니다.”

## 5분 발표 순서

1. **0~1분:** 보관 시 선택 버전 메모의 비유를 말한다.
2. **1~2분:** 생략·명시None·정상 메모와 기존 오류 순서를 설명한다.
3. **2~3분:** exact5와 기존 파일 지문 연결·shape만으로 인증 불가를 말한다.
4. **3~4분:** 생략동등·합성명시·기존catalog부재/null을 구분한다.
5. **4~5분:** 두쓰기 한계·UI미연결·실제resolver/승인BLOCKED를 말한다.

10분 설명에서는rawfield충돌·중복model/datasetID·새top필드없음·추가IO와기존IO·운영부분실패미검증을추가한다.

## Q&A

**버전 메모가 있으면 공식 모델 버전인가?** caller 선언이다. 기관권위·원본인증과 다르다.

**모양이 같으면 명시 호출로 생성됐나?** 단정할 수 없다. 생략이 rawtraining 필드를 복사할 수 있다.

**생략과None은 같은가?** 다르다. 생략은 기존동작이고 명시None은 거부한다.

**두 등록이 원자적으로 저장되나?** 아니다. 두번째 실패 시 dataset만 남을 수 있다.

**기존모델에 version을 채웠나?** 채우지 않았다. 기존version부재는UNKNOWN이며datasetversion으로대신하지않는다.

## 이후 갱신

독립·전체·보존 근거를 읽고 INDEX·변경 이력·계약·Orchestrator·MLOps·구조·용어·발표·FAQ·시연을 함께 갱신했다. 다음은 PLANNED다. 기존 등록API/UI의 기본off옵션으로명시version을전달하되키부재는원호출·명시null은97거부로구분할계획이다. 기존lock/auth·201/422·Draftgate를유지하고실앱성공등록은검증하지않는다. 브라우저는입력과안전한없는report422만,성공표시는TempStore/mock격리근거로구분한다. 현재이연결구현·실제검증은없다. 전체개발과10분보고는계속된다.


## 최종 회귀와 보존 범위 보완

최종 backend 전체 **987건 중986 PASS·기존 Windows symlink 권한 제약1 SKIP**,380.835초·종료0이다. deterministic 경계시험은 통과했다. 신규10개가전체에포함되고관련37/14.006초·독립13/9.575초(새10+기존registry3)·fixture사례는추가합산하지않는다.

보호141참조·기존코어70개·catalog14·Job2본문·이전증거616파일은같았다. experiment_registry.py는이전snapshot에없었다. 최초변경집계가이를누락해멈췄고수정전보관원문SHA a20468f121900094808112b9c8e783bf2a0ce59f520ff0bffbbcf2438bd12548과preflight근거를additional baseline1개로명시보충했다. 변경후코드로역산한baseline이아니다. 최종허용기존수정은registry.py한파일이다. 이전snapshot/증거는바꾸지않았다.

이는지정보호범위와추가사전baseline의대조이며전체workspace나원자snapshot인증이아니다. 운영등록·역채움·JobPOST·executor·실자료QA·정식학습은0이다. 기존UI/API는옵션을생략하며직접frontend/build/browser검사는없다. 실제modelresolver와준비성·과학승인은계속BLOCKED다.
