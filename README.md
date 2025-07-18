
# SQL Outlier Detection & Reporting Tool

## 📖 Overview
This is a powerful and flexible Python script designed to connect to a SQL Server database, perform statistical outlier detection based on user-defined parameters, and generate a clean, formatted Excel report highlighting these outliers.

The tool is fully configurable via a `config.json` file, allowing users to change the SQL query, analysis metrics, grouping criteria, and report appearance without touching a single line of Python code.

## ✨ Features

- **Dynamic SQL Query**: Run any SQL query by simply placing it in the `config.json` file.
- **Two Analysis Modes**:
  - **Direct Analysis**: Directly analyze a metric already calculated in your SQL query (e.g., unit price).
  - **Normalization Analysis**: Calculate a "per-unit" metric from raw data columns before finding outliers.
- **Configurable Grouping**: Analyze outliers within specific groups (e.g., per material group and vendor).
- **Customizable Excel Reports**: Control the output filename, report columns, column headers, and even the decimal precision.
- **Robust Error Handling**: User-friendly messages for invalid column names or duplicate SQL results prevent crashes.

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8+
- SQL Server access
- ODBC Driver 17 for SQL Server

### 2. Installation

```bash
git clone https://github.com/your/repo.git
cd sql-outlier-tool

python -m venv venv
# Windows
.\env\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configuration

#### 3.1: Database Connection (.env)

```ini
AUTH_METHOD=WINDOWS
DB_SERVER="ENTER_YOUR_SERVER_IP"
DB_NAME="ENTER_YOUR_DATABASE_NAME"
DB_USER=""
DB_PASSWORD=""
OUTPUT_DIRECTORY=""
```

#### 3.2: Analysis & Report Setup (config.json)

```json
{
  "sql_query": "SELECT PRODUCT_ID, LOCATION_CODE, UNIT_PRICE, TOTAL_AMOUNT, TAX_AMOUNT FROM SAMPLE_TABLE WHERE CLIENT_ID = '01' AND CREATED_DATE > '2025-01-01 00:00:00.000'",
  "analysis_settings": {
    "analysis_columns": [
      "UNIT_PRICE",
      "TOTAL_AMOUNT"
    ],
    "group_by_columns": [
      "PRODUCT_ID",
      "LOCATION_CODE"
    ],
    "z_score_threshold": 3.0,
    "naming_conventions": {
      "average_prefix": "AVG"
    },
    "analysis_column_precision": 2,
    "average_column_precision": 2
  },
  "report_settings": {
    "output_filename": "Price_Amount_Analysis.xlsx",
    "highlight_color": "#FFFFE0",
    "base_columns_in_report": [
      "PRODUCT_ID",
      "LOCATION_CODE"
    ],
    "column_labels": {
      "PRODUCT_ID": "Product ID",
      "LOCATION_CODE": "Location Code",
      "UNIT_PRICE": "Unit Price",
      "TOTAL_AMOUNT": "Total Amount",
      "TAX_AMOUNT": "Tax Amount"
    }
  }
}
```

### 🗂 Explanation of config.json Keys

| Section             | Key                         | Description                                      |
| ------------------- | --------------------------- | ------------------------------------------------ |
| `sql_query`         | –                           | SQL Server query that fetches data               |
| `analysis_settings` | `analysis_columns`          | Columns to check for outliers (e.g. UNIT\_PRICE) |
|                     | `group_by_columns`          | Groups to calculate outliers within              |
|                     | `z_score_threshold`         | Z-score threshold for detecting outliers         |
|                     | `naming_conventions`        | Prefix for average column names                  |
|                     | `analysis_column_precision` | Decimal places for metric values                 |
|                     | `average_column_precision`  | Decimal places for averages                      |
| `report_settings`   | `output_filename`           | Name of generated Excel report                   |
|                     | `highlight_color`           | Color to highlight outliers in Excel             |
|                     | `base_columns_in_report`    | Descriptive columns to include in the report     |
|                     | `column_labels`             | Friendly names for Excel columns                 |

## ▶️ Usage

Once `.env` and `config.json` are ready:

```bash
python main.py
```

## 📄 Output

An Excel report like `Routing_Time_Analysis.xlsx` will be created, with outliers highlighted.

## 🔧 Troubleshooting

- **Connection Issues**: Validate `.env` values and network access to SQL Server.
- **Config Errors**: Ensure column names exist in your SQL result.
- **Duplicate Columns**: Avoid `SELECT *`; name your fields clearly.

## 🧪 Tip

Run your SQL in SSMS first before using it in config.

## 📜 License

MIT License.
