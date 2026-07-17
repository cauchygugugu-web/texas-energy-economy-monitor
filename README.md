# Texas Energy & Economy Monitor

A reproducible Python project for collecting, cleaning, validating, and organizing Texas electricity-market data from public APIs.

The project is currently focused on building a reliable monthly energy dataset before moving into descriptive analysis, economic interpretation, and potential thesis-related research.

## Project goals

This project is designed to:

- practice working with REST APIs in Python;
- build a reproducible energy-data pipeline;
- organize electricity-price and generation data into analysis-ready formats;
- document data-cleaning and classification decisions;
- create a foundation for future energy-economics research.

The current geographic focus is Texas, but the code is being written so that it can later be extended to other U.S. states.

## Current progress

### Retail electricity data

- Connected to the EIA API.
- Retrieved monthly Texas retail electricity data from 2015 onward.
- Collected residential, commercial, and industrial-sector observations.
- Retrieved:
  - average retail electricity price;
  - electricity sales;
  - retail revenue;
  - number of customers.
- Added automatic pagination.
- Added data-type conversion and structural validation.
- Built long-format and wide-format retail-electricity datasets.
- Created month-coverage and missing-value reports.
- Created a sector-level electricity-price visualization.

### Electricity generation data

- Inspected EIA route metadata and facet values.
- Retrieved monthly Texas electricity generation by fuel type.
- Preserved the original EIA fuel codes and descriptions.
- Created a manually reviewed fuel-category mapping.
- Identified and removed overlapping aggregate and subcategory series.
- Standardized fuel groups including:
  - Coal;
  - Natural Gas;
  - Other Gases;
  - Petroleum;
  - Nuclear;
  - Hydroelectric;
  - Wind;
  - Solar;
  - Biomass;
  - Other.
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

- Converted the retail-electricity data from sector-level long format to monthly wide format.
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

## Data source

The current datasets are retrieved from the U.S. Energy Information Administration API.

Main data categories:

- retail electricity sales and prices;
- electricity generation by fuel type;
- API metadata and facet definitions.

API keys are stored locally in a `.env` file and are not committed to the repository.

## Repository structure

```text
texas-energy-economy-monitor/
├── config/
│   └── fuel_mapping.csv
├── data/
│   ├── metadata/
│   ├── processed/
│   └── raw/
├── notebooks/
│   ├── 01_eia_exploration.ipynb
│   └── 02_sector_comparison.ipynb
├── reports/
│   └── figures/
├── src/
│   ├── build_generation_dataset.py
│   ├── build_price_panel.py
│   ├── build_retail_dataset.py
│   ├── create_fuel_mapping.py
│   ├── fetch_eia.py
│   ├── fetch_generation.py
│   ├── finalize_fuel_mapping.py
│   ├── generation_transform.py
│   ├── inspect_generation_metadata.py
│   ├── validate_generation_totals.py
│   ├── build_integrated_energy_dataset.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

The exact file list may change as the project is refactored.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/cauchygugugu-web/texas-energy-economy-monitor.git
cd texas-energy-economy-monitor
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the EIA API key

Create a local `.env` file in the project root:

```text
EIA_API_KEY=your_eia_api_key_here
```

Do not commit the `.env` file.

## Running the project

### Build the retail-electricity dataset

```bash
python src/build_retail_dataset.py
```

### Build the retail-price panel

```bash
python src/build_price_panel.py
```

### Inspect generation metadata

```bash
python src/inspect_generation_metadata.py
```

### Retrieve generation data

```bash
python src/fetch_generation.py
```

### Build and validate the clean generation dataset

```bash
python src/build_generation_dataset.py
```

### Run the independent generation-total validation

```bash
python src/validate_generation_totals.py
```

### Build the integrated monthly energy dataset

First generate the retail and generation datasets:

```bash
python src/build_retail_dataset.py
python src/build_generation_dataset.py
```

Then merge them
```bash
python src/build_integrated_energy_dataset.py
```

### Build analysis-ready energy indicators

```bash
python src/build_energy_indicators.py
```

## Generated outputs

Generated CSV files are stored under:

```text
data/processed/
```

Important outputs include:

```text
eia_tx_retail_electricity.csv
eia_tx_retail_prices_long.csv
eia_tx_retail_prices_wide.csv
eia_tx_generation_by_fuel.csv
eia_tx_generation_clean_long.csv
eia_tx_generation_clean_wide.csv
eia_tx_generation_group_coverage.csv
eia_tx_generation_derived_petroleum.csv
eia_tx_generation_reconciliation.csv
eia_tx_integrated_energy_monthly.csv
eia_tx_integrated_merge_report.csv
```

Most generated data files are excluded from version control because they can be reproduced from the source code.

The integrated dataset contains one row per month and combines:

- residential, commercial, and industrial retail-electricity measures;
- monthly electricity generation by standardized fuel group.

The merge report records whether each month is available in the retail dataset, the generation dataset, or both.

## Data-validation principles

The project currently follows these rules:

- raw API responses are not manually overwritten;
- dates are converted to monthly datetime values;
- numeric API fields are explicitly converted from strings;
- duplicate month-state-sector or month-fuel observations are rejected;
- aggregate fuel categories are not added to their own subcategories;
- missing values are not automatically treated as zero;
- valid negative generation values are preserved;
- derived observations are stored separately for auditing;
- selected fuel components must reproduce the reported total within a defined numerical tolerance.
- retail and generation datasets are merged using one-to-one monthly validation;
- unmatched months are documented rather than silently discarded;
- missing observations are not automatically converted to zero;
- the integrated dataset retains only months available from both source datasets.

## Current limitations

- The project currently covers Texas only.
- The analysis is primarily descriptive.
- Electricity-generation categories require careful treatment because EIA provides both aggregate and detailed fuel series.
- Some observations may be revised by the data provider.
- No causal conclusions are drawn from the current datasets.
- Macroeconomic and labor-market data have not yet been merged into the project.

## Next milestone

The next stage is to create a formal variable dictionary and
produce the first descriptive summary tables and visualizations
from the analysis-ready monthly dataset.

## Research direction

The project may later serve as preliminary data infrastructure for research on topics such as:

- renewable-energy penetration and retail electricity prices;
- natural-gas dependence and electricity-market outcomes;
- energy-price shocks and regional economic activity;
- changes in the Texas electricity-generation mix.

At the current stage, the priority is data reliability and reproducibility rather than causal inference.

## License

A license has not yet been selected.
