import streamlit as str_module
import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pypdf import PdfReader, PdfWriter

# Try importing ReportLab for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Page Configuration
st.set_page_config(page_title="Muhit's HSC Tracker & Workspace", page_icon="⚡", layout="wide")

# Directory Setup
DATA_DIR = "tracker_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def load_data(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default_val
    return default_val

def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_data_dir(current_username):
    user_dir = os.path.join(DATA_DIR, current_username)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

# --- MULTI-USER AUTHENTICATION CONFIG ---
# এখানে তুমি চাইলে নতুন ইউজার এবং পাসওয়ার্ড যোগ করতে পারো
names = ['Mahathir Muhit', 'Friend User']
usernames = ['muhit', 'friend']
passwords = ['12345', 'abcde'] # প্রত্যেকের আলাদা পাসওয়ার্ড

hashed_passwords = stauth.Hasher(passwords).generate()

credentials = {
    'usernames': {}
}
for i in range(len(usernames)):
    credentials['usernames'][usernames[i]] = {
        'name': names[i],
        'password': hashed_passwords[i]
    }

authenticator = stauth.Authenticate(
    credentials,
    'muhit_portal_cookie',
    'muhit_portal_signature',
    cookie_expiry_days=30
)

# Login Widget Rendering
name, authentication_status, username = authenticator.login('Login', 'main')

if authentication_status == False:
    st.error('ভুল ইউজারনেম অথবা পাসওয়ার্ড!')
elif authentication_status == None:
    st.warning('দয়া করে আপনার ইউজারনেম এবং পাসওয়ার্ড দিয়ে লগইন করুন।')
