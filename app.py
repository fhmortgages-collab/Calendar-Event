import streamlit as st
import re
from datetime import datetime, time
from urllib.parse import quote
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="wide")

# --- SESSION STATE INITIALIZATION ---
if 'show_mapping' not in st.session_state:
    st.session_state.show_mapping = False
if 'widget_key' not in st.session_state:
    st.session_state.widget_key = 0
if 'event_text' not in st.session_state:
    st.session_state.event_text = ""
if 'last_error' not in st.session_state:
    st.session_state.last_error = ""

def clear_all_action():
    st.session_state.show_mapping = False
    st.session_state.widget_key += 1
    st.session_state.event_text = ""
    st.session_state.last_error = ""

# --- MAIN LAYOUT ---
st.title("📅 Compact Event Parser")

col_input, col_form = st.columns([1, 1.3], gap="small")

with col_input:
    # Dropdown for input method
    input_method = st.selectbox(
        "Input Method",
        ["Upload PDF", "Upload Image", "Paste Text"],
        key=f"method_{st.session_state.widget_key}"
    )
    
    extracted_text = ""
    
    if input_method == "Upload PDF":
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed", key=f"pdf_{st.session_state.widget_key}")
        if uploaded_file:
            try:
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                raw_pdf_text = ""
                for page in doc:
                    raw_pdf_text += page.get_text() + "\n"
                raw_pdf_text = raw_pdf_text.strip()
                
                # If no text, try OCR
                if not raw_pdf_text:
                    with st.spinner("OCR scanning PDF pages (may take a while)..."):
                        ocr_text = ""
                        try:
                            for page_num in range(len(doc)):
                                page = doc.load_page(page_num)
                                pix = page.get_pixmap()
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                ocr_text += pytesseract.image_to_string(img) + "\n"
                            raw_pdf_text = ocr_text.strip()
                        except Exception as e:
                            st.session_state.last_error = f"OCR failed: {str(e)}"
                            st.error(f"OCR error: {e}. Please install Tesseract or paste text manually.")
                            raw_pdf_text = ""
                
                extracted_text = "\n".join([line.strip() for line in raw_pdf_text.split('\n') if line.strip()])
            except Exception as e:
                st.error(f"PDF processing error: {str(e)}")
                st.session_state.last_error = f"PDF error: {str(e)}"
                
    elif input_method == "Upload Image":
        uploaded_image = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], label_visibility="collapsed", key=f"img_{st.session_state.widget_key}")
        if uploaded_image:
            try:
                image = Image.open(uploaded_image)
                with st.spinner("Scanning..."):
                    raw_img_text = pytesseract.image_to_string(image)
                extracted_text = "\n".join([line.strip() for line in raw_img_text.split('\n') if line.strip()])
            except Exception as e:
                st.error(f"Image OCR error: {str(e)}")
                st.session_state.last_error = f"OCR error: {str(e)}"

    # If new text was extracted, store it in session state
    if extracted_text:
        st.session_state.event_text = extracted_text
    # If switching to Paste Text, keep the existing session text
    elif input_method == "Paste Text":
        # Keep the current session text (user may paste manually)
        pass

    # Text area – uses session state value
    raw_text = st.text_area(
        "Event Details Text",
        value=st.session_state.event_text,
        height=180,
        placeholder="Event text will appear here...",
        key=f"text_{st.session_state.widget_key}"
    )
    # Update session state when user types manually
    if raw_text != st.session_state.event_text:
        st.session_state.event_text = raw_text

    # Debug expander
    with st.expander("🔍 Debug info (extracted text length)"):
        st.write(f"Session text length: {len(st.session_state.event_text)} characters")
        if st.session_state.last_error:
            st.warning(f"Last error: {st.session_state.last_error}")
        if st.session_state.event_text:
            st.text_area("Current content (first 500 chars)", st.session_state.event_text[:500], height=100)

    # Buttons
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 Extract Info", use_container_width=True, type="primary"):
            if st.session_state.event_text.strip():
                st.session_state.show_mapping = True
            else:
                st.warning("No text to process. Please upload a file or enter text.")
                st.session_state.show_mapping = False
    with c2:
        st.button("🗑️ Clear / Reset", on_click=clear_all_action, use_container_width=True)

    # Auto-show mapping if text exists in session
    if st.session_state.event_text.strip():
        st.session_state.show_mapping = True

