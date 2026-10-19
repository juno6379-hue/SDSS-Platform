# 309 — 지역·연도 최소량 충족 후 새 고정 후보 QA 준비

상태: **PREPARED / ROOT_QA_GO_REQUIRED / 실제 QA0 / 후보 수 미확정**. 304 단1 native 성공 뒤 준비만 진행했다. 실제 후보QA·학습·registry·HTTP·게시/API/UI0이며 운영 제품/원본/원장/모델/split 쓰기0이다. 공유 적용이나 미래 성공을 의미하지 않는다. Root가 sourcehold/추가 collector 금지를 유지한다.

## 실제 준비 입력과 보호

| 역할 | bytes | 직접 metadata SHA256 |
|---|---:|---|
| post304 source |69564847|`0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658`|
| ledger provenance |68395|`d5ee31ff7970adaaa6b166805c240616efa8e9af713bb8394c7a166346f21c91`|
| 고정 policy |1306|`01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7`|
| 단1 native304 |34588|`7e933d923f6a7507a878f66bd7fea391b7b181779746f175567f0febdf8c884c`|

파일별 cap-before-read/streaming hash/전후identity/정확 bytes를 확인했다. source 전체 JSON parse나 래스터 읽기는 준비에서 하지 않았다. source는 default64MiB보다2455983B 크다. 크기로 자동 상향하지 않고 Root가 정확128을 명시 승인해야 한다. 현재source 등록1779/적격1407/cellgap0은 완료native 근거다. split865/292/250은 이전834/292/250에 신규train15+16을 더한 기록상 산술이며 새 전체source QA의 결과가 아니다. history 수/새후보 수/제외량/최종gate는 아직 null·미확정이다.

기존1360 pointer와 `candidate-receipt293-20261018.json`은 각각1211B/동일SHA `996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0`를 직접 확인했다. runner가 시작 전 exact protected_expected 및 종료 뒤 보존을 확인한다. 이전290 원판/prep/완료증거는 보존했고 새 준비 archive2개에 runner/prep 원바이트를 고정했다. receipt275나 과거1348을 현재 보호 대상으로 잘못 사용하지 않는다.

실제 OS 조회에서 해당 QA/collector/native Python0과 execution lock 부재를 확인했다. Root GO 직전 다시 확인해야 하며 준비 관측이 미래 동시성 보장은 아니다. 새 run-id `guarded309-20261018`의 work/evidence/log/launch/terminal 모두 미존재를 확인했다.

## 새 runner 계약과 최소 diff

runner `priority309-runner-20261018.py` SHA `922e70584c51ac0c9cd247bc22d49be4bdf9936c8fcdb3b800be5b5874ea4e83`, prep `priority309-preparation-20261018.json` SHA `698bb2a02155de2027d138d65820e836767f6475003f57301cc0f1a5de73fd33`다. 기존290과 차이는309 식별자/새준비 지문뿐이며 실제 코드16개 SHA/bytes는 현재도290과 exact 일치한다. `.diff`와 archive를 보존했고 AST compile만 수행했다. runner import/CLI 실행/실QA0이다.

한 ContextVar scope에서 정확 `bounded128m-3000-v1` descriptor SHA `db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4`를 확인한다. source/candidate128MiB/scene+history3000/depth32/node4000000/누적JSON IO17179869184B를 유지한다. 역할별 policy1MiB/receipt64KiB/readiness16MiB/saved_plan4MiB 등 개별cap은 그대로다.128MiB가 최대 RAM/RSS/시간 보장은 아니고 depth/node검사는 decode 후다.

준비JSON2회 bootstrap의 실제읽기·GO·native proof·보호pointer 전후와 source snapshot→source QA→split plan/validation→package/stage→후보QA→실파일SHA→summary·log/launch/terminal까지 동일 budget을 사용한다. 중첩 @profile_entry는 기존 scope를 재사용하며 기존164 CLI main 호출 지점은 정확1곳이다. source/policy는 기존164가 출력 전/각QA 뒤/최종 직접 검산한다. ledger 준비핀은 별도 provenance이며 QA입력으로 추가하지 않는다. 준비단계hash를 실제QA 계측값으로 소급하지 않는다.

Root GO schema는 runner의 exact set과 일치해야 한다. 미래 GO는 아직 생성하지 않았다.

```json
{
 "kind":"PINNED_CANDIDATE_QA_309_GO","approved":true,"run_id":"guarded309-20261018",
 "preparation_sha256":"698bb2a02155de2027d138d65820e836767f6475003f57301cc0f1a5de73fd33",
 "native_audit_sha256":"7e933d923f6a7507a878f66bd7fea391b7b181779746f175567f0febdf8c884c",
 "source_sha256":"0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658","source_bytes":69564847,
 "manifest_profile":{"name":"bounded128m-3000-v1","sha256":"db44041c31fd28ef05c3157725fb07356e0799014f7d3300361d0f985ce6afe4"},
 "no_active_collector":true,"execution_lock_absent":true
}
```

Root 전체runner/최소diff/최종freeze/OS·원본·정책·새경로 검토 뒤 별도 GO를 받아야 아래 명령을 **한 번** 실행한다.

```powershell
python -X utf8 -u evidence/integration/priority309-runner-20261018.py --approval E:/GeoAI–MLOps–SDSS/evidence/integration/priority309-go-root-20261018.json
```

현재는 실행 승인0/launch·source사본·후보·summary0이다. 실패·cap초과 시 부분 보존/exit2, 자동 retry·상한 확대·품질우회0이다. budget소진/쓰기 실패는terminal도 없거나 부분일 수 있어 예산밖 fallback 완료영수증을 쓰지 않는다. 느린 metadata 단계를 이유로 재시작하지 않는다.

## 완료 후 검산 및 해석 경계

성공해도 summary/terminal·11실출력핀·세schema2정확128marker·실파일SHA·정확retained rows/lineage/완전partition·같은scene누출 후보에서만제외를 확인해야 한다. 이전290의1360/16제외/5426파일/3차단은 과거이며 이번 개수로 고정하지 않는다. 원본·운영split을 수정하지 않는다. actualwall/sourceQA/candidateQA 함수시간을 구별하고 RSS를 측정하지 못하면false를 유지한다. OS WorkingSet표본을 Linux RSS/최대peak보장으로 표현하지 않는다.

304 native에서 최소수량floor는0부족이 됐지만 신규나지는raw→quality→final→eligible 모두0이다. 나지 각split0.5%·기여5 미달3차단, 독립정답/정확도/다른모델 요구는 별개다. 새gate는 실제결과로 확정해야 하며 수량충족을학습승인으로확대하지않는다. connectivity의 NOT_CAPTURED_BUDGET도 관측대로남긴다. scientific_accuracy_validated/training/registry false를 유지한다.

완료 후 protected pointer/receipt293·원본/정책/원장보존을 metadata 인계검산하고 Root에 종료신호를 보내야 한다. Root가 그 뒤 old1360원바이트archive→새게시→profile명시재결속→실API→브라우저→문서·이해자료/대본FAQINDEX이력 순서로 별도 근거를 마감한다. 이 준비는 제품/UI 변경이 없어 화면 코드를 수정하지 않았고 실API/브라우저를 수행하지 않았다. 전체개발은미완료다.
