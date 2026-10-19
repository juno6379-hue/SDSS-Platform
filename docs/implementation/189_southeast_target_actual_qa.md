# 189 — 남동술라웨시2024 표적1개 실제 수집·신규 native 품질 검산

상태: **VERIFIED_REAL**, 범위는 새로 수집한1개 표적의 로컬 실제 바이트·격자·픽셀·정산 검산이다. 독립 현장 정답이나 모델 과학 정확도·학습 준비 완료를 뜻하지 않는다. Root가 단일 collector를 실행했고 독립 담당은 종료 뒤 새1개만 읽었다. 이 감사는 HTTP·원본/원장 쓰기·수집 재실행·188 감사 재실행을 하지 않았다.

## 실행과 실제 결과

Root의 `target189-launch-root-20261018.json`은12:53:28.278 KST에 기존 명시 collector를 `--execute`, 최대1batch, `-X faulthandler`로 시작한 사실을 기록한다. 목적은 187 재부팅 중단 뒤 같은 후보의 **새 고정 원본/원장/plan으로 재검증한 집행**이다. 187의 남은 lock이나 예산을 근거 없이 재사용한 실행으로 표현하지 않는다.

실행 대상은 `southeast_sulawesi / train / 2024 / local-rank2-2024`이며 batch key는 `target256-bare-southeast_sulawesi-2024-local-rank2-2024-af6c81c01410`이다. stdout에는 worker 시작1건·종료1건과 `BOUNDED_TARGETED_STAGE_FINISHED / executed=true`가 있다. 실제 supervisor terminal은12:58:45.923 KST, exit0·315.938초다. 실행기 기록의 submitted/finalized는 각각1이며 예약·정산·게시 목록도 같은 batch1개다. 171 정산 보완을 포함한 새 프로세스 소스4개가 launch pin과 일치함을 확인했다.

실제 산출물은 **256×256 패치1개·품질 적격1개**다. 감사 시점12:59:59.429 KST의 원본 metadata 누계는 **1,650개·품질 적격1,322개**다. 이 누계 전체를 native 재검사한 것은 아니다.

## 독립 실제 픽셀 검산

`scripts/audit_priority_increment165.py`의 순수 `native_patch`를 재사용했다. 새 image/label/quality3개와 raw-B021개, 명시한 기존 경계·selected STAC·worker/원장 metadata만 읽었다. 전역 support/부분수집 inventory는 189 preflight의 소유이고 여기서 재스캔하지 않았다.

| 검사 | 실제 결과 |
|---|---|
| 영상 CRS·크기·해상도 | EPSG32751 ·256×256·10m·6밴드 |
| 실제 affine | `[10,0,389910,0,-10,9404330]` |
| image/label/quality | CRS·affine·shape 완전 일치 |
| 품질 마스크 | binary0/1 및 최종 training support 계산과 일치 |
| 유효 픽셀 | 65,025 /65,536 = **99.2202759%**, 기준80% 통과 |
| 주 경계 내부 | 65,536 /65,536 = **100%**, 기준95% 통과 |
| 유효 영역의 나지 원분류code8 | **814픽셀** |
| 나지256픽셀 이상 기여 | **train 패치1개** |
| raw B02와 최종 첫 밴드 | 실제 grid와 전체 픽셀 배열 일치 |

유효 영역의 실제 histogram은 code1=7, code2=62,865, code8=814, code11=1,339다. source label의 원분류8은 모델 내부 class7과 구분한다. 814는 caller의 예상 수를 그대로 받아 적은 수치가 아니라 최종 label/quality/경계/영상 유한·비영 조건을 적용한 실제 배열에서 다시 센 값이다.

새 raster4개는 각 선언 SHA를 확인하고 감사 후 다시 해시해 보존됨을 확인했다. selected STAC의 고정 SHA·scene ID·datetime과 최종 row가 같고 실제 선택 B02 asset URL과 raw-B02의 source가 같다. scene은 `S2B_MSIL2A_20240813T021349_R060_T51MUQ_20240813T055551`이고 선언된 관측연도는2024다. worker receipt와 최종 stdout의 `live_b02_checked=true`, first429=false를 함께 확인했다. 이는 실제 native B02 소비 근거이며 위성 사업자의 촬영 진실을 독립적으로 인증한 것은 아니다.

## 원본·예산 보존

고정 `data/target189-recovery-20261018/source.json`의 SHA가 launch의 source pin과 같다. 현재 manifest의 **첫1,649행이 고정 원본과 정확히 동일**하고 그 뒤 새1행만 있다. 기존 반텐2023·서자바2023 pending 두 행과 **136,314,880바이트 예약 전액**이 원형 그대로다. 과거1,649행의 raster 전체 바이트는 이번 좁은 감사에서 다시 읽지 않았다.

worker·window-state·중앙 원장 정산이 다음처럼 일치한다.

- COG 계상: **9,785,391바이트**
- metadata 계상: **193,254바이트**
- 합계: **9,978,645바이트**, 중앙 batch 상태 settled
- 감사 시점 잔여: **2,002,233,523바이트**

같은 batch의 settle/publish1회 기록과 실제 새 row를 대조했고, 감사 시점 실행 lock은 없었다. manifest·ledger는 감사 전후 원바이트가 같았다. 이는 순차 안정 관측이며 OS atomic snapshot이나 crash-safe transaction 증명은 아니다. 새 예산 추가·기존 pending 환불·원장 편집은 하지 않았다.

## 근거와 남은 조건

- 실행: `evidence/integration/target189-launch-root-20261018.json`, `target189-process-terminal-root-20261018.json`, `target189-live-root-20261018-stdout.log`
- 독립 감사: `evidence/integration/target189-native-root-20261018.json` 및 `.log`, **4.193981초·exit0**
- 이전 증가분: `priority188-native-root-20261018.json`은 별도 완료 근거이며 이번에 재실행하지 않았다.

이번 성과는 **실제 train 기여 패치1개**다. Esri 동년 약한 참조이며 독립 정답이 아니다. split별 기여5개·나지 비율0.5%·검증 최소 픽셀·scene 누출 해소·지배 클래스·모델 훈련·운영 승인은 별도 최신 후보 QA가 필요하다. 한 패치의814픽셀을 전체 나지 gate 해결이나 전체 프로젝트 완료로 보고하지 않는다.

새 API나 사용자 입력 기능을 추가하지 않았다. 기존 collection-status는 원본 누계와 고정 후보의 시점을 구분해 표시해야 한다. 실제 UI 반영·후속 고론탈로 후보 검토·전체 분할 후보 준비도는 Root가 소유하며 이 문서의 native 감사 결과만으로 완료됐다고 표시하지 않는다. Root가 완료 코드·실제 증거를 이해 담당에게 전달해 설명·대본·FAQ·INDEX·변경 이력과 공통 인계를 갱신한다.
