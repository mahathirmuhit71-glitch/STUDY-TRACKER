import streamlit as st
import pandas as pd
import json
import os
import time
import textwrap
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pypdf import PdfReader, PdfWriter

# ============================================================
# OPTIONAL REPORTLAB
# ============================================================
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ============================================================
# SUPABASE
# ============================================================
try:
    from supabase import create_client, Client

    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_AVAILABLE = True
except Exception as e:
    supabase = None
    SUPABASE_AVAILABLE = False
    SUPABASE_ERROR = str(e)

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Muhit's HSC Tracker & Workspace",
    page_icon="⚡",
    layout="wide"
)

# ============================================================
# GLOBAL FONT SIZE
# ============================================================
st.markdown(
    """
    <style>
    .stMarkdown, .stText, label, p, li,
    input, textarea, select {
        font-size: 22px !important;
    }

    h1 { font-size: 2.35rem !important; }
    h2 { font-size: 2rem !important; }
    h3 { font-size: 1.7rem !important; }
    h4 { font-size: 1.45rem !important; }

    [data-testid="stMetricValue"] {
        font-size: 1.9rem !important;
    }

    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button {
        font-size: 20px !important;
        font-weight: 700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# LOCAL DIRECTORY
# Used only for migration/backward compatibility.
# After migration, Supabase is the permanent storage.
# ============================================================
DATA_DIR = "tracker_data"
os.makedirs(DATA_DIR, exist_ok=True)

TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
SYLLABUS_FILE = os.path.join(DATA_DIR, "syllabus.json")
TIMER_FILE = os.path.join(DATA_DIR, "timer_logs.json")
DAILY_SESSIONS_FILE = os.path.join(DATA_DIR, "daily_sessions.json")
EXAMS_FILE = os.path.join(DATA_DIR, "admission_exams.json")
SONGS_FILE = os.path.join(DATA_DIR, "songs.json")


# ============================================================
# LOCAL HELPERS
# ============================================================
def load_local(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_val
    return default_val


def save_local(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass


# ============================================================
# SUPABASE DATA HELPERS
# ============================================================
def supabase_get(key, default=None):
    if not SUPABASE_AVAILABLE:
        return default

    try:
        response = (
            supabase
            .table("app_data")
            .select("data")
            .eq("key", key)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]["data"]

    except Exception:
        return default

    return default


def supabase_save(key, value):
    """Save one complete piece of app data to the canonical Supabase row."""
    if not SUPABASE_AVAILABLE:
        return False

    try:
        supabase.table("app_data").upsert(
            {
                "key": key,
                "data": value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            on_conflict="key"
        ).execute()
        return True
    except Exception as e:
        # Keep the error available for the UI instead of silently losing a save.
        st.session_state["last_supabase_error"] = f"{key}: {e}"
        return False


def supabase_check():
    """Return (ok, message) so the app can visibly report database health."""
    if not SUPABASE_AVAILABLE:
        return False, "Supabase client/secrets are not available."

    try:
        supabase.table("app_data").select("key").limit(1).execute()
        return True, "Supabase connected"
    except Exception as e:
        return False, str(e)


def save_all_data():
    """Persist every important state object on every meaningful rerun.

    This is an extra safety net in addition to the individual save calls below.
    Supabase remains the permanent store; local JSON is only a backup.
    """
    if "data_initialized" not in st.session_state:
        return True

    items = [
        ("tasks", TASKS_FILE, st.session_state.get("tasks", [])),
        ("daily_sessions", DAILY_SESSIONS_FILE, st.session_state.get("daily_sessions", {})),
        ("admission_exams", EXAMS_FILE, st.session_state.get("admission_exams", [])),
        ("timer_logs", TIMER_FILE, st.session_state.get("timer_logs", [])),
        ("songs", SONGS_FILE, st.session_state.get("my_songs", DEFAULT_SONGS)),
        ("syllabus", SYLLABUS_FILE, st.session_state.get("syllabus", {})),
    ]

    all_ok = True
    for key, local_file, value in items:
        if not permanent_save(key, local_file, value):
            all_ok = False

    st.session_state["last_cloud_save"] = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    return all_ok


def get_permanent_data(key, local_file, default):
    """
    First tries Supabase.
    If the key does not exist, imports the old local JSON data
    into Supabase automatically.
    """

    if SUPABASE_AVAILABLE:
        cloud_data = supabase_get(key, None)

        if cloud_data is not None:
            return cloud_data

        # Automatic one-time migration from old JSON
        old_data = load_local(local_file, None)

        if old_data is not None:
            if supabase_save(key, old_data):
                return old_data

        # Nothing exists anywhere
        supabase_save(key, default)
        return default

    return load_local(local_file, default)


def permanent_save(key, local_file, data):
    """
    Supabase is the permanent database.
    Local JSON is also updated as a backup when possible.
    """

    saved = False

    if SUPABASE_AVAILABLE:
        saved = supabase_save(key, data)

    # Keep local backup too
    save_local(local_file, data)

    return saved


# ============================================================
# COLUMN DEFINITIONS
# ============================================================
PHYSICS_COLUMNS = [
    "Class",
    "Master Book",
    "Concept Book",
    "Short Note",
    "Book Reading",
    "VAP Master Bank"
]

CHEMISTRY_COLUMNS = [
    "Class",
    "Master Book",
    "Concept Book",
    "Short Note",
    "Book Reading",
    "VAP Master Bank"
]

BIOLOGY_COLUMNS = [
    "Class",
    "Master Book",
    "Book Reading"
]

MATH_COLUMNS = [
    "Class",
    "Master Book",
    "Concept Book",
    "Short Note",
    "VAP Master Bank"
]

CHECKBOX_COLUMNS = PHYSICS_COLUMNS


def get_subject_cols(sub_name):
    if "Biology" in sub_name:
        return BIOLOGY_COLUMNS
    elif "Higher Math" in sub_name:
        return MATH_COLUMNS
    elif "Chemistry" in sub_name:
        return CHEMISTRY_COLUMNS
    return PHYSICS_COLUMNS


# ============================================================
# COMPLETE HSC SYLLABUS
# ============================================================
HSC_DEFAULT_SYLLABUS = {

    # ========================================================
    # BIOLOGY
    # ========================================================
    "Biology (1st & 2nd Paper)": {
        "Chapters": {

            "Biology 1st: Chapter 1: কোষ ও এর গঠন":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 1st: Chapter 2: কোষ বিভাজন":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 1st: Chapter 3: কোষ রসায়ন":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 1st: Chapter 4: অণুজীব":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 1st: Chapter 5: শৈবাল ও ছত্রাক":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 1st: Chapter 6: ব্রায়োফাইটা ও টেরিডোফাইটা":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 1st: Chapter 7: নগ্নবীজী ও আবৃতবীজী উদ্ভিদ":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 1st: Chapter 8: টিস্যু ও টিস্যুতন্ত্র":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 1st: Chapter 9: উদ্ভিদ শারীরতত্ত্ব":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 1st: Chapter 10: উদ্ভিদ প্রজনন":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 1st: Chapter 11: জীবপ্রযুক্তি":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 1st: Chapter 12: জীবের পরিবেশ, বিস্তার ও সংরক্ষণ":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 1: প্রাণীর বিভিন্নতা ও শ্রেণিবিন্যাস":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 2: প্রাণীর পরিচিতি":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 3: মানব শারীরতত্ত্ব: পরিপাক ও শোষণ":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 4: মানব শারীরতত্ত্ব: রক্ত ও সঞ্চালন":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 5: মানব শারীরতত্ত্ব: শ্বাসক্রিয়া ও শ্বসন":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 6: মানব শারীরতত্ত্ব: বর্জ্য ও নিষ্কাশন":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 7: মানব শারীরতত্ত্ব: চলন ও অঙ্গচালনা":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 8: মানব শারীরতত্ত্ব: সমন্বয় ও নিয়ন্ত্রণ":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 9: মানব জীবনের ধারাবাহিকতা":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 10: মানবদেহের প্রতিরক্ষা":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 11: জিনতত্ত্ব ও বিবর্তন":
                {col: False for col in BIOLOGY_COLUMNS},

            "Biology 2nd: Chapter 12: প্রাণীর আচরণ":
                {col: False for col in BIOLOGY_COLUMNS},
        }
    },

    # ========================================================
    # PHYSICS
    # ========================================================
    "Physics (1st & 2nd Paper)": {
        "Chapters": {

            "Physics 1st: Chapter 1: ভৌত জগৎ ও পরিমাপ":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 1st: Chapter 2: ভেক্টর":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 1st: Chapter 3: গতিবিদ্যা":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 1st: Chapter 4: নিউটনীয় বলবিদ্যা":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 1st: Chapter 5: কাজ, শক্তি ও ক্ষমতা":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 1st: Chapter 6: মহাকর্ষ ও অভিকর্ষ":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 1st: Chapter 7: পদার্থের গাঠনিক ধর্ম":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 1st: Chapter 8: পর্যাবৃত্ত গতি":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 1st: Chapter 9: তরঙ্গ":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 1st: Chapter 10: আদর্শ গ্যাস ও গ্যাসের গতিতত্ত্ব":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 2nd: Chapter 1: তাপগতিবিদ্যা":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 2nd: Chapter 2: স্থির তড়িৎ":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 2nd: Chapter 3: চল তড়িৎ":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 2nd: Chapter 4: তড়িৎ প্রবাহের চৌম্বক ক্রিয়া ও চুম্বকত্ব":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 2nd: Chapter 5: তাড়িতচৌম্বক আবেশ ও পরিবর্তী প্রবাহ":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 2nd: Chapter 6: জ্যামিতিক আলোকবিজ্ঞান":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 2nd: Chapter 7: ভৌত আলোকবিজ্ঞান":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 2nd: Chapter 8: আধুনিক পদার্থবিজ্ঞানের সূচনা":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 2nd: Chapter 9: পরমাণু এবং নিউক্লিয়ার পদার্থবিজ্ঞান":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 2nd: Chapter 10: সেমিকন্ডাক্টর ও ইলেকট্রনিক্স":
                {col: False for col in PHYSICS_COLUMNS},

            "Physics 2nd: Chapter 11: জ্যোতির্বিজ্ঞান":
                {col: False for col in PHYSICS_COLUMNS},
        }
    },

    # ========================================================
    # CHEMISTRY
    # ========================================================
    "Chemistry (1st & 2nd Paper)": {
        "Chapters": {

            "Chemistry 1st: Chapter 1: ল্যাবরেটরির নিরাপদ ব্যবহার":
                {col: False for col in CHEMISTRY_COLUMNS},

            "Chemistry 1st: Chapter 2: গুণগত রসায়ন":
                {col: False for col in CHEMISTRY_COLUMNS},

            "Chemistry 1st: Chapter 3: মৌলের পর্যায়বৃত্ত ধর্ম ও রাসায়নিক বন্ধন":
                {col: False for col in CHEMISTRY_COLUMNS},

            "Chemistry 1st: Chapter 4: রাসায়নিক পরিবর্তন":
                {col: False for col in CHEMISTRY_COLUMNS},

            "Chemistry 1st: Chapter 5: কর্মমুখী রসায়ন":
                {col: False for col in CHEMISTRY_COLUMNS},

            "Chemistry 2nd: Chapter 1: পরিবেশ রসায়ন":
                {col: False for col in CHEMISTRY_COLUMNS},

            "Chemistry 2nd: Chapter 2: জৈব রসায়ন":
                {col: False for col in CHEMISTRY_COLUMNS},

            "Chemistry 2nd: Chapter 3: পরিমাণগত রসায়ন":
                {col: False for col in CHEMISTRY_COLUMNS},

            "Chemistry 2nd: Chapter 4: তড়িৎ রসায়ন":
                {col: False for col in CHEMISTRY_COLUMNS},

            "Chemistry 2nd: Chapter 5: অর্থনৈতিক রসায়ন":
                {col: False for col in CHEMISTRY_COLUMNS},
        }
    },

    # ========================================================
    # HIGHER MATH
    # ========================================================
    "Higher Math (1st & 2nd Paper)": {
        "Chapters": {

            "Higher Math 1st: Chapter 1: ম্যাট্রিক্স ও নির্ণায়ক":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 1st: Chapter 2: ভেক্টর":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 1st: Chapter 3: সরলরেখা":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 1st: Chapter 4: বৃত্ত":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 1st: Chapter 5: বিন্যাস ও সমাবেশ":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 1st: Chapter 6: ত্রিকোণমিতিক অনুপাত":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 1st: Chapter 7: সংযুক্ত কোণের ত্রিকোণমিতিক অনুপাত":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 1st: Chapter 8: ফাংশন ও ফাংশনের লেখচিত্র":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 1st: Chapter 9: অন্তরীকরণ":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 1st: Chapter 10: যোগজীকরণ":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 2nd: Chapter 1: বাস্তব সংখ্যা ও অসমতা":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 2nd: Chapter 2: রৈখিক প্রোগ্রামিং":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 2nd: Chapter 3: জটিল সংখ্যা":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 2nd: Chapter 4: বহুপদী ও বহুপদী সমীকরণ":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 2nd: Chapter 5: দ্বিপদী বিস্তৃতি":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 2nd: Chapter 6: কণিক":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 2nd: Chapter 7: বিপরীত ত্রিকোণমিতিক ফাংশন ও ত্রিকোণমিতিক সমীকরণ":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 2nd: Chapter 8: স্থিতিবিদ্যা":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 2nd: Chapter 9: সমতলে বস্তুকণার গতি":
                {col: False for col in MATH_COLUMNS},

            "Higher Math 2nd: Chapter 10: বিস্তার পরিমাপ ও সম্ভাবনা":
                {col: False for col in MATH_COLUMNS},
        }
    }
}


# ============================================================
# MERGE / UPGRADE SYLLABUS WITHOUT DESTROYING OLD CHECKMARKS
# ============================================================
def merge_syllabus(existing, defaults):
    if not existing:
        return defaults

    merged = existing.copy()

    for subject, default_content in defaults.items():

        if subject not in merged:
            merged[subject] = {
                "Chapters": {}
            }

        if "Chapters" not in merged[subject]:
            merged[subject]["Chapters"] = {}

        existing_chapters = merged[subject]["Chapters"]

        for chapter, default_pillars in default_content["Chapters"].items():

            if chapter not in existing_chapters:
                existing_chapters[chapter] = default_pillars.copy()
            else:
                for pillar in default_pillars:
                    if pillar not in existing_chapters[chapter]:
                        existing_chapters[chapter][pillar] = False

    return merged


# ============================================================
# DEFAULT SONGS
# ============================================================
DEFAULT_SONGS = [
    "https://youtu.be/B-ISCaZ2EUw?si=LHSLxrwL8gqv48SE",
    "https://youtu.be/iR5U92Eq-_8",
    "https://youtu.be/Agcvgc23bNc",
    "https://youtu.be/QJpfLoGMgqU",
    "https://youtu.be/aar0oGrJcDM?si=wRRJLEnHo4-dMa3j"
]


# ============================================================
# LOAD PERMANENT DATA
# ============================================================
if "data_initialized" not in st.session_state:

    st.session_state.tasks = get_permanent_data(
        "tasks",
        TASKS_FILE,
        []
    )

    st.session_state.daily_sessions = get_permanent_data(
        "daily_sessions",
        DAILY_SESSIONS_FILE,
        {}
    )

    st.session_state.admission_exams = get_permanent_data(
        "admission_exams",
        EXAMS_FILE,
        []
    )

    st.session_state.timer_logs = get_permanent_data(
        "timer_logs",
        TIMER_FILE,
        []
    )

    st.session_state.my_songs = get_permanent_data(
        "songs",
        SONGS_FILE,
        DEFAULT_SONGS
    )

    existing_syllabus = get_permanent_data(
        "syllabus",
        SYLLABUS_FILE,
        {}
    )

    st.session_state.syllabus = merge_syllabus(
        existing_syllabus,
        HSC_DEFAULT_SYLLABUS
    )

    # Save merged syllabus immediately.
    permanent_save(
        "syllabus",
        SYLLABUS_FILE,
        st.session_state.syllabus
    )

    st.session_state.data_initialized = True

# Check the connection once per browser session so a broken database is visible.
if "supabase_health_checked" not in st.session_state:
    ok, message = supabase_check()
    st.session_state["supabase_health_checked"] = True
    st.session_state["supabase_health_ok"] = ok
    st.session_state["supabase_health_message"] = message


# ============================================================
# SESSION STATE
# ============================================================
if "active_focus_task" not in st.session_state:
    st.session_state.active_focus_task = None

if "is_focus_running" not in st.session_state:
    st.session_state.is_focus_running = False

if "focus_started_at" not in st.session_state:
    st.session_state.focus_started_at = None

if "focus_elapsed_before" not in st.session_state:
    st.session_state.focus_elapsed_before = 0

if "focus_paused" not in st.session_state:
    st.session_state.focus_paused = False


# ============================================================
# BAN NAVIGATION / TAB LEAVE WARNING DURING FOCUS
# ============================================================
if st.session_state.is_focus_running:

    st.markdown(
        textwrap.dedent("""
            <script>
            window.onbeforeunload = function (e) {
                e.preventDefault();
                e.returnValue = "⚠️ Focus session is active. Be Consistent and Determined!";
                return "⚠️ Focus session is active. Be Consistent and Determined!";
            };
            </script>
        """),
        unsafe_allow_html=True
    )


# ============================================================
# DATE / TIME
# ============================================================
DAYS_OF_WEEK = [
    "Saturday",
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday"
]

bd_tz = timezone(timedelta(hours=6))
now_bd = datetime.now(bd_tz)

current_day_name = now_bd.strftime("%A")
today_date_str = now_bd.strftime("%Y-%m-%d")
formatted_display_date = now_bd.strftime("%d %B %Y")


# ============================================================
# COUNTDOWN
# ============================================================
target_exam_date = datetime(
    2026,
    12,
    1,
    tzinfo=bd_tz
)

remaining_seconds = int(
    (target_exam_date - now_bd).total_seconds()
)

remaining_days = max(
    0,
    remaining_seconds // 86400
)


# ============================================================
# ============================================================
# NAVIGATION
# ============================================================
page_selection = [
    "🏠 Dashboard & Focus Station",
    "📖 Syllabus Tracker",
    "🎓 ভর্তি পরীক্ষার তারিখ",
    "📄 PDF Tool",
    "🎵 গানের জগত"
]

if "page" not in st.session_state:
    st.session_state.page = page_selection[0]


def go_to_page(target_page):
    if st.session_state.is_focus_running:
        st.sidebar.error("⚠️ Be Consistent and Determined!")
    else:
        st.session_state.page = target_page
        st.rerun()


# Only two navigation buttons: Dashboard and Study Tracker.
st.sidebar.markdown("### Go to")

if st.sidebar.button(
    "🏠 Dashboard",
    key="sidebar_dashboard_button",
    use_container_width=True
):
    go_to_page("🏠 Dashboard & Focus Station")

if st.sidebar.button(
    "📖 Study Tracker",
    key="sidebar_study_tracker_button",
    use_container_width=True
):
    go_to_page("📖 Syllabus Tracker")


# PAGE 1: DASHBOARD
# ============================================================
if st.session_state.page == "🏠 Dashboard & Focus Station":

    # Visible headline — use raw HTML without Markdown indentation
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
<a href="#target-tracker" title="Go to Daily Sessions" style="text-decoration:none;font-size:32px;line-height:1;display:inline-block;cursor:pointer;">⚡</a>
<h1 style="margin:0;font-size:2.25rem;font-weight:700;color:#FF4B4B !important;display:block;visibility:visible !important;opacity:1 !important;">{remaining_days} days ahead<br><span style="font-size:1rem;font-weight:500;color:#888 !important;">(Consistent, Determined, Hardwork)</span></h1>
</div>""",
        unsafe_allow_html=True
    )

    left_col, right_col = st.columns([1.8, 1.4])

    # ========================================================
    # LEFT COLUMN
    # ========================================================
    with left_col:

        st.markdown(
            f"### 🌞 {formatted_display_date} | {current_day_name}"
        )

        todays_tasks = [
            t for t in st.session_state.tasks
            if t.get("assigned_day") == current_day_name
            and not t.get("done", False)
        ]

        if not todays_tasks:

            st.info(
                f"No active tasks assigned for {current_day_name}. "
                "Pick tasks from your Weekly Vault below!"
            )

        else:

            for task in todays_tasks:

                d_col1, d_col2, d_col3 = st.columns(
                    [0.2, 2, 1]
                )

                with d_col1:

                    is_chk = st.checkbox(
                        "",
                        value=False,
                        key=f"daily_chk_{task['id']}"
                    )

                    if is_chk:

                        for t in st.session_state.tasks:
                            if t["id"] == task["id"]:
                                t["done"] = True

                        permanent_save(
                            "tasks",
                            TASKS_FILE,
                            st.session_state.tasks
                        )

                        st.toast(
                            "🎉 Great job Muhit! Task completed."
                        )

                        time.sleep(0.3)
                        st.rerun()

                with d_col2:
                    st.write(task["title"])

                with d_col3:

                    if not st.session_state.is_focus_running:

                        if st.button(
                            "🎯 Focus Now",
                            key=f"f_now_{task['id']}"
                        ):

                            st.session_state.active_focus_task = task
                            st.session_state.is_focus_running = True
                            st.session_state.focus_started_at = time.time()
                            st.session_state.focus_elapsed_before = 0
                            st.session_state.focus_paused = False

                            st.rerun()

                    else:
                        st.write("🔒 Locked")


        st.write("---")

        # ====================================================
        # WEEKLY TASK MANAGEMENT
        # ====================================================
        col_title, col_btn = st.columns([2, 1])

        with col_title:
            st.markdown("#### 📋 Weekly Task Management")

        with col_btn:

            if st.session_state.tasks:

                if st.button("🧹 Clear All Tasks"):

                    st.session_state.tasks = []

                    permanent_save(
                        "tasks",
                        TASKS_FILE,
                        st.session_state.tasks
                    )

                    st.success("All tasks cleared!")

                    st.rerun()


        if not st.session_state.tasks:

            st.info("Vault is empty. Add tasks below.")

        else:

            for task in st.session_state.tasks:

                t_col1, t_col2, t_col3 = st.columns(
                    [2.2, 1.3, 0.9]
                )

                with t_col1:

                    if task.get("done", False):

                        st.markdown(
                            f"✅ ~~{task['title']}~~"
                        )

                    else:

                        day_text = task.get(
                            "assigned_day",
                            "None"
                        )

                        st.markdown(
                            f"📌 **{task['title']}** "
                            f"<span style='font-size:0.75rem;color:gray;'>"
                            f"({day_text})</span>",
                            unsafe_allow_html=True
                        )

                with t_col2:

                    current_days_list = [
                        "None"
                    ] + DAYS_OF_WEEK

                    try:

                        current_day_idx = current_days_list.index(
                            task.get(
                                "assigned_day",
                                "None"
                            )
                        )

                    except ValueError:

                        current_day_idx = 0

                    selected_day = st.selectbox(
                        "Day",
                        current_days_list,
                        key=f"day_pick_{task['id']}",
                        index=current_day_idx,
                        label_visibility="collapsed"
                    )

                    if selected_day != task.get(
                        "assigned_day",
                        "None"
                    ):

                        task["assigned_day"] = selected_day

                        permanent_save(
                            "tasks",
                            TASKS_FILE,
                            st.session_state.tasks
                        )

                        st.rerun()

                with t_col3:

                    if st.button(
                        "🗑️",
                        key=f"del_task_{task['id']}",
                        help="Delete Task"
                    ):

                        st.session_state.tasks = [
                            t for t in st.session_state.tasks
                            if t["id"] != task["id"]
                        ]

                        permanent_save(
                            "tasks",
                            TASKS_FILE,
                            st.session_state.tasks
                        )

                        st.rerun()

                st.markdown(
                    "<div style='margin:-10px 0;'></div>",
                    unsafe_allow_html=True
                )


        st.write("---")

        # ====================================================
        # ADD TASK
        # ====================================================
        st.markdown("### 📅 Add Task to Weekly Vault")

        with st.form(
            "weekly_add_form",
            clear_on_submit=True
        ):

            w_title = st.text_input(
                "New Task Title:"
            )

            submit_w = st.form_submit_button(
                "➕ Save into Vault"
            )

            if submit_w and w_title:

                new_t = {
                    "id": str(
                        int(time.time() * 1000)
                    ),
                    "title": w_title,
                    "assigned_day": "None",
                    "done": False,
                    "hours_done": 0.0
                }

                st.session_state.tasks.append(
                    new_t
                )

                permanent_save(
                    "tasks",
                    TASKS_FILE,
                    st.session_state.tasks
                )

                st.success(
                    "Task added successfully!"
                )

                st.rerun()


    # ========================================================
    # RIGHT COLUMN
    # ========================================================
    with right_col:

        st.markdown(
            "### ⏱️ Focus Arena & Live Stopwatch"
        )

        # ====================================================
        # STOPWATCH
        # ====================================================
        if st.session_state.active_focus_task:

            active_task = (
                st.session_state.active_focus_task
            )

            st.success(
                f"Focused Task: {active_task['title']}"
            )

            st.info(
                "🔥 Stopwatch Focus Session. "
                "Stay locked in!"
            )

            # Calculate elapsed time
            if st.session_state.focus_started_at:

                if st.session_state.focus_paused:

                    elapsed = (
                        st.session_state.focus_elapsed_before
                    )

                else:

                    elapsed = (
                        st.session_state.focus_elapsed_before
                        + (
                            time.time()
                            - st.session_state.focus_started_at
                        )
                    )

            else:

                elapsed = 0

            elapsed = max(0, int(elapsed))

            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60

            st.markdown(
                textwrap.dedent(f"""
                    <div style="
                        text-align:center;
                        padding:20px;
                        border-radius:15px;
                        background:#111827;
                        margin:15px 0;
                    ">
                        <div style="
                            color:#9CA3AF;
                            font-size:15px;
                        ">
                            FOCUS TIME
                        </div>

                        <div style="
                            color:#00FF88;
                            font-size:48px;
                            font-weight:700;
                            font-family:monospace;
                        ">
                            {hours:02d}:{minutes:02d}:{seconds:02d}
                        </div>
                    </div>
                """),
                unsafe_allow_html=True
            )

            # =================================================
            # PAUSE / RESUME / STOP
            # =================================================
            b1, b2 = st.columns(2)

            with b1:

                if not st.session_state.focus_paused:

                    if st.button(
                        "⏸️ Pause",
                        use_container_width=True
                    ):

                        st.session_state.focus_elapsed_before = elapsed
                        st.session_state.focus_paused = True

                        st.rerun()

                else:

                    if st.button(
                        "▶️ Resume",
                        use_container_width=True
                    ):

                        st.session_state.focus_started_at = time.time()
                        st.session_state.focus_paused = False

                        st.rerun()

            with b2:

                if st.button(
                    "⏹️ Stop & Save",
                    use_container_width=True
                ):

                    final_elapsed = elapsed

                    final_hours = round(
                        final_elapsed / 3600,
                        4
                    )

                    for t in st.session_state.tasks:

                        if (
                            t["id"]
                            == active_task["id"]
                        ):

                            t["hours_done"] = round(
                                float(
                                    t.get(
                                        "hours_done",
                                        0
                                    )
                                )
                                + final_hours,
                                4
                            )

                    permanent_save(
                        "tasks",
                        TASKS_FILE,
                        st.session_state.tasks
                    )

                    st.session_state.timer_logs.append(
                        {
                            "date": formatted_display_date,
                            "task_title": active_task["title"],
                            "hours_focused": final_hours,
                            "seconds_focused": final_elapsed
                        }
                    )

                    permanent_save(
                        "timer_logs",
                        TIMER_FILE,
                        st.session_state.timer_logs
                    )

                    st.session_state.active_focus_task = None
                    st.session_state.is_focus_running = False
                    st.session_state.focus_started_at = None
                    st.session_state.focus_elapsed_before = 0
                    st.session_state.focus_paused = False

                    st.success(
                        f"🎉 Session saved! "
                        f"You studied for "
                        f"{hours:02d}:{minutes:02d}:{seconds:02d}."
                    )

                    st.balloons()

                    time.sleep(0.5)

                    st.rerun()

            # Auto-refresh while stopwatch is running
            if not st.session_state.focus_paused:

                time.sleep(1)
                st.rerun()

        else:

            st.info(
                "💡 Click 'Focus Now' next to any task "
                "to start your stopwatch."
            )


        st.markdown(
            "<hr style='border:1px solid #ccc;margin:20px 0;'>",
            unsafe_allow_html=True
        )

        st.markdown(
            '<div id="target-tracker"></div>',
            unsafe_allow_html=True
        )

        # ====================================================
        # DAILY SESSIONS
        # ====================================================
        st.markdown(
            "### 🎯 Daily Sessions (90-Minute Target Tracker)"
        )

        st.markdown(
            f"**Day:** {current_day_name} | "
            f"**Date:** {formatted_display_date}"
        )

        st.caption(
            "প্রতিটি সেশন ৯০ মিনিটের। "
            "আপনার পড়ার লক্ষ্য অনুযায়ী নিচে টিক দিন:"
        )


        if today_date_str not in st.session_state.daily_sessions:

            st.session_state.daily_sessions[
                today_date_str
            ] = {
                "day_name": current_day_name,
                "display_date": formatted_display_date,
                "sessions": {
                    f"90_{i}": False
                    for i in range(1, 11)
                }
            }

            permanent_save(
                "daily_sessions",
                DAILY_SESSIONS_FILE,
                st.session_state.daily_sessions
            )

        else:

            st.session_state.daily_sessions[
                today_date_str
            ]["day_name"] = current_day_name

            st.session_state.daily_sessions[
                today_date_str
            ]["display_date"] = formatted_display_date


        current_day_data = (
            st.session_state.daily_sessions[
                today_date_str
            ]
        )

        cols_chk = st.columns(2)

        session_keys = list(
            current_day_data["sessions"].keys()
        )

        for i, s_key in enumerate(session_keys):

            col_idx = i % 2

            with cols_chk[col_idx]:

                val = (
                    current_day_data["sessions"][s_key]
                )

                new_val = st.checkbox(
                    "90",
                    value=val,
                    key=f"ds_{today_date_str}_{i}"
                )

                if new_val != val:

                    current_day_data["sessions"][
                        s_key
                    ] = new_val

                    permanent_save(
                        "daily_sessions",
                        DAILY_SESSIONS_FILE,
                        st.session_state.daily_sessions
                    )

                    st.rerun()


        completed_count = sum(
            1
            for v in current_day_data["sessions"].values()
            if v
        )

        total_minutes_today = (
            completed_count * 90
        )

        st.markdown(
            f"💡 **আজকের মোট পড়া হয়েছে:** "
            f"`{total_minutes_today} মিনিট`"
        )


        st.markdown(
            "<hr style='border:1px solid #ccc;margin:20px 0;'>",
            unsafe_allow_html=True
        )


        # ====================================================
        # STUDY HISTORY PDF
        # ====================================================
        st.markdown(
            "#### 📥 Study History PDF Report"
        )

        if REPORTLAB_AVAILABLE:

            def generate_history_pdf(
                sessions_data
            ):

                buffer = BytesIO()

                doc = SimpleDocTemplate(
                    buffer,
                    pagesize=letter,
                    rightMargin=30,
                    leftMargin=30,
                    topMargin=30,
                    bottomMargin=30
                )

                story = []

                styles = getSampleStyleSheet()

                title_style = ParagraphStyle(
                    "TitleStyle",
                    parent=styles["Heading1"],
                    fontSize=16,
                    textColor=colors.HexColor(
                        "#FF4B4B"
                    ),
                    spaceAfter=15,
                    alignment=1
                )

                cell_style = ParagraphStyle(
                    "CellStyle",
                    parent=styles["Normal"],
                    fontSize=10,
                    leading=14,
                    textColor=colors.HexColor(
                        "#222222"
                    )
                )

                header_style = ParagraphStyle(
                    "HeaderStyle",
                    parent=styles["Normal"],
                    fontSize=11,
                    leading=14,
                    fontName="Helvetica-Bold",
                    textColor=colors.whitesmoke
                )

                story.append(
                    Paragraph(
                        "Daily Study History Report - Muhit",
                        title_style
                    )
                )

                story.append(
                    Spacer(1, 10)
                )

                table_content = [
                    [
                        Paragraph("Date", header_style),
                        Paragraph("Day", header_style),
                        Paragraph(
                            "Completed 90m Sessions",
                            header_style
                        ),
                        Paragraph(
                            "Total Minutes",
                            header_style
                        )
                    ]
                ]

                for d_str, d_info in sorted(
                    sessions_data.items(),
                    reverse=True
                ):

                    comp_s = sum(
                        1
                        for v in d_info.get(
                            "sessions",
                            {}
                        ).values()
                        if v
                    )

                    t_mins = comp_s * 90

                    table_content.append(
                        [
                            Paragraph(
                                str(
                                    d_info.get(
                                        "display_date",
                                        d_str
                                    )
                                ),
                                cell_style
                            ),
                            Paragraph(
                                str(
                                    d_info.get(
                                        "day_name",
                                        ""
                                    )
                                ),
                                cell_style
                            ),
                            Paragraph(
                                f"{comp_s} Sessions",
                                cell_style
                            ),
                            Paragraph(
                                f"{t_mins} mins",
                                cell_style
                            )
                        ]
                    )

                pdf_table = Table(
                    table_content,
                    colWidths=[
                        130,
                        110,
                        150,
                        110
                    ]
                )

                pdf_table.setStyle(
                    TableStyle([
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#2E2E2E")
                        ),
                        (
                            "ALIGN",
                            (0, 0),
                            (-1, -1),
                            "LEFT"
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP"
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, 0),
                            8
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, 0),
                            8
                        ),
                        (
                            "BACKGROUND",
                            (0, 1),
                            (-1, -1),
                            colors.HexColor("#F9F9F9")
                        ),
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            colors.HexColor("#CCCCCC")
                        ),
                        (
                            "TOPPADDING",
                            (0, 1),
                            (-1, -1),
                            6
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 1),
                            (-1, -1),
                            6
                        )
                    ])
                )

                story.append(pdf_table)

                doc.build(story)

                buffer.seek(0)

                return buffer.getvalue()


            hist_pdf_bytes = generate_history_pdf(
                st.session_state.daily_sessions
            )

            st.download_button(
                label="📥 Download Study History PDF",
                data=hist_pdf_bytes,
                file_name="study_history_report_muhit.pdf",
                mime="application/pdf",
                key="dl_history_pdf"
            )

        else:

            st.warning(
                "ReportLab library is not installed."
            )


