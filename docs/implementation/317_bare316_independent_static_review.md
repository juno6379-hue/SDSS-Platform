# 317 — 316 나지50 최신 겹침 검토 준비의 독립 정적검토

판정: **316 읽기 검토의 실행 전 필수 코드 수정 발견 없음 / 실제 입력 호환·겹침 결과 미검증**. 다만 검토 후 실제 target256 소비에는 **64MiB manifest 한도에 걸리는 별도 연결 공백**이 있다. 316이 성공해도 실수집 가능·원격 품질·나지 확보·학습 승인으로 보고하면 안 된다. 이번 작업은 코드·동결 준비 request/freeze/doc/archive의 읽기와 지문 대조뿐이며 운영 source/ledger/proposal/label/모델 읽기0, native/fullreview/HTTP/시험/import/제품 편집0이다.

## 고정 입력과 최소 변화

316 request878B SHA `608a04e54e110bba4bc8f1df6b6998391704e240de9317c15376a4a32c4a56ee`, freeze SHA `adbc6307b599df6e137c87da9626155e349c62b385f2d8c5c65e31b5f75a347f`, doc SHA `4288ee750670be74a347510fdb5ef16072bffd92fa7e862cd2957d601f9c605d`를 확인했다. freeze 참조6파일의 bytes/SHA가 모두 일치했다.234 archive와 request JSON을 비교하면 바뀐 최상위 필드는 manifest_ref와 ledger_ref 두 개뿐이다.

manifest는309 고정snapshot `data/priority164-guarded309-20261018/source.json`/0c149628…54658, ledger는운영원장/d5ee31ff…21c91이다. 원 proposal63368b…2a0ee·boundaryde7722…2c909·명시3GiB marker는 보존됐다. 실제 snapshot·원장·proposal·라벨이 현재도 그 지문인지 이번 정적 검토에서 열어 인증하지 않았다. Root가 실행 직전 실지문/원본hold/OSlock/중복검사와 새 출력 부재를 확인해야 한다. 현재 게시1391 후보 JSON이 아니라1779행 원본snapshot을 사용하는 계약이다.

## CLI·profile·용량 경로

`scripts/review_bare_targets179.py:156–172`는 --request/--request-sha256/--output을 요구한다. evidence 안 request/output, 새 JSON 출력·부모경로 alias 부재, request 원문 SHA와 완료 뒤 request 재핀·출력2MiB 상한을 확인하고 exclusive xb 기록한다. 기존50/37 report나 게시 pointer를 쓰는 경로는 없다. CLI는 review 결과를 반환할 뿐 collector를 시작하지 않는다. 실패는 REVIEW_BLOCKED/exit2이며 실행 승인false다.

179:37–51의 inventory_kwargs는 `targeted_inventory_profile.py:18–38`에서 정확 schema_version int2·정확 keyset·marker{name,sha256}를 요구한다. bool/알 수 없는 버전·오염 marker·임의 numeric 한도는 거부한다. 고정 descriptor name TARGETED_LOCAL_SUPPORT_3G_V1/max_files10000/max_support_bytes3221225472/max_file_bytes67108864의 canonical SHA가 request marker062bf3…a75a7a와 직접 일치했다. v1은 기본 inventory kwargs를 유지해2GiB이며 v2만 고정3GiB를 선택한다. 원격 예산4GiB나 품질/집행권을 바꾸지 않는다.

179:39–40은 proposal2MiB/manifest128MiB/ledger8MiB/boundary2MiB로 pinned read한다. `targeted_inventory.py:55–58`의 manifest도128MiB여서 이 둘은 현재 전달된 source69564847B를 받을 정적 경로다. 179:119가 한 번의 inspect_targeted_inventory에 동일 inventory_options를 전달한다. 167:50–53의 함수 자체 최대4GiB 검증 안에서 정확3GiB/10000개가 소비되고,121–132의 전체 support 합계3GiB·각 파일64MiB를 유지한다. 실제 합계가3GiB 안인지는 실행 전 미확정이며 초과하면 INVENTORY_LIMIT로 차단한다. 자동 상향 경로는 없다.

이는 ML QA의 ContextVar128/누적JSON16GiB와 다른 자원 계약이다. 179 전체JSON/decode/RAM/실행시간을16GiB로 측정했다고 표현하면 안 된다. source scenes≤3000은179:50에 있고 history는167이 별도로 목록형을 확인해 전체 support에 포함한다. 이 경로에 ML의 depth32/node4M 누적 계측을 새로 넣은 것은 아니다.

## 원제안50·최신원장·참조 라벨 호환

179:43–51은 ranked_windows 목록1–128, stride256 또는 명시 범위의128, province/fixedsplit/year·boundary 핀을 검증한다. 요청 자체가 후보50개를 강제하지는 않으며 Root가 지정한 고정 proposal 원문에 결속하여 실행 시 실제 개수를 확정한다. 이번 정적 검토는 proposal 본문을 열지 않았으므로50개를 다시 세거나 유효하다고 인증하지 않았다.

