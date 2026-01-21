# Docker 설정 파일 모음

이 폴더는 프로젝트의 다양한 서비스를 위한 Docker 설정 파일들을 모아둔 곳입니다.

## 📁 파일 구조

- `Dockerfile.scentmap` - 향수맵(scentmap) 서비스용 Dockerfile

## 🚀 Scentmap 서비스 사용법

### 1. Docker만 사용하는 경우

```bash
# scentmap 디렉토리에서 빌드
cd Scentence/scentmap
docker build -f ../docker/Dockerfile.scentmap -t scentmap:latest .

# 컨테이너 실행
docker run -d \
  --name scentmap-service \
  -p 8001:8001 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  scentmap:latest
```

### 2. Docker Compose 사용하는 경우

`docker-compose.scentmap.example.yml`의 내용을 메인 `docker-compose.yml` 파일의 `services` 섹션에 추가한 후:

```bash
# Scentence 디렉토리에서 실행
cd Scentence

# scentmap 서비스만 실행
docker-compose up scentmap

# 전체 서비스 실행
docker-compose up
```

## 🔧 Build Context 설명

### Scentmap Dockerfile
- **Build Context**: `Scentence/scentmap/`
- **Dockerfile 위치**: `Scentence/docker/Dockerfile.scentmap`
- **빌드 명령어 예시**: 
  ```bash
  docker build -f docker/Dockerfile.scentmap -t scentmap:latest scentmap/
  ```

## 📝 환경 변수

Scentmap 서비스에 필요한 주요 환경 변수:

```env
DATABASE_URL=postgresql://scentence:scentence@localhost:5433/scentence_db
PERFUME_DATABASE_URL=postgresql://scentence:scentence@localhost:5433/perfume_db
MEMBER_DATABASE_URL=postgresql://scentence:scentence@localhost:5433/member_db
RECOM_DATABASE_URL=postgresql://scentence:scentence@localhost:5433/recom_db
DB_HOST=db
DB_PORT=5432
PYTHONUNBUFFERED=1
```

## 🔍 포트 정보

- **Scentmap**: 8001
- **Backend**: 8000  
- **Frontend**: 3000
- **PostgreSQL**: 5433 (호스트) -> 5432 (컨테이너)

## 💡 팁

1. **개발 모드**: `--reload` 플래그가 활성화되어 있어 코드 변경 시 자동으로 재시작됩니다.
2. **볼륨 마운트**: 로컬 코드가 컨테이너에 마운트되어 실시간 개발이 가능합니다.
3. **헬스체크**: 컨테이너 상태를 모니터링하여 자동으로 재시작합니다.
