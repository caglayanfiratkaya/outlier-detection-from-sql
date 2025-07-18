
# SQL Aykırı Değer Tespit ve Raporlama Aracı

## 📖 Genel Bakış
Bu araç, SQL Server veritabanına bağlanarak kullanıcı tanımlı parametrelere göre istatistiksel aykırı değer analizi yapabilen ve bu değerleri vurgulayan temiz, biçimlendirilmiş bir Excel raporu üreten güçlü ve esnek bir Python betiğidir.

Tüm ayarlar `config.json` dosyası üzerinden yönetilebilir. SQL sorgusu, analiz metrikleri, gruplayıcı sütunlar ve rapor görünümü gibi konfigürasyonları Python koduna dokunmadan düzenleyebilirsiniz.

## ✨ Özellikler

- **Dinamik SQL Sorgusu**: `config.json` dosyasına yazacağınız herhangi bir SQL sorgusu çalıştırılır.
- **İki Analiz Modu**:
  - **Doğrudan Analiz**: SQL sorgusunda zaten hesaplanmış metrikleri analiz eder.
  - **Normalize Edilmiş Analiz**: Ham veri sütunlarından birim başına değer hesaplar.
- **Gruplamaya Göre Tespit**: Malzeme grubu veya tedarikçi gibi alt gruplarda aykırı değer bulur.
- **Özelleştirilebilir Excel Raporları**: Dosya adı, sütun başlıkları, ondalık hassasiyet gibi çıktılar ayarlanabilir.
- **Gelişmiş Hata Yönetimi**: Hatalı sütun adları veya tekrarlı SQL sonuçları gibi durumlar kullanıcı dostu şekilde uyarılır.

## 🚀 Başlarken

### 1. Gereksinimler
- Python 3.8+
- SQL Server erişimi
- SQL Server için ODBC Driver 17

### 2. Kurulum

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

### 3. Yapılandırma

#### 3.1: Veritabanı Bağlantısı (.env)

```ini
AUTH_METHOD=WINDOWS
DB_SERVER="SUNUCU_IP_ADRESİNİZ"
DB_NAME="VERITABANI_ADINIZ"
DB_USER=""
DB_PASSWORD=""
OUTPUT_DIRECTORY=""
```

#### 3.2: Analiz ve Rapor Ayarları (config.json)

##### 🔹 Mod 1: Doğrudan Analiz

```json
{
  "sql_query": "SELECT MATERIAL, WAREHOUSE, SPRICE, GROSS FROM IASSALITEM WHERE ...",
  "analysis_settings": {
    "analysis_columns": ["SPRICE", "GROSS"],
    "group_by_columns": ["MATERIAL", "WAREHOUSE"],
    "z_score_threshold": 3.0,
    "naming_conventions": { "average_prefix": "AVG" },
    "analysis_column_precision": 6,
    "average_column_precision": 2
  },
  "report_settings": {
    "output_filename": "Price_Amount_Analysis.xlsx",
    "base_columns_in_report": ["MATERIAL", "WAREHOUSE"],
    "column_labels": {
      "MATERIAL": "Malzeme No",
      "WAREHOUSE": "Depo",
      "SPRICE": "Fiyat",
      "GROSS": "Tutar"
    }
  }
}
```

##### 🔹 Mod 2: Normalize Edilmiş Analiz

```json
{
  "sql_query": "SELECT MATERIAL, OPERATION, MTK, MTUNIT, BASEQUAN FROM IASROU WHERE ...",
  "analysis_settings": {
    "normalize_map": { "MTK": "MTUNIT" },
    "base_quantity_column": "BASEQUAN",
    "group_by_columns": ["MATERIAL", "OPERATION"],
    "z_score_threshold": 3.0,
    "naming_conventions": {
        "average_prefix": "AVG",
        "normalized_prefix": "NORM",
        "normalized_suffix": "_PER_UNIT"
    },
    "analysis_column_precision": 6,
    "average_column_precision": 2
  },
  "report_settings": {
    "output_filename": "Routing_Time_Analysis.xlsx",
    "base_columns_in_report": ["MATERIAL", "OPERATION", "BASEQUAN"],
    "column_labels": {
      "MATERIAL": "Malzeme No",
      "OPERATION": "Operasyon",
      "BASEQUAN": "Temel Miktar",
      "MTK": "Birim Başına Süre"
    }
  }
}
```

### 🗂 config.json Anahtar Açıklamaları

| Bölüm             | Anahtar                     | Açıklama |
|------------------|-----------------------------|----------|
| `sql_query`       | -                           | Çalıştırılacak tam SQL sorgusu |
| `analysis_settings` | `analysis_columns`        | (Doğrudan Mod) Analiz edilecek metrikler |
|                   | `normalize_map`            | (Normalize Modu) Değer sütununu birim sütunu ile eşleştirir |
|                   | `base_quantity_column`     | (Normalize Modu) Birim başına oran hesaplamak için gereken sütun |
|                   | `group_by_columns`         | Gruplama yapılacak sütunlar |
|                   | `z_score_threshold`        | Aykırı değer eşiği (standart sapma) |
|                   | `naming_conventions`       | Üretilen sütunlar için önek/son ek tanımlamaları |
|                   | `analysis_column_precision` | Değer sütunları için ondalık basamak |
|                   | `average_column_precision` | Ortalama sütunlar için ondalık basamak |
| `report_settings` | `output_filename`          | Oluşturulacak Excel dosyasının adı |
|                   | `highlight_color`          | (Opsiyonel) Aykırı değer hücre rengi (hex) |
|                   | `base_columns_in_report`   | Rapor içinde gösterilecek tanımlayıcı sütunlar |
|                   | `column_labels`            | SQL sütun adlarını kullanıcı dostu başlıklarla eşleştirir |

## ▶️ Kullanım

`.env` ve `config.json` hazır olduktan sonra:

```bash
python main.py
```

## 📄 Çıktı

Örneğin `Routing_Time_Analysis.xlsx` isimli bir Excel dosyası oluşur, aykırı değerler vurgulanır.

## 🔧 Sorun Giderme

- **Bağlantı Sorunları**: `.env` içeriğini kontrol edin, SQL Server’a ağ erişimi sağlanıyor mu?
- **Konfigürasyon Hataları**: config’teki sütun adları SQL çıktısında mevcut mu?
- **Tekrarlanan Sütunlar**: `SELECT *` yerine açık alan adlarını tercih edin.

## 🧪 İpucu

SQL sorgunuzu önce SSMS'te test edin, hata ayıklamayı kolaylaştırır.

## 📜 Lisans

MIT Lisansı
