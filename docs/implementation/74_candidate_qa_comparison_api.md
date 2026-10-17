# 74. 원본/후보 QA 보고서의 최소 읽기 비교 API

상태: **TESTED_SYNTHETIC / BLOCKED**. 기존 저장 보고서 4개만 읽어 정책·출처 역할·계수·차단·나지 부족 관측을 비교한다. source/candidate 53MB manifest, 영상/라벨/QA raster, assess, Registry/Job/DB는 읽거나 실행하지 않는다. 실제 HTTP·실행 서버·브라우저·전체 회귀는 Root와 UI 담당의 별도 근거로 연결한다.

## 코드와 고정 입력

- `backend/app/ml/candidate_qa_comparison.py`: 순수 `project_candidate_qa`와 bounded `compare_candidate_qa(data_root, pins)`.
- `backend/app/candidate_qa_comparison_api.py`: `create_candidate_qa_comparison_router(get_store)`; Root가 main.py에 배선한다.
- `tests/test_candidate_qa_comparison.py`: 작은 합성 4JSON·HTTP 검증.

Store에서는 root만 조회하고 쓰기·복구·등록 메서드는 호출하지 않는다. 기존32코어/원본/원장/lock/예약/분할/모델을 수정하지 않는다. caller 파일 경로 입력은 없다.

| 요청 pin 키 | 고정 DATA 경로 | 한도 |
|---|---|---|
| original_report_sha256 | first-group/readiness-resume-20261017.json | 16MiB |
| candidate_report_sha256 | first-group-candidate-readiness-qa-20261017/readiness.json | 16MiB |
| qa_receipt_sha256 | first-group-candidate-readiness-qa-20261017/qa-receipt.json | 64KiB |
| staging_receipt_sha256 | first-group-candidate-qa-stage-20261017/staging-receipt.json | 64KiB |

원본은 진단66 보고서가 아닌 기존6e59c3…34db readiness다. 입력 pin은 caller가 별도 근거로 고정한다. 각 파일은 별도 strict bounded context에서 처음과 끝에 읽어 SHA·regular-file stat/fstat·논리 경로/target을 확인한다. 4개 최초 read가 끝나기 전에 모든 경로·크기를 사전 확인한다. 최대 설정 read 합은 한 pass32.125MiB, 두 pass64.25MiB이며 per-read cap과 누적 IO/RAM/CPU hard cap은 구분한다. strict UTF8/no BOM/NUL·duplicate/nonfinite·깊이32를 적용한다. source/candidate의 메타 경로는 순수 lexical key로 대조하며 파일을 열거나 hash하지 않는다. 다중 파일 원자 snapshot을 보장하지 않는다.

## 요청·오류·동시 실행

`POST /v1/diagnostics/candidate-readiness-comparison`만 제공한다. body를 stream으로 읽으며 2,048바이트를 넘으면 413, 파싱 전 깊이8과 strict UTF8/중복/비유한 값을 검사한다. JSON 키는 아래 네 개만 허용하며 값은 exact string 소문자64hex다. 요청·응답 schema는 코드와 OpenAPI에 같은 객체로 연결한다.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "original_report_sha256",
    "candidate_report_sha256",
    "qa_receipt_sha256",
    "staging_receipt_sha256"
  ],
  "properties": {
    "original_report_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "candidate_report_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "qa_receipt_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "staging_receipt_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    }
  }
}
```

응답과 처리한 오류는 `Cache-Control: no-store`다. GET은 제공하지 않으며 프레임워크 기본405는 별도다. 기존67과 같은 exact 오류 JSON만 반환하고 예외 문자열·절대경로·원문 차단 detail은 노출하지 않는다.

| HTTP | code | message | retryable |
|---|---|---|---|
| 400 | INVALID_REQUEST | Invalid diagnostic request. | false |
| 409 | PINNED_INPUT_CONFLICT | Pinned diagnostic inputs changed or do not match. | false |
| 413 | REQUEST_TOO_LARGE | Diagnostic request exceeds body limit. | false |
| 429 | DIAGNOSTIC_BUSY | A diagnostic inspection is already running. | true |
| 503 | RESOURCE_UNAVAILABLE | Stored diagnostic is unavailable. | false |

429에는 `Retry-After: 1`을 붙인다. worker 내부에서 nonblocking semaphore를 획득/해제하여 HTTP coroutine이 취소되어도 실제 threadpool 읽기가 끝나기 전에 해제하지 않는다. 제한은 라우터/프로세스당1개이며 여러 프로세스/다른 API를 조율하는 분산 잠금이 아니다.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "error"
  ],
  "properties": {
    "error": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "code",
        "message",
        "retryable"
      ],
      "properties": {
        "code": {
          "enum": [
            "INVALID_REQUEST",
            "REQUEST_TOO_LARGE",
            "PINNED_INPUT_CONFLICT",
            "RESOURCE_UNAVAILABLE",
            "DIAGNOSTIC_BUSY"
          ]
        },
        "message": {
          "type": "string"
        },
        "retryable": {
          "type": "boolean"
        }
      }
    }
  }
}
```

