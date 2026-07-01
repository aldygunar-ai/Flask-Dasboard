from flask import Flask, render_template, request, session, jsonify
from flask_session import Session
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import gspread
from gspread_dataframe import get_as_dataframe
import re
import re as re2
import requests
import io
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = 'ganti-dengan-secret-key-yang-aman'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# ============================================================
# ========== SEMUA FUNGSI DARI KODE STREAMLIT ================
# ============================================================

PLTD_SHEETS = {
    'Pemaron': '1HN-X9OhLTGo5Ieu2uzBa6VHh0UlFdGTiw56yOIX5VgI',
    'Mangoli': '1agNRbhpUJRqsA91eDlDq49BKpbW5x3v-2DiAGlbdq9s',
    'Tayan': '1_FUPGfUWbKFSfYJj4c6rlZDSYDXdL2LOCGG3g6w9vBo',
    'Timika': '1SyaYeykle3Fg0FTQzXPzLhkoN60PC9GzygZkrnDY-04',
    'Bobong': '1OGeGlQqwO2a4tbL_rS0x5b4guTIiIzVNXySUsbK4GMM',
    'Merawang': '1WrNipP179XrvKjNIGjeNSnCz94_6IJQBf4pM-vO5OO8',
    'Air Anyir': '10dCcXN574G_xGxsnaq7UmExsA7asbz_HTJPMo6oWN2o',
    'Padang Manggar': '1IH0prF5h5rOtV2TbRbRI4wuj5PbafbLbAesUIfrYihM',
    'Krueng Raya': '1u8nurDgXSRLCFB0p9YFv3x7i_8FDU0FZmsQK_yw4W4s',
    'Lueng Bata': '1syFmB3cwN0FfYRBmjgYTshlFiZAXdvVDdcdZ-Xr_p6g',
    'Ulee Kareng': '1BlhNGU1L6QJq3W2Qi7Vmp3aOdYNalACKJUwUUecDeoU',
    'Waena': '10NKbFUi0SVh1784OQnSU0ULhWzL6_AK7XLY-8EgKbG8',
    'Sambelia': '1-8uGvDwZnciEgAXBbogkYWdHQcEClcwuln-hbaR0UAc',
    'Timika 2': '17FR17wxkeVgd0_GElV59ugetL8nutqiYwQRyY6FqIVE',
    'Wamena': '14ieCIQwEXf4hZ-RsOeLIMyKi5qEJLtQBwTz35b9JXxs',
    'Sinabang': '1RwBiayIN0S_QeSvLzE-mAUeIYChyQua8VqIQd_EuU8Y',
    'Ampenan': '13AU9pNiNBXjdUObQTfqeq3O7jKuWGaKcqsFq9GAi5pI',
    'Jeranjang': '1zDbsPRHY7l1gtwvh3RoulQ8g0nhQpyyR5RMVN0n44ds',
}
MASTER_PLTD_ID = '1FsaZyKs3DgJlyZkx5qqpBotNK8Z6C8GOrNeJv3I8AJA'
MASTER_D365_ID = '1C7r0AUC3taKIMR1CVmIle5gm333F4r2VPo7lWeqeH8A'
MASTER_GABUNGAN_ID = '1aZZnnBjSybgzEgUECdLSCaPJ_rMKNHJmfGEwetOARbs'

PREVENTIVE_MAP = {
    'LF3325': 'Oil Filter', 'LF777': 'Oil Filter By pass',
    '2020PM V30-C': 'Element Water Separator', 'FS1006': 'Fuel Filter',
    'WF2076': 'Water Filter', '3629140': 'Cylinder head cover gasket',
    'AF872': 'Air Filter Element', 'AF25278': 'Air Filter Element',
    'AF25278 (Free)': 'Air Filter Element', 'AHO1135': 'Air Filter Element (Aksa)',
    '5413003': 'V-BELT Fan Radiator', '3015257': 'V-BELT (Aksa)',
    '5412990': 'V-BELT Alternator', '5PK889': 'V-BELT Alternator',
    '21-3107': 'V-BELT Alternator', '25471145': 'V-BELT Alternator',
    '23PK2032': 'V-BELT Fan Radiator', '21-3110': 'V-BELT Fan Radiator',
    '25477108': 'V-BELT Fan Radiator', 'RIMULA R4 X 15W-40': 'Oli Shell',
    'WCL': 'Coolant',
}

KNOWN_CODES = list(PREVENTIVE_MAP.keys()) + ['5PK889', '21-3107', '25471145', '23PK2032', '21-3110', '25477108']

MULTI_VARIANT_MAP = {
    '5PK889 / 21-3107 / 25471145': '5PK889',
    '23PK2032 / 21-3110 / 25477108': '23PK2032',
}

NORMALIZE_NAME = {
    'AF25278': 'Air Filter Element', 'AF872': 'Air Filter Element',
    'RIMULA R4 X 15W-40': 'Oli Shell', 'WCL': 'Coolant',
    'ACC-Y': 'ACCU 12V N150 YUASA',
}

URUTAN_MATERIAL = [
    'LF3325', 'LF777', '2020PM V30-C', 'FS1006', 'WF2076',
    '3629140', 'AF872', 'AF25278', 'AF25278 (Free)', 'AHO1135',
    '5413003', '3015257', '5412990',
    '5PK889 / 21-3107 / 25471145', '23PK2032 / 21-3110 / 25477108',
    'RIMULA R4 X 15W-40', 'WCL'
]

SEMUA_PLTD = [
    'PEMARON', 'MANGOLI', 'TAYAN', 'TIMIKA', 'BOBONG',
    'MERAWANG', 'AIR ANYIR', 'PADANG MANGGAR', 'KRUENG RAYA',
    'LUENG BATA', 'ULEE KARENG', 'WAENA', 'SAMBELIA', 'TIMIKA 2', 'WAMENA',
    'SINABANG', 'AMPENAN', 'JERANJANG'
]

def extract_kode_from_product_id(product_id, nama_material):
    pid = str(product_id).upper().strip()
    nama = str(nama_material).upper().strip()
    gabungan = pid + ' ' + nama

    PID_TO_CODE = {
        'DP.ELE.PAR.001----': '2020PM V30-C',
        'DP.FIL.FLE.001----': 'FS1006',
        'DP.CF.FLE.001----': 'WF2076',
        'DP.OIL.FLE.009----': 'LF777',
    }
    if pid in PID_TO_CODE:
        return PID_TO_CODE[pid]

    SKIP_LIST = [
        'FS.SO.VDO.001----', 'AKSESORIS PART', 'ES.SKU.POL', 'ASSET',
        'VARISTOR----', '10 MICRON', '5 MICRON', 'AMPERE METER',
        'AVR D350', 'BATRAI ACCU', 'CONTROL GOVERNOR', 'COS PHI METER',
        'DINAMO AMPERE', 'ELEMENT FILTER 20', 'ELEMENT FILTER WIREMESH',
        'FILTER SOLAR', 'HZ METER', 'INJECTOR', 'MODUL', 'MPU',
        'MV FUSE LINK', 'PUSH ROD', 'RACOR FILTER', 'RELAY MY2',
        'RELAY MY4', 'SEAL MAIN FILTER', 'SHOCK ABSORBER', 'SOCKET RELAY',
        'SOLENOID', 'STC (FUEL', 'UVR ABB', 'VALVE PUSH ROD',
        'VOLT METER', 'V BELT',
    ]
    for skip in SKIP_LIST:
        if skip in nama:
            return None

    if 'OIL FILTER' in nama and 'BY PASS' not in nama:
        return 'LF3325'
    if 'OIL FILTER BY PASS' in nama:
        return 'LF777'
    if 'WATER SEPARATOR' in nama or 'RACOR 2020PM' in nama:
        return '2020PM V30-C'
    if 'FUEL FILTER' in nama or 'ELEMENT FUEL FILTER' in nama:
        return 'FS1006'
    if 'WATER FILTER' in nama:
        return 'WF2076'
    if 'GASKET' in nama:
        return '3629140'
    if 'AIR FILTER' in nama and 'ELEMENT' in nama:
        return 'AF872'
    if 'AIR FILTER' in nama and 'AHO1135' in nama:
        return 'AHO1135'
    if 'V-BELT FAN' in nama or 'V BELT FAN' in nama:
        return '5413003'
    if 'V-BELT (AKSA)' in nama or 'V BELT AKSA' in nama:
        return '3015257'
    if 'V-BELT ALTERNATOR' in nama or 'V BELT ALTERNATOR' in nama:
        return '5412990'
    if 'OLI SHELL' in nama or 'RIMULA' in nama:
        return 'RIMULA R4 X 15W-40'
    if 'COOLANT' in nama or 'COLLANT' in nama:
        return 'WCL'

    for kode in KNOWN_CODES:
        pattern = r'(?:^|[-/\s])' + re2.escape(kode) + r'(?:$|[-/\s])'
        if re2.search(pattern, gabungan):
            return kode

    return product_id

