#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 2025
@author: trieukimlanh

🎓 Ứng dụng tính điểm CLO_30
"""

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import unidecode

# ====================== GIAO DIỆN ======================
st.set_page_config(page_title="Ứng dụng tính điểm CLO", layout="wide")
st.title("🎓 Ứng dụng tính điểm CLO")

st.sidebar.header("⚙️ Upload dữ liệu")
uploaded_files = st.sidebar.file_uploader(
    "📂 Tải lên các file CSV (df1.csv, df2.csv, df3.csv, df4.csv)",
    type=["csv"],
    accept_multiple_files=True
)

# --- Nút xử lý ---
if st.sidebar.button("▶️ Thực hiện tính điểm"):
    if not uploaded_files:
        st.error("⚠️ Vui lòng tải đủ 4 file df1, df2, df3, df4 trước khi chạy.")
        st.stop()

    # ======= 1. Tự nhận dạng file =======
    df1_file = next((f for f in uploaded_files if "df1" in f.name.lower()), None)
    df2_file = next((f for f in uploaded_files if "df2" in f.name.lower()), None)
    df3_file = next((f for f in uploaded_files if "df3" in f.name.lower()), None)
    df4_file = next((f for f in uploaded_files if "df4" in f.name.lower()), None)

    if not all([df1_file, df2_file, df3_file, df4_file]):
        st.error("⚠️ Thiếu file! Cần có đủ df1.csv, df2.csv, df3.csv và df4.csv.")
        st.stop()

    try:
        # ======= 2. Đọc dữ liệu =======
        df1 = pd.read_csv(df1_file)
        df2 = pd.read_csv(df2_file)
        df3 = pd.read_csv(df3_file)
        df4 = pd.read_csv(df4_file)

        # ======= 3. Chuẩn hóa =======
        df3['Câu'] = (
            df3['Câu'].astype(str)
            .apply(unidecode.unidecode)
            .str.strip()
            .str.replace(' ', '')
            .str.lower()
        )

        # Tự động nhận diện các cột mã đề (loại bỏ cột 'Câu' và 'Đáp án...')
        ma_de_cols = [c for c in df3.columns if c.lower() not in ['câu'] and "đáp" not in c.lower()]
        dap_an_cols = [c for c in df3.columns if "đáp" in c.lower()]

        df2.columns = [unidecode.unidecode(c.strip().replace(' ', '').lower()) for c in df2.columns]
        for c in df2.columns:
            if c.startswith('cau'):
                df2[c] = df2[c].astype(str).str.strip().str.upper()

        # Chuẩn hóa df4 và ánh xạ điểm
        df4['CLO'] = df4['CLO'].astype(str).str.strip().str.upper()
        df4['Điểm'] = pd.to_numeric(df4['Điểm'], errors='coerce').fillna(0)
        map_diem = df4.set_index('CLO')['Điểm'].to_dict()

        # Tạo các cột điểm cho từng mã đề (tự động)
        for ma_de in ma_de_cols:
            df3[f'Điểm_{ma_de}'] = df3[ma_de].map(map_diem).fillna(0)

        # Chuẩn hóa đáp án
        for c in dap_an_cols:
            df3[c] = df3[c].astype(str).str.strip().str.upper()

        # ======= 4. Hàm tính điểm tự động =======
        def calc_clo_scores(row):
            try:
                de = str(int(row['de'])) if not pd.isna(row['de']) else str(row['de']).strip()
            except:
                de = str(row['de']).strip()
            clo_scores = {}

            # Dò xem mã đề có tồn tại trong df3 không
            if de not in ma_de_cols:
                return pd.Series(clo_scores)

            # Tìm cột đáp án tương ứng
            dap_an_col = next((c for c in dap_an_cols if de in c), None)
            diem_col = f'Điểm_{de}'

            for _, q in df3.iterrows():
                cau_key = q['Câu']
                if cau_key not in row.index:
                    continue
                pa_sv = str(row[cau_key]).strip().upper()

                dap_an = q[dap_an_col] if dap_an_col in q else None
                clo = q[de]
                diem_cau = q[diem_col] if diem_col in q else 0

                if dap_an and pa_sv == dap_an:
                    clo_scores[clo] = clo_scores.get(clo, 0) + diem_cau

            return pd.Series(clo_scores)

        # ======= 5. Tính điểm =======
        df_clo = df2.apply(calc_clo_scores, axis=1)
        df_clo.insert(0, 'MSSV', df2['mssv'])

        # ======= 6. Gộp vào danh sách sinh viên =======
        df_final = pd.merge(
            df1.drop(columns=[col for col in df1.columns if 'CLO' in col or 'Tong' in col], errors='ignore'),
            df_clo,
            on='MSSV',
            how='left'
        ).fillna(0)

        # ======= 7. Tính tổng điểm =======
        cols_diem = [c for c in df_final.columns if 'CLO' in c]
        if cols_diem:
            df_final["Tong diem"] = df_final[cols_diem].sum(axis=1)
        else:
            df_final["Tong diem"] = 0

        # ======= 8. Tổng hợp CLO1–CLO3 (tự động) =======
        for i in range(1, 6):  # linh hoạt nếu sau này có CLO4, CLO5
            clo_cols = [c for c in df_final.columns if f'CLO{i}' in c]
            if clo_cols:
                df_final[f'CLO{i}'] = df_final[clo_cols].sum(axis=1)

        clo_group_cols = [c for c in df_final.columns if c.startswith('CLO') and len(c) == 4]
        df_final["Tong diem (CLO tổng)"] = df_final[clo_group_cols].sum(axis=1)

        # ======= 9. Hiển thị & tải kết quả =======
        st.success("✅ Tính điểm hoàn tất!")
        st.subheader("📊 Kết quả tổng hợp điểm CLO")
        st.dataframe(df_final)

        csv_final = df_final.to_csv(index=False).encode('utf-8-sig')
        st.download_button("💾 Tải file kết quả đầy đủ", csv_final, "ket_qua_tich_hop_full.csv", "text/csv")

        # ======= 10. Phổ điểm =======
        st.subheader("🎯 Phổ điểm sinh viên (theo tổng điểm CLO)")
        bins = [0, 5, 6, 7, 8, 9, 10]
        labels = ["Dưới 5", "Từ 5 - <6", "Từ 6 - <7", "Từ 7 - <8", "Từ 8 - <9", "Từ 9 - 10"]

        df_final["Nhóm điểm"] = pd.cut(
            df_final["Tong diem (CLO tổng)"], bins=bins, labels=labels,
            right=False, include_lowest=True
        )
        score_dist = df_final["Nhóm điểm"].value_counts().reindex(labels, fill_value=0)

        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(score_dist.reset_index().rename(columns={'index': 'Khoảng điểm', 'Nhóm điểm': 'Số SV'}))
        with col2:
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.bar(score_dist.index, score_dist.values, color='skyblue', edgecolor='black')
            ax.set_title("Phổ điểm sinh viên")
            ax.set_xlabel("Khoảng điểm")
            ax.set_ylabel("Số sinh viên")
            for i, v in enumerate(score_dist.values):
                ax.text(i, v + 0.2, str(v), ha='center')
            st.pyplot(fig)

        # ======= 11. Tổng điểm tối đa linh hoạt =======
        max_score = sum(df3[f'Điểm_{ma}'].sum() for ma in ma_de_cols if f'Điểm_{ma}' in df3.columns)
        st.info(f"🔍 Tổng điểm tối đa (nếu đúng hết): {max_score}")

    except Exception as e:
        st.error(f"❌ Lỗi khi xử lý dữ liệu: {e}")
