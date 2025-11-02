"""
Created on Thu Oct 17 2025
@author: trieukimlanh

🎓 Ứng dụng tính điểm CLO_30 (mã đề trắc nghiệm linh hoạt, 30 câu), môn TT-NH-Fintech
"""

import re
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import unidecode

# ====================== GIAO DIỆN ======================
st.set_page_config(page_title="🎓 Ứng dụng tính điểm CLO_30", layout="wide")
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

        # ======= 3. Chuẩn hóa & phát hiện cột =======
        # chuẩn hóa 'Câu' trong df3 để khớp với tên cột df2
        def normalize_question_name(s):
            s = str(s)
            s = unidecode.unidecode(s)
            s = s.strip().replace(' ', '').lower()
            s = re.sub(r'cau0+(\d+)', r'cau\1', s)   # cau01 -> cau1
            s = re.sub(r'[^a-z0-9]', '', s)         # loại ký tự lạ
            return s

        df3['Câu'] = df3['Câu'].astype(str).apply(normalize_question_name)

        # Tự phát hiện cột "đáp án" trong df3 (các cột chứa "đáp" hoặc "dap")
        ans_cols = [c for c in df3.columns if re.search(r'đáp|dap|dapan', c, re.IGNORECASE)]
        # Các cột mã đề là phần còn lại (ngoại trừ 'Câu' và ans_cols)
        de_cols = [c for c in df3.columns if c not in ['Câu'] + ans_cols]
        if len(de_cols) == 0:
            st.error("Không tìm thấy cột mã đề trong df3. Kiểm tra lại df3 (cột mã CLO/đề).")
            st.stop()

        # Chuẩn hóa nội dung cột mã đề (giá trị là mã CLO)
        for de in de_cols:
            df3[de] = df3[de].astype(str).str.strip().str.upper().replace({'NAN': '', 'nan': ''})

        # Chuẩn hóa cột đáp án (nếu có) -> uppercase, no-space
        for c in ans_cols:
            df3[c] = df3[c].astype(str).str.strip().str.upper()

        # ===== chuẩn hóa df4 (CLO -> Điểm) =====
        df4['CLO'] = df4['CLO'].astype(str).str.strip().str.upper()
        df4['Điểm'] = pd.to_numeric(df4['Điểm'], errors='coerce').fillna(0)
        clo_point_map = df4.set_index('CLO')['Điểm'].to_dict()

        # Tạo cột Điểm_<de> trong df3 bằng map từ df4
        for de in de_cols:
            df3[f"Điểm_{de}"] = df3[de].map(clo_point_map).fillna(0)

        # ===== chuẩn hóa df2 (tên cột và giá trị) =====
        def normalize_df2_col(s):
            s = str(s)
            s = unidecode.unidecode(s)
            s = s.strip().replace(' ', '').lower()
            s = re.sub(r'cau0+(\d+)', r'cau\1', s)
            s = re.sub(r'[^a-z0-9]', '', s)
            return s

        orig_df2_cols = list(df2.columns)
        df2_col_map = {c: normalize_df2_col(c) for c in orig_df2_cols}
        # rename temporarily
        df2.rename(columns=df2_col_map, inplace=True)

        # tìm cột chứa mã đề trong df2 (tên như 'de' hoặc 'đề' hoặc 'ma de')
        de_col_candidates = [c for c in df2.columns if re.search(r'\bde\b|\bdê\b|ma?de|code', c, re.IGNORECASE)]
        if not de_col_candidates:
            # cố fallback: cột có tên 'đề' sau bỏ dấu?
            possible = [c for c in df2.columns if 'de' == c or c.startswith('de')]
            de_col = possible[0] if possible else None
        else:
            de_col = de_col_candidates[0]

        if de_col is None:
            # thử tìm cột có tên 'mssv' để chắc chắn df2 structure
            st.error("Không tìm thấy cột mã đề trong df2 (ví dụ 'de' hoặc 'đề').")
            st.stop()

        # Chuẩn hóa tất cả giá trị câu trong df2 thành uppercase chữ cái (A/B/C/D)
        df2_cols_questions = [c for c in df2.columns if c.startswith('cau')]
        for c in df2_cols_questions:
            df2[c] = df2[c].astype(str).str.strip().str.upper()

        # ======= 4. Tạo mapping giữu 'Câu' (df3) và cột df2 =======
        df2_question_cols = df2_cols_questions
        df3_question_keys = df3['Câu'].unique().tolist()

        # build mapping cau_key -> df2_col (nhiều chiến lược)
        cau_match_map = {}
        for k in df3_question_keys:
            # direct
            if k in df2_question_cols:
                cau_match_map[k] = k
                continue
            # try numeric suffix
            m = re.search(r'(\d+)$', k)
            mapped = None
            if m:
                num = m.group(1).lstrip('0')
                for c in df2_question_cols:
                    mc = re.search(r'(\d+)$', c)
                    if mc and mc.group(1).lstrip('0') == num:
                        mapped = c
                        break
            # fallback: try contains num
            if not mapped:
                for c in df2_question_cols:
                    if k in c or c in k:
                        mapped = c
                        break
            cau_match_map[k] = mapped

        unmatched = [k for k, v in cau_match_map.items() if v is None]
        if unmatched:
            st.warning(f"⚠️ Một số 'Câu' trong df3 không khớp với cột câu df2 và sẽ bị bỏ qua: {unmatched[:10]}")

        # ======= 5. Hàm chấm điểm linh hoạt (dùng de_col) =======
        def calc_clo_scores(row):
            clo_scores = {}
            de_val = row.get(de_col, None)
            if pd.isna(de_val):
                return pd.Series(clo_scores)
            # chuẩn hoá kiểu mã đề thành chuỗi giống tên cột df3
            try:
                de_code = str(int(float(de_val)))  # 134.0 -> '134'
            except Exception:
                de_code = str(de_val).strip()
            # tìm tên cột đáp án trong df3 cho de_code: ưu tiên exact 'Đáp án_<de_code>' hoặc chứa de_code
            answer_col = None
            for ac in ans_cols:
                if re.search(re.escape(de_code), ac):
                    answer_col = ac
                    break
            if not answer_col:
                # try 'Đáp án' without code if single answer column exists
                if len(ans_cols) == 1:
                    answer_col = ans_cols[0]

            if not answer_col:
                # không có cột đáp án cho đề này — bỏ qua
                return pd.Series(clo_scores)

            de_col_in_df3 = None
            for cand in de_cols:
                if re.search(re.escape(str(cand)), str(cand)) and str(cand).strip():
                    # cand is itself; we just check membership of de_code in column name OR use columns as is
                    pass
            # choose the de column that corresponds to this de_code: usually column name equals de_code or contains it
            for cand in de_cols:
                if str(cand).strip() == de_code or re.search(re.escape(de_code), str(cand)):
                    de_col_in_df3 = cand
                    break
            if de_col_in_df3 is None:
                # fallback: if only one de_col in df3, use it
                if len(de_cols) == 1:
                    de_col_in_df3 = de_cols[0]
                else:
                    # try numeric match on column names
                    for cand in de_cols:
                        m = re.search(r'(\d+)', str(cand))
                        if m and m.group(1) == de_code:
                            de_col_in_df3 = cand
                            break
            if de_col_in_df3 is None:
                # không thể xác định cột mã đề trong df3 cho de này
                return pd.Series(clo_scores)

            # build point column name
            point_col = f"Điểm_{de_col_in_df3}" if f"Điểm_{de_col_in_df3}" in df3.columns else None

            # iterate rows in df3 and compare
            for _, q in df3.iterrows():
                cau_key = q['Câu']
                df2_col = cau_match_map.get(cau_key)
                if not df2_col:
                    continue
                pa_sv = str(row.get(df2_col, '')).strip().upper()
                dap_an = str(q.get(answer_col, '')).strip().upper()
                clo_code = str(q.get(de_col_in_df3, '')).strip().upper()
                diem = float(q.get(point_col, 0)) if point_col else 0.0

                if dap_an and pa_sv == dap_an and clo_code:
                    clo_scores[clo_code] = clo_scores.get(clo_code, 0) + diem

            return pd.Series(clo_scores)

        # ======= 6. Tính điểm cho toàn bộ sinh viên =======
        df_clo = df2.apply(calc_clo_scores, axis=1)
        # restore MSSV original column name in df2 to insert as MSSV
        # find original MSSV col (before rename we kept orig names)
        mssv_col = next((c for c in df2.columns if 'mssv' in c.lower()), None)
        if mssv_col is None:
            # try common names
            mssv_col = next((c for c in df2.columns if c in ['mssv','id','studentid']), None)
        if mssv_col is None:
            st.error("Không tìm thấy cột MSSV trong df2.")
            st.stop()
        df_clo.insert(0, 'MSSV', df2[mssv_col])

        # ======= 7. Gộp vào df1 (loại bỏ cột CLO cũ để tránh _x/_y) =======
        df1_clean = df1.loc[:, ~df1.columns.str.contains('CLO|Tong|Tổng', case=False, regex=True)].copy()
        df_final = pd.merge(df1_clean, df_clo, on='MSSV', how='left').fillna(0)

        # ======= 8. Tính tổng điểm tổng hợp =======
        clo_columns = [c for c in df_final.columns if re.search(r'clo', str(c), re.IGNORECASE)]
        df_final["Tổng điểm"] = df_final[clo_columns].sum(axis=1) if clo_columns else 0

        # ======= 9. Tổng hợp theo CLO1..CLO5 (tự động) =======
        # phát hiện các nhóm CLO chính (CLO1, CLO2, ...)
        main_clo_names = sorted({re.search(r'(CLO\d+)', c, re.IGNORECASE).group(1).upper()
                                 for c in clo_columns
                                 if re.search(r'(CLO\d+)', c, re.IGNORECASE)} ) if clo_columns else []
        for mc in main_clo_names:
            df_final[mc] = df_final[[c for c in df_final.columns if mc in c]].sum(axis=1)

        # tổng các main CLO
        if main_clo_names:
            df_final["Tổng điểm (CLO tổng)"] = df_final[main_clo_names].sum(axis=1)
        else:
            df_final["Tổng điểm (CLO tổng)"] = df_final["Tổng điểm"]

        # ======= 10. Hiển thị & tải kết quả =======
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
            ax.bar(score_dist.index, score_dist.values, edgecolor='black')
            ax.set_title("Phổ điểm sinh viên")
            ax.set_xlabel("Khoảng điểm")
            ax.set_ylabel("Số sinh viên")
            for i, v in enumerate(score_dist.values):
                ax.text(i, v + 0.2, str(v), ha='center')
            st.pyplot(fig)

        # ======= 12. Thông tin tổng điểm tối đa =======
        max_score = df3[[c for c in df3.columns if c.startswith("Điểm_")]].sum().max() if any(c.startswith("Điểm_") for c in df3.columns) else 0
        st.info(f"🔍 Tổng điểm tối đa (nếu đúng hết): {max_score:.2f}")

    except Exception as e:
        st.error(f"❌ Lỗi khi xử lý dữ liệu: {e}")
