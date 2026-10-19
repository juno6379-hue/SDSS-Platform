# 266 — 249 실패 작업의 저장 약라벨 1개 나지 미리보기

상태: **VERIFIED_REAL_LOCAL_SAVED_LABEL_ZERO_BARE / EXECUTION_UNAPPROVED**. Root GO 뒤 이 저장 라벨 한 개를 실제 검사했다. 원격 수집과 학습 승인은 모두 false다. 266 번호를 문서/evidence에서 검색해 기존 충돌이 없음을 확인했다. 아래 준비 계약과 실제 결과를 구분한다.

## 목적과 입력

249는 예비 SCL을 통과한 뒤 B02 창 정렬에서 차단되어 등록할 patch를 만들지 못했다. 그러나 label-first 단계에서 확대 Esri 약라벨 한 개는 이미 저장했다. 이 파일 안에 나지 표적이 있는지만 아주 좁게 확인한다. 실패한 작업을 성공한 RGB 자료로 바꾸거나 aggregate에 가짜 행을 추가하지 않는다.

고정 준비 근거는 `evidence/integration/bare266-prepared-metadata-20261018.json` SHA `3e0343f730a2e475eb43b4f89547f91730686a3f6e029f7a5eb7e5fb610714fb`다. report·STAC·raw-label file manifest·제품 XML·config·249 완료 감사의 파일별 SHA를 포함한다. 준비 단계에서는 라벨의 헤더와 배열을 열지 않았다.

