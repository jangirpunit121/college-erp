import streamlit as st
import pandas as pd
import json, os, uuid, hashlib, shutil, zipfile, re
from datetime import datetime, date
import calendar
from pathlib import Path

st.set_page_config(page_title="College ERP — Professional", page_icon="🎓",
                   layout="wide", initial_sidebar_state="expanded")

# ============================================================
# STORAGE
# ============================================================
DATA_DIR = Path("data"); UPLOAD_DIR = DATA_DIR/"uploads"
DATA_DIR.mkdir(exist_ok=True); UPLOAD_DIR.mkdir(exist_ok=True)

FILES = {k: DATA_DIR/f"{k}.json" for k in [
    "users","students","teachers","subjects","attendance","marks","fees",
    "papers","announcements","fee_structure","courses","notices",
    "activity_log"]}

def load(key, default=None):
    if default is None:
        default = {} if key=="fee_structure" else []
    if FILES[key].exists():
        try: return json.loads(FILES[key].read_text(encoding="utf-8"))
        except: return default
    return default

def save(key, data):
    FILES[key].write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

def hpw(p): return hashlib.sha256(p.encode()).hexdigest()
def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def save_upload(f, sub):
    if f is None: return None
    d = UPLOAD_DIR/sub; d.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w\.-]", "_", f.name)
    p = d/f"{uuid.uuid4().hex[:8]}_{safe}"; p.write_bytes(f.getbuffer()); return str(p)

def send_mail(to, subj, body):
    with open(DATA_DIR/"mail_log.txt","a",encoding="utf-8") as f:
        f.write(f"[{now()}] TO:{to} | {subj} | {body}\n")

def log_activity(action, details=""):
    logs = load("activity_log")
    logs.insert(0, {"by": st.session_state.user["name"] if st.session_state.get("user") else "system",
                    "role": st.session_state.user["role"] if st.session_state.get("user") else "-",
                    "action": action, "details": details, "time": now()})
    save("activity_log", logs[:500])

# ============================================================
# SEED
# ============================================================
users = load("users")
if not any(u["role"]=="admin" for u in users):
    users.append({"id":"admin_1","username":"admin","password":hpw("admin123"),
                  "role":"admin","name":"Super Admin","email":"admin@college.edu"})
    save("users", users)

COURSES_DEFAULT = [
    {"code":"BSC","name":"B.Sc","level":"Graduation","duration":3},
    {"code":"BCOM","name":"B.Com","level":"Graduation","duration":3},
    {"code":"BA","name":"B.A","level":"Graduation","duration":3},
    {"code":"BTECH","name":"B.Tech","level":"Graduation","duration":4},
    {"code":"MSC","name":"M.Sc","level":"Post Graduation","duration":2},
    {"code":"MCOM","name":"M.Com","level":"Post Graduation","duration":2},
    {"code":"MA","name":"M.A","level":"Post Graduation","duration":2},
    {"code":"MTECH","name":"M.Tech","level":"Post Graduation","duration":2},
]
if not load("courses"): save("courses", COURSES_DEFAULT)

for k in ["users","students","teachers","subjects","attendance","marks","fees",
          "papers","announcements","courses","notices","activity_log"]:
    if not FILES[k].exists(): save(k, [] if k != "fee_structure" else {})
if not FILES["fee_structure"].exists(): save("fee_structure", {})

# ============================================================
# SESSION
# ============================================================
for k,v in {"logged_in":False,"user":None}.items():
    if k not in st.session_state: st.session_state[k]=v

def login_user(u,p):
    for x in load("users"):
        if x["username"]==u and x["password"]==hpw(p): return x
    return None

def logout():
    log_activity("Logout")
    st.session_state.logged_in=False; st.session_state.user=None; st.rerun()

