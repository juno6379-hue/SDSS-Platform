# 280 — 고론탈로 279 supervisor 독립 정적 리뷰

## 최종 결론과 범위

판정은 **STATIC_REVIEW_COMPLETED / NO_BLOCKING_FINDINGS_IN_REVIEWED_FINAL_REVISION**이다. 최초 준비 코드의 base AOI 선택 키 오류를 전달했고 Root가 실행 전에 수정했다. 수정된 고정 판에서 추가 차단사항은 발견하지 못했다. 실제 요청·승인은 아직 발급되지 않은 준비 단계이며 수집 실행이나 성과 확인 결과가 아니다.

읽은 것은279/270 wrapper와 현재 guard의 순수 설정 파생 코드, 최신 작업 원장이다. 운영 config·source·원장·request/approval JSON·래스터를 읽지 않았고 추가 시험·HTTP·collector·승계 실행·제품 수정도0회다. 이 문서만 새로 작성했다.

## 최초 발견과 실행 전 수정

최초279 준비 SHA는 `4b76351ab00d1721d66ba2a8ac9c9c40bd3976fec5f8fcb93d81e166a5382d1e`였다. 여기서는 다음과 같이 base AOI를 선택했다.

```python
base_aois = [x for x in config['aois'] if x['province_id'] == 'gorontalo']
```

현재 guard는 고정6주 config를 `p=aoi['id']`로 매핑하며 base AOI에 `province_id`가 존재할 것을 요구하지 않는다. 따라서 guard에 유효한 base AOI가 wrapper에서는 KeyError로 사전 차단되는 경로가 있다. 이것은 코드 계약 비교로 발견한 문제이며 실제 운영 실패가 발생한 것은 아니다.

Root 수정 후 최종 SHA는 **`112e36ae376dc64625eab6467e411272a554eccf01512a0cf7a38bb888a12aa2`**다. 최종판은 `x['id']=='gorontalo'`로 선택해 정확히1개인지 확인한다. 이후 새 target AOI를 만들 때 `id=identifier`, `province_id='gorontalo'`, 새 bbox를 넣는 부분은 guard와 같게 유지했다. 수정 소스 지문과 해당 부분을 다시 읽어 확인했다. 원판 코드 수정은 Root만 수행했다.

## 고론탈로 예상 config 독립 파생

279는 과거205의 남동부 술라웨시 template를 재사용하지 않는다. 요청 config_ref의 실제 SHA가 승인된 고정핀과 같은지 확인한 뒤6주 base config를 복사하고, 그 안의 고론탈로 AOI 하나에서 새 config를 파생한다.

정적 비교에서 현재 guard391~406 부근과 다음 값이 같다.

- province 고론탈로, year2025, 공식 split train, 새 공간창 id/bbox
- six bands 순서 blue·green·red·nir·swir16·swir22
- Esri 동년 참조,1024창·명목16패치·64MiB COG·prior budget0
- candidate5/search20·cloud 정렬·cloud60·SCL예비65%·최종유효80%
- label_first·제품 metadata 확인·source crop 보존·재시도0·기존 collection policy
- 정확한 v2 marker `DEFICIT_AOI_BBOX_CONTAINS_V1`

정책을 포함한 최종 직렬화 config에 기존 `json.dumps(config,sort_keys=True)` 해시 규칙을 적용하고, 계산값이 새 approval의 `expected_config_sha256`와 같아야 한다. 실행용 `load_config`의 periods 변환을 먼저 적용해서 producer의 저장 config 지문과 섞지 않는다.

요청 전체 canonical은 schema2·정책·선택 year/id와 source/ledger/config 등 refs를 포함하고 새 job key에 반영된다. wrapper는 selected 정확히1개·고론탈로2025·신규 key를 검사한다. 실제 `candidate_metadata_binding`과 target의 fixed split/year·native footprint·선택 scene 검증은 이후 core의 fresh proof/live guard가 수행한다. wrapper의 예상 config 계산만으로 그 보호가 통과됐다고 주장하지 않는다.

## 유지된 단일 실행·보존·정산 경계

`launch_and_wait` AST는 최종270 wrapper와 완전히 같았다. launch 기록·stdout 일반 오류가 생겨도 `finally`에서 자식 종료를 기다리고 실제 exit를 받는 보완을 유지한다.

새 별도279 approval,271 실제 프로젝트96검증의 status/SHA, 승인된 실행 code pin, 새 launch 부재, OS 중복/잠금 사전 관측을 유지한다. wrapper는 approval에 들어 있는 pin map을 검사하며 필요한35핀의 실제 목록·누락 여부와 발급은 Root의 별도 승인 검토 대상이다. 이번 정적 리뷰는 아직 없는 approval의 실제35지문을 검산한 결과가 아니다.

이전 감사 근거는270의 실제16개 native·적격6개·완료/old rows/pending 보존 상태와 감사 파일 SHA를 요구하도록 바뀌었다. 258의 신규0 감사나 옛 approval을 재사용하지 않는다. 현재 source·원장 승인 SHA와 원 pending2행 내용 전체·예약 합136,314,880바이트, 기존4GiB·회로false·65MiB 예약 여유를 확인하는 순서도 유지한다.

원 pending 원형의 비교 기준을 계속 `deficit235-terminal.pending_before`로 쓰는 것은 처음 두 미정산을 원바이트 내용대로 유지하려는 목적이다. 고론탈로 새 batch의 정산을 과거 pending 환불로 바꾸지 않는다.

원 request를 exclusive로 기록한 뒤 source·원장 바이트를 다시 확인하고, 기존 `collect_deficit_guarded.py --execute`를 호출한다. 이 core가 실제 `O_EXCL` lock 안에서 fresh200 inventory·target support·물리3000·고정 scene/split·SCL/B02·최종품질·실측 정산을 다시 수행한다. OS/잠금 사전 관측 자체는 원자 잠금의 대체가 아니다.

wrapper는 한 batch·최대16과 시작/종료 증거를 기록할 뿐 worker 성과·바이트 측정을 만들어내거나 원장을 직접 정산하지 않는다. 시작은 fresh preflight 상태, 종료도 settlement audit 필요 상태로 남긴다. 실제 결과는 terminal·worker·원장·잠금/OS 종료와 신규분 단일 감사로 확인해야 한다.

## 다음 조건과 미검증 사항

Root는278 새 로컬 계획 완료 뒤 현재 고정 source·원장·6개 ref·정확한 예상 config·필수 실행핀을 대조하여 새로운279 request/approval을 별도로 발급해야 한다. 로컬 후보는 실수집 승인이나 실제 품질 통과 근거가 아니다. 실provider/v2선별·고론탈로 영상·나지·적격 확보·예산 정산은 이 리뷰에서 미검증이다.

공유 runtime·원본·원장·모델·split·profile·pointer는 리뷰 담당이 수정하지 않았다. 이 내부 준비 문서는 UI 변경이 없으며, 실제 수집 뒤에는 Root가 신규 단일 native/QA·안전 게시·실API/브라우저·공통 이해자료 인계를 별도로 완료해야 한다.
