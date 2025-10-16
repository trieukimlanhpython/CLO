#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 2025
@author: trieukimlanh

🎓 Ứng dụng tính điểm CLO (tự nhận dạng mã đề & CLO)
streamlit run "app_clo.py"
"""

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import unidecode

# ====================== GIAO DIỆN ======================
st.set_page_config(page_title="Ứng dụng tính điểm CLO", layout="wide")
st.title("🎓 Ứng dụng tính điểm CLO (tự nhận mã đề)")

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

        # ======= 3. Chuẩn hóa dữ liệu =======
        df3['Câu'] = (
            df3['Câu'].astype(str)
            .apply(unidecode.unidecode)
            .str.strip()
            .str.replace(' ', '')
            .str.lower()
        )

        # Nhận diện các cột mã đề (loại trừ cột "Câu" và các cột "Đáp án_*")
        de_cols = [c for c in df3.columns if c not in ['Câu'] and not c.startswith("Đáp án")]

        # Chuẩn hóa đáp án
        for c in df3.columns:
            if "Đáp án" in c:
                df3[c] = df3[c].astype(str).str.strip().str.upper()

        # Chuẩn hóa df2 (bài làm SV)
        df2.columns = [unidecode.unidecode(c.strip().replace(' ', '').lower()) for c in df2.columns]
        for c in df2.columns:
            if c.startswith('cau'):
                df2[c] = df2[c].astype(str).str.strip().str.upper()

        # Chuẩn hóa df4 (điểm từng CLO)
        df4['CLO'] = df4['CLO'].astype(str).str.strip().str.upper()
        df4['Điểm'] = pd.to_numeric(df4['Điểm'], errors='coerce').fillna(0)
        map_diem = df4.set_index('CLO')['Điểm'].to_dict()

        # ======= 4. Map điểm CLO vào df3 cho từng mã đề =======
        for de in de_cols:
            df3[f"Điểm_{de}"] = df3[de].map(map_diem).fillna(0)

        # ======= 5. Hàm tính điểm (linh hoạt với nhiều đề) =======
        def calc_clo_scores(row):
            clo_scores = {}
            de = str(int(row['de'])) if pd.notna(row['de']) else None
            if not de or f"Đáp án_{de}" not in df3.columns:
                return pd.Series(clo_scores)

            for _, q in df3.iterrows():
                cau_key = q['Câu']
                if cau_key not in row.index:
                    continue

                pa_sv = str(row[cau_key]).strip().upper()
                dap_an = str(q.get(f"Đáp án_{de}", "")).strip().upper()
                clo = q.get(de, None)
                diem_cau = q.get(f"Điểm_{de}", 0)

                if clo and dap_an and pa_sv == dap_an:
                    clo_scores[clo] = clo_scores.get(clo, 0) + diem_cau

            return pd.Series(clo_scores)

        # ======= 6. Tính điểm CLO cho tất cả sinh viên =======
        df_clo = df2.apply(calc_clo_scores, axis=1)
        df_clo.insert(0, 'MSSV', df2['mssv'])

        # ======= 7. Gộp kết quả vào danh sách sinh viên =======
        # ❗ Xóa hoàn toàn các cột có chứa "CLO" hoặc "Tong" trước khi merge
        df1_clean = df1.loc[:, ~df1.columns.str.contains('CLO|Tong', case=False, regex=True)]
        
        df_final = pd.merge(
            df1_clean,
            df_clo,
            on='MSSV',
            how='left'
        ).fillna(0)


        # ======= 8. Tính tổng điểm =======
        cols_diem = [c for c in df_final.columns if 'CLO' in c]
        df_final["Tổng điểm"] = df_final[cols_diem].sum(axis=1)

        # ======= 9. Tổng hợp điểm theo CLO1–CLO3 =======
        for i in range(1, 6):
            col_name = f'CLO{i}'
            related_cols = [c for c in df_final.columns if col_name in c]
            if related_cols:
                df_final[col_name] = df_final[related_cols].sum(axis=1)
        df_final["Tổng điểm (CLO tổng)"] = df_final[[c for c in df_final.columns if c.startswith("CLO")]].sum(axis=1)

        # ======= 10. Hiển thị kết quả =======
        st.success("✅ Tính điểm hoàn tất!")
        st.subheader("📊 Kết quả tổng hợp điểm CLO")
        st.dataframe(df_final)

        csv_final = df_final.to_csv(index=False).encode('utf-8-sig')
        st.download_button("💾 Tải file kết quả đầy đủ", csv_final, "ket_qua_tich_hop_full.csv", "text/csv")

        # ======= 11. Phổ điểm =======
        st.subheader("🎯 Phổ điểm sinh viên (theo tổng điểm CLO)")
        bins = [0, 5, 6, 7, 8, 9, 10]
        labels = ["Dưới 5", "Từ 5 - <6", "Từ 6 - <7", "Từ 7 - <8", "Từ 8 - <9", "Từ 9 - 10"]

        df_final["Nhóm điểm"] = pd.cut(
            df_final["Tổng điểm (CLO tổng)"], bins=bins, labels=labels,
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

        # ======= 12. Thông tin tổng điểm tối đa =======
        max_score = df3[[c for c in df3.columns if c.startswith("Điểm_")]].sum().max()
        st.info(f"🔍 Tổng điểm tối đa (nếu đúng hết): {max_score:.2f}")

    except Exception as e:
        st.error(f"❌ Lỗi khi xử lý dữ liệu: {e}")
