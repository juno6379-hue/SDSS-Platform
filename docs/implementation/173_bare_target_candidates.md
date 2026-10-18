# 173. 6개 주의 로컬 약한 라벨에서 나지 표적 후보 발굴

## 쉬운 설명과 상태

기존에 내려받은 ESRI 연차 토지피복 라벨에서 맨땅(code8)이 많이 든256×256창을 찾았다. 이것은 앞으로 검토할 **표적 위치의 후보표**다. 새 위성영상 수집·나지 학습 패치 확보·공간 독립성·실행 승인 결과가 아니다. 현재 영상이나 미정산 작업과 겹치는 후보도 포함될 수 있다.

상태는 **VERIFIED_REAL_LOCAL_LABEL_BYTES**이며 최종 집중9PASS/5.713초·실제 검색 종료0·별도 최종 검산0.875초/종료0이다. **BLOCKED/PLANNED:** Sentinel 품질·SCL·rawB02·미정산 원장/지원 inventory·기존 영상과의 겹침·실제 source scene 분리·기관/과학 승인·다른 주 실행기 연결이다.

소유 구현은 `scripts/find_bare_targets173.py`, 시험 `tests/test_find_bare_targets173.py`이며 기존157/166/167/170 계약을 바꾸지 않는다. 이 작업자는 수집기·원장·모델·원본·기존 분할·계정·UI pointer·공통 문서·이해자료를 수정하지 않았다.

## 입력 사본과 출처

2026-10-18 **11:37:04 KST** 당시 aggregate1,569행/61,060,064바이트를 `data/bare173-cohort-20261018/source.json`에 원바이트로 고정했다. source SHA는 `6b74cfda9afd8a9ab238406bbf5007e50a2c1162989e2f8953a13a6289f7950c`다. 공식 경계 `data/first-group-boundaries/selected-six.geojson`은482,365바이트, SHA `de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909`다.

최초 scanner는 year의int만 받아 실제 collector의 정확4자리 문자열 연도를 사전거부했다. 이는 기존 자료의 오류가 아니며 새 scanner의 입력 호환 공백이었다. `bare173-actual-20261018.log`와 `bare173-initial-diagnostic-20261018.log`를 보존하고, 정확히2020~2025 문자열만 int로 정규화하도록 수정해 시험을 보강했다. 부분 source/경계 사본을 삭제하거나 덮어쓰지 않았다.

최종 실행은 그 고정 source 사본을 입력으로 `data/bare173-verified-20261018/source.json`에 다시 같은 바이트로 복사하고 경계 사본을 새 디렉터리에 저장했다. 이후 수집기의 mutable aggregate가 바뀌어도 이번 범위는 위 SHA에 한정한다. 최종 CLI의 source 전후 대조는 이 명시 고정 입력을 대상으로 하며 이후 실시간 aggregate 전체의 불변을 주장하지 않는다.

## 검색 방식과 한도

각 행의 `source_window.raw_source_crops['raw-esri_io.tif']`를 모아 path/SHA/주/연도 선언이 일치하는 고유 파일 목록을 만든다. `label_source=esri_io`, label_year=행연도, source URL의/lc연도/와 실제 연차 파일 기간을 대조한다. 원문 URL을 네트워크에서 열지 않는다.

각 raw crop의 실제 원바이트 SHA를 먼저 확인하고 MemoryFile의GTiff로 읽는다. 단일 정수밴드·투영좌표계·10m 북향격자·최대8192×8192만 허용한다. 각256정렬창의 code8픽셀을 실제로 세고256 이상이면 공식 주 경계를 같은 투영계로 옮겨 기하 면적95% 이상 조건을 검사한다. 재표본화나 라벨 값 수정은 없다.

| 고정 상한 | 기준 |
|---|---:|
| 원본 JSON | 64MiB / 최대3,000행 |
| 경계 JSON | 2MiB / 고정6주 |
| raw label 파일 | 최대256개 / 파일당64MiB |
| 읽은 raw payload 합 | 최대768MiB |
| 검사할 정렬256창 | 최대32,768개 |
| proposal 후보 | 최대128개 / JSON2MiB |

crop SHA는 검색 후에도 재검산한다. payload 합은 최초 로딩 바이트 합이며 뒤의 SHA 재검산과 메타데이터 읽기까지 포함한 전체 I/O 측정값은 아니다. 추가 SHA패스도 파일·크기 상한 안에서 실행한다. RSS·총 실행시간·모든 OS I/O의 hard sandbox를 뜻하지 않는다. 한도 초과나 SHA/연차/경계 오류면 부분 출력을 보존하고 exit2로 종료하며 자동 retry·삭제·다운로드하지 않는다.

중복제거 키는 **raw label SHA + local x/y**다. 같은 내용의 파일을 다른 이름으로 복사해도 같은창을 중복 후보로 세지 않는다. 다른 연도/다른 crop SHA의 같은 실제 위치나 겹치는창은 이 키만으로 제거되지 않는다. 따라서50개를 독립된50개 공간으로 세면 안 된다. 전체 슬라이딩창이나256보다 작은 오프셋 탐색도 이번 범위 밖이다.

