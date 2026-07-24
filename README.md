# Texas Energy & Economy Monitor

A reproducible Python project for collecting, cleaning, validating, integrating, and analyzing Texas electricity-market, weather, and macroeconomic data from public APIs.

The project combines reliable monthly data infrastructure with descriptive analysis, baseline time-series modeling, and pseudo-out-of-sample forecasting. It is designed both as an API and data-engineering exercise and as preliminary research infrastructure for future work in energy economics.

## Project goals

This project is designed to:

- practice working with REST APIs in Python;
- build reproducible EIA and FRED data pipelines;
- organize electricity-market and macroeconomic data into analysis-ready formats;
- document data-cleaning, classification, and variable-construction decisions;
- produce transparent data-quality and coverage reports;
- estimate reproducible baseline time-series association models;
- evaluate short-term forecasting models using a reproducible expanding-window design;
- create a foundation for future energy-economics research.

The current geographic focus is Texas, but the project structure can later be extended to other U.S. states.

## Current progress

### Retail electricity data

- Connected to the EIA API.
- Retrieved monthly Texas retail electricity data from 2015 onward.
- Collected residential, commercial, and industrial-sector observations.
- Retrieved average retail electricity prices, electricity sales, retail revenue, and customer counts.
- Added automatic pagination, data-type conversion, and structural validation.
- Built long-format and wide-format retail-electricity datasets.
- Created month-coverage and missing-value reports.
- Created a sector-level electricity-price visualization.

### Electricity generation data

- Inspected EIA route metadata and facet values.
- Retrieved monthly Texas electricity generation by fuel type.
- Preserved the original EIA fuel codes and descriptions.
- Created a manually reviewed fuel-category mapping.
- Identified and removed overlapping aggregate and subcategory series.
- Standardized fuel groups including Coal, Natural Gas, Other Gases, Petroleum, Nuclear, Hydroelectric, Wind, Solar, Biomass, and Other.
- Built clean long-format and wide-format generation datasets.
- Added fuel-group coverage checks.
- Derived missing aggregate petroleum observations using:

```text
PET = FOS - COW - NG - OOG
```

- Preserved all derived petroleum observations in a separate audit file.
- Reconciled selected fuel components with the EIA reported all-fuels total.
- Added an automated reconciliation tolerance check.

### Integrated monthly energy dataset

- Converted retail-electricity data from sector-level long format to monthly wide format.
- Aligned retail-electricity and generation data by month.
- Merged the two datasets using one-to-one monthly matching.
- Created a merge-coverage report for unmatched months.
- Preserved only months available in both datasets in the main integrated dataset.
- Built the first integrated Texas monthly energy dataset.

### Analysis-ready energy indicators

- Constructed total monthly electricity generation.
- Constructed renewable and fossil-fuel generation totals.
- Calculated renewable, fossil-fuel, nuclear, and fuel-specific generation shares.
- Calculated sector-level electricity sales per customer.
- Calculated sector-level retail revenue per customer.
- Reconstructed retail electricity prices from revenue and sales.
- Created a retail-price validation report.

### Data documentation and descriptive statistics

- Created a formal variable dictionary.
- Documented variable definitions, units, sources, and construction methods.
- Generated descriptive statistics for the main monthly energy indicators.
- Created a variable-coverage and missing-value report.

### Descriptive visualizations

- Visualized retail electricity prices by customer sector.
- Visualized monthly generation by major energy source.
- Compared renewable, fossil-fuel, and nuclear generation shares.
- Visualized fuel-specific generation shares.
- Examined residential electricity sales per customer.

### Time-series features and seasonality

- Constructed trailing 12-month moving averages.
- Constructed year-over-year percentage changes for level variables.
- Constructed year-over-year percentage-point changes for generation shares.
- Added calendar-year, month, and quarter variables.
- Applied robust STL decomposition to selected monthly indicators.
- Created a feature-coverage report.
- Visualized long-run trends and seasonal patterns.

### FRED macroeconomic and energy-price data

- Connected to the FRED API.
- Created a configuration-driven FRED series list.
- Retrieved monthly observations for:
  - Texas unemployment rate;
  - Texas total nonfarm employment;
  - WTI crude-oil price;
  - Henry Hub natural-gas price;
  - U.S. CPI.
- Retrieved and preserved FRED series metadata.
- Standardized all monthly dates to the first day of the month.
- Preserved missing FRED observations as missing values rather than converting them to zero.
- Built long-format and wide-format FRED datasets.
- Created FRED metadata and coverage reports.
- Added automatic retries and HTTP error handling.

