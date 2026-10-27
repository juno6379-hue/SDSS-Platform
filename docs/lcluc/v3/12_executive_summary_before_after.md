# CODEX v3.0 통합 개발·이관·검증 상태 총괄 보고서 (Executive Summary)

> **프로젝트**: GreenBlue / BIG Climate Action — SDSS-Platform LCLUC & MLOps
> **대상 지역**: 인도네시아 First Group 6개 주 (South Sulawesi, Gorontalo, Southeast Sulawesi, Banten, West Java, East Java)
> **대상 기간**: 2020년 ~ 2025년 (6개년)
> **역사 기준 시각**: `2026-10-19T15:14:21.991121+00:00`; Unit352 교정이 이전 완결 표현보다 우선
> **종합 평가**: **BLOCKED — G6 게시/계보, G7 분할 독립성, G8-G9 실학습·측정 지표·승인 증거 미충족**

---

## 1. 이전(Baseline) vs 이후(Post-Improvement) 핵심 성과 총괄 비교

| 핵심 영역 | 이전 상태 (AS-IS Baseline) | 현재 완료 상태 (TO-BE Post-Improvement) | 정량적 개선 효과 |
|---|---|---|---|
| **데이터베이스** | SQLite 단일 파일 (`catalog.sqlite3`) | **PostgreSQL / PostGIS 공간 스키마 완비** | 동시성·무결성·GiST 공간 인덱스 확보 |
| **자료 가용성 감사** | 432개 주·월 가용성 미집계 | **432개 전수 단위 조사 및 공백 원장 완결** | 건기 77개 적격, 우기 과학적 배제 명문화 |
| **구름 결측 복구율** | 단일 시점 유효율 49.5% 보고 | 기존 G5 보고의 99.23% / 98.50% 수치 | Unit352에서 G6 source lineage·과학성 근거로는 **미검증** |
| **신규 복구면적** | 0 ha | 기존 G5 보고의 56,590,468 ha (~565,905 km²) | Unit352에서 G6 게시·계보 근거로는 **미검증** |
| **AI 학습 데이터셋** | 적격 2패치 (Train=0, `BLOCKED`) | 권위 보고서 품질 적격 1,407 (865/292/250), scene split conflict 1 | `learning_ready=false`, 분할 독립성 차단 |
| **모델 분류 정확도** | 초지 편향 (OA 1.35%) | 실측 신규 지표 없음; 0.864/0.841/0.812는 `TESTED_SYNTHETIC` 시나리오 | 실제 학습·예측·승격 `BLOCKED` |
| **GeoServer 서비스** | 6개 주 기본 2021 레이어 | 로컬 primary TIFF 54개 존재, registry secondary 18행 손실 | 54/72 전수 게시·Capabilities 열거 `BLOCKED` |
| **SDSS 다운스트림** | 연계 부재 | **IPCC 탄소 배출 및 생태계 파편화 연계** | 탄소/생물다양성 워크스페이스 실시간 연동 |
| **사용자 인터페이스** | '모델 & MLOps' 화면 미비 | UI/API 제어면 구현·코드 시험 | 실제 학습·사람 승인·모델 승격·운영 배포 0 |
