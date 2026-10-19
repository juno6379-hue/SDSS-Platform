# G14 — SDSS 배포 아키텍처 및 환경 분리 결정서 (Deployment Architecture)

> **규격**: CODEX v3.0 Section 10  
> **환경 구분**: Development (로컬/파일럿) $\to$ Staging (통합 시험) $\to$ Production (운영 배포)  

---

## 1. 3대 배포 계층 분리

1. **Development (로컬/파일럿)**:
   - Docker Compose: FastAPI API (8002), Vite UI (5174), GeoServer (8088), SQLite/PostgreSQL
   - 파일 기반 COG 저장소 및 로컬 체크포인트 캐시
2. **Staging (사전 통합 환경)**:
   - k8s Staging 네임스페이스 (`sdss-staging`)
   - PostgreSQL/PostGIS 복제본 및 독립 검증 데이터셋
3. **Production (운영 서비스)**:
   - K8s High-Availability Pods (3/3), Ingress TLS 종료
   - 공식 승인 모델 (`challenger_scl_v1_2_0`) 전용 무중단 서빙