원 proposal이 옛 source에서 발견됐다는 사실만으로 최신 manifest와같아야한다고 요구하지 않는다. 대신179:65–99에서 현재 ledger의 report_path 집합에 각 raw label lineage가 있어야 하며 동일 sourcecrop SHA가 정확히한 scene에 연결돼야 한다. 실제 crop path·province/year/label_year·Esri label source URL/연도도 일치해야 한다. 오래된 proposal을 최신 source와 억지로 같은 것으로 간주하지 않고 재사용 가능한 라벨 참조로 검증하는 구조다. 현재원장에 원 report가 빠졌거나 라벨/lineage가 바뀌면 LINEAGE_NOT_LEDGER_BOUND/LABEL_LINEAGE_AMBIGUOUS/FILE_PIN_MISMATCH 등으로 전체검토가 차단된다. 실제 상태는 읽지 않아 미확정이다.

179:71–118은 최대128개 label file/각64MiB/누적768MiB, 같은SHA창 중복거부·10m projected metre CRS/grid/한band dtype·정확 window/좌표·province 내부95%·로컬 raw class8 나지≥256픽셀을 재계수한다. 원시 label 창의 나지는 remote SCL/B02와 최종지원mask 후 적격나지라는 뜻이 아니다. 라벨 bytes와lineage는135–137에서 다시 지문 대조한다. 라벨 누적cap은 캐시에 넣기 전 증가한 raw 크기를 합산한 후 검사하므로 파일1개까지 읽은 뒤 전체초과를 감지할 수 있으며 무한읽기 허용은 아니다.

## 전체 pending/support 및 후보 상호 겹침

167:74–105는 고정sources 폴더와 모든 ledger report parent를 포함하고, 예전smoke/v1·현재 aggregate 밖 파일도 포함한다. label 파일명들은 support 영상 겹침에서 제외되어 재사용 가능하지만, manifest scenes+historical_noneligible 모든 sourcewindow 참조를 품질/연도와 관계없이 추가해 SHA충돌도 검증한다.107–120은 모든 pending의 config semantic SHA와 실제 local rawB02 존재를 요구한다. pending 전체 footprint를 확인하지 못하면 pending검증false/차단이다. 단지 pending 예약금만 보고 footprint를 생략하지 않는다.

167:125–164는 로컬 MemoryFile의 TIFF/CRS/grid를 검사하고 자산 geometry를 모은 뒤 다시 파일집합/identity·config·manifest/ledger를 대조한다.179:120은 inventory_verified/pending_footprints_verified/source_pins_verified 세 boolean이true여야 다음으로 간다. 첫 target이 support와 겹쳐 inventory.status가BLOCKED이더라도 전체 inventory자산검증이 끝난 경우에만 이3flag가true다.179는 그 assets를 재사용해 모든 target의 겹침을 각각 판정하므로 첫후보겹침이 전체50검토를 잘못 중단하지 않는다. resource/핀/pending 오류로3flag가false면 INVENTORY_NOT_VERIFIED로 차단한다.

179:122–134의 TargetedWindowClaims는 각 후보 대 전체 support, 또 각 후보 쌍을 검사한다. 서로 다른 CRS는 densify1024와 보수적margin1m/경위도1e-5를 쓰며 투영 오류는 차단한다. 각독립 claim객체로 역사겹침과후보상호겹침을 분리한다. historical_clear_count가 곧 서로 독립인 확보가능 후보수는 아니다. select_plan:147–153은 최대2개만 선택하고 역사/상호겹침을 모두 거부하지만 실집행권은 만들지 않는다.

## 별도 후속 차단: 실target256 소비의64MiB 제한

`backend/app/data/targeted_bare_plan.py:108`의 prepare_targeted_bare_jobs는 current_manifest_ref를 **64MiB** cap으로 읽는다. `scripts/collect_targeted_bare.py:150`에서 이 함수를 호출하므로,179 select_plan이 만든 current_manifest_ref가 현재309snapshot69564847B라면 이 후속은 FILE_LIMIT로 failclosed될 것으로 코드상 판단한다. collect_targeted_bare.py:138/166의 자체aggregate128MiB와 inventory3GiB 연결만으로 이 내부64MiB 호출까지 해결된 것은 아니다.

이는 이번316→179 읽기검토의 필수 수정 결함과 분리한 **실수집 후속 연결 BLOCKED**다. 현재316 request나원본을 작게복제·분할하거나cap을자동상향해우회하지 않는다. Root가 별도 작은 명시sourceprofile 계약/호출전파·legacy보존·Temp상한/실CLI격리시험을 배정한 뒤 독립검토해야 한다. 이번담당은 제품수정을 하지 않았다. 오류를 숨기고175/176/170실행준비완료라고 보고하지 않는다.

## 실행 판단과 한계

실제proposal50의현재라벨/ledgerlineage·support총량3GiB/파일10000·모든pending·나지/상호겹침결과는 fullreview 전 미확정이다. Root는315 실화면완료 뒤 별도 GO로 단1full179를 실행하고 새결과파일만 기록해야 한다. request CLI SHA는 원문SHA608a…56ee이며 결과의 request_sha256 canonical과 구분한다. 오래걸림/상한초과는원로그/부분결과보존·자동retry상향0이다. CLI는실패시보고서JSON을반드시남기는계약이아니므로 stderr/exit를보존해야한다.

검토성공이어도 execution_supported/actual_quality_eligible/scientifically_verified_bare는false다. 별도실수집의fresh scene/window/split/B02정렬·SCL품질/예산·정산·4GiB/2worker/2초/첫429/물리3000 보호는 여전히 필요하다. 현재 UI/pointer는수정하지않는다. 실제결과를게시할때 Root가API/실브라우저와이해자료·대본FAQINDEX이력에같은소스시점/미검사·집행미승인 의미를인계해야한다. 전체학습·독립정답·운영승인은미완료다.
