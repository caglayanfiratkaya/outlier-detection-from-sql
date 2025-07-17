import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from scipy.stats import zscore
import warnings
import json
import os
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=RuntimeWarning)

def load_config(file_path='config.json'):
    """Yapılandırma dosyasını yükler."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"HATA: {file_path} dosyası bulunamadı. Lütfen config.example.json dosyasını kopyalayıp düzenleyin.")
        return None
    except json.JSONDecodeError:
        print(f"HATA: {file_path} dosyası geçerli bir JSON formatında değil.")
        return None

def get_db_engine():
    """.env dosyasından bilgileri alıp veritabanı motorunu oluşturur."""
    auth_method = os.getenv("AUTH_METHOD", "WINDOWS").upper()
    db_server = os.getenv("DB_SERVER")
    db_name = os.getenv("DB_NAME")
    
    if not db_server or not db_name:
        print("HATA: .env dosyasında DB_SERVER ve DB_NAME değişkenleri tanımlanmalıdır.")
        return None

    connection_string = ""
    if auth_method == 'WINDOWS':
        print("Windows Authentication ile bağlanılıyor...")
        connection_string = f"mssql+pyodbc://@{db_server}/{db_name}?trusted_connection=yes&driver=ODBC+Driver+17+for+SQL+Server"
    elif auth_method == 'SQL':
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        if not db_user or not db_password:
            print("HATA: SQL Authentication için .env dosyasında DB_USER ve DB_PASSWORD tanımlanmalıdır.")
            return None
        print("SQL Server Authentication ile bağlanılıyor...")
        connection_string = f"mssql+pyodbc://{db_user}:{db_password}@{db_server}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server"
    else:
        print(f"HATA: Geçersiz AUTH_METHOD: {auth_method}. 'WINDOWS' veya 'SQL' olmalıdır.")
        return None
    
    try:
        return create_engine(connection_string)
    except Exception as e:
        print(f"Veritabanı bağlantısı kurulamadı: {e}")
        return None

def fetch_data(engine, query):
    """Veriyi SQL sorgusu ile çeker."""
    print("Veritabanından veriler çekiliyor...")
    try:
        df = pd.read_sql(query, engine)
        print(f"Toplam {len(df)} kayıt çekildi.")
        return df
    except Exception as e:
        print(f"Veri çekme sırasında hata: {e}")
        return None

def analyze_data(df, config):
    """Veriyi analiz eder ve aykırı değerleri bulur."""
    print("Veri analizi başlıyor...")
    analysis_cfg = config['analysis_settings']
    base_col = analysis_cfg['base_quantity_column']

    if base_col not in df.columns or (df[base_col] == 0).all():
        print(f"UYARI: '{base_col}' kolonu bulunamadı veya tüm değerleri 0. Normalizasyon yapılamıyor.")
        return pd.DataFrame()

    df = df[df[base_col] != 0].copy()
    
    normalize_map = analysis_cfg['normalize_map']
    
    enk_columns = []
    for val_col, unit_col in normalize_map.items():
        if val_col in df.columns and unit_col in df.columns:
            new_col = f"ENK{val_col.replace('_','')}MIN" # Kolon adlarındaki _ işaretini kaldır
            df[new_col] = np.where(
                df[unit_col] == 'H', (df[val_col] / df[base_col]) * 60,
                np.where(df[unit_col] == 'MIN', df[val_col] / df[base_col], np.nan)
            )
            enk_columns.append(new_col)

    def safe_zscore(x):
        return zscore(x, nan_policy='omit') if x.dropna().nunique() >= 2 else pd.Series([np.nan] * len(x), index=x.index)

    zscore_cols = []
    for col in enk_columns:
        z_col = f"Z_{col}"
        df[z_col] = df.groupby(analysis_cfg['group_by_columns'])[col].transform(safe_zscore)
        df[f"ORT_{col}"] = df.groupby(analysis_cfg['group_by_columns'])[col].transform('mean')
        zscore_cols.append(z_col)
    
    df['SAPAN_SUTUNLAR_TEKNIK'] = df[zscore_cols].abs().gt(analysis_cfg['z_score_threshold']).apply(
        lambda row: ', '.join([col.replace("Z_", "") for col, is_outlier in row.items() if is_outlier]), axis=1
    )
    
    return df[df['SAPAN_SUTUNLAR_TEKNIK'] != ''].copy()

def create_report(outliers_df, config):
    """Analiz sonuçlarını formatlayıp Excel raporu oluşturur."""
    if outliers_df.empty:
        print("Aykırı değer bulunamadı. Rapor oluşturulmayacak.")
        return

    print("Rapor oluşturuluyor...")
    report_cfg = config['report_settings']
    column_labels = report_cfg['column_labels']
    
    outliers_df['SAPAN_SUTUNLAR'] = outliers_df['SAPAN_SUTUNLAR_TEKNIK'].apply(
        lambda x: ', '.join([column_labels.get(tech_name, tech_name) for tech_name in x.split(', ') if tech_name]) if x else ''
    )
    
    final_columns_technical = [col for col in report_cfg['column_order'] if col in outliers_df.columns]
    final_df = outliers_df[final_columns_technical + ['SAPAN_SUTUNLAR']]
    final_df = final_df.rename(columns=column_labels)

    def highlight_outliers(row):
        styles = [''] * len(row)
        sapan_key = column_labels.get("SAPAN_SUTUNLAR", "Sapan Değeri Olan Sütunlar")
        sapan_okunabilir_adlar = row.get(sapan_key, '').split(', ')
        for i, col_name in enumerate(row.index):
            if col_name in sapan_okunabilir_adlar:
                styles[i] = f"background-color: {report_cfg['highlight_color']}"
        return styles

    styler = final_df.style.apply(highlight_outliers, axis=1)
    styler = styler.format(formatter="{:.2f}", na_rep="", subset=pd.IndexSlice[:, final_df.select_dtypes(include=np.number).columns])

    output_dir = os.getenv("OUTPUT_DIRECTORY", "")
    filename = report_cfg['output_filename']
    full_path = os.path.join(output_dir, filename) if output_dir else filename

    try:
        styler.to_excel(full_path, index=False, engine='openpyxl')
        print(f"✅ Rapor başarıyla '{full_path}' adresine kaydedildi. Satır sayısı: {len(final_df)}")
    except Exception as e:
        print(f"HATA: Rapor kaydedilemedi. Klasör yolunu kontrol edin: {e}")


def main():
    """Ana iş akışını yöneten fonksiyon."""
    print("----- Aykırı Değer Analizi Başlatıldı -----")
    load_dotenv()
    
    config = load_config()
    if not config: return

    engine = get_db_engine()
    if not engine: return

    raw_df = fetch_data(engine, config['sql_query'])
    if raw_df is None or raw_df.empty:
        print("Veri çekilemedi veya veri boş. İşlem durduruluyor.")
        return
        
    outliers_df = analyze_data(raw_df, config)
    create_report(outliers_df, config)
    
    print("----- Analiz Tamamlandı -----")

if __name__ == "__main__":
    main()