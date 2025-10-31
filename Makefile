PYTHON ?= python

.PHONY: test sample

test:
$(PYTHON) -m pytest -v

sample:
$(PYTHON) -m t2c_contracts.sample