with col_form:
    if st.session_state.show_mapping and st.session_state.event_text.strip():
        # --- SMART FILTERING LOGIC ---
        text = st.session_state.event_text
        all_lines, title_candidates, date_candidates, time_candidates, loc_candidates = [], [], [], [], []
        
        extracted_lines = [line.strip() for line in text.split('\n') if line.strip()]
        all_lines.extend(extracted_lines)
        
        for line in extracted_lines:
            lower_line = line.lower()
            if re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|mon|tue|wed|thu|fri|sat|sun)', lower_line): date_candidates.append(line)
            if re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', lower_line): time_candidates.append(line)
            if re.search(r'(location:|street|st|ave|avenue|blvd|campus|new york|ny|room)', lower_line) or re.search(r'\d+\s+[a-z]+', lower_line): loc_candidates.append(line)
            if len(line.split()) < 15 and not line.startswith("http"): title_candidates.append(line)

        if not date_candidates: date_candidates = all_lines if all_lines else [""]
        if not time_candidates: time_candidates = all_lines if all_lines else [""]
        if not loc_candidates: loc_candidates = all_lines if all_lines else [""]
        if not title_candidates: title_candidates = all_lines if all_lines else [""]
        
        st.markdown("### 📝 Verify & Map Details")
        manual_opt = "Other (Manual Entry)"
        
        # --- ROW 1: EVENT NAME ---
        t_col1, t_col2 = st.columns(2)
        with t_col1: title_sel = st.selectbox("Detected Event Name", [manual_opt] + title_candidates)
        with t_col2: final_title = st.text_input("Final Event Name", value=title_sel if title_sel != manual_opt else "")
        
        # --- ROW 2: DATE ---
        d_col1, d_col2 = st.columns(2)
        with d_col1: date_sel = st.selectbox("Detected Date", [manual_opt] + date_candidates)
        
        parsed_date = datetime.today().date()
        if date_sel != manual_opt and date_sel != "":
            current_year = datetime.now().year
            date_match = re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*([A-Za-z]+\s+\d{1,2})', date_sel, re.IGNORECASE)
            if date_match:
                try:
                    clean_date_str = f"{date_match.group(1).replace(',', '')} {current_year}"
                    parsed_date = datetime.strptime(clean_date_str, "%B %d %Y").date()
                except ValueError: pass
        with d_col2: final_date = st.date_input("Final Date", value=parsed_date)
        
        # --- ROW 3: TIME ---
        tm_col1, tm_col2, tm_col3 = st.columns([2, 1, 1])
        with tm_col1: time_sel = st.selectbox("Detected Time", [manual_opt] + time_candidates)
        
        parsed_start, parsed_end = time(9, 0), time(10, 0)
        if time_sel != manual_opt and time_sel != "":
            time_range_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))', time_sel, re.IGNORECASE)
            def parse_time(t_str):
                for fmt in ("%I:%M%p", "%I%p"):
                    try: return datetime.strptime(t_str.replace(" ", "").upper(), fmt).time()
                    except ValueError: continue
                return None
                
            if time_range_match:
                s_time = parse_time(time_range_match.group(1))
                e_time = parse_time(time_range_match.group(2))
                if s_time: parsed_start = s_time
                if e_time: parsed_end = e_time

        with tm_col2: final_start = st.time_input("Start Time", value=parsed_start)
        with tm_col3: final_end = st.time_input("End Time", value=parsed_end)
            
        # --- ROW 4: LOCATION ---
        l_col1, l_col2 = st.columns(2)
        with l_col1: loc_sel = st.selectbox("Detected Location", [manual_opt] + loc_candidates)
        
        clean_loc = ""
        if loc_sel != manual_opt and loc_sel != "":
            clean_loc = loc_sel
            loc_match = re.search(r'(?:location:)\s*([^\n]+)', loc_sel, re.IGNORECASE)
            if loc_match: clean_loc = loc_match.group(1).strip()
        with l_col2: final_location = st.text_input("Final Location", value=clean_loc)
        
        # --- ROW 5: NOTES & SUBMIT ---
        final_desc = st.text_area("Event Notes", value=text, height=68) 
        
        if st.button("✅ Generate Link", use_container_width=True):
            base_cal_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
            encoded_title = quote(final_title)
            encoded_location = quote(final_location)
            encoded_desc = quote(final_desc)
            
            date_formatted = final_date.strftime("%Y%m%d")
            start_formatted = final_start.strftime("%H%M%S")
            end_formatted = final_end.strftime("%H%M%S")
            
            dates_param = f"&dates={date_formatted}T{start_formatted}/{date_formatted}T{end_formatted}&ctz=America/New_York"
            final_calendar_url = f"{base_cal_url}&text={encoded_title}&location={encoded_location}&details={encoded_desc}{dates_param}"
            
            st.markdown(f'<a href="{final_calendar_url}" target="_blank"><button style="background-color:#1a73e8;color:white;padding:10px;border:none;border-radius:4px;cursor:pointer;font-size:14px;font-weight:bold;width:100%;">📅 Open Google Calendar</button></a>', unsafe_allow_html=True)
    
    elif st.session_state.show_mapping:
        st.warning("Please provide text/file first.")
