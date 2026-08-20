import streamlit as st
import re
from datetime import datetime, time
from urllib.parse import quote
import pdfplumber
from PIL import Image
import pytesseract

# Page Configuration - Set to WIDE layout
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="wide")

# --- SESSION STATE MANAGEMENT ---
if 'show_mapping' not in st.session_state:
    st.session_state.show_mapping = False
if 'widget_key' not in st.session_state:
    st.session_state.widget_key = 0

def extract_action():
    st.session_state.show_mapping = True

def reset_fields_action():
    st.session_state.show_mapping = False

def clear_all_action():
    st.session_state.show_mapping = False
    st.session_state.widget_key += 1 

# --- MAIN LAYOUT ---
st.title("📅 Event Text, PDF & Image Parser")

col_input, col_form = st.columns([1, 1.2], gap="large")

with col_input:
    # ADDED: Image upload option
    input_method = st.radio("Input Method:", ["Upload PDF", "Upload Image", "Paste Text"], horizontal=True, key=f"radio_{st.session_state.widget_key}")
    
    extracted_text = ""
    
    if input_method == "Upload PDF":
        uploaded_file = st.file_uploader("Upload PDF:", type=["pdf"], key=f"pdf_{st.session_state.widget_key}")
        if uploaded_file:
            try:
                with pdfplumber.open(uploaded_file) as pdf:
                    raw_pdf_text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            raw_pdf_text += page_text + "\n"
                
                filtered_lines = [line.strip() for line in raw_pdf_text.split('\n') if line.strip()]
                extracted_text = "\n".join(filtered_lines)
            except Exception as e:
                st.error(f"Error extracting text: {str(e)}")
                
    elif input_method == "Upload Image":
        uploaded_image = st.file_uploader("Upload Image:", type=["png", "jpg", "jpeg"], key=f"img_{st.session_state.widget_key}")
        if uploaded_image:
            try:
                image = Image.open(uploaded_image)
                # ADDED: Tesseract processes the image into text
                raw_img_text = pytesseract.image_to_string(image)
                filtered_lines = [line.strip() for line in raw_img_text.split('\n') if line.strip()]
                extracted_text = "\n".join(filtered_lines)
                st.image(image, caption="Uploaded Image", use_container_width=True)
            except Exception as e:
                st.error(f"Error extracting text from image: {str(e)}")

    # Text Area
    raw_text = st.text_area(
        "Event Details Text:", 
        height=250, 
        value=extracted_text, 
        placeholder="Paste text, or upload a PDF/Image...",
        key=f"text_{st.session_state.widget_key}"
    )

    # Control Buttons
    b1, b2, b3 = st.columns(3)
    with b1:
        st.button("🔍 Extract Info", on_click=extract_action, use_container_width=True, type="primary")
    with b2:
        st.button("🔄 Reset Fields", on_click=reset_fields_action, use_container_width=True)
    with b3:
        st.button("🗑️ Clear All", on_click=clear_all_action, use_container_width=True)

