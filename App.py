import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. الأمان والوظائف المساعدة ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def init_db():
    conn = sqlite3.connect('djamal_final_pro.db', check_same_thread=False)
    c = conn.cursor()
    # 0=شاغرة، 1=محجوزة، 2=هاتفي
    c.execute('CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY, status_code INTEGER, guest_name TEXT)')
    # سجل الحجوزات الكامل (دمج بيانات الأمن والوثائق)
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, name TEXT, 
                 birth_place TEXT, job TEXT, address TEXT, doc_num TEXT, 
                 issuer TEXT, phone TEXT, price REAL, date TEXT, type TEXT, doc_image BLOB)''')
    # العمال (مع الصلاحيات والملاحظات السرية)
    c.execute('''CREATE TABLE IF NOT EXISTS staff (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, 
                 role TEXT, salary REAL, private_notes TEXT)''')
    # الرقابة والحضور
    c.execute('CREATE TABLE IF NOT EXISTS attendance (user TEXT, login_time TEXT)')
    # القائمة السوداء
    c.execute('CREATE TABLE IF NOT EXISTS blacklist (name TEXT, reason TEXT)')
    # المشتريات والمصاريف
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, amount REAL, date TEXT)')
    
    c.execute("SELECT count(*) FROM rooms")
    if c.fetchone()[0] == 0:
        for i in range(1, 24): c.execute("INSERT INTO rooms VALUES (?, 0, '')", (i,))
        # حساب المدير الافتراضي
        c.execute("INSERT INTO staff (username, password, role, salary, private_notes) VALUES ('admin', ?, 'مدير', 0, 'مدير النظام')", (make_hashes('admin2026'),))
    conn.commit()
    return conn

conn = init_db()

# --- 2. وظيفة طباعة الفاتورة PDF ---
def generate_invoice(res_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Dortoir Djamal - Facture", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=2)
    for key, value in res_data.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=2)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. نظام تسجيل الدخول والصلاحيات ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.set_page_config(page_title="تسجيل الدخول", layout="centered")
    st.title("🔑 نظام فندق جمال - الدخول")
    u = st.text_input("اسم المستخدم")
    p = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        res = conn.execute("SELECT password, role FROM staff WHERE username=?", (u,)).fetchone()
        if res and check_hashes(p, res[0]):
            st.session_state.auth, st.session_state.user, st.session_state.role = True, u, res[1]
            conn.execute("INSERT INTO attendance VALUES (?,?)", (u, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            st.rerun()
        else: st.error("خطأ في بيانات الدخول")
else:
    st.set_page_config(page_title="Dortoir Djamal Pro", layout="wide")
    st.sidebar.title(f"👤 {st.session_state.user}")
    st.sidebar.write(f"الرتبة: {st.session_state.role}")

    # --- 4. عرض لوحة الغرف (التصميم الملون) ---
    rooms_df = pd.read_sql_query("SELECT * FROM rooms", conn)
    st.markdown("<h1 style='text-align: center;'>🏨 لوحة مراقبة الغرف</h1>", unsafe_allow_html=True)
    cols = st.columns(8)
    for i, r in rooms_df.iterrows():
        bg = "#27ae60" if r['status_code'] == 0 else "#c0392b" if r['status_code'] == 1 else "#2980b9"
        label = "شاغرة" if r['status_code'] == 0 else "محجوزة" if r['status_code'] == 1 else "📞 هاتف"
        cols[i%8].markdown(f"<div style='background:{bg}; color:white; padding:10px; border-radius:8px; text-align:center; margin-bottom:10px; font-weight:bold;'>{r['id']}<br><small>{label}</small></div>", unsafe_allow_html=True)

    st.divider()

    # --- 5. القوائم حسب الصلاحيات ---
    if st.session_state.role == "مدير":
        menu = ["🏨 الاستقبال والأمن", "📞 الحجز الهاتفي", "👥 إدارة العمال", "🛒 المشتريات", "📈 الحسابات الشهرية & القائمة السوداء"]
    else:
        menu = ["🏨 الاستقبال والأمن", "📞 الحجز الهاتفي"]
    
    choice = st.sidebar.selectbox("القائمة الرئيسية", menu)

    if choice == "🏨 الاستقبال والأمن":
        st.subheader("📝 تسجيل زبون (Fiche Police)")
        target_rooms = rooms_df[rooms_df['status_code'] != 1]['id'].tolist()
        with st.form("checkin_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                r_id = st.selectbox("رقم الغرفة", target_rooms)
                f_name = st.text_input("الاسم واللقب")
                b_place = st.text_input("مكان الميلاد")
            with c2:
                job = st.text_input("المهنة")
                doc = st.text_input("رقم الوثيقة")
                issuer = st.text_input("جهة الإصدار")
            with c3:
                tel = st.text_input("الهاتف")
                price = st.number_input("السعر", value=4000)
                uploaded_file = st.file_uploader("📷 تصوير الوثيقة", type=['jpg','png'])

            if st.form_submit_button("تأكيد الحجز وطباعة الفاتورة"):
                if conn.execute("SELECT name FROM blacklist WHERE name=?", (f_name,)).fetchone():
                    st.error("⚠️ هذا الزبون محظور (القائمة السوداء)!")
                else:
                    img_blob = uploaded_file.read() if uploaded_file else None
                    conn.execute("UPDATE rooms SET status_code=1, guest_name=? WHERE id=?", (f_name, r_id))
                    conn.execute("INSERT INTO bookings (room_id, name, birth_place, job, doc_num, issuer, phone, price, date, type, doc_image) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                (r_id, f_name, b_place, job, doc, issuer, tel, price, datetime.now().strftime("%Y-%m-%d"), 'فعلي', img_blob))
                    conn.commit()
                    st.success("تم الحفظ بنجاح!")
                    st.rerun()
        
        st.divider()
        st.subheader("📤 خروج زبون / طباعة فواتير")
        occ_rooms = rooms_df[rooms_df['status_code'] != 0]['id'].tolist()
        if occ_rooms:
            r_out = st.selectbox("اختر غرفة للمغادرة أو الطباعة", occ_rooms)
            c_out1, c_out2 = st.columns(2)
            if c_out1.button("إتمام الخروج (تحرير الغرفة)"):
                conn.execute("UPDATE rooms SET status_code=0, guest_name='' WHERE id=?", (r_out,))
                conn.commit()
                st.rerun()
            
            # قسم الطباعة
            last_b = pd.read_sql_query(f"SELECT * FROM bookings WHERE room_id={r_out} ORDER BY id DESC LIMIT 1", conn)
            if not last_b.empty:
                row = last_b.iloc[0]
                inv_data = {"Nom": row['name'], "Chambre": row['room_id'], "Prix": row['price'], "Date": row['date']}
                st.download_button("📄 طباعة الفاتورة PDF", generate_invoice(inv_data), f"invoice_{r_out}.pdf")

    elif choice == "📞 الحجز الهاتفي":
        st.subheader("📞 تسجيل حجز هاتفي")
        with st.form("phone"):
            r_ph = st.selectbox("غرفة شاغرة", rooms_df[rooms_df['status_code']==0]['id'].tolist())
            n_ph = st.text_input("اسم المتصل")
            if st.form_submit_button("تثبيت الحجز الهاتفي (أزرق)"):
                conn.execute("UPDATE rooms SET status_code=2, guest_name=? WHERE id=?", (n_ph, r_ph))
                conn.commit()
                st.rerun()

    elif choice == "👥 إدارة العمال":
        st.subheader("👥 العمال والرقابة")
        with st.expander("إضافة عامل جديد"):
            u_new = st.text_input("اسم مستخدم العامل")
            p_new = st.text_input("كلمة السر", type="password")
            sal = st.number_input("الراتب")
            notes = st.text_area("ملاحظات سرية (المدير فقط يراها)")
            if st.button("حفظ العامل"):
                conn.execute("INSERT INTO staff (username, password, role, salary, private_notes) VALUES (?,?,'استقبال',?,?)",
                            (u_new, make_hashes(p_new), sal, notes))
                conn.commit()
        st.write("### سجل حضور العمال")
        st.dataframe(pd.read_sql_query("SELECT * FROM attendance", conn))
        st.write("### بيانات العمال")
        st.dataframe(pd.read_sql_query("SELECT username, salary, private_notes FROM staff WHERE role='استقبال'", conn))

    elif choice == "🛒 المشتريات":
        st.subheader("🛒 سجل المصاريف")
        with st.form("exp"):
            item = st.text_input("الوصف (كهرباء، لوازم...)")
            amt = st.number_input("المبلغ", min_value=0.0)
            if st.form_submit_button("حفظ المصروف"):
                conn.execute("INSERT INTO expenses (item, amount, date) VALUES (?,?,?)", (item, amt, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success("تم التسجيل")

    elif choice == "📈 الحسابات الشهرية & القائمة السوداء":
        t1, t2 = st.tabs(["💰 الميزانية", "🌑 القائمة السوداء"])
        with t1:
            month = datetime.now().strftime("%Y-%m")
            inc = pd.read_sql_query(f"SELECT SUM(price) FROM bookings WHERE date LIKE '{month}%'", conn).iloc[0,0] or 0
            exp = pd.read_sql_query(f"SELECT SUM(amount) FROM expenses WHERE date LIKE '{month}%'", conn).iloc[0,0] or 0
            salaries = pd.read_sql_query("SELECT SUM(salary) FROM staff", conn).iloc[0,0] or 0
            st.metric("المداخيل", f"{inc} DZD")
            st.metric("المصاريف + الرواتب", f"{exp + salaries} DZD")
            st.metric("الربح الصافي", f"{inc - (exp + salaries)} DZD")
        with t2:
            b_name = st.text_input("اسم للحظر")
            b_reason = st.text_area("السبب")
            if st.button("إضافة للقائمة السوداء"):
                conn.execute("INSERT INTO blacklist VALUES (?,?)", (b_name, b_reason))
                conn.commit()
                st.success("تم الحظر")
