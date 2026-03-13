import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
from fpdf import FPDF

# --- 1. الأمان والضرائب (TAP 1%, TVA 19%) ---
def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

def init_db():
    conn = sqlite3.connect('djamal_final_v2026.db', check_same_thread=False)
    c = conn.cursor()
    # الغرف: 0=شاغرة، 1=محجوزة، 2=هاتف، 3=تنظيف، 4=صيانة
    c.execute('CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY, status_code INTEGER, guest_name TEXT)')
    # أرشيف الزبائن الدائم
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, name TEXT, 
                 birth_date TEXT, birth_place TEXT, job TEXT, address TEXT, doc_num TEXT, 
                 issuer TEXT, phone TEXT, total_price REAL, paid_amount REAL, 
                 date TEXT, worker TEXT)''')
    # العمال والرواتب
    c.execute('CREATE TABLE IF NOT EXISTS staff (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, role TEXT, salary REAL, notes TEXT)')
    # سجل تسليم المداومة (الكاسة)
    c.execute('CREATE TABLE IF NOT EXISTS shifts (id INTEGER PRIMARY KEY AUTOINCREMENT, worker TEXT, login_time TEXT, logout_time TEXT, expected_cash REAL, actual_cash REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS blacklist (name TEXT, reason TEXT)')
    
    if conn.execute("SELECT count(*) FROM rooms").fetchone()[0] == 0:
        for i in range(1, 24): c.execute("INSERT INTO rooms VALUES (?, 0, '')", (i,))
        c.execute("INSERT INTO staff (username, password, role, salary, notes) VALUES ('admin', ?, 'مدير', 0, 'المالك')", (make_hashes('admin2026'),))
    conn.commit()
    return conn

conn = init_db()

# --- 2. محرك الطباعة PDF ---
def generate_invoice(res):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="Facture - Dortoir Djamal", ln=1, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    for k, v in res.items(): pdf.cell(190, 10, txt=f"{k}: {v}", ln=1)
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- 3. نظام الدخول ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.set_page_config(page_title="دخول النظام", layout="centered")
    st.title("🏨 فندق جمال - الدخول")
    u, p = st.text_input("المستخدم"), st.text_input("المرور", type="password")
    if st.button("دخول"):
        res = conn.execute("SELECT password, role FROM staff WHERE username=?", (u,)).fetchone()
        if res and check_hashes(p, res[0]):
            st.session_state.auth, st.session_state.user, st.session_state.role = True, u, res[1]
            st.session_state.start_t = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.rerun()
else:
    st.set_page_config(page_title="Djamal Pro v2026", layout="wide")
    st.sidebar.title(f"👤 {st.session_state.user}")
    
    # عرض الغرف بالألوان
    rooms_df = pd.read_sql_query("SELECT * FROM rooms", conn)
    cols = st.columns(8)
    for i, r in rooms_df.iterrows():
        # أخضر (شاغرة)، أحمر (حجز)، أزرق (هاتف)، أصفر (تنظيف)، رمادي (صيانة)
        colors = {0: "#27ae60", 1: "#e74c3c", 2: "#3498db", 3: "#f1c40f", 4: "#7f8c8d"}
        cols[i%8].markdown(f"<div style='background:{colors.get(r['status_code'])}; color:white; padding:10px; border-radius:8px; text-align:center; margin-bottom:10px; font-weight:bold;'>{r['id']}</div>", unsafe_allow_html=True)

    menu = ["🏨 الاستقبال", "📑 أرشيف الزبائن", "🛠️ الصيانة والتنظيف", "💰 تسليم الكاسة", "⚙️ الإدارة"]
    choice = st.sidebar.selectbox("القائمة", menu if st.session_state.role == "مدير" else menu[:-1])

    # --- 4. الاستقبال (مع ميزة الولاء) ---
    if choice == "🏨 الاستقبال":
        st.subheader("📝 تسجيل دخول زبون")
        with st.form("checkin"):
            c1, c2, c3 = st.columns(3)
            with c1:
                r_id = st.selectbox("الغرفة", rooms_df[rooms_df['status_code'] == 0]['id'].tolist())
                f_name = st.text_input("الاسم واللقب")
                if f_name:
                    v_count = conn.execute("SELECT COUNT(*) FROM bookings WHERE name=?", (f_name,)).fetchone()[0]
                    if v_count > 0: st.info(f"⭐ زبون وفي: {v_count} زيارات")
                b_date = st.text_input("تاريخ الميلاد")
            with c2:
                doc_n = st.text_input("رقم الوثيقة")
                tel = st.text_input("الهاتف")
                addr = st.text_input("العنوان")
            with c3:
                total = st.number_input("المبلغ الإجمالي", value=4000.0)
                paid = st.number_input("المبلغ المدفوع", value=4000.0)
                up_file = st.file_uploader("📷 صورة الوثيقة")

            if st.form_submit_button("تأكيد وحفظ"):
                if conn.execute("SELECT name FROM blacklist WHERE name=?", (f_name,)).fetchone():
                    st.error("⚠️ محظور!")
                else:
                    blob = up_file.read() if up_file else None
                    conn.execute("UPDATE rooms SET status_code=1, guest_name=? WHERE id=?", (f_name, r_id))
                    conn.execute("INSERT INTO bookings (room_id, name, birth_date, doc_num, phone, address, total_price, paid_amount, date, worker) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                (r_id, f_name, b_date, doc_n, tel, addr, total, paid, datetime.now().strftime("%Y-%m-%d"), st.session_state.user))
                    conn.commit()
                    st.success("تم التسكين!")
                    st.rerun()

    # --- 5. أرشيف الزبائن العام ---
    elif choice == "📑 أرشيف الزبائن":
        st.subheader("📂 سجل جميع الزبائن المحفوظ")
        df_all = pd.read_sql_query("SELECT * FROM bookings ORDER BY id DESC", conn)
        st.dataframe(df_all)
        search = st.text_input("🔍 ابحث عن اسم أو رقم وثيقة")
        if search: st.dataframe(df_all[df_all['name'].str.contains(search) | df_all['doc_num'].str.contains(search)])

    # --- 6. الصيانة والتنظيف ---
    elif choice == "🛠️ الصيانة والتنظيف":
        st.subheader("🛠️ تغيير حالة الغرف")
        r_sel = st.selectbox("اختر الغرفة", rooms_df['id'].tolist())
        stat = st.radio("الحالة الجديدة:", ["جاهزة (شاغرة)", "قيد التنظيف 🧹", "صيانة 🛠️"])
        if st.button("تحديث"):
            code = 0 if "جاهزة" in stat else 3 if "تنظيف" in stat else 4
            conn.execute("UPDATE rooms SET status_code=?, guest_name='' WHERE id=?", (code, r_sel))
            conn.commit()
            st.rerun()

    # --- 7. تسليم الكاسة ---
    elif choice == "💰 تسليم الكاسة":
        st.subheader("🧾 إغلاق الوردية والمحاسبة")
        exp = pd.read_sql_query(f"SELECT SUM(paid_amount) FROM bookings WHERE worker='{st.session_state.user}' AND date='{datetime.now().strftime('%Y-%m-%d')}'", conn).iloc[0,0] or 0
        st.warning(f"المبلغ المتوقع في الدرج: {exp} DZD")
        real = st.number_input("أدخل المبلغ الفعلي الموجود:", value=float(exp))
        if st.button("تأكيد التسليم والخروج"):
            conn.execute("INSERT INTO shifts (worker, login_time, logout_time, expected_cash, actual_cash) VALUES (?,?,?,?,?)",
                        (st.session_state.user, st.session_state.start_t, datetime.now().strftime("%Y-%m-%d %H:%M"), exp, real))
            conn.commit()
            st.session_state.auth = False
            st.rerun()

    # --- 8. الإدارة (المدير) ---
    elif choice == "⚙️ الإدارة":
        st.subheader("📊 كشف الحسابات (المدير)")
        df_fin = pd.read_sql_query("SELECT total_price, paid_amount FROM bookings", conn)
        st.metric("إجمالي المداخيل", f"{df_fin['total_price'].sum()} DZD")
        st.metric("إجمالي الديون", f"{df_fin['total_price'].sum() - df_fin['paid_amount'].sum()} DZD")
        st.write("### سجل تسليم الكاسة (المناوبات)")
        st.dataframe(pd.read_sql_query("SELECT * FROM shifts", conn))