def norm(kode, nama):
    k = str(kode).strip().upper()
    nama_lower = str(nama).strip().lower()
    if k in MULTI_VARIANT_MAP:
        primary = MULTI_VARIANT_MAP[k]
        if primary in PREVENTIVE_MAP:
            return PREVENTIVE_MAP[primary]
    if k in NORMALIZE_NAME:
        return NORMALIZE_NAME[k]
    for pk, pn in PREVENTIVE_MAP.items():
        if k == pk.upper():
            if pk.upper() == 'RIMULA R4 X 15W-40':
                if 'drum' in nama_lower or '209' in nama_lower:
                    return 'Oli Shell (Drum)'
                elif 'ibc' in nama_lower or '1000' in nama_lower:
                    return 'Oli Shell (IBC)'
            return pn
    if 'rimula' in k.lower() or 'rimula' in nama_lower:
        if 'drum' in nama_lower or '209' in nama_lower:
            return 'Oli Shell (Drum)'
        elif 'ibc' in nama_lower or '1000' in nama_lower:
            return 'Oli Shell (IBC)'
        return 'Oli Shell'
    if 'coolant' in nama_lower or 'collant' in nama_lower or 'wcl' in k.lower():
        return 'Coolant'
    if 'air filter element' in nama_lower:
        return 'Air Filter Element'
    if 'gasket cylinder head' in nama_lower:
        return 'Cylinder head cover gasket'
    if 'oil filter' in nama_lower and 'by pass' not in nama_lower:
        return 'Oil Filter'
    if 'oil filter by pass' in nama_lower:
        return 'Oil Filter By pass'
    if 'element water separator' in nama_lower or 'racor' in nama_lower:
        return 'Element Water Separator'
    if 'fuel filter' in nama_lower or 'element fuel filter' in nama_lower:
        return 'Fuel Filter'
    if 'water filter' in nama_lower:
        return 'Water Filter'
    if 'v-belt fan' in nama_lower or 'v belt fan' in nama_lower:
        return 'V-BELT Fan Radiator'
    if 'v-belt alternator' in nama_lower or 'v belt alternator' in nama_lower:
        return 'V-BELT Alternator'
    if 'v-belt (aksa)' in nama_lower or 'v belt aksa' in nama_lower:
        return 'V-BELT (Aksa)'
    if 'oli shell' in nama_lower:
        if 'ibc' in nama_lower:
            return 'Oli Shell (IBC)'
        elif 'drum' in nama_lower:
            return 'Oli Shell (Drum)'
        return 'Oli Shell'
    return nama

def get_primary_code(kode):
    k = str(kode).strip().upper()
    if k in MULTI_VARIANT_MAP:
        return MULTI_VARIANT_MAP[k]
    parts = re.split(r'\s*/\s*', k)
    return parts[0].strip() if parts else k

def is_prev(kode):
    k = str(kode).strip().upper()
    for part in re.split(r'\s*/\s*', k):
        if part.strip() in PREVENTIVE_MAP:
            return True
    return k in PREVENTIVE_MAP

def is_valid(kode, nama):
    if not nama or not nama.strip():
        return False
    if re.match(r'^\d+(\.\d+)?$', nama.strip()):
        return False
    return True

@app.cache_data(ttl=1800)
def get_client():
    import os
    import json
    # Ambil dari environment variable
    gcp_json = os.environ.get('GCP_SERVICE_ACCOUNT', '{}')
    if not gcp_json or gcp_json == '{}':
        # Fallback: baca dari file .env atau streamlit secrets
        try:
            import streamlit as st
            c = dict(st.secrets["gcp_service_account"])
            if c.get('private_key'):
                c['private_key'] = c['private_key'].replace('\\n', '\n')
            return gspread.service_account_from_dict(c)
        except:
            pass
    try:
        c = json.loads(gcp_json)
        if c.get('private_key'):
            c['private_key'] = c['private_key'].replace('\\n', '\n')
        return gspread.service_account_from_dict(c)
    except:
        return gspread.service_account()

