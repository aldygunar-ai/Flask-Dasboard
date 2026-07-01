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
app.secret_key = 'rahasia-ganti-ini'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# ========== SEMUA FUNGSI DARI KODE STREAMLIT ==========
# (Saya salin persis semua fungsi: PLTD_SHEETS, MASTER_PLTD_ID, dll,
#  extract_kode..., norm(), get_primary_code(), is_prev(), is_valid(),
#  get_client(), load_all(), hitung_sisa_bulan(), URUTAN_MATERIAL, dll)
# Karena panjang, saya ringkas di sini – tapi Anda harus menempelkan
# seluruh kode asli Anda di bagian ini.

# ... (tempel semua kode dari Streamlit mulai dari PLTD_SHEETS sampai
#      fungsi hitung_sisa_bulan() dan seterusnya) ...

# ========== ROUTING FLASK ==========

@app.route('/')
def home():
    data = load_all()  # fungsi dari kode asli
    df = data.get('stock', pd.DataFrame())
    if df.empty:
        return render_template('index.html', error="Data belum tersedia.")
    
    # Siapkan metric
    metrics = {
        'pltd_aktif': df['PLTD'].nunique(),
        'total_stok': f"{df['Qty'].sum():,.0f}",
        'preventive': (df['Jenis']=='Preventive').sum(),
        'corrective': (df['Jenis']=='Corrective').sum()
    }
    
    # Map (Plotly scatter_mapbox)
    coords = { ... }  # sama seperti di kode Anda
    loc = df[['PLTD']].drop_duplicates()
    loc['lat'] = loc['PLTD'].map(lambda x: coords.get(x, (None, None))[0])
    loc['lon'] = loc['PLTD'].map(lambda x: coords.get(x, (None, None))[1])
    loc = loc.dropna(subset=['lat'])
    fig_map = px.scatter_mapbox(loc, lat='lat', lon='lon', hover_name='PLTD',
                                zoom=3, height=350, mapbox_style='open-street-map')
    map_html = fig_map.to_html(full_html=False)
    
    # Pie chart
    jenis_counts = df['Jenis'].value_counts().reset_index()
    jenis_counts.columns = ['Jenis', 'Jumlah Item']
    fig_pie = px.pie(jenis_counts, values='Jumlah Item', names='Jenis',
                     color_discrete_sequence=['#2C6E9E', '#E67E22'], hole=0.4)
    fig_pie.update_layout(margin=dict(t=0, b=0), height=300)
    pie_html = fig_pie.to_html(full_html=False)
    
    # Bar chart top PLTD
    top_pltd = df.groupby('PLTD')['Qty'].sum().nlargest(5).reset_index()
    fig_bar = px.bar(top_pltd, x='PLTD', y='Qty', text='Qty',
                     color='Qty', color_continuous_scale='Blues')
    fig_bar.update_traces(texttemplate='%{text:.0f}', textposition='outside')
    fig_bar.update_layout(xaxis_title="", yaxis_title="Total Unit", height=300)
    bar_html = fig_bar.to_html(full_html=False)
    
    # Material kritis (jika ada)
    m1 = data.get('m1')
    kritis_html = None
    if m1 is not None and not df[df['Jenis']=='Preventive'].empty:
        sisa_df = hitung_sisa_bulan(df[df['Jenis']=='Preventive'], m1)
        if not sisa_df.empty:
            kritis = sisa_df[(sisa_df['Sisa_Bulan'] <= 1.5) & (sisa_df['Sisa_Bulan'] > 0)]
            if not kritis.empty:
                top_kritis = kritis.groupby(['Nama Material', 'PLTD'])['Sisa_Bulan'].min().reset_index()
                top_kritis = top_kritis.sort_values('Sisa_Bulan').head(10)
                kritis_html = top_kritis.to_html(classes='table table-striped', index=False)
    
    return render_template('index.html', metrics=metrics, map_html=map_html,
                           pie_html=pie_html, bar_html=bar_html,
                           kritis_html=kritis_html)