라벨 경로는 프로젝트 루트 아래 `data/first-group-training-esri-v1/sources/center1024-southeast_sulawesi-2024-7fdcb4d284c6-991dcd39/centers182-southeast_sulawesi-f5fa8f8ccc4f-2024/raw-esri_io.tif`다. 저장 SHA는 `10180e532308d221ac26e9c6db24e288b0b9ac79db404c6f3dfccd2f10e23097`, 크기 97,234B, 선언 격자는 2048×2048·uint8·EPSG:32751·10m다. 남동 술라웨시/2024/**train**이다. 초기 Root 메시지의 test 표기는 코드의 고정 split을 확인한 즉시 train으로 정정했다.

동년 약라벨 출처는 `https://lulctimeseries.blob.core.windows.net/lulctimeseriesv003/lc2024/51M_20240101-20241231.tif`다. 저장 manifest의 `status=registered`는 개별 파일 catalog 상태이며 성공 patch 등록이나 학습 승인 증거가 아니다. 선택 STAC는 `S2B_MSIL2A_20240813T021349_R060_T51MUR_20240813T055551`, 제품 XML의 선언 URI는 `S2B_MSIL2A_20240813T021349_N0511_R060_T51MUR_20240813T055551.SAFE`다. XML 시작시각과 저장 STAC 시각은 2024-08-13T02:13:49.024Z에 대응한다. 별도 모든 STAC/product 검증 계약이 통과했다고 주장하지 않는다.

215 저장 검색 결과의 라벨 SHA 두 개(`1155376b…c2d`, `2bdcc491…5585`), 229 결과의 한 개(`63316ce6…bcc4`)와 이 라벨의 경로/SHA가 다르다. 해당 결과 JSON만 대조했으며 215/229 라벨은 다시 열지 않는다. Root가 확인한 249 감사도 배열 검사를 수행하지 않았으므로 이번은 이 저장 파일 한 개의 첫 독립 preview 배열 검산 범위다. 전체 과거 모든 비기록 접근을 증명하는 포렌식 주장은 아니다.

## 독립 runner와 GO 계약

`evidence/integration/bare266-label-preview-20261018.py`만 새로 작성했다. main 제품은 변경하지 않았다. 173 `discover`는 등록 manifest row의 동년 label lineage에 정확히 존재하는 ref만 허용하므로 이 실패 batch를 그 API에 위장 투입하지 않는다. 독립 evidence 결과만 낸다.

GO JSON의 정확한 키/값은 아래와 같다. Root가 runner 최종 SHA를 넣어 새 파일로 작성하고 SHA를 전달한다. runner는 다른 키·값·타입을 허용하지 않는다.

```json
{
  "schema_version": 1,
  "kind": "BARE266_ONE_SAVED_LABEL_ARRAY_GO",
  "approved": true,
  "runner_sha256": "<frozen-runner-sha256>",
  "prepared_metadata_sha256": "3e0343f730a2e475eb43b4f89547f91730686a3f6e029f7a5eb7e5fb610714fb",
  "boundary_sha256": "de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909",
  "operating_source_sha256": "9473861797b729b6b6eb60607a7edfb67921fa2b259bc2b0ffa8b2af08fc1353",
  "operating_ledger_sha256": "a92506b7b5b2ca5f668a21f9b111b32b3d2080a707ba9646bbf063c53dfe5aea"
}
```

실행 형태는 `python -X utf8 evidence/integration/bare266-label-preview-20261018.py --approval <Root GO path> --approval-sha256 <Root GO SHA>`다. GO 전에는 이 명령을 실행하지 않는다. source/ledger의 실제 전후 SHA 검산은 Root가 소유한다. runner는 GO의 명시 값을 결속하되 운영 source/ledger를 읽거나 쓰지 않는다. 경계는 `data/first-group-boundaries/selected-six.geojson`의 위 SHA로 앞뒤 검산한다.

## 한도와 조기 종료

허용 한도는 이미 저장된 라벨 **1개/최대8MiB/2048²**다. 파일 stat·handle identity를 읽기 전후 확인하고 최대 cap+1 bounded read 한 번으로 파일을 메모리에 가져와 SHA를 검산한다. 그 바이트의 MemoryFile에서 단일 uint8·투영 CRS·10m·정확 격자/범위/NoData를 검사하고 **전체 배열 read 1회**만 수행한다. Esri 공식 코드집합(0 NoData, 1·2·4·5·7·8·9·10·11) 밖 값은 차단한다. 네트워크 PROJ를 끄고 GDAL PAM/인접 파일 검색 없이 메모리 TIFF를 연다.

원래 상한 계획은 256창/stride128/최대225창·나지 class8 최소256픽셀·주내 면적95%·상위50이었다. 그러나 저장 report의 전체 히스토그램은 `{1:962,2:4072659,4:408,5:54635,7:7058,11:58582}`로 합계 4,194,304=2048²이며 class8이 없다. Root는 아래 분기로 실제 승인 범위를 더 좁혔다.

- 실제 전체 histogram이 저장 값과 정확히 같고 class8=0이면, 어떤 부분창도 나지256픽셀을 가질 수 없다. **225창 배열 검사를 생략**하고 `windows_scanned=0`, `province_fraction_computed=false`, 후보0과 수학적 이유를 기록한다. 95% 경계 검사를 통과한 후보가 있다고 표현하지 않는다.
- class8>0·histogram 불일치·격자/클래스/파일 변경이면 부분 결과를 보존하고 차단한다. 자동225창 탐색·상한 변경·재읽기·재시도 없이 Root 재판단으로 넘긴다.

시작 marker와 결과는 `xb` 새 파일로만 만든다. 같은 시작 marker가 있으면 다시 실행하지 않는다. 실패 결과도 관측한 histogram 등 부분 근거를 남기며 URL/무제한 예외문을 출력하지 않는다. 원본 라벨·aggregate·원장·profile·pointer는 쓰지 않는다. 오류가 없을 때도 결과는 weak-label preview이고 최종 영상품질·독립정답·중복/공간독립성·pending inventory·175/170 consumer 연결·학습 승인 모두 false다.

## 검증과 후속 기록

준비 단계 검증: 메타데이터 refs 대조와 runner AST 문법 검사만 수행한다. 실제 라벨 배열0/원격0/collector0/모델0/새 전체 QA0. 실제 실행의 PID/session·시간·result SHA·전체 histogram 대조·Root 운영 핀 전후 증거는 GO 뒤 이 문서 후속 절로 기록한다. UI/API/제품 계약 변경이 없는 evidence 검사이므로 화면 수정은 필요 없다. 완료 뒤 Root를 통해 이해자료에 “저장 약라벨 검사”와 “실제 학습 자료 확보”를 구분해 인계한다.

## 실제 실행 결과 — 2026-10-18 18:01 KST

Root는 runner SHA `c06ea6cd534db9ad51fe2e2028d444209ca2a22317702200c5a6da0bacf4341e`를 읽기 검토하고 원본 source/ledger 전 핀 및 lock 없음 확인 뒤 `evidence/integration/bare266-go-root-20261018.json` SHA `f272d6388077a4c00f01efed5aa64ffa577c0c26df450c0fb2f8d29843386380`를 작성했다. 승인 명령을 **단1회** 실행했다. 시작 marker 시각은 09:01:50.113777Z(18:01:50 KST), exit0, exec 전체 wall 2.0344925초, runner 기록 0.907초다. 즉시 종료되어 exec 도구가 장기 session/PID를 반환하지 않았으며 추정 번호를 기재하지 않는다.

결과 `evidence/integration/bare266-label-preview-result-20261018.json` SHA는 `916866d419a5ca88dccd27da03a59cf2432af87ca90b6d1fc7dc83916fea7cc2`다. 판정은 `LOCAL_SAVED_LABEL_ACTUAL_ZERO_BARE_NO_TARGET_UNAPPROVED`다.

| 실제 검사 항목 | 관측 |
|---|---|
| 라벨 파일 읽기 | 1개, 97,234B; 고정 SHA 일치 |
| 배열 읽기 | 전체 2048² 배열 1회 |
| 격자/클래스 | 지정 EPSG32751·10m·uint8·공식 클래스 조건 통과 |
| 실제 전체 histogram | 1:962 / 2:4,072,659 / 4:408 / 5:54,635 / 7:7,058 / 11:58,582 |
| 저장 histogram과 대조 | 모든 클래스 exact, 총4,194,304픽셀 |
| 실제 나지 class8 | **0픽셀** |
| 256창 검사 수 | **0** — 전체 나지0에 따른 논리적 조기 종료 |
| 나지256·주내95% 후보 | 0; 주내 면적 자체는 계산하지 않음 |
| 파일 불변 확인 | 라벨 후 stat/identity 불변, 메타데이터·경계 전후 SHA 일치 |
| 원격/collector/원본 행 생성/학습 | 모두 0 |

이는 “225개 창을 실제 검사했다”는 결과가 아니다. 전체 라벨에 나지가 하나도 없으므로 어떤 256 부분창도 256개 나지 픽셀을 만들 수 없다는 더 좁은 실제 근거다. 다른 위치·연도·주 전체의 나지 부재나 실제 토지피복 정답 부재를 뜻하지 않는다. 이번 약라벨에 기록된 class8이 없다는 뜻이다. 원래 최소256 기준은 유지했다.

runner는 운영 source/ledger를 읽지 않았다. Root가 별도로 소유한 원본 전후 핀 확인을 최종 인계에 결속한다. 운영 source/ledger/profile/pointer 쓰기0, 173/175/170 소비자 연결0, 신규 확보/적격/나지 기여 증가0이며 최종 영상품질·독립정답·학습 승인은 여전히 false다.

Root 후검사는 [bare266-root-postcheck-20261018.json](../../evidence/integration/bare266-root-postcheck-20261018.json) SHA `1f17bc7731c45971e1f4d4020a96ea32e81ec0b2b1e7a579b73aac7cd905678f`다. `ONE_NEW_SAVED_LABEL_ZERO_BARE_VERIFIED_OPERATING_PINS_PRESERVED`로 source9473/ledgera925·게시 후보 pointer920ceb·나지 pointer1018b·profilea246 불변을 확인했다. 잔여 예산1,893,156,314B, 신규 품질적격/나지기여0, native patch QA 미실행이다. old pending2 전액136,314,880B 보존도 Root 인계로 확인했다. 이 문서는 Root의 운영 핀 검산과 agent의 단일 라벨 검산을 구분하며 동일 라벨을 다시 스캔하지 않는다.

UI/보유량 증가가 없는 이유는 성공 patch를 만든 작업이 아니라 기존 실패 작업의 약라벨 파일만 확인했고 나지 후보도0이기 때문이다. RGB/SCL/B02 최종 정합·최종80%·독립정답·공간/기존자료 중복 검증을 새로 수행하지 않았으므로 영상품질·consumer 연결·학습 승인은 false다. Root에 이 구분과 최종 증거를 이해자료 후속 작업으로 인계한다.