# ============================================================
# PAGE 2: SYLLABUS TRACKER
# ============================================================
elif st.session_state.page == "📖 Syllabus Tracker":

    if st.session_state.is_focus_running:

        st.error(
            "⚠️ Focus session is currently active! "
            "Be Consistent and Determined! "
            "Complete your session first."
        )

    else:

        st.title(
            "📖 Subject & Chapter Syllabus Tracker"
        )

        st.info(
            "⚡ Track your chapter progress below "
            "and generate custom subject-wise PDF "
            "performance reports instantly."
        )

        st.write("---")

        st.subheader(
            "📚 Chapter Progress Checklist"
        )

        for sub, content in (
            st.session_state.syllabus.items()
        ):

            with st.expander(
                f"📘 {sub}",
                expanded=False
            ):

                chapters = content.get(
                    "Chapters",
                    {}
                )

                if chapters:

                    target_cols = get_subject_cols(
                        sub
                    )

                    for ch, parts in chapters.items():

                        st.markdown(
                            f"📍 **{ch}**"
                        )

                        cols = st.columns(
                            len(target_cols)
                        )

                        for col_idx, col_name in enumerate(
                            target_cols
                        ):

                            with cols[col_idx]:

                                val = parts.get(
                                    col_name,
                                    False
                                )

                                chk_val = st.checkbox(
                                    col_name,
                                    value=val,
                                    key=(
                                        f"chk_{sub}_"
                                        f"{ch}_{col_name}"
                                    )
                                )

                                if chk_val != val:

                                    st.session_state.syllabus[
                                        sub
                                    ]["Chapters"][
                                        ch
                                    ][col_name] = chk_val

                                    permanent_save(
                                        "syllabus",
                                        SYLLABUS_FILE,
                                        st.session_state.syllabus
                                    )

                                    st.rerun()

                        st.markdown("---")

                else:

                    st.info(
                        "No chapters mapped."
                    )


        st.write("---")

        st.subheader(
            "📊 Subject Progress & PDF Reports"
        )

        subject_names = list(
            st.session_state.syllabus.keys()
        )

        tabs = st.tabs(
            [
                f"📘 {s.split(' ')[0]}"
                for s in subject_names
            ]
        )


        for idx, sub_name in enumerate(
            subject_names
        ):

            with tabs[idx]:

                st.markdown(
                    f"#### 📑 {sub_name} Progress Report"
                )

                content = (
                    st.session_state.syllabus[
                        sub_name
                    ]
                )

                chapters = content.get(
                    "Chapters",
                    {}
                )

                target_cols = get_subject_cols(
                    sub_name
                )

                total_pillars = len(
                    target_cols
                )

                sub_report_data = []

                for ch, parts in chapters.items():

                    completed_pillars = [
                        col
                        for col in target_cols
                        if parts.get(col, False)
                    ]

                    done_count = len(
                        completed_pillars
                    )

                    percentage = int(
                        (
                            done_count
                            / total_pillars
                        ) * 100
                    )

                    sub_report_data.append(
                        {
                            "Chapter Name": ch,
                            "Completed Progress Metrics":
                                ", ".join(
                                    completed_pillars
                                )
                                if completed_pillars
                                else "—",
                            "Progress (%)":
                                f"{percentage}%"
                        }
                    )


                if sub_report_data:

                    df_sub = pd.DataFrame(
                        sub_report_data
                    )

                    st.dataframe(
                        df_sub,
                        use_container_width=True,
                        hide_index=True
                    )


                    if REPORTLAB_AVAILABLE:

                        def generate_subject_pdf(
                            subject_title,
                            dataframe
                        ):

                            buffer = BytesIO()

                            doc = SimpleDocTemplate(
                                buffer,
                                pagesize=letter,
                                rightMargin=30,
                                leftMargin=30,
                                topMargin=30,
                                bottomMargin=30
                            )

                            story = []

                            styles = getSampleStyleSheet()

                            title_style = ParagraphStyle(
                                "TitleStyle",
                                parent=styles["Heading1"],
                                fontSize=16,
                                textColor=colors.HexColor(
                                    "#FF4B4B"
                                ),
                                spaceAfter=15,
                                alignment=1
                            )

                            cell_style = ParagraphStyle(
                                "CellStyle",
                                parent=styles["Normal"],
                                fontSize=8,
                                leading=12,
                                textColor=colors.HexColor(
                                    "#222222"
                                )
                            )

                            header_style = ParagraphStyle(
                                "HeaderStyle",
                                parent=styles["Normal"],
                                fontSize=9,
                                leading=12,
                                fontName="Helvetica-Bold",
                                textColor=colors.whitesmoke
                            )

                            story.append(
                                Paragraph(
                                    f"Progress Report: "
                                    f"{subject_title} (Muhit)",
                                    title_style
                                )
                            )

                            story.append(
                                Spacer(1, 10)
                            )

                            table_content = [
                                [
                                    Paragraph(
                                        "Chapter Name",
                                        header_style
                                    ),
                                    Paragraph(
                                        "Completed Progress Metrics",
                                        header_style
                                    ),
                                    Paragraph(
                                        "Progress (%)",
                                        header_style
                                    )
                                ]
                            ]

                            for _, row in dataframe.iterrows():

                                c_para = Paragraph(
                                    str(
                                        row[
                                            "Chapter Name"
                                        ]
                                    ),
                                    cell_style
                                )

                                m_para = Paragraph(
                                    str(
                                        row[
                                            "Completed Progress Metrics"
                                        ]
                                    ),
                                    cell_style
                                )

                                p_para = Paragraph(
                                    str(
                                        row[
                                            "Progress (%)"
                                        ]
                                    ),
                                    cell_style
                                )

                                table_content.append(
                                    [
                                        c_para,
                                        m_para,
                                        p_para
                                    ]
                                )


                            pdf_table = Table(
                                table_content,
                                colWidths=[
                                    220,
                                    220,
                                    80
                                ],
                                repeatRows=1
                            )

                            pdf_table.setStyle(
                                TableStyle([
                                    (
                                        "BACKGROUND",
                                        (0, 0),
                                        (-1, 0),
                                        colors.HexColor(
                                            "#2E2E2E"
                                        )
                                    ),
                                    (
                                        "ALIGN",
                                        (0, 0),
                                        (-1, -1),
                                        "LEFT"
                                    ),
                                    (
                                        "VALIGN",
                                        (0, 0),
                                        (-1, -1),
                                        "TOP"
                                    ),
                                    (
                                        "BOTTOMPADDING",
                                        (0, 0),
                                        (-1, 0),
                                        8
                                    ),
                                    (
                                        "TOPPADDING",
                                        (0, 0),
                                        (-1, 0),
                                        8
                                    ),
                                    (
                                        "BACKGROUND",
                                        (0, 1),
                                        (-1, -1),
                                        colors.HexColor(
                                            "#F9F9F9"
                                        )
                                    ),
                                    (
                                        "GRID",
                                        (0, 0),
                                        (-1, -1),
                                        0.5,
                                        colors.HexColor(
                                            "#CCCCCC"
                                        )
                                    ),
                                    (
                                        "TOPPADDING",
                                        (0, 1),
                                        (-1, -1),
                                        6
                                    ),
                                    (
                                        "BOTTOMPADDING",
                                        (0, 1),
                                        (-1, -1),
                                        6
                                    )
                                ])
                            )

                            story.append(
                                pdf_table
                            )

                            doc.build(story)

                            buffer.seek(0)

                            return buffer.getvalue()


                        pdf_bytes = (
                            generate_subject_pdf(
                                sub_name,
                                df_sub
                            )
                        )

                        file_safe_name = (
                            sub_name
                            .split(" ")[0]
                            .lower()
                        )

                        st.download_button(
                            label=(
                                f"📥 Download "
                                f"{sub_name.split(' ')[0]} "
                                f"PDF Report"
                            ),
                            data=pdf_bytes,
                            file_name=(
                                f"{file_safe_name}_"
                                f"progress_report_muhit.pdf"
                            ),
                            mime="application/pdf",
                            key=f"dl_pdf_{sub_name}"
                        )

                    else:

                        st.warning(
                            "ReportLab library is not installed, "
                            "PDF generation is disabled."
                        )