@app.route('/stock')
def stock():
    data = load_all()
    df = data['stock'].copy()
    if df.empty:
        return render_template('stock.html', error="Data stok kosong")
    
    # Ambil filter dari query string
    sel_pltd = request.args.getlist('pltd')
    sel_jenis = request.args.getlist('jenis')
    sel_nama = request.args.getlist('nama')
    sel_kode = request.args.getlist('kode')
    highlight = request.args.get('highlight', 'false') == 'true'
    
    # Filter
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
        prev['WH Cikande'] = 0.0 if not prev.empty else None
    
    # Buat pivot table preventive
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
        prev_pivot = p.to_html(classes='table table-striped table-hover', index=False)
    
    # Sisa bulan preventive (sama seperti di Streamlit)
    sisa_pivot = None
    if not prev.empty and m1 is not None:
        sisa_df = hitung_sisa_bulan(prev, m1)
        if not sisa_df.empty:
            sp = sisa_df.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                                     values='Sisa_Bulan', aggfunc='first', fill_value=0.0).reset_index()
            # Tambahkan PLTD yang hilang
            for pltd in SEMUA_PLTD:
                if pltd not in sp.columns:
                    sp[pltd] = 0.0
            pltd_cols_s = [p for p in SEMUA_PLTD if p in sp.columns]
            sp = sp[['Kode Material','Nama Material'] + pltd_cols_s]
            # Urutkan
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
            # Ubah ke HTML dengan styling
            def highlight_style(val):
                if isinstance(val, (int, float)) and val <= 1.5:
                    return 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
                return ''
            styled = sp.style.map(highlight_style, subset=pltd_cols_s)
            sisa_pivot = styled.to_html(classes='table table-bordered', index=False)
    
    # Corrective pivot
    corr_pivot = None
    if not corr.empty:
        p = corr.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                             values='Qty', aggfunc='sum', fill_value=0).round(0).astype(int)
        cik_c = corr.groupby(['Kode Material','Nama Material'])['WH Cikande'].max().round(0).astype(int) if not cik.empty else pd.Series()
        if not cik_c.empty:
            p = p.join(cik_c)
        p['Total'] = p.drop(columns='WH Cikande', errors='ignore').sum(axis=1)
        p = p.reset_index()
        pltd_cols = [c for c in p.columns if c not in ('Kode Material','Nama Material','WH Cikande','Total')]
        p = p[['Kode Material','Nama Material'] + pltd_cols + ['WH Cikande','Total']]
        corr_pivot = p.to_html(classes='table table-striped table-hover', index=False)
    
    # Ambil daftar unik untuk filter
    pltd_list = sorted(df['PLTD'].unique())
    jenis_list = ['Preventive', 'Corrective']
    nama_list = sorted(df['Nama Material'].unique())
    kode_list = sorted(df['Kode Material'].unique())
    
    return render_template('stock.html',
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
        return render_template('analisis.html', error="Data pemakaian kosong")
    
    # Normalisasi nama (sama seperti di kode asli)
    nama_map = {
        'water coollant reco-cool - drum': 'WATER COOLLANT RECO-COOL',
        'filter udara af872': 'FILTER UDARA AF872',
        # ... tambahkan semua mapping dari kode asli ...
    }
    df_pakai['Nama Material'] = df_pakai['Nama Material'].str.strip().str.lower().apply(
        lambda x: nama_map.get(x, x.upper()))
    # Konversi numerik
    for c in ['Masuk','Keluar','Stok','TOTAL_COST']:
        if c in df_pakai.columns:
            df_pakai[c] = pd.to_numeric(df_pakai[c], errors='coerce').fillna(0)
    # Tanggal
    if 'Tanggal' in df_pakai.columns:
        df_pakai['Tanggal'] = pd.to_datetime(df_pakai['Tanggal'], errors='coerce')
        df_pakai['Tahun'] = df_pakai['Tanggal'].dt.year.astype('Int64').astype(str).replace('<NA>','')
        bln = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'Mei',6:'Jun',7:'Jul',8:'Ags',9:'Sep',10:'Okt',11:'Nov',12:'Des'}
        df_pakai['Periode'] = df_pakai['Tanggal'].dt.month.map(bln).fillna('')
        df_pakai['BulanStr'] = df_pakai['Tanggal'].dt.strftime('%Y-%m').replace('NaT','')
    
    # Filter dari query
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
    
    # Hitung cost
    pc = f.pivot_table(index='Nama Material', values=['Keluar','TOTAL_COST'],
                       aggfunc={'Keluar':'sum','TOTAL_COST':'sum'})
    pc = pc[pc['TOTAL_COST'] > 0]
    total_cost = pc['TOTAL_COST'].sum()
    
    # KPI
    kpi = {
        'total_trans': len(f),
        'total_keluar': f['Keluar'].sum() if 'Keluar' in f.columns else 0,
        'unik_material': len(pc),
        'grand_total': f"Rp {total_cost:,.0f}"
    }
    
    # Tren
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
    
    # Top 10 cost
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
    
    # Top 10 inbound/outbound
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
    
    # Detail tabel
    detail_html = None
    if not f.empty:
        cols = ['Tanggal','Nama Material','Masuk','Keluar','Stok','Gudang','Keterangan','Transaksi','JobType','TOTAL_COST']
        cols = [c for c in cols if c in f.columns]
        if 'Tanggal' in f.columns:
            f = f.sort_values('Tanggal', ascending=False)
        detail_html = f[cols].head(50).to_html(classes='table table-striped', index=False)
    
    # Daftar filter
    nama_list = sorted(df_pakai['Nama Material'].unique().astype(str))
    gudang_list = sorted(df_pakai['Gudang'].unique().astype(str)) if 'Gudang' in df_pakai.columns else []
    tahun_list = sorted([str(t) for t in df_pakai['Tahun'].unique() if pd.notna(t) and str(t) not in ['','<NA>','None','nan']]) if 'Tahun' in df_pakai.columns else []
    periode_list = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Ags','Sep','Okt','Nov','Des']
    
    return render_template('analisis.html', kpi=kpi, trend_html=trend_html,
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
        return render_template('propose.html', error="Data stok atau master tidak tersedia.")
    
    # Hitung sisa bulan
    sisa_df = hitung_sisa_bulan(df_stock[df_stock['Jenis']=='Preventive'], m1)
    if sisa_df.empty:
        return render_template('propose.html', error="Data sisa bulan tidak tersedia.")
    
    # Gabung keb_pm
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
    
    # Tambahkan PLTD yang tidak ada stok tapi ada di m1 (sama seperti kode asli)
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
    
    # Filter dari query
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
    
    # Sisa stok dalam bulan (pivot)
    sp = prev.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                          values='Sisa_Bulan', aggfunc='first', fill_value=0.0).reset_index()
    for pltd in SEMUA_PLTD:
        if pltd not in sp.columns:
            sp[pltd] = 0.0
    pltd_cols_s = [p for p in SEMUA_PLTD if p in sp.columns]
    sp = sp[['Kode Material','Nama Material'] + pltd_cols_s]
    # Tambahkan material yang hilang
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
    # Styling untuk sisa bulan
    def hl_sisa(val):
        if isinstance(val, (int, float)) and val <= 1.5:
            return 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
        return ''
    styled_sisa = sp.style.map(hl_sisa, subset=pltd_cols_s)
    sisa_html = styled_sisa.to_html(classes='table table-bordered', index=False)
    
    # PM per bulan
    pm_p = prev.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                            values='Keb_PM', aggfunc='first', fill_value=0).round(0).astype(int).reset_index()
    for pltd in SEMUA_PLTD:
        if pltd not in pm_p.columns:
            pm_p[pltd] = 0
    pm_p = pm_p[['Kode Material','Nama Material'] + pltd_cols_s]
    pm_html = pm_p.to_html(classes='table table-bordered', index=False)
    
    # CF aktual per bulan
    cf_p = prev.pivot_table(index=['Kode Material','Nama Material'], columns='PLTD',
                            values='Keb_Aktual', aggfunc='first', fill_value=0).round(0).astype(int).reset_index()
    for pltd in SEMUA_PLTD:
        if pltd not in cf_p.columns:
            cf_p[pltd] = 0
    cf_p = cf_p[['Kode Material','Nama Material'] + pltd_cols_s]
    cf_html = cf_p.to_html(classes='table table-bordered', index=False)
    
    # Propose delivery (heatmap)
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
    
    # Rekomendasi order (urgent & warning)
    urg = prev[prev['Status']=='🔴 Urgent']
    wrn = prev[prev['Status']=='🟠 Warning']
    urg_html = urg[['PLTD','Nama Material','Qty','Keb_Aktual','Propose_N_Bulan']].rename(
        columns={'Nama Material':'Material','Keb_Aktual':'Keb/Bulan','Propose_N_Bulan':f'Order ({jb} bln)'}).to_html(classes='table table-danger', index=False) if not urg.empty else None
    wrn_html = wrn[['PLTD','Nama Material','Qty','Keb_Aktual','Propose_N_Bulan']].rename(
        columns={'Nama Material':'Material','Keb_Aktual':'Keb/Bulan','Propose_N_Bulan':f'Order ({jb} bln)'}).to_html(classes='table table-warning', index=False) if not wrn.empty else None
    
    pltd_list = sorted(sisa_df['PLTD'].unique())
    status_list = ['🔴 Urgent', '🟠 Warning', '🟡 Perlu Order', '🟢 Aman']
    
    return render_template('propose.html', sisa_html=sisa_html, pm_html=pm_html,
                           cf_html=cf_html, propose_html=propose_html,
                           urg_html=urg_html, wrn_html=wrn_html,
                           pltd_list=pltd_list, status_list=status_list,
                           selected_pltd=sel_pltd, selected_status=sel_status,
                           jb=jb, total_urg=len(urg), total_wrn=len(wrn),
                           total_urg_qty=urg['Propose_N_Bulan'].sum() if not urg.empty else 0,
                           total_wrn_qty=wrn['Propose_N_Bulan'].sum() if not wrn.empty else 0)

