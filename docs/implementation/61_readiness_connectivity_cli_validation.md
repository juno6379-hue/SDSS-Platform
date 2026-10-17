# 61. CLI의 선택적 연결 근거와 새 readiness 파일 보호

## 쉬운 설명과 상태

기존 `scripts/run_experiment.py`에 기본 off인 `--connectivity-diagnostics`를 연결했다. 요청했을 때만 60의 assess 옵션을 전달하며 진단 결과는 별도 readiness JSON 파일에 기록된다. **진단 요청·CAPTURED 상태는 학습 승인이 아니다.** 기존 execute/run-id/gate/resume/학습 검증과 실행 경로는 바꾸지 않는다.

작은 synthetic manifest·mock 기반 검증은 `TESTED_SYNTHETIC`이다. 실제 자료 readiness 재평가·학습은 실행하지 않았다. Root는 저장 report 부재/기존 코드 구조/전체 회귀와 보호 상태를 별도로 확인한다. UI/API·원장/lock/모델·실제 예약 변경은 없다.

## 호출과 기본 off 보존

```python
run(manifests, root, readiness_path, policy=None, execute=False,
    run_id=None, epochs=20, resume=False, max_seconds=1800,
    epochs_per_call=20, *, connectivity_diagnostics=False)
```

기존 positional signature는 그대로이며 새 옵션만 keyword-only다. 정확한 bool만 허용한다. 기본/off에서는 원래 `assess(normalized_manifests, root, policy)` 호출형, readiness write_text 동작, 결과/요약 key와 문자 체계, 학습 경로를 유지한다. 기존 off가 기존 readiness 파일을 기록하는 동작까지 이 단위에서 바꾸지 않았다.

True에서는 `assess(..., connectivity_diagnostics=True)`만 추가하고 진단용 새 출력 보호를 적용한다. opt-in이어도 ready=False면 학습하지 않으며, ready=True라도 execute=False이면 학습하지 않는다. execute=True와 유효 run-id 등 기존 조건을 모두 만족하면 원래 실행 경로로 진행할 수 있다. 이 옵션 자체가 실행 권한을 추가하거나 차단을 해제하지 않는다.

## CLI 사용

```powershell
python scripts/run_experiment.py --manifest <합성 또는 승인된 입력> `
  --data-root <검사할 DATA root> `
  --readiness-output <DATA root 내부의 명시적인 새 JSON 파일> `
  --connectivity-diagnostics