# ============================================================
# PAGE 3: ADMISSION EXAM
# ============================================================
elif st.session_state.page == "🎓 ভর্তি পরীক্ষার তারিখ":

    if st.session_state.is_focus_running:

        st.error(
            "⚠️ Focus session is currently active! "
            "Be Consistent and Determined! "
            "Complete your session first."
        )

    else:

        st.title(
            "🎓 ভর্তি পরীক্ষার তারিখ ও শিডিউল"
        )

        st.write("---")

        st.markdown(
            "#### 📋 সংরক্ষিত ভর্তি পরীক্ষার তালিকা"
        )


        if not st.session_state.admission_exams:

            st.info(
                "এখনো কোনো বিশ্ববিদ্যালয়ের তথ্য যোগ করা হয়নি। "
                "নিচে ফর্ম থেকে তথ্য যুক্ত করুন।"
            )

        else:

            # =================================================
            # ADMISSION TABLE WITH COUNTDOWN
            # =================================================
            header_cols = st.columns(
                [1.8, 1.2, 1.2, 1.2, 1.2, 0.6]
            )

            with header_cols[0]:
                st.markdown("**🏛️ University**")

            with header_cols[1]:
                st.markdown("**📝 Exam**")

            with header_cols[2]:
                st.markdown("**🚀 Start**")

            with header_cols[3]:
                st.markdown("**⏳ Deadline**")

            with header_cols[4]:
                st.markdown("**⏱️ Countdown**")

            with header_cols[5]:
                st.markdown("**🗑️**")


            for ex in st.session_state.admission_exams:

                e_c1, e_c2, e_c3, e_c4, e_c5, e_c6 = st.columns(
                    [1.8, 1.2, 1.2, 1.2, 1.2, 0.6]
                )

                with e_c1:
                    st.markdown(
                        f"🏛️ **{ex['University Name']}**"
                    )

                with e_c2:
                    st.caption(
                        f"📝 {ex['Exam date']}"
                    )

                with e_c3:
                    st.caption(
                        f"🚀 {ex['1st date']}"
                    )

                with e_c4:
                    st.caption(
                        f"⏳ {ex['Last Date']}"
                    )

                # =================================================
                # COUNTDOWN
                # =================================================
                with e_c5:

                    try:

                        deadline = datetime.strptime(
                            ex["Last Date"],
                            "%d %B, %Y"
                        ).date()

                        days_left = (
                            deadline
                            - now_bd.date()
                        ).days

                        if days_left > 0:

                            st.markdown(
                                f"🟢 **{days_left} days**"
                            )

                        elif days_left == 0:

                            st.markdown(
                                "🔴 **Today!**"
                            )

                        else:

                            st.markdown(
                                "⚫ **Expired**"
                            )

                    except Exception:

                        st.caption(
                            "N/A"
                        )


                with e_c6:

                    if st.button(
                        "🗑️",
                        key=f"del_ex_{ex['id']}",
                        help="ডিলিট করুন"
                    ):

                        st.session_state.admission_exams = [
                            item
                            for item in st.session_state.admission_exams
                            if item["id"] != ex["id"]
                        ]

                        permanent_save(
                            "admission_exams",
                            EXAMS_FILE,
                            st.session_state.admission_exams
                        )

                        st.rerun()

                st.markdown(
                    "<div style='margin:-5px 0;'></div>",
                    unsafe_allow_html=True
                )


            st.write("")


            # =================================================
            # ADMISSION PDF
            # =================================================
            if REPORTLAB_AVAILABLE:

                def generate_admission_pdf(
                    exams_list
                ):

                    buffer = BytesIO()

                    doc = SimpleDocTemplate(
                        buffer,
                        pagesize=letter,
                        rightMargin=30,
                        leftMargin=30,
                        topMargin=30,
                        bottomMargin=30
                    )

                    story = []

                    styles = getSampleStyleSheet()

                    title_style = ParagraphStyle(
                        "TitleStyle",
                        parent=styles["Heading1"],
                        fontSize=16,
                        textColor=colors.HexColor(
                            "#FF4B4B"
                        ),
                        spaceAfter=15,
                        alignment=1
                    )

                    cell_style = ParagraphStyle(
                        "CellStyle",
                        parent=styles["Normal"],
                        fontSize=9,
                        leading=13,
                        textColor=colors.HexColor(
                            "#222222"
                        )
                    )

                    header_style = ParagraphStyle(
                        "HeaderStyle",
                        parent=styles["Normal"],
                        fontSize=10,
                        leading=13,
                        fontName="Helvetica-Bold",
                        textColor=colors.whitesmoke
                    )

                    story.append(
                        Paragraph(
                            "Admission Exam Schedule Report - Muhit",
                            title_style
                        )
                    )

                    story.append(
                        Spacer(1, 10)
                    )

                    table_content = [
                        [
                            Paragraph(
                                "University Name",
                                header_style
                            ),
                            Paragraph(
                                "Exam Date",
                                header_style
                            ),
                            Paragraph(
                                "1st Date",
                                header_style
                            ),
                            Paragraph(
                                "Last Date",
                                header_style
                            ),
                            Paragraph(
                                "Countdown",
                                header_style
                            )
                        ]
                    ]


                    for ex in exams_list:

                        try:

                            deadline = datetime.strptime(
                                ex["Last Date"],
                                "%d %B, %Y"
                            ).date()

                            days_left = (
                                deadline
                                - now_bd.date()
                            ).days

                            countdown = (
                                f"{days_left} days"
                                if days_left > 0
                                else (
                                    "Today"
                                    if days_left == 0
                                    else "Expired"
                                )
                            )

                        except Exception:

                            countdown = "N/A"


                        table_content.append(
                            [
                                Paragraph(
                                    str(
                                        ex[
                                            "University Name"
                                        ]
                                    ),
                                    cell_style
                                ),
                                Paragraph(
                                    str(
                                        ex[
                                            "Exam date"
                                        ]
                                    ),
                                    cell_style
                                ),
                                Paragraph(
                                    str(
                                        ex[
                                            "1st date"
                                        ]
                                    ),
                                    cell_style
                                ),
                                Paragraph(
                                    str(
                                        ex[
                                            "Last Date"
                                        ]
                                    ),
                                    cell_style
                                ),
                                Paragraph(
                                    countdown,
                                    cell_style
                                )
                            ]
                        )


                    pdf_table = Table(
                        table_content,
                        colWidths=[
                            125,
                            90,
                            95,
                            95,
                            75
                        ],
                        repeatRows=1
                    )

                    pdf_table.setStyle(
                        TableStyle([
                            (
                                "BACKGROUND",
                                (0, 0),
                                (-1, 0),
                                colors.HexColor(
                                    "#2E2E2E"
                                )
                            ),
                            (
                                "ALIGN",
                                (0, 0),
                                (-1, -1),
                                "LEFT"
                            ),
                            (
                                "VALIGN",
                                (0, 0),
                                (-1, -1),
                                "TOP"
                            ),
                            (
                                "BACKGROUND",
                                (0, 1),
                                (-1, -1),
                                colors.HexColor(
                                    "#F9F9F9"
                                )
                            ),
                            (
                                "GRID",
                                (0, 0),
                                (-1, -1),
                                0.5,
                                colors.HexColor(
                                    "#CCCCCC"
                                )
                            ),
                            (
                                "TOPPADDING",
                                (0, 0),
                                (-1, -1),
                                6
                            ),
                            (
                                "BOTTOMPADDING",
                                (0, 0),
                                (-1, -1),
                                6
                            )
                        ])
                    )

                    story.append(
                        pdf_table
                    )

                    doc.build(story)

                    buffer.seek(0)

                    return buffer.getvalue()


                admission_pdf_bytes = (
                    generate_admission_pdf(
                        st.session_state.admission_exams
                    )
                )

                st.download_button(
                    label=(
                        "📥 Download Admission "
                        "Schedule PDF"
                    ),
                    data=admission_pdf_bytes,
                    file_name=(
                        "admission_schedule_muhit.pdf"
                    ),
                    mime="application/pdf",
                    key="dl_admission_pdf"
                )


        st.write("---")


        # ====================================================
        # ADD NEW EXAM
        # ====================================================
        with st.form(
            "admission_exam_form",
            clear_on_submit=True
        ):

            st.markdown(
                "#### ➕ নতুন ভর্তি পরীক্ষার তথ্য যোগ করুন"
            )

            f_col1, f_col2 = st.columns(2)

            with f_col1:

                uni_name_input = st.text_input(
                    "University Name "
                    "(যেমন: Dhaka University / BUET)"
                )

                exam_date_input = st.date_input(
                    "Exam Date",
                    value=now_bd.date(),
                    min_value=datetime(
                        2026, 1, 1
                    ).date(),
                    max_value=datetime(
                        2027, 12, 31
                    ).date()
                )

            with f_col2:

                first_date_input = st.date_input(
                    "1st Date "
                    "(Application Start)",
                    value=now_bd.date(),
                    min_value=datetime(
                        2026, 1, 1
                    ).date(),
                    max_value=datetime(
                        2027, 12, 31
                    ).date()
                )

                last_date_input = st.date_input(
                    "Last Date "
                    "(Application Deadline)",
                    value=now_bd.date(),
                    min_value=datetime(
                        2026, 1, 1
                    ).date(),
                    max_value=datetime(
                        2027, 12, 31
                    ).date()
                )


            submit_exam = st.form_submit_button(
                "💾 সেভ করুন"
            )


            if submit_exam:

                if uni_name_input:

                    new_exam_entry = {
                        "id": str(
                            int(
                                time.time() * 1000
                            )
                        ),
                        "University Name":
                            uni_name_input,
                        "Exam date":
                            exam_date_input.strftime(
                                "%d %B, %Y"
                            ),
                        "1st date":
                            first_date_input.strftime(
                                "%d %B, %Y"
                            ),
                        "Last Date":
                            last_date_input.strftime(
                                "%d %B, %Y"
                            )
                    }

                    st.session_state.admission_exams.append(
                        new_exam_entry
                    )

                    permanent_save(
                        "admission_exams",
                        EXAMS_FILE,
                        st.session_state.admission_exams
                    )

                    st.success(
                        "সফলভাবে ভর্তি পরীক্ষার তথ্য সংরক্ষণ করা হয়েছে!"
                    )

                    st.rerun()

                else:

                    st.warning(
                        "দয়া করে অন্তত University Name লিখুন।"
                    )


