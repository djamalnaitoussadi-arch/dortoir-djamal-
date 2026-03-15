import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
from fpdf import FPDF

# ---------------------------
# التشفير
# ---------------------------

def make_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_hash(password, hashed):
    return make_hash(password) == hashed


# ---------------------------
# قاعدة البيانات
# ---------------------------

def init_db():

    conn = sqlite3.connect("hotel.db",check_same_thread=False)
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS rooms(id INTEGER PRIMARY KEY,status_code INTEGER,guest_name TEXT)")

    c.execute("""CREATE TABLE IF NOT EXISTS bookings(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER,
    name TEXT,
    phone TEXT,
    stay_days INTEGER,
    total_price REAL,
    paid_amount REAL,
    date TEXT,
    worker TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS staff(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT,
    role TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS attendance(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    login_time TEXT,
    logout_time TEXT,
    date TEXT)""")

    # إنشاء الغرف
    if conn.execute("SELECT count(*) FROM rooms").fetchone()[0] == 0:

        for i in range(1,24):
            c.execute("INSERT INTO rooms VALUES(?,?,?)",(i,0,''))

        c.execute("INSERT INTO staff(username,password,role) VALUES(?,?,?)",
        ("admin",make_hash("admin2026"),"مدير"))

    conn.commit()

    return conn


conn = init_db()


# ---------------------------
# فاتورة PDF
# ---------------------------

def make_invoice(name,room,days,total,paid):

    pdf=FPDF()
    pdf.add_page()

    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"HOTEL RECEIPT",0,1,"C")

    pdf.set_font("Arial","",12)

    pdf.cell(0,10,f"Guest: {name}",0,1)
    pdf.cell(0,10,f"Room: {room}",0,1)
    pdf.cell(0,10,f"Days: {days}",0,1)

    pdf.cell(0,10,f"Total: {total}",0,1)
    pdf.cell(0,10,f"Paid: {paid}",0,1)

    pdf.cell(0,10,f"Date: {datetime.now().strftime('%Y-%m-%d')}",0,1)

    file="invoice.pdf"
    pdf.output(file)

    return file


# ---------------------------
# تسجيل الدخول
# ---------------------------

if "auth" not in st.session_state:
    st.session_state.auth=False

if not st.session_state.auth:

    st.title("🏨 نظام المرقد")

    user=st.text_input("المستخدم")
    pwd=st.text_input("كلمة المرور",type="password")

    if st.button("دخول"):

        res=conn.execute(
        "SELECT password,role FROM staff WHERE username=?",
        (user,)
        ).fetchone()

        if res and check_hash(pwd,res[0]):

            st.session_state.auth=True
            st.session_state.user=user
            st.session_state.role=res[1]

            st.session_state.login_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn.execute(
            "INSERT INTO attendance(user,login_time,date) VALUES(?,?,?)",
            (user,st.session_state.login_time,datetime.now().strftime("%Y-%m-%d"))
            )

            conn.commit()

            st.rerun()

        else:

            st.error("خطأ في الدخول")


# ---------------------------
# الواجهة الرئيسية
# ---------------------------

else:

    st.sidebar.title(f"👤 {st.session_state.user}")

    menu=[
    "خريطة الغرف",
    "تسجيل زبون",
    "خروج زبون",
    "الأرشيف",
    "الصيانة",
    "الكاسة",
    "الإدارة"
    ]

    choice=st.sidebar.selectbox("القائمة",menu)

    rooms_df=pd.read_sql_query("SELECT * FROM rooms",conn)


# ---------------------------
# خريطة الغرف
# ---------------------------

    if choice=="خريطة الغرف":

        st.subheader("🏨 حالة الغرف")

        colors={
        0:"#2ecc71",
        1:"#e74c3c",
        3:"#f1c40f",
        4:"#7f8c8d"
        }

        cols=st.columns(8)

        for i,r in rooms_df.iterrows():

            color=colors.get(r['status_code'],"#bdc3c7")

            cols[i%8].markdown(
            f"""
            <div style="
            background:{color};
            padding:20px;
            border-radius:10px;
            text-align:center;
            color:white;
            font-weight:bold">
            غرفة {r['id']}
            </div>
            """,
            unsafe_allow_html=True
            )