@app.route('/transaksi')
def transaksi():
    # Fungsi load transaksi dari SharePoint (sama seperti kode asli)
    URL_OPS = "https://bachmulti-my.sharepoint.com/..."
    URL_DAS = "https://bachmulti-my.sharepoint.com/..."
    
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
        return render_template('transaksi.html', error="Data transaksi tidak tersedia.")
    
    # Filter dari query
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
    
    # KPI
    kpi = {
        'total_order': len(df_f),
        'total_qty': int(df_f['QTY'].sum()),
        'total_biaya': f"Rp {df_f['TOTAL COST'].sum():,.0f}",
        'site_aktif': df_f['WH TUJUAN'].nunique()
    }
    
    # Tren harian
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
    
    # Top site
    site_html = None
    if not df_f.empty:
        top_site = df_f.groupby('WH TUJUAN')['QTY'].sum().nlargest(8).reset_index()
        fig_site = px.bar(top_site, x='QTY', y='WH TUJUAN', orientation='h', text='QTY',
                          color='QTY', color_continuous_scale='Blues')
        fig_site.update_layout(yaxis={'categoryorder': 'total ascending'}, height=350)
        fig_site.update_traces(textposition='outside', texttemplate='%{text:,.0f}')
        site_html = fig_site.to_html(full_html=False)
    
    # Top item
    item_html = None
    if not df_f.empty:
        top_item = df_f.groupby('ITEM NAME')['QTY'].sum().nlargest(8).reset_index()
        fig_item = px.bar(top_item, x='QTY', y='ITEM NAME', orientation='h', text='QTY',
                          color_discrete_sequence=['#4B8BBE'])
        fig_item.update_layout(yaxis={'categoryorder': 'total ascending'}, height=350)
        fig_item.update_traces(textposition='outside', texttemplate='%{text:,.0f}')
        item_html = fig_item.to_html(full_html=False)
    
    # Outstanding
    out_html = None
    if 'STATUS' in df_f.columns:
        df_out = df_f[~df_f['STATUS'].isin(['DELIVERED', 'CANCEL'])]
        if not df_out.empty:
            out_html = df_out[['TANGGAL','PROJECT','WH TUJUAN','ITEM NAME','QTY','STATUS']].head(15).to_html(classes='table table-warning', index=False)
    
    # Detail
    detail_html = None
    if not df_f.empty:
        cols = ['TANGGAL','PROJECT','WH TUJUAN','ITEM NAME','QTY']
        if 'TOTAL COST' in df_f.columns:
            cols.append('TOTAL COST')
        if 'STATUS' in df_f.columns:
            cols.append('STATUS')
        detail_html = df_f[cols].head(20).to_html(classes='table table-striped', index=False)
    
    # Filter options
    proj_list = sorted(df_raw['PROJECT'].unique())
    year_list = sorted(df_raw['Tahun'].unique(), reverse=True)
    month_list = sorted(df_raw['Bulan'].unique())
    stat_list = sorted(df_raw['STATUS'].dropna().unique()) if 'STATUS' in df_raw.columns else []
    site_list = sorted(df_raw['WH TUJUAN'].dropna().unique())
    
    return render_template('transaksi.html', kpi=kpi, trend_html=trend_html,
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