# ============================================================
# PAGE 4: PDF TOOL
# ============================================================
elif st.session_state.page == "📄 PDF Tool":

    if st.session_state.is_focus_running:

        st.error(
            "⚠️ Focus session is currently active! "
            "Be Consistent and Determined! "
            "Complete your session first."
        )

    else:

        st.markdown(
            textwrap.dedent("""
                <h2 style="
                    text-align:center;
                    color:#4CAF50;
                ">
                    👨‍💻 Mahathir Muhit Personal Workspace
                </h2>
            """),
            unsafe_allow_html=True
        )

        st.markdown(
            textwrap.dedent("""
                <h3 style="
                    text-align:center;
                    color:#888888;
                ">
                    🤖 ২-ইন-১ পিডিএফ অটো-লেআউট টুল
                    (নিখুঁত রেশিও)
                </h3>
            """),
            unsafe_allow_html=True
        )

        st.write("---")

        st.write(
            "ফাইল আপলোড করুন; ল্যান্ডস্কেপ স্লাইডগুলো "
            "কোনো বর্ডার বা কাটিং ছাড়াই ১টি পেজে "
            "৩টি করে নিখুঁতভাবে বসে যাবে।"
        )


        uploaded_files = st.file_uploader(
            "আপনার পিডিএফ ফাইলগুলো এখানে সিলেক্ট করুন",
            type=["pdf"],
            accept_multiple_files=True,
            key="pdf_tool_uploader"
        )


        if uploaded_files:

            if st.button(
                "🔄 প্রসেসিং শুরু করুন",
                key="pdf_process_btn"
            ):

                with st.spinner(
                    "কাজ চলছে... নিখুঁত রেশিওতে "
                    "লেআউট তৈরি হচ্ছে..."
                ):

                    try:

                        merged_writer = PdfWriter()

                        for uploaded_file in uploaded_files:

                            reader = PdfReader(
                                uploaded_file
                            )

                            for page_obj in reader.pages:

                                merged_writer.add_page(
                                    page_obj
                                )


                        temp_merged = (
                            "temp_merged.pdf"
                        )

                        with open(
                            temp_merged,
                            "wb"
                        ) as f:

                            merged_writer.write(f)


                        output_pdf = (
                            "processed_output.pdf"
                        )

                        final_writer = PdfWriter()

                        reader = PdfReader(
                            temp_merged
                        )

                        total_pages = len(
                            reader.pages
                        )


                        for i in range(
                            0,
                            total_pages,
                            3
                        ):

                            first_page = (
                                reader.pages[i]
                            )

                            orig_w = float(
                                first_page.mediabox.width
                            )

                            orig_h = float(
                                first_page.mediabox.height
                            )

                            new_w = orig_w
                            new_h = orig_h * 3

                            new_page = (
                                final_writer.add_blank_page(
                                    width=new_w,
                                    height=new_h
                                )
                            )


                            for j in range(3):

                                if (
                                    i + j
                                    < total_pages
                                ):

                                    current_slide = (
                                        reader.pages[
                                            i + j
                                        ]
                                    )

                                    ty = (
                                        (2 - j)
                                        * orig_h
                                    )

                                    new_page.merge_translated_page(
                                        current_slide,
                                        tx=0,
                                        ty=ty
                                    )


                        with open(
                            output_pdf,
                            "wb"
                        ) as f:

                            final_writer.write(f)


                        if os.path.exists(
                            temp_merged
                        ):

                            os.remove(
                                temp_merged
                            )


                        st.success(
                            "🎉 মাহাথির, আপনার নিখুঁত "
                            "ফুল-স্ক্রিন ফাইলটি তৈরি হয়েছে!"
                        )


                        with open(
                            output_pdf,
                            "rb"
                        ) as f:

                            st.download_button(
                                label=(
                                    "📥 প্রসেসড পিডিএফ "
                                    "ডাউনলোড করুন"
                                ),
                                data=f,
                                file_name=(
                                    "final_output.pdf"
                                ),
                                mime="application/pdf",
                                key="pdf_download_btn"
                            )


                    except Exception as e:

                        st.error(
                            f"দুঃখিত, একটি সমস্যা হয়েছে: {e}"
                        )


