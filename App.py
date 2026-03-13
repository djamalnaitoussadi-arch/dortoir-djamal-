import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- الحماية ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('hotel_pro_dz_v2.db', check_same_thread=False)
    c = conn.cursor()
    # الغرف (1-23)
    c.execute('''CREATE TABLE IF NOT EXISTS rooms 
                 (id INTEGER PRIMARY KEY, floor TEXT, status TEXT, guest_name TEXT, check_in_date TEXT)''')
    # العمال (10 عمال)
    c.execute('''CREATE TABLE IF NOT EXISTS staff 
                 (id INTEGER PRIMARY KEY, name TEXT, salary_brut REAL, cnas REAL)''')
    # المالية (فواتير وحجز)
    c.execute('''CREATE TABLE IF NOT EXISTS finance 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, amount REAL, tva REAL, type TEXT, date TEXT)''')
    # المستخدمين (5 حسابات)
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    
    # ملء البيانات الأولية
    c.execute("SELECT count(*) FROM rooms")
    if c.fetchone()[0] == 0:
        for i in range(1, 24):
            f = "الأول" if i<=6 else "الثاني" if i<=12 else "الثالث" if i<=18 else "الرابع"
            c.execute("INSERT INTO rooms VALUES (?, ?, ?, ?, ?)", (i, f, "شاغرة", "", ""))
        
        for i in range(1, 11):
            c.execute("INSERT INTO staff VALUES (?, ?, ?, ?)", (i, f"موظف {i}", 42000.0, 42000.0*0.09))
            
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ('admin', make_hashes('admin2026'), 'مدير'))
        for i in range(1, 5):
            c.execute("INSERT INTO users VALUES (?, ?, ?)", (f'reception{i}', make_hashes(f'pass{i}'), 'استقبال'))
            
    conn.commit()
    return conn

conn = init_db()

# --- واجهة تسجيل الدخول ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🇩🇿 نظام إدارة الفندق - الجزائر")
    u = st.text_input("اسم المستخدم")
    p = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        cur = conn.cursor()
        cur.execute("SELECT password, role FROM users WHERE username=?", (u,))
        res = cur.fetchone()
        if res and check_hashes(p, res[0]):
            st.session_state.logged_in = True
            st.session_state.user = u
            st.session_state.role = res[1]
            st.rerun()
        else: st.error("بيانات خاطئة")

# --- النظام بعد الدخول ---
else:
    st.sidebar.write(f"المستخدم: {st.session_state.user}")
    if st.sidebar.button("خروج"):
        st.session_state.logged_in = False
        st.rerun()

    menu = ["🏨 الاستقبال (Check-in/Out)", "💰 الحسابات والضرائب", "👥 العمال والمصاريف"]
    choice = st.sidebar.selectbox("القائمة الرئيسي", menu)

    if choice == "🏨 الاستقبال (Check-in/Out)":
        st.header("تسيير الغرف (1-23)")
        rooms_df = pd.read_sql_query("SELECT * FROM rooms", conn)
        
        # عرض حالة الغرف بصرياً
        cols = st.columns(6)
        for i, r in rooms_df.iterrows():
            color = "#27ae60" if r['status'] == "شاغرة" else "#c0392b"
            cols[i%6].markdown(f"<div style='background:{color}; color:white; padding:10px; border-radius:5px; text-align:center; margin-bottom:10px;'>{r['id']}<br>{r['status']}</div>", unsafe_allow_html=True)

        st.divider()
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("📥 تسجيل دخول (Check-in)")
            room_id = st.selectbox("اختر غرفة شاغرة", rooms_df[rooms_df['status']=="شاغرة"]['id'])
            guest = st.text_input("اسم الزبون")
            if st.button("تأكيد الدخول"):
                cur = conn.cursor()
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                cur.execute("UPDATE rooms SET status='محجوزة', guest_name=?, check_in_date=? WHERE id=?", (guest, now, room_id))
                conn.commit()
                st.success(f"تم تسكين {guest} في غرفة {room_id}")
                st.rerun()

        with col_b:
            st.subheader("📤 تسجيل خروج (Check-out)")
            room_out = st.selectbox("اختر غرفة للمغادرة", rooms_df[rooms_df['status']=="محجوزة"]['id'])
            price_per_night = st.number_input("سعر الليلة (DZD)", value=5000)
            if st.button("حساب الفاتورة والمغادرة"):
                cur = conn.cursor()
                # جلب بيانات الدخول
                cur.execute("SELECT check_in_date, guest_name FROM rooms WHERE id=?", (room_out,))
                data = cur.fetchone()
                
                # حساب المكوث (تبسيطاً سنعتبرها ليلة واحدة أو يمكن حساب الفرق بين التواريخ)
                total = price_per_night # هنا يمكن تطوير معادلة حساب الأيام
                tva = total * 0.19
                
                # تسجيل المالية
                cur.execute("INSERT INTO finance (desc, amount, tva, type, date) VALUES (?,?,?,?,?)",
                           (f"حجز زبون: {data[1]}", total, tva, "Revenue", datetime.now().strftime("%Y-%m-%d")))
                # تفريغ الغرفة
                cur.execute("UPDATE rooms SET status='شاغرة', guest_name='', check_in_date='' WHERE id=?", (room_out,))
                conn.commit()
                st.info(f"الفاتورة: الصافي {total} DZD + ضريبة {tva} DZD")
                st.success("تم تسجيل الخروج وتفريغ الغرفة")
                st.rerun()

    elif choice == "💰 الحسابات والضرائب":
        st.header("📊 السجل المالي والضرائب (19%)")
        df_fin = pd.read_sql_query("SELECT * FROM finance", conn)
        t_rev = df_fin['amount'].sum()
        t_tva = df_fin['tva'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("إجمالي المداخيل", f"{t_rev:,.2f} DZD")
        c2.metric("إجمالي الضرائب المستحقة (TVA)", f"{t_tva:,.2f} DZD")
        st.dataframe(df_fin, use_container_width=True)

    elif choice == "👥 العمال والمصاريف":
        st.header("الموظفون وفواتير سونلغاز")
        tab1, tab2 = st.tabs(["العمال (10)", "المصاريف"])
        
        with tab1:
            df_s = pd.read_sql_query("SELECT * FROM staff", conn)
            st.table(df_s)
            
        with tab2:
            m_type = st.selectbox("نوع المصروف", ["سونلغاز (كهرباء/غاز)", "لوازم", "صيانة"])
            m_val = st.number_input("المبلغ", min_value=0)
            if st.button("تسجيل"):
                cur = conn.cursor()
                cur.execute("INSERT INTO finance (desc, amount, tva, type, date) VALUES (?,?,?,?,?)",
                           (m_type, m_val, 0, "Expense", datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.rerun()