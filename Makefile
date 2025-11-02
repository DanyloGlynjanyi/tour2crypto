PYTHON ?= python

.PHONY: test sample report db-migrate db-seed pipeline-demo bot-simulate api-run sync-export

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

api-run:
$(PYTHON) scripts/api_run.py

sync-export:
$(PYTHON) scripts/sync_export.py