@app.cache_data(ttl=1800)
def load_all():
    cl = get_client()
    res = {'stock': pd.DataFrame(), 'm1': None, 'm2': None, 'cik': pd.DataFrame(), 'pemakaian': pd.DataFrame(), 'debug_log': []}
    log = []

    rows = []
    for pltd, sid in PLTD_SHEETS.items():
        try:
            sh = cl.open_by_key(sid)
            data = sh.sheet1.get_all_values()
            log.append(f"OK {pltd}: {len(data)-1} baris")
            if len(data) < 2:
                continue

            header = [str(c).strip().lower() for c in data[0]] if data else []
            is_format_log = ('keluar' in ' '.join(header[:5]) and 'masuk' in ' '.join(header[:5]))

            is_format_padang = False
            header_row = 0
            if not is_format_log and len(data) >= 2:
                for i in range(min(3, len(data))):
                    row_check = data[i]
                    if len(row_check) > 3:
                        kolom_c = str(row_check[2]).strip().lower()
                        kolom_d = str(row_check[3]).strip().lower()
                        if kolom_c == 'no' and 'matrial' in kolom_d:
                            is_format_padang = True
                            header_row = i
                            break

            if is_format_log:
                log.append(f"  -> Format LOG terdeteksi")
                i_nama = 8
                i_kode = 10
                i_qty = 3
                material_stok = {}
                for r in data[1:]:
                    if len(r) <= max(i_nama, i_kode, i_qty):
                        continue
                    nama = r[i_nama].strip() if i_nama < len(r) else ''
                    product_id = r[i_kode].strip() if i_kode < len(r) else ''
                    qty_s = r[i_qty].strip() if i_qty < len(r) else '0'
                    if not nama:
                        continue
                    if '#REF' in qty_s.upper() or '#N/A' in qty_s.upper():
                        continue
                    try:
                        qty = float(qty_s.replace(',', '')) if qty_s else 0.0
                    except:
                        qty = 0.0
                    kode = extract_kode_from_product_id(product_id, nama)
                    if kode is None:
                        continue
                    key = (nama.strip().lower(), kode.strip().upper())
                    material_stok[key] = qty
                ok = 0
                for (nama_lower, kode), qty in material_stok.items():
                    rows.append((pltd.strip().upper(), kode, norm(kode, nama_lower).strip(), qty, get_primary_code(kode)))
                    ok += 1
                log.append(f"  -> {ok} material unik (format LOG)")

            elif is_format_padang:
                log.append(f"  -> Format PADANG MANGGAR terdeteksi (header di baris {header_row})")
                i_nama = 3
                i_qty = 9
                material_stok = {}
                for r in data[header_row + 1:]:
                    if len(r) <= max(i_nama, i_qty):
                        continue
                    nama = r[i_nama].strip() if i_nama < len(r) else ''
                    qty_s = r[i_qty].strip() if i_qty < len(r) else '0'
                    if not nama:
                        continue
                    if '#REF' in qty_s.upper() or '#N/A' in qty_s.upper():
                        continue
                    try:
                        qty = float(qty_s.replace(',', '')) if qty_s else 0.0
                    except:
                        qty = 0.0
                    kode = extract_kode_from_product_id(nama, nama)
                    if kode is None:
                        continue
                    key = (nama.strip().lower(), kode.strip().upper())
                    material_stok[key] = qty
                ok = 0
                for (nama_lower, kode), qty in material_stok.items():
                    rows.append((pltd.strip().upper(), kode, norm(kode, nama_lower).strip(), qty, get_primary_code(kode)))
                    ok += 1
                log.append(f"  -> {ok} material unik (format Padang)")

            else:
                ok = 0
                for r in data[1:]:
                    if len(r) < 9:
                        continue
                    nama = r[2].strip() if len(r) > 2 else ''
                    kode = r[3].strip() if len(r) > 3 else ''
                    qty_s = r[8].strip() if len(r) > 8 else '0'
                    if not is_valid(kode, nama):
                        continue
                    if '#REF' in qty_s.upper() or '#N/A' in qty_s.upper():
                        continue
                    try:
                        qty = float(qty_s.replace(',', '')) if qty_s else 0.0
                    except:
                        qty = 0.0
                    rows.append((pltd.strip().upper(), kode.upper().strip(), norm(kode, nama).strip(), qty, get_primary_code(kode)))
                    ok += 1
                log.append(f"  -> {ok} valid")

        except Exception as e:
            log.append(f"ERR {pltd}: {str(e)[:80]}")

    df = pd.DataFrame(rows, columns=['PLTD', 'Kode Material', 'Nama Material', 'Qty', 'Primary Code'])
    if not df.empty:
        df['Jenis'] = df['Kode Material'].apply(lambda k: 'Preventive' if is_prev(k) else 'Corrective')
        df = df.groupby(['PLTD', 'Kode Material', 'Nama Material', 'Primary Code', 'Jenis'], as_index=False)['Qty'].sum()
    res['stock'] = df

    # --- MASTER PLTD ---
    try:
        sh = cl.open_by_key(MASTER_PLTD_ID)
        log.append(f"OK Master PLTD: {len(sh.worksheets())} sheet")
        for ws in sh.worksheets():
            t = ws.title.strip().lower()
            if ('master' in t or 'mater' in t) and '1' in t:
                try:
                    d = get_as_dataframe(ws, evaluate_formulas=True)
                    d.columns = [str(c).strip() for c in d.columns]
                    if len(d.columns) >= 12:
                        d = d.rename(columns={d.columns[9]: 'pltd', d.columns[2]: 'kode_material', d.columns[10]: 'keb_pm', d.columns[11]: 'keb_aktual'})
                        d['pltd'] = d['pltd'].astype(str).str.strip().str.upper()
                        d['kode_material'] = d['kode_material'].astype(str).str.strip().str.upper()
                        d['primary_code'] = d['kode_material'].apply(get_primary_code)
                        d['keb_pm'] = pd.to_numeric(d['keb_pm'], errors='coerce').fillna(0)
                        d['keb_aktual'] = pd.to_numeric(d['keb_aktual'], errors='coerce').fillna(0)
                        res['m1'] = d
                        log.append(f"M1 OK: {len(d)} baris")
                except Exception as e:
                    log.append(f"ERR M1: {str(e)[:120]}")
            if ('master' in t or 'mater' in t) and '2' in t:
                try:
                    d = get_as_dataframe(ws, evaluate_formulas=True)
                    d.columns = [str(c).strip() for c in d.columns]
                    pltd_c = next((c for c in d.columns if 'pltd' in c.lower()), None)
                    dur_c = next((c for c in d.columns if 'durasi' in c.lower()), None)
                    if pltd_c: d = d.rename(columns={pltd_c: 'pltd'})
                    if dur_c: d = d.rename(columns={dur_c: 'durasi_kirim'})
                    if 'pltd' in d.columns: d['pltd'] = d['pltd'].astype(str).str.strip().str.upper()
                    d['durasi_kirim'] = pd.to_numeric(d.get('durasi_kirim', 14), errors='coerce').fillna(14)
                    res['m2'] = d
                    log.append(f"M2 OK: {len(d)} baris")
                except Exception as e:
                    log.append(f"ERR M2: {str(e)[:80]}")
    except Exception as e:
        log.append(f"ERR Master PLTD: {str(e)[:80]}")

    # --- CIKANDE ---
    try:
        sh = cl.open_by_key(MASTER_D365_ID)
        ws = sh.worksheet('Sheet1')
        data = ws.get_all_values()
        hrow = 0
        for i, row in enumerate(data[:5]):
            if 'cikande' in ' '.join([str(c).lower() for c in row]):
                hrow = i; break
        header = [str(c).strip().lower() for c in data[hrow]]
        i_nama = next((i for i, h in enumerate(header) if 'nama' in h or 'material' in h), 0)
        i_kode = next((i for i, h in enumerate(header) if 'kode' in h or 'seri' in h), 1)
        i_qty = next((i for i, h in enumerate(header) if 'cikande' in h), 2)
        crows = []
        for r in data[hrow + 1:]:
            if len(r) <= max(i_nama, i_kode, i_qty): continue
            nama = r[i_nama].strip() if i_nama < len(r) else ''
            kode = r[i_kode].strip() if i_kode < len(r) else ''
            qty_s = r[i_qty].strip() if i_qty < len(r) else '0'
            try: qty = float(qty_s.replace(',', '')) if qty_s else 0.0
            except: qty = 0.0
            if nama or kode:
                crows.append({'Kode Material': kode.upper().strip(), 'Nama Material': norm(kode, nama).strip(), 'Primary Code': get_primary_code(kode), 'WH Cikande': qty})
        dc = pd.DataFrame(crows)
        if not dc.empty:
            dc = dc.groupby(['Kode Material', 'Nama Material', 'Primary Code'], as_index=False)['WH Cikande'].sum()
        res['cik'] = dc
        log.append(f"OK Cikande: {len(dc)} baris")
    except Exception as e:
        log.append(f"ERR Cikande: {str(e)[:80]}")

    # --- PEMAKAIAN ---
    try:
        sh = cl.open_by_key(MASTER_GABUNGAN_ID)
        ws = sh.worksheet('Gabungan')
        data = ws.get_all_values()
        if len(data) >= 2:
            header_row = None
            for i, row in enumerate(data[:10]):
                if 'tanggal' in ' '.join([str(c).lower() for c in row]) and 'nama' in ' '.join([str(c).lower() for c in row]):
                    header_row = i; break
            if header_row is None: header_row = 2
            p_rows = []
            for r in data[header_row + 1:]:
                if len(r) < 2 or not any(str(c).strip() for c in r[:5]): continue
                tanggal = r[0].strip() if len(r) > 0 else ''
                masuk = r[1].strip() if len(r) > 1 else '0'
                keluar = r[2].strip() if len(r) > 2 else '0'
                stok_s = r[3].strip() if len(r) > 3 else '0'
                keterangan = r[4].strip() if len(r) > 4 else ''
                transaksi = r[7].strip() if len(r) > 7 else ''
                nama_material = r[8].strip() if len(r) > 8 else ''
                jobtype = r[9].strip() if len(r) > 9 else ''
                gudang = r[11].strip() if len(r) > 11 else ''
                harga_raw = r[14].strip() if len(r) > 14 else '0'
                if nama_material:
                    try:
                        m = float(masuk.replace(',', '')) if masuk else 0.0
                        k = float(keluar.replace(',', '')) if keluar else 0.0
                        s = float(stok_s.replace(',', '')) if stok_s else 0.0
                    except: m = k = s = 0.0
                    try:
                        if '.' in harga_raw and ',' not in harga_raw: h = float(harga_raw.replace('.', ''))
                        elif ',' in harga_raw: h = float(harga_raw.replace(',', '.'))
                        else: h = float(harga_raw)
                    except: h = 0.0
                    p_rows.append({'Tanggal': tanggal, 'Nama Material': nama_material, 'Masuk': m, 'Keluar': k, 'Stok': s, 'Gudang': gudang, 'Keterangan': keterangan, 'Transaksi': transaksi, 'JobType': jobtype, 'HARGA_D365': h, 'TOTAL_COST': k * h})
            df_p = pd.DataFrame(p_rows)
            if not df_p.empty: df_p['Tanggal'] = pd.to_datetime(df_p['Tanggal'], errors='coerce')
            res['pemakaian'] = df_p
            log.append(f"OK Gabungan: {len(df_p)} baris")
    except Exception as e:
        log.append(f"ERR Gabungan: {str(e)[:80]}")

    res['debug_log'] = log
    return res