elif authentication_status == True:
    
    # --- ইউজারের নিজস্ব ফোল্ডার ও ফাইল পাথ সেটআপ ---
    user_folder = get_user_data_dir(username)

    TASKS_FILE = os.path.join(user_folder, "tasks.json")
    SYLLABUS_FILE = os.path.join(user_folder, "syllabus.json")
    TIMER_FILE = os.path.join(user_folder, "timer_logs.json")
    DAILY_SESSIONS_FILE = os.path.join(user_folder, "daily_sessions.json")
    EXAMS_FILE = os.path.join(user_folder, "admission_exams.json")
    SONGS_FILE = os.path.join(user_folder, "songs.json")

    # Initialize Session States & Database Setup
    st.session_state.tasks = load_data(TASKS_FILE, [])
    st.session_state.daily_sessions = load_data(DAILY_SESSIONS_FILE, {})
    st.session_state.admission_exams = load_data(EXAMS_FILE, [])

    DEFAULT_SONGS = [
        "https://youtu.be/B-ISCaZ2EUw?si=LHSLxrwL8gqv48SE",
        "https://youtu.be/iR5U92Eq-_8",
        "https://youtu.be/Agcvgc23bNc",
        "https://youtu.be/QJpfLoGMgqU",
        "https://youtu.be/aar0oGrJcDM?si=wRRJLEnHo4-dMa3j"
    ]
    st.session_state.my_songs = load_data(SONGS_FILE, DEFAULT_SONGS)

    # Checklist Columns Definition for Different Subjects
    CHECKBOX_COLUMNS = ["Class", "Master Book", "Concept Book", "Short Note", "Book Reading", "VAP Master Bank"]
    BIOLOGY_COLUMNS = ["Class", "Master Book", "Book Reading"]
    MATH_COLUMNS = ["Class", "Master Book", "Concept Book", "Short Note", "VAP Master Bank"]

    # User Defined Ordered HSC Syllabus
    HSC_DEFAULT_SYLLABUS = {
        "Physics (1st & 2nd Paper)": {
            "Chapters": {
                "Physics 1st: Chapter 1: ভৌত জগত ও পরিমাপ": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 1st: Chapter 2: ভেক্টর": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 1st: Chapter 3: গতিবিদ্যা": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 1st: Chapter 4: নিউটনীয় বলবিদ্যা": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 1st: Chapter 5: কাজ, শক্তি ও ক্ষমতা": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 1st: Chapter 6: মহাকর্ষ ও অভিকর্ষ": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 1st: Chapter 7: পর্যায়বৃত্ত গতি": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 1st: Chapter 8: তরঙ্গ": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 1st: Chapter 9: গ্যাসের গতি তত্ত্ব": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 2nd: Chapter 1: তাপগতিবিদ্যা": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 2nd: Chapter 2: স্থির তড়িৎ": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 2nd: Chapter 3: চল তড়িৎ": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 2nd: Chapter 4: তড়িৎ প্রবাহের চৌম্বক ক্রিয়া ও চুম্বকত্ব": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 2nd: Chapter 5: তড়িৎ চৌম্বকীয় আবেশ ও পরিবর্তী প্রবাহ": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 2nd: Chapter 6: জ্যামিতিক আলোকবিজ্ঞান": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 2nd: Chapter 7: ভৌত আলোকবিজ্ঞান": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 2nd: Chapter 8: আধুনিক পদার্থবিজ্ঞানের সূচনা": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 2nd: Chapter 9: পরমাণুর মডেল ও নিউক্লীয় পদার্থবিজ্ঞান": {col: False for col in CHECKBOX_COLUMNS},
                "Physics 2nd: Chapter 10: সেমিকন্ডাক্টর ও ইলেকট্রনিক্স": {col: False for col in CHECKBOX_COLUMNS}
            }
        },
        "Chemistry (1st & 2nd Paper)": {
            "Chapters": {
                "Chemistry 1st: Chapter 1: ল্যাবরেটরি নিরাপদ ব্যবহার": {col: False for col in CHECKBOX_COLUMNS},
                "Chemistry 1st: Chapter 2: গুণগত রসায়ন": {col: False for col in CHECKBOX_COLUMNS},
                "Chemistry 1st: Chapter 3: মৌলের পর্যাবৃত্ত ধর্ম ও রাসায়নিক বন্ধন": {col: False for col in CHECKBOX_COLUMNS},
                "Chemistry 1st: Chapter 4: রাসায়নিক পরিবর্তন": {col: False for col in CHECKBOX_COLUMNS},
                "Chemistry 1st: Chapter 5: কর্মমুখী রসায়ন": {col: False for col in CHECKBOX_COLUMNS},
                "Chemistry 2nd: Chapter 1: পরিবেশ রসায়ন": {col: False for col in CHECKBOX_COLUMNS},
                "Chemistry 2nd: Chapter 2: জৈব রসায়ন": {col: False for col in CHECKBOX_COLUMNS},
                "Chemistry 2nd: Chapter 3: পরিমাণগত রসায়ন": {col: False for col in CHECKBOX_COLUMNS},
                "Chemistry 2nd: Chapter 4: তড়িৎ রসায়ন": {col: False for col in CHECKBOX_COLUMNS},
                "Chemistry 2nd: Chapter 5: অর্থনৈতিক রসায়ন": {col: False for col in CHECKBOX_COLUMNS}
            }
        },
        "Higher Math (1st & 2nd Paper)": {
            "Chapters": {
                "Higher Math 1st: Chapter 1: ম্যাট্রিক্স ও নির্ণায়ক": {col: False for col in MATH_COLUMNS},
                "Higher Math 1st: Chapter 2: ভেক্টর": {col: False for col in MATH_COLUMNS},
                "Higher Math 1st: Chapter 3: সরলরেখা": {col: False for col in MATH_COLUMNS},
                "Higher Math 1st: Chapter 4: বৃত্ত": {col: False for col in MATH_COLUMNS},
                "Higher Math 1st: Chapter 5: বিন্যাস ও সমাবেশ": {col: False for col in MATH_COLUMNS},
                "Higher Math 1st: Chapter 9: অন্তরীকরণ": {col: False for col in MATH_COLUMNS},
                "Higher Math 1st: Chapter 10: যোগজীকরণ": {col: False for col in MATH_COLUMNS},
                "Higher Math 2nd: Chapter 3: জটিল সংখ্যা": {col: False for col in MATH_COLUMNS},
                "Higher Math 2nd: Chapter 4: বহুপদী ও বহুপদী সমীকরণ": {col: False for col in MATH_COLUMNS},
                "Higher Math 2nd: Chapter 5: দ্বিপদী বিস্তৃতি": {col: False for col in MATH_COLUMNS},
                "Higher Math 2nd: Chapter 6: কণিক": {col: False for col in MATH_COLUMNS}
            }
        },
        "Biology (1st & 2nd Paper)": {
            "Chapters": {
                "Biology 1st: Chapter 1: কোষ ও এর গঠন": {col: False for col in BIOLOGY_COLUMNS},
                "Biology 1st: Chapter 2: কোষ বিভাজন": {col: False for col in BIOLOGY_COLUMNS},
                "Biology 1st: Chapter 3: কোষ রসায়ন": {col: False for col in BIOLOGY_COLUMNS},
                "Biology 1st: Chapter 4: অনুজীব": {col: False for col in BIOLOGY_COLUMNS},
                "Biology 1st: Chapter 9: উদ্ভিদ শারীরতত্ত্ব": {col: False for col in BIOLOGY_COLUMNS},
                "Biology 2nd: Chapter 1: প্রাণীর বিভিন্নতা ও শ্রেণিন্যাস": {col: False for col in BIOLOGY_COLUMNS},
                "Biology 2nd: Chapter 3: পরিপাক ও শোষণ": {col: False for col in BIOLOGY_COLUMNS},
                "Biology 2nd: Chapter 4: রক্ত ও রক্তসংবহন": {col: False for col in BIOLOGY_COLUMNS},
                "Biology 2nd: Chapter 8: মানব শারীরতত্ত্ব: সমন্বয় ও নিয়ন্ত্রণ": {col: False for col in BIOLOGY_COLUMNS},
                "Biology 2nd: Chapter 11: জিনতত্ত্ব ও বিবর্তন": {col: False for col in BIOLOGY_COLUMNS}
            }
        }
    }

    def get_subject_cols(sub_name):
        if "Biology" in sub_name:
            return BIOLOGY_COLUMNS
        elif "Higher Math" in sub_name:
            return MATH_COLUMNS
        return CHECKBOX_COLUMNS

    saved_syllabus = load_data(SYLLABUS_FILE, {})
    if not saved_syllabus or "Physics (1st & 2nd Paper)" not in saved_syllabus:
        st.session_state.syllabus = HSC_DEFAULT_SYLLABUS
        save_data(SYLLABUS_FILE, HSC_DEFAULT_SYLLABUS)
    else:
        for sub, content in HSC_DEFAULT_SYLLABUS.items():
            if sub not in saved_syllabus:
                saved_syllabus[sub] = {"Chapters": {}}
            target_cols = get_subject_cols(sub)
            for ch, pillars in content["Chapters"].items():
                if ch not in saved_syllabus[sub]["Chapters"]:
                    saved_syllabus[sub]["Chapters"][ch] = pillars
                else:
                    for p in target_cols:
                        if p not in saved_syllabus[sub]["Chapters"][ch]:
                            saved_syllabus[sub]["Chapters"][ch][p] = False
        st.session_state.syllabus = saved_syllabus
        save_data(SYLLABUS_FILE, saved_syllabus)

    if "timer_logs" not in st.session_state:
        st.session_state.timer_logs = load_data(TIMER_FILE, [])
    if "active_focus_task" not in st.session_state:
        st.session_state.active_focus_task = None
    if "is_focus_running" not in st.session_state:
        st.session_state.is_focus_running = False

    DAYS_OF_WEEK = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    # Bangladesh Timezone (UTC +6)
    bd_tz = timezone(timedelta(hours=6))
    now_bd = datetime.now(bd_tz)

    current_day_name = now_bd.strftime('%A')
    today_date_str = now_bd.strftime('%Y-%m-%d')
    formatted_display_date = now_bd.strftime('%d %B %Y')

    # Calculate Dynamic Countdown based on Target Date
    target_exam_date = datetime(2026, 12, 1, tzinfo=bd_tz)
    remaining_days = (target_exam_date - now_bd).days
    if remaining_days < 0:
        remaining_days = 0

    # Sidebar Navigation Control
    st.sidebar.title(f"⚡ Welcome, {name}")
    authenticator.logout('Logout', 'sidebar')
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Navigation**")

    page_selection = [
        "🏠 Dashboard & Focus Station", 
        "📖 Syllabus Tracker", 
        "🎓 ভর্তি পরীক্ষার তারিখ",
        "📄 PDF Tool", 
        "🎵 গানের জগত"
    ]

    def handle_nav_change():
        if st.session_state.is_focus_running:
            st.sidebar.error("⚠️ Be Consistent and Determined!")
            time.sleep(1.2)

    if "page" not in st.session_state:
        st.session_state.page = "🏠 Dashboard & Focus Station"

    page_index_map = {page_selection[i]: i for i in range(len(page_selection))}
    current_index = page_index_map.get(st.session_state.page, 0)

    sidebar_selection = st.sidebar.radio(
        "Go to", 
        page_selection, 
        index=current_index, 
        on_change=handle_nav_change,
        key="sidebar_radio"
    )

    if sidebar_selection != st.session_state.page and not st.session_state.is_focus_running:
        st.session_state.page = sidebar_selection

    # ----------------------------------------------------
    # PAGE 1: DASHBOARD & FOCUS STATION
    # ----------------------------------------------------
    if st.session_state.page == "🏠 Dashboard & Focus Station":
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                <a href="#target-tracker" style="text-decoration: none; font-size: 32px; line-height: 1; cursor: pointer;" title="">⚡</a>
                <h1 style="margin: 0; font-size: 2.25rem; font-weight: 700; color: #FFFFFF;">{remaining_days} days ahead (Consistent, Determined, Hardwork)</h1>
            </div>
        """, unsafe_allow_html=True)

        left_col, right_col = st.columns([1.8, 1.4])
        
        with left_col:
            st.markdown(f"### 🌞 {formatted_display_date} | {current_day_name}")
            todays_tasks = [t for t in st.session_state.tasks if t.get('assigned_day') == current_day_name and not t.get('done', False)]
            
            if not todays_tasks:
                st.info(f"No active tasks assigned for {current_day_name}. Pick tasks from your Weekly Vault below!")
            else:
                for task in todays_tasks:
                    d_col1, d_col2, d_col3 = st.columns([0.2, 2, 1])
                    with d_col1:
                        is_chk = st.checkbox("", value=False, key=f"daily_chk_{task['id']}")
                        if is_chk:
                            for t in st.session_state.tasks:
                                if t['id'] == task['id']:
                                    t['done'] = True
                            save_data(TASKS_FILE, st.session_state.tasks)
                            st.toast("🎉 Great job! Task completed.")
                            time.sleep(0.5)
                            st.rerun()
                    with d_col2:
                        st.write(task['title'])
                    with d_col3:
                        if not st.session_state.is_focus_running:
                            if st.button("🎯 Focus Now", key=f"f_now_{task['id']}"):
                                st.session_state.active_focus_task = task
                                st.session_state.is_focus_running = True
                                st.rerun()
                        else:
                            st.write("🔒 Locked")
                            
            st.write("---")
            
            col_title, col_btn = st.columns([2, 1])
            with col_title:
                st.markdown("#### 📋 Weekly Task Management")
            with col_btn:
                if st.session_state.tasks:
                    if st.button("🧹 Clear All Tasks"):
                        st.session_state.tasks = []
                        save_data(TASKS_FILE, st.session_state.tasks)
                        st.success("All tasks cleared!")
                        st.rerun()

            if not st.session_state.tasks:
                st.info("Vault is empty. Add tasks below.")
            else:
                for idx, task in enumerate(st.session_state.tasks):
                    t_col1, t_col2, t_col3 = st.columns([2.2, 1.3, 0.9])
                    with t_col1:
                        if task.get('done', False):
                            st.markdown(f"✅ ~~{task['title']}~~")
                        else:
                            st.markdown(f"📌 **{task['title']}** " + (f"<span style='font-size:0.75rem; color:gray;'>({task.get('assigned_day')})</span>" if task.get('assigned_day', 'None') != "None" else ""), unsafe_allow_html=True)
                    with t_col2:
                        current_days_list = ["None"] + DAYS_OF_WEEK
                        try:
                            current_day_idx = current_days_list.index(task.get('assigned_day', 'None'))
                        except ValueError:
                            current_day_idx = 0
                        selected_day = st.selectbox("Day", current_days_list, key=f"day_pick_{task['id']}", index=current_day_idx, label_visibility="collapsed")
                        if selected_day != task.get('assigned_day', 'None'):
                            task['assigned_day'] = selected_day
                            save_data(TASKS_FILE, st.session_state.tasks)
                            st.rerun()
                    with t_col3:
                        if st.button("🗑️", key=f"del_task_{task['id']}", help="Delete Task"):
                            st.session_state.tasks = [t for t in st.session_state.tasks if t['id'] != task['id']]
                            save_data(TASKS_FILE, st.session_state.tasks)
                            st.rerun()
                    st.markdown("<div style='margin: -10px 0;'></div>", unsafe_allow_html=True)
                            
            st.write("---")
            st.markdown("### 📅 Add Task to Weekly Vault")
            with st.form("weekly_add_form", clear_on_submit=True):
                w_title = st.text_input("New Task Title:")
                submit_w = st.form_submit_button("➕ Save into Vault")
                if submit_w and w_title:
                    new_t = {
                        "id": str(int(time.time() * 1000)),
                        "title": w_title,
                        "assigned_day": "None",
                        "done": False,
                        "hours_done": 0.0
                    }
                    st.session_state.tasks.append(new_t)
                    save_data(TASKS_FILE, st.session_state.tasks)
                    st.success("Task added successfully!")
                    st.rerun()

        with right_col:
            st.markdown("### ⏱️ Focus Arena & Live Timer")
            if st.session_state.active_focus_task:
                active_task = st.session_state.active_focus_task
                st.success(f"Focused Task: {active_task['title']}")
                st.info("🔥 Fixed 25-Minute Focus Session in Progress. Stay locked in!")
                
                timer_visual = st.empty()
                bar = st.progress(0)
                total_seconds = 25 * 60
                study_seconds = 0
                
                for s in range(total_seconds):
                    time.sleep(1)
                    study_seconds += 1
                    remaining = total_seconds - study_seconds
                    mins, secs = divmod(remaining, 60)
                    timer_visual.markdown(f"### ⏱️ {mins:02d}:{secs:02d}", unsafe_allow_html=True)
                    bar.progress(int((study_seconds / total_seconds) * 100))
                
                final_hrs = round(study_seconds / 3600, 2)
                for t in st.session_state.tasks:
                    if t['id'] == active_task['id']:
                        t['hours_done'] += final_hrs
                save_data(TASKS_FILE, st.session_state.tasks)
                st.session_state.timer_logs.append({
                    "date": formatted_display_date,
                    "task_title": active_task['title'],
                    "hours_focused": final_hrs
                })
                save_data(TIMER_FILE, st.session_state.timer_logs)
                st.session_state.is_focus_running = False
                st.session_state.active_focus_task = None
                st.balloons()
                st.rerun()
            else:
                st.info("💡 Click 'Focus Now' next to any task in your Daily Planner to begin your 25-minute session instantly.")

            st.markdown("<hr style='border: 1px solid #ccc; margin: 20px 0;'>", unsafe_allow_html=True)
            st.markdown('<div id="target-tracker"></div>', unsafe_allow_html=True)

            st.markdown(f"### 🎯 Daily Sessions (90-Minute Target Tracker)")
            st.markdown(f"**Day:** {current_day_name} | **Date:** {formatted_display_date}")
            st.caption("প্রতিটি সেশন ৯০ মিনিটের। আপনার পড়ার লক্ষ্য অনুযায়ী নিচে টিক দিন:")

            if today_date_str not in st.session_state.daily_sessions:
                st.session_state.daily_sessions[today_date_str] = {
                    "day_name": current_day_name,
                    "display_date": formatted_display_date,
                    "sessions": {f"90_{i}": False for i in range(1, 11)}
                }
                save_data(DAILY_SESSIONS_FILE, st.session_state.daily_sessions)
            else:
                st.session_state.daily_sessions[today_date_str]["day_name"] = current_day_name
                st.session_state.daily_sessions[today_date_str]["display_date"] = formatted_display_date

            current_day_data = st.session_state.daily_sessions[today_date_str]
            
            cols_chk = st.columns(2)
            session_keys = list(current_day_data["sessions"].keys())
            
            for i, s_key in enumerate(session_keys):
                col_idx = i % 2
                with cols_chk[col_idx]:
                    val = current_day_data["sessions"][s_key]
                    new_val = st.checkbox("90", value=val, key=f"ds_{today_date_str}_{i}")
                    if new_val != val:
                        current_day_data["sessions"][s_key] = new_val
                        save_data(DAILY_SESSIONS_FILE, st.session_state.daily_sessions)
                        st.rerun()

            completed_count = sum(1 for v in current_day_data["sessions"].values() if v)
            total_minutes_today = completed_count * 90
            st.markdown(f"💡 **আজকের মোট পড়া হয়েছে:** `{total_minutes_today} মিনিট`")

            st.markdown("<hr style='border: 1px solid #ccc; margin: 20px 0;'>", unsafe_allow_html=True)

            st.markdown("#### 📥 Study History PDF Report")
            if REPORTLAB_AVAILABLE:
                def generate_history_pdf(sessions_data):
                    buffer = BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
                    story = []
                    styles = getSampleStyleSheet()
                    
                    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#FF4B4B'), spaceAfter=15, alignment=1)
                    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#222222'))
                    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=11, leading=14, fontName='Helvetica-Bold', textColor=colors.whitesmoke)
                    
                    story.append(Paragraph(f"Daily Study History Report", title_style))
                    story.append(Spacer(1, 10))
                    
                    table_content = [[Paragraph("Date", header_style), Paragraph("Day", header_style), Paragraph("Completed 90m Sessions", header_style), Paragraph("Total Minutes", header_style)]]
                    
                    for d_str, d_info in sorted(sessions_data.items(), reverse=True):
                        comp_s = sum(1 for v in d_info.get("sessions", {}).values() if v)
                        t_mins = comp_s * 90
                        
                        d_para = Paragraph(str(d_info.get("display_date", d_str)), cell_style)
                        day_para = Paragraph(str(d_info.get("day_name", "")), cell_style)
                        s_para = Paragraph(f"{comp_s} Sessions", cell_style)
                        m_para = Paragraph(f"{t_mins} mins", cell_style)
                        table_content.append([d_para, day_para, s_para, m_para])
                        
                    pdf_table = Table(table_content, colWidths=[130, 110, 150, 110])
                    pdf_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E2E2E')),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9F9F9')),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                        ('TOPPADDING', (0, 1), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                    ]))
                    story.append(pdf_table)
                    doc.build(story)
                    buffer.seek(0)
                    return buffer.getvalue()

                hist_pdf_bytes = generate_history_pdf(st.session_state.daily_sessions)
                st.download_button(
                    label="📥 Download Study History PDF",
                    data=hist_pdf_bytes,
                    file_name="study_history_report.pdf",
                    mime="application/pdf",
                    key="dl_history_pdf"
                )
            else:
                st.warning("ReportLab library is not installed.")

    # ----------------------------------------------------
    # PAGE 2: SYLLABUS TRACKER
    # ----------------------------------------------------
    elif st.session_state.page == "📖 Syllabus Tracker":
        if st.session_state.is_focus_running:
            st.error("⚠️ Focus session is currently active! Be Consistent and Determined! Complete your session first.")
        else:
            st.title("📖 Subject & Chapter Syllabus Tracker")
            st.info("⚡ Track your chapter progress below and generate custom subject-wise PDF performance reports instantly.")
            st.write("---")
            st.subheader("📚 Chapter Progress Checklist")
            
            for sub, content in st.session_state.syllabus.items():
                with st.expander(f"📘 {sub}", expanded=False):
                    if "Chapters" in content and content["Chapters"]:
                        target_cols = get_subject_cols(sub)
                        for ch, parts in content["Chapters"].items():
                            st.markdown(f"📍 **{ch}**")
                            cols = st.columns(len(target_cols))
                            for col_idx, col_name in enumerate(target_cols):
                                with cols[col_idx]:
                                    val = parts.get(col_name, False)
                                    chk_val = st.checkbox(col_name, value=val, key=f"chk_{sub}_{ch}_{col_name}")
                                    if chk_val != val:
                                        st.session_state.syllabus[sub]["Chapters"][ch][col_name] = chk_val
                                        save_data(SYLLABUS_FILE, st.session_state.syllabus)
                                        st.rerun()
                            st.markdown("---")
                    else:
                        st.info("No chapters mapped.")

            st.write("---")
            st.subheader("📊 Subject Progress & PDF Reports")
            
            subject_names = list(st.session_state.syllabus.keys())
            tabs = st.tabs([f"📘 {s.split(' ')[0]}" for s in subject_names])
            
            for idx, sub_name in enumerate(subject_names):
                with tabs[idx]:
                    st.markdown(f"#### 📑 {sub_name} Progress Report")
                    content = st.session_state.syllabus[sub_name]
                    chapters = content.get("Chapters", {})
                    target_cols = get_subject_cols(sub_name)
                    total_pillars = len(target_cols)
                    
                    sub_report_data = []
                    for ch, parts in chapters.items():
                        completed_pillars = [col for col in target_cols if parts.get(col, False)]
                        if completed_pillars:
                            done_count = len(completed_pillars)
                            percentage = int((done_count / total_pillars) * 100)
                            sub_report_data.append({
                                "Chapter Name": ch,
                                "Completed Progress Metrics": ", ".join(completed_pillars),
                                "Progress (%)": f"{percentage}%"
                            })
                            
                    if sub_report_data:
                        df_sub = pd.DataFrame(sub_report_data)
                        st.dataframe(df_sub, use_container_width=True)
                        
                        if REPORTLAB_AVAILABLE:
                            def generate_subject_pdf(subject_title, dataframe):
                                buffer = BytesIO()
                                doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
                                story = []
                                styles = getSampleStyleSheet()
                                
                                title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#FF4B4B'), spaceAfter=15, alignment=1)
                                cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#222222'))
                                header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=10, leading=13, fontName='Helvetica-Bold', textColor=colors.whitesmoke)
                                
                                story.append(Paragraph(f"Progress Report: {subject_title}", title_style))
                                story.append(Spacer(1, 10))
                                
                                table_content = [[Paragraph("Chapter Name", header_style), Paragraph("Completed Progress Metrics", header_style), Paragraph("Progress (%)", header_style)]]
                                for _, row in dataframe.iterrows():
                                    raw_ch = str(row['Chapter Name'])
                                    parts_list = raw_ch.split(':')
                                    if len(parts_list) >= 2:
                                        clean_ch = f"{parts_list[0].strip()}: {parts_list[1].strip()}"
                                    else:
                                        clean_ch = "".join([c if ord(c) < 128 else "" for c in raw_ch]).strip()
                                        
                                    c_para = Paragraph(clean_ch, cell_style)
                                    m_para = Paragraph(str(row['Completed Progress Metrics']), cell_style)
                                    p_para = Paragraph(str(row['Progress (%)']), cell_style)
                                    table_content.append([c_para, m_para, p_para])
                                    
                                pdf_table = Table(table_content, colWidths=[200, 240, 100])
                                pdf_table.setStyle(TableStyle([
                                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E2E2E')),
                                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9F9F9')),
                                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                                    ('TOPPADDING', (0, 1), (-1, -1), 6),
                                    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                                ]))
                                story.append(pdf_table)
                                doc.build(story)
                                buffer.seek(0)
                                return buffer.getvalue()
                                
                            pdf_bytes = generate_subject_pdf(sub_name, df_sub)
                            file_safe_name = sub_name.split(' ')[0].lower()
                            st.download_button(
                                label=f"📥 Download {sub_name.split(' ')[0]} PDF Report",
                                data=pdf_bytes,
                                file_name=f"{file_safe_name}_progress_report.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_{sub_name}"
                            )
                        else:
                            st.warning("ReportLab library is not installed, PDF generation is disabled.")
                    else:
                        st.info(f"No chapters completed yet for '{sub_name}'. Check off items above to generate your report and PDF.")

    # ----------------------------------------------------
    # PAGE 3: ADMISSION EXAM DATES TRACKER
    # ----------------------------------------------------
    elif st.session_state.page == "🎓 ভর্তি পরীক্ষার তারিখ":
        if st.session_state.is_focus_running:
            st.error("⚠️ Focus session is currently active! Be Consistent and Determined! Complete your session first.")
        else:
            st.title("🎓 ভর্তি পরীক্ষার তারিখ ও শিডিউল")
            st.write("---")

            st.markdown("#### 📋 সংরক্ষিত ভর্তি পরীক্ষার তালিকা")

            if not st.session_state.admission_exams:
                st.info("এখনো কোনো বিশ্ববিদ্যালয়ের তথ্য যোগ করা হয়নি। নিচে ফর্ম থেকে তথ্য যুক্ত করুন।")
            else:
                for ex in st.session_state.admission_exams:
                    e_c1, e_c2, e_c3, e_c4, e_c5 = st.columns([2, 1.5, 1.5, 1.5, 0.6])
                    with e_c1:
                        st.markdown(f"🏛️ **{ex['University Name']}**")
                    with e_c2:
                        st.caption(f"📝 Exam: {ex['Exam date']}")
                    with e_c3:
                        st.caption(f"🚀 Start: {ex['1st date']}")
                    with e_c4:
                        st.caption(f"⏳ Last: {ex['Last Date']}")
                    with e_c5:
                        if st.button("🗑️", key=f"del_ex_{ex['id']}", help="ডিলিট করুন"):
                            st.session_state.admission_exams = [item for item in st.session_state.admission_exams if item['id'] != ex['id']]
                            save_data(EXAMS_FILE, st.session_state.admission_exams)
                            st.rerun()
                    st.markdown("<div style='margin: -5px 0;'></div>", unsafe_allow_html=True)

                st.write("")
                if REPORTLAB_AVAILABLE:
                    def generate_admission_pdf(exams_list):
                        buffer = BytesIO()
                        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
                        story = []
                        styles = getSampleStyleSheet()
                        
                        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#FF4B4B'), spaceAfter=15, alignment=1)
                        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#222222'))
                        header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=10, leading=13, fontName='Helvetica-Bold', textColor=colors.whitesmoke)
                        
                        story.append(Paragraph("Admission Exam Schedule Report", title_style))
                        story.append(Spacer(1, 10))
                        
                        table_content = [[Paragraph("University Name", header_style), Paragraph("Exam Date", header_style), Paragraph("1st Date (Start)", header_style), Paragraph("Last Date (Deadline)", header_style)]]
                        for ex in exams_list:
                            u_para = Paragraph(str(ex['University Name']), cell_style)
                            e_para = Paragraph(str(ex['Exam date']), cell_style)
                            f_para = Paragraph(str(ex['1st date']), cell_style)
                            l_para = Paragraph(str(ex['Last Date']), cell_style)
                            table_content.append([u_para, e_para, f_para, l_para])
                            
                        pdf_table = Table(table_content, colWidths=[150, 110, 120, 120])
                        pdf_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E2E2E')),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                            ('TOPPADDING', (0, 0), (-1, 0), 8),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9F9F9')),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                            ('TOPPADDING', (0, 1), (-1, -1), 6),
                            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                        ]))
                        story.append(pdf_table)
                        doc.build(story)
                        buffer.seek(0)
                        return buffer.getvalue()

                    admission_pdf_bytes = generate_admission_pdf(st.session_state.admission_exams)
                    st.download_button(
                        label="📥 Download Admission Schedule PDF",
                        data=admission_pdf_bytes,
                        file_name="admission_schedule.pdf",
                        mime="application/pdf",
                        key="dl_admission_pdf"
                    )

            st.write("---")

            with st.form("admission_exam_form", clear_on_submit=True):
                st.markdown("#### ➕ নতুন ভর্তি পরীক্ষার তথ্য যোগ করুন")
                f_col1, f_col2 = st.columns(2)
                with f_col1:
                    uni_name_input = st.text_input("University Name (যেমন: Dhaka University / BUET)")
                    exam_date_input = st.date_input("Exam Date", value=now_bd.date(), min_value=datetime(2026, 1, 1).date(), max_value=datetime(2027, 12, 31).date())
                with f_col2:
                    first_date_input = st.date_input("1st Date (Application Start)", value=now_bd.date(), min_value=datetime(2026, 1, 1).date(), max_value=datetime(2027, 12, 31).date())
                    last_date_input = st.date_input("Last Date (Application Deadline)", value=now_bd.date(), min_value=datetime(2026, 1, 1).date(), max_value=datetime(2027, 12, 31).date())
                
                submit_exam = st.form_submit_button("💾 সেভ করুন")
                if submit_exam:
                    if uni_name_input:
                        new_exam_entry = {
                            "id": str(int(time.time() * 1000)),
                            "University Name": uni_name_input,
                            "Exam date": exam_date_input.strftime("%d %B, %Y"),
                            "1st date": first_date_input.strftime("%d %B, %Y"),
                            "Last Date": last_date_input.strftime("%d %B, %Y")
                        }
                        st.session_state.admission_exams.append(new_exam_entry)
                        save_data(EXAMS_FILE, st.session_state.admission_exams)
                        st.success("সফলভাবে ভর্তি পরীক্ষার তথ্য সংরক্ষণ করা হয়েছে!")
                        st.rerun()
                    else:
                        st.warning("দয়া করে অন্তত University Name লিখুন।")

    # ----------------------------------------------------
    # PAGE 4: PDF TOOL
    # ----------------------------------------------------
    elif st.session_state.page == "📄 PDF Tool":
        if st.session_state.is_focus_running:
            st.error("⚠️ Focus session is currently active! Be Consistent and Determined! Complete your session first.")
        else:
            st.markdown("<h2 style='text-align: center; color: #4CAF50;'>👨‍💻 Personal Workspace</h2>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align: center; color: #888888;'>🤖 ২-ইন-১ পিডিএফ অটো-লেআউট টুল (নিখুঁত রেশিও)</h3>", unsafe_allow_html=True)
            st.write("---")
            st.write("ফাইল আপলোড করুন; ল্যান্ডস্কেপ স্লাইডগুলো কোনো বর্ডার বা কাটিং ছাড়াই ১টি পেজে ৩টি করে নিখুঁতভাবে বসে যাবে।")

            uploaded_files = st.file_uploader("আপনার পিডিএফ ফাইলগুলো এখানে সিলেক্ট করুন", type=["pdf"], accept_multiple_files=True, key="pdf_tool_uploader")

            if uploaded_files:
                if st.button("🔄 প্রসেসিং শুরু করুন", key="pdf_process_btn"):
                    with st.spinner("কাজ চলছে... নিখুঁত রেশিওতে লেআউট তৈরি হচ্ছে..."):
                        try:
                            merged_writer = PdfWriter()
                            for uploaded_file in uploaded_files:
                                reader = PdfReader(uploaded_file)
                                for page_obj in reader.pages:
                                    merged_writer.add_page(page_obj)
                            
                            temp_merged = "temp_merged.pdf"
                            with open(temp_merged, "wb") as f:
                                merged_writer.write(f)
                            
                            output_pdf = "processed_output.pdf"
                            final_writer = PdfWriter()
                            reader = PdfReader(temp_merged)
                            total_pages = len(reader.pages)
                            
                            for i in range(0, total_pages, 3):
                                first_page = reader.pages[i]
                                orig_w = float(first_page.mediabox.width)
                                orig_h = float(first_page.mediabox.height)
                                
                                new_w = orig_w
                                new_h = orig_h * 3
                                
                                new_page = final_writer.add_blank_page(width=new_w, height=new_h)
                                
                                for j in range(3):
                                    if i + j < total_pages:
                                        current_slide = reader.pages[i + j]
                                        ty = (2 - j) * orig_h
                                        new_page.merge_translated_page(current_slide, tx=0, ty=ty)
                            
                            with open(output_pdf, "wb") as f:
                                final_writer.write(f)
                            
                            if os.path.exists(temp_merged):
                                os.remove(temp_merged)
                                
                            st.success("🎉 আপনার নিখুঁত ফুল-স্ক্রিন ফাইলটি তৈরি হয়েছে!")
                            with open(output_pdf, "rb") as f:
                                st.download_button(
                                    label="📥 প্রসেসড পিডিএফ ডাউনলোড করুন",
                                    data=f,
                                    file_name="final_output.pdf",
                                    mime="application/pdf",
                                    key="pdf_download_btn"
                                )
                        except Exception as e:
                            st.error(f"দুঃখিত, একটি সমস্যা হয়েছে: {e}")

    # ----------------------------------------------------
    # PAGE 5: GANER JOGOT
    # ----------------------------------------------------
    elif st.session_state.page == "🎵 গানের জগত":
        if st.session_state.is_focus_running:
            st.error("⚠️ Focus session is currently active! Complete your session first.")
        else:
            st.title("🎵 গানের জগত")
            st.info("তোমার পছন্দের গানগুলো নিচে সরাসরি প্লেয়ারে শুনতে পারো:")
            st.write("---")
            
            for idx, song_url in enumerate(st.session_state.my_songs, 1):
                sc1, sc2 = st.columns([5, 1])
                with sc1:
                    st.markdown(f"#### গান #{idx}")
                    try:
                        st.video(song_url)
                    except Exception as e:
                        st.error(f"গান লোড করতে সমস্যা হয়েছে: {e}")
                with sc2:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ মুছুন", key=f"del_song_{idx}"):
                        st.session_state.my_songs.pop(idx - 1)
                        save_data(SONGS_FILE, st.session_state.my_songs)
                        st.rerun()
                st.markdown("---")

            st.markdown("#### ➕ নতুন গান যোগ করুন")
            with st.form("add_song_form", clear_on_submit=True):
                new_song_link = st.text_input("YouTube Song Link (যেমন: https://youtu.be/...)")
                submit_song = st.form_submit_button("💾 গান সেভ করুন")
                if submit_song:
                    if new_song_link:
                        st.session_state.my_songs.append(new_song_link)
                        save_data(SONGS_FILE, st.session_state.my_songs)
                        st.success("নতুন গান সফলভাবে যোগ করা হয়েছে!")
                        st.rerun()
                    else:
                        st.warning("দয়া করে একটি সঠিক ইউটিউব লিংক দিন।")

    # Footer & Navigation buttons for main pages
    if st.session_state.page in ["🏠 Dashboard & Focus Station", "📖 Syllabus Tracker", "🎓 ভর্তি পরীক্ষার তারিখ", "📄 PDF Tool"]:
        st.markdown("<br><hr style='border: 1px solid #ddd;'>", unsafe_allow_html=True)
        c_space1, c_btn1, c_btn2, c_space2 = st.columns([1, 1, 1, 1])
        with c_btn1:
            if st.button("🏠 Dashboard"):
                st.session_state.page = "🏠 Dashboard & Focus Station"
                st.rerun()
        with c_btn2:
            if st.button("📖 Syllabus Tracker"):
                st.session_state.page = "📖 Syllabus Tracker"
                st.rerun()
        
        st.markdown("<p style='text-align: center; color: gray; font-size: 0.85rem; margin-top: 15px;'>copyright@portal</p>", unsafe_allow_html=True)