## cross-reference·정책·계수 검증

현재 API는 old/new 모두 blocked·ready/science false인 저장 scope만 지원한다. 4pin은 다음 의미로 연결한다.

- original report pin = stage.input_pins.readiness = QA receipt.inputs.old_readiness; 원본 report source pin은 stage.input_pins.source와 같다.
- staging receipt pin = QA receipt.inputs.staging_receipt.
- candidate report pin/size = QA receipt.readiness_report의 pin/size.
- 새 QA 단일 manifest pin/path = stage.staged_candidate = QA receipt.inputs.candidate = stage.verified_package_outputs.candidate. 원본 source 역할과 새 candidate 역할을 혼동하지 않는다.

QA/stage receipt는 정확한 키·typed 상태·true 메타 검증/QA 수행·false 실행 권한·refund0/exactly_onceUNKNOWN·입출력 이름/SHA/크기/행 수 범위/version을 확인한다. completion_contract는 bounded 문자열이며 문구 전체의 byte 동일성을 요구하지 않는다. stage의 source/candidate 물리 행 수는 검증한 저장 **선언**이고 원본 manifest를 다시 센 결과가 아니다. QA receipt의 saved_blockers/patch_counts/capture_status는 새 보고서와 전체 typed 동일해야 한다.

old/new 정책과 band/label signature는 전체 typed 동일해야 한다. 고정6주 map·2020~2025·6bands·patch256, required class의 exact int0..8/중복 없음/7포함, min bare 기준과 signature6키/band indices/label source/class names9/bare7을 확인한다. 전체 readiness gate나 과거 실행 코드를 재검증하는 기능은 아니다.

class arrays는9개 exact unsigned 정수이며 픽셀은 JS safe integer 이하, 클래스 패치 계수는3000 이하로 제한한다. 각 클래스 패치 수는 해당 eligible 수 이하, 픽셀 합은 eligible×256² 이하이어야 한다. split eligible 각0..3000/총합0..9000, blocked report의 blocker는1..10000개, 코드는 대문자 안전 식별자 regex와 unique32개 이하로 제한한다.

차단은 set으로 줄이지 않고 Counter로 빈도를 보존한다. `REFERENCE_CLASS_IMBALANCE`3개를1개로 바꾸지 않는다. 빈도 배열은 코드순 유일하며 각 측 합이 blocker_count다. 공유 source 항목의 old/new 관측 bool은 해당 코드 빈도>0에서 계산한다. 나지 부족 관측은 각 split의 bare pixels<정책 minimum 또는 bare patch count<정책 minimum 중 하나라도 있으면 true다. shortage_resolved는 항상 false다. 임의의 threshold·새 클래스 계산/픽셀 접근은 없다.

진단 capture의 비실행·IO/refund·존재하는 training/historical/provenance false를 확인한다. CAPTURED 상태는 scope/match상태·candidate inputrefs·typed scene수·patch합을 대조한다. 실패/미수집이면 scene count를 null/NOT_CAPTURED로 표시하며 성공으로 추정하지 않는다. 전체 witness 이벤트/공간 독립성을 재생하지 않는다.

## 정확한 응답 schema