# ============================================================
# PAGE 5: SONGS
# ============================================================
elif st.session_state.page == "🎵 গানের জগত":

    if st.session_state.is_focus_running:

        st.error(
            "⚠️ Focus session is currently active! "
            "Complete your session first."
        )

    else:

        st.title("🎵 গানের জগত")

        st.info(
            "তোমার পছন্দের গানগুলো নিচে "
            "সরাসরি প্লেয়ারে শুনতে পারো:"
        )

        st.write("---")


        for idx, song_url in enumerate(
            st.session_state.my_songs,
            1
        ):

            sc1, sc2 = st.columns(
                [5, 1]
            )

            with sc1:

                st.markdown(
                    f"#### গান #{idx}"
                )

                try:

                    st.video(song_url)

                except Exception as e:

                    st.error(
                        f"গান লোড করতে সমস্যা হয়েছে: {e}"
                    )


            with sc2:

                st.write("")
                st.write("")

                if st.button(
                    "🗑️ মুছুন",
                    key=f"del_song_{idx}"
                ):

                    st.session_state.my_songs.pop(
                        idx - 1
                    )

                    permanent_save(
                        "songs",
                        SONGS_FILE,
                        st.session_state.my_songs
                    )

                    st.rerun()


            st.markdown("---")


        # ====================================================
        # ADD SONG
        # ====================================================
        st.markdown(
            "#### ➕ নতুন গান যোগ করুন"
        )

        with st.form(
            "add_song_form",
            clear_on_submit=True
        ):

            new_song_link = st.text_input(
                "YouTube Song Link "
                "(যেমন: https://youtu.be/...)"
            )

            submit_song = st.form_submit_button(
                "💾 গান সেভ করুন"
            )

            if submit_song:

                if new_song_link:

                    st.session_state.my_songs.append(
                        new_song_link
                    )

                    permanent_save(
                        "songs",
                        SONGS_FILE,
                        st.session_state.my_songs
                    )

                    st.success(
                        "নতুন গান সফলভাবে যোগ করা হয়েছে!"
                    )

                    st.rerun()

                else:

                    st.warning(
                        "দয়া করে একটি সঠিক ইউটিউব লিংক দিন।"
                    )


# ============================================================
# FINAL CLOUD SYNC SAFETY NET
# ============================================================
# Every normal app rerun writes the current state to Supabase and the local
# JSON backup. This makes refresh/reload safe for new information entered
# through the app, even if a particular UI action missed its explicit save.
if st.session_state.get("data_initialized"):
    save_all_data()


# ============================================================
# ============================================================
# ============================================================
# ============================================================
# ============================================================
# SUPABASE STATUS
# ============================================================
if not SUPABASE_AVAILABLE:
    st.sidebar.error("🔴 Supabase connection is not active.")
    st.sidebar.caption("Check SUPABASE_URL and SUPABASE_KEY in Secrets.")
elif st.session_state.get("supabase_health_ok"):
    st.sidebar.success("🟢 Cloud save is active")
    if st.session_state.get("last_cloud_save"):
        st.sidebar.caption(f"Last sync: {st.session_state['last_cloud_save']}")
else:
    st.sidebar.error("🔴 Supabase is not responding")
    st.sidebar.caption(st.session_state.get("supabase_health_message", "Unknown database error"))

if st.session_state.get("last_supabase_error"):
    with st.sidebar.expander("Last cloud-save error"):
        st.code(st.session_state["last_supabase_error"])
