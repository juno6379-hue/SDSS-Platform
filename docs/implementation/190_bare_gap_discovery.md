# 190 — 고론탈로·서자바 128픽셀 간격의 실제 로컬 나지 후보 탐색

상태: **VERIFIED_REAL_LOCAL_LABEL_BYTES / LOCAL_OFFSET_DISCOVERY_COMPLETE_UNAPPROVED**. 186에서 시험한 선택 탐색을 실제 고정 자료에 처음 실행했다. **나지 후보37창**을 발견했으며, 실제 Sentinel 취득·품질 적격 패치 증가·과거/상호 겹침 통과·독립 공간·학습 준비·과학 승인은 아니다.

## 쉽게 설명

256×256 크기의 창을 기존에는256픽셀씩 옮겨 보았다. 맨땅이 두 창의 경계에 걸쳐 있으면 각각의 창에서는 나지가 적게 보일 수 있다. 이번에는 **창 크기는256 그대로**, 이동만128픽셀로 줄여 중간 위치도 확인했다. 실제 약한 라벨에서 기존 정렬창7개와 중간 위치30개가 조건을 충족했다. 이동 간격이 작으므로 서로 겹치는 창이 생길 수 있다.37개를 새 학습 패치37개나 독립된37곳으로 세지 않는다.

## 소유·실행 조건

사용자는 담당별 병렬 진행을 요청했고 Root가 이 작업자에게 로컬 후보 탐색만 배정했다. Root가188 native 감사 완료를 확인해 ready를 전달하기 전에는 CONT/186/173과 기존 CLI만 읽었다. 완료 확인 후 고정 사본을 만들고 탐색했다. 실제 collector와189 표적 실행은 Root,188 native 감사는 toolbox_review 소유를 보존했다. 이번 작업은 그 감사나179 full support 감사를 중복 실행하지 않았다.

기존 `scripts/find_bare_targets173.py`의 `discover`를 재사용했다. 기존 CLI main은 bare173 경로와 기본 제한을 사용하므로, 소유 범위인 새190 경로와 더 낮은 제한을 명시하는 evidence 전용 `run.py`를 사용했다. 제품 소스·테스트·기존50 proposal/report·원장·lock·모델·UI/API 변경은 없다. 새 제품 API나 화면을 만들지 않는 내부 후보 탐색이므로 직접 프론트 수정·build·브라우저 시험은 필요하지 않다. 결과 UI 게시 여부는 Root의 별도 후속이다.

## 입력 고정과 실제 실행

Root가188 후속 자료를 native 검사한 뒤 지정한 원본은 **1,649행 / 저장 적격1,321 / 64,172,878바이트**, SHA256은 다음과 같다.

`3d5ae7d2c75e169a2bcf8b3e5dfbb1e854145f73f26d75a5549608e9fa4969d8`

원본을 읽어 같은 SHA를 재확인하고 새 `data/bare190-gap-20261018/source.json`에 exclusive로 원바이트 복사했다. 이후 탐색은 이 고정 사본에 한정한다. 현재 aggregate는189 등 후속 수집이 추가할 수 있으므로 그 변화와 사본 변조를 구분한다. 이번 완료 관측 시 active source도 위 SHA와 같았다. 이후 자료를 이번 결과에 포함했다고 주장하지 않는다.

경계는 기존 `data/first-group-boundaries/selected-six.geojson`, SHA256 `de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909`다. 새 경계 사본을 만들거나 경계를 변경하지 않았다.