def hitung_sisa_bulan(df_stock, m1):
    if df_stock.empty or m1 is None: return pd.DataFrame()
    if 'primary_code' not in m1.columns: m1['primary_code'] = m1['kode_material'].apply(get_primary_code)
    m1_use = m1[['pltd', 'primary_code', 'keb_aktual']].copy()
    m1_use.columns = ['PLTD_M1', 'Primary_Code_M1', 'Keb_Aktual']
    m1_use['PLTD_M1'] = m1_use['PLTD_M1'].astype(str).str.strip().str.upper()
    m1_use['Primary_Code_M1'] = m1_use['Primary_Code_M1'].astype(str).str.strip().str.upper()
    m1_use['Keb_Aktual'] = pd.to_numeric(m1_use['Keb_Aktual'], errors='coerce').fillna(0)
    m1_use = m1_use[(m1_use['PLTD_M1'] != '') & (m1_use['Primary_Code_M1'] != '')]
    m1_use = m1_use.drop_duplicates(subset=['PLTD_M1', 'Primary_Code_M1'], keep='last')
    stok = df_stock.copy()
    stok['PLTD'] = stok['PLTD'].astype(str).str.strip().str.upper()
    stok['Primary Code'] = stok['Primary Code'].astype(str).str.strip().str.upper()
    stok = stok.reset_index(drop=True)
    merged = stok.merge(m1_use, left_on=['PLTD', 'Primary Code'], right_on=['PLTD_M1', 'Primary_Code_M1'], how='left')
    mask_null = merged['Keb_Aktual'].isna() | (merged['Keb_Aktual'] == 0)
    if mask_null.any():
        m1_kode = m1[['pltd', 'kode_material', 'keb_aktual']].copy()
        m1_kode.columns = ['PLTD_M1', 'Kode_M1', 'Keb_Aktual_kode']
        m1_kode['PLTD_M1'] = m1_kode['PLTD_M1'].astype(str).str.strip().str.upper()
        m1_kode['Kode_M1'] = m1_kode['Kode_M1'].astype(str).str.strip().str.upper()
        m1_kode['Keb_Aktual_kode'] = pd.to_numeric(m1_kode['Keb_Aktual_kode'], errors='coerce').fillna(0)
        m1_kode = m1_kode.drop_duplicates(subset=['PLTD_M1', 'Kode_M1'], keep='last')
        null_rows = merged[mask_null].drop(columns=['PLTD_M1', 'Primary_Code_M1', 'Keb_Aktual'], errors='ignore')
        null_fixed = null_rows.merge(m1_kode, left_on=['PLTD', 'Kode Material'], right_on=['PLTD_M1', 'Kode_M1'], how='left')
        null_indices = merged.index[mask_null]
        for i, idx in enumerate(null_indices):
            if i < len(null_fixed):
                new_val = null_fixed.iloc[i].get('Keb_Aktual_kode', 0)
                if pd.notna(new_val) and new_val > 0: merged.loc[idx, 'Keb_Aktual'] = new_val
    merged['Keb_Aktual'] = pd.to_numeric(merged['Keb_Aktual'], errors='coerce').fillna(0)
    merged = merged.drop(columns=['PLTD_M1', 'Primary_Code_M1'], errors='ignore')
    merged['Sisa_Bulan'] = np.where(merged['Keb_Aktual'] > 0, (merged['Qty'] / merged['Keb_Aktual']).round(1), 0.0)
    return merged

# ============================================================
# ========== ROUTING FLASK ====================================
# ============================================================

@app.route('/')
def home():
    data = load_all()
    df = data.get('stock', pd.DataFrame())
    if df.empty:
        return render_template('dashboard.html', page='home', error="Data belum tersedia.")
    
    metrics = {
        'pltd_aktif': df['PLTD'].nunique(),
        'total_stok': f"{df['Qty'].sum():,.0f}",
        'preventive': (df['Jenis']=='Preventive').sum(),
        'corrective': (df['Jenis']=='Corrective').sum()
    }
    
    # Koordinat PLTD
    coords = {
        'PEMARON': (-8.16, 114.68), 'MANGOLI': (-1.88, 125.37), 'TAYAN': (-0.03, 110.10),
        'TIMIKA': (-4.56, 136.89), 'BOBONG': (-1.95, 124.39), 'MERAWANG': (-1.95, 105.96),
        'AIR ANYIR': (-1.94, 106.11), 'PADANG MANGGAR': (-2.14, 106.14), 'KRUENG RAYA': (5.60, 95.53),
        'LUENG BATA': (5.55, 95.33), 'ULEE KARENG': (5.55, 95.33), 'WAENA': (-2.61, 140.56),
        'SAMBELIA': (-8.40, 116.67), 'TIMIKA 2': (-4.56, 136.89), 'WAMENA': (-4.09, 138.94),
        'SINABANG': (2.48, 96.38), 'AMPENAN': (-8.57, 116.07), 'JERANJANG': (-8.67, 116.15),
    }
    loc = df[['PLTD']].drop_duplicates()
    loc['lat'] = loc['PLTD'].map(lambda x: coords.get(x, (None, None))[0])
    loc['lon'] = loc['PLTD'].map(lambda x: coords.get(x, (None, None))[1])
    loc = loc.dropna(subset=['lat'])
    
    if not loc.empty:
        fig_map = px.scatter_mapbox(loc, lat='lat', lon='lon', hover_name='PLTD',
                                    zoom=3, height=350, mapbox_style='open-street-map')
        map_html = fig_map.to_html(full_html=False)
    else:
        map_html = '<p class="text-muted">Tidak ada data lokasi</p>'
    
    # Pie chart
    jenis_counts = df['Jenis'].value_counts().reset_index()
    jenis_counts.columns = ['Jenis', 'Jumlah Item']
    fig_pie = px.pie(jenis_counts, values='Jumlah Item', names='Jenis',
                     color_discrete_sequence=['#2C6E9E', '#E67E22'], hole=0.4)
    fig_pie.update_layout(margin=dict(t=0, b=0), height=300)
    pie_html = fig_pie.to_html(full_html=False)
    
    # Bar chart
    top_pltd = df.groupby('PLTD')['Qty'].sum().nlargest(5).reset_index()
    fig_bar = px.bar(top_pltd, x='PLTD', y='Qty', text='Qty',
                     color='Qty', color_continuous_scale='Blues')
    fig_bar.update_traces(texttemplate='%{text:.0f}', textposition='outside')
    fig_bar.update_layout(xaxis_title="", yaxis_title="Total Unit", height=300)
    bar_html = fig_bar.to_html(full_html=False)
    
    # Kritis
    m1 = data.get('m1')
    kritis_html = None
    if m1 is not None and not df[df['Jenis']=='Preventive'].empty:
        sisa_df = hitung_sisa_bulan(df[df['Jenis']=='Preventive'], m1)
        if not sisa_df.empty:
            kritis = sisa_df[(sisa_df['Sisa_Bulan'] <= 1.5) & (sisa_df['Sisa_Bulan'] > 0)]
            if not kritis.empty:
                top_kritis = kritis.groupby(['Nama Material', 'PLTD'])['Sisa_Bulan'].min().reset_index()
                top_kritis = top_kritis.sort_values('Sisa_Bulan').head(10)
                kritis_html = top_kritis.to_html(classes='table table-striped table-hover', index=False)
    
    return render_template('dashboard.html', page='home', metrics=metrics,
                           map_html=map_html, pie_html=pie_html,
                           bar_html=bar_html, kritis_html=kritis_html)

