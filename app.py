import streamlit as st
import re
from datetime import datetime, time
from urllib.parse import quote
from pypdf import PdfReader

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="centered")

st.title("📅 Event Text & PDF Parser")
st.markdown("Extract event details and map them to calendar fields using dropdowns.")

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

# Extract lines to create dropdown candidates
candidates = ["[Manual Entry]"]
if raw_text.strip():
    extracted_lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    candidates.extend(extracted_lines)

st.markdown("---")
st.markdown("### 📝 Map Extracted Data to Calendar Fields")
st.markdown("Select the extracted line that corresponds to each field, or select **[Manual Entry]** to type it yourself.")

with st.form("event_mapping_form"): # All of this is enclosed in a form
    
    # --- TITLE ---
    st.subheader("Event Title")
    title_selection = st.selectbox("Select Title from text:", candidates, key="sel_title")
    final_title = st.text_input("Confirm/Manual Title Entry", value=title_selection if title_selection != "[Manual Entry]" else "")
    
    # --- DATE ---
    st.subheader("Date")
    date_selection = st.selectbox("Select Date from text:", candidates, key="sel_date")
    
    # Try to parse the selected date line
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
    
    final_date = st.date_input("Confirm/Manual Date Entry", value=parsed_date) # Creates a date widget
    
    # --- TIME ---
    st.subheader("Time")
    time_selection = st.selectbox("Select Time from text:", candidates, key="sel_time")
    
    # Try to parse the selected time line
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
    loc_selection = st.selectbox("Select Location from text:", candidates, key="sel_loc")
    
    # Attempt to clean up the location line if a label is in it (e.g. "Location: 123 Main St")
    clean_loc = loc_selection
    if loc_selection != "[Manual Entry]":
        loc_label_match = re.search(r'(?:location:)\s*([^\n]+)', loc_selection, re.IGNORECASE)
        if loc_label_match:
            clean_loc = loc_label_match.group(1).strip()
            
    final_location = st.text_input("Confirm/Manual Location Entry", value=clean_loc if clean_loc != "[Manual Entry]" else "")
    
    # --- DESCRIPTION ---
    st.subheader("Description / Notes")
    desc_selection = st.selectbox("Select Notes from text (or choose Full Text):", candidates + ["Use Full Text"], index=len(candidates))
    
    desc_val = ""
    if desc_selection == "Use Full Text":
        desc_val = raw_text
    elif desc_selection != "[Manual Entry]":
        desc_val = desc_selection
        
    final_desc = st.text_area("Confirm/Manual Notes Entry", value=desc_val, height=100) # Creates a text area widget
    
    # --- SUBMIT ---
    submitted = st.form_submit_button("✅ Confirm & Create Calendar Link") # Submit button

if submitted:
    # Build the URL using the confirmed form data
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
