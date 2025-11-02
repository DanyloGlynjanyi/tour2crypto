PYTHON ?= python

.PHONY: test sample report db-migrate db-seed pipeline-demo bot-simulate

test:
	$(PYTHON) -m pytest -v

sample:
	$(PYTHON) -m t2c_contracts.sample

report:
	$(PYTHON) scripts/e2e_report.py

db-migrate:
	$(PYTHON) db/migrate.py

db-seed:
	$(PYTHON) db/seed.py

pipeline-demo:
	$(PYTHON) scripts/pipeline_demo.py

bot-simulate:
	$(PYTHON) scripts/bot_simulate.py
