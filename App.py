import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- 1. الحماية ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

# --- 2. قاعدة البيانات (تحديث الجداول لتشمل التفاصيل الأمنية) ---
def init_db():
    conn = sqlite3.connect('djamal_final_v7.db', check_same_thread=False)
    c = conn.cursor()
    # إضافة حالة 'phone' للغرف
    c.execute('CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY, status TEXT, guest_name TEXT)')
    # جدول أمني كامل
    c.execute('''CREATE TABLE IF NOT EXISTS security_records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, full_name TEXT, 
                  birth_date TEXT, birth_place TEXT, job TEXT, address TEXT, 
                  nationality TEXT, doc_num TEXT, doc_issue_date TEXT, 
                  issuer_auth TEXT, doc_expiry TEXT, phone TEXT, status TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS finance (id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, amount REAL, tva REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    
    c.execute("SELECT count(*) FROM rooms")
    if c.fetchone()[0] == 0:
        for i in range(1, 24): c.execute("INSERT INTO rooms VALUES (?, 'شاغرة', '')", (i,))
        c.execute("INSERT INTO users VALUES ('admin', ?, 'مدير')", (make_hashes('admin2026'),))
    conn.commit()
    return conn

conn = init_db()

# --- 3. الواجهة ---
st.set_page_config(page_title="Dortoir Djamal Pro", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🇩🇿 Dortoir Djamal - الأمن والحجوزات")
    u = st.text_input("اسم المستخدم")
    p = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        res = conn.execute("SELECT password, role FROM users WHERE username=?", (u,)).fetchone()
        if res and check_hashes(p, res[0]):
            st.session_state.auth, st.session_state.role = True, res[1]
            st.rerun()
else:
    menu = ["🏨 الاستقبال والأمن", "📞 حجز هاتفي", "📊 المالية"]
    choice = st.sidebar.selectbox("القائمة", menu)

    # --- عرض الغرف (نظام الألوان الثلاثي) ---
    rooms_df = pd.read_sql_query("SELECT * FROM rooms", conn)
    cols = st.columns(8) # عرض واسع
    for i, r in rooms_df.iterrows():
        # تحديد اللون بناءً على الحالة
        bg_color = "#27ae60" # أخضر (شاغرة)
        if r['status'] == 'محجوزة': bg_color = "#c0392b" # أحمر (حجز فعلي)
        elif r['status'] == 'هاتفي': bg_color = "#2980b9" # أزرق (حجز هاتفي)
        
        cols[i%8].markdown(f"<div style='background:{bg_color}; color:white; padding:10px; border-radius:8px; text-align:center; margin-bottom:5px; font-weight:bold;'>غرفة {r['id']}<br><small>{r['status']}</small></div>", unsafe_allow_html=True)

    st.divider()

    if choice == "🏨 الاستقبال والأمن":
        st.subheader("📝 تسجيل معلومات الزبون الكاملة (Fiche Police)")
        with st.form("security_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                r_id = st.selectbox("رقم الغرفة", rooms_df[rooms_df['status']!='محجوزة']['id'])
                f_name = st.text_input("الاسم واللقب")
                b_date = st.date_input("تاريخ الميلاد")
                b_place = st.text_input("مكان الميلاد")
            with col2:
                job = st.text_input("المهنة")
                addr = st.text_input("العنوان الحالي")
                nat = st.text_input("الجنسية", value="جزائرية")
                doc_id = st.text_input("رقم الوثيقة (بطاقة/جواز)")
            with col3:
                iss_date = st.date_input("تاريخ الإصدار")
                iss_auth = st.text_input("السلطة المصدرة (مثلاً: دائرة...)")
                exp_date = st.date_input("تاريخ نهاية الصلاحية")
                phone = st.text_input("رقم الهاتف")
            
            if st.form_submit_button("تأكيد الحجز الفعلي وتسجيل البيانات"):
                cur = conn.cursor()
                cur.execute("UPDATE rooms SET status='محجوزة', guest_name=? WHERE id=?", (f_name, r_id))
                cur.execute('''INSERT INTO security_records (room_id, full_name, birth_date, birth_place, job, address, nationality, doc_num, doc_issue_date, issuer_auth, doc_expiry, phone, status) 
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                            (r_id, f_name, str(b_date), b_place, job, addr, nat, doc_id, str(iss_date), iss_auth, str(exp_date), phone, 'نشط'))
                conn.commit()
                st.success("تم تسجيل الزبون بنجاح وتغيير لون الغرفة للأحمر")
                st.rerun()

    elif choice == "📞 حجز هاتفي":
        st.subheader("📞 تسجيل حجز هاتفي مؤقت")
        with st.form("phone_form"):
            r_id_p = st.selectbox("رقم الغرفة", rooms_df[rooms_df['status']=='شاغرة']['id'])
            p_name = st.text_input("اسم ولقب الزبون (عبر الهاتف)")
            p_num = st.text_input("رقم هاتف الزبون")
            if st.form_submit_button("تأكيد الحجز الهاتفي"):
                cur = conn.cursor()
                cur.execute("UPDATE rooms SET status='هاتفي', guest_name=? WHERE id=?", (p_name, r_id_p))
                conn.commit()
                st.info(f"تم الحجز الهاتفي لـ {p_name}. الغرفة الآن باللون الأزرق.")
                st.rerun()

    elif choice == "📊 المالية":
        if st.session_state.role == 'مدير':
            st.subheader("السجل الأمني والمالي")
            st.write("بيانات الزبائن المسجلة:")
            st.dataframe(pd.read_sql_query("SELECT * FROM security_records", conn))
        else: st.error("خاص بالمدير")