코드의 RESPONSE_SCHEMA를 아래에 그대로 기록했다. cross-field 제약은 schema만으로 끝나지 않고 앞서 설명한 backend 및 UI strict adapter에서 함께 검사한다.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "status",
    "scope",
    "pins",
    "original",
    "candidate",
    "blocker_frequencies",
    "shared_source_blocker",
    "row_counts",
    "bare_class",
    "automatic_resume_allowed",
    "exact_row_binding_verified",
    "execution_authorized",
    "ready_for_training",
    "registry_called",
    "scientific_accuracy_validated",
    "settlement_authorized",
    "source_authenticity_verified",
    "training_executed",
    "training_split_leakage_resolved"
  ],
  "properties": {
    "schema_version": {
      "type": "integer",
      "const": 1
    },
    "status": {
      "const": "BLOCKED"
    },
    "scope": {
      "const": "PINNED_REPORT_COMPARISON_ONLY"
    },
    "pins": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "original_report_sha256",
        "candidate_report_sha256",
        "qa_receipt_sha256",
        "staging_receipt_sha256"
      ],
      "properties": {
        "original_report_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "candidate_report_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "qa_receipt_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "staging_receipt_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        }
      }
    },
    "original": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "eligible_patches_by_split",
        "eligible_patch_count",
        "blocker_count"
      ],
      "properties": {
        "eligible_patches_by_split": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "train",
            "val",
            "test"
          ],
          "properties": {
            "train": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            },
            "val": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            },
            "test": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            }
          }
        },
        "eligible_patch_count": {
          "type": "integer",
          "minimum": 0,
          "maximum": 9000
        },
        "blocker_count": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000
        }
      }
    },
    "candidate": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "eligible_patches_by_split",
        "eligible_patch_count",
        "blocker_count"
      ],
      "properties": {
        "eligible_patches_by_split": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "train",
            "val",
            "test"
          ],
          "properties": {
            "train": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            },
            "val": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            },
            "test": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            }
          }
        },
        "eligible_patch_count": {
          "type": "integer",
          "minimum": 0,
          "maximum": 9000
        },
        "blocker_count": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10000
        }
      }
    },
    "blocker_frequencies": {
      "type": "array",
      "minItems": 1,
      "maxItems": 32,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "code",
          "original_count",
          "candidate_count"
        ],
        "properties": {
          "code": {
            "type": "string",
            "pattern": "^[A-Z][A-Z0-9_]{0,63}$"
          },
          "original_count": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10000
          },
          "candidate_count": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10000
          }
        }
      }
    },
    "shared_source_blocker": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "code",
        "original_observed",
        "candidate_observed",
        "absence_proves_independence"
      ],
      "properties": {
        "code": {
          "const": "SHARED_SOURCE_CROSSES_FIXED_SPLIT"
        },
        "original_observed": {
          "type": "boolean"
        },
        "candidate_observed": {
          "type": "boolean"
        },
        "absence_proves_independence": {
          "type": "boolean",
          "const": false
        }
      }
    },
    "row_counts": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "original_report_physical_scene_count",
        "original_report_scope",
        "source_rows_declared",
        "candidate_rows_declared",
        "declared_scope",
        "candidate_appended_scene_count",
        "candidate_capture_scope"
      ],
      "properties": {
        "original_report_physical_scene_count": {
          "type": "null"
        },
        "original_report_scope": {
          "const": "NOT_PERSISTED"
        },
        "source_rows_declared": {
          "type": "integer",
          "minimum": 0,
          "maximum": 100000
        },
        "candidate_rows_declared": {
          "type": "integer",
          "minimum": 0,
          "maximum": 100000
        },
        "declared_scope": {
          "const": "PINNED_STAGING_RECEIPT_DECLARATION"
        },
        "candidate_appended_scene_count": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 0,
          "maximum": 2000
        },
        "candidate_capture_scope": {
          "enum": [
            "STORED_QA_CAPTURE",
            "NOT_CAPTURED"
          ]
        }
      }
    },
    "bare_class": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "class_index",
        "class_name",
        "original_pixels_by_split",
        "candidate_pixels_by_split",
        "original_patch_counts_by_split",
        "candidate_patch_counts_by_split",
        "required_min_pixels_per_split",
        "required_min_class_patches_per_split",
        "candidate_shortage_observed",
        "shortage_resolved"
      ],
      "properties": {
        "class_index": {
          "type": "integer",
          "const": 7
        },
        "class_name": {
          "const": "bare"
        },
        "original_pixels_by_split": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "train",
            "val",
            "test"
          ],
          "properties": {
            "train": {
              "type": "integer",
              "minimum": 0,
              "maximum": 9007199254740991
            },
            "val": {
              "type": "integer",
              "minimum": 0,
              "maximum": 9007199254740991
            },
            "test": {
              "type": "integer",
              "minimum": 0,
              "maximum": 9007199254740991
            }
          }
        },
        "candidate_pixels_by_split": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "train",
            "val",
            "test"
          ],
          "properties": {
            "train": {
              "type": "integer",
              "minimum": 0,
              "maximum": 9007199254740991
            },
            "val": {
              "type": "integer",
              "minimum": 0,
              "maximum": 9007199254740991
            },
            "test": {
              "type": "integer",
              "minimum": 0,
              "maximum": 9007199254740991
            }
          }
        },
        "original_patch_counts_by_split": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "train",
            "val",
            "test"
          ],
          "properties": {
            "train": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            },
            "val": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            },
            "test": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            }
          }
        },
        "candidate_patch_counts_by_split": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "train",
            "val",
            "test"
          ],
          "properties": {
            "train": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            },
            "val": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            },
            "test": {
              "type": "integer",
              "minimum": 0,
              "maximum": 3000
            }
          }
        },
        "required_min_pixels_per_split": {
          "type": "integer",
          "minimum": 256,
          "maximum": 65536
        },
        "required_min_class_patches_per_split": {
          "type": "integer",
          "minimum": 5,
          "maximum": 3000
        },
        "candidate_shortage_observed": {
          "type": "boolean"
        },
        "shortage_resolved": {
          "type": "boolean",
          "const": false
        }
      }
    },
    "automatic_resume_allowed": {
      "type": "boolean",
      "const": false
    },
    "exact_row_binding_verified": {
      "type": "boolean",
      "const": false
    },
    "execution_authorized": {
      "type": "boolean",
      "const": false
    },
    "ready_for_training": {
      "type": "boolean",
      "const": false
    },
    "registry_called": {
      "type": "boolean",
      "const": false
    },
    "scientific_accuracy_validated": {
      "type": "boolean",
      "const": false
    },
    "settlement_authorized": {
      "type": "boolean",
      "const": false
    },
    "source_authenticity_verified": {
      "type": "boolean",
      "const": false
    },
    "training_executed": {
      "type": "boolean",
      "const": false
    },
    "training_split_leakage_resolved": {
      "type": "boolean",
      "const": false
    }
  }
}
```

original/candidate에는 split eligible·그 합·blocker 수만 반환한다. 원문 path·token·source/candidate JSON·장면 목록·차단 detail은 반환하지 않는다. 최상위 statusBLOCKED와 false10은 원본 인증·정확 binding·학습/과학/실행·등록·누출 해소·정산/자동재개 승인을 하지 않는다는 뜻이다.

특히 `original_report_physical_scene_count=null / NOT_PERSISTED`다. 원본 report에 없는 장면 수를1111 patch나 stage source1384에서 추정하지 않는다. source_rows_declared1384/candidate_rows_declared1368은 PINNED_STAGING_RECEIPT_DECLARATION, 새 appended scene1368은 STORED_QA_CAPTURE로 구분한다. CAPTURED count가 선언 candidate 수와 다르면 거부한다.

## 현재 관측 예시와 한계

Root가 앞 단위에서 확인한 현재 수치를 설명하는 계약 예시다. 이 표는 이번 API 실제 HTTP 성공을 대신하는 증거가 아니며 Root의 별도 실행으로 확인한다.

| 항목 | 원본 | 후보 |
|---|---:|---:|
| eligible train / val / test | 628 / 233 / 250 | 628 / 217 / 250 |
| eligible 합 | 1111 | 1095 |
| blocker 합 | 5 | 4 |
| CLASS_COVERAGE | 1 | 1 |
| REFERENCE_CLASS_IMBALANCE | 3 | 3 |
| SHARED_SOURCE_CROSSES_FIXED_SPLIT | 1 | 0 |
| bare pixel train / val / test | 1418 / 209 / 1025 | 1418 / 209 / 1025 |
| bare patch train / val / test | 0 / 0 / 0 | 0 / 0 / 0 |

기준은 bare pixels256/클래스 포함 patch5다. 나지 부족은 계속 관측되며 전체 개발 queue2 문제가 해결된 것이 아니다. 공유 source 차단 항목이 새 QA에서 **미관측**이라는 결과는 정확한 기하/독립성·모든 누출 해결의 증명이 아니다. 기존 선언 선택과 저장 QA의 비교이며 현재 영상 재검증·새 assess/Registry 실행을 하지 않는다.

## 시험·UI 인계

관련 합성/API 시험: **17 PASS / 14.400초 / 종료0**, `evidence/integration/candidate-qa-comparison-related-20261017.log`. 독립17 PASS /17.124초는 별도 검토이며 중복 합산하지 않는다. 기존 httpx/Starlette deprecation 경고가 있으나 시험은 통과했다.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_candidate_qa_comparison -v
```

