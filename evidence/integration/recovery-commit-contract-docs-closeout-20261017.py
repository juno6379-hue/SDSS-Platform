from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
section='''## 2026-10-18 — 복구 commit 단계 선언 검사 완료 (110)

새 순수 함수는 PREPARED→LEDGER_RECORDED→AGGREGATE_RECORDED→COMMITTED의 caller 선언과 ledger/aggregate/run-result 세 target의 before/expected_after/observed SHA를 검사한다. 최초 PREPARED·인접 전이·전체 동일 재관측만 구분하고 누락 근거·다른 작업 혼합·단계 건너뜀/역행·관측 불일치를 거부한다. source/evidence SHA는 caller 선언이며 실제 파일/권위/phase 증명이 아니다. 동일 before/after는 실제 쓰기나 단계 구별을 보장하지 않는다. 모든 결과 BLOCKED/UNVERIFIED·exactly_once UNKNOWN, 정산/환불/재개/쓰기/실행 false다.

입력 키의 exactstr 검사와 phase 표시용 사전 lookup 순서를 독립 검토로 보완했다. 최초·중간 통과 로그는 보존했고 최종 신규14 PASS/.022초·관련67건66PASS/기존1SKIP41.983초·독립63건62PASS/기존1SKIP41.636초를 완료 근거로 사용한다. 별도 poison-key5사례는 시험 건수에 합산하지 않는다. 새 독립 helper/시험/문서만 추가했으며 기존 제품과 API/UI 호출부는 바꾸지 않았다. 이번 전체/front/build/browser 재시험은 없고107 전체1069건은 이전 근거다.

Root 보존 검사는 보호141·이전증거809·catalog14·이전추적코드 불변을 확인했다. 수집기/예산코드는 현 raw snapshot 직접목록에 없어 별도 고정 Git 기준259b5f3의 원문 바이트와 대조해 둘 다 같음을 확인했다. 실제 pending2건에는 worker-result/annual-report가 여전히 없으며 새 helper를 적용할 operation/afterpin을 지어내지 않았다. 실제 journal·coordinator·원자적 정산·집계·재개는 미구현/미연결이다. 원장/run 차이·예약136314880B·원본/lock/분할/모델·QA차단4/학습BLOCKED를 보존한다.

사용자는 외부5개 모델의 API/SDK/code 실행자료와 독립 정확도 검증용 라벨이 별도 준비되지 않았다고 확인했다. 미연결·실행자료 미제공/미구현·독립 검증 라벨 미확보로 관리하고, 이미 있는 약한라벨 학습자료와 구분한다. 외부 의존은 BLOCKED이며 내부 개발은 계속한다. 관련 계약·문서24/45/46/109·gap/SOP·인계서와 이해자료14개(해설·이론·코드·시험·발표·FAQ·INDEX·변경이력)를 함께 갱신했다.

Git은 지정 origin SDSS-Platform/main259b5f3의 게시 확인 상태를 기준으로 이 단위를 별도 커밋/푸시한다. 다음 내부 후보는 실제 journal 지속화·실패 지점별 복구 coordinator 설계/구현이며110의 선언 검사만으로 완료되지 않는다. 전체 프로젝트는 미완료·담당별10분 보고와 지속 개발을 유지한다. 예약ACTIVE와 실제 수집/학습 프로세스는 구분한다.

근거: `evidence/integration/recovery-commit-contract-live-integrity-20261017.json`, `evidence/integration/recovery-commit-contract-independent-review-20261017.json`, `evidence/integration/recovery-commit-contract-external-dependencies-20261017.json`. 최종 문서 감사/파일 snapshot은 `evidence/integration/recovery-commit-contract-closeout-20261017.json`을 따른다.

'''
for name in ['CONTINUOUS_DEVELOPMENT.md','docs/implementation/00_next_session_handoff.md','docs/implementation/workstream_ownership.md']:
 p=ROOT/name;t=p.read_text('utf-8');h,_,b=t.partition('\n');p.write_text(h+'\n\n'+section+b.lstrip('\n'),'utf-8')
p=ROOT/'docs/implementation/110_recovery_commit_contract.md';p.write_text(p.read_text('utf-8')+'\n'+section,'utf-8')
for pattern in ['24_*','45_*','46_*','109_*']:
 for p in (ROOT/'docs/implementation').glob(pattern+'.md'):
  p.write_text(p.read_text('utf-8')+'''\n### 110 후속: commit 단계 선언 검사

[110 구현 문서](110_recovery_commit_contract.md)의 독립 순수 함수가 caller의 단계·세 target SHA·재관측·충돌을 검사한다. 기존 이 문서의 실자료 검사/형식·수집기·예산코드는 바뀌지 않았고 실제 journal/정산·집계/재개 coordinator는 미연결이다. 기존 pending2/예약·원장-run 차이를 해결하거나 exactly-once를 인증한 것이 아니다. 최종 신규14·관련66PASS/1SKIP·독립62PASS/1SKIP·보존 범위는 `evidence/integration/recovery-commit-contract-live-integrity-20261017.json`을 따른다. 해당 내부 선언 검사만 완료이며109의 실제 지속화/복구 수락 조건은 남는다.
''','utf-8')
for name in ['docs/implementation/04_gap_analysis.md','docs/implementation/04_gap_analysis_ml_draft.md','docs/implementation/08_model_type_validation_sops.md']:
 p=ROOT/name;p.write_text(p.read_text('utf-8')+'''\n### 2026-10-18 사용자 확인: 외부 실행기·독립 검증 라벨 미확보

다른5개 모델 API/SDK/실행코드는 별도 제공·준비되지 않아 미연결·실행기 미구현 상태로 관리한다. 독립 정확도 검증용 라벨도 미확보다. 기존 약한라벨 학습자료는 보존하지만 이를 독립 검증 자료나 과학 승인으로 대체하지 않는다. 유형별 validation/recalibration 요건은 계속 별도 검토하며, 제공되지 않은 물리모델 관측자료까지 새로 확보됐다고 가정하지 않는다. 근거: `evidence/integration/recovery-commit-contract-external-dependencies-20261017.json`; 영역별 잔여 수락 조건은 [109 감사](109_area_completion_audit.md)를 따른다. 전체 사업·모델 운영 승인 완료가 아니다.
''','utf-8')
print('110 related contracts/gaps/SOP/ownership/handoff updated; external dependencies recorded.')
