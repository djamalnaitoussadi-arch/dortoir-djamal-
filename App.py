import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- 1. وظائف الأمان ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

# --- 2. قاعدة البيانات (إضافة جداول العمال والمشتريات) ---
def init_db():
    conn = sqlite3.connect('djamal_enterprise_v9.db', check_same_thread=False)
    c = conn.cursor()
    # الغرف والأمن
    c.execute('CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY, status TEXT, guest_name TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS security_records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, full_name TEXT, 
                  phone TEXT, check_in_time TEXT, total_price REAL)''')
    # المشتريات والمصاريف
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, category TEXT, amount REAL, date TEXT)')
    # العمال
    c.execute('CREATE TABLE IF NOT EXISTS staff (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, position TEXT, salary REAL)')
    # المالية العامة
    c.execute('CREATE TABLE IF NOT EXISTS finance (id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, amount REAL, tva REAL, type TEXT, date TEXT)')
    # المستخدمين
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    
    c.execute("SELECT count(*) FROM rooms")
    if c.fetchone()[0] == 0:
        for i in range(1, 24): c.execute("INSERT INTO rooms VALUES (?, 'شاغرة', '')", (i,))
        c.execute("INSERT INTO users VALUES ('admin', ?, 'مدير')", (make_hashes('admin2026'),))
        # إضافة عمال وهميين كبداية (يمكنك تعديلهم)
        c.execute("INSERT INTO staff (name, position, salary) VALUES ('عامل 1', 'استقبال', 40000)")
    conn.commit()
    return conn

conn = init_db()

# --- 3. تصميم الواجهة ---
st.set_page_config(page_title="Dortoir Djamal Enterprise", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🏨 Dortoir Djamal - نظام الإدارة الشامل")
    u = st.text_input("اسم المستخدم")
    p = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        res = conn.execute("SELECT password, role FROM users WHERE username=?", (u,)).fetchone()
        if res and check_hashes(p, res[0]):
            st.session_state.auth, st.session_state.role = True, res[1]
            st.rerun()
else:
    # عرض حالة الغرف (الأساسيات)
    rooms_df = pd.read_sql_query("SELECT * FROM rooms", conn)
    cols = st.columns(8)
    for i, r in rooms_df.iterrows():
        color = "#27ae60" if r['status'] == 'شاغرة' else "#c0392b" if r['status'] == 'محجوزة' else "#2980b9"
        cols[i%8].markdown(f"<div style='background:{color}; color:white; padding:10px; border-radius:8px; text-align:center; margin-bottom:5px; font-weight:bold; font-size:14px;'>غرفة {r['id']}</div>", unsafe_allow_html=True)

    st.sidebar.title("القائمة الرئيسية")
    menu = ["🏨 الاستقبال والأمن", "📞 حجز هاتفي", "🛒 المشتريات والمصاريف", "👥 إدارة العمال", "📊 الحسابات الشهرية"]
    choice = st.sidebar.selectbox("اختر القسم", menu)

    # --- القسم 1 و 2 (الاستقبال والحجز الهاتفي) - بقيا كما هما لضمان استقرار الكود ---
    if choice == "🏨 الاستقبال والأمن":
        st.subheader("📝 تسجيل دخول فعلي")
        # (نفس كود الاستمارة السابق الخاص بالـ Fiche Police)
        with st.form("checkin_form"):
            r_id = st.selectbox("الغرفة", rooms_df[rooms_df['status']!='محجوزة']['id'])
            name = st.text_input("الاسم واللقب")
            price = st.number_input("السعر", value=4000)
            if st.form_submit_button("تأكيد"):
                conn.execute("UPDATE rooms SET status='محجوزة', guest_name=? WHERE id=?", (name, r_id))
                conn.execute("INSERT INTO finance (desc, amount, tva, type, date) VALUES (?,?,?,?,?)", (f"حجز غرفة {r_id}", price, price*0.19, "مدخول", datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.rerun()

    # --- القسم 3: المشتريات والمصاريف (جديد) ---
    elif choice == "🛒 المشتريات والمصاريف":
        st.subheader("🛍️ سجل المشتريات والمصاريف (سونلغاز، لوازم...)")
        with st.form("exp_form"):
            item = st.text_input("ماذا اشتريت؟ (الوصف)")
            cat = st.selectbox("الصنف", ["فواتير (كهرباء/ماء)", "مشتريات (لوازم نظافة...)", "صيانة", "أخرى"])
            amt = st.number_input("المبلغ (DZD)", min_value=0)
            if st.form_submit_button("تسجيل المصروف"):
                conn.execute("INSERT INTO expenses (item_name, category, amount, date) VALUES (?,?,?,?)", (item, cat, amt, datetime.now().strftime("%Y-%m-%d")))
                conn.execute("INSERT INTO finance (desc, amount, tva, type, date) VALUES (?,?,?,?,?)", (f"مصروف: {item}", amt, 0, "مصروف", datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success("تم تسجيل المصروف")

    # --- القسم 4: إدارة العمال (جديد) ---
    elif choice == "👥 إدارة العمال":
        st.subheader("👥 سجل الموظفين والرواتب")
        with st.expander("إضافة موظف جديد"):
            new_name = st.text_input("اسم الموظف")
            new_pos = st.text_input("الوظيفة")
            new_sal = st.number_input("الراتب الشهري", min_value=0)
            if st.button("حفظ الموظف"):
                conn.execute("INSERT INTO staff (name, position, salary) VALUES (?,?,?)", (new_name, new_pos, new_sal))
                conn.commit()
        
        staff_df = pd.read_sql_query("SELECT * FROM staff", conn)
        st.table(staff_df)

    # --- القسم 5: الحسابات الشهرية (جديد ومعالج) ---
    elif choice == "📊 الحسابات الشهرية":
        st.subheader("📈 ميزانية الفندق الشهرية")
        month = datetime.now().strftime("%Y-%m")
        st.write(f"إحصائيات شهر: {month}")
        
        income = pd.read_sql_query(f"SELECT SUM(amount) FROM finance WHERE type='مدخول' AND date LIKE '{month}%'", conn).iloc[0,0] or 0
        exp_items = pd.read_sql_query(f"SELECT SUM(amount) FROM finance WHERE type='مصروف' AND date LIKE '{month}%'", conn).iloc[0,0] or 0
        staff_salaries = pd.read_sql_query("SELECT SUM(salary) FROM staff", conn).iloc[0,0] or 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي المداخيل", f"{income:,.2f} DZD")
        c2.metric("المصاريف + الرواتب", f"{(exp_items + staff_salaries):,.2f} DZD")
        
        net_profit = income - (exp_items + staff_salaries)
        c3.metric("الربح الصافي", f"{net_profit:,.2f} DZD", delta=float(net_profit))
        
        st.divider()
        st.write("تفاصيل فواتير الشهر:")
        st.dataframe(pd.read_sql_query(f"SELECT * FROM finance WHERE date LIKE '{month}%'", conn))