작은 합성 4JSON만 사용했다. pin 역할/size/path·정책/signature/false/type·counter중복·bare상한/부족·원본장면null/선언/캡처 scope·stale·입력cap/strictJSON·정확히4파일8open/바이트보존·무assess/순수projection무IO·OpenAPI exact키·2KiB/body/privacy/no-store·pin409·worker busy/취소 후해제/회복을 확인했다. source/candidate53MB 및 실제 QA를 담당이 읽거나 호출하지 않았다.

web_ui에 exact4pin/응답 schema/수치 상한·교차제약·오류 계약을 인계했다. UI75는 LCLUC 근거 탭에서 사용자 명시 조회만 하고 mount/메뉴 이동에 자동 POST나 assess를 붙이지 않는다. 경로/거대JSON은 노출하지 않고 원본/후보·선언/관측·차단 미관측/미해결을 구분한다. Root가 main 최소배선·실제HTTP/브라우저·전체 회귀·141보호/32기존 계약·catalog 보존 및 운영/이해자료 갱신을 맡는다. 구현·테스트와 실제 실행 서버 적용을 구분하며 단일 API/UI 완료를 전체 프로젝트 완료로 보지 않는다.


## Root 실제 통합·보존 확인

main.py에 router import/include 두 줄을 연결하고 API8002 및 Vite5174에서 실제 저장 자료 비교를 확인했다. HTTP200에서 원본1111/후보1095·차단5/4·REFERENCE_CLASS_IMBALANCE 빈도3·나지209/기여패치0·원본 물리 장면null/선언1384→1368/후보 QA 캡처1368·승인10false를 대조했다. 잘못된 핀409·bool형식400·2049바이트413·GET405, POST no-store와 경로/보고서 원문 비노출을 확인했다. 근거는 `evidence/integration/candidate-qa-comparison-live-http-20261017.json`이다. 이번 비교는 새 QA·학습을 수행하지 않는다.