### Integrated energy-and-economy dataset

- Merged monthly EIA energy features with monthly FRED variables.
- Used one-to-one monthly merge validation.
- Created an EIA–FRED merge-coverage report.
- Constructed year-over-year Texas employment growth.
- Constructed year-over-year unemployment-rate changes in percentage points.
- Constructed year-over-year WTI and Henry Hub price changes.
- Constructed CPI-adjusted retail electricity prices in January 2025 price levels, measured in cents per kWh.
- Created a variable-coverage report for the integrated dataset.

### Texas weather-data pipeline

- Connected to the NOAA NCEI Climate at a Glance API.
- Retrieved statewide monthly Texas weather indicators.
- Added monthly average temperature and precipitation.
- Added monthly heating and cooling degree days.
- Preserved NOAA departures from the 1901–2000 base period.
- Created weather-series metadata and coverage reports.
- Merged weather data with the existing energy-and-economy dataset.
- Created the final monthly analysis sample and merge report.

### Baseline monthly time-series models

- Added `notebooks/06_baseline_time_series_models.ipynb`.
- Examined the relationship between Henry Hub natural-gas prices and real Texas residential electricity prices.
- Controlled for lagged residential electricity prices, generation shares, heating and cooling degree days, a time trend, and month-of-year effects.
- Estimated static ordinary least-squares models with heteroskedasticity and autocorrelation-consistent standard errors.
- Evaluated residual autocorrelation, multicollinearity, influential observations, and sensitivity to February 2021.
- Compared AR(1) through AR(4) dynamic specifications on common estimation samples.
- Selected a stable AR(3) model using information criteria, residual diagnostics, and model parsimony.
- Obtained a Durbin–Watson statistic of 1.9615 and nonsignificant Breusch–Godfrey tests at maximum lags 1, 6, and 12 for the preferred model.
- Estimated a contemporaneous Henry Hub coefficient of approximately 0.0734 cents per kWh for a $1/MMBtu increase, with a HAC p-value of approximately 0.0006.
- Estimated an autoregressive-coefficient sum of approximately 0.8893 and an implied long-run multiplier of approximately 0.66 cents per kWh.
- Interpreted all model estimates as conditional associations rather than causal effects.

### Pseudo-out-of-sample forecasting

- Added `notebooks/07_out_of_sample_forecasting.ipynb`.
- Compared a previous-month naive benchmark, a seasonal-naive benchmark, and three AR(3) forecasting specifications.
- Generated one-step-ahead forecasts over a continuous 24-month evaluation period from October 2023 through September 2025.
- Re-estimated each regression model using an expanding estimation window.
- Distinguished feasible forecasts using lagged controls from conditional forecasts using realized contemporaneous controls.
- Found that the price-history AR(3) achieved the best overall forecasting performance.
- Reduced RMSE from 0.3008 to 0.2380, a 20.87% improvement relative to the previous-month naive benchmark.
- Reduced MAE from 0.2411 to 0.1969, an improvement of approximately 18.33%.
- Outperformed the previous-month naive benchmark in 15 of the 24 evaluation months.
- Confirmed through leave-one-month-out checks that the improvement was not driven by a single evaluation month.
- Compared forecast accuracy using Harvey–Leybourne–Newbold-corrected Diebold–Mariano tests, a Clark–West test, and an exact sign test.
- Found strong evidence of incremental predictive information in the Clark–West test, while the remaining tests provided weaker or mixed evidence.
- Interpreted the forecasting evidence as promising rather than definitive because of the short evaluation period and model-selection process.

## Data sources

### U.S. Energy Information Administration

The EIA API currently provides retail electricity data, electricity generation by fuel type, and route metadata.

### Federal Reserve Economic Data

The FRED API currently provides Texas labor-market indicators, energy prices, and U.S. CPI.

### NOAA National Centers for Environmental Information

The NOAA Climate at a Glance API provides statewide Texas temperature, precipitation, heating-degree-day, and cooling-degree-day observations.

API keys are stored locally in a `.env` file and are not committed to the repository.

## Repository structure

