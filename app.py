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
            .select("data_value")
            .eq("data_key", key)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]["data_value"]

    except Exception:
        pass

    return default


def supabase_save(key, value):
    if not SUPABASE_AVAILABLE:
        return False

    try:
        supabase.table("app_data").upsert(
            {
                "data_key": key,
                "data_value": value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            on_conflict="data_key"
        ).execute()

        return True

    except Exception:
        return False


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
# NAVIGATION
# ============================================================
page_selection = [
    "🏠 Dashboard & Focus Station",
    "📖 Syllabus Tracker",
    "🎓 ভর্তি পরীক্ষার তারিখ",
    "📄 PDF Tool",
    "🎵 গানের জগত"
]


def handle_nav_change():

    if st.session_state.is_focus_running:

        st.sidebar.error(
            "⚠️ Be Consistent and Determined!"
        )

        time.sleep(1.0)

        # Restore dashboard
        st.session_state.sidebar_radio = st.session_state.page


if "page" not in st.session_state:
    st.session_state.page = page_selection[0]


page_index_map = {
    page_selection[i]: i
    for i in range(len(page_selection))
}


current_index = page_index_map.get(
    st.session_state.page,
    0
)


sidebar_selection = st.sidebar.radio(
    "Go to",
    page_selection,
    index=current_index,
    on_change=handle_nav_change,
    key="sidebar_radio"
)


if (
    sidebar_selection != st.session_state.page
    and not st.session_state.is_focus_running
):
    st.session_state.page = sidebar_selection


# ============================================================
# PAGE 1: DASHBOARD
# ============================================================
if st.session_state.page == "🏠 Dashboard & Focus Station":

    # Visible headline
    st.markdown(
        textwrap.dedent(f"""
            <div style="
                display:flex;
                align-items:center;
                gap:12px;
                margin-bottom:20px;
            ">
                <span style="
                    font-size:32px;
                    line-height:1;
                ">⚡</span>

                <h1 style="
                    margin:0;
                    font-size:2.25rem;
                    font-weight:700;
                    color:#FF4B4B !important;
                    display:block;
                    visibility:visible !important;
                    opacity:1 !important;
                ">
                    {remaining_days} days ahead
                    (Consistent, Determined, Hardwork)
                </h1>
            </div>
        """),
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

            b_col1, b_col2, b_col3 = st.columns(3)

            with b_col1:

                if st.session_state.focus_paused:

                    if st.button("▶️ Resume"):

                        st.session_state.focus_started_at = time.time()
                        st.session_state.focus_paused = False

                        st.rerun()

                else:

                    if st.button("⏸️ Pause"):

                        st.session_state.focus_elapsed_before = elapsed
                        st.session_state.focus_paused = True

                        st.rerun()

            with b_col2:

                if st.button("✅ Finish"):

                    hours_spent = round(elapsed / 3600, 2)

                    # Update task in tasks list
                    for t in st.session_state.tasks:
                        if t["id"] == active_task["id"]:
                            t["done"] = True
                            t["hours_done"] = t.get("hours_done", 0.0) + hours_spent

                    permanent_save(
                        "tasks",
                        TASKS_FILE,
                        st.session_state.tasks
                    )

                    # Log session
                    log_entry = {
                        "date": today_date_str,
                        "task": active_task["title"],
                        "hours": hours_spent
                    }
                    st.session_state.timer_logs.append(log_entry)
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

                    st.success("🎉 Focus session completed and logged!")
                    time.sleep(1)
                    st.rerun()

            with b_col3:

                if st.button("❌ Abort"):

                    st.session_state.active_focus_task = None
                    st.session_state.is_focus_running = False
                    st.session_state.focus_started_at = None
                    st.session_state.focus_elapsed_before = 0
                    st.session_state.focus_paused = False

                    st.warning("Focus session aborted.")
                    time.sleep(1)
                    st.rerun()

            # Refresh ticker if running
            if not st.session_state.focus_paused:
                time.sleep(1)
                st.rerun()

        else:
            st.info("Select a task from your daily list and click **'Focus Now'** to start tracking time.")


# ============================================================
# PAGE 2: SYLLABUS TRACKER
# ============================================================
elif st.session_state.page == "📖 Syllabus Tracker":

    st.markdown("### 📖 HSC Syllabus Progress Tracker")

    selected_subject = st.selectbox(
        "Select Subject",
        list(st.session_state.syllabus.keys())
    )

    subject_data = st.session_state.syllabus[selected_subject]
    chapters = subject_data.get("Chapters", {})
    cols_to_use = get_subject_cols(selected_subject)

    if chapters:

        # Build Dataframe rows
        table_rows = []
        chapter_names = list(chapters.keys())

        for ch in chapter_names:
            row_data = {"Chapter": ch}
            for col in cols_to_use:
                row_data[col] = chapters[ch].get(col, False)
            table_rows.append(row_data)

        df = pd.DataFrame(table_rows)

        # Config columns for data editor
        column_config = {
            "Chapter": st.column_config.TextColumn("Chapter Name", disabled=True)
        }
        for col in cols_to_use:
            column_config[col] = st.column_config.CheckboxColumn(col)

        edited_df = st.data_editor(
            df,
            column_config=column_config,
            hide_index=True,
            use_container_width=True,
            key=f"editor_{selected_subject}"
        )

        # Save updates if changed
        updated = False
        for idx, row in edited_df.iterrows():
            ch_name = row["Chapter"]
            for col in cols_to_use:
                val = bool(row[col])
                if chapters[ch_name].get(col) != val:
                    chapters[ch_name][col] = val
                    updated = True

        if updated:
            permanent_save(
                "syllabus",
                SYLLABUS_FILE,
                st.session_state.syllabus
            )
            st.toast("Progress saved successfully!")

    else:
        st.info("No chapters found for this subject.")


# ============================================================
# PAGE 3: ADMISSION EXAMS
# ============================================================
elif st.session_state.page == "🎓 ভর্তি পরীক্ষার তারিখ":

    st.markdown("### 🎓 ভর্তি পরীক্ষার তারিখ ও কাউন্টডাউন")

    # Add new exam
    with st.form("exam_form", clear_on_submit=True):
        ex_name = st.text_input("পরীক্ষার নাম (যেমন: ঢাকা বিশ্ববিদ্যালয় ভর্তি পরীক্ষা)")
        ex_date = st.date_input("পরীক্ষার তারিখ", value=datetime.today() + timedelta(days=30))
        ex_submit = st.form_submit_button("➕ পরীক্ষা যোগ করুন")

        if ex_submit and ex_name:
            new_ex = {
                "id": str(int(time.time() * 1000)),
                "name": ex_name,
                "date": ex_date.strftime("%Y-%m-%d")
            }
            st.session_state.admission_exams.append(new_ex)
            permanent_save("admission_exams", EXAMS_FILE, st.session_state.admission_exams)
            st.success("পরীক্ষা সফলভাবে যোগ করা হয়েছে!")
            st.rerun()

    st.write("---")

    if not st.session_state.admission_exams:
        st.info("কোনো ভর্তি পরীক্ষার তারিখ যোগ করা হয়নি।")
    else:
        for ex in st.session_state.admission_exams:
            ex_dt = datetime.strptime(ex["date"], "%Y-%m-%d").date()
            days_left = (ex_dt - now_bd.date()).days

            col_ex1, col_ex2, col_ex3 = st.columns([2, 1, 0.5])
            with col_ex1:
                st.markdown(f"**{ex['name']}** ({ex['date'])})")
            with col_ex2:
                if days_left >= 0:
                    st.markdown(f"⏳ **{days_left} দিন বাকি**")
                else:
                    st.markdown("✅ পরীক্ষা সম্পন্ন")
            with col_ex3:
                if st.button("🗑️", key=f"del_ex_{ex['id']}"):
                    st.session_state.admission_exams = [
                        e for e in st.session_state.admission_exams if e["id"] != ex["id"]
                    ]
                    permanent_save("admission_exams", EXAMS_FILE, st.session_state.admission_exams)
                    st.rerun()


# ============================================================
# PAGE 4: PDF TOOL
# ============================================================
elif st.session_state.page == "📄 PDF Tool":

    st.markdown("### 📄 PDF Merger & Splitter Tool")

    pdf_tab1, pdf_tab2 = st.tabs(["🔗 Merge PDFs", "✂️ Split PDF"])

    with pdf_tab1:
        st.markdown("#### Merge multiple PDF files into one")
        uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True, key="merge_uploader")

        if uploaded_files and len(uploaded_files) > 1:
            if st.button("🚀 Merge PDFs"):
                writer = PdfWriter()
                for f in uploaded_files:
                    reader = PdfReader(f)
                    for page in reader.pages:
                        writer.add_page(page)

                output_stream = BytesIO()
                writer.write(output_stream)
                output_stream.seek(0)

                st.download_button(
                    label="📥 Download Merged PDF",
                    data=output_stream,
                    file_name="merged_output.pdf",
                    mime="application/pdf"
                )

    with pdf_tab2:
        st.markdown("#### Extract pages from a PDF")
        single_pdf = st.file_uploader("Upload PDF file", type=["pdf"], key="split_uploader")

        if single_pdf:
            reader = PdfReader(single_pdf)
            total_pages = len(reader.pages)
            st.info(f"Total pages in PDF: {total_pages}")

            page_range = st.text_input("Enter page numbers/ranges to extract (e.g., 1-3, 5):")

            if st.button("✂️ Extract Pages"):
                try:
                    writer = PdfWriter()
                    pages_to_add = []
                    parts = page_range.split(",")
                    for part in parts:
                        if "-" in part:
                            start, end = map(int, part.split("-"))
                            pages_to_add.extend(range(start - 1, end))
                        else:
                            pages_to_add.append(int(part) - 1)

                    for p_idx in pages_to_add:
                        if 0 <= p_idx < total_pages:
                            writer.add_page(reader.pages[p_idx])

                    output_stream = BytesIO()
                    writer.write(output_stream)
                    output_stream.seek(0)

                    st.download_button(
                        label="📥 Download Extracted PDF",
                        data=output_stream,
                        file_name="extracted_output.pdf",
                        mime="application/pdf"
                    )
                except Exception as ex:
                    st.error(f"Error parsing page range: {ex}")


# ============================================================
# PAGE 5: SONGS
# ============================================================
elif st.session_state.page == "🎵 গানের জগত":

    st.markdown("### 🎵 গানের জগত (Focus & Relaxation)")

    with st.form("song_form", clear_on_submit=True):
        new_song_url = st.text_input("YouTube Song URL (e.g., https://youtu.be/...)")
        add_song_btn = st.form_submit_button("➕ গান যোগ করুন")

        if add_song_btn and new_song_url:
            st.session_state.my_songs.append(new_song_url)
            permanent_save("songs", SONGS_FILE, st.session_state.my_songs)
            st.success("গান সফলভাবে যোগ করা হয়েছে!")
            st.rerun()

    st.write("---")

    if not st.session_state.my_songs:
        st.info("কোনো গান যোগ করা হয়নি।")
    else:
        for idx, song_url in enumerate(st.session_state.my_songs):
            col_s1, col_s2 = st.columns([3, 1])
            with col_s1:
                st.video(song_url)
            with col_s2:
                if st.button("🗑️ ডিলিট", key=f"del_song_{idx}"):
                    st.session_state.my_songs.pop(idx)
                    permanent_save("songs", SONGS_FILE, st.session_state.my_songs)
                    st.rerun()
