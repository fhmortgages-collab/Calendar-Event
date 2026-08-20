import streamlit as st
import re
from datetime import datetime, time
from urllib.parse import quote
from pypdf import PdfReader

# Page Configuration - Set to WIDE layout to prevent scrolling
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="wide")

st.title("📅 Event Text & PDF Parser")
st.markdown("Extract event details on the left, and verify them on the right without scrolling.")

# Split the page into two main columns (Input on Left, Form on Right)
col_input, col_form = st.columns([1, 1.2], gap="large")

with col_input:
    st.markdown("### 📥 1. Input Event Data")
    input_method = st.radio("Select Input Method:", ["Upload PDF File", "Paste Text Manually"], horizontal=True)
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
                st.success("Extracted text from PDF!")
            except Exception as e:
                st.error(f"Error reading PDF file: {str(e)}")

    # Make the text area fill the remaining vertical space neatly
    raw_text = st.text_area(
        "Event Details Text:", 
        height=350, 
        value=extracted_text if extracted_text else "",
        placeholder="Paste event text here or upload a PDF above..."
    )

# --- SMART FILTERING LOGIC ---
all_lines = []
title_candidates = []
date_candidates = []
time_candidates = []
loc_candidates = []

if raw_text.strip():
    extracted_lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    all_lines.extend(extracted_lines)
    
    for line in extracted_lines:
        lower_line = line.lower()
        if re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|aug|sep|oct|nov|dec|monday|tuesday|wednesday|thursday|friday|saturday|sunday)', lower_line):
            date_candidates.append(line)
        if re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', lower_line):
            time_candidates.append(line)
        if re.search(r'(location:|street|st|ave|avenue|blvd|campus|new york|ny|room)', lower_line) or re.search(r'\d+\s+[a-z]+', lower_line):
            loc_candidates.append(line)
        if len(line.split()) < 15 and not line.startswith("http"):
            title_candidates.append(line)

# Fallbacks: If no matches, supply all lines, or a blank string if empty
if not date_candidates: date_candidates = all_lines if all_lines else [""]
if not time_candidates: time_candidates = all_lines if all_lines else [""]
if not loc_candidates: loc_candidates = all_lines if all_lines else [""]
if not title_candidates: title_candidates = all_lines if all_lines else [""]

with col_form:
    st.markdown("### 📝 2. Verify & Map Details")
    
    with st.form("event_mapping_form"): 
        
        # --- TITLE ---
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            title_selection = st.selectbox("Detected Titles:", title_candidates, key="sel_title")
        with t_col2:
            final_title = st.text_input("Final Title:", value=title_selection)
        
        # --- DATE ---
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            date_selection = st.selectbox("Detected Dates:", date_candidates, key="sel_date")
        
        parsed_date = datetime.today().date()
        if date_selection and date_selection != "":
            current_year = datetime.now().year
            date_match = re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*([A-Za-z]+\s+\d{1,2})', date_selection, re.IGNORECASE)
            if date_match:
                try:
                    clean_date_str = f"{date_match.group(1).replace(',', '')} {current_year}"
                    parsed_date = datetime.strptime(clean_date_str, "%B %d %Y").date()
                except ValueError:
                    pass
        
        with d_col2:
            final_date = st.date_input("Final Date:", value=parsed_date)
        
        # --- TIME ---
        tm_col1, tm_col2, tm_col3 = st.columns([2, 1, 1])
        with tm_col1:
            time_selection = st.selectbox("Detected Times:", time_candidates, key="sel_time")
        
        parsed_start, parsed_end = time(9, 0), time(10, 0)
        if time_selection and time_selection != "":
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

        with tm_col2:
            final_start = st.time_input("Start Time:", value=parsed_start)
        with tm_col3:
            final_end = st.time_input("End Time:", value=parsed_end)
            
        # --- LOCATION ---
        l_col1, l_col2 = st.columns(2)
        with l_col1:
            loc_selection = st.selectbox("Detected Locations:", loc_candidates, key="sel_loc")
        
        clean_loc = loc_selection
        if loc_selection and loc_selection != "":
            loc_label_match = re.search(r'(?:location:)\s*([^\n]+)', loc_selection, re.IGNORECASE)
            if loc_label_match:
                clean_loc = loc_label_match.group(1).strip()
                
        with l_col2:
            final_location = st.text_input("Final Location:", value=clean_loc)
        
        # --- DESCRIPTION ---
        final_desc = st.text_area("Event Notes (Editable):", value=raw_text, height=100) 
        
        # --- SUBMIT ---
        st.markdown("<br>", unsafe_allow_html=True) # Adds a little spacing
        submitted = st.form_submit_button("✅ Generate Calendar Link", use_container_width=True)

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
        
        st.success("Link generated successfully!")
        st.markdown(f'<a href="{final_calendar_url}" target="_blank"><button style="background-color:#1a73e8;color:white;padding:12px 24px;border:none;border-radius:4px;cursor:pointer;font-size:16px;font-weight:bold;width:100%;">📅 Open in Google Calendar</button></a>', unsafe_allow_html=True)
