# 304 신규분 native runner 독립 정적 검토

## 결론과 지문

상태는 **IMPLEMENTED_UNVERIFIED — 동결 준비 코드 정적 검토**다.299 검증 원판과307의 새304 runner·최소diff·freeze·문서를 읽었고 추가 실행 차단 결함을 발견하지 못했다. 운영 원본·원장·이미지 읽기,HTTP·실native·새 시험·collector 실행은0이며 코드 편집0이다. 실제304 관측·단일 감사 소유는 ml_pipeline307 담당이다. 이 검토가 별도 감사나 Root GO를 대신하지 않는다.

freeze evidence/integration/deficit307-native-preparation-freeze-20261018.json SHA7aa69e84b0ead75c825228d0f2de93f5723dced81e3a728ae66f0ba405e88ba1의4파일 byte/SHA가 일치했다. runner36a6cf451a86e0b3f0f963e689f732b4228f73d03f21e20687a08582ec141e8f,299 원판사본a8a9ed9fcdbb0fafb60c3c71f028f188b6f855ccc5f7c6768a328c327da608ca,diff009fd49a2a28a07258db7553169186739cfd9ed5bbe2c8112d1a3ef81769e504,doc30778e5809a074bc4bd9a96de2701b58fcc8d2011d3a54f027db2697cb8fdfa5fc2를 확인했다.165 helper 코드도 freeze의ba4da0b03bd19a0d327200a49eb5c75b28a1f42620be43c84826092c50c661ba와 맞았다. 이는 정적 코드 지문 확인이며 제품 시험이나 기존 native 재실행이 아니다.

## 최소 변경과 실행 전 경계

299 대비 변경은304 경로·GO status·새 request/key/config·동자바2025/train·old1763행에 한정된다. 정확한 request는981abcd9b78b6eaa94dcb48a2f2bc62346ac939967076490b41c0c10e03f0987,key는 center1024-east_java-2025-981abcd9b78b-9c40f177,config는31044c97e5dd1cf84648eec174975eacd9b5f8e1eacfcbf50e355bc0bb7d657a다. 고론탈로 원판의 CRS를 하드코딩하지 않으며 실제 파일 CRS/affine/grid를 읽어 비교한다. EPSG 문자열 literal이 없는 것도 확인했다.

Root GO는 GO_304_BOUNDED_NEW_MAX16_NATIVE_AUDIT와 collector 종료·정산 및 중복collector/audit 없음의 정확히 true 선언,실제 source bytes의 정수/128MiB 상한,신규수0~16 정수,helper/runner/launch/terminal/source/ledger SHA를 요구한다. terminal은 종료0/lock false여야 하고 실제 lock 부재도 검사한다. 이전 고정사본과 원1763행 prefix/history를 비교하며 source bytes/SHA와 신규수를 GO와 맞춘다. 실제 OS 종료·감사 배타성·원본 hold는 Root 운영 확인에 의존한다. GO 선언만으로 runner가 OS를 감시하거나 lock을 잡는 것은 아니다.

## 양수 신규분 검사 계약

양수1~16개만165 helper를 정확히 한 번 호출한다. 정적 callsite도1개다. 임시 adapter에 실제 prefix count/canonical 값을 넣으며 원launch를 바꾸지 않는다. 기존 자료는 메타데이터 prefix 비교이고 옛 래스터 native를 다시 수행하지 않는다. 새 최대48개 image/label/quality의 실제 SHA·256grid·6밴드·유효/주내 지원 mask·histogram/적격은165 제품이 검사한다. helper 완료·검사수·외부 문서 안정·lock 부재 뒤만 추가 trace를 수행한다. 실제 파일 수와 소요시간은 실행 전 확정하지 않는다.

trace는 고정 STAC/선택 raw B02·raw Esri·source image/quality와 새 patch image로 제한한다. 관측시각·장면·연도2025·collection·B02 URL·metadata bbox를 검사한다. GTiff MemoryFile과 네트워크 비활성 조건에서 raw B02와1024²×6 source 첫밴드의 실배열·CRS/affine/shape를 확인하고,10/-10m 회전0 grid와 각256부분창 affine/첫밴드를 대조한다. 실제 동자바 투영 CRS를 이전 고론 CRS와 같다고 선언하지 않는다. label_year는2025에 결속하지만 독립 현장 정답이나 약라벨 정확도를 승인하지 않는다.

나지는 raw Esri를 실제1024 B02 grid에 nearest 정렬한 값→source quality만 적용한 값→최종 지원 label histogram→적격패치의 나지/256이상 기여로 구분한다. 행 sample_class_coverage는165 실제 label histogram 검산의 뒷받침을 받는다. source quality와 최종 주경계/라벨지원/전체밴드 유효 mask는 다르며,목표1024 결과를2048 전체 라벨이나 주 전체로 일반화하지 않는다.

새 batch의 tif 집합은 신규행의3참조와 정확히 같아야 한다. trace 파일 수에는 이미 제품이 검사한 새 patch image가 중복되므로 단순 합을 고유 파일 수로 발표하지 않는다. metadata filter 저장요약의 정책/request/source·최대20인덱스/rank·개수·최대5선택풀과 선택 STAC bbox를 확인하지만 모든 원격 후보 원문 재생은 아니다. 기존 pending은 launch 원형과 같아야 하고165가 config·worker/window-state·원장 COG+metadata 계상을 대조한다. finalize/settle/publish는 해당key 각1개,최종 source/ledger/launch와 trace 재해시가 안정돼야 성공한다. 모든 추가 검사가 끝나야 native_validation_complete=true가 된다.

## 0패치·부분 실패·인계

0행 분기는 helper0/native false/exit2와 ZERO_PATCH_REQUIRES_SEPARATE_ROOT_AUDIT를 유지한다. 양수 분기 뒤에 있는 pending/config/정산/출처 검사를 완료한 것으로 꾸미지 않는다.0패치의 종료·실정산·원pending·탈락 사유는 별도 Root 좁은 감사가 필요하다. 일부 실패는 exclusive JSON/log/stderr를 보존하고 자동 재시도·상한 증가·이전 감사를 반복하지 않는다. 순차 두 읽기 안정은 원자 snapshot이 아니다.

ml307은 collector 실제 종료·정산·OS/lock 해제와 Root source hold·별도 GO 뒤 단일 감사만 실행한다. 이 정적 문서에서는 실제 패치·적격·나지·셀 부족·예산을 확정하지 않는다. 완료 후 Root가 최종 고정 source QA/게시/API/UI·문서/이해자료를 각각 실제 근거로 인계하며,셀 최소량 충족을 나지 준비·훈련 승인·전체 프로젝트 완료로 바꾸지 않는다.
