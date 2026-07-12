import streamlit as st
import datetime
import base64
import os
import csv
import pandas as pd
import streamlit.components.v1 as components

# --- KONFIGURASI ---
st.set_page_config(page_title="MYSA SPACE POS", layout="wide")
CSV_FILE = "riwayat_transaksi.csv"

# --- CSS KHUSUS UNTUK PRINTER THERMAL ---
st.markdown("""
<style>
@media print {
    body * { visibility: hidden; }
    #printable-receipt, #printable-receipt * { visibility: visible; }
    #printable-receipt { position: absolute; left: 0; top: 0; width: 100%; margin: 0; padding: 0; }
}
</style>
""", unsafe_allow_html=True)

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except: 
        return None

# --- DATABASE MENU LENGKAP ---
menu = {
    "☕ COFFEE": {
        "Americano": 28000, "Ice Americano with Honey": 30000, "Cappuccino (Hot)": 38000, 
        "Cappuccino (Ice)": 40000, "Cafe Latte (Hot/Ice)": 38000, "Dirty Iced Cafe Latte": 38000,
        "Ice Japanese Coffee Milk": 40000, "Ice Honey Espresso Oat Latte": 40000, 
        "Ice Cinnamon Espresso Oat Latte": 40000, "Ice Ceremonial Dirty Matcha": 65000
    },
    "🍵 NON-COFFEE": {
        "Ceremonial Matcha Latte": 55000, "Choco Latte (Hot/Ice)": 38000, "Chai Latte (Hot/Ice)": 38000, 
        "Babyccino": 30000, "Tea (Hot/Ice)": 20000, "Ice Lychee Tea": 35000, "Yuzu Mint Tea (Hot/Ice)": 38000
    },
    "🥤 SOFT DRINK & BEER": {
        "Aqua Cube 220ml": 8000, "Aqua Life 1.1L": 30000, "Green Tea Pokka": 28000, 
        "Chrysanthemum Tea": 28000, "Hoegaarden Rose": 85000
    },
    "🥐 SNACK & FOOD": {
        "Tahu Isi": 16000, "Lontong Oncom": 16000, "Pastel Sambal Kacang": 16000, 
        "Risoles Chicken Ragout": 16000, "Kue Soes": 16000, "Bolu Marbel": 16000, 
        "Lupis": 16000, "Nasi Kuning": 46000, "Nasi Cumi": 46000, "Lasagna": 46000
    }
}

if 'keranjang' not in st.session_state: 
    st.session_state.keranjang = []

def update_keranjang(nama, harga, delta):
    for it in st.session_state.keranjang:
        if it['nama'] == nama:
            it['jumlah'] += delta
            it['subtotal'] = it['jumlah'] * it['harga']
            if it['jumlah'] <= 0: 
                st.session_state.keranjang.remove(it)
            return
    if delta > 0: 
        st.session_state.keranjang.append({"nama": nama, "jumlah": 1, "harga": harga, "subtotal": harga})

# --- UI ---
logo_b64 = get_base64_image("logomysa.jpeg")
col_t1, col_t2 = st.columns([1, 6])
with col_t1:
    if logo_b64: 
        st.markdown(f'<img src="data:image/jpeg;base64,{logo_b64}" width="80" style="border-radius: 50%;">', unsafe_allow_html=True)
with col_t2: 
    st.title("Sistem Kasir MYSA SPACE")

col1, col2 = st.columns([2, 1])

with col1:
    tabs = st.tabs(list(menu.keys()))
    for i, cat in enumerate(menu.keys()):
        with tabs[i]:
            cols = st.columns(3)
            for idx, (nama, harga) in enumerate(menu[cat].items()):
                with cols[idx % 3]:
                    st.info(f"**{nama}**\nRp {harga:,}")
                    if st.button("Tambah", key=f"add_{cat}_{nama}"): 
                        update_keranjang(nama, harga, 1)
                        st.rerun()

