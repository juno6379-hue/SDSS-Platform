# 123 — per_scene 정규화 근거의 bounded 읽기 전용 파일 검증

후속124는 [모델 등록 참조와 실제 checkpoint manifest 읽기](124_model_checkpoint_manifest.md)를 별도 추가했다.123의 caller manifest 입력은 바꾸지 않았고 두 helper의 자동 결합·Dataset Registry/전연차/실행 연계는 여전히 후속이다. Temp 수동 대조 성공을 기존 Workflow 연결로 해석하지 않는다.

## 쉬운 설명

122는 선언 형식과 값만 비교했다. 신규 `backend/app/ml/per_scene_normalization_files.py`의 `verify_per_scene_normalization_files(data_root, checkpoint_manifest, source_scene, normalization, image_path)`는 명시 root 아래 영상 역할·보정 JSON·원 metadata 세 파일을 실제로 읽어 각 역할의 고정 SHA와 비교한다. 보정 JSON의 복사 바이트를 strict 파싱하고122 선언 관측도 재사용한다.

세 역할이 맞으면 `FILES_MATCHED_UNVERIFIED`와 바깥 `artifact_bytes_verified:true`를 반환한다. 이것은 읽은 파일 바이트의 SHA 일치다. 실제 영상 header·공식 원출처·checkpoint·과학 정확도·실행 허가·Workflow 지원 완료가 아니다. 영상 역할에 raster가 아닌 임의 바이트를 넣어도 선언 SHA와 맞으면 이 범위에서는 성공하는 것이 정상이다.

기존122·115·ML 서비스·Registry·API·UI·실행기를 수정하거나 이 함수를 연결하지 않는다. Store 생성/쓰기·파일 생성·보정/학습·checkpoint 로드·추론·자료 수집·다운로드를 수행하지 않는다. source_url을 HTTP로 읽거나 네트워크 라이브러리를 사용하지 않는다. 파일시스템 mapped drive의 실제 매체가 원격인지까지 증명하지는 않는다.

## exact12 반환과 검증 순서

| 필드 | 값 |
|---|---|
| schema_version | 1 |
| scope | PER_SCENE_NORMALIZATION_FILE_SNAPSHOTS_ONLY |
| status | OUT_OF_SCOPE / BLOCKED / FILES_MATCHED_UNVERIFIED |
| issue | null 또는 exact {code,field} |
| declaration_observation | 122의 exact9 관측 또는 null |
| file_bindings | exact {image,normalization_evidence,source_metadata}; 각 NOT_CHECKED/MATCH/MISMATCH |
| artifact_bytes_verified | 성공 때만 true |
| checkpoint_artifact_verified | 항상 false |
| source_authority_verified | 항상 false |
| scientific_accuracy_validated | 항상 false |
| execution_authorized | 항상 false |
| workflow_supported | 항상 false |

고정 issue code는 INVALID_INPUT / ROOT_UNAVAILABLE / PATH_INVALID / FILE_UNAVAILABLE / FILE_LIMIT / FILE_CHANGED / SHA256_MISMATCH / EVIDENCE_JSON_INVALID / DECLARATION_NOT_CONSISTENT다. field는 data_root / image / normalization_evidence / source_metadata / declarations / inputs의 고정 역할 이름만 반환한다. 경로·URL·파일 내용·예외 원문을 결과에 넣지 않는다.

순서는 다음과 같다.

1. 122를 evidence={}로 먼저 관측한다. missing/global/다른 지원외 mode이면 OUT_OF_SCOPE로 끝나며 root와 다른 경로를 열지 않는다. source/normalization의 잘못된 타입·누락·잘못된 SHA도 파일 I/O 전에 BLOCKED다. 빈 evidence는 `evidence.status` 미확보라는 의도적 probe이며 조작한 근거가 아니다.
2. 명시 root, image_path, normalization.evidence_path의 경계를 검사한다.
3. 보정 evidence를 최대2MiB로 복사하며 SHA를 계산하고 normalization.evidence_sha256과 먼저 비교한다. SHA 불일치가 JSON 오류보다 우선한다.
4. 동일 복사 바이트의 strict JSON을 파싱한 뒤122를 실제 evidence로 다시 관측한다. 순서·제품ID·밴드·scale/offset 등 선언이 consistent인 경우에만 다음으로 간다.122는 per_scene 정상 경로에서 probe/full 최대2회 호출된다.
5. evidence.source_metadata_path 경계를 검사하고 image64MiB, source metadata2MiB의 순서로 SHA를 읽어 source_scene.image_sha256 및 evidence.source_metadata_sha256에 비교한다.

