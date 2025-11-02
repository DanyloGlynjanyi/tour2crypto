PYTHON ?= python

.PHONY: test sample report db-migrate db-seed pipeline-demo bot-simulate api-run sync-export report-daily report-weekly env-example diag

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

report-daily:
	$(PYTHON) scripts/report_daily.py

report-weekly:
	$(PYTHON) scripts/report_weekly_pnl.py

env-example:
	$(PYTHON) scripts/make_env.py

diag:
	$(PYTHON) scripts/diag_run.py
