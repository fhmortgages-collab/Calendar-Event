import streamlit as st
import re
from datetime import datetime, time
from urllib.parse import quote
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="wide")

# --- SESSION STATE INIT ---
if 'show_mapping' not in st.session_state:
    st.session_state.show_mapping = False
if 'event_text' not in st.session_state:
    st.session_state.event_text = ""
if 'uploaded_bytes' not in st.session_state:
    st.session_state.uploaded_bytes = None
if 'input_method' not in st.session_state:
    st.session_state.input_method = "Upload PDF"

def clear_all():
    st.session_state.show_mapping = False
    st.session_state.event_text = ""
    st.session_state.uploaded_bytes = None
    st.session_state.input_method = "Upload PDF"

# --- Helper: Custom time picker with dropdowns ---
def custom_time_picker(label, default_time, key_prefix):
    """
    Returns a time object from three dropdowns: hour (1-12), minute (00-59), AM/PM.
    """
    if default_time is None:
        default_time = time(9, 0)
    # Convert to 12-hour format
    hour_12 = default_time.hour % 12
    if hour_12 == 0:
        hour_12 = 12
    minute = default_time.minute
    am_pm = "AM" if default_time.hour < 12 else "PM"

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        hour = st.selectbox(
            f"{label} – Hour",
            options=list(range(1, 13)),
            index=hour_12 - 1,
            key=f"{key_prefix}_hour"
        )
    with col2:
        minute = st.selectbox(
            "Minute",
            options=[f"{i:02d}" for i in range(0, 60, 5)],  # 5‑minute increments for simplicity
            index=minute // 5,
            key=f"{key_prefix}_minute"
        )
    with col3:
        am_pm = st.selectbox(
            "AM/PM",
            options=["AM", "PM"],
            index=0 if am_pm == "AM" else 1,
            key=f"{key_prefix}_ampm"
        )
    # Convert to 24-hour
    hour_24 = hour if am_pm == "AM" else hour + 12
    if hour_24 == 12 and am_pm == "AM":
        hour_24 = 0
    if hour_24 == 24:
        hour_24 = 12
    return time(hour_24, int(minute))

# --- MAIN LAYOUT ---
st.title("📅 Compact Event Parser")

col_input, col_form = st.columns([1, 1.3], gap="small")

with col_input:
    input_method = st.selectbox(
        "Input Method",
        ["Upload PDF", "Upload Image", "Paste Text"],
        key="input_method_select",
        index=["Upload PDF", "Upload Image", "Paste Text"].index(st.session_state.input_method)
    )
    st.session_state.input_method = input_method

    extracted_text = ""

    if input_method == "Upload PDF":
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], key="pdf_uploader")
        if uploaded_file is not None:
            st.session_state.uploaded_bytes = uploaded_file.read()
            try:
                doc = fitz.open(stream=st.session_state.uploaded_bytes, filetype="pdf")
                raw_text = ""
                for page in doc:
                    raw_text += page.get_text() + "\n"
                raw_text = raw_text.strip()

                if not raw_text:
                    with st.spinner("OCR scanning PDF pages..."):
                        ocr_text = ""
                        for page_num in range(len(doc)):
                            page = doc.load_page(page_num)
                            pix = page.get_pixmap()
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            ocr_text += pytesseract.image_to_string(img) + "\n"
                        raw_text = ocr_text.strip()

                extracted_text = "\n".join([line.strip() for line in raw_text.split('\n') if line.strip()])
                if extracted_text:
                    st.session_state.event_text = extracted_text
                else:
                    st.warning("No text could be extracted from this PDF. Please paste manually.")
            except Exception as e:
                st.error(f"PDF error: {e}")

    elif input_method == "Upload Image":
        uploaded_image = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], key="image_uploader")
        if uploaded_image is not None:
            try:
                image = Image.open(uploaded_image)
                with st.spinner("Scanning..."):
                    raw_img_text = pytesseract.image_to_string(image)
                extracted_text = "\n".join([line.strip() for line in raw_img_text.split('\n') if line.strip()])
                if extracted_text:
                    st.session_state.event_text = extracted_text
                else:
                    st.warning("No text could be extracted from this image. Please paste manually.")
            except Exception as e:
                st.error(f"Image error: {e}")

    raw_text = st.text_area(
        "Event Details Text",
        value=st.session_state.event_text,
        height=180,
        placeholder="Event text will appear here...",
        key="event_text_area"
    )
    if raw_text != st.session_state.event_text:
        st.session_state.event_text = raw_text

    with st.expander("🔍 Debug info"):
        st.write(f"Session text length: {len(st.session_state.event_text)} characters")
        if st.session_state.event_text:
            st.text_area("Current content (first 500 chars)", st.session_state.event_text[:500], height=100)
        else:
            st.info("No text in session state.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 Extract Info", use_container_width=True, type="primary"):
            if st.session_state.event_text.strip():
                st.session_state.show_mapping = True
            else:
                st.warning("No text to process. Please upload a file or enter text.")
                st.session_state.show_mapping = False
    with c2:
        if st.button("🗑️ Clear / Reset", use_container_width=True):
            clear_all()
            st.rerun()

    if st.session_state.event_text.strip():
        st.session_state.show_mapping = True

with col_form:
    if st.session_state.show_mapping and st.session_state.event_text.strip():
        text = st.session_state.event_text

        # --- SMART FILTERING (unchanged) ---
        all_lines, title_candidates, date_candidates, time_candidates, loc_candidates = [], [], [], [], []
        extracted_lines = [line.strip() for line in text.split('\n') if line.strip()]
        all_lines.extend(extracted_lines)

        for line in extracted_lines:
            lower_line = line.lower()
            if re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|mon|tue|wed|thu|fri|sat|sun)', lower_line):
                date_candidates.append(line)
            if re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', lower_line):
                time_candidates.append(line)
            if re.search(r'(location:|street|st|ave|avenue|blvd|campus|new york|ny|room)', lower_line) or re.search(r'\d+\s+[a-z]+', lower_line):
                loc_candidates.append(line)
            if len(line.split()) < 15 and not line.startswith("http"):
                title_candidates.append(line)

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

        # --- ROW 3: TIME (CUSTOM PICKER) ---
        st.markdown("**Event Time**")
        # Parse detected time to get default start/end
        parsed_start, parsed_end = time(9, 0), time(10, 0)

        # Try to parse from detected time line
        if time_candidates and time_candidates[0] != "":
            time_line = time_candidates[0]
            time_range_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))', time_line, re.IGNORECASE)
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

        # Use custom pickers
        col_start, col_end = st.columns(2)
        with col_start:
            st.write("**Start**")
            final_start = custom_time_picker("Start", parsed_start, "start_time")
        with col_end:
            st.write("**End**")
            final_end = custom_time_picker("End", parsed_end, "end_time")

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
