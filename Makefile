.PHONY: all clean setup base stats confounds regional timeseries police crossval plots report fetch-nzta

PYTHON = python3
SRC = src
OUT = output

all: setup base stats confounds regional timeseries police crossval plots report

setup:
	pip install -r requirements.txt --break-system-packages -q

base:
	cd $(SRC) && $(PYTHON) base_rate_analysis.py

stats:
	cd $(SRC) && $(PYTHON) statistical_tests.py

confounds:
	cd $(SRC) && $(PYTHON) confound_model.py

regional:
	cd $(SRC) && $(PYTHON) regional_analysis.py

timeseries:
	cd $(SRC) && $(PYTHON) time_series_analysis.py

police:
	cd $(SRC) && $(PYTHON) police_data_analysis.py

crossval:
	cd $(SRC) && $(PYTHON) cross_source_validation.py

plots:
	cd $(SRC) && $(PYTHON) visualisation.py

report:
	cd $(SRC) && $(PYTHON) report_generator.py

fetch-nzta:
	cd $(SRC) && $(PYTHON) nzta_fetcher.py --fetch-nzta

clean:
	rm -rf $(OUT)/*.csv $(OUT)/*.md $(OUT)/figures/*.png