with col2:
    st.subheader("🛒 Keranjang")
    total = 0
    total_items = 0
    for it in st.session_state.keranjang:
        c1, c2, c3, c4 = st.columns([2, 0.5, 0.5, 1])
        c1.write(f"**{it['nama']}**")
        if c2.button("-", key=f"min_{it['nama']}"): 
            update_keranjang(it['nama'], it['harga'], -1)
            st.rerun()
        c3.write(f" {it['jumlah']} ")
        if c4.button("+", key=f"pls_{it['nama']}"): 
            update_keranjang(it['nama'], it['harga'], 1)
            st.rerun()
        total += it['subtotal']
        total_items += it['jumlah']
    
    st.markdown("---")
    st.markdown(f"### Total: Rp {total:,}")
    tipe = st.radio("Tipe:", ["Dine In", "Take Away"])
    metode = st.radio("Metode Bayar:", ["QRIS", "Debit"])
    
    if st.button("✅ Cetak Struk & Simpan", type="primary"):
        if not st.session_state.keranjang:
            st.warning("Keranjang masih kosong!")
        else:
            now = datetime.datetime.now()
            tgl, jam = now.strftime("%d %b %Y"), now.strftime("%H:%M:%S")
            
            # --- LOGIKA ORDER ID BARU (MS + YY + MM + NNN) ---
            prefix_oid = now.strftime("MS%y%m") # Menghasilkan "MS2607" untuk Juli 2026
            urutan = 1
            
            if os.path.exists(CSV_FILE):
                try:
                    df_temp = pd.read_csv(CSV_FILE)
                    if not df_temp.empty and 'Order ID' in df_temp.columns:
                        # Filter transaksi yang Order ID-nya dimulai dengan prefix bulan ini
                        df_temp['Order ID'] = df_temp['Order ID'].astype(str)
                        df_bulan_ini = df_temp[df_temp['Order ID'].str.startswith(prefix_oid)]
                        
                        if not df_bulan_ini.empty:
                            # Ambil Order ID baris terakhir
                            last_oid = df_bulan_ini.iloc[-1]['Order ID']
                            # Ekstrak 3 digit terakhir dan jadikan angka, lalu tambah 1
                            last_urutan = int(last_oid[-3:])
                            urutan = last_urutan + 1
                            
                            # Jika urutan melebihi 999, kembali ke 1 (sesuai batas maksimal)
                            if urutan > 999:
                                urutan = 1
                except Exception:
                    pass # Jika terjadi error (misal file korup), otomatis mulai dari 1
            
            # Format menjadi 3 digit (contoh: 1 menjadi "001")
            oid = f"{prefix_oid}{urutan:03d}"
            # ------------------------------------------------

            items_html = "".join([f"<tr><td>{it['nama']}<br>{it['jumlah']}x @ {it['harga']:,}</td><td style='text-align:right; vertical-align:bottom;'>{it['subtotal']:,}</td></tr>" for it in st.session_state.keranjang])
            
            struk_total_items = sum([it['jumlah'] for it in st.session_state.keranjang])
            ringkasan_pesanan = ", ".join([f"{it['nama']} ({it['jumlah']}x)" for it in st.session_state.keranjang])

            # Simpan Data Transaksi ke CSV
            file_exists = os.path.isfile(CSV_FILE)
            with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Order ID', 'Tanggal', 'Jam', 'Tipe Pesanan', 'Metode Bayar', 'Total Item', 'Total Pendapatan', 'Detail Pesanan'])
                writer.writerow([oid, tgl, jam, tipe, metode, struk_total_items, total, ringkasan_pesanan])

            # HTML Struk (Menggunakan tabel agar titik dua ":" sejajar sempurna)
            st.session_state.struk_terakhir = f"""<div id="printable-receipt">
<div style="background:#fff; padding:20px; border:1px solid #ccc; width:300px; font-family:'Courier New', monospace; font-size:11px; color:#000;">
<div style="text-align:center; border-bottom:1px dashed #000; padding-bottom:10px;">
{f'<img src="data:image/jpeg;base64,{logo_b64}" width="80" style="border-radius:50%">' if logo_b64 else ''}
<h2 style="margin:5px 0;">MYSA SPACE</h2>
<p style="margin:0;">Jl. RC Veteran Raya No 29B.<br>RT01/RW01 Bintaro Jakarta Selatan</p>
<p style="margin:0;">WA: 082312487402</p>
</div>
<div style="margin:10px 0; text-align:left;">
<div style="display:flex; justify-content:space-between; margin-bottom:5px;">
<span>{tgl}</span> <span>{jam}</span>
</div>
<table style="width:100%; border:none; margin:0; padding:0; font-size:11px; font-family:'Courier New', monospace; color:#000;">
<tr><td style="width:70px; padding:2px 0;">Order ID</td><td style="width:10px; padding:2px 0;">:</td><td style="padding:2px 0;">{oid}</td></tr>
<tr><td style="padding:2px 0;">Served By</td><td style="padding:2px 0;">:</td><td style="padding:2px 0;">Dhesy</td></tr>
<tr><td style="padding:2px 0;">Payment</td><td style="padding:2px 0;">:</td><td style="padding:2px 0;">{metode}</td></tr>
</table>
<div style="text-align:center; font-weight:bold; margin-top:5px;">--- {tipe} ---</div>
</div>
<table style="width:100%; border-collapse:collapse;">{items_html}</table>
<div style="border-top:1px dashed #000; margin-top:10px; padding-top:10px;">
<div style="margin-bottom:10px; text-align:left;">
Jumlah Item: {struk_total_items}
</div>
<div style="display:flex; justify-content:flex-end; font-weight:bold; font-size:14px;">
<div style="width:70px; text-align:left;">TOTAL</div> 
<div style="text-align:right;">Rp {total:,}</div>
</div>
<div style="display:flex; justify-content:flex-end; font-weight:bold; font-size:14px; margin-top:2px;">
<div style="width:70px; text-align:left;">{metode}</div> 
<div style="text-align:right;">Rp {total:,}</div>
</div>
</div>
<div style="text-align:center; margin-top:15px; border-top:1px dashed #000; padding-top:10px;">
<p style="margin:0;">Terima Kasih!</p>
<p style="margin:0;">IG: @mysaspacejakarta</p>
</div>
</div>
</div>"""
            
            st.session_state.keranjang = []
            st.success("Transaksi Berhasil Disimpan!")
            st.rerun()

