@echo off
SET PORT=3002
SET INTERNAL_PORT=3002

docker compose -p firecrawler -f firecrawl/docker-compose.yaml up -d

echo FireCrawl is running on port %PORT% in the background
echo To stop the service, run: docker compose -p firecrawler down 