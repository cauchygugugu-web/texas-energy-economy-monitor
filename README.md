# Texas Energy & Economy Monitor

A reproducible Python project for collecting, cleaning, validating, integrating, and analyzing Texas electricity-market and macroeconomic data from public APIs.

The project currently focuses on building reliable monthly data infrastructure before moving into more formal economic analysis. It is designed both as an API and data-engineering exercise and as preliminary research infrastructure for future work in energy economics.

## Project goals

This project is designed to:

- practice working with REST APIs in Python;
- build reproducible EIA and FRED data pipelines;
- organize electricity-market and macroeconomic data into analysis-ready formats;
- document data-cleaning, classification, and variable-construction decisions;
- produce transparent data-quality and coverage reports;
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
- Constructed CPI-adjusted retail electricity prices in January 2025 dollars.
- Created a variable-coverage report for the integrated dataset.

## Data sources

### U.S. Energy Information Administration

The EIA API currently provides retail electricity data, electricity generation by fuel type, and route metadata.

### Federal Reserve Economic Data

The FRED API currently provides Texas labor-market indicators, energy prices, and U.S. CPI.

API keys are stored locally in a `.env` file and are not committed to the repository.

## Repository structure

```text
texas-energy-economy-monitor/
├── config/
│   ├── fred_series.csv
│   └── fuel_mapping.csv
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
│   └── 04_seasonality_and_trends.ipynb
├── reports/
│   ├── figures/
│   └── tables/
│       ├── energy_indicator_coverage.csv
│       ├── energy_indicator_summary.csv
│       ├── fred_series_coverage.csv
│       ├── fred_series_metadata.csv
│       └── time_series_feature_coverage.csv
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
│   └── build_energy_economy_dataset.py
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

## Current limitations

- The project currently focuses on Texas.
- The analysis remains primarily descriptive.
- Some EIA and FRED observations may be revised by the data providers.
- Source series may have different publication lags and latest available months.
- No causal conclusions are drawn from the current datasets.
- Quarterly state GDP and detailed industry-level labor-market data have not yet been added.

## Next milestone

The next stage is to create the first descriptive overview
of the integrated Texas energy-and-economy dataset.

Planned work includes:

- real retail electricity prices and natural-gas prices;
- Texas employment growth and crude-oil price changes;
- renewable generation shares and real electricity prices;
- correlation and lag-pattern exploration;
- documentation of descriptive relationships without causal claims.

## Research direction

The project may later support research on renewable-energy penetration, retail electricity prices, natural-gas dependence, energy-price shocks, regional economic activity, and changes in the Texas electricity-generation mix.

At the current stage, the priority is data reliability, transparent variable construction, and reproducibility rather than causal inference.

## License

A license has not yet been selected.
