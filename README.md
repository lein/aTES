# aTES

## How to start
```
docker network create popug-jira
docker-compose build
docker-compose run oauth rake db:create
docker-compose run oauth rake db:migrate
docker-compose up -d
```