@app.route('/stock')
def stock():
    data = load_all()
    df = data['stock'].copy()
    if df.empty:
        return render_template('dashboard.html', page='stock', error="Data stok kosong")
    
    sel_pltd = request.args.getlist('pltd')
    sel_jenis = request.args.getlist('jenis')
    sel_nama = request.args.getlist('nama')
    sel_kode = request.args.getlist('kode')
    highlight = request.args.get('highlight', 'false') == 'true'
    
    f = df.copy()
    if sel_pltd:
        f = f[f['PLTD'].isin(sel_pltd)]
    if sel_jenis:
        f = f[f['Jenis'].isin(sel_jenis)]
    if sel_nama:
        f = f[f['Nama Material'].isin(sel_nama)]
    if sel_kode:
        f = f[f['Kode Material'].isin(sel_kode)]
    
    prev = f[f['Jenis']=='Preventive']
    corr = f[f['Jenis']=='Corrective']
    m1 = data.get('m1')
    cik = data.get('cik')
    
    # Gabung WH Cikande
    if not cik.empty and not prev.empty:
        prev = prev.merge(cik, on=['Kode Material','Nama Material','Primary Code'], how='left')
        prev['WH Cikande'] = prev['WH Cikande'].fillna(0)
    else:
        if not prev.empty:
            prev['WH Cikande'] = 0.0
    
    # Preventive pivot
    prev_pivot = None
    if not prev.empty:
        p = prev.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                             values='Qty', aggfunc='sum', fill_value=0).round(0).astype(int)
        cik_p = prev.groupby(['Kode Material','Nama Material'])['WH Cikande'].max().round(0).astype(int)
        p = p.join(cik_p)
        p['Total'] = p.drop(columns='WH Cikande').sum(axis=1)
        p = p.reset_index()
        pltd_cols = [c for c in p.columns if c not in ('Kode Material','Nama Material','WH Cikande','Total')]
        p = p[['Kode Material','Nama Material'] + pltd_cols + ['WH Cikande','Total']]
        prev_pivot = p.to_html(classes='table table-striped table-hover table-bordered', index=False)
    
    # Sisa bulan
    sisa_pivot = None
    if not prev.empty and m1 is not None:
        sisa_df = hitung_sisa_bulan(prev, m1)
        if not sisa_df.empty:
            sp = sisa_df.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                                     values='Sisa_Bulan', aggfunc='first', fill_value=0.0).reset_index()
            for pltd in SEMUA_PLTD:
                if pltd not in sp.columns:
                    sp[pltd] = 0.0
            pltd_cols_s = [p for p in SEMUA_PLTD if p in sp.columns]
            sp = sp[['Kode Material','Nama Material'] + pltd_cols_s]
            def urutkan(kode):
                try:
                    return URUTAN_MATERIAL.index(kode)
                except ValueError:
                    return 999
            sp['_sort'] = sp['Kode Material'].apply(urutkan)
            sp = sp.sort_values('_sort').drop(columns=['_sort'])
            if highlight:
                mask = (sp[pltd_cols_s] > 0) & (sp[pltd_cols_s] <= 1.5)
                sp = sp[mask.any(axis=1)]
            styled = sp.style.map(lambda val: 'background-color: #ffcccc; color: #cc0000; font-weight: bold;' if isinstance(val, (int, float)) and val <= 1.5 else '', subset=pltd_cols_s)
            sisa_pivot = styled.to_html(classes='table table-bordered', index=False)
    
    # Corrective pivot
    corr_pivot = None
    if not corr.empty:
        p = corr.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                             values='Qty', aggfunc='sum', fill_value=0).round(0).astype(int)
        if not cik.empty:
            cik_c = corr.groupby(['Kode Material','Nama Material'])['WH Cikande'].max().round(0).astype(int)
            p = p.join(cik_c)
        else:
            p['WH Cikande'] = 0
        p['Total'] = p.drop(columns=['WH Cikande'], errors='ignore').sum(axis=1)
        p = p.reset_index()
        pltd_cols = [c for c in p.columns if c not in ('Kode Material','Nama Material','WH Cikande','Total')]
        p = p[['Kode Material','Nama Material'] + pltd_cols + ['WH Cikande','Total']]
        corr_pivot = p.to_html(classes='table table-striped table-hover table-bordered', index=False)
    
    pltd_list = sorted(df['PLTD'].unique())
    jenis_list = ['Preventive', 'Corrective']
    nama_list = sorted(df['Nama Material'].unique())
    kode_list = sorted(df['Kode Material'].unique())
    
    return render_template('dashboard.html', page='stock',
                           pltd_list=pltd_list, jenis_list=jenis_list,
                           nama_list=nama_list, kode_list=kode_list,
                           prev_pivot=prev_pivot, sisa_pivot=sisa_pivot,
                           corr_pivot=corr_pivot,
                           selected_pltd=sel_pltd, selected_jenis=sel_jenis,
                           selected_nama=sel_nama, selected_kode=sel_kode,
                           highlight=highlight)