## 실제 발견 결과

동년raw label **104개**, 압축 payload **17,796,901바이트**, 정렬256창 **6,404개**를 읽었다. 나지256픽셀 이상과 주내95%를 동시에 만족하는 후보는 **50개**, split별 **Train29/Validation15/Test6**이다. SHA/localxy 중복은0개 관측됐다.

| 주 | 고정 split | raw crop | 검사창 | 나지256+·주내95% 후보 | 조건을 통과한 창의 최대 나지 픽셀 |
|---|---|---:|---:|---:|---:|
| 남술라웨시 | train | 20 | 1,088 | 9 | 961 |
| 고론탈로 | train | 14 | 896 | 1 | 271 |
| 남동술라웨시 | train | 19 | 1,216 | 11 | 1,171 |
| 동자바 | train | 14 | 896 | 8 | 620 |
| 반텐 | val | 20 | 1,220 | 15 | 3,910 |
| 서자바 | test | 17 | 1,088 | 6 | 802 |

proposal의 province_summary.maximum_bare_pixels는 주 경계 조건 적용 전 검사창의 최댓값이다. 위 표는 주 경계 조건까지 통과한 후보의 최댓값이므로 두 값을 혼동하지 않는다. 예를 들어 남동술라웨시의 경계 적용 전 최대6,918픽셀은95%주내를 통과한 후보의 최대1,171픽셀과 다르다.

순위는 **칸당28개 계획 부족 셀 우선 → 나지 픽셀 내림차순 → 부족량 내림차순 → 고정 tie-break**다. 총량이나 성능에 따라 split을 바꾸지 않는다. 상위 사례는 남동술라웨시2021의1,112픽셀(셀 부족1), 남동술라웨시2025의840픽셀(부족5), 남동술라웨시2024의814픽셀(부족18), 동자바2025의620픽셀(부족1)이다. 이 부족은 해당고정 source 시점의 저장 적격행 집계이며 신규수집후 현재누계와 다를 수 있다.

## proposal·실행 연결과 한계

결과는 `evidence/integration/bare173-verified-20261018/proposal.json`, SHA **`63368b398ff02382db10213753fb937a7653b925b912c7c5946a857b2152a0ee`**다. receipt와 최종원로그는 같은 디렉터리/`bare173-actual-final-20261018.log`에 있다.

ranked_windows는 기존157가 읽는 year/province/fixed_split/source_crop_path/source_crop_sha256/local_window_xy/declared_weak_label_bare_pixels를 제공하며 native grid·native corners·WGS84 bbox도 기록한다. source_lineage_ref를 포함한 최종157 plan을 자동 생성하거나 승인하지 않는다.

현재157 consumer는 **Banten/val만 허용**한다. train/test 후보35개는 `PLANNED_CONSUMER_NOT_CONNECTED`이며 실행기 일반화는 Root 후속이다. 반텐15개도 자동 실행 가능 수가 아니다. 기존 영상/sourcewindow/SCL/rawB02/미정산 원장·실제 source scene·지원 inventory·동시 claim·공간 겹침은167/170과 후속 가드가 최종 판정한다. 이미 수집한 반텐2020 표적의 주변창도 포함될 수 있으므로 이름이 새롭다는 이유로 새독립 공간으로 승인하지 않는다.

모든 후보는 execution_supported/actual_quality_eligible/scientifically_verified_bare/spatial_independence_verified=false다. 후보 나지 비율은 약한 라벨의 통계이며 독립 현장 정답·검증/시험의 과학적 독립성·모델 승인과 다르다. 이 결과를 적격50패치 증가나 나지 gate 충족으로 표시하면 안 된다.

## 시험과 최종 검산

최종 집중 **9PASS/5.713초·종료0**: 실제 작은 로컬GTiff로256 임계·255거부·연도불일치·stalecropSHA·동일SHA창중복·누적byte/창cap·주경계미달/누락·부족셀 우선순위와train미연결·원파일/PAM보존을 검증했다. 초기 집중9PASS/3.539초 로그도 보존했으며 실제 year문자열 호환 보강 뒤 최종9건을 다시 실행했다. 묶음을 합산하지 않는다.

별도 `bare173-final-verifier-20261018.py`는 proposal/receipt SHA·source/경계 사본·104crop핀을 다시 검산하고50개 후보의 code8픽셀을 전부 실제로 다시 세었다. **0.875초·종료0·불일치0·proposal 전후SHA동일**, 근거는 `bare173-final-verification-20261018.json`과 `bare173-final-verifier-20261018.log`다. 이 독립 검산은 기하 경계 교차면적을 다시 계산하지 않았으며 원래 검색의95% 검사와 구분한다.

Root에 검증된 source/proposal SHA·주/split 통계·실행/공간 한계를 전달한다. 공통 인계·이해자료·UI반영은 Root/해당 담당이 수행한다. 이번 명령은 로컬후보 발굴이므로 새 제품 API·화면을 직접 변경하지 않았고 네트워크/수집/학습/모델/원장 변경0이다.
