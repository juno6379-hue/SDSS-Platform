# 297 신규분 native 감사 준비 runner 독립 정적 검토

## 결론과 고정판

상태는 **IMPLEMENTED_UNVERIFIED — 준비 코드의 정적 검토**다. 최종 runner와285 긍정 감사 원판의 diff,165 제품 helper의 계약을 읽고 추가 실행 차단 결함을 발견하지 못했다. 실제 collector 관측과 native 감사 소유는299 담당에게 있으며 이 검토 담당자는 운영 원본·원장·래스터 읽기, HTTP·실native·새 시험·collector 실행을 하지 않았다. 기존285 감사 및 완료290 QA도 반복하지 않았다. 코드 편집0이며 이 문서만 새로 작성한다.

freeze evidence/integration/deficit299-native-preparation-freeze-20261018.json의 SHA는0922c1704c9f595f8f9df9e537e1a4e006e29af5b5342a1515a6cc074c9af098다. 그4개 파일 byte/SHA가 모두 일치했다.297 runner SHAa8a9ed9fcdbb0fafb60c3c71f028f188b6f855ccc5f7c6768a328c327da608ca,원285 사본479dff23370e2db3fd58918e456fc9b263ad614afd3b69baa1f252a66011a4cb,diff e23333cc268f8a9cf41a60fab2cfd0440e5ae2188880d4a268213a96ee2bd9fe,doc299 abf457fc0179cbae9617f3d2e4ab943481e01b175f2c2a17c5b885b8cb4fd9df를 확인했다. 실제165 helper 코드 SHAba4da0b03bd19a0d327200a49eb5c75b28a1f42620be43c84826092c50c661ba도 freeze와 일치했다.

## GO와 신규 범위

runner는 GO_297_BOUNDED_NEW_MAX16_NATIVE_AUDIT, collector 종료·정산 및 중복 collector/audit 없음의 정확히 true 선언,128MiB 이하 source의 실제 byte 정수,0~16의 예상 신규 행수 정수를 요구한다. runner/helper/launch/terminal/source/ledger SHA를 별도로 확인한다.297 canonical request e9ebe6f7dcbb986a853ed1749e97c4feafcacde1702c1937c946d7f6e2602487,고론2025/train,key center1024-gorontalo-2025-e9ebe6f7dcbb-73cbb072,config9d3618a258fbfd272c227cde90bffd3fc98fac2fd574864a69349a5825e41f71에 고정한다. 실행 terminal 종료0·lock false 및 실제 lock 부재도 확인한다.

현재 source의 실제 byte/SHA와 시작 고정사본·launch source핀을 대조하고,기존1747행 prefix와 historical_noneligible_patches를 정확히 비교한다. 신규수는 GO 정수와 같아야 한다.1~16개 양수 분기에서만 batch prefix/fixed split/config·원pending 보존을 확인하고165 helper를 호출한다. audit_increment의 정적 callsite는1개이며 반복·자동 재시도 경로는 없다. 원launch는 바꾸지 않고 임시 adapter에 실제 old count/canonical prefix만 추가한다. source128MiB·기존 helper cap을 유지하며 기존 자료 전체 raster 재감사로 확장하지 않는다.

GO의 OS/중복 없음은 Root의 실제 확인과 원본 hold 선언에 의존한다. runner가 OS를 독립 감시하거나 collector lock을 획득하는 것은 아니다. 고정 helper를 import한 뒤 실행 중 SHA를 비교하는 구조는 기존 준비판의 trusted code/Root hold를 전제로 하므로 실행 도중 코드 변경을 허용하지 않는다. 감사 완료의 두 파일 읽기는 순차 관측이며 원자 snapshot이 아니다.

## 양수 신규분의 실제 검사 계약

165가 새 최대16패치 image/label/quality의 SHA·GTiff·256grid·6밴드 및 지원 mask·80% 유효/95% 주내·histogram·적격·나지 실픽셀을 검사한다. 원행은 메타데이터 prefix만 검산하며 옛 래스터를 다시 읽지 않는다. helper의 native_validation_complete와 검사 패치 수,외부 문서 변경 없음,lock 부재를 확인한 후에만 추적 검사를 계속한다.

추적은 선택 STAC·고정 raw B02/Esri·source image/quality와 신규 patch image로 제한한다. STAC id/datetime/관측연도2025·collection·AOI bbox 포함·B02 source URL 결속을 검사한다. 고정바이트 MemoryFile/GTiff와 PROJ_NETWORK=OFF를 사용하며 raw B02와 source 첫밴드 실제배열·CRS/affine/shape를 대조한다.1024²×6·10/-10m·회전0 source에 대한 각256부분창 affine 및 첫밴드 일치를 확인한다. 동년 라벨은 row label_year와2025 결속이며 독립 현장 정답의 진실성을 승인하지 않는다.

나지는 raw Esri를 목표1024 B02 grid에 nearest 정렬한 값,source quality만 적용한 값,최종 지원 label histogram,적격패치에 한정한 값과256픽셀 이상 기여패치를 나눠 기록한다. 최종 histogram의 행 metadata는165의 실제 label 재계수 일치 검증에 근거한다. source quality와 최종 province/전체밴드/라벨 유효 mask는 서로 다르며,목표범위 결과를2048 확대라벨 전체·주 전체로 일반화하지 않는다.

새 batch patch leaf의 tif가 신규행3참조와 정확히 같아야 하며 최대48개다. 추가 trace hash 중 신규 patch image는 제품검사와 중복되므로 제품52개와 trace 수를 단순 합산한 고유 파일 수라고 보고하지 않는다. metadata summary는 정책/request/source 결속·최대20 입력·rank/index·포함/제외 합·최대5 풀과 URL 미포함,선택 STAC bbox를 확인한다. 모든 원격 후보 원문을 다시 검색·검산한 결과는 아니다.

실측 COG+metadata 합과 settled 원장값은165에서 교차검사하고 runner에서도 합계를 확인한다. 최종화 시도·settle·publish 목록은 해당key 각1개여야 한다. source/ledger/launch 두 읽기 안정과 고정 trace 재해시를 확인한 뒤에만 native_validation_complete=true로 성공한다. 중간 실패는 JSON/log/stderr를 exclusive 보존하고 exit2이며 자동 재시도하지 않는다.

## 0패치와 보고의 한계

신규0이면 helper를 부르기 전에 ZERO_PATCH_REQUIRES_SEPARATE_ROOT_AUDIT로 반환한다. native_helper_invocations=0,native_validation_complete=false,exit2이며 성공 native로 위장하지 않는다. 이 분기는 원행·history/source핀은 비교하지만 양수 분기의 pending/config/정산/출처 후검사까지 완료하지 않는다. 따라서0패치의 종료·실정산·원pending·탈락 원인 감사는 별도 Root 좁은 감사 승인과 실제 근거가 필요하다. 이 runner 실행을0패치 감사 성공으로 보고하거나 동일 runner를 자동 재실행하지 않는다.

현재297 수집의 성과·최종 source/ledger 지문은 이 정적 리뷰가 확정하지 않는다.299 담당은 terminal/실정산/OS/lock 종료와 Root 고정·별도 GO를 받은 후만 단일 감사를 실행한다. 실제 적격·셀 부족·나지·예산은 완료 산출물로 보고하고,Root의 후속 후보 QA/게시/API/UI·이해자료와 구별한다. 학습·독립 정확도·전체 프로젝트 완료는 승인하지 않는다.