# --- TAMPILAN BAWAH (STRUK & RIWAYAT) ---
st.markdown("---")
col_bawah1, col_bawah2 = st.columns([1, 2])

with col_bawah1:
    if 'struk_terakhir' in st.session_state and st.session_state.struk_terakhir:
        st.markdown("### 📄 Struk Terakhir")
        st.markdown(st.session_state.struk_terakhir, unsafe_allow_html=True)
        
        # Fitur Download Gambar (PNG)
        download_js = """
        <script>
        if (!window.parent.document.getElementById('html2canvas-script')) {
            var script = window.parent.document.createElement('script');
            script.id = 'html2canvas-script';
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
            window.parent.document.head.appendChild(script);
        }

        function downloadStruk() {
            var parentWin = window.parent;
            var target = parentWin.document.getElementById('printable-receipt');
            
            if (parentWin.html2canvas) {
                parentWin.html2canvas(target, { backgroundColor: '#ffffff', scale: 2 }).then(function(canvas) {
                    var link = parentWin.document.createElement('a');
                    link.download = 'Struk_MYSA_SPACE.png';
                    link.href = canvas.toDataURL('image/png');
                    link.click();
                });
            } else {
                alert('Sistem sedang menyiapkan gambar. Silakan klik tombol sekali lagi.');
            }
        }
        </script>
        <button onclick="downloadStruk()" style="width:100%; padding:10px 0; background-color:#ff4b4b; color:white; border:none; border-radius:8px; font-size:16px; font-weight:bold; cursor:pointer; font-family:sans-serif; margin-bottom: 10px;">⬇️ Download Struk (PNG)</button>
        """
        components.html(download_js, height=55)
        
        # Tombol Print Fisik
        if st.button("🖨️ Cetak Fisik ke Printer", type="secondary", use_container_width=True):
            components.html("<script>window.parent.print();</script>", width=0, height=0)

with col_bawah2:
    st.markdown("### 📊 Riwayat Transaksi Hari Ini")
    if os.path.exists(CSV_FILE):
        df_riwayat = pd.read_csv(CSV_FILE)
        
        if df_riwayat.empty:
            st.info("Belum ada data transaksi yang tersimpan.")
        else:
            st.dataframe(df_riwayat.iloc[::-1], use_container_width=True, hide_index=True)
            total_pendapatan = df_riwayat['Total Pendapatan'].sum()
            total_terjual = df_riwayat['Total Item'].sum()
            st.info(f"**Ringkasan Penjualan:** {len(df_riwayat)} Transaksi | Terjual: {total_terjual} Item | Omzet: Rp {total_pendapatan:,}")
            
            # --- FITUR HAPUS TRANSAKSI SPESIFIK ---
            st.markdown("#### Manajemen Riwayat")
            col_m1, col_m2 = st.columns([2, 1])
            with col_m1:
                # Pilihan dropdown bisa memilih lebih dari satu (multiselect)
                list_order = df_riwayat['Order ID'].tolist()
                order_to_delete = st.multiselect("Pilih Order ID yang ingin dihapus:", list_order)
            with col_m2:
                st.write("") # Memberi jarak agar tombol sejajar dengan kotak input
                st.write("")
                if st.button("🗑️ Hapus Transaksi Terpilih", use_container_width=True):
                    if order_to_delete:
                        # Menghapus baris yang Order ID-nya dipilih
                        df_riwayat = df_riwayat[~df_riwayat['Order ID'].isin(order_to_delete)]
                        df_riwayat.to_csv(CSV_FILE, index=False)
                        st.success("Transaksi berhasil dihapus!")
                        st.rerun()
                    else:
                        st.warning("Pilih minimal 1 transaksi untuk dihapus.")
            
            st.markdown("---")
            # Fitur Hapus Semua & Download Riwayat
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🚨 Hapus Semua Riwayat", use_container_width=True):
                    os.remove(CSV_FILE)
                    st.rerun()
            with col_btn2:
                csv_data = df_riwayat.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="💾 Download Excel (CSV)",
                    data=csv_data,
                    file_name=f"Riwayat_Penjualan_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    else:
        st.info("Belum ada data transaksi yang tersimpan.")