전체 backend761개 중760 PASS·기존 OS symlink 제약1 SKIP /398.767초/종료0이다. `candidate-qa-comparison-full-tests-20261017.log`와 관련17/독립17 시험은 중복 합산하지 않는다. 보호141참조/기존코어32 SHA·catalog14행 canonical SHA 불변, 직전 추적 backend/scripts/tests/data/frontend의 변경은 승인한 main.py와 AgentCenter.tsx뿐이다. 새 구현 파일은 별도 추가했으며 전체 workspace/원자적 snapshot 불변을 뜻하지 않는다. `candidate-qa-comparison-live-integrity-20261017.json`을 따른다.

UI 실제 브라우저 성공·입력 변경/409/뒤로·앞으로 결과 무효화·수정후 신규 콘솔0과 초기중복key6 이력은 [문서75](75_candidate_qa_comparison_ui.md)와 `candidate-qa-comparison-ui-live-20261017.json`에 기록했다. 최종 UI신규13/전체72 PASS·build75modules18.69초, 독립최종13 PASS382.2987ms다. 원본1111/5와 후보1095/4의 근거 및 미해결 나지·미승인 상태는 유지한다.


## 후속 내부 나지 요구 계약

비교 응답의 나지 부족을 더 구체적으로 설명하는 읽기 전용 내부 CLI를 [문서76](76_bare_class_requirements.md)에 추가했다. 바닥 픽셀 부족·기여 patch 부족·같은 분할9클래스 전체 픽셀 대비 비율을 구분하고 저장 balance 메타데이터를 대조한다. 이번 comparator API/응답 및 UI 카드 계약은 변경하지 않았으며, 내부 CLI 결과를 화면에 자동 조회하거나 데이터/승인 상태로 대체하지 않는다. 후보 적격1095/차단4·나지 미해결 및10개 승인false도 그대로다.
