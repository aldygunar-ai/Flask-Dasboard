# ⚡ Flask Dashboard - PLTD Logistics Center

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.2-purple.svg)](https://getbootstrap.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Dashboard monitoring untuk **PLTD (Pusat Logistik)** yang terintegrasi dengan Google Sheets. Dikonversi dari Streamlit ke Flask untuk performa dan fleksibilitas yang lebih baik.

## ✨ Fitur

- 📊 **Dashboard Interaktif** - Visualisasi data dengan Plotly
- 📦 **Stok Material PLTD** - Monitoring stok preventive & corrective
- 📈 **Analisis Pemakaian** - Tren inbound/outbound material
- 🎯 **Propose Order** - Perencanaan pengadaan berdasarkan stok vs kebutuhan
- 🚚 **Transaksi Project** - Tracking permintaan material project
- 🗺️ **Map Lokasi** - Visualisasi lokasi PLTD
- 🔔 **Alert Material Kritis** - Notifikasi stok ≤1.5 bulan

## 🛠️ Tech Stack

- **Backend**: Flask 2.3.3
- **Database**: Google Sheets (via gspread)
- **Visualisasi**: Plotly 5.17.0
- **Frontend**: Bootstrap 5, Chart.js
- **Data Processing**: Pandas, NumPy
- **Deployment**: Ready for Render, PythonAnywhere, Heroku

## 📁 Project Structure
flask_pltd_dashboard/
├── app.py # Main application & routing
├── requirements.txt # Python dependencies
├── .env # Environment variables
├── .gitignore
├── README.md
├── LICENSE
├── static/
│ ├── css/
│ │ └── style.css # Custom styling
│ └── js/
│ └── script.js # Interactive features
└── templates/
├── base.html # Base template
├── index.html # Home dashboard
├── stock.html # Stock monitoring
├── analisis.html # Analysis page
├── propose.html # Order proposal
└── transaksi.html # Transaction tracking


## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Google Service Account credentials (for Google Sheets API)
- Access to PLTD Google Sheets

### Installation

1. **Clone repository**
```bash
git clone https://github.com/yourusername/Flask-Dashboard.git
cd Flask-Dashboard