```text
texas-energy-economy-monitor/
├── config/
│   ├── fred_series.csv
│   ├── fuel_mapping.csv
│   └── weather_series.csv
├── data/
│   ├── metadata/
│   ├── processed/
│   └── raw/
├── docs/
│   └── variable_dictionary.csv
├── notebooks/
│   ├── 01_eia_exploration.ipynb
│   ├── 02_sector_comparison.ipynb
│   ├── 03_descriptive_visualizations.ipynb
│   ├── 04_seasonality_and_trends.ipynb
│   ├── 05_energy_economy_overview.ipynb
│   ├── 06_baseline_time_series_models.ipynb
│   └── 07_out_of_sample_forecasting.ipynb
├── reports/
│   ├── figures/
│   │   ├── baseline_model_4_residual_diagnostics.png
│   │   ├── preferred_ar3_residual_acf_pacf.png
│   │   └── out_of_sample_forecast_performance.png
│   └── tables/
│       ├── energy_indicator_coverage.csv
│       ├── energy_indicator_summary.csv
│       ├── fred_series_coverage.csv
│       ├── fred_series_metadata.csv
│       ├── time_series_feature_coverage.csv
│       ├── energy_economy_correlation_matrix.csv
│       ├── energy_economy_selected_summary.csv
│       ├── wti_employment_lag_correlations.csv
│       ├── weather_series_metadata.csv
│       ├── weather_series_coverage.csv
│       ├── analysis_sample_merge_report.csv
│       ├── analysis_sample_coverage.csv
│       ├── baseline_model_coefficients.csv
│       ├── baseline_residual_diagnostics.csv
│       ├── robustness_henry_hub_effects.csv
│       ├── ar_order_candidate_comparison.csv
│       ├── preferred_ar3_model_results.csv
│       ├── preferred_ar3_residual_correlations.csv
│       ├── out_of_sample_forecasts.csv
│       ├── out_of_sample_forecast_metrics.csv
│       ├── forecast_monthly_win_summary.csv
│       ├── preferred_forecast_monthly_details.csv
│       ├── forecast_leave_one_month_out_results.csv
│       ├── forecast_leave_one_month_out_summary.csv
│       └── forecast_statistical_tests.csv
├── src/
│   ├── build_descriptive_summary.py
│   ├── build_energy_indicators.py
│   ├── build_fred_dataset.py
│   ├── build_generation_dataset.py
│   ├── build_integrated_energy_dataset.py
│   ├── build_price_panel.py
│   ├── build_retail_dataset.py
│   ├── build_time_series_features.py
│   ├── build_variable_dictionary.py
│   ├── create_fred_series_config.py
│   ├── create_fuel_mapping.py
│   ├── fetch_eia.py
│   ├── fetch_fred.py
│   ├── fetch_generation.py
│   ├── finalize_fuel_mapping.py
│   ├── generation_transform.py
│   ├── inspect_generation_metadata.py
│   ├── validate_generation_totals.py
│   ├── build_energy_economy_dataset.py
│   ├── create_weather_series_config.py
│   ├── inspect_weather_api.py
│   ├── fetch_weather.py
│   ├── build_weather_dataset.py
│   └── build_analysis_sample.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/cauchygugugu-web/texas-energy-economy-monitor.git
cd texas-energy-economy-monitor
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

Create a local `.env` file in the project root:

```text
EIA_API_KEY=your_eia_api_key_here
FRED_API_KEY=your_fred_api_key_here
```

Do not commit the `.env` file.

## Running the project

### Build the retail-electricity dataset

```bash
python src/build_retail_dataset.py
```

### Build and validate the clean generation dataset

```bash
python src/build_generation_dataset.py
```

### Build the integrated monthly energy dataset

```bash
python src/build_integrated_energy_dataset.py
```

### Build analysis-ready energy indicators

```bash
python src/build_energy_indicators.py
```

### Build the variable dictionary

```bash
python src/build_variable_dictionary.py
```

### Generate descriptive statistics

```bash
python src/build_descriptive_summary.py
```

### Build time-series features

```bash
python src/build_time_series_features.py
```

### Create the FRED series configuration

```bash
python src/create_fred_series_config.py
```

### Test the FRED API connection

```bash
python src/fetch_fred.py
```

### Build the FRED macroeconomic dataset

```bash
python src/build_fred_dataset.py
```

### Build the integrated energy-and-economy dataset

```bash
python src/build_energy_economy_dataset.py
```

### Create the weather-series configuration
```bash
python src/create_weather_series_config.py
```

### Build the Texas weather dataset
```bash
python src/build_weather_dataset.py
```

### Build the final analysis sample
```bash
python src/build_analysis_sample.py
```

### Run the baseline monthly time-series analysis

After building the final analysis sample, open and run:

```text
notebooks/06_baseline_time_series_models.ipynb
```

### Run the pseudo-out-of-sample forecasting analysis

After running the baseline monthly time-series analysis, open and run:

```text
notebooks/07_out_of_sample_forecasting.ipynb
```

## Generated outputs

Generated data files are stored under:

```text
data/processed/
```

Important FRED outputs include:

```text
fred_tx_macro_energy_long.csv
fred_tx_macro_energy_wide.csv
fred_series_metadata.csv
fred_series_coverage.csv
```

Most generated data files are excluded from version control because they can be reproduced from the source code.

Small documentation and validation outputs are stored under:

```text
reports/tables/
```

The variable dictionary is stored at:

```text
docs/variable_dictionary.csv
```

Important baseline-model outputs include:

```text
reports/tables/baseline_model_coefficients.csv
reports/tables/baseline_residual_diagnostics.csv
reports/tables/robustness_henry_hub_effects.csv
reports/tables/ar_order_candidate_comparison.csv
reports/tables/ar_order_key_coefficients.csv
reports/tables/preferred_ar3_model_results.csv
reports/tables/preferred_ar3_residual_correlations.csv
reports/figures/baseline_model_4_residual_diagnostics.png
reports/figures/preferred_ar3_residual_acf_pacf.png
```

Important forecasting outputs include:

```text
reports/tables/out_of_sample_forecasts.csv
reports/tables/out_of_sample_forecast_metrics.csv
reports/tables/forecast_monthly_win_summary.csv
reports/tables/preferred_forecast_monthly_details.csv
reports/tables/forecast_leave_one_month_out_results.csv
reports/tables/forecast_leave_one_month_out_summary.csv
reports/tables/forecast_statistical_tests.csv
reports/figures/out_of_sample_forecast_performance.png
```

## Data-validation principles

- Raw API responses are not manually overwritten.
- API keys are never stored in committed source files.
- Dates are standardized to monthly datetime values.
- Numeric API fields are explicitly converted from strings.
- Duplicate monthly observations are rejected.
- Aggregate fuel categories are not added to their own subcategories.
- Missing observations are not automatically converted to zero.
- Valid negative generation values are preserved.
- Derived observations are stored separately for auditing.
- Selected fuel components must reproduce reported generation totals within a defined tolerance.
- Retail and generation datasets are merged using one-to-one monthly validation.
- Unmatched months are documented rather than silently discarded.
- FRED frequency, units, seasonal adjustment, and coverage are preserved in metadata reports.
- Competing dynamic models are compared on common estimation samples.
- Preferred-model residual autocorrelation is assessed using Durbin–Watson, Ljung–Box, Breusch–Godfrey, ACF, and PACF diagnostics.
- Forecasting models are evaluated over the same continuous test interval.
- Expanding estimation windows exclude observations from the forecast month and all future months.
- Competing forecasts are compared using identical evaluation observations.
- Leave-one-month-out checks are used to assess whether forecast improvements depend on a single evaluation month.

## Current limitations

- The project currently focuses on Texas.
- The empirical analysis is observational and does not identify causal effects.
- Some EIA and FRED observations may be revised by the data providers.
- Source series may have different publication lags and latest available months.
- Statewide monthly averages conceal variation across utilities, retail plans, customer groups, and regions.
- The dynamic specification approximates potentially heterogeneous and nonlinear retail-price adjustment.
- The implied long-run multiplier is sensitive to uncertainty in the estimated autoregressive persistence.
- The pseudo-out-of-sample evaluation contains only 24 monthly forecasts.
- The preferred forecasting model was selected after comparing several candidate specifications.
- The forecasting design does not incorporate publication delays, historical data vintages, or subsequent data revisions.
- Quarterly state GDP and detailed industry-level labor-market data have not yet been added.

## Next milestone

The project now contains a reproducible data pipeline, a baseline explanatory time-series model, and an expanding-window forecasting evaluation. Potential next steps include:

- extending the forecasting evaluation as additional monthly observations become available;
- evaluating forecast combinations and additional parsimonious benchmarks;
- adding wholesale electricity-price measures;
- examining nonlinear or asymmetric natural-gas price transmission;
- studying variation across utilities, retail plans, or Texas regions where suitable data are available;
- developing a formal identification strategy for causal analysis.

## Research direction

The project may later support research on renewable-energy penetration, retail electricity prices, natural-gas dependence, energy-price shocks, regional economic activity, and changes in the Texas electricity-generation mix.

At the current stage, the priority remains data reliability, transparent variable construction, reproducible model comparison, and cautious interpretation rather than causal inference.

## License

The project code is licensed under the [MIT License](LICENSE).

Data retrieved from EIA, FRED, and NOAA remains subject to the respective data providers' terms and policies.