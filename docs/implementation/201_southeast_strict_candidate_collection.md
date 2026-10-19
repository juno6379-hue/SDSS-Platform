# 201 — 남동2025 엄격 표적의 기존 지원 영상 겹침 차단

상태: **BLOCKED — 실제 사전검사에서 기존 지원 영상 겹침으로 중단**. 새 worker·예약·파일·적격 패치는0개다. 새 패치가 없어 native QA는 수행하지 않았다. 196 재감사·광역 support 재스캔·재시도·가드 우회도 하지 않았다.

## 명시 실행과 중단 지점

Root는13:34:57.260 KST에 남동술라웨시2025 `local-rank10-2025`를 최대1batch로 지정해 기존170 명시 entry를 시작했다. 이 후보는 과거179 index10의 로컬 나지 **321픽셀 선언**에 해당하며,198의 새 최소 후보 선별0.9와175/176/170 fresh 전검사를 사용했다. 선언321픽셀이나 과거 검토 통과를 현재 수집 성공으로 간주하지 않았다.

`target201-terminal-root-20261018.json`은13:36:35.788 KST 종료·**exit2·96.547초**를 기록한다. 실제 stdout은 다음 상태다.

```json
{
  "status": "BLOCKED",
  "executed": false,
  "execute_requested": true,
  "execution_started": false,
  "execution_progress": null,
  "issue": "TARGETED_INVENTORY_EXISTING_SUPPORT_OVERLAP"
}
```

이 중단은169/170 worker의 원격 수집 시작 전 로컬 inventory 검사에서 발생했다. worker 시작/종료 기록은0건이며 예상 batch key의 중앙 원장 행과 sources/patches 출력 leaf가 모두 없다. source·ledger SHA가 launch 전과 같아 새 예산 예약·정산도 없다. 기록과 코드 순서상 이201 worker의 새 HTTP가 시작되지 않은 상태이며 시스템 전체 네트워크 추적을 수행했다는 뜻은 아니다.

## 구체적인 지원 범위 대조

170 stdout은 **처음 거부한 파일 경로를 출력하지 않는다.** 따라서 첫 거부 파일을 독립적으로 확정했다고 주장하지 않는다. 대신201 대상과 직전196의 두 산출물 metadata만 좁게 대조했다. 원본 전체·167 inventory를 재실행하거나 기존 raster를 다시 열지 않았다.

201의 EPSG32751 target bounds는 `[501910,9554880,504470,9557440]`이다. 직전196의2025 rank1에서 기록된 지원 범위와 다음 양성 면적 겹침이 있다.

| 196 지원 파일 | 기록된 실제 crop bounds | 201과의 양성 교차 면적 |
|---|---|---:|
| raw-B11.tif | `[504440,9554880,507040,9557480]` | **76,800m²** |
| raw-B12.tif | `[504440,9554880,507040,9557480]` | **76,800m²** |
| raw-SCL.tif | `[504460,9554900,507020,9557460]` | **25,400m²** |

196 native 감사에서 이미 확인한 B02의 bounds는 `[504470,9554890,507030,9557450]`로201과 양성 교차 면적이0이다. **B02의 겹침0만으로 SWIR·SCL 지원 범위의 겹침0을 보장하지 않는 사례**다. 이 대조는 기록 bounds와 이전 감사의 격자에 대한 metadata 계산이며,201에서 세 support 파일의 바이트를 새로 읽거나 SHA를 독립 재검산한 결과가 아니다. exact first-veto 귀속이나 모든 support의 완전성 증명과 구분한다.

과거179의 clear 상태 이후196이 실제 support 파일을 추가했으므로 fresh inventory가 필요했다. 이번 차단을 없애려고 파일·경계·품질 기준을 지우거나 겹침 허용폭을 넓히지 않았다. 원래 label·source·raw support를 보존했다.

## 재고·예산·잠금 보존 검산

`evidence/integration/target201-native-root-20261018.json`은 이름에 native가 들어가지만 내용은 **사전검사 중단에 따른 native 추가0**을 명시한다. 실제 검산 결과는 다음과 같다.

- 기존1,667행이 고정 source와 정확히 동일하며 새 행0개
- 품질 적격 누계 **1,333개**, 새 적격0개
- launch 전 source SHA와 현재 SHA 동일: `1a12b7bca384dd09d73a04cc31df21f75377fc34c332b501a6ee37508dd46fb5`
- ledger SHA 동일: `f49d7e778359c1f60743f617edb599fe2ba3170e9e9243a3459211aa4bc9b0fe`
- 기존 반텐2023·서자바2023 pending 두 행·**136,314,880바이트 예약 전액 보존**
- 새 target batch 예약/계상 **0바이트**, 잔여 **1,963,547,857바이트**
- 예상 source/patch 출력 leaf 없음, 종료 뒤 실행 lock 없음·관련 collector process 없음
- 원본·원장 두 차례 읽기 안정,429 비활성

196에서 미등록 보존한1개를 포함하는 기존 실제 물리 수1,668개도 이번 실행으로 늘지 않았다. 이번 담당은 이를 광역 파일 스캔으로 다시 센 것이 아니라 새 출력0과 기존 원본/원장 불변으로 구분했다. 기존193의1,317 고정 후보와 현재 원본1,333 적격은 서로 다른 범위다.

## 근거와 후속 소유

실행 근거는 `target201-launch-root-20261018.json`, `target201-live-root-20261018-stdout.log`, `target201-terminal-root-20261018.json`이다. 상세 보존 검산과 좁은196 metadata 교차는 `target201-native-root-20261018.json`에 있다. 원격 수집 성공·최종 나지 기여·학습 준비를 인증한 산출물이 아니다.

후속203 고론탈로 단일 표적 실행은 Root 소유다. 이 담당은201을 다시 실행하거나 별도 collector를 시작하지 않는다. 새 API나 사용자 입력 기능을 추가하지 않아 이 단위 자체의 화면 변경은 없으며 Root가 실제 재고·차단 상태와 후속 증거를 인계한다. 학습·Registry·라벨/모델·정산 원장은 변경하지 않았다.