명령은 다음과 같다. 이미 사용한 새 경로를 덮어쓰지 않으므로 같은 명령을 재실행하면 기존190 출력/사본을 보존하고 거부한다.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python evidence/integration/bare190-gap-20261018/run.py
```

**실제9.406초·종료0**이며 후보 발견과 반환37개 native 라벨 재계수, 입력/과거 출력의 최종 SHA 대조까지 포함한다. 실행 시각은 같은 디렉터리 `preflight.json`·`receipt.json`의 KST 값을 따른다. 실제 로컬 배열 실행이며 합성 시험 건수로 표시하지 않는다.

## 제한과 기준

| 항목 | 이번 명시 값 |
|---|---|
| 창 크기 / 이동 | 256×256 / 128픽셀 |
| 선택 주 | gorontalo, west_java |
| split | 고론탈로 train / 서자바 test 고정 |
| 반환 후보 상한 | 50 |
| 최초 raw label payload 합 상한 | 50MiB |
| label 파일 / 개별 파일 상한 | 256개 / 64MiB |
| 전체 검사창 상한 | 32,768 |
| manifest 상한 | 64MiB / 3,000행 |
| 라벨 규격 | 동년 ESRI·고정 원본 SHA·단일 정수 band·투영 미터계·native10m |
| 후보 조건 | 코드8 나지≥256픽셀 / 주내 기하 면적≥95% |

메타데이터 선택 필터를 쓰더라도 원본 전체 행과6주 경계 계약을 검증했다. 동년 lineage·GTiff header·native 창·해시·품질 기준을 완화하지 않았다. 나지 code8은 ESRI 원분류이며 모델 class7과 구분한다. 반환 후보의 실행/품질/공간독립/과학/학습 플래그는 false다.

## 실제 발견 결과

| 주 | 로컬 label crop | 검사한128격자 창 | 나지≥256 창 | 주내95%까지 충족 | 기존256 정렬 / 새128 오프셋 |
|---|---:|---:|---:|---:|---:|
| 고론탈로 | 14 | 3,150 | 8 | 8 | 1 / 7 |
| 서자바 | 17 | 3,825 | 51 | 29 | 6 / 23 |
| 합계 | **31** | **6,975** | **59** | **37** | **7 / 30** |

최초 압축 label payload 합은 **5,332,454바이트**, SHA/local x/y 중복 제외는 **0**이다. 제한50 이내라 발견37개를 모두 반환했다. split별 발견은 train8/test29이며 validation 탐색은 요청 범위 밖이다. 고론탈로 검사창의 최대 나지 픽셀은360, 서자바는1,708이다. `maximum_bare_pixels`는 주내95% 필터 전 전체 검사창의 최대이므로 반환 후보의 최댓값으로 바꾸어 설명하지 않는다.

중복 제거 키는 `(라벨 SHA, local x, local y)`다. **중복0은 실제 지리적 비겹침0과 다르다.** 서로 다른 crop SHA나 다른 연도의 같은 위치,128 간격의 서로 겹치는 창은179 과거지원/상호 겹침 검토가 필요하다. 기존50에 추가해87개 독립 공간이라고 합산하지 않는다.

## 별도 검산·보존·한계

반환37개 모두 pinned raw label을 다시 MemoryFile로 열어 native256 창의 code8 픽셀을 재계수했다. 저장 후보의 값과 전부 같고256 이상이었다. 이 재계수는 기하 경계 면적이나 실제 Sentinel/SCL/rawB02/미정산 inventory를 재검사한179 full 감사가 아니다.

source 사본·경계·선택31개 label의 SHA가 최종 대조에서 유지되었다. 기존 `bare173-verified-20261018/proposal.json`·receipt와 `bare179-report-20261018.json`의 전후 SHA도 모두 같았다. 원격 요청·collector·학습·원장·lock 쓰기는0이다. 여기의 기존 source 쓰기0과 별도로, 허용된 새 source 사본1개는 위 경로에 생성했다.

`label_bytes_read`는 최초 압축 payload 합이다. 최종 SHA 패스와37개 재계수는 추가 로컬 IO를 사용하므로 전체 OS 읽기량이나 메모리·시간 hard cap으로 표시하지 않는다. 파일 pin은 순차 관측이며 OS 다중 파일 원자 snapshot 보증이 아니다. ESRI는 약한 참조이며 나지의 현장 진실성·기관 승인도 미검증이다.

## 산출물과 후속 인계

| 산출물 | 바이트 | SHA256 |
|---|---:|---|
| proposal.json | 75,672 | `1cda6dd428dfffcca9df4ac690d9f79ca2187fdc953de0dd3b67d0d1226dce92` |
| receipt.json | 12,098 | `9391a75b9e048eaf7db44882140f30d685adfc4cf94fee41014c8cc4dee1eb1b` |

위 파일과 `preflight.json`·재현 wrapper는 `evidence/integration/bare190-gap-20261018/`에 있다. receipt는 실행 가능 승인서가 아니라 발견·재계수·핀 보존 증거다.

Root는 현재189의 단일 실행을 보존하고, 이37개를 **새 proposal**로179의 전체 최신 support inventory·과거/상호 겹침·source lineage에 연결할지 결정한다. 그 검토와175/176/170의 명시 최종 검사를 통과하기 전에는 실행하지 않는다. 과거 고론탈로/서자바 clear0이 이번에 해소됐다는 결론도 아직 내리지 않는다. 공통 원장·인계·이해자료·INDEX/대본/FAQ 갱신과 필요 시 UI 인계는 Root/understanding 담당에게 이 문서와 고정 SHA를 전달한다.
