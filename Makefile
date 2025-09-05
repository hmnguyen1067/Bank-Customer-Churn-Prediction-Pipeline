SHELL = /bin/bash

getdata:
	mkdir -p ./data
	curl -L -o ./data/bank-customer-churn.zip\
  		https://www.kaggle.com/api/v1/datasets/download/radheshyamkollipara/bank-customer-churn
	unzip ./data/bank-customer-churn.zip -d ./data
	rm ./data/bank-customer-churn.zip