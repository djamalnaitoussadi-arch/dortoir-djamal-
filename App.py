import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
from fpdf import FPDF
import shutil

# ---------------------
# تشفير كلمة المرور
# ---------------------
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

def check_pass(p,h):
    return hash_pass(p)==h

# ---------------------
# قاعدة البيانات
# ---------------------
def init_db():
    conn=sqlite3.connect("hotel_system.db",check_same_thread=False)
    c=conn.cursor()

    # غرف الفندق
    c.execute("""
    CREATE TABLE IF NOT EXISTS rooms(
    id INTEGER PRIMARY KEY,
    status_code INTEGER,
    guest_name TEXT)
    """)

    # الحجز والتسجيل
    c.execute("""
    CREATE TABLE IF NOT EXISTS bookings(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER,
    name TEXT,
    phone TEXT,
    stay_days INTEGER,
    night_price REAL,
    total_price REAL,
    paid_amount REAL,
    date TEXT,
    worker TEXT,
    is_phone_booking INTEGER DEFAULT 0)
    """)

    # العمال وصلاحياتهم
    c.execute("""
    CREATE TABLE IF NOT EXISTS staff(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT,
    role TEXT,
    salary_rate REAL DEFAULT 0)
    """)

    # سجل الحضور
    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    login_time TEXT,
    logout_time TEXT,
    date TEXT)
    """)

    # المصاريف
    c.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT,
    amount REAL,
    date TEXT,
    category TEXT)
    """)

    # إذا الغرف فارغة، نملأها وننشئ مدير افتراضي
    if conn.execute("SELECT count(*) FROM rooms").fetchone()[0]==0:
        for i in range(1,24):
            c.execute("INSERT INTO rooms VALUES(?,?,?)",(i,0,''))
        # مدير افتراضي
        c.execute("INSERT INTO staff(username,password,role) VALUES(?,?,?)",
                  ("admin",hash_pass("admin2026"),"مدير"))
    conn.commit()
    return conn

conn=init_db()

# ---------------------
# إنشاء فاتورة PDF
# ---------------------
def make_invoice(name,room,days,total,paid):
    pdf=FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"مرقد جمال - FACTURE / RECEIPT",0,1,"C")
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

# ---------------------
# النسخ الاحتياطي
# ---------------------
def backup():
    file="backup_"+datetime.now().strftime("%Y%m%d")+".db"
    shutil.copy("hotel_system.db",file)
    return file

# ---------------------
# تسجيل الدخول
# ---------------------
if "auth" not in st.session_state:
    st.session_state.auth=False

if not st.session_state.auth:
    st.title("🏨 مرقد جمال")
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
    st.sidebar.title("👤 مرقد جمال")
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

