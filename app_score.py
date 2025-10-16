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
st.set_page_config(page_title="Ứng dụng tính điểm CLO_30", layout="wide")
st.title("🎓 Ứng dụng tính điểm CLO_30")

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

        df3['134'] = df3['134'].astype(str).str.strip().str.upper()
        df3['210'] = df3['210'].astype(str).str.strip().str.upper()

        df2.columns = [unidecode.unidecode(c.strip().replace(' ', '').lower()) for c in df2.columns]
        for c in df2.columns:
            if c.startswith('cau'):
                df2[c] = df2[c].astype(str).str.strip().str.upper()

        df4['CLO'] = df4['CLO'].astype(str).str.strip().str.upper()
        df4['Điểm'] = pd.to_numeric(df4['Điểm'], errors='coerce').fillna(0)

        # Map điểm từ df4 vào df3
        map_diem = df4.set_index('CLO')['Điểm'].to_dict()
        df3['Điểm_134'] = df3['134'].map(map_diem).fillna(0)
        df3['Điểm_210'] = df3['210'].map(map_diem).fillna(0)

        for c in df3.columns:
            if "Đáp án" in c:
                df3[c] = df3[c].astype(str).str.strip().str.upper()

        # ======= 4. Hàm tính điểm =======
        def calc_clo_scores(row):
            de = int(row['de'])
            clo_scores = {}

            for _, q in df3.iterrows():
                cau_key = q['Câu']
                if cau_key not in row.index:
                    continue
                pa_sv = str(row[cau_key]).strip().upper()

                if de == 134:
                    dap_an = q['Đáp án_134']
                    clo = q['134']
                    diem_cau = q['Điểm_134']
                elif de == 210:
                    dap_an = q['Đáp án_210']
                    clo = q['210']
                    diem_cau = q['Điểm_210']
                else:
                    dap_an, clo, diem_cau = None, None, 0

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
        df_final["Tong diem"] = df_final[cols_diem].sum(axis=1)

        # ======= 8. Tổng hợp CLO1–CLO3 =======
        df_final['CLO1'] = df_final[[c for c in df_final.columns if 'CLO1' in c]].sum(axis=1)
        df_final['CLO2'] = df_final[[c for c in df_final.columns if 'CLO2' in c]].sum(axis=1)
        df_final['CLO3'] = df_final[[c for c in df_final.columns if 'CLO3' in c]].sum(axis=1)
        df_final["Tong diem (CLO tổng)"] = df_final[['CLO1', 'CLO2', 'CLO3']].sum(axis=1)

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

        # ======= 11. Kiểm tra tổng điểm tối đa =======
        max_score = max(df3['Điểm_134'].sum(), df3['Điểm_210'].sum())
        st.info(f"🔍 Tổng điểm tối đa (nếu đúng hết): {max_score}")

    except Exception as e:
        st.error(f"❌ Lỗi khi xử lý dữ liệu: {e}")
