import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
from fpdf import FPDF
import shutil

# -----------------
# تشفير كلمة المرور
# -----------------
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

def check_pass(p,h):
    return hash_pass(p)==h

# -----------------
# قاعدة البيانات
# -----------------
def init_db():
    conn=sqlite3.connect("hotel_system.db",check_same_thread=False)
    c=conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS rooms(
    id INTEGER PRIMARY KEY,
    status_code INTEGER,
    guest_name TEXT)
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS bookings(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER,
    name TEXT,
    phone TEXT,
    stay_days INTEGER,
    total_price REAL,
    paid_amount REAL,
    date TEXT,
    worker TEXT)
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS staff(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT,
    role TEXT)
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    login_time TEXT,
    logout_time TEXT,
    date TEXT)
    """)

    if conn.execute("SELECT count(*) FROM rooms").fetchone()[0]==0:
        for i in range(1,24):
            c.execute("INSERT INTO rooms VALUES(?,?,?)",(i,0,''))
        c.execute(
            "INSERT INTO staff(username,password,role) VALUES(?,?,?)",
            ("admin",hash_pass("admin2026"),"مدير")
        )
    conn.commit()
    return conn

conn=init_db()

# -----------------
# إنشاء فاتورة PDF
# -----------------
def make_invoice(name,room,days,total,paid):
    pdf=FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"FACTURE / RECEIPT",0,1,"C")
    pdf.set_font("Arial","",12)
    pdf.cell(0,10,f"Name : {name}",0,1)
    pdf.cell(0,10,f"Room : {room}",0,1)
    pdf.cell(0,10,f"Days : {days}",0,1)
    pdf.cell(0,10,f"Total : {total}",0,1)
    pdf.cell(0,10,f"Paid : {paid}",0,1)
    pdf.cell(0,10,f"Date : {datetime.now().strftime('%Y-%m-%d')}",0,1)
    file="invoice.pdf"
    pdf.output(file)
    return file

# -----------------
# النسخ الاحتياطي
# -----------------
def backup():
    file="backup_"+datetime.now().strftime("%Y%m%d")+".db"
    shutil.copy("hotel_system.db",file)
    return file

# -----------------
# تسجيل الدخول
# -----------------
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
        if res and check_pass(pwd,res[0]):
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
            st.error("خطأ في تسجيل الدخول")

else:
    st.sidebar.title("👤 "+st.session_state.user)
    menu=[
        "خريطة الغرف",
        "الأرشيف",
        "الصيانة",
        "الكاسة",
        "الإحصائيات",
        "الإدارة"
    ]
    choice=st.sidebar.selectbox("القائمة",menu)
    rooms_df=pd.read_sql_query("SELECT * FROM rooms",conn)

# -----------------
# خريطة غرف تفاعلية
# -----------------
if choice=="خريطة الغرف":
    st.subheader("🏨 خريطة الغرف التفاعلية")
    colors={0:"🟢 شاغرة",1:"🔴 مشغولة",3:"🟡 تنظيف",4:"⚫ صيانة"}
    cols=st.columns(8)
    for i,r in rooms_df.iterrows():
        room_id=r['id']
        status=r['status_code']
        if cols[i%8].button(f"غرفة {room_id}\n{colors.get(status,'')}"):
            st.session_state.selected_room=room_id

    if "selected_room" in st.session_state:
        room=st.session_state.selected_room
        st.divider()
        st.subheader(f"معلومات الغرفة {room}")
        status=rooms_df[rooms_df['id']==room]['status_code'].values[0]

        # غرفة مشغولة
        if status==1:
            data=pd.read_sql_query(
                "SELECT * FROM bookings WHERE room_id=? ORDER BY id DESC LIMIT 1",
                conn,
                params=(room,)
            )
            if not data.empty:
                d=data.iloc[0]
                st.write("👤 الاسم:",d['name'])
                st.write("📞 الهاتف:",d['phone'])
                st.write("📅 الأيام:",d['stay_days'])
                st.write("💰 السعر الكلي:",d['total_price'])
                st.write("💵 المدفوع:",d['paid_amount'])
                st.write("👷 العامل:",d['worker'])
                st.divider()
                add_days=st.number_input("تمديد الأيام",0)
                if st.button("تمديد الإقامة"):
                    conn.execute(
                        "UPDATE bookings SET stay_days=stay_days+? WHERE id=?",
                        (add_days,d['id'])
                    )
                    conn.commit()
                    st.success("تم التمديد")
                    st.rerun()
                add_pay=st.number_input("مبلغ إضافي",0.0)
                if st.button("تسجيل دفع"):
                    conn.execute(
                        "UPDATE bookings SET paid_amount=paid_amount+? WHERE id=?",
                        (add_pay,d['id'])
                    )
                    conn.commit()
                    st.success("تم تسجيل الدفع")
                    st.rerun()
                if st.button("طباعة فاتورة"):
                    pdf=FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial","B",16)
                    pdf.cell(0,10,"RECEIPT",0,1,"C")
                    pdf.set_font("Arial","",12)
                    pdf.cell(0,10,f"Name: {d['name']}",0,1)
                    pdf.cell(0,10,f"Room: {room}",0,1)
                    pdf.cell(0,10,f"Days: {d['stay_days']}",0,1)
                    pdf.cell(0,10,f"Total: {d['total_price']}",0,1)
                    pdf.cell(0,10,f"Paid: {d['paid_amount']}",0,1)
                    file="room_invoice.pdf"
                    pdf.output(file)
                    with open(file,"rb") as f:
                        st.download_button("تحميل الفاتورة",f,file_name=file)
                if st.button("🚪 إخراج الزبون"):
                    conn.execute(
                        "UPDATE rooms SET status_code=0,guest_name='' WHERE id=?",
                        (room,)
                    )
                    conn.commit()
                    st.success("تم إخلاء الغرفة")
                    st.rerun()

        # غرفة شاغرة
        elif status==0:
            st.success("الغرفة شاغرة")
            name=st.text_input("اسم الزبون")
            phone=st.text_input("الهاتف")
            days=st.number_input("الأيام",1)
            total=st.number_input("السعر الكلي")
            paid=st.number_input("المدفوع")
            if st.button("تسجيل الزبون"):
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
                st.rerun()

        elif status==3:
            st.warning("الغرفة قيد التنظيف")
        elif status==4:
            st.error("الغرفة في الصيانة")

# -----------------
# الأرشيف
# -----------------
elif choice=="الأرشيف":
    df=pd.read_sql_query("SELECT * FROM bookings ORDER BY id DESC",conn)
    s=st.text_input("بحث")
    if s:
        df=df[
            df['name'].str.contains(s,na=False) |
            df['phone'].str.contains(s,na=False)
        ]
    st.dataframe(df,use_container_width=True)

# -----------------
# الصيانة
# -----------------
elif choice=="الصيانة":
    room=st.selectbox("الغرفة",rooms_df['id'])
    status=st.radio("الحالة",["جاهزة","تنظيف","صيانة"])
    if st.button("تحديث"):
        code=0 if status=="جاهزة" else 3 if status=="تنظيف" else 4
        conn.execute(
            "UPDATE rooms SET status_code=? WHERE id=?",
            (code,room)
        )
        conn.commit()
        st.success("تم التحديث")
        st.rerun()

# -----------------
# الكاسة
# -----------------
elif choice=="الكاسة":
    today=datetime.now().strftime("%Y-%m-%d")
    expected=pd.read_sql_query(
        f"SELECT SUM(paid_amount) FROM bookings WHERE worker='{st.session_state.user}' AND date='{today}'",
        conn
    ).iloc[0,0]
    expected=expected or 0
    st.info(f"المبلغ المسجل : {expected}")
    actual=st.number_input("المبلغ الحقيقي",value=float(expected))
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

# -----------------
# الإحصائيات
# -----------------
elif choice=="الإحصائيات":
    today=datetime.now().strftime("%Y-%m-%d")
    income=pd.read_sql_query(
        "SELECT SUM(paid_amount) FROM bookings WHERE date=?",
        conn,
        params=(today,)
    ).iloc[0,0]
    income=income or 0
    busy=len(rooms_df[rooms_df['status_code']==1])
    st.metric("مداخيل اليوم",income)
    st.metric("الغرف المشغولة",busy)

# -----------------
# الإدارة
# -----------------
elif choice=="الإدارة":
    if st.session_state.role!="مدير":
        st.error("مدير فقط")
    else:
        if st.button("إنشاء نسخة احتياطية"):
            file=backup()
            st.success("تم إنشاء النسخة: "+file)
        att=pd.read_sql_query("SELECT * FROM attendance",conn)
        st.dataframe(att)