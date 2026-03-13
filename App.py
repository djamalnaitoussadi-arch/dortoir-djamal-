import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import matplotlib.pyplot as plt
from fpdf import FPDF

# --- إعدادات الحماية ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

# --- إعداد قاعدة البيانات المتقدمة ---
def init_db():
    conn = sqlite3.connect('djamal_pro_final.db', check_same_thread=False)
    c = conn.cursor()
    # جداول النظام
    c.execute('CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY, status TEXT, guest_name TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS bookings 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, guest_name TEXT, id_card TEXT, 
                  phone TEXT, check_in TEXT, total_price REAL, paid REAL, status TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS blacklist (name TEXT PRIMARY KEY, reason TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finance (id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, amount REAL, type TEXT, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    
    # ملء البيانات الأولية
    c.execute("SELECT count(*) FROM rooms")
    if c.fetchone()[0] == 0:
        for i in range(1, 24): c.execute("INSERT INTO rooms VALUES (?, 'شاغرة', '')", (i,))
        c.execute("INSERT INTO users VALUES ('admin', ?)", (make_hashes('admin2026'),))
    conn.commit()
    return conn

conn = init_db()

# --- واجهة تسجيل الدخول ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🇩🇿 نظام Dortoir Djamal الاحترافي")
    u = st.text_input("اسم المستخدم")
    p = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username=?", (u,))
        res = cur.fetchone()
        if res and check_hashes(p, res[0]):
            st.session_state.logged_in = True
            st.rerun()
        else: st.error("بيانات الدخول غير صحيحة")

else:
    st.sidebar.title("لوحة التحكم")
    menu = ["🏨 الاستقبال والأمن", "💳 الديون والقائمة السوداء", "📈 الإحصائيات والمالية", "📞 حجز هاتفي"]
    choice = st.sidebar.selectbox("اختر القسم", menu)
    
    if st.sidebar.button("تسجيل الخروج"):
        st.session_state.logged_in = False
        st.rerun()

    # --- القسم 1: الاستقبال والأمن ---
    if choice == "🏨 الاستقبال والأمن":
        st.header("تسجيل الزبائن (Fiche Police)")
        tab1, tab2 = st.tabs(["📥 دخول (Check-in)", "📤 خروج (Check-out)"])
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                r_id = st.selectbox("اختر غرفة", [r[0] for r in conn.execute("SELECT id FROM rooms WHERE status='شاغرة'").fetchall()])
                g_name = st.text_input("اسم الزبون الكامل")
                g_id = st.text_input("رقم بطاقة التعريف / الجواز")
            with col2:
                g_phone = st.text_input("رقم الهاتف")
                price = st.number_input("السعر المتفق عليه (DZD)", value=4000)
            
            if st.button("تأكيد الحجز والأمن"):
                # فحص القائمة السوداء
                black = conn.execute("SELECT reason FROM blacklist WHERE name=?", (g_name,)).fetchone()
                if black:
                    st.error(f"⚠️ تحذير: هذا الزبون ممنوع! السبب: {black[0]}")
                else:
                    cur = conn.cursor()
                    cur.execute("UPDATE rooms SET status='محجوزة', guest_name=? WHERE id=?", (g_name, r_id))
                    cur.execute("INSERT INTO bookings (guest_name, id_card, phone, check_in, total_price, paid, status) VALUES (?,?,?,?,?,?,?)",
                               (g_name, g_id, g_phone, datetime.now().strftime("%Y-%m-%d"), price, 0, 'نشط'))
                    conn.commit()
                    st.success(f"تم تسكين {g_name} في الغرفة {r_id}")
                    st.rerun()

        with tab2:
            occ_rooms = pd.read_sql_query("SELECT id, guest_name FROM rooms WHERE status='محجوزة'", conn)
            if not occ_rooms.empty:
                r_out = st.selectbox("غرفة المغادرة", occ_rooms['id'])
                amount_paid = st.number_input("المبلغ المدفوع الآن (DZD)", min_value=0)
                if st.button("إتمام الخروج وتوليد الفاتورة"):
                    cur = conn.cursor()
                    cur.execute("SELECT guest_name FROM rooms WHERE id=?", (r_out,))
                    name = cur.fetchone()[0]
                    # تحديث المبدأ المالي
                    cur.execute("UPDATE bookings SET paid=?, status='منتهي' WHERE guest_name=? AND status='نشط'", (amount_paid, name))
                    cur.execute("UPDATE rooms SET status='شاغرة', guest_name='' WHERE id=?", (r_out,))
                    # تسجيل في المالية
                    tva = amount_paid * 0.19
                    cur.execute("INSERT INTO finance (desc, amount, type, date) VALUES (?,?,?,?)", 
                               (f"حجز {name}", amount_paid, "Revenue", datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.balloons()
                    st.success("تم الخروج بنجاح!")
                    st.rerun()

    # --- القسم 2: الديون والقائمة السوداء ---
    elif choice == "💳 الديون والقائمة السوداء":
        st.header("إدارة الديون والممنوعين")
        col_d, col_b = st.columns(2)
        
        with col_d:
            st.subheader("💰 سجل الديون")
            # الدين = السعر الكلي - المدفوع
            debts = pd.read_sql_query("SELECT guest_name, phone, (total_price - paid) as debt FROM bookings WHERE debt > 0", conn)
            st.dataframe(debts)
            
        with col_b:
            st.subheader("🌑 إضافة للقائمة السوداء")
            b_name = st.text_input("اسم الشخص الممنوع")
            reason = st.text_area("السبب (مشاكل، عدم دفع، الخ)")
            if st.button("حظر الشخص"):
                conn.execute("INSERT OR REPLACE INTO blacklist VALUES (?,?)", (b_name, reason))
                conn.commit()
                st.warning("تمت إضافة الشخص للقائمة السوداء")

    # --- القسم 3: الإحصائيات ---
    elif choice == "📈 الإحصائيات والمالية":
        st.header("التقرير المالي العام")
        df_f = pd.read_sql_query("SELECT * FROM finance", conn)
        if not df_f.empty:
            total = df_f['amount'].sum()
            st.metric("إجمالي المداخيل (DZD)", f"{total:,.2f}")
            
            # رسم بياني بسيط
            fig, ax = plt.subplots()
            df_f.groupby('date')['amount'].sum().plot(kind='line', ax=ax)
            st.pyplot(fig)
        else:
            st.info("لا توجد بيانات مالية بعد")

    # --- القسم 4: حجز هاتفي ---
    elif choice == "📞 حجز هاتفي":
        st.header("سجل الحجوزات الهاتفية")
        h_name = st.text_input("اسم المتصل")
        h_date = st.date_input("تاريخ القدوم المتوقع")
        if st.button("تسجيل الحجز المؤقت"):
            st.info(f"تم تسجيل حجز مؤقت لـ {h_name} بتاريخ {h_date}")
            # يمكن تطوير هذا القسم لاحقاً لربطه بجدول خاص
