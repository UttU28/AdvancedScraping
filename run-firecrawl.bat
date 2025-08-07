@echo off
SET PORT=3002
SET INTERNAL_PORT=3002

echo Starting Docker Compose for FireCrawl...
echo Make sure Docker Desktop is running before proceeding.
pause

echo Building and starting FireCrawl services...
docker compose -p firecrawler -f firecrawl/docker-compose.yaml up --build -d

if %ERRORLEVEL% NEQ 0 (
    echo Error: Docker compose failed to start FireCrawl.
    echo Please make sure Docker Desktop is running and try again.
    exit /b %ERRORLEVEL%
)

echo FireCrawl is running on port %PORT% in the background
echo To stop the service, run: docker compose -p firecrawler down
