import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- 1. المحرك الأساسي (إصلاح شامل لقاعدة البيانات) ---
def init_db():
    conn = sqlite3.connect('djamal_ultimate_v10.db', check_same_thread=False)
    c = conn.cursor()
    # 0=شاغرة (أخضر)، 1=محجوزة (أحمر)، 2=هاتفي (أزرق)
    c.execute('CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY, status_code INTEGER, guest_name TEXT)')
    # سجل الأمن والحجوزات الشامل
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, name TEXT, 
                 birth_place TEXT, job TEXT, address TEXT, doc_num TEXT, 
                 issuer TEXT, phone TEXT, price REAL, date TEXT, type TEXT)''')
    # المصاريف والمشتريات
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, amount REAL, date TEXT)')
    # العمال
    c.execute('CREATE TABLE IF NOT EXISTS staff (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, salary REAL)')
    
    c.execute("SELECT count(*) FROM rooms")
    if c.fetchone()[0] == 0:
        for i in range(1, 24): c.execute("INSERT INTO rooms VALUES (?, 0, '')", (i,))
    conn.commit()
    return conn

conn = init_db()

# --- 2. التصميم (أفضل ما وجد في النسخة الأولى) ---
st.set_page_config(page_title="Dortoir Djamal Ultimate", layout="wide")
st.markdown("<h1 style='text-align: center; color: #2c3e50;'>🏨 نظام تسيير فندق جمال - الاحترافي</h1>", unsafe_allow_html=True)

# --- 3. عرض الغرف التفاعلي (إصلاح الألوان والتحديث) ---
rooms_df = pd.read_sql_query("SELECT * FROM rooms", conn)
st.write("### 📊 لوحة المراقبة اللحظية")
cols = st.columns(8)
for i, r in rooms_df.iterrows():
    # المنطق البصري
    bg = "#27ae60" if r['status_code'] == 0 else "#c0392b" if r['status_code'] == 1 else "#2980b9"
    label = "شاغرة" if r['status_code'] == 0 else "محجوزة" if r['status_code'] == 1 else "📞 هاتف"
    
    cols[i%8].markdown(f"""
        <div style='background:{bg}; color:white; padding:12px; border-radius:10px; text-align:center; margin-bottom:10px; border: 1px solid #ddd;'>
            <div style='font-size:18px; font-weight:bold;'>{r['id']}</div>
            <div style='font-size:11px;'>{label}</div>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 4. القائمة الجانبية (أفضل تقسيم للمهام) ---
menu = ["🏨 الاستقبال والأمن", "📞 الحجز الهاتفي", "🛒 المشتريات والعمال", "📈 الحسابات الشهرية"]
choice = st.sidebar.selectbox("القائمة الرئيسية", menu)

# --- 5. معالجة العمليات (أقوى Logic) ---

if choice == "🏨 الاستقبال والأمن":
    st.subheader("📝 Fiche Police & تسجيل دخول")
    # نختار الغرف غير المحجوزة فعلياً
    target_rooms = rooms_df[rooms_df['status_code'] != 1]['id'].tolist()
    
    with st.form("security_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            r_id = st.selectbox("رقم الغرفة", target_rooms)
            f_name = st.text_input("الاسم واللقب")
            b_place = st.text_input("مكان الميلاد")
        with c2:
            job = st.text_input("المهنة")
            doc = st.text_input("رقم الهوية")
            issuer = st.text_input("جهة الإصدار")
        with c3:
            addr = st.text_input("العنوان")
            tel = st.text_input("الهاتف")
            price = st.number_input("السعر المتفق عليه", value=4000)

        if st.form_submit_button("تأكيد التسكين (تحويل للأحمر)"):
            cur = conn.cursor()
            cur.execute("UPDATE rooms SET status_code=1, guest_name=? WHERE id=?", (f_name, r_id))
            cur.execute("INSERT INTO bookings (room_id, name, birth_place, job, address, doc_num, issuer, phone, price, date, type) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (r_id, f_name, b_place, job, addr, doc, issuer, tel, price, datetime.now().strftime("%Y-%m-%d"), 'فعلي'))
            conn.commit()
            st.success("تم التسكين بنجاح!")
            st.rerun()

    st.divider()
    st.subheader("📤 تسوية المغادرة (Check-out)")
    occ_rooms = rooms_df[rooms_df['status_code'] != 0]['id'].tolist()
    if occ_rooms:
        r_out = st.selectbox("اختر غرفة للمغادرة", occ_rooms)
        if st.button("تحرير الغرفة (إرجاع للأخضر)"):
            conn.execute("UPDATE rooms SET status_code=0, guest_name='' WHERE id=?", (r_out,))
            conn.commit()
            st.warning(f"الغرفة {r_out} أصبحت شاغرة الآن")
            st.rerun()

elif choice == "📞 الحجز الهاتفي":
    st.subheader("📞 إدارة الحجوزات الهاتفية")
    with st.form("phone_form"):
        free = rooms_df[rooms_df['status_code'] == 0]['id'].tolist()
        r_ph = st.selectbox("غرفة شاغرة", free)
        n_ph = st.text_input("اسم المتصل")
        p_ph = st.text_input("رقم الهاتف")
        if st.form_submit_button("تثبيت الحجز (تحويل للأزرق)"):
            conn.execute("UPDATE rooms SET status_code=2, guest_name=? WHERE id=?", (n_ph, r_ph))
            conn.commit()
            st.info("تم تمييز الغرفة باللون الأزرق")
            st.rerun()

elif choice == "🛒 المشتريات والعمال":
    tab1, tab2 = st.tabs(["🛍️ المشتريات", "👥 العمال"])
    with tab1:
        with st.form("exp"):
            item = st.text_input("الوصف (كهرباء، ماء، لوازم)")
            amt = st.number_input("المبلغ", min_value=0)
            if st.form_submit_button("حفظ المصروف"):
                conn.execute("INSERT INTO expenses (item, amount, date) VALUES (?,?,?)", (item, amt, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success("تم الحفظ")
    with tab2:
        with st.form("staff"):
            s_name = st.text_input("اسم العامل")
            s_sal = st.number_input("الراتب الشهري", min_value=0)
            if st.form_submit_button("إضافة عامل"):
                conn.execute("INSERT INTO staff (name, salary) VALUES (?,?)", (s_name, s_sal))
                conn.commit()
                st.rerun()

elif choice == "📈 الحسابات الشهرية":
    st.subheader("📊 ملخص الميزانية الصافية")
    month = datetime.now().strftime("%Y-%m")
    
    income = pd.read_sql_query(f"SELECT SUM(price) FROM bookings WHERE date LIKE '{month}%'", conn).iloc[0,0] or 0
    expenses = pd.read_sql_query(f"SELECT SUM(amount) FROM expenses WHERE date LIKE '{month}%'", conn).iloc[0,0] or 0
    salaries = pd.read_sql_query("SELECT SUM(salary) FROM staff", conn).iloc[0,0] or 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("المداخيل", f"{income:,.0f} DZD")
    col2.metric("المصاريف + الرواتب", f"{(expenses + salaries):,.0f} DZD")
    col3.metric("الربح الصافي", f"{(income - expenses - salaries):,.0f} DZD")
