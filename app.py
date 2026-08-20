import streamlit as st
import re
from datetime import datetime, time
from urllib.parse import quote

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="wide")

# --- SESSION STATE ---
if 'show_mapping' not in st.session_state:
    st.session_state.show_mapping = False
if 'event_text' not in st.session_state:
    st.session_state.event_text = ""

def clear_all():
    st.session_state.show_mapping = False
    st.session_state.event_text = ""

# --- MAIN LAYOUT ---
st.title("📅 Compact Event Parser")

col_input, col_form = st.columns([1, 1.3], gap="small")

with col_input:
    st.markdown("### 📝 Enter Event Details")
    raw_text = st.text_area(
        "Paste your event text here",
        value=st.session_state.event_text,
        height=180,
        placeholder="e.g. Meeting on Friday at 2pm, Room 101 ...",
        key="event_text_area"
    )
    if raw_text != st.session_state.event_text:
        st.session_state.event_text = raw_text

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 Extract Info", use_container_width=True, type="primary"):
            if st.session_state.event_text.strip():
                st.session_state.show_mapping = True
            else:
                st.warning("Please paste some text first.")
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

        # --- SMART FILTERING ---
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
        with t_col1:
            title_sel = st.selectbox("Detected Event Name", [manual_opt] + title_candidates)
        with t_col2:
            final_title = st.text_input("Final Event Name", value=title_sel if title_sel != manual_opt else "")

        # --- ROW 2: DATE ---
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            date_sel = st.selectbox("Detected Date", [manual_opt] + date_candidates)
        parsed_date = datetime.today().date()
        if date_sel != manual_opt and date_sel != "":
            current_year = datetime.now().year
            date_match = re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*([A-Za-z]+\s+\d{1,2})', date_sel, re.IGNORECASE)
            if date_match:
                try:
                    clean_date_str = f"{date_match.group(1).replace(',', '')} {current_year}"
                    parsed_date = datetime.strptime(clean_date_str, "%B %d %Y").date()
                except ValueError:
                    pass
        with d_col2:
            final_date = st.date_input("Final Date", value=parsed_date)

        # --- ROW 3: TIME (DETECTED + COMPACT PICKER) ---
        st.markdown("**Event Time**")
        # Parse detected times
        parsed_start, parsed_end = time(9, 0), time(10, 0)
        detected_start_str = "Not detected"
        detected_end_str = "Not detected"

        if time_candidates and time_candidates[0] != "":
            time_line = time_candidates[0]
            time_range_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))', time_line, re.IGNORECASE)
            def parse_time(t_str):
                for fmt in ("%I:%M%p", "%I%p"):
                    try:
                        return datetime.strptime(t_str.replace(" ", "").upper(), fmt).time()
                    except ValueError:
                        continue
                return None
            if time_range_match:
                s_time = parse_time(time_range_match.group(1))
                e_time = parse_time(time_range_match.group(2))
                if s_time:
                    parsed_start = s_time
                    detected_start_str = s_time.strftime("%I:%M %p")
                if e_time:
                    parsed_end = e_time
                    detected_end_str = e_time.strftime("%I:%M %p")

        # Compact time picker with detected label
        def compact_time_picker(label, default_time, detected_str, key_prefix):
            # Convert default to hour (12h), minute, am/pm
            hour_12 = default_time.hour % 12
            if hour_12 == 0: hour_12 = 12
            minute = default_time.minute
            am_pm = "AM" if default_time.hour < 12 else "PM"

            # Show detected time as a label
            st.write(f"**Detected {label}:** {detected_str}")

            # Dropdowns (compact, labels collapsed)
            cols = st.columns([1, 1, 1, 0.2])  # last is spacer
            with cols[0]:
                hour = st.selectbox(
                    f"{label} Hour",
                    options=list(range(1, 13)),
                    index=hour_12 - 1,
                    key=f"{key_prefix}_hour",
                    label_visibility="collapsed"
                )
            with cols[1]:
                minute = st.selectbox(
                    "Minute",
                    options=[f"{i:02d}" for i in range(0, 60, 5)],
                    index=minute // 5,
                    key=f"{key_prefix}_minute",
                    label_visibility="collapsed"
                )
            with cols[2]:
                am_pm = st.selectbox(
                    "AM/PM",
                    options=["AM", "PM"],
                    index=0 if am_pm == "AM" else 1,
                    key=f"{key_prefix}_ampm",
                    label_visibility="collapsed"
                )
            # Convert to 24h
            hour_24 = hour if am_pm == "AM" else hour + 12
            if hour_24 == 12 and am_pm == "AM":
                hour_24 = 0
            if hour_24 == 24:
                hour_24 = 12
            return time(hour_24, int(minute))

        # Start and End times side‑by‑side
        time_col1, time_col2 = st.columns(2)
        with time_col1:
            final_start = compact_time_picker("Start", parsed_start, detected_start_str, "start")
        with time_col2:
            final_end = compact_time_picker("End", parsed_end, detected_end_str, "end")

        # --- ROW 4: LOCATION ---
        l_col1, l_col2 = st.columns(2)
        with l_col1:
            loc_sel = st.selectbox("Detected Location", [manual_opt] + loc_candidates)
        clean_loc = ""
        if loc_sel != manual_opt and loc_sel != "":
            clean_loc = loc_sel
            loc_match = re.search(r'(?:location:)\s*([^\n]+)', loc_sel, re.IGNORECASE)
            if loc_match:
                clean_loc = loc_match.group(1).strip()
        with l_col2:
            final_location = st.text_input("Final Location", value=clean_loc)

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
            st.markdown(
                f'<a href="{final_calendar_url}" target="_blank"><button style="background-color:#1a73e8;color:white;padding:10px;border:none;border-radius:4px;cursor:pointer;font-size:14px;font-weight:bold;width:100%;">📅 Open Google Calendar</button></a>',
                unsafe_allow_html=True
            )

    elif st.session_state.show_mapping:
        st.warning("Please paste some text first.")