@app.route('/analisis')
def analisis():
    data = load_all()
    df_pakai = data.get('pemakaian', pd.DataFrame()).copy()
    if df_pakai.empty:
        return render_template('dashboard.html', page='analisis', error="Data pemakaian kosong")
    
    nama_map = {
        'water coollant reco-cool - drum': 'WATER COOLLANT RECO-COOL',
        'filter udara af872': 'FILTER UDARA AF872', 'air filter element af872': 'FILTER UDARA AF872',
        'element racor 2020pm parker': 'ELEMENT RACOR 2020PM', 'oil filter lf777 fleet gruad': 'OIL FILTER LF777',
        'coolant filter wf2076 fleetguard': 'COOLANT FILTER WF2076',
        'oil shell rimula r3mv 15w-40 (drum @ 209 ltr)': 'OIL SHELL RIMULA R3MV',
        'oli rimula r4 x 15w-40 (ibc @ 1000 liter)': 'OLI RIMULA R4 (IBC)',
        'filter separator fs 1006 fleetguard': 'FILTER SEPARATOR FS1006',
        'oil filter lf3325 fleetguard': 'OIL FILTER LF3325',
    }
    df_pakai['Nama Material'] = df_pakai['Nama Material'].str.strip().str.lower().apply(lambda x: nama_map.get(x, x.upper()))
    for c in ['Masuk','Keluar','Stok','TOTAL_COST']:
        if c in df_pakai.columns:
            df_pakai[c] = pd.to_numeric(df_pakai[c], errors='coerce').fillna(0)
    if 'Tanggal' in df_pakai.columns:
        df_pakai['Tanggal'] = pd.to_datetime(df_pakai['Tanggal'], errors='coerce')
        df_pakai['Tahun'] = df_pakai['Tanggal'].dt.year.astype('Int64').astype(str).replace('<NA>','')
        bln = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'Mei',6:'Jun',7:'Jul',8:'Ags',9:'Sep',10:'Okt',11:'Nov',12:'Des'}
        df_pakai['Periode'] = df_pakai['Tanggal'].dt.month.map(bln).fillna('')
        df_pakai['BulanStr'] = df_pakai['Tanggal'].dt.strftime('%Y-%m').replace('NaT','')
    
    sel_nama = request.args.getlist('nama')
    sel_gudang = request.args.getlist('gudang')
    sel_tahun = request.args.getlist('tahun')
    sel_periode = request.args.getlist('periode')
    
    f = df_pakai.copy()
    if sel_nama:
        f = f[f['Nama Material'].astype(str).isin(sel_nama)]
    if sel_gudang and 'Gudang' in f.columns:
        f = f[f['Gudang'].astype(str).isin(sel_gudang)]
    if sel_tahun:
        f = f[f['Tahun'].astype(str).isin(sel_tahun)]
    if sel_periode:
        f = f[f['Periode'].astype(str).isin(sel_periode)]
    
    pc = f.pivot_table(index='Nama Material', values=['Keluar','TOTAL_COST'],
                       aggfunc={'Keluar':'sum','TOTAL_COST':'sum'})
    pc = pc[pc['TOTAL_COST'] > 0]
    total_cost = pc['TOTAL_COST'].sum()
    
    kpi = {
        'total_trans': len(f),
        'total_keluar': f['Keluar'].sum() if 'Keluar' in f.columns else 0,
        'unik_material': len(pc),
        'grand_total': f"Rp {total_cost:,.0f}"
    }
    
    trend_html = None
    if 'BulanStr' in f.columns:
        trend = f[f['BulanStr']!=''].groupby('BulanStr').agg(
            Masuk=('Masuk','sum'), Keluar=('Keluar','sum')).reset_index().sort_values('BulanStr')
        if not trend.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trend['BulanStr'], y=trend['Masuk'],
                                     mode='lines+markers+text', name='Inbound',
                                     line=dict(color='#4B8BBE', width=2),
                                     text=trend['Masuk'].apply(lambda x: f'{x:,.0f}'),
                                     textposition='top center'))
            fig.add_trace(go.Scatter(x=trend['BulanStr'], y=trend['Keluar'],
                                     mode='lines+markers+text', name='Outbound',
                                     line=dict(color='#E67E22', width=2),
                                     text=trend['Keluar'].apply(lambda x: f'{x:,.0f}'),
                                     textposition='top center'))
            fig.update_layout(height=400, xaxis_title='Periode', yaxis_title='Qty',
                              legend=dict(orientation='h', yanchor='bottom', y=-0.25,
                                          xanchor='center', x=0.5),
                              xaxis=dict(tickangle=-45))
            trend_html = fig.to_html(full_html=False)
    
    cost_html = None
    if not pc.empty:
        tc = pc.nlargest(10, 'TOTAL_COST').sort_values('TOTAL_COST', ascending=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(y=tc.index, x=tc['TOTAL_COST'], orientation='h',
                              marker=dict(color='#27AE60'),
                              text=tc['TOTAL_COST'].apply(lambda x: f'Rp {x:,.0f}'),
                              textposition='outside'))
        fig2.update_layout(height=400, margin=dict(l=250, r=100, t=30, b=20))
        cost_html = fig2.to_html(full_html=False)
    
    inout_html = None
    if not f.empty:
        t10 = f.groupby('Nama Material').agg(Masuk=('Masuk','sum'), Keluar=('Keluar','sum')).sum(axis=1).nlargest(10).index.tolist()
        agg = f[f['Nama Material'].isin(t10)].groupby('Nama Material').agg(
            Masuk=('Masuk','sum'), Keluar=('Keluar','sum')).reset_index().sort_values('Masuk', ascending=True)
        if not agg.empty:
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(y=agg['Nama Material'], x=agg['Masuk'], name='Inbound',
                                  orientation='h', marker=dict(color='#4B8BBE'),
                                  text=agg['Masuk'].apply(lambda x: f'{x:,.0f}'),
                                  textposition='outside'))
            fig3.add_trace(go.Bar(y=agg['Nama Material'], x=agg['Keluar'], name='Outbound',
                                  orientation='h', marker=dict(color='#E67E22'),
                                  text=agg['Keluar'].apply(lambda x: f'{x:,.0f}'),
                                  textposition='outside'))
            fig3.update_layout(barmode='group', height=400, margin=dict(l=200, r=80, t=30, b=60),
                               legend=dict(orientation='h', yanchor='bottom', y=-0.25,
                                           xanchor='center', x=0.5))
            inout_html = fig3.to_html(full_html=False)
    
    detail_html = None
    if not f.empty:
        cols = ['Tanggal','Nama Material','Masuk','Keluar','Stok','Gudang','Keterangan','Transaksi','JobType','TOTAL_COST']
        cols = [c for c in cols if c in f.columns]
        if 'Tanggal' in f.columns:
            f = f.sort_values('Tanggal', ascending=False)
        detail_html = f[cols].head(50).to_html(classes='table table-striped table-hover', index=False)
    
    nama_list = sorted(df_pakai['Nama Material'].unique().astype(str))
    gudang_list = sorted(df_pakai['Gudang'].unique().astype(str)) if 'Gudang' in df_pakai.columns else []
    tahun_list = sorted([str(t) for t in df_pakai['Tahun'].unique() if pd.notna(t) and str(t) not in ['','<NA>','None','nan']]) if 'Tahun' in df_pakai.columns else []
    periode_list = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Ags','Sep','Okt','Nov','Des']
    
    return render_template('dashboard.html', page='analisis',
                           kpi=kpi, trend_html=trend_html,
                           cost_html=cost_html, inout_html=inout_html,
                           detail_html=detail_html,
                           nama_list=nama_list, gudang_list=gudang_list,
                           tahun_list=tahun_list, periode_list=periode_list,
                           selected_nama=sel_nama, selected_gudang=sel_gudang,
                           selected_tahun=sel_tahun, selected_periode=sel_periode)

