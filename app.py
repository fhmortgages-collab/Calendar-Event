import streamlit as st
import re
from datetime import datetime, time, timedelta
from urllib.parse import quote

# --- IMPROVED EXTRACTION FUNCTIONS ---

def get_title_candidates(text):
    """Return up to 3 candidate titles (short lines not date/time/location)."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    candidates = []
    for line in lines:
        lower = line.lower()
        # Skip if it looks like a date, time, or location
        if re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|mon|tue|wed|thu|fri|sat|sun)', lower):
            continue
        if re.search(r'\d{1,2}:\d{2}\s*(am|pm)', lower):
            continue
        if re.search(r'(location|venue|room|building|street|ave|blvd|campus|floor|hosted by|sponsored by)', lower):
            continue
        # Skip very long lines (likely descriptions)
        if len(line.split()) > 12:
            continue
        candidates.append(line)
    # Remove duplicates and limit to 3
    unique = list(dict.fromkeys(candidates))
    return unique[:3] if unique else [""]

def get_organization_candidates(text):
    """Extract organization/company/host names."""
    candidates = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Look for organization indicators
    org_patterns = [
        r'(?i)(?:hosted by|sponsored by|presented by|organized by|from|with)\s+([^\n,]+)',
        r'(?i)([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:Inc|Corp|LLC|Ltd|Company|Co\.?|Corporation|Foundation|Agency|Group|Partners|Associates)',
        r'(?i)([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:meeting|event|workshop|seminar|conference)',
    ]
    
    for pattern in org_patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            org = m.strip()
            if len(org) > 2 and len(org) < 50:
                candidates.append(org)
    
    # Also check for capitalized phrases that might be companies
    for line in lines:
        # Look for "at [Company]" or "with [Company]"
        if re.search(r'\b(at|with)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', line):
            match = re.search(r'\b(at|with)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', line)
            if match and len(match.group(2)) > 2:
                candidates.append(match.group(2))
    
    # Remove duplicates and limit to 3
    unique = list(dict.fromkeys(candidates))
    return unique[:3] if unique else [""]

def get_date_candidates(text):
    """Return up to 3 unique date strings (formatted)."""
    today = datetime.today().date()
    year = today.year
    patterns = [
        r'(?i)(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})?',
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*,?\s*(\d{4})?',
        r'(\d{1,2})/(\d{1,2})/(\d{2,4})',
        r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})',
        r'(?i)(tomorrow|next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday))'
    ]
    date_strings = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                if len(match) == 3:
                    if match[0].isalpha():
                        month_str, day_str, year_str = match
                        day = int(day_str)
                        yr = int(year_str) if year_str else year
                        month = datetime.strptime(month_str[:3], "%b").month
                        try:
                            dt = datetime(yr, month, day).date()
                            date_strings.append(dt.strftime("%B %d, %Y"))
                        except:
                            pass
                    elif match[1].isalpha():
                        day_str, month_str, year_str = match
                        day = int(day_str)
                        yr = int(year_str) if year_str else year
                        month = datetime.strptime(month_str[:3], "%b").month
                        try:
                            dt = datetime(yr, month, day).date()
                            date_strings.append(dt.strftime("%B %d, %Y"))
                        except:
                            pass
                    else:
                        a, b, c = int(match[0]), int(match[1]), int(match[2])
                        if c < 100:
                            c += 2000 if c < 70 else 1900
                        if a <= 12 and b <= 31:
                            try:
                                dt = datetime(c, a, b).date()
                                date_strings.append(dt.strftime("%B %d, %Y"))
                            except:
                                pass
                        if b <= 12 and a <= 31:
                            try:
                                dt = datetime(c, b, a).date()
                                date_strings.append(dt.strftime("%B %d, %Y"))
                            except:
                                pass
                elif len(match) == 1:
                    keyword = match[0].lower()
                    if keyword == 'tomorrow':
                        dt = today + timedelta(days=1)
                        date_strings.append(dt.strftime("%B %d, %Y"))
                    elif keyword.startswith('next '):
                        day_name = keyword.split()[1]
                        days = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
                        target = days.index(day_name)
                        today_weekday = today.weekday()
                        diff = target - today_weekday
                        if diff <= 0:
                            diff += 7
                        dt = today + timedelta(days=diff)
                        date_strings.append(dt.strftime("%B %d, %Y"))
    unique = list(dict.fromkeys(date_strings))
    return unique[:3] if unique else [""]

def get_time_candidates(text):
    """Return up to 3 time range strings."""
    def parse(t_str):
        for fmt in ("%I:%M%p", "%I%p"):
            try:
                return datetime.strptime(t_str.replace(" ", "").upper(), fmt).time()
            except:
                continue
        return None

    range_pattern = r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))'
    ranges = re.findall(range_pattern, text, re.IGNORECASE)
    time_strings = []
    for start_str, end_str in ranges:
        start_t = parse(start_str)
        end_t = parse(end_str)
        if start_t and end_t:
            start_fmt = start_t.strftime("%I:%M %p").lstrip("0")
            end_fmt = end_t.strftime("%I:%M %p").lstrip("0")
            time_strings.append(f"{start_fmt} - {end_fmt}")
    if not time_strings:
        single_pattern = r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))'
        singles = re.findall(single_pattern, text, re.IGNORECASE)
        for s in singles:
            t = parse(s)
            if t:
                end = (datetime.combine(datetime.today(), t) + timedelta(hours=1)).time()
                start_fmt = t.strftime("%I:%M %p").lstrip("0")
                end_fmt = end.strftime("%I:%M %p").lstrip("0")
                time_strings.append(f"{start_fmt} - {end_fmt}")
    unique = list(dict.fromkeys(time_strings))
    return unique[:3] if unique else [""]

def get_location_candidates(text):
    """Extract location details (address, room, building, venue)."""
    candidates = []
    
    # Pattern 1: Explicit location indicators
    patterns = [
        r'(?i)(?:location|venue|room|address|where|place|at)\s*[:.]?\s*([^\n]+)',
        r'(?i)(?:in|at)\s+([^\n,]+(?:street|st|ave|avenue|blvd|road|rd|building|room|suite|floor|hall|center|centre|theater|theatre|campus|nyc|new york))',
        # Room numbers
        r'(?i)(?:room|suite|floor|office)\s*[:.]?\s*([^\n]+)',
        # Building names
        r'(?i)([A-Z][a-zA-Z]+\s+(?:building|tower|plaza|center|centre|hall|house))',
        # Full address with numbers
        r'(\d{1,5}\s+[A-Za-z]+\s+(?:street|st|ave|avenue|road|rd|blvd|boulevard|drive|dr|lane|ln|way|plaza|square))',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            loc = m.strip()
            if len(loc) > 2 and len(loc) < 100:
                # Clean up
                loc = re.sub(r'\s+', ' ', loc)
                candidates.append(loc)
    
    # Also get any line that contains "in" or "at" and a place name
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines:
        lower = line.lower()
        if re.search(r'\b(in|at)\s+[a-z]', lower) and len(line.split()) < 15:
            # Skip if it looks like a time
            if not re.search(r'\d{1,2}:\d{2}', line):
                candidates.append(line)
    
    # Remove duplicates and limit to 3
    unique = list(dict.fromkeys(candidates))
    return unique[:3] if unique else [""]

# --- Page Config ---
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="wide")

# --- Session State ---
if 'show_mapping' not in st.session_state:
    st.session_state.show_mapping = False
if 'event_text' not in st.session_state:
    st.session_state.event_text = ""
if 'final_title' not in st.session_state:
    st.session_state.final_title = ""
if 'final_organization' not in st.session_state:
    st.session_state.final_organization = ""
if 'final_date' not in st.session_state:
    st.session_state.final_date = datetime.today().date()
if 'final_start' not in st.session_state:
    st.session_state.final_start = time(9, 0)
if 'final_end' not in st.session_state:
    st.session_state.final_end = time(10, 0)
if 'final_location' not in st.session_state:
    st.session_state.final_location = ""

def clear_all():
    st.session_state.show_mapping = False
    st.session_state.event_text = ""
    st.session_state.final_title = ""
    st.session_state.final_organization = ""
    st.session_state.final_date = datetime.today().date()
    st.session_state.final_start = time(9, 0)
    st.session_state.final_end = time(10, 0)
    st.session_state.final_location = ""

# --- MAIN LAYOUT ---
st.title("📅 Compact Event Parser")

col_input, col_form = st.columns([1, 1.3], gap="small")

with col_input:
    st.markdown("### 📝 Enter Event Details")
    raw_text = st.text_area(
        "Paste your event text here",
        value=st.session_state.event_text,
        height=180,
        placeholder="e.g. Acme Corp Quarterly Meeting at 2pm in Conference Room 101"
    )
    if raw_text != st.session_state.event_text:
        st.session_state.event_text = raw_text
        if raw_text.strip():
            st.session_state.show_mapping = True
        else:
            st.session_state.show_mapping = False

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Re‑extract", use_container_width=True):
            if st.session_state.event_text.strip():
                st.session_state.show_mapping = True
            else:
                st.warning("Please paste some text first.")
    with c2:
        if st.button("🗑️ Clear / Reset", use_container_width=True):
            clear_all()

with col_form:
    if st.session_state.show_mapping and st.session_state.event_text.strip():
        text = st.session_state.event_text

        # --- Get candidates ---
        title_candidates = get_title_candidates(text)
        org_candidates = get_organization_candidates(text)
        date_candidates = get_date_candidates(text)
        time_candidates = get_time_candidates(text)
        location_candidates = get_location_candidates(text)

        # Set default best (first candidate) if available, else empty
        best_title = title_candidates[0] if title_candidates and title_candidates[0] else ""
        best_org = org_candidates[0] if org_candidates and org_candidates[0] else ""
        best_date_str = date_candidates[0] if date_candidates and date_candidates[0] else ""
        best_time_str = time_candidates[0] if time_candidates and time_candidates[0] else ""
        best_location = location_candidates[0] if location_candidates and location_candidates[0] else ""

        # Parse best date into date object
        if best_date_str:
            try:
                best_date_obj = datetime.strptime(best_date_str, "%B %d, %Y").date()
            except:
                best_date_obj = datetime.today().date()
        else:
            best_date_obj = datetime.today().date()

        # Parse best time range into start/end
        if best_time_str:
            parts = re.split(r'\s*-\s*', best_time_str)
            if len(parts) == 2:
                def parse_time_str(t):
                    for fmt in ("%I:%M %p", "%I%p"):
                        try:
                            return datetime.strptime(t.replace(" ", "").upper(), fmt).time()
                        except:
                            continue
                    return None
                start_t = parse_time_str(parts[0])
                end_t = parse_time_str(parts[1])
                if start_t and end_t:
                    best_start = start_t
                    best_end = end_t
                else:
                    best_start = time(9, 0)
                    best_end = time(10, 0)
            else:
                best_start = time(9, 0)
                best_end = time(10, 0)
        else:
            best_start = time(9, 0)
            best_end = time(10, 0)

        # Update session state with these bests (if not already set)
        if best_title and not st.session_state.final_title:
            st.session_state.final_title = best_title
        if best_org and not st.session_state.final_organization:
            st.session_state.final_organization = best_org
        if best_location and not st.session_state.final_location:
            st.session_state.final_location = best_location

        st.markdown("### 📝 Verify & Map Details")
        manual_opt = "Other (Manual Entry)"

        # --- TITLE ---
        title_options = title_candidates + [manual_opt]
        if st.session_state.final_title in title_candidates:
            title_idx = title_candidates.index(st.session_state.final_title)
        else:
            title_idx = len(title_candidates)
        title_sel = st.selectbox(
            "Event Name",
            title_options,
            index=title_idx,
            key="title_select"
        )
        if title_sel == manual_opt:
            final_title = st.text_input("Event Name (manual)", value=st.session_state.final_title)
        else:
            final_title = title_sel
        st.session_state.final_title = final_title

        # --- ORGANIZATION (NEW!) ---
        org_options = org_candidates + [manual_opt]
        if st.session_state.final_organization in org_candidates:
            org_idx = org_candidates.index(st.session_state.final_organization)
        else:
            org_idx = len(org_candidates)
        org_sel = st.selectbox(
            "Organization / Host",
            org_options,
            index=org_idx,
            key="org_select"
        )
        if org_sel == manual_opt:
            final_organization = st.text_input("Organization (manual)", value=st.session_state.final_organization)
        else:
            final_organization = org_sel
        st.session_state.final_organization = final_organization

        # --- DATE ---
        date_options = date_candidates + [manual_opt]
        current_date_str = st.session_state.final_date.strftime("%B %d, %Y")
        if current_date_str in date_candidates:
            date_idx = date_candidates.index(current_date_str)
        else:
            date_idx = len(date_candidates)
        date_sel = st.selectbox(
            "Date",
            date_options,
            index=date_idx,
            key="date_select"
        )
        if date_sel == manual_opt:
            final_date = st.date_input("Date (manual)", value=st.session_state.final_date)
        else:
            try:
                final_date = datetime.strptime(date_sel, "%B %d, %Y").date()
            except:
                final_date = datetime.today().date()
        st.session_state.final_date = final_date

        # --- TIME ---
        time_options = time_candidates + [manual_opt]
        def format_time_range(start, end):
            return f"{start.strftime('%I:%M %p').lstrip('0')} - {end.strftime('%I:%M %p').lstrip('0')}"
        current_time_str = format_time_range(st.session_state.final_start, st.session_state.final_end)
        if current_time_str in time_candidates:
            time_idx = time_candidates.index(current_time_str)
        else:
            time_idx = len(time_candidates)
        time_sel = st.selectbox(
            "Time Range",
            time_options,
            index=time_idx,
            key="time_select"
        )
        if time_sel == manual_opt:
            st.markdown("**Adjust times manually**")
            def compact_time_picker(label, default_time, key_prefix):
                hour_12 = default_time.hour % 12
                if hour_12 == 0: hour_12 = 12
                minute = default_time.minute
                am_pm = "AM" if default_time.hour < 12 else "PM"
                cols = st.columns([1, 1, 1, 0.2])
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
                hour_24 = hour if am_pm == "AM" else hour + 12
                if hour_24 == 12 and am_pm == "AM":
                    hour_24 = 0
                if hour_24 == 24:
                    hour_24 = 12
                return time(hour_24, int(minute))
            time_col1, time_col2 = st.columns(2)
            with time_col1:
                final_start = compact_time_picker("Start", st.session_state.final_start, "manual_start")
            with time_col2:
                final_end = compact_time_picker("End", st.session_state.final_end, "manual_end")
        else:
            parts = re.split(r'\s*-\s*', time_sel)
            if len(parts) == 2:
                def parse_time_str(t):
                    for fmt in ("%I:%M %p", "%I%p"):
                        try:
                            return datetime.strptime(t.replace(" ", "").upper(), fmt).time()
                        except:
                            continue
                    return None
                start_t = parse_time_str(parts[0])
                end_t = parse_time_str(parts[1])
                if start_t and end_t:
                    final_start = start_t
                    final_end = end_t
                else:
                    final_start = st.session_state.final_start
                    final_end = st.session_state.final_end
            else:
                final_start = st.session_state.final_start
                final_end = st.session_state.final_end
        st.session_state.final_start = final_start
        st.session_state.final_end = final_end

        # --- LOCATION (IMPROVED!) ---
        location_options = location_candidates + [manual_opt]
        if st.session_state.final_location in location_candidates:
            loc_idx = location_candidates.index(st.session_state.final_location)
        else:
            loc_idx = len(location_candidates)
        loc_sel = st.selectbox(
            "Location",
            location_options,
            index=loc_idx,
            key="location_select"
        )
        if loc_sel == manual_opt:
            final_location = st.text_input("Location (manual)", value=st.session_state.final_location)
        else:
            final_location = loc_sel
        st.session_state.final_location = final_location

        # --- NOTES (optional) ---
        final_desc = st.text_area("Event Notes (optional)", value=text, height=68)

        # --- GENERATE LINK ---
        if st.button("✅ Generate Link", use_container_width=True):
            # Combine title and organization for the calendar title
            calendar_title = final_title
            if final_organization and final_organization not in final_title:
                calendar_title = f"{final_title} ({final_organization})"
            
            base_cal_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
            encoded_title = quote(calendar_title)
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
