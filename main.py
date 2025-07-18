import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import warnings
import json
import os
from dotenv import load_dotenv

# Suppress pandas and runtime warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning, module='pandas')
warnings.filterwarnings("ignore", category=RuntimeWarning)

def load_config(file_path='config.json'):
    """
    Loads the JSON configuration file containing analysis and report settings.
    Returns the config dictionary or None if file is missing/invalid.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {file_path} file not found.")
        return None
    except json.JSONDecodeError:
        print(f"ERROR: {file_path} is not a valid JSON format.")
        return None

def get_db_engine():
    """
    Creates and returns a SQLAlchemy database engine using environment variables.
    Supports both Windows and SQL Server authentication.
    Returns None if connection fails or required variables are missing.
    """
    auth_method = os.getenv("AUTH_METHOD", "WINDOWS").strip().upper()
    db_server = os.getenv("DB_SERVER", "").strip()
    db_name = os.getenv("DB_NAME", "").strip()
    
    if not db_server or not db_name:
        print("ERROR: DB_SERVER and DB_NAME must be defined in the .env file.")
        return None

    connection_string = ""
    if auth_method == 'WINDOWS':
        print("Connecting with Windows Authentication...")
        connection_string = f"mssql+pyodbc://@{db_server}/{db_name}?trusted_connection=yes&driver=ODBC+Driver+17+for+SQL+Server"
    elif auth_method == 'SQL':
        print("Connecting with SQL Server Authentication...")
        db_user = os.getenv("DB_USER", "").strip()
        db_password = os.getenv("DB_PASSWORD", "").strip()
        if not db_user or not db_password:
            print("ERROR: DB_USER and DB_PASSWORD must be defined in the .env file for SQL Authentication.")
            return None
        connection_string = f"mssql+pyodbc://{db_user}:{db_password}@{db_server}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server"
    else:
        print(f"ERROR: Invalid authentication method: {auth_method}. Use 'WINDOWS' or 'SQL'.")
        return None
        
    try:
        engine = create_engine(connection_string)
        with engine.connect() as connection:
            print("✅ Database connection successful.")
        return engine
    except Exception as e:
        print(f"ERROR: Could not establish database connection: {e}")
        return None

def get_data(engine, sql_query):
    """
    Executes the SQL query using the provided engine and returns the result as a DataFrame.
    Returns None if query fails.
    """
    try:
        print("Fetching data...")
        df = pd.read_sql(sql_query, engine)
        print(f"✅ {len(df)} rows fetched.")
        return df
    except Exception as e:
        print(f"ERROR: An error occurred while fetching data: {e}")
        return None

def normalize_data(df, config):
    """
    Normalizes specified columns in the DataFrame according to the config.
    Calculates value per unit for each mapping in 'normalize_map'.
    Returns the updated DataFrame and a list of normalized column names.
    """
    print("Normalizing data (Calculating value per unit)...")
    settings = config.get('analysis_settings', {})
    normalize_map = settings.get('normalize_map', {})
    base_quantity_column = settings.get('base_quantity_column')
    naming = settings.get('naming_conventions', {})
    
    normalized_prefix = naming.get('normalized_prefix', 'NORM')
    normalized_suffix = naming.get('normalized_suffix', '_PER_UNIT')

    if not base_quantity_column or base_quantity_column not in df.columns:
        print(f"ERROR: '{base_quantity_column}' base quantity column not found.")
        return df, []
    
    df[base_quantity_column] = pd.to_numeric(df[base_quantity_column], errors='coerce').fillna(0)
    
    normalized_columns = []
    for value_col, unit_col in normalize_map.items():
        if value_col in df.columns and unit_col in df.columns:
            new_col_name = f"{normalized_prefix}_{value_col}{normalized_suffix}"
            value_series = pd.to_numeric(df[value_col], errors='coerce').fillna(0)
            unit_series = pd.to_numeric(df[unit_col], errors='coerce').fillna(0)

            df[new_col_name] = np.where(
                (unit_series == 0) | (df[base_quantity_column] == 0), 
                0, 
                (value_series * 1000) / (df[base_quantity_column] * unit_series)
            )
            df[new_col_name] = df[new_col_name].fillna(0)
            normalized_columns.append(new_col_name)

    print("✅ Data normalization completed.")
    return df, normalized_columns

def analyze_outliers(df, config, analysis_columns):
    """
    Detects outliers in the DataFrame using Z-score analysis.
    Handles missing columns and configuration errors gracefully.
    Returns a DataFrame containing only outlier rows.
    """
    print("Performing data cleaning and analysis...")
    
    report_settings = config.get('report_settings', {})
    base_columns = report_settings.get('base_columns_in_report', [])
    
    existing_base_columns = [col for col in base_columns if col in df.columns]
    missing_columns = [col for col in base_columns if col not in df.columns]
    
    if missing_columns:
        print("\n" + "="*80)
        print("💡 INFO: Some columns in `base_columns_in_report` were not found in the SQL query result.")
        print(f"   Missing Columns: {', '.join(missing_columns)}")
        print("   These columns will be ignored and analysis will continue.")
        print("="*80 + "\n")
    
    if existing_base_columns:
        for col in existing_base_columns:
            is_object_check = (df.dtypes[col] == 'object')
            is_object = is_object_check.any() if isinstance(is_object_check, pd.Series) else is_object_check
            
            if is_object:
                df[col] = df[col].replace(r'^\s*$', np.nan, regex=True)
        
        original_rows = len(df)
        df.dropna(subset=existing_base_columns, inplace=True)
        print(f"{original_rows - len(df)} rows containing missing data were removed after cleaning.")
        
        if df.empty:
            print("WARNING: No rows left for analysis after data cleaning.")
            return pd.DataFrame()

    settings = config.get('analysis_settings', {})
    group_by = settings.get('group_by_columns', [])
    
    missing_group_by_cols = [col for col in group_by if col not in df.columns]

    if missing_group_by_cols:
        print("\n" + "="*80)
        print("🚨 CONFIGURATION ERROR: Some columns in 'group_by_columns' were not found in the SQL query result!")
        print(f"   Missing Column(s): {', '.join(missing_group_by_cols)}")
        print("   All grouping columns must be present in the data for correct analysis.")
        print("   Please check your config file.")
        print("="*80 + "\n")
        return pd.DataFrame()
        
    # Check for missing analysis columns
    missing_analysis_cols = [col for col in analysis_columns if col not in df.columns]

    if missing_analysis_cols:
        print("\n" + "="*80)
        print("🚨 CONFIGURATION ERROR: Some columns in 'analysis_columns' were not found in the SQL query result!")
        print(f"   Missing Column(s): {', '.join(missing_analysis_cols)}")
        print("   These are key columns for outlier analysis and must be present in the data.")
        print("   Please check your config file.")
        print("="*80 + "\n")
        return pd.DataFrame()
    
    z_score_threshold = float(settings.get('z_score_threshold', 3.0))
    naming = settings.get('naming_conventions', {})
    final_labels = report_settings.get('column_labels', {})
    avg_prefix = naming.get('average_prefix', 'AVG')

    # Calculate Z-score and group averages for each analysis column
    for col in analysis_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        zscore_col_name = f"ZSCORE_{col}"
        avg_col_name = f"{avg_prefix}_{col}"

        if group_by:
            group_means = df.groupby(group_by)[col].transform('mean')
            group_stds = df.groupby(group_by)[col].transform('std')
            df[zscore_col_name] = np.where(group_stds > 0, (df[col] - group_means) / group_stds, 0)
            df[avg_col_name] = group_means
        else:
            mean = df[col].mean()
            std = df[col].std()
            df[zscore_col_name] = np.where(std > 0, (df[col] - mean) / std, 0)
            df[avg_col_name] = mean
        
        df[zscore_col_name] = df[zscore_col_name].fillna(0)

    outlier_columns_internal_key = 'OUTLIER_COLUMNS'
    
    # Identify outlier rows for each analysis column
    is_outlier_df = pd.DataFrame(index=df.index)
    for col in analysis_columns:
        is_outlier_df[col] = df[f'ZSCORE_{col}'].abs() > z_score_threshold

    def get_outlier_names(row):
        outlier_columns = row[row].index.tolist()
        if 'normalize_map' in settings:
            labels = [final_labels.get(col.replace(f"{naming.get('normalized_prefix', 'NORM')}_", "").replace(f"{naming.get('normalized_suffix', '_PER_UNIT')}", ""), col) for col in outlier_columns]
        else:
            labels = [final_labels.get(col, col) for col in outlier_columns]
        return ', '.join(labels)

    df[outlier_columns_internal_key] = is_outlier_df.apply(get_outlier_names, axis=1)

    outliers_df = df[df[outlier_columns_internal_key] != ''].copy()
    print(f"✅ Outlier analysis completed. {len(outliers_df)} outlier rows found.")
    return outliers_df

def create_report(df, config, analysis_columns):
    """
    Generates an Excel report of the outlier analysis.
    Applies formatting and highlights outlier cells.
    """
    if df.empty:
        print("✅ Report not created because no outliers were found.")
        return
        
    print("Creating report...")
    try:
        report_settings = config.get('report_settings', {})
        analysis_settings = config.get('analysis_settings', {})
        output_filename = report_settings.get('output_filename', 'Outlier_Report.xlsx')
        
        final_labels = report_settings.get('column_labels', {}).copy()
        outlier_columns_internal_key = 'OUTLIER_COLUMNS'
        
        if outlier_columns_internal_key not in final_labels:
            final_labels[outlier_columns_internal_key] = "Outlier Value"
        
        outlier_flag_column_name = final_labels[outlier_columns_internal_key]
        
        naming = analysis_settings.get('naming_conventions', {})
        avg_prefix = naming.get('average_prefix', 'AVG')
        
        analysis_precision = int(analysis_settings.get('analysis_column_precision', 6))
        average_precision = int(analysis_settings.get('average_column_precision', 2))
        
        # Add average column labels if missing
        for col in analysis_columns:
            avg_col_key = f"{avg_prefix}_{col}"
            if avg_col_key not in final_labels:
                base_label = ""
                if 'normalize_map' in analysis_settings:
                    base_key = col.replace(f"{naming.get('normalized_prefix', 'NORM')}_", "").replace(f"{naming.get('normalized_suffix', '_PER_UNIT')}", "")
                    base_label = final_labels.get(base_key, base_key)
                else:
                    base_label = final_labels.get(col, col)
                final_labels[avg_col_key] = f"Avg. {base_label}"
        
        temp_report_columns = report_settings.get('base_columns_in_report', []).copy()
        for col in analysis_columns:
            temp_report_columns.append(col)
            temp_report_columns.append(f"{avg_prefix}_{col}")
        temp_report_columns.append(outlier_columns_internal_key)

        temp_report_df = df[[col for col in temp_report_columns if col in df.columns]].rename(columns=final_labels)
        
        final_report_df = temp_report_df.drop(columns=outlier_flag_column_name, errors='ignore')

        writer = pd.ExcelWriter(output_filename, engine='xlsxwriter')
        final_report_df.to_excel(writer, sheet_name='Outliers', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['Outliers']
        
        analysis_format_str = f'#,##0.{"0" * analysis_precision}'
        average_format_str = f'#,##0.{"0" * average_precision}'
        
        header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'fg_color': '#D7E4BC', 'border': 1})
        
        # Default cell format with border
        default_format = workbook.add_format({'border': 1})
        analysis_float_format = workbook.add_format({'num_format': analysis_format_str, 'border': 1})
        average_float_format = workbook.add_format({'num_format': average_format_str, 'border': 1})
        yellow_analysis_format = workbook.add_format({'num_format': analysis_format_str, 'bg_color': report_settings.get('highlight_color', '#FFFFE0'), 'border': 1})
        yellow_format = workbook.add_format({'bg_color': report_settings.get('highlight_color', '#FFFFE0'), 'border': 1})

        header_list = list(final_report_df.columns)
        
        analysis_column_labels = [final_labels.get(col, col) for col in analysis_columns]
        average_column_labels = [final_labels.get(f"{avg_prefix}_{col}", f"{avg_prefix}_{col}") for col in analysis_columns]

        # Write headers and set column formats
        for col_idx, value in enumerate(header_list):
            worksheet.write(0, col_idx, value, header_format)
            if value in analysis_column_labels:
                worksheet.set_column(col_idx, col_idx, 18, analysis_float_format)
            elif value in average_column_labels:
                worksheet.set_column(col_idx, col_idx, 18, average_float_format)
            else:
                worksheet.set_column(col_idx, col_idx, 18, default_format)

        # Highlight outlier cells in yellow
        temp_report_df_reset = temp_report_df.reset_index(drop=True)
        for idx, row in temp_report_df_reset.iterrows():
            if outlier_flag_column_name in row:
                outlier_text = row[outlier_flag_column_name]
                if pd.notna(outlier_text) and outlier_text:
                    outlier_columns = outlier_text.split(', ')
                    for col_idx, col_name in enumerate(header_list):
                        if col_name in outlier_columns:
                            format_to_use = yellow_analysis_format if col_name in analysis_column_labels else yellow_format
                            worksheet.write(idx + 1, col_idx, row[col_name], format_to_use)
        
        writer.close()
        print(f"✅ Report successfully saved to '{output_filename}'.")

    except Exception as e:
        print(f"ERROR: Report could not be saved: {e}")

def main():
    """
    Main function for outlier analysis workflow.
    Loads config, checks for logic errors, fetches data, normalizes if needed,
    performs outlier analysis, and creates report.
    """
    print("----- Outlier Analysis Started -----")
    load_dotenv()
    config = load_config()
    if not config: return

    # Check for columns present in both analysis and base columns (logic error)
    analysis_settings = config.get('analysis_settings', {})
    report_settings = config.get('report_settings', {})
    
    analysis_cols_list = analysis_settings.get('analysis_columns', [])
    base_cols_list = report_settings.get('base_columns_in_report', [])
    
    intersection = set(analysis_cols_list) & set(base_cols_list)
    
    if intersection:
        print("\n" + "="*80)
        print("🚨 CONFIGURATION ERROR: A column cannot be in both 'analysis_columns' and 'base_columns_in_report'!")
        print(f"   Conflicting Column(s): {', '.join(intersection)}")
        print("   Please remove these column(s) from 'base_columns_in_report'.")
        print("   'base_columns_in_report' should only contain columns that identify the row and are not analyzed.")
        print("="*80 + "\n")
        return

    engine = get_db_engine()
    if not engine: return
    
    df = get_data(engine, config['sql_query'])
    if df is None or df.empty: return

    # Remove duplicate columns from SQL result
    if df.columns.duplicated().any():
        duplicate_cols = df.columns[df.columns.duplicated()].unique().tolist()
        print("\n" + "="*80)
        print("🚨 WARNING: DUPLICATE COLUMNS DETECTED IN YOUR SQL QUERY! 🚨")
        print(f"   Duplicate Columns: {', '.join(duplicate_cols)}")
        print("   Duplicates have been automatically removed to continue analysis.")
        print("="*80 + "\n")
        df = df.loc[:, ~df.columns.duplicated()]
    
    analysis_cols = []
    
    # Determine analysis mode: normalization or direct analysis
    if 'normalize_map' in analysis_settings and 'base_quantity_column' in analysis_settings:
        print("▶️  Normalization Required Analysis Mode Active.")
        df, analysis_cols = normalize_data(df, config)
    elif 'analysis_columns' in analysis_settings:
        print("▶️  Direct Analysis Mode Active.")
        analysis_cols = analysis_settings.get('analysis_columns', [])
    else:
        print("ERROR: Analysis method not specified in config.json ('normalize_map' or 'analysis_columns' required).")
        return

    if not analysis_cols:
        print("WARNING: No columns found or created for analysis.")
        return

    outliers_df = analyze_outliers(df, config, analysis_cols)
    if not outliers_df.empty:
        create_report(outliers_df, config, analysis_cols)
    
    print("----- Analysis Completed -----")


if __name__ == "__main__":
    main()