# 268 공유 적용 및 271 실제 프로젝트 검증

상태: TESTED_SYNTHETIC(실제 공유 코드의 합성/격리 시험), 운영 수집 및 실제 provider 호환은 IMPLEMENTED_UNVERIFIED.

265 명시 v2 metadata 선별은 marker와 callback 양방향 결속을 네트워크 전에 검증한다. v1/default/부모256 경로는 유지한다. metadata fullAOI 포함은 실제 B02 픽셀 coverage나 품질의 증거가 아니다. 기존 cloud 안정정렬 후 최대20 metadata에서 포함 조건을 적용하고 상위5만 SCL 검사하며, 추가 page/refill/자동재시도하지 않는다. 응답6–20이 필터 뒤 새 상위5에 들어갈 수 있는 명시 선별정책 변경이다. 기존 SCL지원 겹침·scene/window/split·B02 정렬·품질·예산/정산 보호는 유지된다.

267 독립 정적리뷰 후 Root268이 runtime3/test6만 baseline 원바이트 archive와 지문 대조 뒤 적용했다. 최초 실제96검사 중95개 통과·1개 실패했다. 부모 sys.path 설정이 자식 환경에 상속되지 않아 import 격리 시험이 app 모듈을 찾지 못한 Root 시험환경 오류다. selection268-application-root-20261018.json과 원 log는 실패 상태 그대로 보존한다. 이를 제품 결함 수정 또는 최초 시험 통과로 바꾸지 않는다.

Root271은 제품/시험 소스를 바꾸지 않고 child PYTHONPATH를 workspace/.runtime/backend/scripts/tests에 명시한 별도 검증이다. 동일7모듈96개 exit0, wall141.469초. 운영 source/ledger/candidate pointer/bare pointer/profile 5핀 및 적용9파일이 전후 동일하다. 결과 JSON SHA24b837029aafa7413a5a31b56ddbf9cdab91a7a6a53155e45b3608820aaaef9d, log SHAe3fd236d50336cc5378b301e5f2c6c43af95edeb0cd0f524c11e6e8c41dc4ddf. 격리96개와 실제동일96개는 중복 시험군이므로192개로 합산하지 않는다.

내부 collector CLI 경로 변경으로 API/프론트 상태계약은 바뀌지 않아 서버 재시작/UI 수정은 필요없다. 기존 실제261 UI의 source 시점 차이 경고를 유지하며 신규 수집 결과가 생길 때 실API/브라우저를 다시 확인한다. 원본1358/셀부족21/후보1342/나지3차단·학습false/잔여1893156314B/oldpending136314880B는 불변이다. 다른5모델/독립정답 미확보와 전체개발 미완료도 유지한다.

다음: 269 단1 로컬계획,272 새v2 supervisor 독립 정적리뷰,Root fresh source/ledger/OS/lock 확인과 새 요청·configSHA 승인 후 소단위 실행한다. 이 시험 완료 자체는 collector 실행/학습/운영 승인 근거가 아니다. 별도 understanding_agent가 설명·발표대본·FAQ·INDEX·이력을 갱신한다.
