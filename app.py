import json
import os
import streamlit as st
import pandas as pd

# ডেটা সেভ করার জন্য ফাইলের নাম
DATA_FILE = "admission_schedule.json"

# ডিফল্ট ডাটা বা ছবি অনুযায়ী ডাটাগুলো লোড করা
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    # ছবি থেকে প্রাপ্ত ডিফল্ট শিডিউল ডাটা
    return [
        {
            "University Name": "DU",
            "Exam Date": "12 December, 2026",
            "1st Date (Start)": "11 November, 2026",
            "Last Date (Deadline)": "25 November, 2026"
        },
        {
            "University Name": "KUET",
            "Exam Date": "07 January, 2027",
            "1st Date (Start)": "05 September, 2026",
            "Last Date (Deadline)": "05 September, 2026"
        },
        {
            "University Name": "SUST",
            "Exam Date": "26 January, 2027",
            "1st Date (Start)": "05 September, 2026",
            "Last Date (Deadline)": "05 September, 2026"
        },
        {
            "University Name": "MIST",
            "Exam Date": "18 December, 2026",
            "1st Date (Start)": "05 September, 2026",
            "Last Date (Deadline)": "05 September, 2026"
        },
        {
            "University Name": "KU",
            "Exam Date": "18 December, 2026",
            "1st Date (Start)": "05 September, 2026",
            "Last Date (Deadline)": "05 September, 2026"
        },
        {
            "University Name": "Jagannath",
            "Exam Date": "01 January, 2027",
            "1st Date (Start)": "15 November, 2026",
            "Last Date (Deadline)": "10 September, 2026"
        },
        {
            "University Name": "Chattogram Uni",
            "Exam Date": "30 January, 2027",
            "1st Date (Start)": "15 November, 2026",
            "Last Date (Deadline)": "10 December, 2026"
        },
        {
            "University Name": "RAJSHAHI",
            "Exam Date": "09 January, 2027",
            "1st Date (Start)": "12 November, 2026",
            "Last Date (Deadline)": "27 November, 2026"
        },
        {
            "University Name": "BUP",
            "Exam Date": "08 January, 2026",
            "1st Date (Start)": "05 September, 2026",
            "Last Date (Deadline)": "05 September, 2026"
        }
    ]

# ডাটা সেভ করার ফাংশন
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

st.set_page_config(page_title="Muhit's HSC Tracker & Workspace", layout="wide")

st.title("🎓 Admission Exam Schedule Report - Muhit")

# সেশন স্টেটে ডেটা ইনিশিয়ালাইজ করা এবং অটো-লোড করা
if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = load_data()

st.subheader("📋 University Admission Schedule List")

# ডাটা টেবিল আকারে প্রদর্শন
df = pd.DataFrame(st.session_state.schedule_data)
st.dataframe(df, use_container_width=True)

st.markdown("---")
st.subheader("➕ Add New Admission Schedule")

# নতুন ডাটা যোগ করার ফর্ম
with st.form("add_schedule_form"):
    col1, col2 = st.columns(2)
    with col1:
        uni_name = st.text_input("University Name")
        exam_date = st.text_input("Exam Date (e.g., 12 December, 2026)")
    with col2:
        start_date = st.text_input("1st Date (Start)")
        last_date = st.text_input("Last Date (Deadline)")
    
    submitted = st.form_submit_button("Add Schedule")
    
    if submitted:
        if uni_name:
            new_entry = {
                "University Name": uni_name,
                "Exam Date": exam_date,
                "1st Date (Start)": start_date,
                "Last Date (Deadline)": last_date
            }
            # লিস্টে নতুন ডাটা যোগ করা
            st.session_state.schedule_data.append(new_entry)
            # অটো JSON ফাইলে সেভ করা যাতে ডাটা হারিয়ে না যায়
            save_data(st.session_state.schedule_data)
            st.success(f"Successfully added schedule for {uni_name}!")
            st.rerun()
        else:
            st.error("Please enter at least the University Name.")

# ডেটা রিসেট বা ক্লিয়ার করার অপশন (প্রয়োজন হলে)
if st.button("Reset to Default Schedule"):
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.session_state.schedule_data = load_data()
    st.success("Reset to original schedule successfully!")
    st.rerun()
