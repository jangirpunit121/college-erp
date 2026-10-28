"""
CampusPro ERP — Professional College Management System (Upgraded)
Run: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import json, os, uuid, hashlib, zipfile, re, io, base64, html
import pymysql
import os
try:
    import redis
except ImportError:
    redis = None
from datetime import datetime, date, timedelta
from pathlib import Path
import calendar
import streamlit.components.v1 as components

# Redis is an optional cache only; MariaDB remains the source of truth.
# Configure REDIS_URL (e.g. redis://localhost:6379/0) or Streamlit secret [redis] url.
_REDIS = None
try:
    _redis_url = os.getenv("REDIS_URL", "")
    if not _redis_url:
        try:
            _redis_url = st.secrets.get("redis", {}).get("url", "")
        except Exception:
            _redis_url = ""
    if redis and _redis_url:
        _REDIS = redis.Redis.from_url(_redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
        _REDIS.ping()
except Exception:
    _REDIS = None

def cached_load(key, ttl=120):
    """Read small, frequently used lists from Redis; gracefully fall back to MariaDB."""
    if _REDIS is not None and key in ("courses", "subjects"):
        cache_key = f"campuspro:v1:{key}"
        try:
            cached = _REDIS.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        value = load(key)
        try:
            _REDIS.setex(cache_key, ttl, json.dumps(value, ensure_ascii=False, default=str))
        except Exception:
            pass
        return value
    return load(key)

# ============================================================
# CONFIG & PROFESSIONAL CSS
# ============================================================
st.set_page_config(page_title="CampusPro ERP", page_icon="🎓",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu, footer {visibility:hidden;}
    /* Hide the extra Streamlit header toolbar buttons; retain the mobile sidebar menu. */
    header[data-testid="stHeader"] {background:transparent !important; box-shadow:none !important;}
    header[data-testid="stHeader"] [data-testid="stToolbar"],
    header[data-testid="stHeader"] [data-testid="stDecoration"],
    header[data-testid="stHeader"] [data-testid="stStatusWidget"] {display:none !important;}
    /* Keep the sidebar in a fixed left column without covering the main content. */
    [data-testid="stSidebar"] {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        height: 100vh !important;
        min-width: 260px !important;
        width: 260px !important;
        transform: none;
        z-index: 1000;
        overflow-y: auto !important;
    }
    [data-testid="stSidebar"] > div:first-child {height:100vh; overflow-y:auto;}
    [data-testid="stAppViewContainer"] {overflow-x:hidden;}
    [data-testid="stMain"] {
        margin-left:260px !important;
        width:calc(100% - 260px) !important;
        min-width:0 !important;
    }
    [data-testid="stMainBlockContainer"] {
        width:100% !important;
        max-width:1400px !important;
        box-sizing:border-box !important;
    }
    [data-testid="stAppViewContainer"] .main {margin-left:0 !important; width:100% !important; min-width:0 !important;}
    [data-testid="stSidebarCollapsedControl"] {display:none !important;}
    /* Visible, animated processing indicator */
    .process-spinner {
        display:inline-block; width:18px; height:18px;
        border:3px solid #c7d2fe; border-top-color:#4f46e5;
        border-radius:50%; animation:campuspro-spin .75s linear infinite;
        vertical-align:middle; margin-right:8px;
    }
    /* Give all buttons immediate click feedback while Streamlit handles the action. */
    [data-testid="stButton"] button:active,
    [data-testid="stFormSubmitButton"] button:active,
    [data-testid="stDownloadButton"] button:active {
        cursor: progress !important; filter: brightness(.92); transform:scale(.99);
    }
    [data-testid="stButton"] button:active::after,
    [data-testid="stFormSubmitButton"] button:active::after {
        content:""; display:inline-block; width:12px; height:12px; margin-left:8px;
        border:2px solid currentColor; border-right-color:transparent;
        border-radius:50%; animation:campuspro-spin .65s linear infinite; vertical-align:middle;
    }
    @keyframes campuspro-spin {to {transform:rotate(360deg);}}
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            position:fixed !important; width:min(86vw,320px) !important;
            min-width:min(86vw,320px) !important; z-index:100000;
        }
        [data-testid="stMain"] {margin-left:0 !important; width:100% !important;}
        [data-testid="stAppViewContainer"] .main {margin-left:0 !important; width:100% !important;}
        [data-testid="stSidebarCollapsedControl"] {display:flex !important;}
        header[data-testid="stHeader"] [data-testid="stToolbar"] {display:none !important;}
        .block-container {padding-top:3.5rem !important;}
        .page-banner {padding:18px; gap:12px; flex-direction:column; align-items:flex-start;}
        .page-banner .right {text-align:left;}
    }
    .block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px;}
    
    /* Metrics */
    [data-testid="stMetric"] {
        background: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border: 1px solid #eef0f4;
    }
    [data-testid="stMetricValue"] {font-size: 28px; font-weight: 700; color: #1e293b;}
    [data-testid="stMetricLabel"] {color: #64748b; font-weight: 500;}

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0f172a;
        border-right: 1px solid #1e293b;
    }
    [data-testid="stSidebar"] * {color: #cbd5e1 !important;}
    [data-testid="stSidebar"] .stRadio label {
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 4px;
        transition: all 0.2s;
        cursor: pointer;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: #1e293b;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
        border: 1px solid #e2e8f0;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .stButton>button[kind="primary"] {
        background: #4f46e5;
        color: white;
        border: none;
    }
    .stButton>button[kind="primary"]:hover {
        background: #4338ca;
    }

    /* Form inputs */
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
        padding: 0;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: #4f46e5 !important;
        color: white !important;
        border: 1px solid #4f46e5;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: #f8fafc;
        border-radius: 8px;
        font-weight: 500;
    }
    
    /* Containers */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px;
        border: 1px solid #eef0f4;
        box-shadow: 0 1px 4px rgba(0,0,0,0.02);
    }

    /* Headers */
    h1 {color: #0f172a; font-weight: 700; font-size: 28px;}
    h2 {color: #1e293b; font-weight: 600; font-size: 22px;}
    h3 {color: #1e293b; font-weight: 600; font-size: 18px;}

    /* Top banner */
    .page-banner {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        padding: 24px 32px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 8px 24px rgba(79,70,229,0.15);
    }
    .page-banner h1 {color: white; margin: 0; font-size: 26px;}
    .page-banner p {margin: 6px 0 0 0; opacity: 0.9; font-size: 14px;}
    .page-banner .right {text-align: right;}
    
    /* DataFrames */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #eef0f4;
    }

    /* Info/warning boxes */
    .stAlert {border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# STORAGE — MariaDB (one physical table per ERP module)
# ============================================================
DATA_DIR = Path("data").resolve()
DOCS_DIR = DATA_DIR / "documents"
PHOTOS_DIR = DATA_DIR / "photos"
UPLOAD_DIR = DATA_DIR / "uploads"
for d in [DATA_DIR, DOCS_DIR, PHOTOS_DIR, UPLOAD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

KEYS = ["users", "students", "staff", "non_teaching", "courses", "subjects",
        "attendance", "marks", "fees", "fee_structure", "papers", "materials",
        "leaves", "library_books", "library_issues", "hostel", "transport",
        "announcements", "settings", "exams", "bills", "salaries"]
FILES = {k: DATA_DIR / f"{k}.json" for k in KEYS}

# MariaDB configuration. Defaults match the user's local database setup.
# Streamlit Cloud can override these with secrets/environment variables.
import os

def _read_secret(key, default):
    """Read Streamlit secrets if configured; work normally when secrets.toml is absent."""
    try:
        value = st.secrets.get(key, default)
        return default if value is None else value
    except Exception:
        return default

DB_HOST = os.getenv("DB_HOST", _read_secret("DB_HOST", "localhost"))
DB_PORT = int(os.getenv("DB_PORT", str(_read_secret("DB_PORT", "3306"))))
DB_USER = os.getenv("DB_USER", _read_secret("DB_USER", "root"))
DB_PASSWORD = os.getenv("DB_PASSWORD", _read_secret("DB_PASSWORD", "12345"))
DB_NAME = os.getenv("DB_NAME", _read_secret("DB_NAME", "myclgerp"))
try:
    _dbsec = st.secrets.get("mariadb", {})
    if _dbsec:
        DB_HOST = os.getenv("DB_HOST", _dbsec.get("host", DB_HOST))
        DB_PORT = int(os.getenv("DB_PORT", _dbsec.get("port", DB_PORT)))
        DB_USER = os.getenv("DB_USER", _dbsec.get("user", DB_USER))
        DB_PASSWORD = os.getenv("DB_PASSWORD", _dbsec.get("password", DB_PASSWORD))
        DB_NAME = os.getenv("DB_NAME", _dbsec.get("database", DB_NAME))
except Exception:
    pass


def _server_connection():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                           password=DB_PASSWORD, charset="utf8mb4", autocommit=True,
                           cursorclass=pymysql.cursors.DictCursor, connect_timeout=8)


_DB_SCHEMA_READY = False


def db_connect():
    """Create the requested database and module tables once per Streamlit run."""
    global _DB_SCHEMA_READY
    if not _DB_SCHEMA_READY:
        conn = _server_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                cur.execute(f"USE `{DB_NAME}`")
                for key in KEYS:
                    table = f"erp_{key}"
                    cur.execute(f"""CREATE TABLE IF NOT EXISTS `{table}` (
                        row_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        record_key VARCHAR(255) NULL,
                        payload LONGTEXT NOT NULL,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_record_key (record_key)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
                cur.execute("""CREATE TABLE IF NOT EXISTS erp_activity (
                    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    ts VARCHAR(32), username VARCHAR(255), user_role VARCHAR(100),
                    action_name VARCHAR(255), details TEXT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
            _DB_SCHEMA_READY = True
        finally:
            conn.close()
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
                           database=DB_NAME, charset="utf8mb4", autocommit=True,
                           cursorclass=pymysql.cursors.DictCursor, connect_timeout=8)


def _json_default(key):
    return {} if key in ("fee_structure", "settings") else []


def _record_key(item, index):
    if isinstance(item, dict):
        value = item.get("id") or item.get("username") or item.get("code")
        if value is not None:
            return str(value)[:255]
    return str(index) if isinstance(item, (str, int, float)) else None


def load(key):
    if key not in KEYS:
        return []
    default = _json_default(key)
    conn = None
    try:
        conn = db_connect()
        with conn.cursor() as cur:
            cur.execute(f"USE `{DB_NAME}`")
            cur.execute(f"SELECT payload, record_key FROM `erp_{key}` ORDER BY row_id")
            rows = cur.fetchall()
            if rows:
                if isinstance(default, dict):
                    result = {}
                    for row in rows:
                        try: result[row.get("record_key") or str(len(result))] = json.loads(row["payload"])
                        except (ValueError, TypeError): pass
                    return result
                result = []
                for row in rows:
                    try: result.append(json.loads(row["payload"]))
                    except (ValueError, TypeError): pass
                return result
        # One-time import of existing JSON data when this module's MariaDB table is empty.
        file_path = FILES[key]
        try:
            data = json.loads(file_path.read_text(encoding="utf-8")) if file_path.exists() else default
        except (ValueError, OSError):
            data = default
        save(key, data)
        return data
    except Exception as exc:
        st.error(f"MariaDB connection/read error ({DB_NAME}.{key}): {exc}. Check MariaDB is running and credentials are correct.")
        st.stop()
    finally:
        if conn:
            conn.close()


def save(key, data):
    if key not in KEYS:
        raise ValueError(f"Unknown ERP data module: {key}")
    conn = None
    try:
        with st.spinner(f"Saving {key.replace('_', ' ')}..."):
            conn = db_connect()
            with conn.cursor() as cur:
                cur.execute(f"USE `{DB_NAME}`")
                cur.execute(f"DELETE FROM `erp_{key}`")
                if isinstance(data, dict):
                    items = [(str(k)[:255], json.dumps(v, ensure_ascii=False, default=str)) for k, v in data.items()]
                elif isinstance(data, list):
                    items = [(_record_key(item, i), json.dumps(item, ensure_ascii=False, default=str)) for i, item in enumerate(data)]
                else:
                    items = [(None, json.dumps(data, ensure_ascii=False, default=str))]
                if items:
                    cur.executemany(f"INSERT INTO `erp_{key}` (record_key, payload, updated_at) VALUES (%s,%s,NOW())", items)
            # JSON mirror retained for manual backup and one-time migration compatibility.
            FILES[key].write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        if _REDIS is not None and key in ("courses", "subjects"):
            try: _REDIS.delete(f"campuspro:v1:{key}")
            except Exception: pass
    except Exception as exc:
        st.error(f"MariaDB save error ({DB_NAME}.{key}): {exc}")
        raise
    finally:
        if conn:
            conn.close()


def hpw(p): return hashlib.sha256(p.encode()).hexdigest()
def nid(p="ID"): return f"{p}{uuid.uuid4().hex[:6].upper()}"
def _next_number(records, field, prefix, width=4):
    year = str(date.today().year)
    stem = f"{prefix}{year}"
    highest = 0
    for row in records:
        if not isinstance(row, dict):
            continue
        value = str(row.get(field, "") or "")
        match = re.fullmatch(re.escape(stem) + r"(\d+)", value)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{stem}{highest + 1:0{width}d}"

def next_student_roll(students):
    return _next_number(students, "roll_no", "ROLL", 4)

def next_student_enrollment(students):
    return _next_number(students, "enrollment_no", "ENR", 4)

def next_employee_id():
    employees = [x for x in load("staff") if isinstance(x, dict)] + [x for x in load("non_teaching") if isinstance(x, dict)]
    return _next_number(employees, "id", "EMP", 4)

def flash_message(kind, message):
    st.session_state["_flash_message"] = {"kind": kind, "message": str(message)}

def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def today(): return date.today().isoformat()


def log(user, role, action, details=""):
    conn = None
    try:
        conn = db_connect()
        with conn.cursor() as cur:
            cur.execute(f"USE `{DB_NAME}`")
            cur.execute("INSERT INTO erp_activity (ts,username,user_role,action_name,details) VALUES (%s,%s,%s,%s,%s)",
                        (now(), user or "-", role or "-", str(action)[:255], str(details)[:500]))
    except Exception:
        # Activity logging should never prevent the user from completing an ERP task.
        pass
    finally:
        if conn: conn.close()

# ============================================================
# SEED (Only Admin)
# ============================================================
def seed():
    if not load("users"):
        save("users", [
            {"username":"admin","password":hpw("admin123"),"role":"Admin","name":"System Admin","active":True}
        ])
    if not load("settings"):
        save("settings", {"college_name":"ABC College of Engineering",
            "address":"Sector 12, New Delhi","phone":"011-12345678",
            "email":"info@college.edu","academic_year":"2024-2025"})
seed()

# ============================================================
# HELPERS
# ============================================================
def show_pdf(path, height=700):
    p = Path(path)
    if not p.exists(): st.error(f"❌ Not found: {p.name}"); return
    try: b64 = base64.b64encode(p.read_bytes()).decode()
    except Exception as e: st.error(str(e)); return
    components.html(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" '
        f'height="{height}px" style="border:1px solid #ddd;border-radius:8px;"></iframe>',
        height=height+20, scrolling=True)

def save_file(file, subdir=DOCS_DIR):
    if not file: return None
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", file.name)
    fname = f"{uuid.uuid4().hex[:8]}_{safe}"
    dest = subdir / fname
    dest.write_bytes(file.getbuffer())
    return str(dest)

def is_admin_role(r):
    if not r: return False
    s = str(r).strip().lower().replace("_"," ")
    return "admin" in s or s in ("administrator","root","owner")

def do_login(u, p):
    for user in load("users"):
        if isinstance(user, dict) and user.get("username")==u and user.get("password")==hpw(p):
            if not user.get("active", True): return None
            return user
    return None

def current_user(): return st.session_state.get("user")
def current_role():
    u = current_user()
    return u.get("role") if u else None
def is_admin(): return is_admin_role(current_role())

def has_role(*allowed):
    r = current_role()
    if not r: return False
    if is_admin_role(r): return True
    return r in allowed

def guard(*allowed):
    if not has_role(*allowed):
        st.error(f"🚫 Access denied. Requires: {', '.join(allowed)}"); return False
    return True

def logout():
    u = current_user()
    if u: log(u.get("username"), u.get("role"), "LOGOUT")
    st.session_state.clear(); st.rerun()

def login_page():
    s = load("settings")
    st.markdown("""
    <style>
    /* Login is the only page that uses the full viewport: true horizontal + vertical center. */
    [data-testid="stMain"] {margin-left:0 !important; width:100% !important;}
    [data-testid="stMainBlockContainer"] {
        width:100% !important; max-width:100% !important; min-height:100vh !important;
        box-sizing:border-box !important; display:flex !important; flex-direction:column !important;
        justify-content:center !important; align-items:center !important;
        padding:24px !important; margin:0 auto !important;
    }
    [data-testid="stSidebar"] {display:none !important;}
    .login-heading {text-align:center; padding:16px 0 18px 0;}
    div[data-testid="stForm"] {background:#fff; border:1px solid #e8edf5; border-radius:16px;
        padding:26px; box-shadow:0 12px 36px rgba(15,23,42,.10);}
    @media(max-width:768px) {
        [data-testid="stMainBlockContainer"] {padding:18px !important;}
        div[data-testid="stForm"] {padding:18px;}
    }
    </style>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.15, 1], gap="small")
    with c2:
        st.markdown(f"""
        <div class="login-heading">
            <div style="font-size:56px;">🎓</div>
            <h1 style="color:#0f172a; margin:12px 0 4px 0; font-size:28px;">{html.escape(str(s.get('college_name','College ERP')))}</h1>
            <p style="color:#64748b; margin:0;">{html.escape(str(s.get('academic_year','')))}</p>
        </div>""", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Username", placeholder="Enter username")
            p = st.text_input("Password", type="password", placeholder="Enter password")
            if st.form_submit_button("🔐 Login", use_container_width=True, type="primary"):
                user = do_login(u.strip(), p)
                if user:
                    st.session_state["user"] = user
                    log(u, user.get("role"), "LOGIN")
                    st.rerun()
                else: st.error("❌ Invalid username or password. Please try again.")

def page_header(title, sub=""):
    s = load("settings"); u = current_user() or {}
    st.markdown(f"""
    <div class="page-banner">
        <div><h1>{title}</h1><p>{sub or s.get('academic_year','')}</p></div>
        <div class="right">
            <p style="margin:0; font-weight:600;">{s.get('college_name','')}</p>
            <p style="margin:4px 0 0 0; font-size:12px;">{u.get('name','')} · {u.get('role','')}</p>
        </div>
    </div>""", unsafe_allow_html=True)

def csv_dl(df, name, key):
    st.download_button("⬇ Export CSV", df.to_csv(index=False).encode(),
                       file_name=f"{name}_{today()}.csv", mime="text/csv", key=key)

def xlsx_dl(df, name, key):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    st.download_button("📥 Export Excel", buf.getvalue(),
                       file_name=f"{name}_{today()}.xlsx", key=key,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def course_map(): return {c["id"]:c["name"] for c in load("courses") if isinstance(c,dict)}
def student_map(): return {s["id"]:s["name"] for s in load("students") if isinstance(s,dict) and s.get("id")}
def staff_map(): return {s["id"]:s["name"] for s in load("staff") if isinstance(s,dict) and s.get("id")}
def non_teaching_map(): return {s["id"]:s["name"] for s in load("non_teaching") if isinstance(s,dict) and s.get("id")}
def subject_map(): return {s["id"]:f"{s['code']} — {s['name']}" for s in load("subjects") if isinstance(s,dict)}

# ============================================================
# DASHBOARD
# ============================================================
def page_dashboard():
    """Role-scoped dashboard: show each login only the metrics it is allowed to see."""
    u = current_user() or {}
    role = str(u.get("role", "")).strip()
    role_key = role.lower().replace("_", " ")
    page_header(f"Welcome, {u.get('name', 'User')}!", "Your Dashboard")

    # Load data once, then strictly scope metrics by role.
    students_all = [x for x in load("students") if isinstance(x, dict)]
    staff_all = [x for x in load("staff") if isinstance(x, dict)]
    subjects_all = [x for x in load("subjects") if isinstance(x, dict)]
    attendance_all = [x for x in load("attendance") if isinstance(x, dict)]
    marks_all = [x for x in load("marks") if isinstance(x, dict)]
    fees_all = [x for x in load("fees") if isinstance(x, dict)]
    today_str = str(date.today())

    metrics = []
    if is_admin_role(role) or (u.get("username") or "").lower() == "admin":
        # Only administrators receive university-wide totals.
        metrics = [
            ("👨‍🎓 Total Students", len(students_all)),
            ("👨‍🏫 Faculty", len(staff_all)),
            ("📚 Subjects", len(subjects_all)),
            ("💰 Fees Collected", f"₹{sum(float(f.get('amount', 0) or 0) for f in fees_all):,.0f}"),
        ]
    elif role_key == "student":
        sid = u.get("student_id")
        my_student = next((x for x in students_all if sid and str(x.get("id")) == str(sid)), None)
        if my_student:
            sid = my_student.get("id")
            my_att = [a for a in attendance_all if str(a.get("student_id")) == str(sid)]
            my_marks = [m for m in marks_all if str(m.get("student_id")) == str(sid)]
            my_fees = [f for f in fees_all if str(f.get("student_id")) == str(sid)]
            paid = sum(float(f.get("amount", 0) or 0) for f in my_fees)
            payable = float(my_student.get("final_fee", 0) or 0)
            present = sum(1 for a in my_att if str(a.get("status", "")).lower() == "present")
            absent = sum(1 for a in my_att if str(a.get("status", "")).lower() == "absent")
            metrics = [
                ("📋 My Attendance", f"{present} Present / {absent} Absent"),
                ("📝 My Marks Records", len(my_marks)),
                ("💰 My Fees Paid", f"₹{paid:,.0f}"),
                ("⏳ My Fee Due", f"₹{max(0, payable-paid):,.0f}"),
            ]
        else:
            metrics = [("👤 My Profile", "Not linked"), ("📋 My Attendance", 0), ("📝 My Marks", 0), ("💰 My Fees", "No linked record")]
            st.warning("Your login is not linked to a student record. Please contact the administration; university-wide totals are hidden.")
    elif role_key == "teacher":
        teacher = next((x for x in staff_all if
                        (u.get("staff_id") and str(x.get("id")) == str(u.get("staff_id"))) or
                        (u.get("username") and str(x.get("username", "")).lower() == str(u.get("username", "")).lower())), None)
        assigned_ids = set((teacher or {}).get("subject_ids", u.get("subject_ids", [])) or [])
        my_subjects = [x for x in subjects_all if x.get("id") in assigned_ids or str(x.get("id")) in {str(i) for i in assigned_ids}]
        class_keys = {(x.get("course_id"), str(x.get("semester", 1))) for x in my_subjects}
        my_students = [x for x in students_all if (x.get("course_id"), str(x.get("semester", 1))) in class_keys] if class_keys else []
        my_student_ids = {str(x.get("id")) for x in my_students}
        my_att = [a for a in attendance_all if str(a.get("student_id")) in my_student_ids and
                  (not assigned_ids or str(a.get("subject_id")) in {str(i) for i in assigned_ids}) and a.get("date") == today_str]
        present = sum(1 for a in my_att if str(a.get("status", "")).lower() == "present")
        absent = sum(1 for a in my_att if str(a.get("status", "")).lower() == "absent")
        my_marks = [m for m in marks_all if str(m.get("student_id")) in my_student_ids and
                    (not assigned_ids or str(m.get("subject_id")) in {str(i) for i in assigned_ids})]
        metrics = [
            ("🎓 My Assigned Students", len(my_students)),
            ("✅ Present Today", present),
            ("❌ Absent Today", absent),
            ("📝 My Subject Marks Records", len(my_marks)),
        ]
        if not assigned_ids:
            st.info("Aapke login par subjects/classes assign nahi hain. Admin se Faculty section mein subjects assign karwayein. Isliye students aur attendance counts 0 dikh rahe hain; university-wide data nahi dikhaya jayega.")
    elif role_key == "accountant":
        my_total = sum(float(f.get("amount", 0) or 0) for f in fees_all)
        metrics = [("💰 Fees Collected", f"₹{my_total:,.0f}"), ("🧾 Fee Transactions", len(fees_all)),
                   ("⏳ Students With Due", sum(1 for st in students_all if sum(float(f.get("amount",0) or 0) for f in fees_all if str(f.get("student_id")) == str(st.get("id"))) < float(st.get("final_fee",0) or 0))),
                   ("📄 Bills", len([b for b in load("bills") if isinstance(b, dict)]))]
    elif role_key == "admission cell":
        metrics = [("🎓 Admissions / Students", len(students_all)), ("🧑‍🏫 Faculty Records", len(staff_all)),
                   ("📚 Courses", len(load("courses"))), ("📖 Subjects", len(subjects_all))]
    elif role_key == "librarian":
        books = [b for b in load("library_books") if isinstance(b, dict)]
        issues = [i for i in load("library_issues") if isinstance(i, dict)]
        metrics = [("📚 Book Titles", len(books)), ("📖 Active Issues", sum(1 for i in issues if i.get("status") == "Issued")),
                   ("↩ Returned Books", sum(1 for i in issues if i.get("status") == "Returned")), ("📦 Copies Available", sum(int(b.get("available",0) or 0) for b in books))]
    elif role_key == "exam cell":
        exams = [e for e in load("exams") if isinstance(e, dict)]
        metrics = [("📅 Scheduled Exams", len(exams)), ("📚 Subjects", len(subjects_all)),
                   ("📝 Marks Records", len(marks_all)), ("📄 Papers", len([p for p in load("papers") if isinstance(p, dict)]))]
    elif role_key == "hostel manager":
        hostel_students = [x for x in students_all if str(x.get("hostel", "")).lower() in ("yes", "true", "1")]
        metrics = [("🏠 Hostel Students", len(hostel_students)), ("🛏 Rooms Allocated", sum(1 for x in hostel_students if x.get("hostel_room"))),
                   ("🚌 Transport Students", sum(1 for x in students_all if str(x.get("transport", "")).lower() in ("yes", "true", "1"))),
                   ("📋 My Hostel Records", len(hostel_students))]
    else:
        # Other logins get personal leave/salary records only where a record owner matches.
        username = str(u.get("username", "")).lower()
        my_leaves = [x for x in load("leaves") if isinstance(x, dict) and str(x.get("username", x.get("user", ""))).lower() == username]
        my_salary = [x for x in load("salaries") if isinstance(x, dict) and str(x.get("username", x.get("user", ""))).lower() == username]
        metrics = [("🏖 My Leave Requests", len(my_leaves)), ("💼 My Salary Records", len(my_salary))]

    cols = st.columns(min(4, max(1, len(metrics))))
    for i, (label, value) in enumerate(metrics):
        cols[i % len(cols)].metric(label, value)

    st.divider()
    st.subheader("✨ Rotating Campus Slider · Top 10 Notices")
    anns = [a for a in load("announcements") if isinstance(a, dict)][::-1][:10]
    slides = anns[:10] or [
        {"title": "Welcome to CampusPro ERP", "body": "Manage students, faculty, fees and academic activities in one place."},
        {"title": "Automatic Student Numbers", "body": "Roll numbers and enrollment numbers are generated during admission."},
        {"title": "Campus at a Glance", "body": "Use the left menu to access the modules available to your login."},
    ]
    count = len(slides)
    duration = count * 4
    keyframes = []
    slide_html = []
    for idx, item in enumerate(slides):
        start, end = idx * 100 / count, (idx + 1) * 100 / count
        keyframes.append(f"{start:.3f}% {{opacity:0;transform:translateX(18px)}} {start+1:.3f}% {{opacity:1;transform:translateX(0)}} {max(start+1,end-1):.3f}% {{opacity:1;transform:translateX(0)}} {end:.3f}% {{opacity:0;transform:translateX(-18px)}}")
        title = html.escape(str(item.get("title", "Campus Update")))
        body = html.escape(str(item.get("body", "")))[:420]
        by = html.escape(str(item.get("by", "CampusPro ERP")))
        slide_html.append(f'<div class="campus-slide" style="animation-delay:{idx*4}s"><div class="slide-kicker">CAMPUS UPDATE · {idx+1:02d}</div><h2>{title}</h2><p>{body}</p><small>{by}</small></div>')
    css = f'''<style>
    .campus-slider{{position:relative;height:190px;overflow:hidden;border-radius:16px;background:linear-gradient(120deg,#3730a3,#7c3aed,#2563eb);color:white;margin:10px 0 24px}}
    .campus-slide{{position:absolute;inset:0;padding:26px 30px;opacity:0;box-sizing:border-box;animation:campus-slide-rotate {duration}s linear infinite}}
    .campus-slide h2{{color:white!important;font-size:23px;margin:8px 0}}
    .campus-slide p{{color:#f5f3ff;max-width:900px;margin:0 0 10px}}
    .campus-slide small,.slide-kicker{{color:#ddd6fe}} .slide-kicker{{font-size:10px;letter-spacing:2px;font-weight:700}}
    @keyframes campus-slide-rotate{{{' '.join(keyframes)}}}
    @media(max-width:768px){{.campus-slider{{height:230px}}.campus-slide{{padding:20px}}.campus-slide h2{{font-size:20px}}}}
    </style>'''
    st.markdown(css + '<div class="campus-slider">' + ''.join(slide_html) + '</div>', unsafe_allow_html=True)
    st.subheader("📢 Latest 10 Announcements / Notices")
    if not anns: st.info("No announcements")
    for a in anns:
        with st.container(border=True):
            st.markdown(f"**{a.get('title','')}**")
            st.write(str(a.get('body',''))[:300])
            st.caption(f"{a.get('by','')} · {a.get('ts','')}")

# ============================================================
# COURSES & SUBJECTS
# ============================================================
def page_courses():
    if not is_admin(): st.error("🚫 Only Admin"); return
    page_header("Courses", "Manage courses")
    courses = load("courses")
    with st.expander("➕ Add Course", expanded=False):
        with st.form("add_c"):
            c1, c2, c3 = st.columns(3)
            cid = c1.text_input("Course ID", value=nid("C"))
            name = c2.text_input("Name *")
            code = c3.text_input("Code")
            c1, c2, c3 = st.columns(3)
            dur = c1.number_input("Duration (yrs)", 1, 6, 4)
            seats = c2.number_input("Seats", 1, 500, 60)
            base_fee = c3.number_input("Base Fee (₹)", 0, 10_000_000, 50000)
            submitted_course = st.form_submit_button("➕ Add Course", type="primary")
            if submitted_course and not name.strip(): st.error("❌ Course name is required; nothing was saved.")
            if submitted_course and name.strip():
                courses.append({"id":cid,"name":name,"code":code,
                                "duration":dur,"seats":seats,"base_fee":base_fee})
                save("courses", courses); flash_message("success", "Added"); st.rerun()
    if courses:
        st.dataframe(pd.DataFrame([c for c in courses if isinstance(c,dict)]),
                     use_container_width=True, hide_index=True)

def page_subjects():
    if not is_admin(): st.error("🚫 Only Admin"); return
    page_header("Subjects", "Manage subjects")
    subs = load("subjects")
    cm = course_map()
    with st.expander("➕ Add Subject"):
        with st.form("add_s"):
            c1, c2 = st.columns(2)
            code = c1.text_input("Code *")
            name = c2.text_input("Name *")
            c1, c2 = st.columns(2)
            course = c1.selectbox("Course", list(cm.keys()) or [""], format_func=lambda x: cm.get(x,x))
            sem = c2.number_input("Semester", 1, 8, 1)
            max_marks = st.number_input("Maximum Marks", 1, 1000, 100, step=5)
            submitted_subject = st.form_submit_button("➕ Add Subject", type="primary")
            if submitted_subject and (not name.strip() or not code.strip()): st.error("❌ Subject name and code are required; nothing was saved.")
            if submitted_subject and name.strip() and code.strip():
                subs.append({"id":nid("SUB"),"code":code,"name":name,"course_id":course,"semester":sem,"max_marks":int(max_marks)})
                save("subjects", subs); flash_message("success", "Added"); st.rerun()
    if subs:
        df = pd.DataFrame([s for s in subs if isinstance(s,dict)])
        if "course_id" in df.columns: df["course"] = df["course_id"].map(cm)
        st.dataframe(df, use_container_width=True, hide_index=True)

# ============================================================
# ADMISSION (Complete Form)
# ============================================================
def page_admission():
    if not guard("Admission Cell"): return
    page_header("New Student Admission", "Complete student profile, documents and optional services")
    students = load("students")
    course_rows = cached_load("courses")
    courses = {x.get("id"): x.get("name", x.get("id", "")) for x in course_rows if isinstance(x, dict) and x.get("id")}
    all_subjects = cached_load("subjects")
    if not courses:
        st.warning("Pehle Courses section mein course add karein.")
        return

    with st.form("admission_full", clear_on_submit=False):
        st.markdown("#### 🎓 Course & Admission Details")
        c1, c2, c3 = st.columns(3)
        sid = c1.text_input("Student ID (Automatic)", value=nid("S"), disabled=True)
        course = c2.selectbox("Course *", list(courses.keys()), format_func=lambda x: courses.get(x, x))
        sem = c3.selectbox("Current Semester *", list(range(1, 9)), index=0)
        c1, c2, c3 = st.columns(3)
        roll = next_student_roll(students)
        enrollment_no = next_student_enrollment(students)
        c1.text_input("Roll Number (Automatic)", value=roll, disabled=True)
        c2.text_input("Enrollment Number (Automatic)", value=enrollment_no, disabled=True)
        year = c3.number_input("Admission Year", 2000, 2035, date.today().year)
        batch = st.text_input("Batch / Academic Year", value=str(date.today().year))

        st.markdown("#### 👤 Personal Details")
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Full Name *")
        email = c2.text_input("Email *")
        phone = c3.text_input("Phone *")
        c1, c2, c3 = st.columns(3)
        alt_phone = c1.text_input("Alternate Phone")
        dob = c2.date_input("Date of Birth", value=date(2005, 1, 1))
        gender = c3.selectbox("Gender", ["Male", "Female", "Other"])
        c1, c2, c3 = st.columns(3)
        marital = c1.selectbox("Marital Status", ["Single", "Married", "Divorced", "Widowed"])
        category = c2.selectbox("Category / Caste", ["General", "OBC", "SC", "ST", "EWS", "Other"])
        subcaste = c3.text_input("Sub-Caste")
        c1, c2, c3 = st.columns(3)
        religion = c1.text_input("Religion")
        nationality = c2.text_input("Nationality", value="Indian")
        blood = c3.selectbox("Blood Group", ["Unknown", "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        c1, c2, c3 = st.columns(3)
        aadhaar = c1.text_input("Aadhaar Number")
        category_cert = c2.text_input("Category Certificate No.")
        disability = c3.selectbox("Disability", ["No", "Yes - Locomotor", "Yes - Visual", "Yes - Hearing", "Yes - Other"])

        with st.expander("📍 Address Details", expanded=False):
            st.markdown("**Permanent Address**")
            c1, c2, c3 = st.columns(3)
            p_street = c1.text_input("Street / House No.")
            p_city = c2.text_input("City / Village")
            p_district = c3.text_input("District")
            c1, c2, c3 = st.columns(3)
            p_state = c1.text_input("State")
            p_pin = c2.text_input("PIN Code")
            p_country = c3.text_input("Country", value="India")
            same_as_perm = st.checkbox("Current address same as permanent", value=True)
            if not same_as_perm:
                st.markdown("**Current Address**")
                c1, c2, c3 = st.columns(3)
                c_street = c1.text_input("Current Street / House No.")
                c_city = c2.text_input("Current City / Village")
                c_district = c3.text_input("Current District")
                c1, c2, c3 = st.columns(3)
                c_state = c1.text_input("Current State")
                c_pin = c2.text_input("Current PIN Code")
                c_country = c3.text_input("Current Country", value="India")
            else:
                c_street, c_city, c_district = p_street, p_city, p_district
                c_state, c_pin, c_country = p_state, p_pin, p_country

        with st.expander("👨‍👩‍👧 Family & Guardian Details", expanded=False):
            c1, c2, c3 = st.columns(3)
            father = c1.text_input("Father's Name")
            father_occ = c2.text_input("Father's Occupation")
            father_phone = c3.text_input("Father's Phone")
            c1, c2, c3 = st.columns(3)
            mother = c1.text_input("Mother's Name")
            mother_occ = c2.text_input("Mother's Occupation")
            mother_phone = c3.text_input("Mother's Phone")
            c1, c2, c3 = st.columns(3)
            guardian = c1.text_input("Guardian Name")
            guardian_relation = c2.text_input("Guardian Relation")
            guardian_phone = c3.text_input("Guardian Phone")
            c1, c2, c3 = st.columns(3)
            family_income = c1.text_input("Annual Family Income (₹)")
            siblings = c2.number_input("No. of Siblings", 0, 20, 0)
            first_gen = c3.selectbox("First Generation Learner?", ["No", "Yes"])

        st.markdown("#### 📘 10th Details")
        c1, c2, c3 = st.columns(3)
        tenth_board = c1.text_input("10th Board")
        tenth_year = c2.text_input("10th Passing Year")
        tenth_school = c3.text_input("10th School Name")
        c1, c2, c3 = st.columns(3)
        tenth_obtained = c1.number_input("10th Marks Obtained", 0, 1000, 0)
        tenth_total = c2.number_input("10th Total Marks", 1, 1000, 500)
        tenth_percent = round(tenth_obtained / tenth_total * 100, 2) if tenth_total else 0.0
        c3.metric("10th Percentage", f"{tenth_percent:.2f}%")
        tenth_doc = st.file_uploader("10th Marksheet", type=["pdf", "jpg", "jpeg", "png"])

        st.markdown("#### 📗 12th Details")
        c1, c2, c3 = st.columns(3)
        twelfth_board = c1.text_input("12th Board")
        twelfth_year = c2.text_input("12th Passing Year")
        twelfth_school = c3.text_input("12th School Name")
        c1, c2, c3 = st.columns(3)
        twelfth_stream = c1.selectbox("12th Stream", ["Science", "Commerce", "Arts", "Other"])
        twelfth_obtained = c2.number_input("12th Marks Obtained", 0, 1000, 0)
        twelfth_total = c3.number_input("12th Total Marks", 1, 1000, 500)
        twelfth_percent = round(twelfth_obtained / twelfth_total * 100, 2) if twelfth_total else 0.0
        st.caption(f"12th Percentage: {twelfth_percent:.2f}%")
        twelfth_doc = st.file_uploader("12th Marksheet", type=["pdf", "jpg", "jpeg", "png"])

        with st.expander("🎓 Graduation Details (if applicable)", expanded=False):
            c1, c2, c3 = st.columns(3)
            grad_degree = c1.text_input("Graduation Degree")
            grad_univ = c2.text_input("Graduation University")
            grad_year = c3.text_input("Graduation Passing Year")
            c1, c2, c3 = st.columns(3)
            grad_obtained = c1.number_input("Graduation Marks Obtained", 0, 1000, 0)
            grad_total = c2.number_input("Graduation Total Marks", 1, 1000, 500)
            grad_percent = round(grad_obtained / grad_total * 100, 2) if grad_total else 0.0
            c3.metric("Graduation Percentage", f"{grad_percent:.2f}%")
            grad_doc = st.file_uploader("Graduation Marksheet", type=["pdf", "jpg", "jpeg", "png"])

        with st.expander("🎓 Post-Graduation Details (if applicable)", expanded=False):
            c1, c2, c3 = st.columns(3)
            pg_degree = c1.text_input("PG Degree")
            pg_univ = c2.text_input("PG University")
            pg_year = c3.text_input("PG Passing Year")
            c1, c2, c3 = st.columns(3)
            pg_obtained = c1.number_input("PG Marks Obtained", 0, 1000, 0)
            pg_total = c2.number_input("PG Total Marks", 1, 1000, 500)
            pg_percent = round(pg_obtained / pg_total * 100, 2) if pg_total else 0.0
            c3.metric("PG Percentage", f"{pg_percent:.2f}%")
            pg_doc = st.file_uploader("PG Marksheet", type=["pdf", "jpg", "jpeg", "png"])

        with st.expander("📄 Documents Upload", expanded=True):
            c1, c2, c3 = st.columns(3)
            photo = c1.file_uploader("Photo *", type=["jpg", "jpeg", "png"])
            signature = c2.file_uploader("Signature", type=["jpg", "jpeg", "png"])
            aadhaar_doc = c3.file_uploader("Aadhaar Card", type=["pdf", "jpg", "jpeg", "png"])
            c1, c2, c3 = st.columns(3)
            domicile_doc = c1.file_uploader("Domicile Certificate", type=["pdf", "jpg", "png"])
            caste_doc = c2.file_uploader("Caste Certificate", type=["pdf", "jpg", "png"])
            income_doc = c3.file_uploader("Income Certificate", type=["pdf", "jpg", "png"])
            c1, c2, c3 = st.columns(3)
            tc_doc = c1.file_uploader("Transfer Certificate", type=["pdf", "jpg", "png"])
            migration_doc = c2.file_uploader("Migration Certificate", type=["pdf", "jpg", "png"])
            medical_doc = c3.file_uploader("Medical Certificate", type=["pdf", "jpg", "png"])
            c1, c2, c3 = st.columns(3)
            sports_doc = c1.file_uploader("Sports Certificate", type=["pdf", "jpg", "png"])
            gap_doc = c2.file_uploader("Gap Year Certificate", type=["pdf", "jpg", "png"])
            other_doc = c3.file_uploader("Other Document", type=["pdf", "jpg", "png", "zip"])

        with st.expander("🏥 Medical & Emergency Details", expanded=False):
            c1, c2, c3 = st.columns(3)
            allergies = c1.text_input("Known Allergies")
            chronic = c2.text_input("Chronic Illness")
            medications = c3.text_input("Current Medications")
            c1, c2, c3 = st.columns(3)
            emergency_name = c1.text_input("Emergency Contact Name")
            emergency_relation = c2.text_input("Emergency Contact Relation")
            emergency_phone = c3.text_input("Emergency Contact Phone")

        with st.expander("🏫 Previous Institution & Achievements", expanded=False):
            c1, c2, c3 = st.columns(3)
            previous_school = c1.text_input("Previous Institution")
            previous_board = c2.text_input("Board / University")
            previous_year = c3.text_input("Last Year Attended")
            previous_reason = st.text_area("Reason for Leaving")
            achievements = st.text_area("Achievements")
            hobbies = st.text_area("Hobbies & Interests")
            c1, c2, c3 = st.columns(3)
            ncc = c1.selectbox("NCC / NSS", ["No", "NCC", "NSS"])
            scouts = c2.selectbox("Scouts & Guides", ["No", "Yes"])
            sports_level = c3.selectbox("Sports Level", ["None", "School", "District", "State", "National", "International"])

        with st.expander("🏠 Optional Hostel, Mess & Transport", expanded=False):
            c1, c2, c3 = st.columns(3)
            hostel = c1.selectbox("Hostel Required?", ["No", "Yes"])
            hostel_type = c2.selectbox("Room Type", ["N/A", "Single", "Double", "Triple", "Dormitory"])
            mess = c3.selectbox("Mess Required?", ["No", "Yes"])
            c1, c2, c3 = st.columns(3)
            hostel_room = c1.text_input("Hostel Room No. (allotment)")
            mess_pref = c2.selectbox("Mess Preference", ["N/A", "Veg", "Non-Veg", "Jain"])
            transport = c3.selectbox("Transport Required?", ["No", "Yes"])
            c1, c2 = st.columns(2)
            transport_route = c1.text_input("Bus Route")
            pickup_point = c2.text_input("Pickup Point")

        with st.expander("💰 Course Fee & Optional Charges", expanded=True):
            c1, c2, c3 = st.columns(3)
            base_fee = c1.number_input("Course Fee (₹)", 0, 10_000_000, 0, step=1000)
            discount_pct = c2.number_input("Course Fee Discount (%)", 0.0, 100.0, 0.0)
            quota = c3.selectbox("Quota", ["None", "Sports", "SC/ST", "OBC", "Merit", "Staff Ward", "Other"])
            discount_remark = st.text_input("Discount Remark / Reason")
            discount_applied_by = st.text_input("Discount Applied By", value=(current_user() or {}).get("name", ""))
            payment_plan = st.selectbox("Payment Plan", ["Full Payment", "Installments (2)", "Installments (3)", "Installments (4)"])
            st.caption("Library, Transport, Hostel aur Mess optional hain. Select na karne par unka charge zero rahega.")
            fee_cols = st.columns(4)
            library_req = fee_cols[0].selectbox("Library", ["No", "Yes"])
            library_fee = fee_cols[0].number_input("Library Fee (₹)", 0, 1_000_000, 0, disabled=library_req == "No")
            transport_fee = fee_cols[1].number_input("Transport Fee (₹)", 0, 1_000_000, 0)
            hostel_fee = fee_cols[2].number_input("Hostel Fee (₹)", 0, 1_000_000, 0)
            mess_fee = fee_cols[3].number_input("Mess Fee (₹)", 0, 1_000_000, 0)
            fee_cols2 = st.columns(3)
            id_card_fee = fee_cols2[0].number_input("ID Card Fee (₹)", 0, 100_000, 0)
            exam_fee = fee_cols2[1].number_input("Exam Fee (₹)", 0, 1_000_000, 0)
            other_fee = fee_cols2[2].number_input("Other Charges (₹)", 0, 1_000_000, 0)
            course_discount = round(base_fee * discount_pct / 100, 2)
            optional_total = (library_fee if library_req == "Yes" else 0) + (transport_fee if transport == "Yes" else 0) + (hostel_fee if hostel == "Yes" else 0) + (mess_fee if mess == "Yes" else 0) + id_card_fee + exam_fee + other_fee
            final_fee = max(0, round(base_fee - course_discount + optional_total, 2))
            c1, c2, c3 = st.columns(3)
            c1.metric("Course Discount", f"₹{course_discount:,.2f}")
            c2.metric("Optional Charges", f"₹{optional_total:,.2f}")
            c3.metric("Total Payable", f"₹{final_fee:,.2f}")

        with st.expander("📚 Enrolled Subjects", expanded=False):
            eligible_subjects = [x for x in all_subjects if isinstance(x, dict) and x.get("course_id") == course and int(x.get("semester", 1)) == int(sem)]
            course_name = courses.get(course, course)
            subject_labels = {x.get("id"): f"{course_name} {int(x.get('semester', 1))}{'st' if int(x.get('semester', 1)) == 1 else 'nd' if int(x.get('semester', 1)) == 2 else 'rd' if int(x.get('semester', 1)) == 3 else 'th'} Sem — {x.get('code','')} — {x.get('name','')}" for x in eligible_subjects}
            selected_subjects = st.multiselect("Subjects", list(subject_labels.keys()), format_func=lambda x: subject_labels.get(x, x))

        with st.expander("🏦 Bank Details (Optional)", expanded=False):
            c1, c2, c3 = st.columns(3)
            bank_name = c1.text_input("Bank Name")
            account_no = c2.text_input("Account Number")
            ifsc = c3.text_input("IFSC Code")
            c1, c2, c3 = st.columns(3)
            account_holder = c1.text_input("Account Holder Name")
            bank_branch = c2.text_input("Branch")
            upi = c3.text_input("UPI ID")

        st.markdown("#### 🔐 Student Login Credentials")
        c1, c2 = st.columns(2)
        username = c1.text_input("Username *", value=f"stu{sid.lower()}")
        password = c2.text_input("Password *", type="password", value="student123")
        submitted = st.form_submit_button("✅ Submit Admission", type="primary", use_container_width=True)

    if submitted:
        errors = []
        if not name.strip(): errors.append("Full Name required")
        if not email.strip(): errors.append("Email required")
        if not phone.strip(): errors.append("Phone required")
        if not username.strip() or not password.strip(): errors.append("Username and password required")
        if not photo: errors.append("Photo required")
        if not signature: errors.append("Signature required")
        if not aadhaar_doc: errors.append("Aadhaar document required")
        if not tenth_doc: errors.append("10th marksheet required")
        if not twelfth_doc: errors.append("12th marksheet required")
        if not tenth_board.strip() or not str(tenth_year).strip(): errors.append("10th Board and Passing Year required")
        if not twelfth_board.strip() or not str(twelfth_year).strip(): errors.append("12th Board and Passing Year required")
        if any(isinstance(s, dict) and s.get("id") == sid for s in students): errors.append("Student ID already exists")
        users = load("users")
        if any(isinstance(u, dict) and u.get("username", "").lower() == username.strip().lower() for u in users): errors.append("Username already exists")
        if errors:
            st.error("Please correct the following:\n- " + "\n- ".join(errors))
            return

        photo_path = save_file(photo, PHOTOS_DIR)
        signature_path = save_file(signature)
        aadhaar_path = save_file(aadhaar_doc)
        domicile_path = save_file(domicile_doc)
        caste_path = save_file(caste_doc)
        income_path = save_file(income_doc)
        tenth_path = save_file(tenth_doc)
        twelfth_path = save_file(twelfth_doc)
        graduation_path = save_file(grad_doc)
        pg_path = save_file(pg_doc)
        tc_path = save_file(tc_doc)
        migration_path = save_file(migration_doc)
        medical_path = save_file(medical_doc)
        sports_path = save_file(sports_doc)
        gap_path = save_file(gap_doc)
        other_path = save_file(other_doc)
        student = {
            "id": sid, "roll_no": roll, "enrollment_no": enrollment_no, "name": name.strip(), "email": email.strip(), "phone": phone.strip(),
            "alt_phone": alt_phone, "dob": str(dob), "gender": gender, "marital_status": marital,
            "blood_group": blood, "category": category, "caste": category, "subcaste": subcaste,
            "religion": religion, "nationality": nationality, "aadhaar": aadhaar,
            "category_cert": category_cert, "disability": disability,
            "father_name": father, "mother_name": mother,
            "address": ", ".join(x for x in [p_street, p_city, p_district, p_state, p_pin, p_country] if x),
            "addresses": {"permanent": {"street": p_street, "city": p_city, "district": p_district, "state": p_state, "pin": p_pin, "country": p_country},
                          "current": {"street": c_street, "city": c_city, "district": c_district, "state": c_state, "pin": c_pin, "country": c_country}},
            "pincode": p_pin, "family": {"father": father, "father_occupation": father_occ, "father_phone": father_phone,
                "mother": mother, "mother_occupation": mother_occ, "mother_phone": mother_phone, "guardian": guardian,
                "guardian_relation": guardian_relation, "guardian_phone": guardian_phone, "income": family_income,
                "siblings": siblings, "first_gen": first_gen},
            "tenth_school": tenth_school, "tenth_year": tenth_year, "tenth_percent": tenth_percent, "tenth_board": tenth_board,
            "tenth": {"board": tenth_board, "year": tenth_year, "school": tenth_school, "obtained": tenth_obtained,
                      "total": tenth_total, "pct": tenth_percent, "doc": tenth_path},
            "twelfth_school": twelfth_school, "twelfth_year": twelfth_year, "twelfth_percent": twelfth_percent, "twelfth_board": twelfth_board,
            "twelfth": {"board": twelfth_board, "year": twelfth_year, "school": twelfth_school, "stream": twelfth_stream,
                        "obtained": twelfth_obtained, "total": twelfth_total, "pct": twelfth_percent, "doc": twelfth_path},
            "graduation": {"degree": grad_degree, "univ": grad_univ, "year": grad_year, "obtained": grad_obtained,
                           "total": grad_total, "pct": grad_percent, "doc": graduation_path},
            "pg": {"degree": pg_degree, "univ": pg_univ, "year": pg_year, "obtained": pg_obtained,
                   "total": pg_total, "pct": pg_percent, "doc": pg_path},
            "course_id": course, "course": courses.get(course, course), "course_level": next((x.get("level", "") for x in load("courses") if isinstance(x, dict) and x.get("id") == course), ""),
            "semester": int(sem), "admission_year": year, "batch": batch,
            "subjects": selected_subjects, "base_fee": base_fee, "discount_pct": discount_pct,
            "course_discount": course_discount, "optional_charges": {"library": library_fee if library_req == "Yes" else 0,
                "transport": transport_fee if transport == "Yes" else 0, "hostel": hostel_fee if hostel == "Yes" else 0,
                "mess": mess_fee if mess == "Yes" else 0, "id_card": id_card_fee, "exam": exam_fee, "other": other_fee},
            "library": library_req, "final_fee": final_fee, "fee": {"course_fee": base_fee, "discount": course_discount,
                "optional_total": optional_total, "payable": final_fee, "quota": quota, "remark": discount_remark,
                "applied_by": discount_applied_by, "payment_plan": payment_plan},
            "quota": quota, "discount_remark": discount_remark, "hostel": hostel, "hostel_type": hostel_type,
            "hostel_room": hostel_room, "mess": mess, "mess_pref": mess_pref, "transport": transport,
            "transport_route": transport_route, "pickup_point": pickup_point,
            "photo": photo_path, "signature": signature_path, "aadhaar_doc": aadhaar_path,
            "domicile_doc": domicile_path, "caste_doc": caste_path, "income_doc": income_path,
            "tenth_doc": tenth_path, "twelfth_doc": twelfth_path, "graduation_doc": graduation_path,
            "pg_doc": pg_path, "tc_doc": tc_path, "migration_doc": migration_path,
            "medical_doc": medical_path, "sports_doc": sports_path, "gap_doc": gap_path,
            "other_doc": other_path, "docs": {"photo": photo_path, "signature": signature_path,
                "aadhaar": aadhaar_path, "domicile": domicile_path, "caste": caste_path,
                "income": income_path, "tc": tc_path, "migration": migration_path,
                "medical": medical_path, "sports": sports_path, "gap": gap_path, "other": other_path},
            "medical": {"allergies": allergies, "chronic": chronic, "medications": medications,
                "emergency_name": emergency_name, "emergency_relation": emergency_relation, "emergency_phone": emergency_phone},
            "previous": {"school": previous_school, "board": previous_board, "year": previous_year, "reason": previous_reason},
            "achievements": achievements, "hobbies": hobbies, "ncc": ncc, "scouts": scouts, "sports_level": sports_level,
            "bank": {"name": bank_name, "account_no": account_no, "ifsc": ifsc, "holder": account_holder, "branch": bank_branch, "upi": upi},
            "status": "Active", "ts": now(), "admitted": now()
        }
        students.append(student)
        save("students", students)
        users.append({"username": username.strip(), "password": hpw(password), "role": "Student",
                      "name": name.strip(), "student_id": sid, "active": True, "email": email.strip()})
        save("users", users)
        log(current_user().get("username"), "Admission Cell", "ADMISSION", f"{sid}:{name}")
        flash_message("success", f"✅ {name} admitted successfully. Student ID: {sid}; login: {username}")
        st.rerun()

# ============================================================
# FULL RECORD VIEW / EDIT HELPERS
# ============================================================
def _flatten_record(value, prefix=""):
    """Flatten nested records so every value captured by a form is visible/editable."""
    out = []
    if isinstance(value, dict):
        if not value:
            out.append((prefix, {}))
        else:
            for k, v in value.items():
                path = f"{prefix}.{k}" if prefix else str(k)
                out.extend(_flatten_record(v, path))
    elif isinstance(value, list):
        out.append((prefix, value))
    else:
        out.append((prefix, value))
    return out


def _set_record_path(record, dotted_path, value):
    parts = dotted_path.split(".")
    node = record
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value


def _field_label(path):
    return " / ".join(part.replace("_", " ").title() for part in path.split("."))


def _is_document_field(path, value):
    names = ("doc", "document", "photo", "signature", "certificate", "marksheet", "aadhaar", "domicile", "caste", "income_proof", "migration", "medical", "sports_doc", "appointment", "identity", "experience", "qualification")
    key = path.split(".")[-1].lower()
    return any(token in key for token in names) or (isinstance(value, str) and value.lower().endswith((".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx")) and ("/" in value or "\\" in value))


def _show_record_documents(record, prefix):
    files = [(path, val) for path, val in _flatten_record(record) if _is_document_field(path, val) and isinstance(val, str) and val.strip()]
    if not files:
        st.info("Is record mein abhi koi uploaded document path nahi mila.")
        return
    for idx, (path, val) in enumerate(files):
        pth = Path(val)
        cols = st.columns([3, 2])
        cols[0].write(f"**{_field_label(path)}**")
        if pth.exists() and pth.is_file():
            try:
                cols[1].download_button("⬇ Download", pth.read_bytes(), file_name=pth.name, key=f"{prefix}_download_{idx}")
                if pth.suffix.lower() in (".png", ".jpg", ".jpeg"):
                    with st.expander(f"Preview: {pth.name}"):
                        st.image(str(pth), use_container_width=True)
                elif pth.suffix.lower() == ".pdf":
                    with st.expander(f"Preview: {pth.name}"):
                        show_pdf(str(pth), height=450)
            except Exception as exc:
                cols[1].caption(f"File read nahi hui: {exc}")
        else:
            cols[1].caption(f"Path saved, file is server par nahi mili: {pth.name}")


def _edit_complete_record(record, form_key, record_type):
    """Generic editor for all nested fields; uploaded documents can be replaced."""
    flat = _flatten_record(record)
    edits = {}
    uploads = {}
    st.caption("Is editor mein record ke saare saved fields dikhte hain. Document fields mein nayi file upload karke replace kar sakte ho. Record ID read-only rakhi gayi hai taaki linked records na tootain.")
    with st.form(form_key):
        for idx, (path, value) in enumerate(flat):
            leaf = path.split(".")[-1].lower()
            label = _field_label(path)
            key = f"{form_key}_{idx}_{hashlib.md5(path.encode()).hexdigest()[:8]}"
            if path == "id":
                st.text_input(label, value=str(value or ""), disabled=True, key=key)
                continue
            if _is_document_field(path, value):
                current = str(value or "")
                if current:
                    st.caption(f"Current file for {label}: {Path(current).name}")
                file_types = ["pdf", "jpg", "jpeg", "png", "doc", "docx", "xlsx", "xls"]
                uploads[path] = st.file_uploader(f"Add / Replace — {label}", type=file_types, key=f"{key}_upload")
                edits[path] = value
            elif isinstance(value, bool):
                edits[path] = st.checkbox(label, value=value, key=key)
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                if isinstance(value, int):
                    edits[path] = int(st.number_input(label, value=int(value), step=1, key=key))
                else:
                    edits[path] = float(st.number_input(label, value=float(value), key=key))
            elif isinstance(value, list) or isinstance(value, dict):
                raw = st.text_area(f"{label} (JSON)", value=json.dumps(value, ensure_ascii=False, indent=2, default=str), height=100, key=key)
                edits[path] = raw
            else:
                text_value = "" if value is None else str(value)
                if any(token in leaf for token in ("remark", "reason", "address", "achievement", "hobbies", "allerg", "medication", "chronic", "notes")):
                    edits[path] = st.text_area(label, value=text_value, key=key)
                else:
                    edits[path] = st.text_input(label, value=text_value, key=key)
        submitted = st.form_submit_button("💾 Save All Changes", type="primary", use_container_width=True)
    if not submitted:
        return None

    updated = json.loads(json.dumps(record, ensure_ascii=False, default=str))
    for path, new_value in edits.items():
        if path == "id":
            continue
        if isinstance(new_value, str) and isinstance(dict(flat).get(path), (list, dict)):
            try:
                new_value = json.loads(new_value)
            except json.JSONDecodeError:
                st.error(f"{_field_label(path)} ka JSON valid nahi hai. Is field ko sahi JSON mein likho.")
                return None
        elif isinstance(new_value, str) and isinstance(dict(flat).get(path), int) and new_value.strip().isdigit():
            new_value = int(new_value)
        elif isinstance(new_value, str) and isinstance(dict(flat).get(path), float):
            try: new_value = float(new_value)
            except ValueError: pass
        _set_record_path(updated, path, new_value)
    for path, uploaded in uploads.items():
        if uploaded is not None:
            subdir = PHOTOS_DIR if path.split(".")[-1].lower() in ("photo", "signature") else DOCS_DIR
            _set_record_path(updated, path, save_file(uploaded, subdir))
    return updated


# ============================================================
# STUDENTS MANAGEMENT — complete record view/edit
# ============================================================
def page_students():
    if not guard("Admission Cell"): return
    page_header("Student Management", "View, search, inspect documents and edit every admission field")
    students = load("students")
    cm = course_map()
    tab1, tab2, tab3 = st.tabs(["📋 All Students", "🔎 Complete Student Record", "✏ Edit Full Student Record"])

    with tab1:
        q = st.text_input("🔍 Search name / ID / roll / phone / email", key="student_search_all")
        cf = st.selectbox("Filter course", ["All"] + list(cm.keys()), format_func=lambda x: "All" if x == "All" else cm.get(x, x), key="student_filter_course")
        filt = [x for x in students if isinstance(x, dict)]
        if q:
            filt = [x for x in filt if q.lower() in " ".join(str(x.get(k, "")) for k in ("id", "name", "roll_no", "phone", "email")).lower()]
        if cf != "All":
            filt = [x for x in filt if x.get("course_id") == cf]
        if filt:
            rows = []
            for x in filt:
                rows.append({"Student ID": x.get("id", ""), "Name": x.get("name", ""), "Course": x.get("course", cm.get(x.get("course_id"), x.get("course_id", ""))), "Semester": x.get("semester", ""), "Roll No": x.get("roll_no", ""), "Phone": x.get("phone", ""), "Email": x.get("email", ""), "Status": x.get("status", "")})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            csv_dl(pd.DataFrame(rows), "students", "stu_csv_full")
        else:
            st.info("No students found. Admission submit hone ke baad records yahan aayenge.")

    student_ids = [x.get("id") for x in students if isinstance(x, dict) and x.get("id")]
    if not student_ids:
        with tab2: st.info("Abhi koi student record nahi hai.")
        with tab3: st.info("Edit karne ke liye pehle student admission hona chahiye.")
        return

    def _student_label(x):
        obj = next((z for z in students if isinstance(z, dict) and z.get("id") == x), {})
        return f"{x} — {obj.get('name', '')} | {obj.get('course', cm.get(obj.get('course_id'), obj.get('course_id', '')))} Sem {obj.get('semester', '')}"

    with tab2:
        st.markdown("**Filter Complete Student Records**")
        sv1, sv2 = st.columns([2, 1])
        view_q = sv1.text_input("Search student by name / ID / roll / phone", key="student_complete_view_search")
        view_course = sv2.selectbox("Course", ["All"] + list(cm.keys()), format_func=lambda x: "All Courses" if x == "All" else cm.get(x, x), key="student_complete_view_course")
        view_students = [x for x in students if isinstance(x, dict) and x.get("id")]
        if view_q.strip():
            needle = view_q.strip().lower()
            view_students = [x for x in view_students if needle in " ".join(str(x.get(k, "")) for k in ("id", "name", "roll_no", "phone", "email")).lower()]
        if view_course != "All":
            view_students = [x for x in view_students if str(x.get("course_id", "")) == str(view_course)]
        view_ids = [x.get("id") for x in view_students]
        if not view_ids:
            st.info("Is filter ke liye koi student record nahi mila.")
            selected = None
        else:
            selected = st.selectbox("Student record dekhein", view_ids, format_func=_student_label, key="student_view_id")
        obj = next((x for x in students if isinstance(x, dict) and x.get("id") == selected), None) if selected else None
        if obj:
            st.subheader(f"{obj.get('name', '')} — {obj.get('id', '')}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Course", obj.get("course", cm.get(obj.get("course_id"), "—")))
            c2.metric("Semester", str(obj.get("semester", "—")))
            c3.metric("Phone", str(obj.get("phone", "—")))
            c4.metric("Status", str(obj.get("status", "—")))
            with st.expander("📄 Uploaded Documents — Preview / Download", expanded=True):
                _show_record_documents(obj, f"student_docs_{selected}")
            with st.expander("🧾 Complete Saved Data (all admission fields)", expanded=True):
                for path, value in _flatten_record(obj):
                    if _is_document_field(path, value) and isinstance(value, str) and value:
                        st.write(f"**{_field_label(path)}:** `{Path(value).name}`")
                    else:
                        st.write(f"**{_field_label(path)}:** {json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, (dict, list)) else (value if value is not None else '')}")

    with tab3:
        st.markdown("**Filter Student Records to Edit**")
        se1, se2 = st.columns([2, 1])
        edit_q = se1.text_input("Search student by name / ID / roll / phone", key="student_complete_edit_search")
        edit_course = se2.selectbox("Course", ["All"] + list(cm.keys()), format_func=lambda x: "All Courses" if x == "All" else cm.get(x, x), key="student_complete_edit_course")
        edit_students = [x for x in students if isinstance(x, dict) and x.get("id")]
        if edit_q.strip():
            needle = edit_q.strip().lower()
            edit_students = [x for x in edit_students if needle in " ".join(str(x.get(k, "")) for k in ("id", "name", "roll_no", "phone", "email")).lower()]
        if edit_course != "All":
            edit_students = [x for x in edit_students if str(x.get("course_id", "")) == str(edit_course)]
        edit_ids = [x.get("id") for x in edit_students]
        if not edit_ids:
            st.info("Is filter ke liye koi student record nahi mila.")
            selected_edit = None
        else:
            selected_edit = st.selectbox("Student to edit", edit_ids, format_func=_student_label, key="student_edit_id")
        obj = next((x for x in students if isinstance(x, dict) and x.get("id") == selected_edit), None) if selected_edit else None
        if obj:
            with st.expander("📂 Existing Documents — Preview / Download", expanded=True):
                _show_record_documents(obj, f"student_edit_docs_{selected_edit}")
            updated = _edit_complete_record(obj, f"edit_student_full_{selected_edit}", "Student")
            if updated is not None:
                for i, existing in enumerate(students):
                    if isinstance(existing, dict) and existing.get("id") == selected_edit:
                        students[i] = updated
                        break
                # Keep related student login name/email in sync when present.
                users = load("users")
                for user in users:
                    if isinstance(user, dict) and user.get("student_id") == selected_edit:
                        user["name"] = updated.get("name", user.get("name", ""))
                        user["email"] = updated.get("email", user.get("email", ""))
                save("users", users)
                save("students", students)
                log(current_user().get("username"), "Admission Cell", "STUDENT_FULL_UPDATE", selected_edit)
                flash_message("success", "Student ke saare saved fields update ho gaye.")
                st.rerun()

# ============================================================
# FACULTY MANAGEMENT (with EDIT)
# ============================================================
def page_faculty():
    if not guard("Admission Cell"): return
    page_header("Faculty Management", "Manage teaching staff")
    staff = load("staff")

    tab1, tab2 = st.tabs(["📋 All Faculty", "✏ Edit Faculty"])

    with tab1:
        # Search/filter faculty by name and the course attached to their assigned subjects.
        faculty_q = st.text_input("🔍 Search faculty by name / ID", key="faculty_search_name")
        faculty_course_filter = st.selectbox(
            "Filter by Course",
            ["All"] + list(course_map().keys()),
            format_func=lambda x: "All Courses" if x == "All" else course_map().get(x, x),
            key="faculty_filter_course",
        )
        subject_rows = [x for x in load("subjects") if isinstance(x, dict)]
        subject_by_id = {str(x.get("id")): x for x in subject_rows if x.get("id")}
        filtered_staff = [x for x in staff if isinstance(x, dict)]
        if faculty_q.strip():
            needle = faculty_q.strip().lower()
            filtered_staff = [
                x for x in filtered_staff
                if needle in str(x.get("name", "")).lower()
                or needle in str(x.get("id", "")).lower()
            ]
        if faculty_course_filter != "All":
            course_filtered = []
            for faculty in filtered_staff:
                assigned = faculty.get("subject_ids", []) or []
                if isinstance(assigned, str):
                    assigned = [assigned]
                assigned_courses = {
                    str(subject_by_id.get(str(sid), {}).get("course_id", ""))
                    for sid in assigned
                    if str(sid) in subject_by_id
                }
                # Also support older records that store course_id directly.
                if str(faculty.get("course_id", "")) == str(faculty_course_filter) or str(faculty_course_filter) in assigned_courses:
                    course_filtered.append(faculty)
            filtered_staff = course_filtered

        with st.expander("➕ Add New Faculty"):
            with st.form("add_staff"):
                c1, c2 = st.columns(2)
                tid = c1.text_input("Employee ID (Automatic)", value=next_employee_id(), disabled=True)
                name = c2.text_input("Name *")
                dept = c1.selectbox("Dept", ["CSE","ECE","ME","Civil","Science"])
                desig = c2.selectbox("Designation", ["Professor","Associate Professor","Assistant Professor","Lecturer"])
                email = c1.text_input("Email")
                phone = c2.text_input("Phone")
                qual = c1.text_input("Qualification")
                st.markdown("**Faculty Documents**")
                fdoc1, fdoc2, fdoc3 = st.columns(3)
                faculty_photo = fdoc1.file_uploader("Photo", type=["jpg", "jpeg", "png"], key="faculty_photo_new")
                faculty_id_doc = fdoc2.file_uploader("Identity Proof", type=["pdf", "jpg", "jpeg", "png"], key="faculty_id_new")
                faculty_qual_doc = fdoc3.file_uploader("Qualification Certificate", type=["pdf", "jpg", "jpeg", "png"], key="faculty_qual_new")
                fdoc1, fdoc2, fdoc3 = st.columns(3)
                faculty_exp_doc = fdoc1.file_uploader("Experience Certificate", type=["pdf", "jpg", "jpeg", "png"], key="faculty_exp_new")
                faculty_join_doc = fdoc2.file_uploader("Appointment / Joining Letter", type=["pdf", "jpg", "jpeg", "png"], key="faculty_join_new")
                faculty_other_doc = fdoc3.file_uploader("Other Document", type=["pdf", "jpg", "jpeg", "png"], key="faculty_other_new")
                subject_options = {x["id"]: f"{course_map().get(x.get('course_id'), x.get('course_id', 'Course'))} {int(x.get('semester',1))}{'st' if int(x.get('semester',1)) == 1 else 'nd' if int(x.get('semester',1)) == 2 else 'rd' if int(x.get('semester',1)) == 3 else 'th'} Sem — {x.get('code','')} — {x.get('name','')}" for x in load("subjects") if isinstance(x,dict) and x.get("id")}
                assigned_subject_ids = st.multiselect("Assigned Subjects / Classes", list(subject_options.keys()), format_func=lambda x: subject_options[x])
                uname = c1.text_input("Login Username")
                upwd = c2.text_input("Login Password", type="password")
                submitted_faculty = st.form_submit_button("➕ Add Faculty", type="primary")
                if submitted_faculty and not name.strip():
                    st.error("❌ Faculty name is required. Nothing was saved.")
                if submitted_faculty and name.strip():
                    staff.append({"id":tid,"name":name,"dept":dept,"designation":desig,
                                  "email":email,"phone":phone,"qualification":qual,
                                  "username":uname,"subject_ids":assigned_subject_ids,
                                  "documents": {"photo": save_file(faculty_photo), "identity": save_file(faculty_id_doc),
                                                "qualification": save_file(faculty_qual_doc), "experience": save_file(faculty_exp_doc),
                                                "appointment": save_file(faculty_join_doc), "other": save_file(faculty_other_doc)}})
                    save("staff", staff)
                    if uname and upwd:
                        users = load("users")
                        users.append({"username":uname,"password":hpw(upwd),"role":"Teacher",
                                      "name":name,"active":True,"staff_id":tid,"subject_ids":assigned_subject_ids})
                        save("users", users)
                    flash_message("success", "Added"); st.rerun()
        if filtered_staff:
            # Show readable assigned course/semester subjects in the faculty list.
            display_rows = []
            for faculty in filtered_staff:
                row = dict(faculty)
                assigned = faculty.get("subject_ids", []) or []
                if isinstance(assigned, str):
                    assigned = [assigned]
                labels = []
                for sid in assigned:
                    subj = subject_by_id.get(str(sid))
                    if not subj:
                        continue
                    course_name = course_map().get(subj.get("course_id"), subj.get("course_id", "Course"))
                    sem = subj.get("semester", "")
                    labels.append(f"{course_name} Sem {sem} — {subj.get('name', '')}")
                row["Assigned Courses / Subjects"] = "; ".join(labels)
                display_rows.append(row)
            st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
            with st.expander("📂 View Faculty Documents / Complete Record", expanded=False):
                doc_faculty_ids = [x.get("id") for x in filtered_staff if x.get("id")]
                if doc_faculty_ids:
                    doc_faculty_id = st.selectbox("Select faculty documents", doc_faculty_ids, format_func=lambda x: f"{x} — {staff_map().get(x, '')}", key="faculty_all_docs_select")
                    doc_faculty = next((x for x in filtered_staff if x.get("id") == doc_faculty_id), None)
                    if doc_faculty:
                        _show_record_documents(doc_faculty, f"faculty_all_docs_{doc_faculty_id}")
                        st.markdown("**All saved faculty fields**")
                        for path, value in _flatten_record(doc_faculty):
                            if _is_document_field(path, value) and isinstance(value, str) and value:
                                st.write(f"**{_field_label(path)}:** `{Path(value).name}`")
                            else:
                                st.write(f"**{_field_label(path)}:** {json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, (dict, list)) else (value if value is not None else '')}")
        else:
            st.info("Is name/course filter ke liye koi faculty record nahi mila.")

    with tab2:
        if not staff:
            st.info("No faculty records yet. Add faculty first.")
        else:
            st.markdown("**Filter Faculty Records**")
            fe1, fe2 = st.columns([2, 1])
            faculty_edit_q = fe1.text_input("Search faculty by name / ID / email / phone", key="faculty_complete_edit_search")
            faculty_edit_course = fe2.selectbox("Course", ["All"] + list(course_map().keys()), format_func=lambda x: "All Courses" if x == "All" else course_map().get(x, x), key="faculty_complete_edit_course")
            all_subjects_for_edit = [x for x in load("subjects") if isinstance(x, dict)]
            subj_by_id_for_edit = {str(x.get("id")): x for x in all_subjects_for_edit if x.get("id")}
            filtered_faculty_edit = [x for x in staff if isinstance(x, dict) and x.get("id")]
            if faculty_edit_q.strip():
                needle = faculty_edit_q.strip().lower()
                filtered_faculty_edit = [x for x in filtered_faculty_edit if needle in " ".join(str(x.get(k, "")) for k in ("id", "name", "email", "phone", "dept", "designation")).lower()]
            if faculty_edit_course != "All":
                keep = []
                for faculty in filtered_faculty_edit:
                    assigned = faculty.get("subject_ids", []) or []
                    if isinstance(assigned, str): assigned = [assigned]
                    assigned_courses = {str(subj_by_id_for_edit.get(str(sid), {}).get("course_id", "")) for sid in assigned if str(sid) in subj_by_id_for_edit}
                    if str(faculty.get("course_id", "")) == str(faculty_edit_course) or str(faculty_edit_course) in assigned_courses:
                        keep.append(faculty)
                filtered_faculty_edit = keep
            staff_ids = [x.get("id") for x in filtered_faculty_edit]
            if not staff_ids:
                st.info("Is filter ke liye koi faculty record nahi mila.")
                tid = None
            else:
                tid = st.selectbox("Select Faculty", staff_ids, format_func=lambda x: f"{x} — {staff_map().get(x, '')}", key="faculty_full_edit_id")
            t = next((x for x in staff if isinstance(x, dict) and x.get("id") == tid), None) if tid else None
            if t:
                st.subheader(f"{t.get('name', '')} — {t.get('id', '')}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Department", str(t.get("dept", "—")))
                c2.metric("Designation", str(t.get("designation", "—")))
                c3.metric("Email", str(t.get("email", "—")))
                with st.expander("📄 Existing Faculty Documents — Preview / Download", expanded=True):
                    _show_record_documents(t, f"faculty_docs_{tid}")
                with st.expander("🧾 Complete Saved Faculty Data", expanded=True):
                    for path, value in _flatten_record(t):
                        if _is_document_field(path, value) and isinstance(value, str) and value:
                            st.write(f"**{_field_label(path)}:** `{Path(value).name}`")
                        else:
                            st.write(f"**{_field_label(path)}:** {json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, (dict, list)) else (value if value is not None else '')}")
                updated = _edit_complete_record(t, f"edit_faculty_full_{tid}", "Faculty")
                if updated is not None:
                    for i, existing in enumerate(staff):
                        if isinstance(existing, dict) and existing.get("id") == tid:
                            staff[i] = updated
                            break
                    users = load("users")
                    for user in users:
                        if isinstance(user, dict) and user.get("role") == "Teacher" and (user.get("staff_id") == tid or user.get("username") == updated.get("username")):
                            user["name"] = updated.get("name", user.get("name", ""))
                            user["subject_ids"] = updated.get("subject_ids", user.get("subject_ids", []))
                    save("users", users)
                    save("staff", staff)
                    log(current_user().get("username"), "Admission Cell", "FACULTY_FULL_UPDATE", tid)
                    flash_message("success", "Faculty ke saare saved fields update ho gaye.")
                    st.rerun()

# ============================================================
# NON-TEACHING STAFF
# ============================================================
def page_non_teaching():
    if not guard("Admission Cell"): return
    page_header("Non-Teaching Staff", "Drivers, Peons, Clerk, Admin Staff, etc.")
    nt = load("non_teaching")

    tab1, tab2 = st.tabs(["📋 All Staff", "✏ Edit Staff"])

    with tab1:
        with st.expander("➕ Add Non-Teaching Staff"):
            with st.form("add_nt"):
                c1, c2 = st.columns(2)
                nid_val = c1.text_input("Employee ID (Automatic)", value=next_employee_id(), disabled=True)
                name = c2.text_input("Name *")
                role_type = c1.selectbox("Role", ["Driver","Peon","Clerk","Admin Staff","Security","Cleaner","Lab Assistant","Librarian Assistant","Other"])
                phone = c2.text_input("Phone")
                email = c1.text_input("Email")
                designation = c2.text_input("Designation")
                qualification = c1.text_input("Qualification")
                joining_date = c2.date_input("Joining Date", value=date.today())
                salary = c2.number_input("Monthly Salary (₹)", 0, 1_000_000, 15000)
                st.markdown("**Staff Documents**")
                nt_photo = st.file_uploader("Photo", type=["jpg", "jpeg", "png"], key="nt_photo")
                nt_id_doc = st.file_uploader("Identity Proof", type=["pdf", "jpg", "png"], key="nt_id_doc")
                nt_qual_doc = st.file_uploader("Qualification Certificate", type=["pdf", "jpg", "png"], key="nt_qual_doc")
                nt_appoint_doc = st.file_uploader("Appointment Letter", type=["pdf", "jpg", "png"], key="nt_appoint_doc")
                nt_other_doc = st.file_uploader("Other Document", type=["pdf", "jpg", "png"], key="nt_other_doc")
                uname = c1.text_input("Login Username (optional)")
                upwd = c2.text_input("Login Password", type="password")
                submitted_nt = st.form_submit_button("➕ Add Staff", type="primary")
                if submitted_nt and not name.strip():
                    st.error("❌ Staff name is required. Nothing was saved.")
                if submitted_nt and name.strip():
                    nt.append({"id":nid_val,"name":name,"role":role_type, "designation":designation,
                               "qualification":qualification,"joining_date":str(joining_date),
                               "phone":phone,"email":email,"salary":salary,
                               "documents":{"photo":save_file(nt_photo, PHOTOS_DIR),"identity":save_file(nt_id_doc),
                                            "qualification":save_file(nt_qual_doc),"appointment":save_file(nt_appoint_doc),
                                            "other":save_file(nt_other_doc)}})
                    save("non_teaching", nt)
                    if uname and upwd:
                        users = load("users")
                        users.append({"username":uname,"password":hpw(upwd),"role":"Non-Teaching",
                                      "name":name,"active":True})
                        save("users", users)
                    flash_message("success", "Added"); st.rerun()
        if nt:
            st.dataframe(pd.DataFrame([n for n in nt if isinstance(n,dict)]),
                         use_container_width=True, hide_index=True)
            with st.expander("📂 View Staff Documents / Complete Record", expanded=False):
                doc_nt_ids = [x.get("id") for x in nt if isinstance(x, dict) and x.get("id")]
                if doc_nt_ids:
                    doc_nt_id = st.selectbox("Select staff documents", doc_nt_ids, format_func=lambda x: f"{x} — {non_teaching_map().get(x, '')}", key="nt_all_docs_select")
                    doc_nt = next((x for x in nt if isinstance(x, dict) and x.get("id") == doc_nt_id), None)
                    if doc_nt:
                        _show_record_documents(doc_nt, f"nt_all_docs_{doc_nt_id}")
                        st.markdown("**All saved staff fields**")
                        for path, value in _flatten_record(doc_nt):
                            if _is_document_field(path, value) and isinstance(value, str) and value:
                                st.write(f"**{_field_label(path)}:** `{Path(value).name}`")
                            else:
                                st.write(f"**{_field_label(path)}:** {json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, (dict, list)) else (value if value is not None else '')}")

    with tab2:
        if not nt:
            st.info("No non-teaching staff records yet.")
        else:
            st.markdown("**Filter Non-Teaching Staff Records**")
            ns1, ns2 = st.columns([2, 1])
            nt_q = ns1.text_input("Search staff by name / ID / phone / email", key="nt_complete_search")
            nt_role_filter = ns2.selectbox("Staff Role", ["All"] + sorted({str(x.get("role", "Other")) for x in nt if isinstance(x, dict)}), key="nt_complete_role_filter")
            filtered_nt = [x for x in nt if isinstance(x, dict) and x.get("id")]
            if nt_q.strip():
                needle = nt_q.strip().lower()
                filtered_nt = [x for x in filtered_nt if needle in " ".join(str(x.get(k, "")) for k in ("id", "name", "phone", "email", "designation")).lower()]
            if nt_role_filter != "All":
                filtered_nt = [x for x in filtered_nt if str(x.get("role", "Other")) == nt_role_filter]
            nt_ids = [x.get("id") for x in filtered_nt]
            if not nt_ids:
                st.info("Is filter ke liye koi non-teaching staff record nahi mila.")
                nid_sel = None
            else:
                nid_sel = st.selectbox("Select Non-Teaching Staff", nt_ids, format_func=lambda x: f"{x} — {non_teaching_map().get(x, '')}", key="nt_full_edit_id")
            obj = next((x for x in nt if isinstance(x, dict) and x.get("id") == nid_sel), None) if nid_sel else None
            if obj:
                st.subheader(f"{obj.get('name', '')} — {obj.get('id', '')}")
                with st.expander("📄 Existing Staff Documents — Preview / Download", expanded=True):
                    _show_record_documents(obj, f"nt_docs_{nid_sel}")
                with st.expander("🧾 Complete Saved Staff Data", expanded=True):
                    for path, value in _flatten_record(obj):
                        if _is_document_field(path, value) and isinstance(value, str) and value:
                            st.write(f"**{_field_label(path)}:** `{Path(value).name}`")
                        else:
                            st.write(f"**{_field_label(path)}:** {json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, (dict, list)) else (value if value is not None else '')}")
                updated = _edit_complete_record(obj, f"edit_nt_full_{nid_sel}", "Non-Teaching Staff")
                if updated is not None:
                    for i, existing in enumerate(nt):
                        if isinstance(existing, dict) and existing.get("id") == nid_sel:
                            nt[i] = updated
                            break
                    save("non_teaching", nt)
                    log(current_user().get("username"), "Admission Cell", "NON_TEACHING_FULL_UPDATE", nid_sel)
                    flash_message("success", "Non-teaching staff ke saare saved fields update ho gaye.")
                    st.rerun()

# ============================================================
# ATTENDANCE
# ============================================================
def page_attendance():
    page_header("Attendance", "Mark / View")
    role = current_role()
    students = [s for s in load("students") if isinstance(s,dict) and s.get("id")]
    cm = course_map()
    sm = subject_map()

    if role in ("Teacher","Admin") or is_admin():
        tab1, tab2 = st.tabs(["✏ Mark", "📊 View"])
        with tab1:
            c1, c2 = st.columns(2)
            course = c1.selectbox("Course", list(cm.keys()), format_func=lambda x: cm[x])
            sem = c2.number_input("Semester", 1, 8, 1)
            subs = [s for s in load("subjects") if s.get("course_id")==course and s.get("semester")==sem]
            if not subs: st.warning("No subjects"); return
            sub_map = {s["id"]: f"{s['code']} — {s['name']}" for s in subs}
            sub = st.selectbox("Subject", list(sub_map.keys()), format_func=lambda x: sub_map[x])
            d = st.date_input("Date", value=date.today())
            class_students = [s for s in students if s.get("course_id")==course and s.get("semester")==sem]
            if not class_students: st.warning("No students"); return
            marks = {}
            for s in class_students:
                marks[s["id"]] = st.checkbox(f"{s['id']} — {s['name']}", value=True,
                                              key=f"att_{s['id']}_{d}_{sub}")
            if st.button("💾 Save Attendance", type="primary"):
                att = load("attendance")
                att = [a for a in att if not (isinstance(a,dict) and
                       a.get("date")==str(d) and a.get("subject_id")==sub)]
                for s in class_students:
                    att.append({"id":nid("A"),"date":str(d),"subject_id":sub,
                                "student_id":s["id"],
                                "status":"Present" if marks[s["id"]] else "Absent",
                                "by":current_user()["username"],"ts":now()})
                save("attendance", att); flash_message("success", "Saved"); st.rerun()

        with tab2:
            c1, c2 = st.columns(2)
            date_f = c1.date_input("Date", value=date.today(), key="df")
            att = [a for a in load("attendance") if isinstance(a,dict)]
            att = [a for a in att if a.get("date")==str(date_f)]
            if att:
                df = pd.DataFrame(att)
                df["student"] = df["student_id"].map(student_map())
                df["subject"] = df["subject_id"].map(sm)
                st.dataframe(df, use_container_width=True, hide_index=True)
                csv_dl(df, "attendance", "att_dl")
            else:
                st.info("No records for this date")

# ============================================================
# MARKS
# ============================================================
def page_marks():
    page_header("Marks & Results", "Enter / View")
    role = current_role()
    students = [s for s in load("students") if isinstance(s,dict) and s.get("id")]
    cm = course_map()

    if role in ("Teacher","Admin") or is_admin():
        tab1, tab2 = st.tabs(["✏ Enter", "📊 View"])
        with tab1:
            c1, c2 = st.columns(2)
            course = c1.selectbox("Course", list(cm.keys()), format_func=lambda x: cm[x])
            sem = c2.number_input("Semester", 1, 8, 1)
            subs = [s for s in load("subjects") if s.get("course_id")==course and s.get("semester")==sem]
            if not subs: st.warning("No subjects"); return
            sub_map = {s["id"]: f"{s['code']} — {s['name']}" for s in subs}
            sub = st.selectbox("Subject", list(sub_map.keys()), format_func=lambda x: sub_map[x])
            selected_subject = next((x for x in subs if x.get("id") == sub), {})
            subject_max = int(selected_subject.get("max_marks", 100) or 100)
            st.info(f"Maximum marks for this subject: **{subject_max}**")
            exam = st.selectbox("Exam", ["Internal-1","Internal-2","Midterm","Final"])
            class_students = [s for s in students if s.get("course_id")==course and s.get("semester")==sem]
            if not class_students: st.warning("No students"); return
            mks = {}
            for s in class_students:
                mks[s["id"]] = st.number_input(f"{s['id']} — {s['name']}",
                    min_value=0, max_value=subject_max, value=0, key=f"mk_{s['id']}_{sub}_{exam}")
            if st.button("💾 Save Marks", type="primary"):
                marks = load("marks")
                marks = [m for m in marks if not (isinstance(m,dict) and
                         m.get("subject_id")==sub and m.get("exam")==exam)]
                for s in class_students:
                    marks.append({"id":nid("M"),"subject_id":sub,"student_id":s["id"],
                                  "exam":exam,"marks":mks[s["id"]],"max":subject_max,"ts":now()})
                save("marks", marks); flash_message("success", "Saved"); st.rerun()

        with tab2:
            c1, c2 = st.columns(2)
            course_f = c1.selectbox("Course", ["All"]+list(cm.keys()),
                                    format_func=lambda x: "All" if x=="All" else cm[x], key="mf")
            exam_f = c2.selectbox("Exam", ["All","Internal-1","Internal-2","Midterm","Final"])
            marks = [m for m in load("marks") if isinstance(m,dict)]
            sm = subject_map()
            if exam_f != "All":
                marks = [m for m in marks if m.get("exam")==exam_f]
            if marks:
                df = pd.DataFrame(marks)
                df["student"] = df["student_id"].map(student_map())
                df["subject"] = df["subject_id"].map(sm)
                st.dataframe(df, use_container_width=True, hide_index=True)
                xlsx_dl(df, "marks", "mk_xl")
            else: st.info("No marks")

# ============================================================
# FEES (Accountant — Update also)
# ============================================================
def page_teacher_fees():
    if not guard("Teacher"): return
    page_header("Student Fee Overview", "Read-only fee status for students in your assigned classes")
    user = current_user() or {}
    staff_rows = [x for x in load("staff") if isinstance(x, dict)]
    staff = next((x for x in staff_rows if x.get("username") == user.get("username") or x.get("id") == user.get("staff_id")), None)
    assigned_subjects = set((staff or {}).get("subject_ids", user.get("subject_ids", [])) or [])
    subjects = [x for x in load("subjects") if isinstance(x, dict)]
    assigned = [x for x in subjects if x.get("id") in assigned_subjects]
    if not assigned:
        st.info("Is teacher ke liye subjects assign nahi hain. Admin → Faculty mein teacher ke subjects assign karein; tab sirf unhi classes ke students ki fee status dikhegi.")
        return
    class_keys = {(x.get("course_id"), int(x.get("semester", 1))) for x in assigned}
    students = [x for x in load("students") if isinstance(x, dict) and (x.get("course_id"), int(x.get("semester", 1))) in class_keys]
    fees = [x for x in load("fees") if isinstance(x, dict)]
    rows = []
    for student in students:
        sid = student.get("id")
        paid = sum(float(f.get("amount", 0) or 0) for f in fees if f.get("student_id") == sid)
        total = float(student.get("final_fee", 0) or 0)
        rows.append({"Student ID": sid, "Name": student.get("name", ""),
                     "Course": course_map().get(student.get("course_id"), student.get("course_id", "")),
                     "Semester": student.get("semester", ""), "Total Payable": total,
                     "Paid": paid, "Due": max(0, total-paid),
                     "Status": "Paid" if paid >= total else ("Partial" if paid > 0 else "Unpaid")})
    if rows:
        df = pd.DataFrame(rows)
        c1, c2, c3 = st.columns(3)
        c1.metric("Students", len(rows))
        c2.metric("Total Paid", f"₹{df['Paid'].sum():,.2f}")
        c3.metric("Total Due", f"₹{df['Due'].sum():,.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)
        xlsx_dl(df, "teacher_fee_overview", "teacher_fee_export")
    else:
        st.info("Assigned courses/semesters mein abhi students nahi hain.")


def page_fees():
    if not guard("Accountant"): return
    page_header("Fee Management", "Collect & Manage fees")
    students = [s for s in load("students") if isinstance(s,dict) and s.get("id")]
    cm = course_map()
    sm = {s["id"]:s.get("name","") for s in students}
    fees = [f for f in load("fees") if isinstance(f,dict)]

    tab1, tab2, tab3 = st.tabs(["💳 Collect Fee", "📊 Fee Status", "✏ Update Fee Data"])

    with tab1:
        q = st.text_input("🔍 Search student by name / ID")
        filt = [s for s in students if q.lower() in (s.get("name","")+s.get("id","")).lower()] if q else students
        if not filt: st.info("No match"); return
        sid = st.selectbox("Select student", [s["id"] for s in filt],
                           format_func=lambda x: f"{x} — {sm.get(x,'')}")
        stu = next((s for s in filt if s["id"]==sid), None)
        if stu:
            total_fee = stu.get("final_fee", 0)
            paid = sum(f.get("amount",0) for f in fees if f.get("student_id")==sid)
            due = total_fee - paid
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Fee", f"₹{total_fee:,}")
            c2.metric("Paid", f"₹{paid:,}")
            c3.metric("Due", f"₹{due:,}")
            with st.form("pay"):
                amt = st.number_input("Amount (₹)", 0, 10_000_000, max(0,int(due)))
                mode = st.selectbox("Mode", ["Cash","UPI","Card","NEFT/RTGS","Cheque","DD"])
                note = st.text_input("Note")
                submitted_payment = st.form_submit_button("✅ Record Payment", type="primary")
                if submitted_payment and amt <= 0: st.error("❌ Enter a payment amount greater than zero.")
                if submitted_payment and amt > 0:
                    fees.append({"id":nid("R"),"student_id":sid,"amount":amt,
                                 "mode":mode,"note":note,"ts":now(),
                                 "by":current_user()["username"]})
                    save("fees", fees)
                    flash_message("success", f"✅ Receipt: {fees[-1]['id']}"); st.rerun()

    with tab2:
        rows = []
        for s in students:
            paid = sum(f.get("amount",0) for f in fees if f.get("student_id")==s["id"])
            total = s.get("final_fee", 0)
            rows.append({"Student":s.get("name",""),"ID":s["id"],
                         "Total":total,"Paid":paid,"Due":total-paid,
                         "Status":"Paid" if paid>=total else ("Partial" if paid>0 else "Unpaid")})
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            xlsx_dl(df, "fees_status", "fee_xl")

    with tab3:
        st.subheader("✏ Update Student Fee Data")
        sid_e = st.selectbox("Select student", [s["id"] for s in students],
                             format_func=lambda x: f"{x} — {sm.get(x,'')}", key="fee_edit")
        stu_e = next((s for s in students if s["id"]==sid_e), None)
        if stu_e:
            with st.form("edit_fee"):
                c1, c2 = st.columns(2)
                base = c1.number_input("Base Fee", 0, 10_000_000, int(stu_e.get("base_fee",0)))
                disc = c2.number_input("Discount %", 0.0, 100.0, float(stu_e.get("discount_pct",0)))
                optional_total = sum(float(v or 0) for v in (stu_e.get("optional_charges", {}) or {}).values())
                final = max(0, base * (1 - disc/100) + optional_total)
                st.info(f"Final Fee (including optional charges): ₹{final:,.2f}")
                if st.form_submit_button("💾 Update", type="primary"):
                    stu_e["base_fee"] = base
                    stu_e["discount_pct"] = disc
                    stu_e["final_fee"] = round(final, 2)
                    save("students", students)
                    flash_message("success", "Updated"); st.rerun()

# ============================================================
# BILLS & OTHER CHARGES
# ============================================================
def page_bills():
    if not guard("Accountant"): return
    page_header("Accounts, Bills & Expenses", "Track income, expenses, employee salary payments, invoices and supporting bills")

    bills = [b for b in load("bills") if isinstance(b, dict)]
    students = [x for x in load("students") if isinstance(x, dict) and x.get("id")]
    teaching = [x for x in load("staff") if isinstance(x, dict) and x.get("id")]
    non_teaching = [x for x in load("non_teaching") if isinstance(x, dict) and x.get("id")]
    employees = [(str(x.get("id")), x.get("name", "Employee"), "Teaching") for x in teaching]
    employees += [(str(x.get("id")), x.get("name", "Employee"), "Non-Teaching") for x in non_teaching]
    student_names = {str(x.get("id")): x.get("name", "") for x in students}
    employee_map = {str(eid): (name, typ) for eid, name, typ in employees}

    income_categories = ["Student Fee Collection", "Admission Fee", "Tuition Fee", "Examination Fee",
        "Library Fee/Fine", "Hostel Fee", "Transport Fee", "Laboratory Fee", "Canteen Income",
        "Grant/Funding", "Donation", "Interest Income", "Other Income"]
    expense_categories = ["Electricity Bill", "Water Bill", "Internet/Wi-Fi Bill", "Telephone/Mobile Bill",
        "Employee Salary", "Staff Allowance/Bonus", "Building Rent", "Building Maintenance/Repair",
        "Cleaning/Sanitation", "Security Services", "Stationery/Office Supplies", "Printing/Photocopy",
        "Computer/IT Equipment", "Software/Cloud Services", "Laboratory Equipment/Supplies",
        "Library Books/Journals", "Furniture", "Vehicle/Fuel/Transport", "Travel/Conveyance",
        "Exam Paper/Printing/Exam Expenses", "Events/Functions", "Sports/Cultural Activities",
        "Hostel/Mess Supplies", "Medical/First Aid", "Taxes/Government Fees", "Insurance",
        "Marketing/Advertisement", "Bank Charges", "Professional/Legal/Audit Fees",
        "Water Tanker", "Waste Disposal", "Other Expense"]

    def money(value):
        try: return float(value or 0)
        except (ValueError, TypeError): return 0.0

    # Cash totals include only actual receipts/payments, not unpaid invoices.
    received = sum(money(b.get("amount")) for b in bills
                   if b.get("entry_kind") == "Income" and b.get("status") in ("Received", "Paid"))
    paid_expenses = sum(money(b.get("amount")) for b in bills
                        if b.get("entry_kind") == "Expense" and b.get("status") == "Paid")
    unpaid_expenses = sum(money(b.get("amount")) for b in bills
                          if b.get("entry_kind") == "Expense" and b.get("status") == "Unpaid")
    net = received - paid_expenses
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Income Received", f"₹{received:,.2f}")
    m2.metric("Expenses Paid", f"₹{paid_expenses:,.2f}")
    m3.metric("Unpaid Expenses", f"₹{unpaid_expenses:,.2f}")
    m4.metric("Net Profit / Loss", f"₹{net:,.2f}", delta="Profit" if net >= 0 else "Loss")
    st.caption("Profit/loss shown here = recorded income received minus expenses marked Paid. Unpaid bills are shown separately.")

    tab1, tab2, tab3 = st.tabs(["📚 Ledger & Bills", "➕ Add Entry", "✏️ Edit Entry"])

    with tab1:
        if not bills:
            st.info("No account entries yet. Use Add Entry to record income, expenses, salaries or student bills.")
        else:
            rows = []
            for b in bills:
                row = dict(b)
                row["student_name"] = student_names.get(str(b.get("student_id", "")), "")
                eid = str(b.get("employee_id", ""))
                row["employee_name"] = b.get("employee_name") or employee_map.get(eid, ("", ""))[0]
                row["record_type"] = b.get("entry_kind", "Student Bill" if b.get("student_id") else "Legacy Entry")
                row["attachment"] = "Attached" if b.get("attachment_data") else "—"
                rows.append(row)
            display_cols = [c for c in ["id", "record_type", "type", "category", "student_name", "employee_name",
                "employee_id", "amount", "status", "date", "note", "attachment"] if any(c in r for r in rows)]
            st.dataframe(pd.DataFrame(rows)[display_cols], use_container_width=True, hide_index=True)
            # Show receipt/invoice image for the selected record, when present.
            ids = [str(b.get("id")) for b in bills if b.get("id")]
            if ids:
                view_id = st.selectbox("View attached bill / receipt", ["— Select —"] + ids, key="view_bill_attachment")
                record = next((b for b in bills if str(b.get("id")) == view_id), None)
                if record and record.get("attachment_data"):
                    try:
                        st.image(base64.b64decode(record["attachment_data"]), caption=record.get("attachment_name", "Attached bill"), use_container_width=True)
                        st.download_button("⬇ Download attachment", base64.b64decode(record["attachment_data"]),
                            file_name=record.get("attachment_name") or "bill_attachment", key=f"download_attachment_{view_id}")
                    except Exception:
                        st.warning("This attachment could not be displayed. Try downloading it from the record.")

    with tab2:
        entry_kind = st.selectbox("Entry Type", ["Expense", "Income", "Student Bill"],
            help="Income is money received; Expense is money paid/payable; Student Bill is a student invoice/charge.")
        c1, c2 = st.columns(2)
        if entry_kind == "Income":
            category = c1.selectbox("Income Type", income_categories)
        elif entry_kind == "Expense":
            category = c1.selectbox("Expense Type", expense_categories)
        else:
            category = c1.selectbox("Student Bill Type", ["Tuition Fee", "Admission Fee", "Examination Fee",
                "Library Fee/Fine", "Hostel Charges", "Transport Charges", "Laboratory Fee", "Other Student Charge"])
        amount = c2.number_input("Amount (₹)", min_value=0.0, max_value=100000000.0, value=0.0, step=500.0)
        c1, c2 = st.columns(2)
        entry_date = c1.date_input("Entry Date", value=date.today())
        status_options = ["Received", "Pending", "Cancelled"] if entry_kind == "Income" else (["Paid", "Unpaid", "Cancelled"] if entry_kind == "Expense" else ["Unpaid", "Paid", "Cancelled"])
        status = c2.selectbox("Payment / Bill Status", status_options, index=0 if entry_kind in ("Income", "Expense") else 0)
        note = st.text_area("Description / Notes", placeholder="Vendor, bill number, purpose, payment reference, etc.")

        student_id = ""
        employee_id = ""
        employee_name = ""
        custom_category = ""
        if category in ("Other Expense", "Other Income", "Other Student Charge"):
            custom_category = st.text_input("Specify expense/income type", placeholder="e.g. campus generator repair")
        if entry_kind == "Student Bill":
            if students:
                student_id = st.selectbox("Student", [str(x["id"]) for x in students],
                    format_func=lambda x: f"{x} — {student_names.get(x, '')}")
            else:
                st.warning("No student records found. You can still record general university income/expenses.")
        if entry_kind == "Expense" and category == "Employee Salary":
            if employees:
                employee_id = st.selectbox("Employee ID", [e[0] for e in employees],
                    format_func=lambda x: f"{x} — {employee_map.get(x, ('Unknown', ''))[0]} ({employee_map.get(x, ('', ''))[1]})")
                employee_name = employee_map.get(employee_id, ("", ""))[0]
                st.info(f"Salary payment employee: {employee_name} · ID: {employee_id}")
            else:
                st.warning("No teaching/non-teaching employee records found. Add employee records first.")
        uploaded = st.file_uploader("Attach bill / receipt image (optional)", type=["png", "jpg", "jpeg", "webp"], key="new_account_attachment")
        submit = st.button("💾 Save Account Entry", type="primary", use_container_width=True)
        if submit:
            if amount <= 0:
                st.error("Amount must be greater than zero.")
            elif entry_kind == "Student Bill" and not student_id:
                st.error("Select a student before creating a student bill.")
            elif category in ("Other Expense", "Other Income", "Other Student Charge") and not custom_category.strip():
                st.error("Please specify the Other expense/income type.")
            elif entry_kind == "Expense" and category == "Employee Salary" and not employee_id:
                st.error("Select an employee for salary payment.")
            else:
                with st.spinner("Saving account entry..."):
                    entry_id = nid("BL")
                    attach_data, attach_name, attach_mime = "", "", ""
                    if uploaded is not None:
                        attach_data = base64.b64encode(uploaded.getvalue()).decode("ascii")
                        attach_name, attach_mime = uploaded.name, uploaded.type or "application/octet-stream"
                    final_category = custom_category.strip() if custom_category.strip() else category
                    entry = {"id": entry_id, "entry_kind": entry_kind, "type": final_category,
                        "category": final_category, "amount": float(amount), "status": status,
                        "date": entry_date.isoformat(), "note": note.strip(), "student_id": student_id,
                        "employee_id": employee_id, "employee_name": employee_name,
                        "attachment_data": attach_data, "attachment_name": attach_name,
                        "attachment_mime": attach_mime, "ts": now(),
                        "created_by": current_user().get("username", "")}
                    bills.append(entry)
                    save("bills", bills)
                flash_message("success", f"Account entry {entry_id} saved successfully.")
                st.rerun()

    with tab3:
        if not bills:
            st.info("There are no entries to edit yet.")
        else:
            edit_ids = [str(b.get("id")) for b in bills if b.get("id")]
            edit_id = st.selectbox("Select entry to edit", edit_ids, key="edit_account_entry_id")
            selected = next((b for b in bills if str(b.get("id")) == edit_id), {})
            st.caption(f"Editing record {edit_id}. Existing attachment will be kept unless you upload a replacement.")
            kind_default = selected.get("entry_kind", "Student Bill" if selected.get("student_id") else "Expense")
            c1, c2 = st.columns(2)
            edit_kind = c1.selectbox("Entry Type", ["Expense", "Income", "Student Bill"],
                index=["Expense", "Income", "Student Bill"].index(kind_default) if kind_default in ["Expense", "Income", "Student Bill"] else 0)
            current_category = selected.get("category", selected.get("type", "Other Expense"))
            if edit_kind == "Income":
                categories = income_categories
            elif edit_kind == "Expense":
                categories = expense_categories
            else:
                categories = ["Tuition Fee", "Admission Fee", "Examination Fee", "Library Fee/Fine", "Hostel Charges", "Transport Charges", "Laboratory Fee", "Other Student Charge"]
            if current_category not in categories:
                categories = categories + [current_category]
            edit_category = c2.selectbox("Category", categories, index=categories.index(current_category))
            c1, c2 = st.columns(2)
            edit_amount = c1.number_input("Amount (₹)", min_value=0.0, max_value=100000000.0, value=money(selected.get("amount")), step=500.0)
            current_status = selected.get("status", "Unpaid")
            edit_status_options = ["Received", "Pending", "Cancelled"] if edit_kind == "Income" else ["Paid", "Unpaid", "Cancelled"]
            if current_status not in edit_status_options: edit_status_options.append(current_status)
            edit_status = c2.selectbox("Status", edit_status_options, index=edit_status_options.index(current_status))
            date_value = selected.get("date", date.today().isoformat())
            try: parsed_date = date.fromisoformat(str(date_value)[:10])
            except ValueError: parsed_date = date.today()
            edit_date = st.date_input("Entry Date", value=parsed_date)
            edit_note = st.text_area("Description / Notes", value=str(selected.get("note", "")))
            edit_student_id = ""
            if edit_kind == "Student Bill" and students:
                existing_sid = str(selected.get("student_id", students[0]["id"]))
                student_ids = [str(x["id"]) for x in students]
                if existing_sid not in student_ids: student_ids.append(existing_sid)
                edit_student_id = st.selectbox("Student", student_ids, index=student_ids.index(existing_sid),
                    format_func=lambda x: f"{x} — {student_names.get(x, '')}")
            edit_employee_id = str(selected.get("employee_id", ""))
            edit_employee_name = str(selected.get("employee_name", ""))
            if edit_kind == "Expense" and edit_category == "Employee Salary" and employees:
                emp_ids = [e[0] for e in employees]
                if edit_employee_id not in emp_ids: emp_ids.append(edit_employee_id)
                edit_employee_id = st.selectbox("Employee ID", emp_ids,
                    index=emp_ids.index(edit_employee_id) if edit_employee_id in emp_ids else 0,
                    format_func=lambda x: f"{x} — {employee_map.get(x, (edit_employee_name, ''))[0]}")
                edit_employee_name = employee_map.get(edit_employee_id, (edit_employee_name, ""))[0]
            replacement = st.file_uploader("Replace bill / receipt attachment (optional)", type=["png", "jpg", "jpeg", "webp"], key=f"replace_attachment_{edit_id}")
            delete_attachment = st.checkbox("Remove existing attachment", value=False, key=f"remove_attachment_{edit_id}")
            save_edit = st.button("💾 Save Changes", type="primary", use_container_width=True)
            if save_edit:
                if edit_amount <= 0:
                    st.error("Amount must be greater than zero.")
                else:
                    with st.spinner("Updating account entry..."):
                        for b in bills:
                            if str(b.get("id")) == edit_id:
                                b.update({"entry_kind": edit_kind, "type": edit_category, "category": edit_category,
                                    "amount": float(edit_amount), "status": edit_status, "date": edit_date.isoformat(),
                                    "note": edit_note.strip(), "student_id": edit_student_id,
                                    "employee_id": edit_employee_id, "employee_name": edit_employee_name,
                                    "updated_at": now()})
                                if delete_attachment:
                                    b["attachment_data"], b["attachment_name"], b["attachment_mime"] = "", "", ""
                                if replacement is not None:
                                    b["attachment_data"] = base64.b64encode(replacement.getvalue()).decode("ascii")
                                    b["attachment_name"] = replacement.name
                                    b["attachment_mime"] = replacement.type or "application/octet-stream"
                        save("bills", bills)
                    flash_message("success", f"Account entry {edit_id} updated successfully.")
                    st.rerun()

# ============================================================
# SALARY MANAGEMENT
# ============================================================
def _salary_slip_download(slip, employee_name, employee_type, college_name):
    """Return a downloadable salary slip; use PDF when ReportLab is installed, HTML otherwise."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=48, leftMargin=48, topMargin=48, bottomMargin=48)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("SlipTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#1d4ed8"))
        story = [Paragraph(html.escape(str(college_name or "College")), title_style),
                 Paragraph("SALARY SLIP", ParagraphStyle("SlipSub", parent=styles["Heading2"], alignment=TA_CENTER)),
                 Spacer(1, 18)]
        details = [
            ["Slip ID", str(slip.get("id", "")), "Pay Period", f'{slip.get("month", "")} {slip.get("year", "")}'],
            ["Employee Name", str(employee_name or ""), "Employee ID", str(slip.get("employee_id", ""))],
            ["Employee Type", str(employee_type or ""), "Generated On", str(slip.get("ts", ""))],
        ]
        details_table = Table(details, colWidths=[95, 155, 90, 155])
        details_table.setStyle(TableStyle([("GRID", (0,0), (-1,-1), .5, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#eff6ff")),
            ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#eff6ff")),
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 9), ("BOTTOMPADDING", (0,0), (-1,-1), 9)]))
        story += [details_table, Spacer(1, 22)]
        pay_rows = [["Earnings / Deductions", "Amount (INR)"],
                    ["Basic Salary", f'{float(slip.get("basic", 0) or 0):,.2f}'],
                    ["Allowance", f'{float(slip.get("allowance", 0) or 0):,.2f}'],
                    ["Deductions", f'-{float(slip.get("deduction", 0) or 0):,.2f}'],
                    ["NET SALARY", f'{float(slip.get("net", 0) or 0):,.2f}']]
        pay_table = Table(pay_rows, colWidths=[330, 165])
        pay_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1d4ed8")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), .5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (1,1), (1,-1), "RIGHT"), ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#dbeafe")),
            ("TOPPADDING", (0,0), (-1,-1), 10), ("BOTTOMPADDING", (0,0), (-1,-1), 10)]))
        story += [pay_table, Spacer(1, 36), Paragraph("This is a computer-generated salary slip.", styles["Italic"])]
        doc.build(story)
        return buffer.getvalue(), "pdf", "application/pdf"
    except ImportError:
        # Still provide a printable slip if ReportLab is not installed in the deployment.
        body = f"""<!doctype html><html><head><meta charset='utf-8'><title>Salary Slip {html.escape(str(slip.get('id','')))}</title>
        <style>body{{font-family:Arial,sans-serif;max-width:760px;margin:40px auto;color:#172033}}h1,h2{{text-align:center}}table{{width:100%;border-collapse:collapse;margin-top:24px}}td,th{{border:1px solid #ccd;padding:12px}}th{{background:#eaf1ff}}.net{{font-weight:bold;background:#dbeafe}}@media print{{button{{display:none}}}}</style></head><body>
        <h1>{html.escape(str(college_name or 'College'))}</h1><h2>SALARY SLIP</h2>
        <p><b>Slip ID:</b> {html.escape(str(slip.get('id','')))} &nbsp; <b>Employee ID:</b> {html.escape(str(slip.get('employee_id','')))}</p>
        <p><b>Employee:</b> {html.escape(str(employee_name or ''))} ({html.escape(str(employee_type or ''))})</p>
        <p><b>Pay Period:</b> {html.escape(str(slip.get('month','')))} {html.escape(str(slip.get('year','')))} &nbsp; <b>Generated:</b> {html.escape(str(slip.get('ts','')))}</p>
        <table><tr><th>Earnings / Deductions</th><th>Amount (INR)</th></tr>
        <tr><td>Basic Salary</td><td>{float(slip.get('basic',0) or 0):,.2f}</td></tr>
        <tr><td>Allowance</td><td>{float(slip.get('allowance',0) or 0):,.2f}</td></tr>
        <tr><td>Deductions</td><td>-{float(slip.get('deduction',0) or 0):,.2f}</td></tr>
        <tr class='net'><td>NET SALARY</td><td>{float(slip.get('net',0) or 0):,.2f}</td></tr></table>
        <p>This is a computer-generated salary slip.</p><button onclick='window.print()'>Print / Save as PDF</button></body></html>"""
        return body.encode("utf-8"), "html", "text/html"

def page_salary():
    if not guard("Accountant"): return
    page_header("Salary Management", "Manage staff salaries & generate slips")
    staff = [s for s in load("staff") if isinstance(s,dict)]
    nt = [n for n in load("non_teaching") if isinstance(n,dict)]
    salaries = [s for s in load("salaries") if isinstance(s,dict)]

    all_emp = [(s["id"], s.get("name",""), "Teaching", s.get("designation","")) for s in staff if s.get("id")]
    all_emp += [(n["id"], n.get("name",""), "Non-Teaching", n.get("role","")) for n in nt if n.get("id")]

    tab1, tab2 = st.tabs(["📋 Salary Slips", "➕ Generate Slip"])

    with tab1:
        if not salaries:
            st.info("No salary slips have been generated yet. Use Generate Slip to create the first one.")
        else:
            df = pd.DataFrame(salaries)
            # Add employee names for a more useful salary register.
            employee_names = {e[0]: e[1] for e in all_emp}
            df["employee_name"] = df["employee_id"].map(employee_names)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("⬇ Download Salary Register (CSV)",
                               df.to_csv(index=False).encode("utf-8-sig"),
                               file_name="salary_register.csv", mime="text/csv",
                               key="salary_register_csv")
            settings = load("settings")
            college_name = settings.get("college_name", "College") if isinstance(settings, dict) else "College"
            employee_details = {e[0]: (e[1], e[2]) for e in all_emp}
            st.subheader("Download Individual Salary Slips")
            for slip in salaries[::-1]:
                emp_name, emp_type = employee_details.get(slip.get("employee_id"), ("Employee", "Staff"))
                file_bytes, file_ext, mime = _salary_slip_download(slip, emp_name, emp_type, college_name)
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{emp_name}** · {slip.get('month', '')} {slip.get('year', '')} · Net ₹{float(slip.get('net', 0) or 0):,.2f}")
                c2.download_button("⬇ Download Slip", file_bytes,
                    file_name=f"salary_slip_{slip.get('id', 'slip')}.{file_ext}", mime=mime,
                    key=f"salary_slip_download_{slip.get('id', uuid.uuid4().hex)}")

    with tab2:
        if not all_emp: st.info("No staff found"); return
        with st.form("add_slip"):
            c1, c2 = st.columns(2)
            emp = c1.selectbox("Employee", [e[0] for e in all_emp],
                               format_func=lambda x: f"{x} — {next((e[1] for e in all_emp if e[0]==x),'')}")
            month = c2.selectbox("Month", list(calendar.month_name)[1:])
            year = c1.number_input("Year", 2020, 2030, date.today().year)
            c1, c2 = st.columns(2)
            basic = c1.number_input("Basic Salary (₹)", 0, 10_000_000, 20000)
            allowance = c2.number_input("Allowance (₹)", 0, 10_000_000, 5000)
            c1, c2 = st.columns(2)
            deduction = c1.number_input("Deductions (₹)", 0, 10_000_000, 2000)
            net = basic + allowance - deduction
            st.info(f"Net Salary: ₹{net:,.2f}")
            if st.form_submit_button("➕ Generate Slip", type="primary"):
                salaries.append({"id":nid("SL"),"employee_id":emp,
                                 "month":month,"year":year,
                                 "basic":basic,"allowance":allowance,
                                 "deduction":deduction,"net":net,"ts":now()})
                save("salaries", salaries)
                flash_message("success", f"✅ Salary slip {salaries[-1]['id']} generated successfully.")
                st.rerun()

# ============================================================
# PAPERS
# ============================================================
def page_papers():
    page_header("Question Papers", "Upload / View")
    if not (current_role() in ("Teacher","Exam Cell") or is_admin()):
        st.error("🚫 Access Denied"); return

    with st.expander("📤 Upload Paper"):
        with st.form("paper"):
            c1, c2, c3 = st.columns(3)
            title = c1.text_input("Title *")
            course = c2.selectbox("Course", list(course_map().keys()),
                                  format_func=lambda x: course_map().get(x,x))
            sem = c3.number_input("Semester", 1, 8, 1)
            file = st.file_uploader("PDF", type=["pdf"])
            submitted_paper = st.form_submit_button("Upload", type="primary")
            if submitted_paper and (not file or not title.strip()): st.error("❌ Enter a title and choose a PDF before uploading.")
            if submitted_paper and file and title.strip():
                p = save_file(file, UPLOAD_DIR)
                papers = load("papers")
                papers.append({"id":nid("P"),"title":title,"course_id":course,
                               "semester":sem,"filename":Path(p).name,
                               "path":p,"ts":now(),
                               "by":current_user()["username"]})
                save("papers", papers); flash_message("success", "Uploaded"); st.rerun()
    st.divider()
    c1, c2 = st.columns(2)
    course_f = c1.selectbox("View Course", list(course_map().keys()),
                            format_func=lambda x: course_map().get(x,x))
    sem_f = c2.number_input("View Semester", 1, 8, 1)
    papers = [p for p in load("papers") if isinstance(p,dict)
              and p.get("course_id")==course_f and p.get("semester")==sem_f]
    if not papers: st.info("No papers"); return
    for p in papers[::-1]:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4,1,1])
            c1.markdown(f"**{p['title']}**")
            c1.caption(f"{p.get('ts','')}")
            if c2.button("👁", key=f"vp_{p['id']}"):
                st.session_state["view_pdf"] = p["path"]
            try:
                c3.download_button("⬇", Path(p["path"]).read_bytes(),
                                   file_name=p["filename"], key=f"dp_{p['id']}")
            except: c3.caption("missing")
    if st.session_state.get("view_pdf"):
        show_pdf(st.session_state["view_pdf"], 600)

# ============================================================
# MATERIALS
# ============================================================
def page_materials():
    page_header("Study Materials", "Notes & resources")
    if current_role() in ("Teacher",) or is_admin():
        with st.expander("📤 Upload Material"):
            with st.form("mat"):
                title = st.text_input("Title *")
                course = st.selectbox("Course", list(course_map().keys()),
                                      format_func=lambda x: course_map().get(x,x))
                sem = st.number_input("Semester", 1, 8, 1)
                file = st.file_uploader("File", type=["pdf","docx","pptx","zip"])
                submitted_material = st.form_submit_button("Upload", type="primary")
                if submitted_material and (not file or not title.strip()):
                    st.error("❌ Enter a title and choose a file before uploading.")
                if submitted_material and file and title.strip():
                    p = save_file(file, UPLOAD_DIR)
                    mats = load("materials")
                    mats.append({"id":nid("MT"),"title":title,"course_id":course,
                                 "semester":sem,"filename":Path(p).name,
                                 "path":p,"ts":now(),
                                 "by":current_user()["username"]})
                    save("materials", mats); flash_message("success", "Uploaded"); st.rerun()
    st.divider()
    mats = [m for m in load("materials") if isinstance(m,dict)]
    if not mats: st.info("No materials"); return
    for m in mats[::-1]:
        with st.container(border=True):
            c1, c2 = st.columns([4,1])
            c1.markdown(f"**{m['title']}**")
            c1.caption(f"{m.get('ts','')} · {m.get('filename','')}")
            try:
                c2.download_button("⬇", Path(m["path"]).read_bytes(),
                                   file_name=m["filename"], key=f"dm_{m['id']}")
            except: c2.caption("missing")

# ============================================================
# LEAVES
# ============================================================
def page_leaves():
    page_header("Leave Management", "Apply / Approve")
    u = current_user()
    role = current_role()
    leaves = load("leaves")

    if role in ("Student", "Teacher", "Accountant"):
        with st.form("apply_leave"):
            c1, c2 = st.columns(2)
            frm = c1.date_input("From", value=date.today())
            to = c2.date_input("To", value=date.today())
            reason = st.text_area("Reason *")
            submitted_leave = st.form_submit_button("📄 Apply", type="primary")
            if submitted_leave and not reason.strip(): st.error("❌ Leave reason is required.")
            if submitted_leave and reason.strip():
                leaves.append({"id":nid("L"),"user":u["username"],"name":u["name"],
                               "role":role,"from":str(frm),"to":str(to),
                               "reason":reason,"status":"Pending","remark":"","ts":now()})
                save("leaves", leaves); flash_message("success", "Applied"); st.rerun()

    if role in ("Accountant","Admin") or is_admin():
        pending = [l for l in leaves if isinstance(l,dict) and l.get("status")=="Pending"]
        st.subheader(f"⏳ Pending ({len(pending)})")
        for l in pending:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3,1,1])
                c1.markdown(f"**{l.get('name','')}** ({l.get('role','')})")
                c1.caption(f"{l.get('from','')} → {l.get('to','')} · {l.get('reason','')}")
                remark = c2.text_input("Remark", key=f"rm_{l['id']}")
                if c2.button("✅ Approve", key=f"ap_{l['id']}"):
                    for x in leaves:
                        if x.get("id")==l["id"]:
                            x["status"]="Approved"; x["remark"]=remark
                    save("leaves", leaves); st.rerun()
                if c3.button("❌ Reject", key=f"rj_{l['id']}"):
                    for x in leaves:
                        if x.get("id")==l["id"]:
                            x["status"]="Rejected"; x["remark"]=remark
                    save("leaves", leaves); st.rerun()

    st.divider()
    st.subheader("📋 Leave Requests")
    if role in ("Admin", "Accountant") or is_admin():
        visible_leaves = [l for l in leaves if isinstance(l, dict)]
    else:
        visible_leaves = [l for l in leaves if isinstance(l, dict) and
                          str(l.get("user", l.get("username", ""))).lower() ==
                          str(u.get("username", "")).lower()]
    if visible_leaves:
        st.dataframe(pd.DataFrame(visible_leaves), use_container_width=True, hide_index=True)
    else:
        st.info("No leave requests to display yet.")

# ============================================================
# LIBRARY
# ============================================================
def page_library():
    if not guard("Librarian"): return
    page_header("Library", "Books & issue history")
    books = [b for b in load("library_books") if isinstance(b,dict)]
    issues = [i for i in load("library_issues") if isinstance(i,dict)]
    students = [s for s in load("students") if isinstance(s,dict) and s.get("id")]

    tab1, tab2, tab3 = st.tabs(["📚 Add Book", "📤 Issue", "🔍 Search History"])

    with tab1:
        with st.form("add_b"):
            c1, c2 = st.columns(2)
            t = c1.text_input("Title *")
            a = c2.text_input("Author")
            copies = c1.number_input("Copies", 1, 100, 1)
            submitted_book = st.form_submit_button("Add", type="primary")
            if submitted_book and not t.strip(): st.error("❌ Book title is required.")
            if submitted_book and t.strip():
                books.append({"id":nid("B"),"title":t,"author":a,
                              "total":copies,"available":copies})
                save("library_books", books); flash_message("success", "✅ Book added successfully."); st.rerun()
        if books:
            st.dataframe(pd.DataFrame(books), use_container_width=True, hide_index=True)

    with tab2:
        if not books or not students: st.info("Need books & students"); return
        bmap = {b["id"]:f"{b['title']} ({b['available']}/{b['total']})" for b in books}
        with st.form("issue"):
            c1, c2 = st.columns(2)
            bid = c1.selectbox("Book", list(bmap.keys()), format_func=lambda x: bmap[x])
            sid = c2.selectbox("Student", [s["id"] for s in students],
                               format_func=lambda x: f"{x} — {student_map().get(x,'')}")
            due = st.date_input("Due Date", value=date.today() + timedelta(days=14))
            if st.form_submit_button("📤 Issue"):
                b = next((b for b in books if b["id"]==bid), None)
                if b and b["available"] > 0:
                    b["available"] -= 1
                    save("library_books", books)
                    issues.append({"id":nid("I"),"book_id":bid,"student_id":sid,
                                   "status":"Issued","ts":now(),
                                   "due_date":str(due),"return_ts":""})
                    save("library_issues", issues); flash_message("success", "Issued"); st.rerun()
        active = [i for i in issues if i.get("status")=="Issued"]
        st.subheader(f"📖 Active ({len(active)})")
        for i in active:
            b = next((b for b in books if b["id"]==i.get("book_id")), None)
            with st.container(border=True):
                c1, c2 = st.columns([3,1])
                c1.write(f"**{b['title'] if b else '?'}** → {student_map().get(i.get('student_id'))}")
                c1.caption(f"Issued: {i.get('ts','')} · Due: {i.get('due_date','')}")
                if c2.button("Return", key=f"rt_{i['id']}"):
                    i["status"]="Returned"; i["return_ts"]=now()
                    if b: b["available"] += 1
                    save("library_books", books); save("library_issues", issues); st.rerun()

    with tab3:
        st.subheader("🔍 Search Book Issue History")
        search_q = st.text_input("Search book title")
        if search_q:
            matched = [b for b in books if search_q.lower() in b.get("title","").lower()]
            for b in matched:
                st.write(f"### 📖 {b['title']}")
                book_issues = [i for i in issues if i.get("book_id")==b["id"]]
                if not book_issues:
                    st.info("No history")
                else:
                    df = pd.DataFrame(book_issues)
                    df["student"] = df["student_id"].map(student_map())
                    df["status"] = df["status"].apply(lambda x: "✅ Returned" if x=="Returned" else "⏳ Issued")
                    st.dataframe(df[["student","ts","due_date","return_ts","status"]], use_container_width=True, hide_index=True)

# ============================================================
# HOSTEL & TRANSPORT
# ============================================================
def page_hostel_transport():
    if not guard("Hostel Manager"): return
    page_header("Hostel & Transport", "Room & route management")
    tab1, tab2 = st.tabs(["🏠 Hostel", "🚌 Transport"])

    with tab1:
        c = st.selectbox("Course", list(course_map().keys()), format_func=lambda x: course_map().get(x,x))
        students = [s for s in load("students") if isinstance(s,dict) and s.get("course_id")==c and s.get("hostel")=="Yes"]
        if students:
            df = pd.DataFrame(students)
            cols = [x for x in ["id","name","hostel_room","hostel_type","final_fee"] if x in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
            with st.form("hostel_room_allotment"):
                room_student = st.selectbox("Student for room allotment", [x["id"] for x in students],
                    format_func=lambda x: f"{x} — {student_map().get(x, '')}")
                room_value = st.text_input("Allotted Room Number", value=next((x.get("hostel_room", "") for x in students if x.get("id") == room_student), ""))
                room_type_value = st.selectbox("Room Type", ["N/A", "Single", "Double", "Triple", "Dormitory"])
                if st.form_submit_button("💾 Save Room Allotment", type="primary"):
                    all_students = load("students")
                    for st_row in all_students:
                        if st_row.get("id") == room_student:
                            st_row["hostel_room"] = room_value.strip()
                            st_row["hostel_type"] = room_type_value
                            break
                    save("students", all_students)
                    flash_message("success", "Hostel room allotment saved.")
                    st.rerun()
        else: st.info("No hostel students")

    with tab2:
        students = [s for s in load("students") if isinstance(s,dict) and s.get("transport")=="Yes"]
        if students:
            df = pd.DataFrame(students)
            cols = [x for x in ["id","name","transport_route"] if x in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
        else: st.info("No transport students")

# ============================================================
# ANNOUNCEMENTS
# ============================================================
def page_announcements():
    page_header("Announcements & Notices", "Create, edit and remove campus notices")
    can_manage = current_role() in ("Admin", "Exam Cell") or is_admin()
    if can_manage:
        with st.expander("➕ Create New Notice / Announcement", expanded=True):
            with st.form("ann"):
                title = st.text_input("Notice title *", placeholder="e.g. University examination schedule")
                body = st.text_area("Notice details *", placeholder="Write the complete notice here…", height=130)
                priority = st.selectbox("Priority", ["Normal", "Important", "Urgent"])
                submitted_announcement = st.form_submit_button("📢 Publish Notice", type="primary", use_container_width=True)
            if submitted_announcement:
                if not title.strip() or not body.strip():
                    st.error("❌ Notice title aur details dono bharna zaroori hai.")
                else:
                    with st.spinner("Publishing notice…"):
                        a = load("announcements")
                        a.append({"id":nid("AN"), "title":title.strip(), "body":body.strip(),
                                  "priority":priority, "by":current_user().get("name", "Admin"), "ts":now()})
                        save("announcements", a)
                    flash_message("success", "📢 Notice successfully published.")
                    st.rerun()

    notices = [a for a in load("announcements") if isinstance(a, dict)][::-1]
    st.subheader(f"📌 Notices & Announcements ({len(notices)})")
    if not notices:
        st.info("Abhi koi notice publish nahi hua hai.")
        return
    for i, notice in enumerate(notices):
        priority = notice.get("priority", "Normal")
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"### {html.escape(str(notice.get('title', 'Untitled notice')))}")
                if priority in ("Important", "Urgent"):
                    st.warning(f"{priority} notice")
                st.write(str(notice.get("body", "")))
                st.caption(f"{notice.get('by', 'Campus Admin')} · {notice.get('ts', '')} · ID: {notice.get('id', '—')}")
            if can_manage:
                with c2:
                    if st.button("✏️ Edit", key=f"edit_notice_{notice.get('id', i)}", use_container_width=True):
                        st.session_state["editing_notice_id"] = notice.get("id")
                if st.session_state.get("editing_notice_id") == notice.get("id"):
                    with st.form(f"edit_notice_form_{notice.get('id', i)}"):
                        edit_title = st.text_input("Title", value=str(notice.get("title", "")))
                        edit_body = st.text_area("Notice details", value=str(notice.get("body", "")), height=120)
                        edit_priority = st.selectbox("Priority", ["Normal", "Important", "Urgent"], index=["Normal", "Important", "Urgent"].index(priority) if priority in ["Normal", "Important", "Urgent"] else 0)
                        save_notice = st.form_submit_button("💾 Save Notice", type="primary")
                    if save_notice:
                        if not edit_title.strip() or not edit_body.strip():
                            st.error("Title aur details blank nahi ho sakte.")
                        else:
                            with st.spinner("Updating notice…"):
                                all_notices = load("announcements")
                                for item in all_notices:
                                    if isinstance(item, dict) and item.get("id") == notice.get("id"):
                                        item.update({"title":edit_title.strip(), "body":edit_body.strip(), "priority":edit_priority, "updated_at":now()})
                                        break
                                save("announcements", all_notices)
                            st.session_state.pop("editing_notice_id", None)
                            flash_message("success", "Notice updated successfully.")
                            st.rerun()
                    if st.button("Cancel edit", key=f"cancel_notice_{notice.get('id', i)}"):
                        st.session_state.pop("editing_notice_id", None)
                        st.rerun()
                if st.button("🗑️ Delete", key=f"delete_notice_{notice.get('id', i)}"):
                    st.session_state["confirm_delete_notice_id"] = notice.get("id")
                if st.session_state.get("confirm_delete_notice_id") == notice.get("id"):
                    st.warning("Delete this notice permanently?")
                    yes, no = st.columns(2)
                    if yes.button("Yes, delete", key=f"yes_delete_notice_{notice.get('id', i)}"):
                        with st.spinner("Deleting notice…"):
                            remaining = [item for item in load("announcements") if not (isinstance(item, dict) and item.get("id") == notice.get("id"))]
                            save("announcements", remaining)
                        st.session_state.pop("confirm_delete_notice_id", None)
                        flash_message("success", "Notice deleted.")
                        st.rerun()
                    if no.button("Cancel", key=f"no_delete_notice_{notice.get('id', i)}"):
                        st.session_state.pop("confirm_delete_notice_id", None)
                        st.rerun()

# ============================================================
# EXAMS
# ============================================================
def page_exams():
    page_header("Exam Schedule", "Set / View")
    role = current_role()

    if role in ("Exam Cell","Admin") or is_admin():
        with st.form("exam"):
            c1, c2, c3 = st.columns(3)
            sub = c1.selectbox("Subject", list(subject_map().keys()),
                               format_func=lambda x: subject_map().get(x,x))
            typ = c2.selectbox("Type", ["Internal","Midterm","Final","Practical"])
            d = c3.date_input("Date", value=date.today())
            c1, c2 = st.columns(2)
            tm = c1.text_input("Time")
            venue = c2.text_input("Venue")
            if st.form_submit_button("📅 Add Exam", type="primary"):
                exams = load("exams")
                exams.append({"id":nid("E"),"subject_id":sub,"type":typ,
                              "date":str(d),"time":tm,"venue":venue,"ts":now()})
                save("exams", exams); flash_message("success", "Scheduled"); st.rerun()
    st.divider()
    st.subheader("📅 Exam Calendar")
    exams = [e for e in load("exams") if isinstance(e,dict)]

    if not exams:
        st.info("No exams"); return

    if role == "Student":
        u = current_user()
        student = next((s for s in load("students") if s.get("id")==u.get("student_id")), None)
        if student:
            my_subs = {s["id"] for s in load("subjects") if s.get("course_id")==student.get("course_id") and s.get("semester")==student.get("semester")}
            exams = [e for e in exams if e.get("subject_id") in my_subs]

    if not exams: st.info("No exams for you"); return

    exam_dates = sorted(list({e["date"] for e in exams}))
    selected_date = st.selectbox("Select Date", exam_dates,
                                 format_func=lambda x: datetime.strptime(x, "%Y-%m-%d").strftime("%A, %d %B %Y"))

    if selected_date:
        day_exams = [e for e in exams if e["date"]==selected_date]
        st.markdown(f"### 📅 {selected_date}")
        for e in day_exams:
            subj = subject_map().get(e.get("subject_id"), "")
            with st.container(border=True):
                st.markdown(f"**{subj}** — {e.get('type','')}")
                st.caption(f"🕒 {e.get('time','')} · 📍 {e.get('venue','')}")

# ============================================================
# STUDENT SELF-SERVICE
# ============================================================
def page_my_profile():
    u = current_user()
    sid = u.get("student_id")
    students = load("students")
    stu = next((s for s in students if s.get("id")==sid), None)
    if not stu:
        st.warning("Profile not linked"); return
    page_header("My Profile", stu.get("name",""))
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**Name:** {stu.get('name')}")
        st.write(f"**ID:** {stu.get('id')}")
        st.write(f"**Roll:** {stu.get('roll_no')}")
        st.write(f"**Course:** {course_map().get(stu.get('course_id'),'')}")
        st.write(f"**Semester:** {stu.get('semester')}")
        st.write(f"**Email:** {stu.get('email')}")
        st.write(f"**Phone:** {stu.get('phone')}")
    with c2:
        st.write(f"**Father:** {stu.get('father_name')}")
        st.write(f"**Category:** {stu.get('category')}")
        st.write(f"**Quota:** {stu.get('quota')}")
        st.write(f"**Total Fee:** ₹{stu.get('final_fee',0):,}")

def page_my_attendance_calendar():
    """Student's own attendance calendar view."""
    u = current_user()
    sid = u.get("student_id")
    page_header("My Attendance Calendar", "Click a date to see attendance")
    att = [a for a in load("attendance") if isinstance(a,dict) and a.get("student_id")==sid]

    if not att:
        st.info("No attendance yet"); return

    # Build month navigation
    months = sorted(set(a["date"][:7] for a in att))
    month_sel = st.selectbox("Month", months)

    year, mon = map(int, month_sel.split("-"))
    st.markdown(f"### 📅 {calendar.month_name[mon]} {year}")

    # Show calendar grid
    cal = calendar.monthcalendar(year, mon)
    day_att = {}
    for a in att:
        if a["date"].startswith(month_sel):
            d = int(a["date"].split("-")[2])
            if d not in day_att:
                day_att[d] = {"present":0,"absent":0}
            if a.get("status")=="Present":
                day_att[d]["present"] += 1
            else:
                day_att[d]["absent"] += 1

    # Render calendar
    html = "<table style='width:100%; text-align:center; border-collapse:collapse;'>"
    html += "<tr>" + "".join([f"<th style='padding:8px; background:#f1f5f9;'>{"Mon Tue Wed Thu Fri Sat Sun".split()[i]}</th>" for i in range(7)]) + "</tr>"
    for week in cal:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td style='padding:20px; border:1px solid #e2e8f0;'></td>"
            else:
                info = day_att.get(day)
                if info:
                    total = info["present"] + info["absent"]
                    if info["absent"] == 0:
                        bg, label = "#10b981", f"✅ {info['present']}P"
                        color = "white"
                    elif info["present"] == 0:
                        bg, label = "#ef4444", f"❌ {info['absent']}A"
                        color = "white"
                    else:
                        bg, label = "#f59e0b", f"{info['present']}P/{info['absent']}A"
                        color = "white"
                    html += f"<td style='padding:12px; border:1px solid #e2e8f0; background:{bg}; color:{color}; border-radius:6px; font-weight:600;'>{day}<br><small>{label}</small></td>"
                else:
                    html += f"<td style='padding:20px; border:1px solid #e2e8f0; color:#cbd5e1;'>{day}</td>"
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    # Detail view - click a specific date
    st.divider()
    st.subheader("📋 Date-wise Detail")
    date_sel = st.selectbox("Select a date",
                            sorted(set(a["date"] for a in att if a["date"].startswith(month_sel))))
    if date_sel:
        day_att_rec = [a for a in att if a["date"]==date_sel]
        for a in day_att_rec:
            subj = subject_map().get(a.get("subject_id"), "")
            status = "✅ Present" if a.get("status")=="Present" else "❌ Absent"
            with st.container(border=True):
                st.markdown(f"**{subj}** — {status}")

def page_my_marks():
    u = current_user()
    sid = u.get("student_id")
    page_header("My Marks", "")
    marks = [m for m in load("marks") if isinstance(m,dict) and m.get("student_id")==sid]
    if not marks:
        st.info("No marks yet"); return
    df = pd.DataFrame(marks)
    df["subject"] = df["subject_id"].map(subject_map())
    st.dataframe(df, use_container_width=True, hide_index=True)

def page_my_fees():
    u = current_user()
    sid = u.get("student_id")
    page_header("My Fees", "")
    students = load("students")
    stu = next((s for s in students if s.get("id")==sid), None)
    fees = [f for f in load("fees") if isinstance(f,dict) and f.get("student_id")==sid]
    bills = [b for b in load("bills") if isinstance(b,dict) and b.get("student_id")==sid]
    total = stu.get("final_fee",0) if stu else 0
    paid = sum(f.get("amount",0) for f in fees)
    bill_total = sum(b.get("amount",0) for b in bills if b.get("status")=="Unpaid")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Fee", f"₹{total:,}")
    c2.metric("Paid", f"₹{paid:,}")
    c3.metric("Due Fee", f"₹{total-paid:,}")
    c4.metric("Other Bills", f"₹{bill_total:,}")
    if fees:
        df = pd.DataFrame(fees)
        st.dataframe(df[["id","amount","mode","ts"]], use_container_width=True, hide_index=True)
    if bills:
        st.subheader("📄 Bills")
        st.dataframe(pd.DataFrame(bills), use_container_width=True, hide_index=True)

# ============================================================
# USERS
# ============================================================
def page_users():
    if not is_admin(): st.error("🚫 Only Admin"); return
    page_header("User Management", "All logins")
    users = load("users")
    df = pd.DataFrame([u for u in users if isinstance(u,dict)])
    cols = [c for c in ["username","role","name","active"] if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)

    with st.form("new_user"):
        c1, c2 = st.columns(2)
        uname = c1.text_input("Username *")
        pwd = c2.text_input("Password *", type="password")
        role = c1.selectbox("Role", ["Admin","Admission Cell","Accountant","Teacher",
                                    "Student","Librarian","Exam Cell","Hostel Manager","Non-Teaching"])
        name = c2.text_input("Name *")
        submitted_user = st.form_submit_button("Add User", type="primary")
        if submitted_user and (not uname.strip() or not pwd.strip() or not name.strip()):
            st.error("❌ Username, password and name are required.")
        if submitted_user and uname.strip() and pwd.strip() and name.strip():
            if any(u.get("username")==uname for u in users):
                st.error("Username exists")
            else:
                users.append({"username":uname,"password":hpw(pwd),"role":role,
                              "name":name,"active":True})
                save("users", users); flash_message("success", "Added"); st.rerun()

# ============================================================
# UNIVERSAL RECORD EDITOR — all ERP modules
# ============================================================
def page_all_records_editor():
    if not is_admin():
        st.error("🚫 Only Admin can edit all module records.")
        return
    page_header("Edit Any ERP Record", "Admin can edit saved fields from any module")
    module = st.selectbox("Select module", KEYS, format_func=lambda x: x.replace("_", " ").title(), key="universal_edit_module")
    data = load(module)
    if isinstance(data, dict):
        records = [data]
        record_labels = [module.replace("_", " ").title()]
    elif isinstance(data, list):
        records = [x for x in data if isinstance(x, dict)]
        record_labels = [str(x.get("id") or x.get("username") or x.get("code") or f"Record {i+1}") + (f" — {x.get('name','')}" if x.get("name") else "") for i, x in enumerate(records)]
    else:
        records, record_labels = [], []
    if not records:
        st.info("Is module mein abhi editable record nahi hai.")
        return
    idx = st.selectbox("Choose record", range(len(records)), format_func=lambda i: record_labels[i], key=f"universal_edit_record_{module}")
    record = records[idx]
    st.caption("Saved fields edit karo. Nested list/dict fields JSON format mein editable hain. Record ID locked rahegi taaki linked records na tootain.")
    updated = _edit_complete_record(record, f"universal_editor_{module}_{idx}", module.title())
    if updated is not None:
        with st.spinner("Saving edited record..."):
            if isinstance(data, dict):
                save(module, updated)
            else:
                positions = [i for i, item in enumerate(data) if isinstance(item, dict)]
                if idx < len(positions):
                    data[positions[idx]] = updated
                save(module, data)
        flash_message("success", f"✅ {module.replace('_', ' ').title()} record updated successfully.")
        st.rerun()


# ============================================================
# REPORTS
# ============================================================
def page_reports():
    if not is_admin(): st.error("🚫 Only Admin"); return
    page_header("Reports", "Export data")
    tab1, tab2, tab3 = st.tabs(["Students","Fees","Attendance"])
    with tab1:
        students = [s for s in load("students") if isinstance(s,dict)]
        if students:
            df = pd.DataFrame(students)
            st.dataframe(df, use_container_width=True, hide_index=True)
            xlsx_dl(df, "students_report", "rep_stu")
    with tab2:
        fees = [f for f in load("fees") if isinstance(f,dict)]
        if fees:
            df = pd.DataFrame(fees)
            st.dataframe(df, use_container_width=True, hide_index=True)
            xlsx_dl(df, "fees_report", "rep_fee")
    with tab3:
        att = [a for a in load("attendance") if isinstance(a,dict)]
        if att:
            df = pd.DataFrame(att)
            st.dataframe(df, use_container_width=True, hide_index=True)
            xlsx_dl(df, "attendance_report", "rep_att")

# ============================================================
# MENU
# ============================================================
def build_menu(role):
    if is_admin_role(role):
        return [
            ("🏠 Dashboard", page_dashboard),
            ("📚 Courses", page_courses),
            ("📖 Subjects", page_subjects),
            ("➕ Admission", page_admission),
            ("🎓 Students", page_students),
            ("👨‍🏫 Faculty", page_faculty),
            ("👷 Non-Teaching", page_non_teaching),
            ("📋 Attendance", page_attendance),
            ("📝 Marks", page_marks),
            ("💰 Fees", page_fees),
            ("📄 Papers", page_papers),
            ("📁 Materials", page_materials),
            ("🏖 Leaves", page_leaves),
            ("📚 Library", page_library),
            ("🏠 Hostel/Transport", page_hostel_transport),
            ("📅 Exams", page_exams),
            ("📢 Announcements", page_announcements),
            ("👤 Users", page_users),
            ("🛠 Edit Any Record", page_all_records_editor),
            ("📊 Reports", page_reports),
        ]
    if role == "Admission Cell":
        return [("🏠 Dashboard", page_dashboard),
                ("➕ Admission", page_admission),
                ("🎓 Students", page_students),
                ("👨‍🏫 Faculty", page_faculty),
                ("👷 Non-Teaching", page_non_teaching)]
    if role == "Accountant":
        return [("🏠 Dashboard", page_dashboard),
                ("💰 Fees", page_fees),
                ("🧾 Bills", page_bills),
                ("💼 Salary", page_salary),
                ("🏖 Leaves", page_leaves)]
    if role == "Teacher":
        return [("🏠 Dashboard", page_dashboard),
                ("💰 Student Fees (View Only)", page_teacher_fees),
                ("📋 Attendance", page_attendance),
                ("📝 Marks", page_marks),
                ("📄 Papers", page_papers),
                ("📁 Materials", page_materials),
                ("🏖 Leaves", page_leaves)]
    if role == "Student":
        return [("🏠 Dashboard", page_dashboard),
                ("👤 My Profile", page_my_profile),
                ("📝 My Marks", page_my_marks),
                ("📋 Attendance Calendar", page_my_attendance_calendar),
                ("💰 My Fees", page_my_fees),
                ("📅 Exam Calendar", page_exams),
                ("📁 Materials", page_materials),
                ("🏖 Apply Leave", page_leaves),
                ("📢 Announcements", page_announcements)]
    if role == "Librarian":
        return [("🏠 Dashboard", page_dashboard),
                ("📚 Library", page_library)]
    if role == "Exam Cell":
        return [("🏠 Dashboard", page_dashboard),
                ("📄 Papers", page_papers),
                ("📅 Exams", page_exams),
                ("📢 Announcements", page_announcements),
                ("📝 Marks", page_marks)]
    if role == "Hostel Manager":
        return [("🏠 Dashboard", page_dashboard),
                ("🏠 Hostel/Transport", page_hostel_transport)]
    return [("🏠 Dashboard", page_dashboard)]

def main():
    if "user" not in st.session_state:
        login_page(); return
    u = current_user()
    if not isinstance(u, dict) or not u.get("role"):
        st.error("⚠ No role. Contact admin.")
        if st.button("Logout"): logout()
        return

    pending_flash = st.session_state.pop("_flash_message", None)
    if isinstance(pending_flash, dict):
        kind = pending_flash.get("kind", "success")
        message = pending_flash.get("message", "")
        if kind == "error": st.error(message)
        elif kind == "warning": st.warning(message)
        else: st.success(message)

    role = u["role"]
    if (u.get("username") or "").lower() == "admin":
        role = "Admin"

    try: menu = build_menu(role)
    except Exception as e:
        st.error(f"Menu error: {e}"); menu = [("🏠 Dashboard", page_dashboard)]

    if not menu: menu = [("🏠 Dashboard", page_dashboard)]

    with st.sidebar:
        s = load("settings")
        st.markdown(f"""
        <div style="padding:16px 0; border-bottom:1px solid #1e293b; margin-bottom:16px;">
            <div style="font-size:20px; font-weight:700; color:#f1f5f9;">🎓 CampusPro ERP</div>
            <div style="font-size:11px; color:#64748b; margin-top:4px;">{s.get('college_name','')[:28]}</div>
        </div>
        <div style="background:#1e293b; padding:12px; border-radius:10px; margin-bottom:16px;">
            <div style="font-size:13px; font-weight:600; color:#f1f5f9;">{u.get('name','')}</div>
            <div style="font-size:11px; color:#94a3b8;">{u.get('role','')} · @{u.get('username','')}</div>
        </div>
        """, unsafe_allow_html=True)
        labels = [m[0] for m in menu]
        choice = st.radio("Nav", labels, label_visibility="collapsed")
        st.divider()
        st.caption(f"📋 Modules: **{len(menu)}**")
        if st.button("🚪 Logout", use_container_width=True): logout()

    for label, func in menu:
        if label == choice:
            try: func()
            except Exception as e:
                st.error(f"⚠ {e}"); st.exception(e)
            break

if __name__ == "__main__":
    main()