@app.route('/propose')
def propose():
    data = load_all()
    df_stock = data.get('stock', pd.DataFrame()).copy()
    m1 = data.get('m1')
    if df_stock.empty or m1 is None:
        return render_template('dashboard.html', page='propose', error="Data stok atau master tidak tersedia.")
    
    sisa_df = hitung_sisa_bulan(df_stock[df_stock['Jenis']=='Preventive'], m1)
    if sisa_df.empty:
        return render_template('dashboard.html', page='propose', error="Data sisa bulan tidak tersedia.")
    
    if 'primary_code' not in m1.columns:
        m1['primary_code'] = m1['kode_material'].apply(get_primary_code)
    m1_pm = m1[['primary_code','keb_pm']].copy()
    m1_pm.columns = ['Primary Code','Keb_PM']
    m1_pm['Primary Code'] = m1_pm['Primary Code'].astype(str).str.strip().str.upper()
    m1_pm['Keb_PM'] = pd.to_numeric(m1_pm['Keb_PM'], errors='coerce').fillna(0)
    m1_pm = m1_pm.drop_duplicates(subset=['Primary Code'], keep='first')
    sisa_df['Primary Code'] = sisa_df['Primary Code'].astype(str).str.strip().str.upper()
    sisa_df = sisa_df.merge(m1_pm, on='Primary Code', how='left')
    sisa_df['Keb_PM'] = pd.to_numeric(sisa_df['Keb_PM'], errors='coerce').fillna(sisa_df['Keb_Aktual'])
    
    pltd_stok = set(sisa_df['PLTD'].unique())
    pltd_m1 = set(m1['pltd'].dropna().astype(str).str.strip().str.upper().unique())
    pltd_missing = pltd_m1 - pltd_stok
    if pltd_missing:
        m1_miss = m1[m1['pltd'].str.strip().str.upper().isin(pltd_missing)].copy()
        miss_rows = []
        for _, row in m1_miss.iterrows():
            pc = str(row.get('primary_code','')).strip().upper()
            miss_rows.append({
                'PLTD': row['pltd'].strip().upper(),
                'Kode Material': row.get('kode_material', pc),
                'Nama Material': PREVENTIVE_MAP.get(pc, 'Unknown'),
                'Primary Code': pc,
                'Qty': 0,
                'Jenis': 'Preventive',
                'Keb_Aktual': pd.to_numeric(row.get('keb_aktual',0), errors='coerce') or 0,
                'Keb_PM': pd.to_numeric(row.get('keb_pm',0), errors='coerce') or 0,
                'Sisa_Bulan': 0.0
            })
        if miss_rows:
            sisa_df = pd.concat([sisa_df, pd.DataFrame(miss_rows)], ignore_index=True)
    
    for c in ['Qty','Keb_PM','Keb_Aktual']:
        if c in sisa_df.columns:
            sisa_df[c] = pd.to_numeric(sisa_df[c], errors='coerce').fillna(0)
    
    sel_pltd = request.args.getlist('pltd')
    jb = int(request.args.get('jb', 3))
    sel_status = request.args.getlist('status')
    
    prev = sisa_df.copy()
    if sel_pltd:
        prev = prev[prev['PLTD'].isin(sel_pltd)]
    
    prev['Keb_N_Bulan'] = prev['Keb_Aktual'] * jb
    prev['Propose_N_Bulan'] = np.ceil(np.maximum(0, prev['Keb_N_Bulan'] - prev['Qty']))
    
    def sts(row):
        if row['Keb_Aktual'] <= 0:
            return '⚪ No Data'
        if row['Qty'] >= row['Keb_N_Bulan']:
            return '🟢 Aman'
        if row['Sisa_Bulan'] < 1:
            return '🔴 Urgent'
        if row['Sisa_Bulan'] < 2:
            return '🟠 Warning'
        return '🟡 Perlu Order'
    prev['Status'] = prev.apply(sts, axis=1)
    prev = prev[prev['Keb_Aktual'] > 0]
    if sel_status:
        prev = prev[prev['Status'].isin(sel_status)]
    
    # Sisa bulan
    sp = prev.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                          values='Sisa_Bulan', aggfunc='first', fill_value=0.0).reset_index()
    for pltd in SEMUA_PLTD:
        if pltd not in sp.columns:
            sp[pltd] = 0.0
    pltd_cols_s = [p for p in SEMUA_PLTD if p in sp.columns]
    sp = sp[['Kode Material','Nama Material'] + pltd_cols_s]
    for kode in URUTAN_MATERIAL:
        if kode not in sp['Kode Material'].values:
            nama = PREVENTIVE_MAP.get(kode, PREVENTIVE_MAP.get(get_primary_code(kode), 'Unknown'))
            new_row = {'Kode Material': kode, 'Nama Material': nama}
            for p in pltd_cols_s:
                new_row[p] = 0.0
            sp = pd.concat([sp, pd.DataFrame([new_row])], ignore_index=True)
    def urutkan(kode):
        try:
            return URUTAN_MATERIAL.index(kode)
        except ValueError:
            return 999
    sp['_sort'] = sp['Kode Material'].apply(urutkan)
    sp = sp.sort_values('_sort').drop(columns=['_sort'])
    styled_sisa = sp.style.map(lambda val: 'background-color: #ffcccc; color: #cc0000; font-weight: bold;' if isinstance(val, (int, float)) and val <= 1.5 else '', subset=pltd_cols_s)
    sisa_html = styled_sisa.to_html(classes='table table-bordered', index=False)
    
    # PM
    pm_p = prev.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                            values='Keb_PM', aggfunc='first', fill_value=0).round(0).astype(int).reset_index()
    for pltd in SEMUA_PLTD:
        if pltd not in pm_p.columns:
            pm_p[pltd] = 0
    pm_p = pm_p[['Kode Material','Nama Material'] + pltd_cols_s]
    pm_html = pm_p.to_html(classes='table table-bordered', index=False)
    
    # CF
    cf_p = prev.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                            values='Keb_Aktual', aggfunc='first', fill_value=0).round(0).astype(int).reset_index()
    for pltd in SEMUA_PLTD:
        if pltd not in cf_p.columns:
            cf_p[pltd] = 0
    cf_p = cf_p[['Kode Material','Nama Material'] + pltd_cols_s]
    cf_html = cf_p.to_html(classes='table table-bordered', index=False)
    
    # Propose delivery
    dp = prev.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                          values='Propose_N_Bulan', aggfunc='first', fill_value=0).round(0).astype(int).reset_index()
    for pltd in SEMUA_PLTD:
        if pltd not in dp.columns:
            dp[pltd] = 0
    dp = dp[['Kode Material','Nama Material'] + pltd_cols_s]
    def urutkan3(kode):
        try:
            return URUTAN_MATERIAL.index(kode)
        except ValueError:
            return 999
    dp['_sort'] = dp['Kode Material'].apply(urutkan3)
    dp = dp.sort_values('_sort').drop(columns=['_sort'])
    def heatmap_style(val):
        if isinstance(val, (int, float)):
            if val <= 0:
                return 'background-color: #e8f5e9; color: #888;'
            elif val < 50:
                return 'background-color: #fff9c4;'
            elif val < 200:
                return 'background-color: #ffe0b2; font-weight: bold;'
            elif val < 1000:
                return 'background-color: #ffab91; font-weight: bold; color: #bf360c;'
            else:
                return 'background-color: #ef5350; font-weight: bold; color: white;'
        return ''
    styled_dp = dp.style.map(heatmap_style, subset=pltd_cols_s)
    propose_html = styled_dp.to_html(classes='table table-bordered', index=False)
    
    # Rekomendasi
    urg = prev[prev['Status']=='🔴 Urgent']
    wrn = prev[prev['Status']=='🟠 Warning']
    urg_html = urg[['PLTD','Nama Material','Qty','Keb_Aktual','Propose_N_Bulan']].rename(
        columns={'Nama Material':'Material','Keb_Aktual':'Keb/Bulan','Propose_N_Bulan':f'Order ({jb} bln)'}).to_html(classes='table table-danger table-striped', index=False) if not urg.empty else None
    wrn_html = wrn[['PLTD','Nama Material','Qty','Keb_Aktual','Propose_N_Bulan']].rename(
        columns={'Nama Material':'Material','Keb_Aktual':'Keb/Bulan','Propose_N_Bulan':f'Order ({jb} bln)'}).to_html(classes='table table-warning table-striped', index=False) if not wrn.empty else None
    
    pltd_list = sorted(sisa_df['PLTD'].unique())
    status_list = ['🔴 Urgent', '🟠 Warning', '🟡 Perlu Order', '🟢 Aman']
    
    return render_template('dashboard.html', page='propose',
                           sisa_html=sisa_html, pm_html=pm_html,
                           cf_html=cf_html, propose_html=propose_html,
                           urg_html=urg_html, wrn_html=wrn_html,
                           pltd_list=pltd_list, status_list=status_list,
                           selected_pltd=sel_pltd, selected_status=sel_status,
                           jb=jb, total_urg=len(urg), total_wrn=len(wrn),
                           total_urg_qty=urg['Propose_N_Bulan'].sum() if not urg.empty else 0,
                           total_wrn_qty=wrn['Propose_N_Bulan'].sum() if not wrn.empty else 0)