```

진단 요청에는 명시적인 `--readiness-output`이 필수다. 기존 기본 output을 무심코 덮어쓰지 않게 하기 위한 opt-in 계약이다. off에서 readiness-output 생략시에는 종전 기본 경로를 그대로 사용한다. manifest/plan 상대 경로는 현재 작업 디렉터리 기준이며, readiness-output 상대 경로는 DATA root 기준이다.

`--connectivity-diagnostics`와 `--write-default-plan` 동시 요청은 어떤 plan 쓰기·plan 읽기·assess보다 먼저 CLI 오류로 거부한다. 기본 plan을 생성하는 기존 off action과 진단 action을 한 호출로 합쳐 보호를 우회할 수 없다.

## 새 출력 안전 경계

True의 출력은 다음 순서로 보호한다.

1. **assess 전에** 입력 manifest 경로를 canonical 정규화하고 출력이 DATA root 내부의 새 파일인지 검사한다. 기존 파일·디렉터리·final symlink·broken symlink를 거부한다. final symlink는 exists보다 먼저 검사해 불필요한 target 따라가기를 피한다. input canonical path와 같은 출력도 거부한다.
2. CLI는 plan 파일의 canonical path도 보호 대상으로 추가하여 plan 읽기 전에 output alias를 거부한다. Python run은 policy 객체만 받으므로 알지 못하는 plan 파일의 경로를 추측하지 않는다.
3. True 전용 경로 검사에서 원격/UNC/extended UNC, drive separator 외 colon·Windows ADS, 예약 device 이름(확장자 포함), 끝점/공백 등 Win32 별칭을 거부한다. PureWindowsPath로 비Windows 환경에서도 예약 이름을 보수적으로 판정한다. 실제 ADS를 생성하지 않는다.
4. 사전 logical output/parent의 resolved target과 가장 가까운 기존 parent directory identity(device/inode)를 기록한다. assess 후와 부모 생성 후에 target/parent·ancestor identity·새 파일 존재 여부를 다시 확인한다.
5. UTF-8 `open('x')`로 exclusive create한다. 최종 파일이 중간에 생기면 기존 writer의 파일을 덮어쓰지 않고 실패한다. JSON은 indent2, ensure_ascii=False, allow_nan=False로 기록한다.

이는 원래 입력 byte hash를 새 필수 조건으로 만드는 기능이 아니다. 원본 데이터·plan·readiness·원장·lock을 지우거나 고치지 않는다. 새 파일 쓰기 중 예외가 발생하면 **부분 생성된 새 파일은 남긴다**. 오류 조사용 흔적으로 보존하며 cleanup/재시도로 기존 파일을 삭제하지 않는다. 이후 호출은 다른 명시적 새 출력 경로를 사용해야 한다. 부모 디렉터리가 일부 생성된 경우에도 자동 삭제하지 않는다.

경로 재대조와 x-mode는 전체 작업의 원자성을 보장하지 않는다. 마지막 parent 검사와 open 사이의 악의적 OS-level directory retarget까지 완전히 차단하는 fd-anchored transaction은 아니다. 검사 시점의 canonical target/identity를 관측한 범위이며 atomic snapshot 또는 전역 writer lock을 주장하지 않는다.

## 요약·오류 계약

off stdout 요약은 기존 4키 `status`, `ready_for_training`, `blocker_count`, `scientific_accuracy_validated`를 유지한다. True만 다음을 더한다.

| 필드 | 의미 |
|---|---|
| connectivity_capture_status | 알려진 capture 상태, 미지/비문자 상태는 UNKNOWN_CAPTURE_STATUS, 진단 객체 부재는 NOT_REPORTED |
| connectivity_scene_count | 알려진 bool 아닌 비음수 int만, 그 외 null |
| eligible_patch_count | 알려진 supplied_eligible_patch_sum, 또는 유효한 train/val/test count 합계. bool/음수/잘못된 구조는 null |
| connectivity_is_training_authorization | 항상 false |

scene 수와 eligible patch 수를 혼동하지 않는다. 누락·미지 상태를 CAPTURED 또는 성공으로 추정하지 않는다. True 요약은 ensure_ascii=True로 ASCII bytes가 된다. 기존 main의 stdout UTF-8 reconfigure는 그대로이며, `PYTHONIOENCODING=cp949` 시험에서 stdout 자체가 CP949로 고정되었다고 주장하지 않는다. 확인한 사실은 새 요약이 ASCII라 인코딩에 독립적이라는 점이다. True 오류 stderr도 ASCII escaped 문자열을 사용한다.

일반 진단/path/write 실패는 CLI 종료1이다. 옵션 충돌·명시 output 누락은 argparse 종료2다. 기존처럼 `--execute` 요청인데 gate status=blocked면 요약 후 종료2다. 비실행 blocked 진단은 종료0일 수 있으며 이것은 학습/과학/운영 승인이 아니다.

True+execute=True가 실제로 기존 학습 경로를 통과하면 최종 experiment report에는 diagnostics를 자동 전파하지 않는다. 진단 원문은 앞서 기록한 **별도 readiness-output 파일**에 있다. 최종 experiment report 기반 요약은 diagnostics가 없어 NOT_REPORTED/null이 될 수 있다. 이를 성공으로 추정하거나 두 보고서를 합치지 않는다. 이번 시험에서는 실제 학습을 수행하지 않았다.

## 시험 증거

관련 파일: `tests/test_readiness_connectivity_cli.py`, 최종 **19 PASS / 4.770초**. 로그: `evidence/integration/readiness-connectivity-cli-related-20261017.log`.

검증은 default/off assess 호출형·기존 출력 write 동작, True flag 전달·새 UTF8 JSON, 정확 bool 사전거부, 존재/디렉터리/broken symlink·input/plan alias·root 이탈·원격/ADS/device/Win32 별칭 사전거부, assess 중/최종 open 직전 writer race의 승자 byte 보존, parent identity/logical retarget, 부분 새 파일 보존을 포함한다. 실제 ADS 쓰기는 하지 않았고 tiny synthetic path preflight만 사용했다.

mock으로 ready+noexecute·blocked+execute no-train, 진단이 기존 run-id 검증을 우회하지 않음, unknown/missing capture·typed count·off 요약 키를 확인했다. 작은 synthetic manifest를 실제 CLI subprocess로 실행해 CP949 env ASCII 요약·UTF8 파일·명시 output/planwrite 충돌·재실행 기존파일 보존·blocked --execute 종료2와 결과/model 폴더 미생성을 확인했다. 실자료 assess·training 호출은 없다. 독립시험/전체회귀는 동일 시험을 중복 합산하지 않는다.

초기17 PASS는 final symlink 순서와 Windows ADS/예약명 보강 전 이력이다. 독립검토에서 tiny preflight 경로 synthetic.json:diagnostic 및 CON.json이 통과함을 발견해 보완했다. 실제 ADS/device 쓰기나 원본 변경은 없었고 최종 회귀에서 거부를 확인했다.

## 문서·UI·후속 범위

의도적으로 바뀐 기존 파일은 run_experiment.py 하나다. 기존 assess/adapter/58/59·학습 경로의 계약을 변경하지 않는다. 현재 스크립트 SHA는 의도적으로 변하므로 Root가 preflight/AST tail/종결 보호 증거를 관리한다. 과거 저장 readiness를 재작성하거나 부재한 scene/원인을 복원하지 않는다.

이 기능은 내부 CLI의 명시적 선택 옵션이다. 공개 API/frontend 상태·버튼 계약이 없으므로 UI 변경은 필요 없다. UI 활성화·자동 실행·59 envelope와의 저장 연결·원장/스케줄 통합은 후속 범위다. 진단 기록은 기존 gate·독립 정확도·정산·자동 재개 승인을 대신하지 않는다.


## Root 실제 CLI 노출·정적 학습 경로 확인

[실제 도움말 로그](../../evidence/integration/readiness-connectivity-cli-live-help-20261017.log)와 [검사 기록](../../evidence/integration/readiness-connectivity-cli-live-help-20261017.json)은 실제 `--help` 1회 종료0·새 --connectivity-diagnostics/--readiness-output 노출을 확인한다. 자료 입력 없이 도움말만 실행했으며 실자료 assess·학습을 실행한 것이 아니다. parent 환경은 PYTHONIOENCODING=cp949였지만 기존 main의 stdout UTF8 재설정으로 도움말은 UTF8이며, 이를 CP949 출력 고정으로 표현하지 않는다.

[변경 전 소스](../../evidence/integration/readiness-connectivity-cli-run-experiment-before-20261017.txt)의 실제 bytes SHA는 `0e3ae07d2fb540547e746170d2c414c57537e852b5ae818945c36e19ac79b1c1`, 현재 raw SHA는 `a1b372fc5f920f2d8f83d889a2d1303e6e52a4e76b79841b14b477cf078e3cf3`다. [AST tail 대조](../../evidence/integration/readiness-connectivity-cli-ast-parity-20261017.json)와 [소스 diff](../../evidence/integration/readiness-connectivity-cli-source-20261017.diff)는 기존 `if not execute or not result['ready_for_training']` 경계부터 이후 학습/재개/추론/반환 구문까지 원형과 동일함을 확인한다. 새 경로 보호/요약 부분은 별도 합성 시험 범위이며 모듈 전체가 변경되지 않았다는 뜻은 아니다.

최종 독립 시험은 **19 PASS / 5.636초**, [독립 로그](../../evidence/integration/readiness-connectivity-cli-independent-20261017.log)에 추가 Windows 경로14종 preflight 거부를 기록했다. 초기 ADS/device 검사 공백은 코드 보완 후 재검증했고 실제 ADS/device 파일을 쓰지 않았다. 독립 반복/별도 실험은 전체 unittest 건수에 합산하지 않는다.


## Root 전체 회귀·보존과 후속 진단

[전체 회귀](../../evidence/integration/readiness-connectivity-cli-full-tests-20261017.log)는 **608건/607 PASS/1 SKIP/207.921초/종료0**이다. SKIP은 기존 Windows symlink 생성 권한 조건이며 deterministic 경계 시험은 통과했다. 관련/독립 반복19건과 별도 Windows 경로14종 실험을 전체 건수에 중복 합산하지 않는다.

[사전 기록](../../evidence/integration/readiness-connectivity-cli-preflight-20261017.json)과 [최종 보존 증거](../../evidence/integration/readiness-connectivity-cli-live-integrity-20261017.json)는 보호132참조·기존23진단/ML계약 SHA·저장 readiness SHA 불변, 기존 blocker5 원형/패치628·233·250 보존을 기록한다. 이전 evidence snapshot에 추적된 코드/데이터/계약의 변경은0이다. run_experiment.py는 당시 snapshot에 없었으므로 이번 명시적 preflight 원본과 raw SHA로 의도된 변경을 별도 확인했다. 전체 workspace의 무변경/원자적 snapshot 보장으로 확장하지 않는다. 원본/원장/lock/예약136314880B/분할/모델·terminal 없는2건·BLOCKED/모든 승인false/환불0 유지. 기존 보고서는 재생성하지 않았으며 실제 scene 수·과거 원인 분기는 UNKNOWN_NOT_PERSISTED다.

다음 단위는 명시적인 새 출력 보호와 고정 입력/정책 SHA·자료 읽기/시간/메모리 범위를 먼저 확인하고, **학습 없이** 실자료 readiness 연결 진단을 새 보고서로 1회 관측하는 것이다. 기존 저장 보고서·정책·분할·원장/lock을 고치지 않으며 --execute/--resume/학습/다운로드를 호출하지 않는다. 현재 이 실자료 실행은 PLANNED/미수행이다. 필요한 조건을 확인할 수 없으면 근거를 기록하고 독립 내부 개발을 이어간다. 공개 API/UI/버튼 계약이 없어 이번 UI 수정·49 UI시험/build·실제 브라우저 재검증 대상은 없다.


## 실자료 진단 후속 완료

[62 학습 없는 실제 연결 진단](62_readiness_connectivity_real_validation.md)에서 기존 정책과 고정 입력으로 CLI1회(70.437초/종료0)를 실행했다. 기존 보고서와 진단·시각 외 전필드 동일/차단5를 확인했고 새 보고서의1384scene·1111patch·0patch273 및 현재 token 연결을 검증했다. 생산코드/기존보고서/정책/분할/원장/모델을 변경하지 않았고 학습을 실행하지 않았다. 과거 원인 복원·차단해제·과학승인은 아니다.