def is_pg_course(course_code):
    c = next((x for x in load("courses") if x["code"]==course_code), None)
    return c and c.get("level") in ("Post Graduation","PhD")

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root {
  --ink: #172033;
  --muted: #526079;
  --line: #dbe3ef;
  --surface: #ffffff;
  --brand: #4338ca;
  --brand-2: #6366f1;
}
html, body, [class*="css"], * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
.stApp { background: linear-gradient(180deg, #f8fafc 0%, #f1f5ff 100%) !important; color: var(--ink) !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] { color: var(--ink) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem clamp(1rem, 3vw, 2.5rem) 3rem !important; max-width: 1480px; }

/* Global contrast: force readable dark text on light surfaces */
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
.stText, .stCaption, [data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
.stRadio label, .stCheckbox label, .stFileUploader label,
.stSelectbox label, .stMultiSelect label, .stTextInput label,
.stNumberInput label, .stTextArea label, .stDateInput label,
.stTimeInput label, .stSlider label, .stToggle label,
[data-testid="stMarkdownContainer"] p { color: var(--ink) !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: var(--muted) !important; }
h1, h2, h3, h4, h5, h6 { color: #111827 !important; font-weight: 800 !important; letter-spacing: -.025em; }
.main-header {
  font-size: clamp(2rem, 4vw, 2.65rem); font-weight: 900;
  background: linear-gradient(135deg, #3730a3 0%, #6d28d9 55%, #be185d 100%);
  background-clip: text; -webkit-background-clip: text;
  color: #4338ca !important; -webkit-text-fill-color: transparent;
  margin-bottom: .35rem; line-height: 1.2;
}
.sub-header { color: #526079 !important; -webkit-text-fill-color: #526079 !important; font-size: 1rem; font-weight: 500; margin-bottom: 1.5rem; }

/* Dashboard metric cards retain white text only on dark gradient */
.metric-card { background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: #fff !important; padding: 24px 20px; border-radius: 18px; box-shadow: 0 10px 28px rgba(79,70,229,.18); text-align: center; transition: transform .2s, box-shadow .2s; }
.metric-card:hover { transform: translateY(-3px); box-shadow: 0 14px 34px rgba(79,70,229,.25); }
.metric-card h2, .metric-card p, .metric-card span, .metric-card div { color: #fff !important; -webkit-text-fill-color: #fff !important; }
.metric-card h2 { margin: 0; font-size: 2.1rem; font-weight: 900; }
.metric-card p { margin: 6px 0 0; font-size: .9rem; font-weight: 600; }
.fee-card { background: linear-gradient(135deg, #3730a3 0%, #6d28d9 55%, #be185d 100%); color: #fff !important; padding: 26px; border-radius: 18px; margin: 14px 0; box-shadow: 0 10px 28px rgba(79,70,229,.18); }
.fee-card h3, .fee-card div, .fee-card span { color: #fff !important; -webkit-text-fill-color: #fff !important; }
.fee-card h3 { margin: 0 0 4px !important; }
.fee-card .fee-label { font-size: .78rem; opacity: .95; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.fee-card .fee-val { font-size: 1.55rem; font-weight: 900; margin-top: 4px; }

/* Cards, containers, tabs */
[data-testid="stVerticalBlockBorderWrapper"] { background: #fff !important; border: 1px solid var(--line) !important; border-radius: 16px !important; padding: 8px !important; box-shadow: 0 3px 12px rgba(15,23,42,.035); }
.stTabs [data-baseweb="tab-list"] { gap: 6px; background: #e8edf7; padding: 6px; border-radius: 14px; }
.stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 10px 16px; font-weight: 700; color: #334155 !important; }
.stTabs [data-baseweb="tab"] p { color: #334155 !important; }
.stTabs [aria-selected="true"] { background: #fff !important; color: #3730a3 !important; box-shadow: 0 2px 8px rgba(15,23,42,.09); }
.stTabs [aria-selected="true"] p { color: #3730a3 !important; }

/* Inputs: visible values, placeholders, and dropdown options */
.stTextInput input, .stNumberInput input, .stTextArea textarea,
.stDateInput input, .stTimeInput input,
.stSelectbox [data-baseweb="select"] > div,
.stMultiSelect [data-baseweb="select"] > div {
  background: #fff !important; border: 1.5px solid #cbd5e1 !important;
  border-radius: 10px !important; color: #172033 !important;
  -webkit-text-fill-color: #172033 !important; font-size: .94rem !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #64748b !important; -webkit-text-fill-color: #64748b !important; opacity: 1 !important; }
.stSelectbox [data-baseweb="select"] *, .stMultiSelect [data-baseweb="select"] *,
[data-baseweb="popover"] *, [role="listbox"] *, [role="option"] { color: #172033 !important; -webkit-text-fill-color: #172033 !important; }
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus { border-color: #6366f1 !important; box-shadow: 0 0 0 3px rgba(99,102,241,.13) !important; }
.stTextInput label, .stSelectbox label, .stNumberInput label, .stTextArea label,
.stDateInput label, .stTimeInput label, .stMultiSelect label, .stFileUploader label,
.stCheckbox label, .stRadio label { color: #334155 !important; font-weight: 700 !important; font-size: .83rem !important; }

/* Buttons have high contrast */
.stButton > button, .stFormSubmitButton > button { background: linear-gradient(135deg, #4338ca, #6366f1) !important; color: #fff !important; -webkit-text-fill-color: #fff !important; border: 0 !important; border-radius: 11px !important; font-weight: 750 !important; padding: 10px 18px !important; transition: transform .18s, box-shadow .18s; }
.stButton > button *, .stFormSubmitButton > button * { color: #fff !important; -webkit-text-fill-color: #fff !important; }
.stButton > button:hover, .stFormSubmitButton > button:hover { transform: translateY(-1px); box-shadow: 0 7px 18px rgba(79,70,229,.25); }
.stDownloadButton > button { background: linear-gradient(135deg, #047857, #059669) !important; color: #fff !important; -webkit-text-fill-color: #fff !important; border: 0 !important; border-radius: 11px !important; font-weight: 750 !important; }
.stDownloadButton > button * { color: #fff !important; -webkit-text-fill-color: #fff !important; }

/* Dark sidebar with readable light text */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #111827 0%, #1e1b4b 58%, #312e81 100%) !important; border-right: 1px solid rgba(255,255,255,.08); }
[data-testid="stSidebar"] * { color: #eef2ff !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #fff !important; }
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #c7d2fe !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { padding: 11px 13px !important; border-radius: 10px !important; margin: 3px 0 !important; font-weight: 650 !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover { background: rgba(255,255,255,.09) !important; }
[data-testid="stSidebar"] .stButton > button { background: rgba(255,255,255,.1) !important; border: 1px solid rgba(255,255,255,.18) !important; }

/* Alerts and expanders */
.stAlert { border-radius: 12px !important; border-left-width: 4px !important; }
.stAlert p, .stAlert span, .stAlert div { color: #172033 !important; }
.stSuccess { background: #ecfdf5 !important; } .stError { background: #fef2f2 !important; }
.stInfo { background: #eff6ff !important; } .stWarning { background: #fffbeb !important; }
.streamlit-expanderHeader { background: #f8fafc !important; border-radius: 12px !important; color: #172033 !important; font-weight: 750 !important; border: 1px solid #dbe3ef !important; padding: 12px 16px !important; }
.streamlit-expanderHeader p { color: #172033 !important; }
.streamlit-expanderContent { background: #fff !important; border: 1px solid #dbe3ef !important; border-top: none !important; border-radius: 0 0 12px 12px !important; padding: 12px !important; }
.stDataFrame { border-radius: 12px; overflow: hidden; border: 1px solid #dbe3ef; }
.role-badge { display: inline-block; padding: 6px 14px; border-radius: 24px; background: #ede9fe; color: #5b21b6 !important; -webkit-text-fill-color: #5b21b6 !important; font-size: .82rem; font-weight: 750; margin-bottom: 1rem; }
.info-card { background: #fff; border: 1px solid #dbe3ef; border-radius: 14px; padding: 16px 20px; margin: 8px 0; }
.info-card, .info-card * { color: #172033 !important; }
.info-card:hover { border-color: #a5b4fc; box-shadow: 0 5px 16px rgba(99,102,241,.09); }
hr { border: none; border-top: 1px solid #dbe3ef; margin: 1.4rem 0; }
/* Admission and profile forms: force readable foreground/background across widgets */
[data-testid="stForm"], [data-testid="stExpander"] [data-testid="stExpanderDetails"] { color: #172033 !important; }
[data-testid="stForm"] label, [data-testid="stForm"] p,
[data-testid="stExpander"] label, [data-testid="stExpander"] p,
[data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] { color: #172033 !important; }
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
[data-testid="stDateInput"] [data-baseweb="input"], [data-testid="stNumberInput"] [data-baseweb="input"] {
  background-color: #ffffff !important; color: #111827 !important;
}
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea,
[data-baseweb="select"] input, [data-baseweb="select"] span,
[data-baseweb="select"] div, [data-testid="stNumberInput"] button,
[data-testid="stDateInput"] button { color: #111827 !important; -webkit-text-fill-color: #111827 !important; }
[data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="listbox"],
[data-baseweb="popover"] ul, [data-baseweb="popover"] li { background: #ffffff !important; color: #111827 !important; }
[data-baseweb="menu"] *, [data-baseweb="listbox"] *, [role="option"] *,
[data-testid="stSelectbox"] *, [data-testid="stMultiSelect"] * { color: #111827 !important; -webkit-text-fill-color: #111827 !important; }
[data-testid="stFileUploader"] section { background: #ffffff !important; border: 1px dashed #94a3b8 !important; border-radius: 12px !important; }
[data-testid="stFileUploader"] section, [data-testid="stFileUploader"] section * { color: #334155 !important; }
[data-testid="stCheckbox"] label, [data-testid="stRadio"] label { color: #172033 !important; }
[data-testid="stDataFrame"] { background: #ffffff !important; }
[data-testid="stMetric"] { background: #ffffff; padding: 14px; border: 1px solid #dbe3ef; border-radius: 12px; }
.stMarkdown a { color: #4338ca !important; text-decoration: underline; }
@media (max-width: 768px) { .block-container { padding: 1rem .8rem 2rem !important; } .metric-card { padding: 18px 12px; } .fee-card { padding: 18px; } }


/* FINAL OVERRIDE: remove colored backgrounds throughout the ERP */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stSidebar"], [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stForm"], [data-testid="stExpander"], [data-testid="stExpanderDetails"],
.stTabs [data-baseweb="tab-list"], .stTabs [data-baseweb="tab"],
.streamlit-expanderHeader, .streamlit-expanderContent, .stAlert,
.stSuccess, .stError, .stInfo, .stWarning,
.metric-card, .fee-card, .role-badge, .info-card,
[data-testid="stMetric"], [data-testid="stDataFrame"],
[data-testid="stFileUploader"] section,
[data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="listbox"],
[data-baseweb="popover"] ul, [data-baseweb="popover"] li,
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="textarea"],
.stTextInput input, .stNumberInput input, .stTextArea textarea,
.stDateInput input, .stTimeInput input,
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button,
[data-testid="stSidebar"] .stButton > button,
[role="option"], [role="listbox"] {
  background: #ffffff !important;
  background-color: #ffffff !important;
  background-image: none !important;
  box-shadow: none !important;
}
/* Keep every label, heading, card and control readable on plain white */
.main-header, .main-header *, .metric-card, .metric-card *, .fee-card, .fee-card *,
.role-badge, .info-card, .info-card *, h1, h2, h3, h4, h5, h6,
.stMarkdown, .stMarkdown *, [data-testid="stSidebar"], [data-testid="stSidebar"] *,
.stTabs [data-baseweb="tab"], .stTabs [data-baseweb="tab"] *,
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button,
.stButton > button *, .stFormSubmitButton > button *, .stDownloadButton > button * {
  color: #172033 !important;
  -webkit-text-fill-color: #172033 !important;
}
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button,
[data-testid="stSidebar"] .stButton > button {
  border: 1px solid #cbd5e1 !important;
  border-radius: 10px !important;
}
[data-testid="stSidebar"] { border-right: 1px solid #e5e7eb !important; }
[data-testid="stSidebar"] * { color: #172033 !important; -webkit-text-fill-color: #172033 !important; }
.stTabs [aria-selected="true"] { border-bottom: 2px solid #64748b !important; }
[role="option"]:hover, [data-baseweb="menu"] li:hover { background: #f3f4f6 !important; }

</style>
""", unsafe_allow_html=True)

# ============================================================
# LOGIN
# ============================================================
def login_page():
    st.markdown('<div style="height:50px"></div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns([1,1.4,1])
    with c2:
        st.markdown('<div class="main-header" style="text-align:center">🎓 College ERP</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header" style="text-align:center">Complete Academic & Administration Portal</div>', unsafe_allow_html=True)
        st.markdown('<div style="height:25px"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### 🔐 Sign In")
            role = st.selectbox("Role",["Admin","Teacher","Student"], key="login_role")
            u = st.text_input("Username / Email", key="login_user")
            p = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login →", use_container_width=True, type="primary"):
                x = login_user(u,p)
                if x and x["role"].lower()==role.lower():
                    st.session_state.logged_in=True; st.session_state.user=x
                    log_activity("Login", f"{x['role']}")
                    st.rerun()
                else: st.error("Invalid credentials or wrong role.")
            st.markdown("---")
            st.caption("🔑 Demo: `admin` / `admin123`")

# ============================================================
# ADMIN DASHBOARD
# ============================================================
def admin_dashboard():
    try:
        students = load("students"); teachers = load("teachers")
        subjects = load("subjects"); fees = load("fees"); courses = load("courses")
    except Exception as e:
        st.error(f"Error: {e}"); return
    total_paid = sum(f["amount"] for f in fees) if fees else 0
    total_pending = 0
    fs = load("fee_structure")
    for s in students:
        sf = s.get("fee",{})
        fr = fs.get(f"{s['course']}|{s['semester']}", {})
        payable = sf.get("payable", fr.get("payable", fr.get("total",0)-fr.get("discount",0)))
        paid = sum(f["amount"] for f in fees if f["student_id"]==s["id"])
        total_pending += max(payable-paid, 0)
    c1,c2,c3,c4 = st.columns(4)
    for col,ico,val,label in [(c1,"👥",len(students),"Students"),(c2,"👨‍🏫",len(teachers),"Teachers"),
                              (c3,"💰",f"₹{total_paid:,}","Fee Collected"),(c4,"⏳",f"₹{total_pending:,}","Fee Pending")]:
        col.markdown(f'<div class="metric-card"><h2>{ico} {val}</h2><p>{label}</p></div>', unsafe_allow_html=True)
    st.markdown("---")
    c1,c2 = st.columns([2,1])
    with c1:
        st.subheader("📢 Announcements")
        ann = load("announcements") or []
        with st.form("ann_f"):
            t = st.text_input("Title"); b = st.text_area("Message")
            if st.form_submit_button("Post Announcement", type="primary"):
                if t and b:
                    ann.insert(0,{"title":t,"body":b,"by":st.session_state.user["name"],"time":now()})
                    save("announcements", ann); log_activity("Announcement", t)
                    st.success("Posted!"); st.rerun()
        for a in ann[:5]:
            st.info(f"**{a.get('title','-')}** — {a.get('body','-')}  \n_{a.get('by','-')} • {a.get('time','-')}_")
    with c2:
        st.subheader("📊 Quick Stats")
        st.markdown(f"""
        <div class="info-card"><div style="font-size:.8rem;color:#64748b;font-weight:700">TOTAL COURSES</div>
        <div style="font-size:1.8rem;font-weight:900;color:#4f46e5">{len(courses)}</div></div>
        <div class="info-card"><div style="font-size:.8rem;color:#64748b;font-weight:700">SUBJECTS</div>
        <div style="font-size:1.8rem;font-weight:900;color:#7c3aed">{len(subjects)}</div></div>
        <div class="info-card"><div style="font-size:.8rem;color:#64748b;font-weight:700">PAPERS</div>
        <div style="font-size:1.8rem;font-weight:900;color:#db2777">{len(load('papers'))}</div></div>
        """, unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("🕐 Recent Activity")
    logs = load("activity_log")[:10]
    if logs:
        for l in logs:
            st.caption(f"**{l['by']}** ({l['role']}) — {l['action']} _{l['time']}_")
    else:
        st.info("No activity yet.")

# ============================================================
# ADMISSION
# ============================================================
def admin_admission():
    st.subheader("📝 New Student Admission")
    courses = load("courses"); subjects = load("subjects"); fs = load("fee_structure")
    c1,c2,c3 = st.columns(3)
    course_sel = c1.selectbox("Course *", [f"{c['code']} - {c['name']} ({c['level']})" for c in courses], key="adm_course")
    sem = c2.selectbox("Current Semester *", list(range(1,9)), key="adm_sem")
    batch = c3.text_input("Batch", "2025-2027", key="adm_batch")
    course_code = course_sel.split(" - ")[0]
    pg_course = is_pg_course(course_code)
    fee_key = f"{course_code}|{sem}"
    default_total = 0; default_disc = 0; default_remark = ""
    if fee_key in fs:
        f = fs[fee_key]
        default_total = f["total"]; default_disc = f.get("discount", 0); default_remark = f.get("remark", "")
    st.markdown("### 💰 Fee & Discount (Student-Specific)")
    with st.container(border=True):
        c1,c2,c3 = st.columns(3)
        adm_total = c1.number_input("Total Fee (₹) *", 0, 1000000, int(default_total), step=1000, key="adm_fee_total")
        adm_disc = c2.number_input("Discount (₹) *", 0, 1000000, int(default_disc), step=500, key="adm_fee_disc")
        adm_payable = adm_total - adm_disc
        c3.markdown(f"<div style='padding-top:32px;color:#16a34a;font-weight:900;font-size:1.4rem'>Payable: ₹{adm_payable}</div>", unsafe_allow_html=True)
        adm_disc_remark = st.text_input("Discount Remark / Reason *", value=default_remark,
                                        placeholder="Merit scholarship / Sports quota / Sibling discount",
                                        key="adm_fee_remark")
        c1,c2 = st.columns(2)
        adm_disc_by = c1.text_input("Discount Applied By *", value=st.session_state.user["name"], key="adm_fee_by")
        adm_payment_plan = c2.selectbox("Payment Plan", ["Full Payment", "Installments (2)", "Installments (3)", "Installments (4)"], key="adm_fee_plan")
        if fee_key not in fs:
            st.warning("⚠️ No fee structure set for this course+semester. Default values used.")
    st.markdown("---")
    with st.expander("🧑 Personal Details", expanded=True):
        c1,c2,c3 = st.columns(3)
        name=c1.text_input("Full Name *", key="adm_name")
        email=c2.text_input("Email *", key="adm_email")
        phone=c3.text_input("Phone *", key="adm_phone")
        c1,c2,c3 = st.columns(3)
        alt_phone=c1.text_input("Alternate Phone", key="adm_altphone")
        dob=c2.date_input("Date of Birth *", date(2005,1,1), key="adm_dob")
        gender=c3.selectbox("Gender *",["Male","Female","Other"], key="adm_gender")
        c1,c2,c3 = st.columns(3)
        marital=c1.selectbox("Marital Status *",["Single","Married","Divorced","Widowed"], key="adm_marital")
        caste=c2.selectbox("Caste *",["General","OBC","SC","ST","EWS","Other"], key="adm_caste")
        subcaste=c3.text_input("Sub-Caste", key="adm_subcaste")
        c1,c2,c3 = st.columns(3)
        religion=c1.text_input("Religion", key="adm_religion")
        nationality=c2.text_input("Nationality", "Indian", key="adm_nationality")
        blood=c3.selectbox("Blood Group",["A+","A-","B+","B-","O+","O-","AB+","AB-","Unknown"], key="adm_blood")
        c1,c2,c3 = st.columns(3)
        aadhaar_no=c1.text_input("Aadhaar Number", key="adm_aadhaar_no")
        category_cert=c2.text_input("Category Certificate No.", key="adm_cat_cert")
        disability=c3.selectbox("Disability",["No","Yes - Locomotor","Yes - Visual","Yes - Hearing","Yes - Other"], key="adm_disability")
    with st.expander("📍 Address Details", expanded=False):
        st.markdown("**Permanent Address**")
        c1,c2,c3 = st.columns(3)
        p_street=c1.text_input("Street / House No.", key="adm_p_street")
        p_city=c2.text_input("City / Village", key="adm_p_city")
        p_district=c3.text_input("District", key="adm_p_dist")
        c1,c2,c3 = st.columns(3)
        p_state=c1.text_input("State", key="adm_p_state")
        p_pin=c2.text_input("PIN Code", key="adm_p_pin")
        p_country=c3.text_input("Country", "India", key="adm_p_country")
        same_as_perm = st.checkbox("Current address same as permanent", value=True, key="adm_same_addr")
        if not same_as_perm:
            st.markdown("**Current Address**")
            c1,c2,c3 = st.columns(3)
            c_street=c1.text_input("Street / House No.", key="adm_c_street")
            c_city=c2.text_input("City / Village", key="adm_c_city")
            c_district=c3.text_input("District", key="adm_c_dist")
            c1,c2,c3 = st.columns(3)
            c_state=c1.text_input("State", key="adm_c_state")
            c_pin=c2.text_input("PIN Code", key="adm_c_pin")
            c_country=c3.text_input("Country", "India", key="adm_c_country")
        else:
            c_street, c_city, c_district = p_street, p_city, p_district
            c_state, c_pin, c_country = p_state, p_pin, p_country
    with st.expander("👨‍👩‍👦 Family & Guardian Details", expanded=False):
        c1,c2,c3 = st.columns(3)
        fname=c1.text_input("Father's Name", key="adm_father")
        foccup=c2.text_input("Father's Occupation", key="adm_f_occup")
        fphone=c3.text_input("Father's Phone", key="adm_f_phone")
        c1,c2,c3 = st.columns(3)
        mname=c1.text_input("Mother's Name", key="adm_mother")
        moccup=c2.text_input("Mother's Occupation", key="adm_m_occup")
        mphone=c3.text_input("Mother's Phone", key="adm_m_phone")
        c1,c2,c3 = st.columns(3)
        gname=c1.text_input("Guardian Name", key="adm_guardian")
        grelation=c2.text_input("Guardian Relation", key="adm_g_relation")
        gphone=c3.text_input("Guardian Phone", key="adm_g_phone")
        c1,c2,c3 = st.columns(3)
        family_income=c1.text_input("Annual Family Income (₹)", key="adm_f_income")
        siblings=c2.number_input("No. of Siblings", 0, 20, 0, key="adm_siblings")
        first_gen=c3.selectbox("First Generation Learner?",["No","Yes"], key="adm_first_gen")
    with st.expander("📘 10th Details", expanded=True):
        c1,c2,c3 = st.columns(3)
        t_board=c1.text_input("Board *", key="adm_t_board")
        t_year=c2.text_input("Passing Year *", key="adm_t_year")
        t_school=c3.text_input("School Name", key="adm_t_school")
        c1,c2,c3 = st.columns(3)
        t_obtained=c1.number_input("Marks Obtained *", 0, 1000, 0, key="adm_t_ob")
        t_total=c2.number_input("Total Marks *", 1, 1000, 500, key="adm_t_tot")
        t_pct = round((t_obtained/t_total*100), 2) if t_total>0 else 0.0
        c3.markdown(f"<div style='padding-top:32px;color:#4f46e5;font-weight:900;font-size:1.2rem'>📊 {t_pct}%</div>", unsafe_allow_html=True)
        t_doc=st.file_uploader("10th Marksheet *", type=["pdf","jpg","png"], key="adm_t_doc")
    with st.expander("📗 12th Details", expanded=True):
        c1,c2,c3 = st.columns(3)
        tw_board=c1.text_input("Board *", key="adm_tw_board")
        tw_year=c2.text_input("Passing Year *", key="adm_tw_year")
        tw_school=c3.text_input("School Name", key="adm_tw_school")
        c1,c2,c3 = st.columns(3)
        tw_stream=c1.selectbox("Stream", ["Science","Commerce","Arts","Other"], key="adm_tw_stream")
        tw_obtained=c2.number_input("Marks Obtained *", 0, 1000, 0, key="adm_tw_ob")
        tw_total=c3.number_input("Total Marks *", 1, 1000, 500, key="adm_tw_tot")
        tw_pct = round((tw_obtained/tw_total*100), 2) if tw_total>0 else 0.0
        c1.markdown(f"<div style='color:#4f46e5;font-weight:900;font-size:1.2rem'>📊 {tw_pct}%</div>", unsafe_allow_html=True)
        tw_doc=st.file_uploader("12th Marksheet *", type=["pdf","jpg","png"], key="adm_tw_doc")
    grad_label = "🎓 Graduation Details" + (" (Compulsory for Masters)" if pg_course else " (Optional)")
    with st.expander(grad_label, expanded=pg_course):
        c1,c2,c3 = st.columns(3)
        grad_degree=c1.text_input("Degree", key="adm_g_deg")
        grad_univ=c2.text_input("University", key="adm_g_uni")
        grad_year=c3.text_input("Passing Year", key="adm_g_year")
        c1,c2,c3 = st.columns(3)
        grad_obtained=c1.number_input("Marks Obtained", 0, 1000, 0, key="adm_g_ob")
        grad_total=c2.number_input("Total Marks", 1, 1000, 500, key="adm_g_tot")
        grad_pct = round((grad_obtained/grad_total*100),2) if grad_total>0 else 0.0
        c3.markdown(f"<div style='padding-top:32px;color:#4f46e5;font-weight:900;font-size:1.2rem'>📊 {grad_pct}%</div>", unsafe_allow_html=True)
        grad_doc=st.file_uploader("Graduation Marksheet", type=["pdf","jpg","png"], key="adm_g_doc")
    with st.expander("🎓 Post-Graduation Details (if applicable)", expanded=False):
        c1,c2,c3 = st.columns(3)
        pg_degree=c1.text_input("PG Degree", key="adm_pg_deg")
        pg_univ=c2.text_input("University", key="adm_pg_uni")
        pg_year=c3.text_input("Passing Year", key="adm_pg_year")
        c1,c2,c3 = st.columns(3)
        pg_obtained=c1.number_input("Marks Obtained", 0, 1000, 0, key="adm_pg_ob")
        pg_total=c2.number_input("Total Marks", 1, 1000, 500, key="adm_pg_tot")
        pg_pct = round((pg_obtained/pg_total*100),2) if pg_total>0 else 0.0
        c3.markdown(f"<div style='padding-top:32px;color:#4f46e5;font-weight:900;font-size:1.2rem'>📊 {pg_pct}%</div>", unsafe_allow_html=True)
        pg_doc=st.file_uploader("PG Marksheet", type=["pdf","jpg","png"], key="adm_pg_doc")
    with st.expander("📄 Documents Upload", expanded=False):
        c1,c2,c3 = st.columns(3)
        photo=c1.file_uploader("Photo *", type=["jpg","png","jpeg"], key="adm_photo")
        sign=c2.file_uploader("Signature *", type=["jpg","png","jpeg"], key="adm_sign")
        aadhar_doc=c3.file_uploader("Aadhaar Card *", type=["pdf","jpg","png"], key="adm_aadhar")
        c1,c2,c3 = st.columns(3)
        domicile=c1.file_uploader("Domicile Certificate", type=["pdf","jpg","png"], key="adm_domicile")
        caste_doc=c2.file_uploader("Caste Certificate", type=["pdf","jpg","png"], key="adm_caste_doc")
        income_doc=c3.file_uploader("Income Certificate", type=["pdf","jpg","png"], key="adm_income_doc")
        c1,c2,c3 = st.columns(3)
        tc=c1.file_uploader("Transfer Certificate", type=["pdf","jpg","png"], key="adm_tc")
        migration=c2.file_uploader("Migration Certificate", type=["pdf","jpg","png"], key="adm_migration")
        medical=c3.file_uploader("Medical Certificate", type=["pdf","jpg","png"], key="adm_medical")
        c1,c2,c3 = st.columns(3)
        sports_cert=c1.file_uploader("Sports Certificate", type=["pdf","jpg","png"], key="adm_sports")
        gap_cert=c2.file_uploader("Gap Year Certificate", type=["pdf","jpg","png"], key="adm_gap")
        other_doc=c3.file_uploader("Any Other Document", type=["pdf","jpg","png"], key="adm_other")
    with st.expander("🏥 Medical & Emergency", expanded=False):
        c1,c2,c3 = st.columns(3)
        allergies=c1.text_input("Known Allergies", key="adm_allergies")
        chronic=c2.text_input("Chronic Illness", key="adm_chronic")
        medications=c3.text_input("Current Medications", key="adm_meds")
        c1,c2,c3 = st.columns(3)
        emergency_name=c1.text_input("Emergency Contact Name", key="adm_em_name")
        emergency_relation=c2.text_input("Relation", key="adm_em_relation")
        emergency_phone=c3.text_input("Emergency Phone", key="adm_em_phone")
    with st.expander("🏫 Previous School/College", expanded=False):
        c1,c2,c3 = st.columns(3)
        prev_school=c1.text_input("Previous Institution", key="adm_prev_school")
        prev_board=c2.text_input("Board/University", key="adm_prev_board")
        prev_year=c3.text_input("Last Year Attended", key="adm_prev_year")
        prev_reason=st.text_area("Reason for Leaving", key="adm_prev_reason")
    with st.expander("🏆 Achievements & Extra-Curricular", expanded=False):
        achievements=st.text_area("Achievements", key="adm_achievements")
        hobbies=st.text_area("Hobbies & Interests", key="adm_hobbies")
        c1,c2,c3 = st.columns(3)
        ncc=c1.selectbox("NCC/NSS", ["No","NCC","NSS"], key="adm_ncc")
        scouts=c2.selectbox("Scouts & Guides", ["No","Yes"], key="adm_scouts")
        sports_level=c3.selectbox("Sports Level", ["None","School","District","State","National","International"], key="adm_sports_level")
    with st.expander("🏠 Hostel & Transport", expanded=False):
        c1,c2,c3 = st.columns(3)
        hostel_req=c1.selectbox("Hostel Required?", ["No","Yes"], key="adm_hostel")
        hostel_type=c2.selectbox("Room Type", ["N/A","Single","Double","Triple","Dormitory"], key="adm_hostel_type")
        mess_pref=c3.selectbox("Mess Preference", ["N/A","Veg","Non-Veg","Jain"], key="adm_mess")
        c1,c2,c3 = st.columns(3)
        transport_req=c1.selectbox("Transport Required?", ["No","Yes"], key="adm_transport")
        route=c2.text_input("Bus Route", key="adm_route")
        pickup_point=c3.text_input("Pickup Point", key="adm_pickup")
    with st.expander("🏦 Bank Details", expanded=False):
        c1,c2,c3 = st.columns(3)
        bank_name=c1.text_input("Bank Name", key="adm_bank")
        account_no=c2.text_input("Account Number", key="adm_acc")
        ifsc=c3.text_input("IFSC Code", key="adm_ifsc")
        c1,c2,c3 = st.columns(3)
        account_holder=c1.text_input("Account Holder Name", key="adm_acc_holder")
        branch=c2.text_input("Branch", key="adm_branch")
        upi=c3.text_input("UPI ID", key="adm_upi")
    with st.expander("📚 Enrolled Subjects", expanded=True):
        eligible = [s for s in subjects if s.get("course","")==course_code and s.get("semester")==sem]
        chosen = st.multiselect("Subjects", [f"{s['code']} - {s['name']}" for s in eligible], key="adm_subjects")
    with st.expander("🔑 Login Credentials", expanded=True):
        c1,c2 = st.columns(2)
        uname=c1.text_input("Username *", key="adm_uname")
        pwd=c2.text_input("Password *", type="password", key="adm_pwd")
    st.markdown("---")
    if st.button("✅ Admit Student", type="primary", use_container_width=True):
        errors = []
        if not name.strip(): errors.append("Name required")
        if not email.strip(): errors.append("Email required")
        if not phone.strip(): errors.append("Phone required")
        if not uname.strip(): errors.append("Username required")
        if not pwd.strip(): errors.append("Password required")
        if not photo: errors.append("Photo required")
        if not sign: errors.append("Signature required")
        if not aadhar_doc: errors.append("Aadhaar document required")
        if not t_board.strip() or not t_year.strip(): errors.append("10th Board & Year required")
        if not t_doc: errors.append("10th Marksheet required")
        if not tw_board.strip() or not tw_year.strip(): errors.append("12th Board & Year required")
        if not tw_doc: errors.append("12th Marksheet required")
        if pg_course and not grad_degree.strip(): errors.append("Graduation required for Masters")
        if any(u["username"]==uname for u in load("users")): errors.append("Username exists")
        if errors:
            st.error("⚠️ Please fix:\n- " + "\n- ".join(errors))
        else:
            sid = f"STU{len(load('students'))+1:04d}"
            codes = [s.split(" - ")[0] for s in chosen]
            students = load("students")
            students.append({
                "id":sid,"name":name,"email":email,"phone":phone,"alt_phone":alt_phone,
                "dob":str(dob),"gender":gender,"marital":marital,"caste":caste,"subcaste":subcaste,
                "religion":religion,"nationality":nationality,"blood":blood,
                "aadhaar_no":aadhaar_no,"category_cert":category_cert,"disability":disability,
                "address":{"permanent":{"street":p_street,"city":p_city,"district":p_district,"state":p_state,"pin":p_pin,"country":p_country},
                           "current":{"street":c_street,"city":c_city,"district":c_district,"state":c_state,"pin":c_pin,"country":c_country}},
                "family":{"father":fname,"father_occupation":foccup,"father_phone":fphone,
                          "mother":mname,"mother_occupation":moccup,"mother_phone":mphone,
                          "guardian":gname,"guardian_relation":grelation,"guardian_phone":gphone,
                          "income":family_income,"siblings":siblings,"first_gen":first_gen},
                "course":course_code,"course_level":("PG" if pg_course else "UG"),
                "semester":sem,"batch":batch,"subjects":codes,
                "fee":{"total":int(adm_total),"discount":int(adm_disc),"payable":int(adm_payable),
                       "remark":adm_disc_remark,"applied_by":adm_disc_by,"plan":adm_payment_plan},
                "tenth":{"board":t_board,"year":t_year,"school":t_school,"obtained":t_obtained,"total":t_total,"pct":t_pct,"doc":save_upload(t_doc,"docs")},
                "twelfth":{"board":tw_board,"year":tw_year,"school":tw_school,"stream":tw_stream,"obtained":tw_obtained,"total":tw_total,"pct":tw_pct,"doc":save_upload(tw_doc,"docs")},
                "graduation":{"degree":grad_degree,"univ":grad_univ,"year":grad_year,"obtained":grad_obtained,"total":grad_total,"pct":grad_pct,"doc":save_upload(grad_doc,"docs")},
                "pg":{"degree":pg_degree,"univ":pg_univ,"year":pg_year,"obtained":pg_obtained,"total":pg_total,"pct":pg_pct,"doc":save_upload(pg_doc,"docs")},
                "docs":{"photo":save_upload(photo,"docs"),"signature":save_upload(sign,"docs"),
                        "aadhar":save_upload(aadhar_doc,"docs"),"domicile":save_upload(domicile,"docs"),
                        "caste":save_upload(caste_doc,"docs"),"income":save_upload(income_doc,"docs"),
                        "tc":save_upload(tc,"docs"),"migration":save_upload(migration,"docs"),
                        "medical":save_upload(medical,"docs"),"sports":save_upload(sports_cert,"docs"),
                        "gap":save_upload(gap_cert,"docs"),"other":save_upload(other_doc,"docs")},
                "medical":{"allergies":allergies,"chronic":chronic,"medications":medications,
                           "emergency_name":emergency_name,"emergency_relation":emergency_relation,"emergency_phone":emergency_phone},
                "previous":{"school":prev_school,"board":prev_board,"year":prev_year,"reason":prev_reason},
                "achievements":achievements,"hobbies":hobbies,"ncc":ncc,"scouts":scouts,"sports_level":sports_level,
                "hostel":{"required":hostel_req,"type":hostel_type,"mess":mess_pref},
                "transport":{"required":transport_req,"route":route,"pickup":pickup_point},
                "bank":{"name":bank_name,"account_no":account_no,"ifsc":ifsc,"holder":account_holder,"branch":branch,"upi":upi},
                "admitted":now()
            })
            save("students", students)
            users = load("users")
            users.append({"id":f"u_{sid}","username":uname,"password":hpw(pwd),
                          "role":"student","name":name,"email":email,"ref":sid})
            save("users", users)
            send_mail(email,"Admission Confirmed",f"Welcome {name}!")
            log_activity("Admitted", f"{sid} — {name}")
            st.success(f"✅ Student {sid} admitted. Username: `{uname}`")
            for k in list(st.session_state.keys()):
                if k.startswith("adm_"): del st.session_state[k]
            st.rerun()

# ============================================================
# STUDENT PROFILES: VIEW / EDIT / DELETE
# ============================================================
def admin_students():
    st.subheader("👨‍🎓 Student Profiles")
    students = load("students")
    if not students:
        st.info("Abhi koi student admission nahi hua hai. Pehle Admission section se student add karein.")
        return

    q = st.text_input("🔎 Search by student name, ID, email, or phone", key="student_search")
    filtered = [x for x in students if q.lower() in " ".join(str(x.get(k, "")) for k in ("id", "name", "email", "phone")).lower()]
    st.caption(f"Total students: {len(students)} • Showing: {len(filtered)}")
    if not filtered:
        st.warning("Koi student match nahi hua.")
        return

    labels = {f"{x.get('id','—')} | {x.get('name','Unnamed')} | {x.get('course','—')} | Sem {x.get('semester','—')}": x for x in filtered}
    chosen_label = st.selectbox("Select student profile", list(labels.keys()), key="student_profile_select")
    student = labels[chosen_label]
    sid = student.get("id")

    tab_view, tab_edit, tab_delete = st.tabs(["👁️ View Profile", "✏️ Edit Profile", "🗑️ Delete Student"])
    with tab_view:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Student ID", sid or "—")
        c2.metric("Course", student.get("course", "—"))
        c3.metric("Semester", student.get("semester", "—"))
        c4.metric("Batch", student.get("batch", "—"))
        a, b, c = st.columns(3)
        a.markdown(f"**Name**\n\n{student.get('name','—')}")
        b.markdown(f"**Email**\n\n{student.get('email','—')}")
        c.markdown(f"**Phone**\n\n{student.get('phone','—')}")
        with st.expander("Complete saved profile data", expanded=False):
            st.json(student)

    with tab_edit:
        st.info("Yahan basic profile aur academic details edit kar sakte hain. Baaki admission details/document paths ko jaisa hai waisa preserve kiya jayega.")
        courses = load("courses")
        course_codes = [x.get("code", "") for x in courses]
        if student.get("course") and student["course"] not in course_codes:
            course_codes.append(student["course"])
        with st.form(f"edit_student_{sid}"):
            c1, c2, c3 = st.columns(3)
            new_name = c1.text_input("Full Name *", value=student.get("name", ""))
            new_email = c2.text_input("Email *", value=student.get("email", ""))
            new_phone = c3.text_input("Phone *", value=student.get("phone", ""))
            c1, c2, c3 = st.columns(3)
            new_alt_phone = c1.text_input("Alternate Phone", value=student.get("alt_phone", ""))
            new_dob = c2.text_input("Date of Birth (YYYY-MM-DD)", value=str(student.get("dob", "")))
            genders = ["Male", "Female", "Other"]
            old_gender = student.get("gender", "Male")
            new_gender = c3.selectbox("Gender", genders, index=genders.index(old_gender) if old_gender in genders else 0)
            c1, c2, c3 = st.columns(3)
            new_course = c1.selectbox("Course", course_codes, index=course_codes.index(student.get("course")) if student.get("course") in course_codes else 0)
            new_semester = c2.selectbox("Current Semester", list(range(1, 9)), index=max(0, min(7, int(student.get("semester", 1) or 1)-1)))
            new_batch = c3.text_input("Batch", value=str(student.get("batch", "")))
            c1, c2 = st.columns(2)
            new_caste = c1.text_input("Caste", value=str(student.get("caste", "")))
            new_blood = c2.text_input("Blood Group", value=str(student.get("blood", "")))
            save_edit = st.form_submit_button("💾 Save Profile Changes", type="primary", use_container_width=True)
        if save_edit:
            if not new_name.strip() or not new_email.strip() or not new_phone.strip():
                st.error("Name, email aur phone required hain.")
            elif any(x.get("id") != sid and x.get("email", "").lower() == new_email.strip().lower() for x in students):
                st.error("Ye email kisi aur student ke profile me already use ho raha hai.")
            else:
                updated = []
                for x in students:
                    if x.get("id") == sid:
                        x = dict(x)
                        x.update({"name": new_name.strip(), "email": new_email.strip(), "phone": new_phone.strip(),
                                  "alt_phone": new_alt_phone.strip(), "dob": new_dob.strip(), "gender": new_gender,
                                  "course": new_course, "semester": int(new_semester), "batch": new_batch.strip(),
                                  "caste": new_caste.strip(), "blood": new_blood.strip()})
                        x["course_level"] = "PG" if is_pg_course(new_course) else "UG"
                    updated.append(x)
                save("students", updated)
                users = load("users")
                for u in users:
                    if u.get("role") == "student" and u.get("ref") == sid:
                        u["name"] = new_name.strip(); u["email"] = new_email.strip()
                save("users", users)
                log_activity("Student profile updated", f"{sid} — {new_name.strip()}")
                st.success("Student profile update ho gayi.")
                st.rerun()

    with tab_delete:
        st.warning(f"Student **{student.get('name','—')} ({sid})** ko delete karne par uska student login aur related fee/marks/attendance records bhi delete honge. Uploaded documents disk se automatically remove nahi honge.")
        confirm = st.checkbox("Main confirm karta/karti hoon ki is student ko delete karna hai.", key=f"confirm_delete_{sid}")
        if st.button("🗑️ Permanently Delete Student", type="primary", disabled=not confirm, key=f"delete_student_{sid}"):
            save("students", [x for x in students if x.get("id") != sid])
            save("users", [u for u in load("users") if not (u.get("role") == "student" and u.get("ref") == sid)])
            for key in ("fees", "attendance", "marks"):
                rows = load(key)
                kept = [r for r in rows if r.get("student_id") != sid and r.get("student") != sid and r.get("student_id") != f"u_{sid}"]
                save(key, kept)
            log_activity("Student deleted", f"{sid} — {student.get('name','')}")
            st.success(f"Student {sid} delete kar diya gaya.")
            st.rerun()


# ============================================================
# TEACHERS
# ============================================================
def admin_teachers():
    st.subheader("👨‍🏫 Manage Teachers")
    subjects = load("subjects")
    tab1, tab2 = st.tabs(["➕ Add Teacher", "📋 All Teachers"])
    with tab1:
        with st.form("tea_add", clear_on_submit=True):
            c1,c2,c3 = st.columns(3)
            name=c1.text_input("Name *"); email=c2.text_input("Email *"); phone=c3.text_input("Phone")
            subj_names=[f"{s['course']}-{s['semester']} | {s['code']} - {s['name']}" for s in subjects]
            chosen = st.multiselect("Subjects Taught", subj_names)
            c1,c2 = st.columns(2)
            uname=c1.text_input("Username *"); pwd=c2.text_input("Password *", type="password")
            if st.form_submit_button("Add Teacher", type="primary"):
                if not (name and email and uname and pwd):
                    st.error("Fill required fields."); return
                if any(u["username"]==uname for u in load("users")):
                    st.error("Username exists."); return
                tid=f"TEA{len(load('teachers'))+1:04d}"
                codes=[s.split(" | ")[1].split(" - ")[0] for s in chosen]
                teachers=load("teachers")
                teachers.append({"id":tid,"name":name,"email":email,"phone":phone,"subjects":codes})
                save("teachers", teachers)
                users=load("users")
                users.append({"id":f"u_{tid}","username":uname,"password":hpw(pwd),
                              "role":"teacher","name":name,"email":email,"ref":tid})
                save("users", users)
                log_activity("Added teacher", f"{tid} — {name}")
                st.success(f"✅ Teacher {tid} added."); st.rerun()
    with tab2:
        teachers = load("teachers")
        if not teachers: st.info("No teachers yet."); return
        for t in teachers:
            with st.container(border=True):
                c1,c2,c3 = st.columns([4,1,1])
                c1.markdown(f"**{t['id']} — {t['name']}**")
                c1.caption(f"📧 {t['email']} • 📞 {t.get('phone','-')}")
                c1.caption(f"📚 Subjects: {', '.join(t.get('subjects',[])) or '-'}")
                if c2.button("✏️ Edit", key=f"edit_{t['id']}", use_container_width=True):
                    st.session_state[f"editing_teacher_{t['id']}"] = True
                if c3.button("🗑️ Delete", key=f"del_{t['id']}", use_container_width=True):
                    save("teachers", [x for x in teachers if x["id"]!=t["id"]])
                    u=load("users"); save("users",[x for x in u if x.get("ref")!=t["id"]])
                    log_activity("Deleted teacher", t['id'])
                    st.success("Deleted"); st.rerun()
            if st.session_state.get(f"editing_teacher_{t['id']}"):
                with st.container(border=True):
                    st.markdown(f"##### ✏️ Editing: {t['name']}")
                    c1,c2,c3 = st.columns(3)
                    n=c1.text_input("Name", t["name"], key=f"en_{t['id']}")
                    e=c2.text_input("Email", t["email"], key=f"ee_{t['id']}")
                    ph=c3.text_input("Phone", t.get("phone",""), key=f"ep_{t['id']}")
                    subj_names=[f"{s['course']}-{s['semester']} | {s['code']} - {s['name']}" for s in subjects]
                    current = [x for x in subj_names if x.split(" | ")[1].split(" - ")[0] in t.get("subjects",[])]
                    chosen = st.multiselect("Subjects", subj_names, default=current, key=f"es_{t['id']}")
                    c1,c2 = st.columns(2)
                    if c1.button("💾 Save", key=f"sv_{t['id']}", use_container_width=True, type="primary"):
                        codes=[s.split(" | ")[1].split(" - ")[0] for s in chosen]
                        for x in teachers:
                            if x["id"]==t["id"]:
                                x.update({"name":n,"email":e,"phone":ph,"subjects":codes})
                        save("teachers", teachers)
                        log_activity("Updated teacher", t['id'])
                        st.session_state[f"editing_teacher_{t['id']}"] = False
                        st.success("Updated"); st.rerun()
                    if c2.button("✖️ Cancel", key=f"cx_{t['id']}", use_container_width=True):
                        st.session_state[f"editing_teacher_{t['id']}"] = False; st.rerun()

# ============================================================
# COURSES
# ============================================================
def admin_courses():
    st.subheader("🎓 Courses")
    with st.form("crs_f", clear_on_submit=True):
        c1,c2,c3,c4 = st.columns(4)
        code=c1.text_input("Code *"); name=c2.text_input("Name *")
        level=c3.selectbox("Level",["Graduation","Post Graduation","Diploma","PhD"])
        duration=c4.number_input("Duration (years)", 1, 6, 3)
        if st.form_submit_button("Add Course", type="primary"):
            if code and name:
                crs=load("courses")
                if any(c["code"]==code for c in crs): st.error("Code exists.")
                else:
                    crs.append({"code":code,"name":name,"level":level,"duration":duration})
                    save("courses", crs); log_activity("Added course", code)
                    st.success("Added!"); st.rerun()
    df = pd.DataFrame(load("courses"))
    if not df.empty: st.dataframe(df, use_container_width=True)

# ============================================================
# SUBJECTS
# ============================================================
def admin_subjects():
    st.subheader("📚 Manage Subjects")
    courses = load("courses")
    with st.form("sub_f", clear_on_submit=True):
        c1,c2,c3,c4 = st.columns(4)
        course = c1.selectbox("Course", [c["code"] for c in courses])
        sem = c2.selectbox("Semester", list(range(1,9)))
        code = c3.text_input("Code *"); name = c4.text_input("Name *")
        if st.form_submit_button("Add Subject", type="primary"):
            if code and name:
                subs=load("subjects")
                if any(s["code"]==code and s["course"]==course for s in subs):
                    st.error("Code exists for this course.")
                else:
                    subs.append({"code":code,"name":name,"course":course,"semester":sem})
                    save("subjects", subs); st.success("Added!"); st.rerun()
    df = pd.DataFrame(load("subjects"))
    if not df.empty: st.dataframe(df, use_container_width=True)

# ============================================================
# FEE STRUCTURE
# ============================================================
def admin_fee_structure():
    st.subheader("💰 Fee Structure")
    courses = load("courses"); fs = load("fee_structure")
    tab1, tab2 = st.tabs(["➕ Add / Update Fee", "📋 All Fee Structures"])
    with tab1:
        with st.form("fs_f"):
            c1,c2 = st.columns(2)
            course = c1.selectbox("Course", [c["code"] for c in courses], key="fs_course")
            sem = c2.selectbox("Semester", list(range(1,9)), key="fs_sem")
            st.markdown("#### 💵 Fee Details")
            c1,c2 = st.columns(2)
            total = c1.number_input("Total Fee (₹)", min_value=0, value=50000, step=1000, key="fs_total")
            discount = c2.number_input("Default Discount (₹)", min_value=0, value=0, step=500, key="fs_disc")
            payable = total - discount
            st.markdown(f"<div style='background:#ede9fe;padding:12px;border-radius:10px;color:#6d28d9;font-weight:800;font-size:1.1rem'>💳 Payable Amount: ₹{payable}</div>", unsafe_allow_html=True)
            remark = st.text_input("Discount Remark", key="fs_remark")
            if st.form_submit_button("💾 Save Fee Structure", type="primary"):
                fs[f"{course}|{sem}"] = {"total":int(total),"discount":int(discount),
                                         "payable":int(payable),"remark":remark,
                                         "applied_by":st.session_state.user["name"],"time":now()}
                save("fee_structure", fs)
                log_activity("Fee structure", f"{course} Sem {sem}: ₹{payable}")
                st.success(f"✅ {course} Sem {sem} saved: ₹{payable}")
                st.rerun()
    with tab2:
        if not fs: st.info("No fee structures yet."); return
        for key, v in fs.items():
            c,s = key.split("|")
            with st.container(border=True):
                cols = st.columns([3,1,1])
                cols[0].markdown(f"**{c} • Semester {s}**")
                cols[0].caption(f"Total: ₹{v['total']} | Discount: ₹{v['discount']} | **Payable: ₹{v.get('payable', v['total']-v['discount'])}**")
                cols[0].caption(f"Remark: {v.get('remark','-')} | By: {v.get('applied_by','-')}")
                if cols[1].button("✏️ Edit", key=f"fe_{key}", use_container_width=True):
                    st.session_state[f"edit_fee_{key}"] = True
                if cols[2].button("🗑️ Delete", key=f"fd_{key}", use_container_width=True):
                    del fs[key]; save("fee_structure", fs)
                    log_activity("Deleted fee structure", key)
                    st.success("Deleted"); st.rerun()
            if st.session_state.get(f"edit_fee_{key}"):
                with st.container(border=True):
                    st.markdown(f"##### ✏️ Edit: {c} Sem {s}")
                    c1,c2 = st.columns(2)
                    nt = c1.number_input("Total Fee", value=v["total"], key=f"nt_{key}")
                    nd = c2.number_input("Discount", value=v["discount"], key=f"nd_{key}")
                    npay = nt - nd
                    st.caption(f"Payable: ₹{npay}")
                    c1,c2 = st.columns(2)
                    nr = c1.text_input("Remark", v.get("remark",""), key=f"nr_{key}")
                    na = c2.text_input("Applied By", v.get("applied_by",""), key=f"na_{key}")
                    c1,c2 = st.columns(2)
                    if c1.button("💾 Save", key=f"fsave_{key}", use_container_width=True, type="primary"):
                        fs[key].update({"total":int(nt),"discount":int(nd),"payable":int(npay),
                                        "remark":nr,"applied_by":na,"time":now()})
                        save("fee_structure", fs)
                        st.session_state[f"edit_fee_{key}"] = False
                        st.success("Updated"); st.rerun()
                    if c2.button("✖️ Cancel", key=f"fcx_{key}", use_container_width=True):
                        st.session_state[f"edit_fee_{key}"] = False; st.rerun()

# ============================================================
# FEES
# ============================================================
def admin_fees():
    st.subheader("💳 Fee Payments")
    students = load("students"); fees = load("fees"); fs = load("fee_structure")
    st.markdown("### 🔎 Search Student")
    c1,c2 = st.columns(2)
    q = c1.text_input("Search by Name / ID / Email", key="fee_search")
    course_filter = c2.selectbox("Filter Course", ["All"]+[c["code"] for c in load("courses")], key="fee_course_filter")
    filtered = students
    if q: filtered = [s for s in filtered if q.lower() in (s["id"]+s["name"]+s["email"]).lower()]
    if course_filter != "All": filtered = [s for s in filtered if s["course"]==course_filter]
    if not filtered: st.info("No student found."); return
    for s in filtered:
        s_fee = s.get("fee", {})
        if s_fee.get("total"):
            total = s_fee["total"]; disc = s_fee.get("discount",0)
            payable = s_fee.get("payable", total-disc)
            remark = s_fee.get("remark",""); applied_by = s_fee.get("applied_by","")
        else:
            fr = fs.get(f"{s['course']}|{s['semester']}", {})
            total = fr.get("total",0); disc = fr.get("discount",0)
            payable = fr.get("payable", total-disc)
            remark = fr.get("remark",""); applied_by = fr.get("applied_by","")
        paid = sum(f["amount"] for f in fees if f["student_id"]==s["id"])
        due = max(payable - paid, 0)
        with st.container(border=True):
            c1,c2,c3,c4,c5 = st.columns([3,1,1,1,1])
            c1.markdown(f"**{s['id']} — {s['name']}**")
            c1.caption(f"{s['course']} • Sem {s['semester']} • {s.get('phone','-')}")
            c2.metric("Payable", f"₹{payable}")
            c3.metric("Paid", f"₹{paid}")
            c4.metric("Due", f"₹{due}")
            if c5.button("💰 Pay", key=f"pay_{s['id']}", use_container_width=True, type="primary"):
                st.session_state[f"paying_{s['id']}"] = True
            if st.session_state.get(f"paying_{s['id']}"):
                with st.container(border=True):
                    st.markdown(f"##### 💳 Record Payment for {s['name']}")
                    if remark: st.caption(f"💡 Discount: ₹{disc} — {remark} (by {applied_by})")
                    c1,c2,c3 = st.columns(3)
                    amt = c1.number_input("Amount (₹)", min_value=1, value=max(int(due),1), key=f"amt_{s['id']}")
                    mode = c2.selectbox("Mode", ["UPI","Card","NetBanking","Cash","Cheque"], key=f"mode_{s['id']}")
                    date_paid = c3.date_input("Payment Date", date.today(), key=f"dt_{s['id']}")
                    note = st.text_input("Note (optional)", key=f"note_{s['id']}")
                    c1,c2 = st.columns(2)
                    if c1.button("✅ Confirm Payment", key=f"confirm_{s['id']}", use_container_width=True, type="primary"):
                        fees = load("fees")
                        fees.append({"student_id":s["id"],"name":s["name"],"course":s["course"],
                                     "semester":s["semester"],"amount":int(amt),"mode":mode,
                                     "date":str(date_paid),"note":note,
                                     "recorded_by":st.session_state.user["name"],"time":now()})
                        save("fees", fees)
                        send_mail(s["email"],"Fee Payment Received",f"₹{amt} via {mode} on {date_paid}. {note}")
                        log_activity("Fee payment", f"{s['id']} ₹{amt}")
                        st.session_state[f"paying_{s['id']}"] = False
                        st.success(f"✅ ₹{amt} recorded for {s['name']}")
                        st.rerun()
                    if c2.button("✖️ Cancel", key=f"cancel_{s['id']}", use_container_width=True):
                        st.session_state[f"paying_{s['id']}"] = False; st.rerun()
    st.markdown("---")
    st.markdown("### 📊 All Fee Payments")
    fees = load("fees")
    if fees:
        df = pd.DataFrame(fees); st.dataframe(df, use_container_width=True)
        st.download_button("⬇️ Download CSV", df.to_csv(index=False), "fees.csv", "text/csv")
    else: st.info("No payments recorded yet.")

# ============================================================
# PAPERS
# ============================================================
def admin_papers():
    st.subheader("📄 Papers / Study Material (View Only)")
    courses = load("courses"); papers = load("papers")
    c1,c2 = st.columns(2)
    fc = c1.selectbox("Filter Course", ["All"]+[c["code"] for c in courses])
    fsem = c2.selectbox("Filter Semester", ["All"]+list(range(1,9)))
    filtered = [p for p in papers if (fc=="All" or p.get("course")==fc) and (fsem=="All" or p.get("semester")==fsem)]
    if not filtered: st.info("No papers uploaded yet."); return
    for p in filtered[::-1]:
        with st.container(border=True):
            c1,c2 = st.columns([4,1])
            c1.markdown(f"**{p['title']}**  \n`{p.get('course','-')} Sem {p.get('semester','-')}` — {p['subject']}  \n🖊️ Uploaded by **{p['by']}** • {p['time']}")
            if os.path.exists(p["file"]):
                c2.download_button("⬇️ Download", open(p["file"],"rb").read(),
                                   Path(p["file"]).name, key=p["id"])

# ============================================================
# REPORTS
# ============================================================
def admin_reports():
    st.subheader("📊 Student Search & Reports")
    students = load("students")
    q = st.text_input("🔎 Search by ID / Name / Email", key="rep_search")
    if q:
        results = [s for s in students if q.lower() in (s["id"]+s["name"]+s["email"]).lower()]
        if not results: st.warning("No student found.")
        for s in results:
            with st.expander(f"🎓 {s['id']} — {s['name']} ({s['course']} Sem {s['semester']})", expanded=True):
                st.markdown(f"**Email:** {s['email']} • **Phone:** {s.get('phone','-')}")
                st.markdown(f"**Batch:** {s.get('batch','-')} • **Caste:** {s.get('caste','-')} • **Marital:** {s.get('marital','-')}")
                st.markdown(f"**Subjects:** {', '.join(s.get('subjects',[])) or '-'}")
                s_fee = s.get("fee", {})
                if s_fee.get("total"):
                    st.markdown(f"##### 💰 Fee (Admission)")
                    st.write(f"Total: ₹{s_fee['total']} • Discount: ₹{s_fee.get('discount',0)} • Payable: ₹{s_fee.get('payable', s_fee['total']-s_fee.get('discount',0))}")
                    if s_fee.get("remark"):
                        st.caption(f"💡 {s_fee['remark']} (by {s_fee.get('applied_by','-')})")
                st.markdown("##### 📘 10th Details")
                t = s.get("tenth",{})
                st.write(f"{t.get('board','-')} • {t.get('year','-')} • {t.get('obtained','-')}/{t.get('total','-')} • **{t.get('pct','-')}%**")
                if t.get("doc") and os.path.exists(t["doc"]):
                    st.download_button("⬇️ 10th", open(t["doc"],"rb").read(), Path(t["doc"]).name, key=f"t_{s['id']}")
                st.markdown("##### 📗 12th Details")
                tw = s.get("twelfth",{})
                st.write(f"{tw.get('board','-')} • {tw.get('year','-')} • {tw.get('stream','-')} • {tw.get('obtained','-')}/{tw.get('total','-')} • **{tw.get('pct','-')}%**")
                if tw.get("doc") and os.path.exists(tw["doc"]):
                    st.download_button("⬇️ 12th", open(tw["doc"],"rb").read(), Path(tw["doc"]).name, key=f"tw_{s['id']}")
                st.markdown("##### 🎓 Graduation")
                g = s.get("graduation",{})
                st.write(f"{g.get('degree','-')} • {g.get('univ','-')} • {g.get('year','-')} • {g.get('obtained','-')}/{g.get('total','-')} • **{g.get('pct','-')}%**")
                if g.get("doc") and os.path.exists(g["doc"]):
                    st.download_button("⬇️ Grad", open(g["doc"],"rb").read(), Path(g["doc"]).name, key=f"gd_{s['id']}")
                st.markdown("##### 📄 All Documents")
                for k,v in s.get("docs",{}).items():
                    if v and os.path.exists(v):
                        st.download_button(f"⬇️ {k}", open(v,"rb").read(), Path(v).name, key=f"d_{s['id']}_{k}")
                fam = s.get("family",{})
                st.markdown("##### 👨‍👩‍👦 Family")
                st.write(f"Father: {fam.get('father','-')} • Mother: {fam.get('mother','-')} • Guardian: {fam.get('guardian','-')}")
                fr = load("fee_structure").get(f"{s['course']}|{s['semester']}", {})
                payable = s.get("fee",{}).get("payable", fr.get("payable", fr.get("total",0)-fr.get("discount",0)))
                paid = sum(f["amount"] for f in load("fees") if f["student_id"]==s["id"])
                c1,c2,c3 = st.columns(3)
                c1.metric("Payable", f"₹{payable}"); c2.metric("Paid", f"₹{paid}"); c3.metric("Due", f"₹{max(payable-paid,0)}")
                st.markdown("##### 📝 Marks")
                marks = [m for m in load("marks") if m["student_id"]==s["id"]]
                if marks: st.dataframe(pd.DataFrame(marks), use_container_width=True)
                st.markdown("##### ✅ Attendance")
                att = [a for a in load("attendance") if a["student_id"]==s["id"]]
                if att: st.dataframe(pd.DataFrame(att), use_container_width=True)
                st.markdown("##### 🧾 Payment History")
                pays = [f for f in load("fees") if f["student_id"]==s["id"]]
                if pays: st.dataframe(pd.DataFrame(pays), use_container_width=True)

# ============================================================
# BACKUP
# ============================================================
def admin_backup():
    st.subheader("💾 Backup & Recovery")
    tab1, tab2 = st.tabs(["📦 Backup", "♻️ Recovery"])
    with tab1:
        if st.button("📦 Create Backup ZIP", type="primary"):
            bname=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.make_archive(bname,"zip",DATA_DIR)
            with open(bname+".zip","rb") as f:
                st.download_button("⬇️ Download Backup", f, bname+".zip")
        st.markdown("---")
        st.markdown("#### Individual JSON Downloads")
        for k,path in FILES.items():
            if path.exists():
                st.download_button(f"⬇️ {k}.json", path.read_bytes(), f"{k}.json", key=f"bk_{k}")
    with tab2:
        st.markdown("#### Restore from Backup ZIP")
        st.warning("⚠️ This will OVERWRITE current data!")
        up = st.file_uploader("Upload backup ZIP", type=["zip"], key="rec_zip")
        if up and st.button("♻️ Restore Now", type="primary"):
            try:
                tmp = DATA_DIR/"_restore_tmp.zip"
                tmp.write_bytes(up.getbuffer())
                with zipfile.ZipFile(tmp) as z: z.extractall(DATA_DIR.parent)
                tmp.unlink(); log_activity("Restored ZIP")
                st.success("✅ Restored!"); st.rerun()
            except Exception as e: st.error(f"Restore failed: {e}")
        st.markdown("---")
        st.markdown("#### Restore Individual JSON")
        c1,c2 = st.columns(2)
        target = c1.selectbox("Target file", list(FILES.keys()))
        upj = c2.file_uploader("Upload JSON", type=["json"], key="rec_json")
        if upj and st.button("♻️ Restore JSON", type="primary"):
            try:
                FILES[target].write_bytes(upj.getbuffer())
                log_activity("Restored JSON", target)
                st.success(f"✅ {target}.json restored"); st.rerun()
            except Exception as e: st.error(f"Failed: {e}")

# ============================================================
# SETTINGS
# ============================================================
def settings_page():
    st.subheader("⚙️ Settings")
    u = st.session_state.user
    st.markdown(f"**Logged in as:** {u['name']} ({u['role'].title()})")
    st.markdown(f"**Username:** `{u['username']}`")
    st.markdown("---")
    st.markdown("### 🔑 Change Password")
    with st.form("chpw"):
        c1,c2,c3 = st.columns(3)
        old = c1.text_input("Current Password", type="password")
        new = c2.text_input("New Password", type="password")
        confirm = c3.text_input("Confirm New Password", type="password")
        if st.form_submit_button("Update Password", type="primary"):
            users = load("users")
            me = next((x for x in users if x["id"]==u["id"]), None)
            if not me: st.error("User not found"); return
            if me["password"] != hpw(old): st.error("Current password incorrect."); return
            if len(new) < 6: st.error("New password must be at least 6 characters."); return
            if new != confirm: st.error("Passwords do not match."); return
            me["password"] = hpw(new)
            save("users", users); log_activity("Password changed")
            st.success("✅ Password updated!")

# ============================================================
# TEACHER
# ============================================================
def teacher_home():
    tid = st.session_state.user["ref"]
    me = next((t for t in load("teachers") if t["id"] == tid), None)
    if not me:
        st.error("Teacher record missing")
        return

    all_subjects = load("subjects")
    assigned = [x for x in all_subjects if x.get("code") in me.get("subjects", [])]
    st.subheader(f"👋 Welcome, {me['name']}")
    st.markdown(f'<span class="role-badge">Teacher • {len(assigned)} assigned subjects</span>', unsafe_allow_html=True)
    if not assigned:
        st.warning("No subjects assigned. Ask Admin to assign your subjects.")
        return

    # Filter first by course and semester, then subject and only then students.
    courses = sorted(set(x.get("course", "") for x in assigned))
    fc1, fc2, fc3 = st.columns([1, 1, 2])
    course = fc1.selectbox("🎓 Select Course / Class", courses, key="teach_course")
    course_subjects = [x for x in assigned if x.get("course") == course]
    semesters = sorted(set(int(x.get("semester", 1)) for x in course_subjects))
    semester = fc2.selectbox("📅 Select Semester", semesters, key="teach_semester")
    sem_subjects = [x for x in course_subjects if int(x.get("semester", 1)) == int(semester)]
    subject_options = {f"{x['name']} ({x['code']})": x for x in sem_subjects}
    chosen_label = fc3.selectbox("📚 Select Subject", list(subject_options), key="teach_subject")
    subject_rec = subject_options[chosen_label]
    chosen = subject_rec["code"]
    students = [x for x in load("students")
                if x.get("course") == course and int(x.get("semester", 0) or 0) == int(semester)
                and chosen in x.get("subjects", [])]
    st.caption(f"Showing {len(students)} students • {course} / Semester {semester} • {subject_rec['name']} ({chosen})")
    tab1, tab2, tab3, tab4 = st.tabs(["👥 Students", "✅ Attendance", "📝 Marks", "📄 Papers"])

    with tab1:
        st.markdown("#### Class Students")
        if not students:
            st.info("No students enrolled in this course, semester and subject.")
        else:
            st.dataframe(pd.DataFrame([{"Student ID": x["id"], "Name": x["name"],
                                        "Email": x.get("email", "-"), "Phone": x.get("phone", "-"),
                                        "Batch": x.get("batch", "-")} for x in students]),
                         use_container_width=True, hide_index=True)
            profile_options = {f"{x['id']} — {x['name']}": x for x in students}
            selected_profile = st.selectbox("View student profile", ["Select a student"] + list(profile_options), key="teach_profile")
            if selected_profile != "Select a student":
                st.session_state["teach_profile_id"] = profile_options[selected_profile]["id"]
                student = profile_options[selected_profile]
                with st.container(border=True):
                    st.markdown(f"### 👤 {student['name']}  ")
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Student ID:** {student['id']}\n\n**Course:** {student.get('course','-')}\n\n**Semester:** {student.get('semester','-')}")
                    c2.write(f"**Email:** {student.get('email','-')}\n\n**Phone:** {student.get('phone','-')}\n\n**Batch:** {student.get('batch','-')}")
                    fam = student.get("family", {})
                    c3.write(f"**Father:** {fam.get('father','-')}\n\n**Mother:** {fam.get('mother','-')}\n\n**Gender:** {student.get('gender','-')}")

    with tab2:
        st.markdown("#### Mark Attendance")
        if not students:
            st.info("No students available for this class and subject.")
        else:
            attendance_date = st.date_input("Attendance Date", date.today(), key=f"att_date_{course}_{semester}_{chosen}")
            all_att = load("attendance")
            old_by_student = {a.get("student_id"): a for a in all_att
                              if a.get("subject") == chosen and a.get("date") == str(attendance_date)}
            attendance_rows = []
            for student in students:
                old = old_by_student.get(student["id"], {})
                c1, c2, c3 = st.columns([2, 1, 2])
                c1.write(f"**{student['name']}**  \n`{student['id']}`")
                statuses = ["Present", "Absent", "Late"]
                old_status = old.get("status", "Present")
                if old_status == "P": old_status = "Present"
                if old_status == "A": old_status = "Absent"
                if old_status not in statuses: old_status = "Present"
                status = c2.selectbox("Status", statuses, index=statuses.index(old_status),
                                      key=f"att_status_{course}_{semester}_{chosen}_{student['id']}_{attendance_date}")
                remark = c3.text_input("Remark", value=old.get("remark", ""),
                                       key=f"att_remark_{course}_{semester}_{chosen}_{student['id']}_{attendance_date}",
                                       placeholder="Optional remark")
                attendance_rows.append({"subject": chosen, "course": course, "semester": int(semester),
                                        "date": str(attendance_date), "student_id": student["id"],
                                        "name": student["name"], "status": status, "remark": remark,
                                        "by": me["name"], "time": now()})
            if st.button("💾 Save Attendance", type="primary", key=f"save_att_{course}_{semester}_{chosen}_{attendance_date}"):
                current = [a for a in all_att if not (a.get("subject") == chosen and a.get("date") == str(attendance_date)
                           and a.get("student_id") in {x["id"] for x in students})]
                current.extend(attendance_rows)
                save("attendance", current)
                log_activity("Attendance", f"{course} Semester {semester} / {chosen} on {attendance_date}")
                st.success("Attendance saved with Present / Absent / Late status and remarks.")
                st.rerun()
            if all_att:
                recent = [a for a in all_att if a.get("subject") == chosen and a.get("course", course) == course
                          and int(a.get("semester", semester) or semester) == int(semester)]
                if recent:
                    st.markdown("##### Previous attendance records")
                    st.dataframe(pd.DataFrame(recent).sort_values("date", ascending=False), use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("#### Student Profiles — Click/select a student to enter marks")
        if not students:
            st.info("No students available for marks entry.")
        else:
            mark_profiles = {f"{x['id']} — {x['name']}": x for x in students}
            chosen_student = st.selectbox("Select Student Profile", list(mark_profiles), key=f"marks_student_{course}_{semester}_{chosen}")
            student = mark_profiles[chosen_student]
            with st.container(border=True):
                st.markdown(f"### 👤 {student['name']}  ·  `{student['id']}`")
                st.caption(f"{course} • Semester {semester} • {subject_rec['name']} ({chosen})")
                marks = load("marks")
                student_marks = [m for m in marks if m.get("student_id") == student["id"] and m.get("subject") == chosen]
                if student_marks:
                    st.dataframe(pd.DataFrame(student_marks), use_container_width=True, hide_index=True)
                else:
                    st.info("No marks entered for this student and subject yet.")
                with st.form(f"mk_f_{course}_{semester}_{chosen}_{student['id']}"):
                    exam = st.selectbox("Exam / Assessment", ["Mid-Term", "End-Sem", "Quiz", "Assignment", "Practical", "Internal"])
                    c1, c2 = st.columns(2)
                    total = c1.number_input("Maximum Marks", min_value=1, max_value=1000, value=100, step=1)
                    obtained = c2.number_input("Marks Obtained", min_value=0, max_value=1000, value=0, step=1)
                    remark = st.text_input("Remark (optional)")
                    if st.form_submit_button("💾 Save Marks", type="primary"):
                        if obtained > total:
                            st.error("Marks obtained cannot exceed maximum marks.")
                        else:
                            marks = [m for m in marks if not (m.get("subject") == chosen and m.get("student_id") == student["id"] and m.get("exam") == exam)]
                            marks.append({"course": course, "semester": int(semester), "subject": chosen,
                                          "subject_name": subject_rec["name"], "student_id": student["id"],
                                          "name": student["name"], "exam": exam, "obtained": int(obtained),
                                          "total": int(total), "remark": remark, "by": me["name"], "time": now()})
                            save("marks", marks)
                            log_activity("Marks", f"{student['id']} {chosen} {exam}")
                            st.success("Marks saved successfully.")
                            st.rerun()

    with tab4:
        st.markdown("#### Upload Paper / Study Material")
        paper_courses = sorted(set(x.get("course", "") for x in assigned))
        p1, p2 = st.columns(2)
        paper_course = p1.selectbox("Class / Course", paper_courses, key="paper_course")
        paper_semesters = sorted(set(int(x.get("semester", 1)) for x in assigned if x.get("course") == paper_course))
        paper_sem = p2.selectbox("Semester", paper_semesters, key="paper_sem")
        paper_subjects = [x for x in assigned if x.get("course") == paper_course and int(x.get("semester", 1)) == int(paper_sem)]
        paper_subj_opts = {f"{x['name']} — {x['code']}": x for x in paper_subjects}
        if not paper_subj_opts:
            st.info("No assigned subject available for this course and semester.")
        else:
            paper_label = st.selectbox("Subject Name / Code", list(paper_subj_opts), key="paper_subject")
            paper_subj = paper_subj_opts[paper_label]
            st.info(f"Selected: **{paper_subj['name']}** | Subject Code: **{paper_subj['code']}** | {paper_course}, Semester {paper_sem}")
            with st.form(f"tp_f_{paper_course}_{paper_sem}_{paper_subj['code']}", clear_on_submit=True):
                title = st.text_input("Paper / Material Title *", placeholder="e.g. Unit 1 Notes or Mid-Term Paper")
                uploaded = st.file_uploader("Upload File *", type=["pdf", "docx", "doc", "zip", "jpg", "jpeg", "png", "ppt", "pptx"])
                if st.form_submit_button("⬆️ Upload Paper", type="primary"):
                    if not title.strip() or not uploaded:
                        st.error("Enter a title and select a file.")
                    else:
                        papers = load("papers")
                        papers.append({"id": uuid.uuid4().hex[:8], "course": paper_course,
                                       "semester": int(paper_sem), "subject": paper_subj["code"],
                                       "subject_name": paper_subj["name"], "title": title.strip(),
                                       "file": save_upload(uploaded, "papers"), "by": me["name"], "time": now()})
                        save("papers", papers)
                        log_activity("Uploaded paper", f"{paper_course} Sem {paper_sem} {paper_subj['code']}")
                        st.success("Paper uploaded successfully.")
                        st.rerun()
        papers = [x for x in load("papers") if x.get("course") == paper_course and int(x.get("semester", 0) or 0) == int(paper_sem)]
        if papers:
            st.markdown("##### Uploaded papers for selected class")
            for paper in papers[::-1]:
                with st.container(border=True):
                    st.write(f"**{paper.get('title','Untitled')}** — {paper.get('subject_name', paper.get('subject',''))} ({paper.get('subject','')})")
                    st.caption(f"By {paper.get('by','-')} • {paper.get('time','-')}")
                    if paper.get("file") and os.path.exists(paper["file"]):
                        st.download_button("⬇️ Download", open(paper["file"], "rb").read(), Path(paper["file"]).name, key=f"download_{paper['id']}")

# ============================================================
# STUDENT
# ============================================================
def student_home():
    sid=st.session_state.user["ref"]
    me = next((s for s in load("students") if s["id"]==sid), None)
    if not me: st.error("Student record missing"); return
    st.subheader(f"👋 Welcome, {me['name']} ({sid})")
    st.markdown(f'<span class="role-badge">{me["course"]} • Semester {me["semester"]}</span>', unsafe_allow_html=True)
    tab1,tab2,tab3,tab4,tab5=st.tabs(["👤 Profile","📚 Subjects","📝 Marks","✅ Attendance","💰 Fees"])
    with tab1:
        st.write(f"**Email:** {me['email']} • **Phone:** {me.get('phone','-')}")
        st.write(f"**Batch:** {me.get('batch','-')} • **Caste:** {me.get('caste','-')} • **Marital:** {me.get('marital','-')}")
        fam = me.get("family",{})
        st.write(f"**Father:** {fam.get('father','-')} • **Mother:** {fam.get('mother','-')}")
        st.markdown("##### 📘 10th Details")
        t = me.get("tenth",{})
        st.write(f"{t.get('board','-')} • {t.get('year','-')} • {t.get('obtained','-')}/{t.get('total','-')} • **{t.get('pct','-')}%**")
        if t.get("doc") and os.path.exists(t["doc"]):
            st.download_button("⬇️ 10th", open(t["doc"],"rb").read(), Path(t["doc"]).name, key="s_t")
        st.markdown("##### 📗 12th Details")
        tw = me.get("twelfth",{})
        st.write(f"{tw.get('board','-')} • {tw.get('year','-')} • {tw.get('stream','-')} • {tw.get('obtained','-')}/{tw.get('total','-')} • **{tw.get('pct','-')}%**")
        if tw.get("doc") and os.path.exists(tw["doc"]):
            st.download_button("⬇️ 12th", open(tw["doc"],"rb").read(), Path(tw["doc"]).name, key="s_tw")
        st.markdown("##### 📄 Documents")
        for k,v in me.get("docs",{}).items():
            if v and os.path.exists(v):
                st.download_button(f"⬇️ {k}", open(v,"rb").read(), Path(v).name, key=f"doc_{k}")
    with tab2:
        subs = load("subjects")
        mine = [s for s in subs if s["code"] in me.get("subjects",[])]
        if mine: st.dataframe(pd.DataFrame(mine), use_container_width=True)
        else: st.info("No subjects.")
    with tab3:
        marks=[m for m in load("marks") if m["student_id"]==sid]
        if marks: st.dataframe(pd.DataFrame(marks), use_container_width=True)
        else: st.info("No marks yet.")
    with tab4:
        st.markdown("#### 📅 Attendance Calendar")
        subject_records = [x for x in load("subjects") if x.get("code") in me.get("subjects", [])]
        if not subject_records:
            st.info("No subjects are assigned to your profile yet.")
        else:
            subject_opts = {f"{x['name']} ({x['code']})": x for x in subject_records}
            selected_subject_label = st.selectbox("Select Subject", list(subject_opts), key="student_att_subject")
            selected_subject = subject_opts[selected_subject_label]
            teachers_for_subject = [t.get("name", "-") for t in load("teachers") if selected_subject["code"] in t.get("subjects", [])]
            st.info(f"**Subject:** {selected_subject['name']} ({selected_subject['code']})  ·  **Teacher:** {', '.join(teachers_for_subject) if teachers_for_subject else 'Not assigned'}")
            cal_col1, cal_col2 = st.columns(2)
            month_choice = cal_col1.selectbox("Month", list(range(1, 13)), index=date.today().month-1, format_func=lambda m: calendar.month_name[m], key="student_att_month")
            year_choice = cal_col2.selectbox("Year", list(range(date.today().year-2, date.today().year+3)), index=2, key="student_att_year")
            subject_att = [a for a in load("attendance") if a.get("student_id") == sid and a.get("subject") == selected_subject["code"]]
            by_date = {a.get("date"): a for a in subject_att}
            st.caption("P = Present · A = Absent · L = Late · Select a date to view status and remark.")
            for day_names in [calendar.day_name[i] for i in range(7)]:
                pass
            day_cols = st.columns(7)
            for i, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
                day_cols[i].markdown(f"**{day_name}**")
            month_grid = calendar.monthcalendar(int(year_choice), int(month_choice))
            for week_index, week in enumerate(month_grid):
                day_cols = st.columns(7)
                for day_index, day_num in enumerate(week):
                    if day_num == 0:
                        day_cols[day_index].write(" ")
                    else:
                        day_str = date(int(year_choice), int(month_choice), int(day_num)).isoformat()
                        rec = by_date.get(day_str, {})
                        status = rec.get("status", "")
                        icon = "🟢" if status in ("Present", "P") else ("🔴" if status in ("Absent", "A") else ("🟠" if status in ("Late", "L") else "⚪"))
                        label = f"{icon} {day_num}"
                        if day_cols[day_index].button(label, key=f"stud_cal_{sid}_{selected_subject['code']}_{year_choice}_{month_choice}_{day_num}", use_container_width=True):
                            st.session_state["student_att_selected_date"] = day_str
                            st.session_state["student_att_selected_subject"] = selected_subject["code"]
                
            chosen_date = st.session_state.get("student_att_selected_date")
            if chosen_date and st.session_state.get("student_att_selected_subject") == selected_subject["code"]:
                record = by_date.get(chosen_date)
                with st.container(border=True):
                    st.markdown(f"### 📌 Attendance on {chosen_date}")
                    if record:
                        raw_status = record.get("status", "Not marked")
                        if raw_status == "P": raw_status = "Present"
                        elif raw_status == "A": raw_status = "Absent"
                        elif raw_status == "L": raw_status = "Late"
                        st.write(f"**Status:** {raw_status}")
                        st.write(f"**Remark:** {record.get('remark') or 'No remark added'}")
                        st.write(f"**Marked by:** {record.get('by', '—')}")
                    else:
                        st.info("Attendance has not been marked for this date.")
            if subject_att:
                st.markdown("##### Attendance summary")
                present_count = sum(1 for a in subject_att if a.get("status") in ("Present", "P"))
                absent_count = sum(1 for a in subject_att if a.get("status") in ("Absent", "A"))
                late_count = sum(1 for a in subject_att if a.get("status") in ("Late", "L"))
                m1, m2, m3 = st.columns(3)
                m1.metric("Present", present_count); m2.metric("Absent", absent_count); m3.metric("Late", late_count)
    with tab5:
        s_fee = me.get("fee", {})
        fr = load("fee_structure").get(f"{me['course']}|{me['semester']}", {})
        total = s_fee.get("total", fr.get("total",0))
        disc = s_fee.get("discount", fr.get("discount",0))
        payable = s_fee.get("payable", fr.get("payable", total-disc))
        remark = s_fee.get("remark", fr.get("remark",""))
        applied_by = s_fee.get("applied_by", fr.get("applied_by",""))
        paid = sum(f["amount"] for f in load("fees") if f["student_id"]==sid)
        due = max(payable - paid, 0)
        st.markdown(f"""
        <div class="fee-card">
            <h3>{me['course']} • Semester {me['semester']}</h3>
            <div style="display:flex;gap:40px;margin-top:14px;flex-wrap:wrap">
                <div><div class="fee-label">Total</div><div class="fee-val">₹{total}</div></div>
                <div><div class="fee-label">Discount</div><div class="fee-val">₹{disc}</div></div>
                <div><div class="fee-label">Payable</div><div class="fee-val">₹{payable}</div></div>
                <div><div class="fee-label">Paid</div><div class="fee-val">₹{paid}</div></div>
                <div><div class="fee-label">Due</div><div class="fee-val">{'✅' if due==0 else '₹'+str(due)}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if remark: st.info(f"💡 Discount ₹{disc}: {remark} (by {applied_by})")
        if due > 0: st.warning(f"⚠️ ₹{due} pending.")
        else: st.success("✅ All fees paid!")
        st.markdown("### 🧾 Payment History")
        hist=[f for f in load("fees") if f["student_id"]==sid]
        if hist: st.dataframe(pd.DataFrame(hist), use_container_width=True)
        else: st.info("No payments yet.")

# ============================================================
# SIDEBAR + ROUTER
# ============================================================
def sidebar():
    u=st.session_state.user
    st.sidebar.markdown(f"### 🎓 College ERP")
    st.sidebar.caption(f"{u['name']} • {u['role'].title()}")
    if st.sidebar.button("🚪 Logout", use_container_width=True): logout()
    st.sidebar.markdown("---")
    if u["role"]=="admin":
        return st.sidebar.radio("Menu",["Dashboard","Admission","Students","Teachers","Courses",
            "Subjects","Fee Structure","Fees","Papers","Reports","Backup","Settings"],
            label_visibility="collapsed")
    if u["role"]=="teacher":
        return st.sidebar.radio("Menu",["Teaching","Settings"], label_visibility="collapsed")
    return st.sidebar.radio("Menu",["My Dashboard","Settings"], label_visibility="collapsed")

if not st.session_state.logged_in:
    login_page()
else:
    menu = sidebar()
    role = st.session_state.user["role"]
    if role == "admin":
        if menu == "Dashboard": admin_dashboard()
        elif menu == "Admission": admin_admission()
        elif menu == "Students": admin_students()
        elif menu == "Teachers": admin_teachers()
        elif menu == "Courses": admin_courses()
        elif menu == "Subjects": admin_subjects()
        elif menu == "Fee Structure": admin_fee_structure()
        elif menu == "Fees": admin_fees()
        elif menu == "Papers": admin_papers()
        elif menu == "Reports": admin_reports()
        elif menu == "Backup": admin_backup()
        elif menu == "Settings": settings_page()
    elif role == "teacher":
        if menu == "Teaching": teacher_home()
        else: settings_page()
    else:
        if menu == "My Dashboard": student_home()
        else: settings_page()