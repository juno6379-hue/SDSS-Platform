# 미정산 예약·부분 영상 지원범위 검사 계약 (167)

`backend/app/data/targeted_inventory.py`의 `inspect_targeted_inventory(project_root, request)`는 고정 manifest/ledger 참조와 표적 native 사각형을 받아 로컬 수집 자산을 검사한다. 실행 승인 함수가 아니며 HTTP·원장·lock·파일 수정은 하지 않는다.

현재 collection sources 디렉터리와 원장에 기록된 과거 batch의 report 디렉터리를 링크 추적 없이 열거한다. 각 원본/이력 행의 source_window도 빠뜨리지 않는다. 미정산 batch는 설정 canonical SHA 일치와 실제 raw-B02 파일을 요구한다. 부족하거나 파일 목록·원장·원본 지문이 검사 중 변하면 차단한다. 원본 라벨(raw-esri_io 등)은 목록에 기록하되 기존 영상의 중복 영역으로 취급하지 않는다. 넓은 참조라벨은 새 표적의 라벨을 찾는 데 재사용할 수 있지만 영상·SCL·부분 밴드는 중복 보호에 포함된다.

각 지원 파일을 실제 바이트 SHA와 내부 GTiff header로 검사한다. 같은 CRS는 실제 사각형의 양성 교차를 검사하며 다른 CRS는1024분할 densified envelope와 보수적 여유1m(경위도1e-5도)를 적용한다. 수학적 모든 투영의 연속영역 증명이나 과학적 독립성 인증은 아니다. 고정된 열거·파일 읽기는 순차 관측이며 OS 원자 스냅샷도 아니다. 파일 수/바이트 상한은 전체 검사를 생략하는 성공 경로가 아니라 차단 조건이다.

입력의 정확한 키는 `manifest_ref`, `ledger_ref`, `target`이며 참조는 프로젝트 data 아래 상대경로·SHA, target은 projected CRS·축 정렬4개 corners다. 결과는 검사한 자산·라벨 제외 목록·미정산 예약 전액·겹침·issue를 포함한다. `LOCAL_INVENTORY_VERIFIED_EXECUTION_BLOCKED`에서도 `execution_supported=false`, `scientific_independence_proven=false`, `training_ready=false`다. 기존157 지역/연도/픽셀/영상검사와166 출력예약/claim, 실제선택영상/예산/429/정산이 함께 연결돼야 실제 표적 집행을 판단할 수 있다.

시험은 실제 합성 GTiff와 미정산 설정을 사용했다. 12개가7.415초에 통과했다. 라벨 재사용, 목록에 없는 SCL 겹침, 비적격/이력 영상, 누락 B02, 설정/원본 SHA 변조, 파일/바이트 한도, 링크 별칭, 검사 중 새 파일·원장 변경, 과거 원장 source 디렉터리 포함을 확인했다. 최초11개6.735초 로그도 보존했다. 근거: `evidence/integration/targeted-inventory-root-final-20261018.log`.

내부 가드이므로 단독 UI 버튼이나 완료 표시를 추가하지 않는다. 실제 collector 통합·현장 자료 검사와 후속 UI 상태 인계는 별도 완료 증거가 필요하다. 기존 데이터와 원장·모델·분할은 보존한다.

## 2026-10-18 최종 보강 및 실제 자료 확인

최종 시험은 `targeted-inventory-root-final2-20261018.log`의 **13 PASS / 5.926초**다. 실제 원본에는 EPSG:4326 지원 영상도 있어 최초 실제 검사에서는 RASTER_GRID_INVALID로 차단됐다(`targeted-inventory-real-20261018.json`,118.005초). 경위도 내부 grid 검사와 WorldCover 참조라벨 구분을 보강하고, 최초 실패 증거를 보존했다. target 입력의 native 투영 좌표 요구와 지원 파일의 경위도 CRS 허용은 서로 다른 범위다.

후속170의 로컬 preflight에서는 실제 지원 자산 **1,152개**를 검사하고 `LOCAL_DISPATCH_INPUTS_VERIFIED`를 반환했다(`targeted170-dryrun-20261018.log`). 이 실행은 HTTP·수집 없이 입력과 겹침을 검사한 것이다. 실제 수집 결과 및 예외 정산·물리 상한 보완은170/171의 별도 증거로 판단한다. 이 helper의 execution_supported=false는 유지한다.