# ---------------------------
# تسجيل زبون
# ---------------------------

    elif choice=="تسجيل زبون":

        st.subheader("تسجيل النزيل")

        free_rooms=rooms_df[rooms_df['status_code']==0]['id'].tolist()

        if not free_rooms:

            st.warning("لا توجد غرف شاغرة")
            st.stop()

        room=st.selectbox("الغرفة",free_rooms)

        name=st.text_input("الاسم")

        phone=st.text_input("الهاتف")

        days=st.number_input("عدد الأيام",1)

        total=st.number_input("السعر الكلي")

        paid=st.number_input("المبلغ المدفوع")

        img=st.camera_input("تصوير الوثيقة")

        if st.button("تسجيل"):

            conn.execute(
            "UPDATE rooms SET status_code=1,guest_name=? WHERE id=?",
            (name,room)
            )

            conn.execute("""
            INSERT INTO bookings(room_id,name,phone,stay_days,total_price,paid_amount,date,worker)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (room,name,phone,days,total,paid,
            datetime.now().strftime("%Y-%m-%d"),
            st.session_state.user)
            )

            conn.commit()

            st.success("تم تسجيل الزبون")

            file=make_invoice(name,room,days,total,paid)

            with open(file,"rb") as f:

                st.download_button(
                "تحميل الفاتورة",
                f,
                file_name=file
                )

            st.rerun()


# ---------------------------
# خروج زبون
# ---------------------------

    elif choice=="خروج زبون":

        busy=rooms_df[rooms_df['status_code']==1]

        if busy.empty:

            st.info("لا يوجد زبائن")

        else:

            room=st.selectbox("الغرفة",busy['id'])

            if st.button("خروج"):

                conn.execute(
                "UPDATE rooms SET status_code=0,guest_name='' WHERE id=?",
                (room,)
                )

                conn.commit()

                st.success("تم خروج الزبون")

                st.rerun()


# ---------------------------
# الأرشيف
# ---------------------------

    elif choice=="الأرشيف":

        df=pd.read_sql_query("SELECT * FROM bookings ORDER BY id DESC",conn)

        search=st.text_input("بحث")

        if search:

            df=df[df['name'].str.contains(search,na=False)]

        st.dataframe(df,use_container_width=True)


# ---------------------------
# الصيانة
# ---------------------------

    elif choice=="الصيانة":

        room=st.selectbox("الغرفة",rooms_df['id'])

        status=st.radio("الحالة",["جاهزة","تنظيف","صيانة"])

        if st.button("تحديث"):

            if status=="جاهزة":
                code=0
            elif status=="تنظيف":
                code=3
            else:
                code=4

            conn.execute(
            "UPDATE rooms SET status_code=?,guest_name='' WHERE id=?",
            (code,room)
            )

            conn.commit()

            st.success("تم التحديث")

            st.rerun()


# ---------------------------
# الكاسة
# ---------------------------

    elif choice=="الكاسة":

        today=datetime.now().strftime("%Y-%m-%d")

        expected=pd.read_sql_query(
        f"SELECT SUM(paid_amount) FROM bookings WHERE worker='{st.session_state.user}' AND date='{today}'",
        conn
        ).iloc[0,0]

        if expected is None:
            expected=0

        st.info(f"المبلغ المسجل: {expected}")

        actual=st.number_input("المبلغ الحقيقي",value=float(expected))

        diff=actual-expected

        if diff<0:
            st.error(f"عجز {abs(diff)}")

        if st.button("إغلاق الوردية"):

            conn.execute(
            "UPDATE attendance SET logout_time=? WHERE user=? AND login_time=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            st.session_state.user,
            st.session_state.login_time)
            )

            conn.commit()

            st.session_state.auth=False

            st.rerun()


# ---------------------------
# الإدارة
# ---------------------------

    elif choice=="الإدارة":

        if st.session_state.role!="مدير":

            st.error("صلاحية المدير فقط")

        else:

            income=pd.read_sql_query(
            "SELECT SUM(paid_amount) FROM bookings",
            conn
            ).iloc[0,0]

            if income is None:
                income=0

            st.metric("إجمالي المداخيل",income)

            st.write("سجل الحضور")

            att=pd.read_sql_query("SELECT * FROM attendance",conn)

            st.dataframe(att)