import streamlit as st
import re
from datetime import datetime, time
from urllib.parse import quote
from pypdf import PdfReader

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="centered")

st.title("📅 Event Text & PDF Parser")
st.markdown("Smart extraction maps specific details to the correct calendar fields.")

# --- STEP 1: INPUT & EXTRACTION ---
input_method = st.radio("Select Input Method:", ["Upload PDF File", "Paste Text Manually"])
extracted_text = ""

if input_method == "Upload PDF File":
    uploaded_file = st.file_uploader("Upload Event PDF:", type=["pdf"])
    if uploaded_file is not None:
        try:
            reader = PdfReader(uploaded_file)
            raw_pdf_text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    raw_pdf_text += page_text + "\n"
            
            filtered_lines = [
                line.strip() for line in raw_pdf_text.split('\n') 
                if line.strip() and not any(noise in line.lower() for noise in ["http://", "https://", "page ", "mail.google.com"])
                and not re.match(r'^\d{1,2}/\d{1,2}/\d{2},?\s*\d{1,2}:\d{2}', line.strip())
            ]
            extracted_text = "\n".join(filtered_lines)
            st.success("Successfully extracted and cleaned text from PDF!")
        except Exception as e:
            st.error(f"Error reading PDF file: {str(e)}")

raw_text = st.text_area(
    "Event Details:", 
    height=150, 
    value=extracted_text if extracted_text else "",
    placeholder="Paste event text here or upload a PDF above..."
)

# --- SMART FILTERING LOGIC ---
all_lines = ["[Manual Entry]"]
title_candidates = ["[Manual Entry]"]
date_candidates = ["[Manual Entry]"]
time_candidates = ["[Manual Entry]"]
loc_candidates = ["[Manual Entry]"]

if raw_text.strip():
    extracted_lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    all_lines.extend(extracted_lines)
    
    for line in extracted_lines:
        lower_line = line.lower()
        
        # 1. Date Filter (Months, Days of week)
        if re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|aug|sep|oct|nov|dec|monday|tuesday|wednesday|thursday|friday|saturday|sunday)', lower_line):
            date_candidates.append(line)
            
        # 2. Time Filter (AM/PM or formatted time)
        if re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', lower_line):
            time_candidates.append(line)
            
        # 3. Location Filter (Addresses, Location labels, Campus)
        if re.search(r'(location:|street|st|ave|avenue|blvd|campus|new york|ny|room)', lower_line) or re.search(r'\d+\s+[a-z]+', lower_line):
            loc_candidates.append(line)
            
        # 4. Title Filter (Keep it relatively short, ignore obvious URLs or purely numbers)
        if len(line.split()) < 15 and not line.startswith("http"):
            title_candidates.append(line)

# Fallbacks: If a smart filter found nothing, give it all the lines just in case
if len(date_candidates) == 1: date_candidates = all_lines
if len(time_candidates) == 1: time_candidates = all_lines
if len(loc_candidates) == 1: loc_candidates = all_lines
if len(title_candidates) == 1: title_candidates = all_lines


st.markdown("---")
st.markdown("### 📝 Verify & Edit Details")

with st.form("event_mapping_form"): 
    
    # --- TITLE ---
    st.subheader("Event Title")
    title_selection = st.selectbox("Detected Titles:", title_candidates, key="sel_title")
    final_title = st.text_input("Confirm/Manual Title Entry", value=title_selection if title_selection != "[Manual Entry]" else "")
    
    # --- DATE ---
    st.subheader("Date")
    date_selection = st.selectbox("Detected Dates:", date_candidates, key="sel_date")
    
    parsed_date = datetime.today().date()
    if date_selection != "[Manual Entry]":
        current_year = datetime.now().year
        date_match = re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*([A-Za-z]+\s+\d{1,2})', date_selection, re.IGNORECASE)
        if date_match:
            try:
                clean_date_str = f"{date_match.group(1).replace(',', '')} {current_year}"
                parsed_date = datetime.strptime(clean_date_str, "%B %d %Y").date()
            except ValueError:
                pass
    
    final_date = st.date_input("Confirm/Manual Date Entry", value=parsed_date)
    
    # --- TIME ---
    st.subheader("Time")
    time_selection = st.selectbox("Detected Times:", time_candidates, key="sel_time")
    
    parsed_start, parsed_end = time(9, 0), time(10, 0)
    if time_selection != "[Manual Entry]":
        time_range_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))', time_selection, re.IGNORECASE)
        def parse_time(t_str):
            t_str = t_str.replace(" ", "").upper()
            for fmt in ("%I:%M%p", "%I%p"):
                try:
                    return datetime.strptime(t_str, fmt).time()
                except ValueError:
                    continue
            return None
            
        if time_range_match:
            s_time = parse_time(time_range_match.group(1))
            e_time = parse_time(time_range_match.group(2))
            if s_time: parsed_start = s_time
            if e_time: parsed_end = e_time

    col1, col2 = st.columns(2)
    with col1:
        final_start = st.time_input("Start Time", value=parsed_start)
    with col2:
        final_end = st.time_input("End Time", value=parsed_end)
        
    # --- LOCATION ---
    st.subheader("Location")
    loc_selection = st.selectbox("Detected Locations:", loc_candidates, key="sel_loc")
    
    clean_loc = loc_selection
    if loc_selection != "[Manual Entry]":
        loc_label_match = re.search(r'(?:location:)\s*([^\n]+)', loc_selection, re.IGNORECASE)
        if loc_label_match:
            clean_loc = loc_label_match.group(1).strip()
            
    final_location = st.text_input("Confirm/Manual Location Entry", value=clean_loc if clean_loc != "[Manual Entry]" else "")
    
    # --- DESCRIPTION ---
    st.subheader("Description / Notes")
    final_desc = st.text_area("Event Notes", value=raw_text, height=120) 
    
    # --- SUBMIT ---
    submitted = st.form_submit_button("✅ Confirm & Create Calendar Link")

if submitted:
    base_cal_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    encoded_title = quote(final_title)
    encoded_location = quote(final_location)
    encoded_desc = quote(final_desc)
    
    date_formatted = final_date.strftime("%Y%m%d")
    start_formatted = final_start.strftime("%H%M%S")
    end_formatted = final_end.strftime("%H%M%S")
    
    dates_param = f"&dates={date_formatted}T{start_formatted}/{date_formatted}T{end_formatted}&ctz=America/New_York"
    
    final_calendar_url = f"{base_cal_url}&text={encoded_title}&location={encoded_location}&details={encoded_desc}{dates_param}"
    
    st.markdown("### 🚀 Add to Your Calendar")
    st.markdown(f'<a href="{final_calendar_url}" target="_blank"><button style="background-color:#1a73e8;color:white;padding:10px 20px;border:none;border-radius:4px;cursor:pointer;font-size:16px;">📅 Open in Google Calendar</button></a>', unsafe_allow_html=True)
