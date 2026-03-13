import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
from fpdf import FPDF

# --- 1. الإعدادات وقاعدة البيانات ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def init_db():
    conn = sqlite3.connect('djamal_final_system_2026.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY, status_code INTEGER, guest_name TEXT)')
    # السجل الكامل (الأرشيف)
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, name TEXT, 
                 birth_date TEXT, birth_place TEXT, job TEXT, address TEXT, doc_type TEXT, 
                 doc_num TEXT, issuer TEXT, phone TEXT, stay_days INTEGER, 
                 total_price REAL, paid_amount REAL, date TEXT, worker TEXT, doc_image BLOB)''')
    c.execute('CREATE TABLE IF NOT EXISTS staff (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, role TEXT, salary_rate REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, login_time TEXT, 
                 logout_time TEXT, date TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, amount REAL, date TEXT, category TEXT)')
    
    if conn.execute("SELECT count(*) FROM rooms").fetchone()[0] == 0:
        for i in range(1, 24): c.execute("INSERT INTO rooms VALUES (?, 0, '')", (i,))
        c.execute("INSERT INTO staff (username, password, role, salary_rate) VALUES ('admin', ?, 'مدير', 0)", (make_hashes('admin2026'),))
    conn.commit()
    return conn

conn = init_db()

# --- 2. نظام الدخول ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🏨 مرقد جمال - تسجيل الدخول")
    u, p = st.text_input("المستخدم"), st.text_input("المرور", type="password")
    if st.button("دخول"):
        res = conn.execute("SELECT password, role FROM staff WHERE username=?", (u,)).fetchone()
        if res and check_hashes(p, res[0]):
            st.session_state.auth, st.session_state.user, st.session_state.role = True, u, res[1]
            st.session_state.login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO attendance (user, login_time, date) VALUES (?,?,?)", (u, st.session_state.login_time, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            st.rerun()
else:
    # --- 3. واجهة التحكم ---
    st.sidebar.title(f"👤 {st.session_state.user}")
    rooms_df = pd.read_sql_query("SELECT * FROM rooms", conn)
    
    # خريطة الغرف الملونة
    cols = st.columns(8)
    for i, r in rooms_df.iterrows():
        colors = {0: "#27ae60", 1: "#e74c3c", 2: "#3498db", 3: "#f1c40f", 4: "#95a5a6"}
        bg = colors.get(r['status_code'], "#eee")
        cols[i%8].markdown(f"<div style='background:{bg}; color:white; padding:10px; border-radius:5px; text-align:center; font-size:12px; margin-bottom:5px; font-weight:bold;'>{r['id']}</div>", unsafe_allow_html=True)

    menu = ["🏨 الاستقبال", "📑 أرشيف الزبائن", "🛠️ الصيانة والتنظيف", "💰 تسليم الكاسة", "⚙️ الإدارة"]
    choice = st.sidebar.selectbox("القائمة", menu)

    # --- المحور 1: الاستقبال (منظم وكامل) ---
    if choice == "🏨 الاستقبال":
        st.subheader("📝 تسجيل بيانات الزبون")
        with st.form("checkin_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                r_id = st.selectbox("رقم الغرفة", rooms_df[rooms_df['status_code'] == 0]['id'].tolist())
                f_name = st.text_input("الاسم واللقب")
                b_date = st.text_input("تاريخ الميلاد")
                b_place = st.text_input("مكان الميلاد")
            with c2:
                d_type = st.selectbox("نوع الوثيقة", ["بطاقة تعريف", "رخصة سياقة", "جواز سفر"])
                d_num = st.text_input("رقم الوثيقة")
                issuer = st.text_input("جهة الإصدار")
                addr = st.text_input("العنوان")
            with c3:
                tel = st.text_input("الهاتف")
                job = st.text_input("المهنة")
                days = st.number_input("مدة الإقامة", min_value=1)
                up_file = st.file_uploader("📷 تصوير الوثيقة")
            
            st.divider()
            col_f1, col_f2 = st.columns(2)
            t_price = col_f1.number_input("المبلغ الإجمالي المتفق عليه", value=0.0)
            p_amount = col_f2.number_input("المبلغ المدفوع (العربون)", value=0.0)

            if st.form_submit_button("تأكيد الحجز"):
                img = up_file.read() if up_file else None
                conn.execute("UPDATE rooms SET status_code=1, guest_name=? WHERE id=?", (f_name, r_id))
                conn.execute('''INSERT INTO bookings (room_id, name, birth_date, birth_place, job, address, doc_type, doc_num, issuer, phone, stay_days, total_price, paid_amount, date, worker, doc_image) 
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                            (r_id, f_name, b_date, b_place, job, addr, d_type, d_num, issuer, tel, days, t_price, p_amount, datetime.now().strftime("%Y-%m-%d"), st.session_state.user, img))
                conn.commit()
                st.success("تم تسجيل الزبون بنجاح")
                st.rerun()

    # --- المحور 2: أرشيف الزبائن (كما أعجبك) ---
    elif choice == "📑 أرشيف الزبائن":
        st.subheader("📂 السجل التاريخي للزبائن")
        df_log = pd.read_sql_query("SELECT id, room_id, name, doc_num, phone, total_price, paid_amount, date, worker FROM bookings ORDER BY id DESC", conn)
        st.dataframe(df_log, use_container_width=True)
        search = st.text_input("🔍 بحث سري")
        if search: st.dataframe(df_log[df_log['name'].str.contains(search) | df_all['doc_num'].str.contains(search)])

    # --- المحور 3: الصيانة والتنظيف (مدمج مع خيارات الغرف) ---
    elif choice == "🛠️ الصيانة والتنظيف":
        st.subheader("🛠️ إدارة حالة الغرف")
        r_sel = st.selectbox("اختر الغرفة", rooms_df['id'].tolist())
        new_stat = st.radio("الحالة الجديدة", ["جاهزة (شاغرة)", "قيد التنظيف 🧹", "في الصيانة 🛠️"], horizontal=True)
        if st.button("تحديث الحالة"):
            code = 0 if "جاهزة" in new_stat else 3 if "تنظيف" in new_stat else 4
            conn.execute("UPDATE rooms SET status_code=?, guest_name='' WHERE id=?", (code, r_sel))
            conn.commit()
            st.rerun()

    # --- المحور 4: تسليم الكاسة (المعادلة الصفرية) ---
    elif choice == "💰 تسليم الكاسة":
        st.subheader("🧾 جرد وتسليم المداومة")
        # حساب مبالغ العامل الحالية فقط
        expected = pd.read_sql_query(f"SELECT SUM(paid_amount) FROM bookings WHERE worker='{st.session_state.user}' AND date='{datetime.now().strftime('%Y-%m-%d')}'", conn).iloc[0,0] or 0
        st.info(f"المبالغ المسجلة في ورديتك: {expected} DZD")
        actual = st.number_input("المبلغ النقدي المسلم فعلياً:", value=float(expected))
        
        diff = actual - expected
        if diff < 0: st.error(f"⚠️ عجز: {abs(diff)} DZD (سيُسجل كتسبيق على العامل)")
        
        if st.button("إغلاق الوردية والخروج"):
            if diff < 0:
                conn.execute("INSERT INTO expenses (item, amount, date, category) VALUES (?,?,?,?)", 
                            (f"عجز وردية: {st.session_state.user}", abs(diff), datetime.now().strftime("%Y-%m-%d"), "تسبيق عمال"))
            conn.execute("UPDATE attendance SET logout_time=? WHERE user=? AND login_time=?", 
                        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.user, st.session_state.login_time))
            conn.commit()
            st.session_state.auth = False
            st.rerun()

    # --- المحور 5: الإدارة (أجور، مصاريف، مداخل) ---
    elif choice == "⚙️ الإدارة":
        if st.session_state.role == "مدير":
            tab1, tab2 = st.tabs(["📊 الميزانية العامة", "👷 شؤون العمال"])
            with tab1:
                st.write("### 📈 كشف المداخيل والمصاريف")
                inc_df = pd.read_sql_query("SELECT date, name, paid_amount as amount FROM bookings", conn)
                exp_df = pd.read_sql_query("SELECT date, item, amount FROM expenses", conn)
                total_i, total_e = inc_df['amount'].sum(), exp_df['amount'].sum()
                st.metric("الربح الصافي", f"{total_i - total_e} DZD")
                st.write("تفاصيل المصاريف:")
                st.dataframe(exp_df)
            with tab2:
                st.write("### 🕒 سجل الورديات والأجور")
                # حساب ساعات العمل والأيام
                st.dataframe(pd.read_sql_query("SELECT user, date, login_time, logout_time FROM attendance", conn))
        else:
            st.error("صلاحية المدير فقط")