with col_form:
    if st.session_state.show_mapping and raw_text.strip():
        # --- SMART FILTERING LOGIC ---
        all_lines = []
        title_candidates, date_candidates, time_candidates, loc_candidates = [], [], [], []
        
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

        # Fallbacks
        if not date_candidates: date_candidates = all_lines if all_lines else [""]
        if not time_candidates: time_candidates = all_lines if all_lines else [""]
        if not loc_candidates: loc_candidates = all_lines if all_lines else [""]
        if not title_candidates: title_candidates = all_lines if all_lines else [""]
        
        st.markdown("### 📝 Verify & Map Details")
        
        # ADDED: "Other" option appended to the top of all dropdowns
        manual_opt = "Other (Manual Entry)"
        
        # --- TITLE ---
        t_col1, t_col2 = st.columns(2)
        with t_col1: 
            title_selection = st.selectbox("Detected Titles:", [manual_opt] + title_candidates)
        with t_col2: 
            final_title = st.text_input("Final Title:", value=title_selection if title_selection != manual_opt else "")
        
        # --- DATE ---
        d_col1, d_col2 = st.columns(2)
        with d_col1: 
            date_selection = st.selectbox("Detected Dates:", [manual_opt] + date_candidates)
        
        parsed_date = datetime.today().date()
        if date_selection != manual_opt and date_selection != "":
            current_year = datetime.now().year
            date_match = re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*([A-Za-z]+\s+\d{1,2})', date_selection, re.IGNORECASE)
            if date_match:
                try:
                    clean_date_str = f"{date_match.group(1).replace(',', '')} {current_year}"
                    parsed_date = datetime.strptime(clean_date_str, "%B %d %Y").date()
                except ValueError: pass
        
        with d_col2: 
            final_date = st.date_input("Final Date:", value=parsed_date)
        
        # --- TIME ---
        tm_col1, tm_col2, tm_col3 = st.columns([2, 1, 1])
        with tm_col1: 
            time_selection = st.selectbox("Detected Times:", [manual_opt] + time_candidates)
        
        parsed_start, parsed_end = time(9, 0), time(10, 0)
        if time_selection != manual_opt and time_selection != "":
            time_range_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))', time_selection, re.IGNORECASE)
            def parse_time(t_str):
                t_str = t_str.replace(" ", "").upper()
                for fmt in ("%I:%M%p", "%I%p"):
                    try: return datetime.strptime(t_str, fmt).time()
                    except ValueError: continue
                return None
                
            if time_range_match:
                s_time = parse_time(time_range_match.group(1))
                e_time = parse_time(time_range_match.group(2))
                if s_time: parsed_start = s_time
                if e_time: parsed_end = e_time

        with tm_col2: 
            # Click inside this box to see the clock icon
            final_start = st.time_input("Start:", value=parsed_start)
        with tm_col3: 
            final_end = st.time_input("End:", value=parsed_end)
            
        # --- LOCATION ---
        l_col1, l_col2 = st.columns(2)
        with l_col1: 
            loc_selection = st.selectbox("Detected Locations:", [manual_opt] + loc_candidates)
        
        clean_loc = ""
        if loc_selection != manual_opt and loc_selection != "":
            clean_loc = loc_selection
            loc_label_match = re.search(r'(?:location:)\s*([^\n]+)', loc_selection, re.IGNORECASE)
            if loc_label_match: clean_loc = loc_label_match.group(1).strip()
                
        with l_col2: 
            final_location = st.text_input("Final Location (Autocomplete via browser):", value=clean_loc)
        
        # --- DESCRIPTION & SUBMIT ---
        final_desc = st.text_area("Notes:", value=raw_text, height=68) 
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # We use a standard button here instead of a form submit
        if st.button("✅ Generate Calendar Link", use_container_width=True):
            base_cal_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
            encoded_title = quote(final_title)
            encoded_location = quote(final_location)
            encoded_desc = quote(final_desc)
            
            date_formatted = final_date.strftime("%Y%m%d")
            start_formatted = final_start.strftime("%H%M%S")
            end_formatted = final_end.strftime("%H%M%S")
            
            dates_param = f"&dates={date_formatted}T{start_formatted}/{date_formatted}T{end_formatted}&ctz=America/New_York"
            
            final_calendar_url = f"{base_cal_url}&text={encoded_title}&location={encoded_location}&details={encoded_desc}{dates_param}"
            
            st.markdown(f'<a href="{final_calendar_url}" target="_blank"><button style="background-color:#1a73e8;color:white;padding:12px 24px;border:none;border-radius:4px;cursor:pointer;font-size:16px;font-weight:bold;width:100%;">📅 Open in Google Calendar</button></a>', unsafe_allow_html=True)

    elif st.session_state.show_mapping and not raw_text.strip():
        st.warning("Please paste text, or upload a PDF/Image before extracting.")
    else:
        st.info("👈 Enter your event details on the left and click **Extract Info**.")