# ---------------------
# خريطة غرف تفاعلية كاملة
# ---------------------
if choice=="خريطة الغرف":
    st.subheader("🏨 مرقد جمال - خريطة الغرف")
    colors={
        0:"🟢 شاغرة",
        1:"🔴 مشغولة",
        2:"🔵 محجوزة عبر الهاتف",
        3:"🟡 تنظيف",
        4:"⚫ صيانة"
    }
    cols=st.columns(8)
    for i,r in rooms_df.iterrows():
        room_id=r['id']
        status=r['status_code']
        label=f"غرفة {room_id}\n{colors.get(status,'')}"
        if cols[i%8].button(label):
            st.session_state.selected_room=room_id

    if "selected_room" in st.session_state:
        room=st.session_state.selected_room
        st.divider()
        st.subheader(f"معلومات الغرفة {room}")
        status=rooms_df[rooms_df['id']==room]['status_code'].values[0]

        # -----------------------------
        # غرفة محجوزة عبر الهاتف
        # -----------------------------
        if status==2:
            data=pd.read_sql_query(
                "SELECT * FROM bookings WHERE room_id=? ORDER BY id DESC LIMIT 1",
                conn,
                params=(room,)
            )
            if not data.empty:
                d=data.iloc[0]
                st.info("💬 تم الحجز مسبقاً عبر الهاتف")
                st.write("👤 الاسم:",d['name'])
                st.write("📞 الهاتف:",d['phone'])
                st.write("📅 الأيام:",d['stay_days'])
                st.write("💵 السعر المتفق:",d['total_price'])
                st.write("👷 الموظف المسجل:",d['worker'])

                col1,col2=st.columns(2)
                if col1.button("✅ وصول الزبون"):
                    conn.execute(
                        "UPDATE rooms SET status_code=1 WHERE id=?",
                        (room,)
                    )
                    conn.commit()
                    st.success("تم تغيير الحالة إلى مشغولة 🔴")
                    st.rerun()

                if col2.button("❌ إلغاء الحجز"):
                    conn.execute(
                        "UPDATE rooms SET status_code=0, guest_name='' WHERE id=?",
                        (room,)
                    )
                    conn.execute("DELETE FROM bookings WHERE id=?", (d['id'],))
                    conn.commit()
                    st.warning("تم إلغاء الحجز وعودة الغرفة للشاغرة 🟢")
                    st.rerun()

        # -----------------------------
        # غرفة مشغولة
        # -----------------------------
        elif status==1:
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
                    pdf_file=make_invoice(d['name'],room,d['stay_days'],d['total_price'],d['paid_amount'])
                    with open(pdf_file,"rb") as f:
                        st.download_button("تحميل الفاتورة",f,file_name=pdf_file)

                if st.button("🚪 إخراج الزبون"):
                    conn.execute(
                        "UPDATE rooms SET status_code=0,guest_name='' WHERE id=?",
                        (room,)
                    )
                    conn.commit()
                    st.success("تم إخلاء الغرفة")
                    st.rerun()

        # -----------------------------
        # غرفة شاغرة أو تسجيل حجز عند وصول الزبون
        # -----------------------------
        elif status==0:
            st.success("الغرفة شاغرة")
            phone=st.text_input("📞 رقم الهاتف")
            name=st.text_input("👤 الاسم واللقب")
            days=st.number_input("📅 عدد الأيام",1)
            night_price=st.number_input("💵 سعر الليلة",value=1000.0)
            total=days*night_price
            st.info(f"المبلغ الإجمالي تلقائياً: {total} DZD")
            paid=st.number_input("💰 المدفوع (العربون)",value=0.0)
            is_phone_booking=st.checkbox("حجز عبر الهاتف (لم يصل الزبون بعد)")
            if st.button("تسجيل الزبون"):
                if not phone or not name:
                    st.error("يجب إدخال الاسم ورقم الهاتف")
                else:
                    status_code=2 if is_phone_booking else 1
                    conn.execute(
                        "UPDATE rooms SET status_code= ?, guest_name=? WHERE id=?",
                        (status_code,name,room)
                    )
                    conn.execute("""
                        INSERT INTO bookings(room_id,name,phone,stay_days,night_price,total_price,paid_amount,date,worker,is_phone_booking)
                        VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (room,name,phone,days,night_price,total,paid,datetime.now().strftime("%Y-%m-%d"),st.session_state.user,int(is_phone_booking))
                    )
                    conn.commit()
                    st.success(f"تم تسجيل الزبون. الحالة: {'محجوز عبر الهاتف' if is_phone_booking else 'مشغولة'}")
                    st.rerun()

        # -----------------------------
        # تنظيف وصيانة
        # -----------------------------
        elif status==3:
            st.warning("الغرفة قيد التنظيف")
        elif status==4:
            st.error("الغرفة في الصيانة")

# ---------------------
# الأرشيف
# ---------------------
elif choice=="الأرشيف":
    df=pd.read_sql_query("SELECT * FROM bookings ORDER BY id DESC",conn)
    s=st.text_input("بحث")
    if s:
        df=df[
            df['name'].str.contains(s,na=False) |
            df['phone'].str.contains(s,na=False)
        ]
    st.dataframe(df,use_container_width=True)

# ---------------------
# الصيانة
# ---------------------
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

# ---------------------
# الكاسة
# ---------------------
elif choice=="الكاسة":
    today=datetime.now().strftime("%Y-%m-%d")
    expected=pd.read_sql_query(
        "SELECT SUM(paid_amount) FROM bookings WHERE worker=? AND date=?",
        conn,
        params=(st.session_state.user,today)
    ).iloc[0,0] or 0
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

# ---------------------
# الإحصائيات
# ---------------------
elif choice=="الإحصائيات":
    today=datetime.now().strftime("%Y-%m-%d")
    income=pd.read_sql_query(
        "SELECT SUM(paid_amount) FROM bookings WHERE date=?",
        conn,
        params=(today,)
    ).iloc[0,0] or 0
    busy=len(rooms_df[rooms_df['status_code']==1])
    st.metric("مداخيل اليوم",income)
    st.metric("الغرف المشغولة",busy)

# ---------------------
# الإدارة وصلاحيات المدير
# ---------------------
elif choice=="الإدارة":
    if st.session_state.role!="مدير":
        st.error("مدير فقط")
    else:
        st.subheader("👷 إدارة العمال والحسابات")
        # إضافة عامل
        st.write("### إضافة عامل جديد")
        new_user=st.text_input("اسم المستخدم")
        new_pass=st.text_input("كلمة المرور",type="password")
        role=st.selectbox("الدور",["عامل","مدير"])
        salary=st.number_input("أجر الليلة / اليوم",0.0)
        if st.button("إضافة العامل"):
            if not new_user or not new_pass:
                st.error("ادخل الاسم وكلمة المرور")
            else:
                conn.execute(
                    "INSERT INTO staff(username,password,role,salary_rate) VALUES(?,?,?,?)",
                    (new_user,hash_pass(new_pass),role,salary)
                )
                conn.commit()
                st.success("تم إضافة العامل بنجاح")
                st.rerun()

        # نسخة احتياطية
        if st.button("إنشاء نسخة احتياطية"):
            file=backup()
            st.success("تم إنشاء النسخة: "+file)

        # سجل الحضور
        att=pd.read_sql_query("SELECT * FROM attendance",conn)
        st.write("### سجل الحضور")
        st.dataframe(att)

        # الحسابات الشهرية للعمال
        st.write("### الحسابات الشهرية للعمال")
        month=pd.to_datetime(datetime.now().strftime("%Y-%m"))
        bookings=pd.read_sql_query("SELECT * FROM bookings",conn)
        bookings['date']=pd.to_datetime(bookings['date'])
        bookings['month']=bookings['date'].dt.to_period('M')
        month_bookings=bookings[bookings['month']==month.to_period('M')]
        salaries=[]
        for user in month_bookings['worker'].unique():
            total=month_bookings[month_bookings['worker']==user]['paid_amount'].sum()
            salaries.append({"العامل":user,"الأجر الشهري":total})
        df_salaries=pd.DataFrame(salaries)
        st.dataframe(df_salaries)