실패 전 완료한 role의 binding은 보존한다. 예를 들어 evidence SHA가 맞고 product 선언이 다르면 evidence MATCH와122의 DECLARATION_MISMATCH는 남지만 바깥 status BLOCKED·artifact false다. evidence MATCH는 JSON 유효성이나 선언 의미의 성공까지 뜻하지 않는다. 성공 시에도 안쪽122의 artifact_bytes_verified는 원래대로 false이며 바깥 파일 관측과 범위가 다르다.

## 경로·입력·파일 한도

data_root는 기본값 없는 명시 절대 기존 디렉터리다. 정확한 builtin str 또는 현재 플랫폼 concrete Path 타입만 허용하며 커스텀 `__fspath__`/Path subclass를 호출하지 않는다. 문자열 root는4096자 이하 제어문자·고립 surrogate 없는 값이다. UNC `\\server` 또는 `//server` root는 stat/resolve 전 거부한다. drive-letter mapped drive의 물리적 로컬성은 이 정책으로 보장되지 않는다.

root lexical path와 resolve가 같아야 하고 root뿐 아니라 모든 ancestor도 symlink/junction이 아니어야 한다. 세 파일은 root 아래 상대 문자열 경로만 받는다. POSIX /와 Windows 역슬래시를 비교용으로 수용하지만 절대 경로·drive/URI의 colon·빈 segment·`.`·`..`·segment128자 초과·끝 공백/점을 거부한다. 전체 경로 문자열은512자 상한이다. 경로를 추정·보정하거나 밖의 파일을 참조하지 않는다.

파일별 읽기 전 regular-file/lstat·resolve·ancestor link를 확인하고 열린 fd의 stat을 비교한다.1MiB 이하 chunk로 누적 SHA를 계산하며 누적이 상한을 넘는 즉시 중단한다. 마지막 fd 및 path의 dev/inode/size/mtime_ns/ctime_ns를 다시 비교한다. 보정 JSON만 최대2MiB 복사하고 영상·원 metadata 바이트는 반환/보관하지 않는다. 읽기 중 크기 성장·mtime 변경 등의 탐지 실패는 고정 오류가 된다.

evidence JSON은 UTF-8 object여야 하고 중복 키·NaN/Inf/지수 overflow·고립 surrogate·잘못된 UTF-8을 거부한다. 파싱 후 깊이64·값 node65536 상한을 검사하고 순회 stack 확장도 node 한도로 제한한다. 기본 JSON 파서는 먼저2MiB 파일 상한 안의 객체를 구성하므로 무제한 JSON 스트림 파서라고 표현하지 않는다.

같은 경로가 image와 metadata 역할에 쓰이는 것은 허용한다. 역할별 SHA가 각각 맞는지만 관측하며 다른 파일임이나 영상 유효성을 추정하지 않는다. evidence 경로도 임의 자동 대체/중복 해소를 하지 않는다.

## 한계와 다음 실행 연계

세 파일의 순차 snapshot은 세 파일을 같은 시점에 묶은 원자 snapshot이 아니다. stat/link/resolve 검사와 fd 비교는 일부 경쟁을 탐지하지만 모든 TOCTOU를 제거하지 않는다. regular-file 확인 직후 FIFO 등으로 바뀌는 경쟁이나 open 단계의 blocking까지 원천 제거하는 OS 격리/파일 잠금은 제공하지 않는다. 호출자는 신뢰할 수 있는 내부 파일 작업 환경을 사용해야 한다.

이 함수는 caller가 준 세 역할 SHA와 지정된 내부 파일만 비교한다. Registry의 고정 ID/version이나 기관 인증을 읽지 않고 checkpoint_manifest와 실제 checkpoint 파일을 결합하지 않는다. 따라서 여기서 고정 SHA라는 말은 Registry 고정 참조 연결 완료를 뜻하지 않는다. checkpoint_manifest는 caller가 제공한 metadata이며 checkpoint 파일의 SHA/architecture/state_dict를 검증하지 않는다. source_url과 status=`verified_product_metadata`는 caller 진술이고 기관 서명·라이선스·원문 내용 진위를 인증하지 않는다. raster header/실물6밴드/CRS/정렬/구름 mask/spectral 의미/float32 변환 결과도 검사하지 않는다. manifest global 계수와 per_scene 계수를 같게 강제하지 않는다. 모델 Deployed/독립 평가·Registry·연도·품질 gate와 실행 전 재확인은 기존 경계/후속 구현의 일이다. 성공 결과를 실행 payload로 자동 전달하지 않는다. 다음124는 실제 Registry/모델 참조와 per_scene 장면 metadata의 연계 계약 검토·구현 후속이다.

