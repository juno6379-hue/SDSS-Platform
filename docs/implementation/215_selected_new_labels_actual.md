# 215 — 209 신규 확대 라벨 2개 선택 탐색 실제 결과

상태: **VERIFIED_REAL — 저장 라벨의 제한된 로컬 탐색 완료**. 새 영상 수집·실품질 승인·학습은 수행하지 않았다. Root가 2026-10-18 14:34 KST 한 번 실행했다. 문서 담당은 저장 JSON·실행기·로그만 읽었고 배열 재검사와 탐색 재실행은 0회다.

## 무엇을 확인했나

209에서 저장한 남동술라웨시 2021년·2024년 확대 Esri 라벨 두 개에서 나지 밀집 창을 찾았다. 기존 중심 영상 밖을 포함하는 저장 확대 라벨을 활용했으므로 새 다운로드는 필요하지 않았다. 다른 다섯 주의 라벨은 읽지 않았다. 전체 manifest와 여섯 주 경계 검증을 여섯 주 탐색으로 표현하지 않는다.

214의 `discover(..., label_refs=...)`에 실제 manifest 행에 존재하는 두 경로와 SHA만 지정했다. 같은 주의 참조 가능 라벨 25개 중 23개는 명시적으로 제외했다. 전체 source 1,699행의 coverage 분모는 유지했다. 두 라벨의 고정 분할은 train이다.

| 항목 | 저장된 실제 결과 |
|---|---:|
| 실행 시간 | 4.860초 |
| 읽은 라벨 | 2개 |
| 로컬 파일 읽기 합계 | 295,070바이트 |
| 평가한 256×256 창 | 450개 |
| 창 이동 간격 | 128픽셀 |
| 어느 창에서든 가장 많은 나지 선언 | 10픽셀 |
| 나지 256픽셀 이상 창 | 0개 |
| 나지·주내 영역 조건을 함께 충족한 창 | 0개 |
| 최종 순위 후보 | 0개 |
| 원격 요청 / 새 영상 수집 / 학습 | 모두 0 |

명시 상한은 파일 2개·합계 16MiB·창 512개·후보 50개였다. 실행기는 두 선택 참조 및 운영 원본/원장 해시를 검산하고 새 결과 폴더에만 proposal을 기록했다. 위 바이트는 저장 라벨 읽기량이며 원격 전송량이 아니다.

최대 나지 선언 10픽셀은 기존 256픽셀 기준에 못 미치므로 바로 넘길 새 표적은 없다. 기준을 완화하거나 나지를 생성하지 않았다. 남동술라웨시 전체에 나지가 없다는 증명은 아니며, 실제 Sentinel-2 구름·최종 유효 픽셀 검증도 아니다. 적격 나지 기여와 212 부족 산술은 이 탐색으로 개선되지 않았다.

## 고정 입력과 증거

실행 당시 current source와 고정 사본 SHA는 `80eef2d274942c7a7f9bf8ee2483af070a729060d84ceb1a19baacb52ae4976a`, 원장은 `6e9e27b0ba9e4d222f9fde6b1e22f2adfd604701163d8e2c4653617c47af02fc`다. 실행기 기록상 전후 동일하며 문서 담당이 운영 원장을 재독하지 않았다.

선택 참조는 다음 source 폴더의 `raw-esri_io.tif`다.

- 2021: `data/first-group-training-esri-v1/sources/center1024-southeast_sulawesi-2021-c28a69f1093e-2ce2bf2f/centers182-southeast_sulawesi-6ad43e34c63c-2021/`, SHA `1155376b5a36e1cf6680e332aa8bde47882ab3b71a446ffcf39f93a9f9213c2d`.
- 2024: `data/first-group-training-esri-v1/sources/center1024-southeast_sulawesi-2024-c28a69f1093e-7158f440/centers182-southeast_sulawesi-bd99d40b7b68-2024/`, SHA `2bdcc491f2859c7c2c44918ba026b4b66206fba947fe02923578657f8b6b5585`.

실제 증거: [Root 결과 JSON](../../evidence/integration/bare215-new209-result-root-20261018.json), [단일 실행기](../../evidence/integration/bare215-new209-labels-root-20261018.py), [stdout 로그](../../evidence/integration/bare215-new209-labels-root-20261018.log), [검토 코드핀](../../evidence/integration/bare215-reviewed-code-pins-root-20261018.json), [고정 proposal](../../data/bare215-new209-20261018/proposal.json). 문서 작성 시 proposal JSON 바이트의 SHA만 재검산했고 `206fef366b42fe196749d06eea2c52c41755af8bc03ec2cc92b882ab501c0ff8` 일치를 확인했다.

## 다음 단계의 경계

[213 설계](213_dense_bare_discovery_contract.md)의 저비용 우선 경로 중 이번 두 라벨 경로는 후보 0으로 끝났다. 다른 위치의 원격 라벨 탐색은 별도 PLANNED 작업이다. Root의 명시 seed·고정 요청·동일 예산/계측·실측 정산과 SURVEY 전용 출처가 필요하다. 라벨만 받은 자료를 RGB 완성 행이나 기존 173 manifest 행으로 위장하지 않는다. 새 후보 발견 뒤에도 175/170의 명시 호환 계약 및 실제 Sentinel-2 품질·겹침·분할 검사가 필요하다.

이번 단위는 내부 결과 문서화다. 제품 코드·UI/API·브라우저 변경은 없으며 전체 개발 완료나 나지 gate 통과가 아니다. Root가 이해담당에게 실제 탐색 0후보와 원격 후속 PLANNED를 구분해 인계한다.
