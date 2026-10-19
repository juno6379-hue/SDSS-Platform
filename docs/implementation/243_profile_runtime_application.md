# 243 — 명시 원본 목록 profile의 로컬 API 반영

상태: **VERIFIED_REAL — 제품 코드 18개·실제 로컬 API 반영 / 수집·학습 미실행**. 시험 파일 배치는 별도 242 보완 단위다.

## 적용 결정과 보존

Root는 240 독립 검토 후속판 SHA `c617a634b50690eb3f83926be438b8747b430f2679da0007777db37f51b7b9f5`의 제품 코드 필수 수정 미발견 판정과 시험 이동성 차단을 구분했다. 241 합성 목록 21개 중 **제품 18개만** 적용했다. 이전 3개 시험 파일은 그대로 복사하지 않았다. 이전 판본의 디렉터리 전체를 덮어쓰지 않았다.

각 제품의 최초 baseline SHA·최종 237 SHA를 대조하고 기존 파일 원바이트를 `evidence/integration/profile243-runtime-baseline-root-20261018/`에 보존했다. 새 파일은 기존 경로 부재를 확인했다. 승인·적용 근거는 `profile243-runtime-approval-root-20261018.json`, `profile243-runtime-application-root-20261018.json`이다. 232·167·199·수집기·Toolbox 동시 편집 파일은 적용 목록에 없다.

## 로컬 서버와 명시 설정

기존 localhost8002 API PID40492만 확인해 중단하고 PID40156으로 교체했다. frontend5174와 다른 애플리케이션 서버는 변경하지 않았다. `profile237-api-entrypoint-root-20261018.py`는 같은 app의 내부 `collection_source_profile_path`를 고정한 뒤 localhost8002만 제공한다. 외부 배포·새 학습은 없다.

Root는 `data/first-group-training-priority/source-profile237-root-20261018.json`을 직접 작성했다. 정확한 profile marker와 현재 source SHA `9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987`를 결속한다. 설정 SHA는 `61dd13f8de88f8eef826a0ad4461f22c1a3f4bb698d5b7c5c4833d730fe3ffcc`다. 파일 크기를 보고 자동으로 선택한 것이 아니다. 향후 source가 달라지면 이 설정도 미일치로 차단되며, Root가 새 실측 지문을 확인하고 명시 갱신해야 한다.

128MiB는 로컬 source/candidate JSON 처리 상한이다. 원격 추가 4GiB·COG64MiB+metadata1MiB/batch·2worker·공유2초·첫429·물리3000·고정 split·품질·학습 gate는 변경하지 않았다.

## 실제 검증

- 16:51:07 KST 서버 기동 확인. 인증 방식은 기존 localhost-only, CORS는 기존127.0.0.1:5174를 유지했다. dashboard의 datasets6/models1/jobs0/analyses3와 카탈로그14건의 내용 지문이 전후 같았다.
- 원본·원장·학습 후보 pointer·나지 검토 pointer 4개 지문을 보존했다. 미정산2건136,314,880바이트와 잔여1,896,944,955바이트도 그대로다.
- 실제 `/api/data/collection-status` 한 번의 응답200·21.781초. 재고 시점16:52:21.650782, 예산 시점16:52:23.091159 KST다. 단일 관측을 SLA로 확대하지 않는다.
- 원본 적격1,358/부족21, 후보1,342/차단3/현재 source 일치, 나지50후보/현재 source 일치, 예산·예약 유지 등 13개 확인이 모두 true였다. 원본66,826,849바이트는 여전히 기존64MiB 안이다. 128MiB 최대 크기의 실제 성능 검증은 아니다.

근거는 `profile243-api-status-root-20261018.json`과 `profile243-api-status-checks-root-20261018.json`이다. API 응답 성공을 모델 품질·학습 승인으로 표현하지 않는다. native QA·새 영상 다운로드·수집은 실행하지 않았다.

## 실제 화면과 다음 단계

244 담당이 기존 검증 탭의 연결을 복구해 한 번 새로 조회했다. 16:54:33.928 재고/16:54:34.849 예산 응답에서 같은 수치와 미검사·미승인 안내를 확인했다. 16:54:54 콘솔 경고·오류0/가로 넘침0이다. [244 실제 UI 후속](244_profile_runtime_ui_followup.md)에 근거와 스크린샷 도구 관측 한계를 기록했다. 이전234의 브라우저 차단 이력은 보존하고 현재 후속으로 해소했다.

242 시험 파일·필수 fixture 10개를 Root가 새 경로 부재·고정 지문 확인 후 공유 위치에 반영했다. 실제 E 프로젝트 배치의 관련 93개가31.408초에 모두 통과했다(전체 준비·검증 elapsed36.75초). runtime18과 운영4개 지문은 그대로였고 시험 DATA는 임시 폴더만 사용했다. `profile242-shared-application-root-20261018.json`과 `profile242-main-regression-root-20261018.log`에 기록했다. 이93개는 앞선 두 위치의 같은93개와 합산하지 않는다.

그 후 Root는235 최신 코드30지문·프로세스·잠금·원장·예산을 재확인하고 단일 coordinator를 실제 시작했다. 17:03 관측은 fresh200 잠금 안의 전체 전검사 단계이며 아직 worker/HTTP/확보량은 미확정이다. cached234 겹침 사전계산을 새 전체 검산 대신 사용하지 않는다. 종료 후239 단일 신규분 감사→새자료가 있으면238 고정 후보QA→안전 pointer/UI/문서·이해자료를 이어간다.