@app.route('/transaksi')
def transaksi():
    URL_OPS = "https://bachmulti-my.sharepoint.com/:x:/g/personal/prabawa_bachgroup_co_id/IQDpLV2xOcHmS51kfDxWqHQAAUHHovDCqOPtICGu3HUp6nc?download=1"
    URL_DAS = "https://bachmulti-my.sharepoint.com/:x:/g/personal/prabawa_bachgroup_co_id/IQBxJHUjgIjQTooUQPRp14iZAUy5KIiRVxLFRW-z8X17lDY?e=QEqUQc&download=1"
    
    @app.cache_data(ttl=600)
    def load_transaksi():
        headers = {'User-Agent': 'Mozilla/5.0'}
        df_ops = pd.DataFrame()
        df_das = pd.DataFrame()
        try:
            res_ops = requests.get(URL_OPS, headers=headers, timeout=20)
            df_ops = pd.read_excel(io.BytesIO(res_ops.content))
            df_ops['PROJECT'] = 'PROJECT PLTD'
        except Exception as e:
            pass
        try:
            res_das = requests.get(URL_DAS, headers=headers, timeout=20)
            if res_das.status_code == 200:
                df_das = pd.read_excel(io.BytesIO(res_das.content), sheet_name='PR MR')
                df_das['PROJECT'] = 'PROJECT DAS'
        except Exception as e:
            pass
        frames = []
        if not df_ops.empty:
            frames.append(df_ops)
        if not df_das.empty:
            frames.append(df_das)
        if frames:
            df = pd.concat(frames, ignore_index=True)
        else:
            df = pd.DataFrame()
        if not df.empty and 'TANGGAL' in df.columns:
            df['TANGGAL'] = pd.to_datetime(df['TANGGAL'], errors='coerce')
            df = df.dropna(subset=['TANGGAL'])
            df['Tahun'] = df['TANGGAL'].dt.year.astype(str)
            df['Bulan'] = df['TANGGAL'].dt.strftime('%B')
            df['Tgl_Str'] = df['TANGGAL'].dt.strftime('%Y-%m-%d')
        for col in ['QTY', 'TOTAL COST']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    
    df_raw = load_transaksi()
    if df_raw.empty:
        return render_template('dashboard.html', page='transaksi', error="Data transaksi tidak tersedia.")
    
    sel_proj = request.args.getlist('proj')
    sel_year = request.args.getlist('year')
    sel_month = request.args.getlist('month')
    sel_stat = request.args.getlist('stat')
    sel_site = request.args.getlist('site')
    
    df_f = df_raw.copy()
    if sel_proj:
        df_f = df_f[df_f['PROJECT'].isin(sel_proj)]
    if sel_year:
        df_f = df_f[df_f['Tahun'].isin(sel_year)]
    if sel_month:
        df_f = df_f[df_f['Bulan'].isin(sel_month)]
    if sel_stat and 'STATUS' in df_f.columns:
        df_f = df_f[df_f['STATUS'].isin(sel_stat)]
    if sel_site:
        df_f = df_f[df_f['WH TUJUAN'].isin(sel_site)]
    
    kpi = {
        'total_order': len(df_f),
        'total_qty': int(df_f['QTY'].sum()),
        'total_biaya': f"Rp {df_f['TOTAL COST'].sum():,.0f}",
        'site_aktif': df_f['WH TUJUAN'].nunique()
    }
    
    trend_html = None
    if not df_f.empty and 'Tgl_Str' in df_f.columns:
        trend_data = df_f.groupby('Tgl_Str').size().reset_index(name='Requests')
        if len(trend_data) > 60:
            trend_data = df_f.groupby(pd.Grouper(key='TANGGAL', freq='W')).size().reset_index(name='Requests')
            trend_data['Tgl_Str'] = trend_data['TANGGAL'].dt.strftime('%Y-%m-%d')
        fig_tr = px.line(trend_data, x='Tgl_Str', y='Requests', markers=True, text='Requests',
                         color_discrete_sequence=['#0E2F56'])
        fig_tr.update_traces(textposition="top center")
        trend_html = fig_tr.to_html(full_html=False)
    
    site_html = None
    if not df_f.empty:
        top_site = df_f.groupby('WH TUJUAN')['QTY'].sum().nlargest(8).reset_index()
        fig_site = px.bar(top_site, x='QTY', y='WH TUJUAN', orientation='h', text='QTY',
                          color='QTY', color_continuous_scale='Blues')
        fig_site.update_layout(yaxis={'categoryorder': 'total ascending'}, height=350)
        fig_site.update_traces(textposition='outside', texttemplate='%{text:,.0f}')
        site_html = fig_site.to_html(full_html=False)
    
    item_html = None
    if not df_f.empty:
        top_item = df_f.groupby('ITEM NAME')['QTY'].sum().nlargest(8).reset_index()
        fig_item = px.bar(top_item, x='QTY', y='ITEM NAME', orientation='h', text='QTY',
                          color_discrete_sequence=['#4B8BBE'])
        fig_item.update_layout(yaxis={'categoryorder': 'total ascending'}, height=350)
        fig_item.update_traces(textposition='outside', texttemplate='%{text:,.0f}')
        item_html = fig_item.to_html(full_html=False)
    
    out_html = None
    if 'STATUS' in df_f.columns:
        df_out = df_f[~df_f['STATUS'].isin(['DELIVERED', 'CANCEL'])]
        if not df_out.empty:
            out_html = df_out[['TANGGAL','PROJECT','WH TUJUAN','ITEM NAME','QTY','STATUS']].head(15).to_html(classes='table table-warning table-striped', index=False)
    
    detail_html = None
    if not df_f.empty:
        cols = ['TANGGAL','PROJECT','WH TUJUAN','ITEM NAME','QTY']
        if 'TOTAL COST' in df_f.columns:
            cols.append('TOTAL COST')
        if 'STATUS' in df_f.columns:
            cols.append('STATUS')
        detail_html = df_f[cols].head(20).to_html(classes='table table-striped table-hover', index=False)
    
    proj_list = sorted(df_raw['PROJECT'].unique())
    year_list = sorted(df_raw['Tahun'].unique(), reverse=True)
    month_list = sorted(df_raw['Bulan'].unique())
    stat_list = sorted(df_raw['STATUS'].dropna().unique()) if 'STATUS' in df_raw.columns else []
    site_list = sorted(df_raw['WH TUJUAN'].dropna().unique())
    
    return render_template('dashboard.html', page='transaksi',
                           kpi=kpi, trend_html=trend_html,
                           site_html=site_html, item_html=item_html,
                           out_html=out_html, detail_html=detail_html,
                           proj_list=proj_list, year_list=year_list,
                           month_list=month_list, stat_list=stat_list,
                           site_list=site_list,
                           selected_proj=sel_proj, selected_year=sel_year,
                           selected_month=sel_month, selected_stat=sel_stat,
                           selected_site=sel_site)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
