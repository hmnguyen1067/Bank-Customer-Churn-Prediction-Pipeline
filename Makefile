SHELL = /bin/bash

data:
	mkdir -p ./data
	curl -L -o ./data/bank-customer-churn.zip\
  		https://www.kaggle.com/api/v1/datasets/download/radheshyamkollipara/bank-customer-churn
	unzip ./data/bank-customer-churn.zip -d ./data
	rm ./data/bank-customer-churn.zip

report: data
	python ./scripts/initial_report.py

docker-up:
	docker compose -f infra/docker-compose.yaml --env-file infra/config/config.env up -d --build

docker-down:
	docker compose -f infra/docker-compose.yaml down