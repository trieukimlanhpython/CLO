#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 14 07:55:07 2025

@author: trieukimlanh
streamlit run "/Users/trieukimlanh/Library/CloudStorage/GoogleDrive-lanhtk@hub.edu.vn/My Drive/Spyder/app/app_score.py"
"""

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ============= GIAO DIỆN =============
st.set_page_config(page_title="Ứng dụng quy đổi điểm CLO", layout="wide")
st.title("🎓 Ứng dụng quy đổi điểm CLO")

st.sidebar.header("⚙️ Upload dữ liệu")
uploaded_files = st.sidebar.file_uploader(
    "📂 Tải lên các file CSV (df1.csv, df2.csv, df3.csv)",
    type=["csv"],
    accept_multiple_files=True
)

# --- Nút xử lý ---
if st.sidebar.button("▶️ Thực hiện tính điểm"):
    if not uploaded_files:
        st.error("⚠️ Vui lòng tải đủ 3 file df1, df2, df3 trước khi chạy.")
        st.stop()

    # ======= 1. Tự nhận dạng file =======
    df1_file = next((f for f in uploaded_files if "df1" in f.name.lower()), None)
    df2_file = next((f for f in uploaded_files if "df2" in f.name.lower()), None)
    df3_file = next((f for f in uploaded_files if "df3" in f.name.lower()), None)

    if not all([df1_file, df2_file, df3_file]):
        st.error("⚠️ Thiếu file! Cần có đủ df1.csv, df2.csv, df3.csv.")
        st.stop()

    try:
        # ======= 2. Đọc dữ liệu =======
        df1 = pd.read_csv(df1_file)
        df2 = pd.read_csv(df2_file)
        df3 = pd.read_csv(df3_file)

        # ======= 3. Chuẩn hóa & tự động nhận diện mã đề =======
        df3['Câu'] = df3['Câu'].astype(str).str.strip().str.replace(' ', '').str.lower()
        
        # Tự động tìm các cột mã đề
        de_cols = [c for c in df3.columns if c.lower() != 'câu']
        maps = {int(col): df3.set_index('Câu')[col].to_dict() for col in de_cols}
        
        df2.columns = [c.strip().replace(' ', '').lower() for c in df2.columns]
        for c in df2.columns:
            if c.startswith('câu'):
                df2[c] = pd.to_numeric(df2[c], errors='coerce').fillna(0)
        
        # ======= 4. Hàm tính điểm CLO cho từng mã đề =======
        def calc_clo_scores(row):
            de = int(row['đề'])
            clo_scores = {}
            for cau in [c for c in row.index if c.startswith('câu')]:
                key = cau.lower().strip()
                mapping = maps.get(de, {})  # tự động chọn theo mã đề
                clo = mapping.get(key)
                if clo:
                    clo_scores[clo] = clo_scores.get(clo, 0) + float(row[cau])
            return pd.Series(clo_scores)


        # ======= 5. Tính điểm CLO =======
        df_clo = df2.apply(calc_clo_scores, axis=1)
        df_clo.insert(0, 'MSSV', df2['mssv'])

        # ======= 6. Gộp với danh sách sinh viên =======
        df_final = pd.merge(
            df1.drop(columns=[col for col in df1.columns if 'CLO' in col], errors='ignore'),
            df_clo,
            on='MSSV',
            how='left'
        )

        # ======= 7. Thêm tổng số câu (tự động) =======
        cau_cols = [c for c in df2.columns if c.startswith('câu')]
        so_cau = len(cau_cols)
        df2['tong_cau'] = df2[cau_cols].sum(axis=1)
        df_final = pd.merge(df_final, df2[['mssv', 'tong_cau']],
                            left_on='MSSV', right_on='mssv', how='left')
        df_final = df_final.drop(columns=['mssv']).rename(columns={'tong_cau': f'Tổng ({so_cau} câu)'})

        st.success("✅ Tính điểm CLO hoàn tất!")

        # ======= 8. Hiển thị kết quả gốc =======
        st.subheader("📊 Kết quả tính điểm CLO")
        st.dataframe(df_final)

        csv_final = df_final.to_csv(index=False).encode('utf-8-sig')
        st.download_button("💾 Tải file kết quả CLO", csv_final, "ket_qua_tich_hop.csv", "text/csv")

        # ======= 9. Quy đổi điểm (1 → 0.4, giống code gốc) =======
        df1_new = df_final.copy()
        # Chỉ chọn các cột có ".CLO" trong tên (đảm bảo chỉ là cột điểm CLO)
        cols_diem = [c for c in df1_new.columns if c.startswith("C") and "CLO" in c]
    
    
        for col in cols_diem:
            df1_new[col] = df1_new[col].fillna(0) * 0.4
        df1_new["Tổng (quy đổi)"] = df1_new[cols_diem].sum(axis=1)
        
        
        st.subheader("📈 Bảng điểm quy đổi theo thang 10")
        st.dataframe(df1_new)

        csv_quydoi = df1_new.to_csv(index=False).encode('utf-8-sig')
        st.download_button("💾 Tải file điểm quy đổi", csv_quydoi, "ket_qua_tich_hop_quydoi.csv", "text/csv")

        # ======= 6. Kiểm tra chênh lệch (nếu có) =======
        compare = pd.merge(
            df2[['mssv', 'tong_cau']],
            df_final[['MSSV', f'Tổng ({so_cau} câu)']],
            left_on='mssv', right_on='MSSV', how='left'
        )
        compare['chenhlech'] = compare[f'Tổng ({so_cau} câu)'] - compare['tong_cau']
        errors = compare[compare['chenhlech'].abs() > 1e-6]
        
        if not errors.empty:
            st.error("⚠️ Có **chênh lệch tổng điểm** ở các sinh viên sau (không khớp giữa dữ liệu gốc và bảng kết quả):")
            st.dataframe(errors)
        else:
            st.success(f"✅ Kiểm tra thành công: Tổng điểm {so_cau} câu khớp hoàn toàn!")


        # ======= 10. Phổ điểm sinh viên =======
        st.subheader("🎯 Phổ điểm sinh viên (thang 10)")

        bins = [0, 5, 6, 7, 8, 9, 10]
        labels = ["Dưới 5", "Từ 5 - <6", "Từ 6 - <7", "Từ 7 - <8", "Từ 8 - <9", "Từ 9 - 10"]

        df1_new["Nhóm điểm"] = pd.cut(
            df1_new["Tổng (quy đổi)"], bins=bins, labels=labels,
            right=False, include_lowest=True
        )
        score_dist = df1_new["Nhóm điểm"].value_counts().reindex(labels, fill_value=0)

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

    except Exception as e:
        st.error(f"❌ Lỗi khi xử lý dữ liệu: {e}")
