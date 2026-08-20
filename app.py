import streamlit as st
import re
from datetime import datetime, date, time
from urllib.parse import quote
from pypdf import PdfReader

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="centered")

# Initialize Session State for parsed data
if 'parsed_data' not in st.session_state:
    st.session_state.parsed_data = None

st.title("📅 Event Text & PDF Parser")
st.markdown("Extract event details and review them before generating your calendar link.")

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
                text = page.extract_text()
                if text:
                    raw_pdf_text += text + "\n"
            
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

if st.button("Extract Details", type="primary"):
    if not raw_text.strip():
        st.error("Please provide event details first.")
    else:
        with st.spinner("Extracting..."):
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            
            # Guesses
            title_guess = lines[0] if lines else "Untitled Event"
            for line in lines:
                if any(keyword in line for keyword in ["Ambassador", "Mission", "Meeting", "Volunteer", "Shift", "Reminder"]):
                    title_guess = line.strip()
                    break

            date_guess = datetime.today().date()
            current_year = datetime.now().year
            date_match = re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*([A-Za-z]+\s+\d{1,2})', raw_text, re.IGNORECASE)
            if date_match:
                try:
                    clean_date_str = f"{date_match.group(1).replace(',', '')} {current_year}"
                    date_guess = datetime.strptime(clean_date_str, "%B %d %Y").date()
                except ValueError:
                    pass 

            start_time_guess, end_time_guess = None, None
            time_range_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))', raw_text, re.IGNORECASE)
            
            def parse_time(t_str):
                t_str = t_str.replace(" ", "").upper()
                for fmt in ("%I:%M%p", "%I%p"):
                    try:
                        return datetime.strptime(t_str, fmt).time()
                    except ValueError:
                        continue
                return None

            if time_range_match:
                start_time_guess = parse_time(time_range_match.group(1))
                end_time_guess = parse_time(time_range_match.group(2))

            location_guess = ""
            loc_label_match = re.search(r'(?:location:)\s*([^\n]+)', raw_text, re.IGNORECASE)
            if loc_label_match:
                location_guess = loc_label_match.group(1).strip()
            else:
                addr_match = re.search(r'(\d+\s+[A-Za-z0-9\s,\.-]+(?:New York|NY)[\s\d]*)', raw_text, re.IGNORECASE)
                if addr_match:
                    location_guess = addr_match.group(1).strip()
                else:
                    campus_match = re.search(r'((?:Tribeca|Bowery)\s+Campus[^\n]*)', raw_text, re.IGNORECASE)
                    if campus_match:
                        location_guess = campus_match.group(1).strip()

            # Save to session state so it populates the form below
            st.session_state.parsed_data = {
                "title": title_guess,
                "date": date_guess,
                "start_time": start_time_guess,
                "end_time": end_time_guess,
                "location": location_guess,
                "description": raw_text
            }

# --- STEP 2: REVIEW & EDIT FORM ---
if st.session_state.parsed_data:
    st.markdown("---")
    st.markdown("### 📝 Review and Edit Event Details")
    
    with st.form("event_review_form"):
        # Editable fields pre-populated with our parser's guesses
        final_title = st.text_input("Event Title", value=st.session_state.parsed_data["title"])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            final_date = st.date_input("Date", value=st.session_state.parsed_data["date"])
        with col2:
            final_start = st.time_input("Start Time", value=st.session_state.parsed_data["start_time"] if st.session_state.parsed_data["start_time"] else time(9, 0))
        with col3:
            final_end = st.time_input("End Time", value=st.session_state.parsed_data["end_time"] if st.session_state.parsed_data["end_time"] else time(10, 0))
            
        final_location = st.text_input("Location", value=st.session_state.parsed_data["location"])
        final_desc = st.text_area("Notes / Description", value=st.session_state.parsed_data["description"], height=100)
        
        submitted = st.form_submit_button("✅ Confirm & Create Calendar Link")
        
        if submitted:
            # Build the URL using the confirmed form data
            base_cal_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
            encoded_title = quote(final_title)
            encoded_location = quote(final_location)
            encoded_desc = quote(final_desc)
            
            date_formatted = final_date.strftime("%Y%m%d")
            start_formatted = final_start.strftime("%H%M%S")
            end_formatted = final_end.strftime("%H%M%S")
            
            # ctz parameter locks it to Eastern Time
            dates_param = f"&dates={date_formatted}T{start_formatted}/{date_formatted}T{end_formatted}&ctz=America/New_York"
            
            final_calendar_url = f"{base_cal_url}&text={encoded_title}&location={encoded_location}&details={encoded_desc}{dates_param}"
            
            st.markdown("### 🚀 Add to Your Calendar")
            st.markdown(f'<a href="{final_calendar_url}" target="_blank"><button style="background-color:#1a73e8;color:white;padding:10px 20px;border:none;border-radius:4px;cursor:pointer;font-size:16px;">📅 Open in Google Calendar</button></a>', unsafe_allow_html=True
