# 10:55 보고 주기 — 전체 수량 목표와 남은 품질·지역 기준

## 5차 수집 독립 검산

현재1512물리/1212적격/300적격 외다.5차 동자바2021 두 작업 중 하나는 COG 범위 오류로 패치0, 다른 하나는16개 생성·16개 적격이다. 전체1200 목표 부족은0이 됐지만 주×연도 최소28 기준 부족은85다. 주별 부족은 남동술라웨시45·동자바18·고론탈로17·반텐5, 남술라웨시/서자바0이다. 우선수집 시작1400/1122 대비112개 생성·90개 적격이며 셀 부족151→85다. 서로 다른 부족 지표를 합치거나 총량 달성을 학습 승인으로 해석하지 않는다.

Root는 launch 이전 행의 canonical SHA, 기존pending2/136314880B 전행, 두 batch settled를 직접 대조하고 manifest/ledger 두 번 읽기 바이트가 같음을 확인했다. 이번 계상20950392B·5차 완료 기준 잔여2188636799B,429false·lock없음이다. 관측은 원장/저장 라벨 집계이며 native QA나 OS 원자 snapshot이 아니다. 새 나지 선언은6픽셀이고 기여 패치 증가는0이다. 현재 나지 기여 패치는train0/val1/test0, 각 분할 최소5 미달이다. 기존 후보1125는 고정1432행 기준으로 여전히4차단·학습false다.

## 162 새 기능과 검증

신규 `SceneClaimRegistry`는 한 프로세스 안에서 같은 객체를 공유하는 worker의 선언 이력 확인·격리·사용 기록을 하나의 lock 안에서 처리한다. 다른 split 이력이나 다른 owner의 중복 scene을 거부하고, 같은 owner/scene/split 재요청만 무증가로 반환한다. 신규 scene cap도 같은 lock에서 적용한다. 자동 release/TTL/환불과 다른 객체·프로세스 간 보호는 없다. 파일·네트워크·collector·운영 원장에는 연결하지 않았다.

집중10 PASS/0.132초, 독립10 PASS/0.058초, Root 관련162/160/157 합계28 PASS/9.204초/exit0이다. 시험 집합은 중복이므로 합산하지 않는다. 같은 unseen scene을 train/val로 동시에 요청하는 Barrier 경쟁, cap 경쟁, 입력/반환 오염·예외 복구 등을 검사했다.

Root 실제 관측은1512행의 선언을 축약한94개 고유 scene/95개 scene-split 기록으로 별도 private 메모리 객체를 만든 것이다. 기존 여러 split scene1개를 세 split 모두에서 quarantine으로 거부하고, 단일 split의 다른 split 요청도 거부했다. 올바른 split의 private claim1개만 남았고 원본 SHA는 불변이다. 이력은 caller 선언이며 sourcepin/inventorycomplete/pending/footprint/alias/quality/execution은 계속false다. 전체 source report나 운영 worker를 검사·수정한 것은 아니다.

새 코드·시험·구현/계약/사용법·이해자료·증거10파일은 별도 로컬커밋4901fcc612d21fc7bd9f7461fc8c037329140a92 / codex/targeted-scene-claims-20261018에 보관했다. 기반8c58444이므로160도 포함한다. 공유 HEAD/index/작업파일 보존·push0이다. 내부 helper여서 새 API/UI 연결과 브라우저 검증이 필요한 제품 흐름 변경은 없다. 설명·대본·FAQ는 docs/understanding/162_TARGETED_SCENE_CLAIMS.md에 별도 이해 담당이 완료했다.

## 현재 실행·다음 작업

기존 담당이11:00 관측에서 동자바2024 두 작업의6차를 실행 중이다(wrapper8688/collector30492, launch01:59:08UTC).5차 완료1212와 새시작을 합치지 않는다. API36400/Vite34484 실행과 다른 개발 채팅active,10분 예약ACTIVE를 각각 확인한다.147 마감 범위와 기존 중단의 직접 원인 미확정·예약 보호는 유지한다.

다음 표적 실행 연결에는 aggregate 밖 source report·pending·보조 footprint까지의 고정 inventory, 실제 후보/160 crop 정렬, 검증된 단일 coordinator 공유 registry, 배타 출력·예산/정산·최종 품질이 필요하다.160·162의 로컬 성공을 전체 보호 체계 완성이나 실제 표적수집으로 보고하지 않는다. 남은 셀85 수집과 나지 균형·독립 검증도 계속된다.

근거: heartbeat-1055-round5-audit-20261018.py/json, priority-collection-round5-final-20261018.json, targeted-scene-claims-agent/root-related log·independent/real-history/git-isolation JSON, priority-collection-round6-launch-20261018.json.