## 시험 근거와 동결 인계

집중 최종 **14 PASS / 0.810초 / exit0**: `evidence/integration/per-scene-files-focused-final-20261018.log`. 최초14 PASS/1.143초 로그도 `per-scene-files-focused-20261018.log`에 보존했다. 최종에는 UNC root를 resolve 이전에 차단하는 시험을 포함한다.

관련 최종 **28 PASS / 1.309초 / exit0**: `evidence/integration/per-scene-files-related-20261018.log`. Root가 실행한 현재 최종 로그이며 신규14와122 선언14를 포함한다. 집중과 중복 합산하지 않는다. 이전 완료 단위의 증거는 수정하지 않았다.

TempDirectory의 실제 임의 바이트·보정 JSON·원 XML 역할을 사용했다. 각 role 변조·누락·상한·읽는 중 성장·mtime 변경·SHA 재바인딩 후 JSON/선언 오류·중복/nonfinite/surrogate/depth/nodes·경로 탈출·Windows separator·UNC·커스텀 fspath callback 방지·same-role path·부분 MATCH·원본/입력 불변을 확인했다. symlink 생성은 호스트 권한이 허용되면 실제 생성하고 아니면 predicate 경계로 대체하는 시험이므로 실제 생성 성공으로 일괄 주장하지 않는다. 독립 검토의 실제 Windows junction 생성 여부는 별도 증거로 구분한다.

source SHA `77b6d844aa1a71304826d34f492780b80a8b0b7c7f21740856510d8acd463366`, test SHA `b5bae5db47e7ed4178ae2c41cebcd4481400c1bce40445afcfd1cfea57284c8b`로 Root/독립 검토자에게 동결 인계했다. Root가 실제 GeoTIFF·기존 file verifier 대비·보존을, 독립 검토자가 별도 fixture/link 경계를 검증한다. 이해 에이전트에는 완료 소스·시험·한계를 전달해 설명·대본·FAQ·INDEX·변경 이력을 갱신한다.

미연결 내부 reader이므로 기존 UI/API/global-only 안내를 바꾸지 않고 frontend/build/browser를 재실행하지 않는다. 이전120의 전체 backend1184건/front261건은 과거 근거이며 이번 신규 시험과 합산하지 않는다. 운영 데이터/Registry·모델 쓰기·수집·훈련·추론·배포는0이다.

## 최종 독립·실파일 대비·보존 증거

독립 검토 **9 PASS / 0 SKIP / 1.2948352초 / exit0**는 `evidence/integration/per-scene-files-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 실제 Windows junction을 만들어 root/child 거부를 확인한 뒤 링크 자체만 비재귀 해제하고 target sentinel 보존을 확인했다. 초기 독립 시험의 Path.is_junction 미지원 오류는 별도 초기 JSON·LOG에 보존했으며 독립 시험의 lstat reparse-tag 검사만 고쳤다. 제품 소스 변경으로 처리한 결함이 아니다.

독립 검토는 세 역할 SHA·부분 MATCH 우선순서·global1..16 무I/O·strict JSON 오염/깊이/node·상한/실제 stream 성장·누락/디렉터리/탈출·선언 불일치 전 영상 미접근·입력 불변·exact12/바깥5false 및122 내부 false도 확인했다. 정상 파일 비교의 artifact_bytes_verified만 true이고 그 밖의 checkpoint/기관/과학/실행/Workflow 다섯 flags는 false다. 비영상 임의 바이트가 MATCH인 예시는 header/mask/calibration/과학 검증이 아님을 확인한다. Git9c5acb4의 기존 핵심8 source SHA·tracked source 불변이며 새 지적0이다.

Root의 `evidence/integration/per-scene-files-runtime-comparison-20261018.py`와 같은 stem `.json`·`.log`는 실제 임시 GeoTIFF/evidence/XML와 기존 normalization file verifier를 대비한 **6 PASS** 근거다. 이 자료는 생성 fixture이며 학습·추론·checkpoint 로드·운영 자료 접촉을 수행하지 않았다. 신규 helper와 기존 verifier의 비교 범위를 넘어 실행 연계 성공이나 독립 정확도를 주장하지 않는다.

`evidence/integration/per-scene-files-live-integrity-20261018.json`에서 보호141개·기존source279개·이전증거1019개·catalog14행 SHA와 예약136314880바이트가 불변이다. source/test 동결 SHA는 최종까지 유지했다. 기존 전체 backend/frontend를 다시 실행한 것처럼 표시하지 않고 이번 신규 집중·관련·독립·실파일 대비 범위만 최종 근거로 사용한다. 문서 최종 근거를 반영하고 동결했다.
