import streamlit as st
import re
from datetime import datetime, time, timedelta
from urllib.parse import quote
import json
import google.generativeai as genai

# --- Page Configuration ---
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="wide")

# --- Session State ---
if 'show_mapping' not in st.session_state:
    st.session_state.show_mapping = False
if 'event_text' not in st.session_state:
    st.session_state.event_text = ""
if 'ai_parsed' not in st.session_state:
    st.session_state.ai_parsed = None  # Will store dict from AI
if 'api_key_valid' not in st.session_state:
    st.session_state.api_key_valid = True

def clear_all():
    st.session_state.show_mapping = False
    st.session_state.event_text = ""
    st.session_state.ai_parsed = None

# --- AI Setup ---
# Try to configure Gemini using secrets; if not available, show warning
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
except Exception as e:
    st.session_state.api_key_valid = False
    model = None

def parse_with_ai(text):
    """Send text to Gemini AI and return structured JSON."""
    if not model or not st.session_state.api_key_valid:
        return None

    prompt = f"""
You are an expert calendar assistant. Extract event details from the following text.
Return ONLY a valid JSON object with these exact keys:
- "title" (string)
- "date" (string in YYYY-MM-DD format)
- "start_time" (string in HH:MM AM/PM format, e.g. "02:30 PM")
- "end_time" (string in HH:MM AM/PM format)
- "location" (string)

If a piece of information is missing, use an empty string "".

Text:
{text}
"""
    try:
        response = model.generate_content(prompt)
        # Extract JSON from response (might be wrapped in markdown)
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return json.loads(json_str)
    except Exception as e:
        st.error(f"AI parsing error: {e}")
        return None

# --- Helper: parse time string from AI ---
def parse_time_from_ai(t_str):
    if not t_str:
        return None
    t_str = t_str.strip().upper()
    for fmt in ("%I:%M %p", "%I%p", "%I:%M%p"):
        try:
            return datetime.strptime(t_str.replace(" ", ""), fmt).time()
        except:
            continue
    return None

# --- Helper: date from AI ---
def parse_date_from_ai(d_str):
    if not d_str:
        return None
    try:
        return datetime.strptime(d_str, "%Y-%m-%d").date()
    except:
        return None

# --- MAIN LAYOUT ---
st.title("📅 Compact Event Parser")

if not st.session_state.api_key_valid:
    st.warning("⚠️ Gemini API key not set. Please add it to Streamlit secrets (`GEMINI_API_KEY`) or use the manual fallback below.")

col_input, col_form = st.columns([1, 1.3], gap="small")

with col_input:
    st.markdown("### 📝 Enter Event Details")
    raw_text = st.text_area(
        "Paste your event text here",
        value=st.session_state.event_text,
        height=180,
        placeholder="e.g. Meeting on Friday at 2pm, Room 101 ..."
    )
    if raw_text != st.session_state.event_text:
        st.session_state.event_text = raw_text
        # Clear AI parsed when text changes
        st.session_state.ai_parsed = None

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 Extract with AI", use_container_width=True, type="primary"):
            if st.session_state.event_text.strip():
                with st.spinner("🧠 AI is thinking..."):
                    parsed = parse_with_ai(st.session_state.event_text)
                    if parsed:
                        st.session_state.ai_parsed = parsed
                        st.session_state.show_mapping = True
                    else:
                        st.warning("AI parsing failed. Please fill in manually.")
                        # Fallback: use rule-based extraction (we'll keep it as fallback)
                        st.session_state.ai_parsed = None
                        st.session_state.show_mapping = True
            else:
                st.warning("Please paste some text first.")
    with c2:
        if st.button("🗑️ Clear / Reset", use_container_width=True):
            clear_all()

    # Auto-show if text exists (for manual mode)
    if st.session_state.event_text.strip() and not st.session_state.show_mapping:
        st.session_state.show_mapping = True

with col_form:
    if st.session_state.show_mapping and st.session_state.event_text.strip():
        text = st.session_state.event_text

        # --- Get best guesses: AI first, then fallback to rule-based ---
        if st.session_state.ai_parsed:
            ai = st.session_state.ai_parsed
            best_title = ai.get('title', '')
            best_date = parse_date_from_ai(ai.get('date', ''))
            best_start = parse_time_from_ai(ai.get('start_time', ''))
            best_end = parse_time_from_ai(ai.get('end_time', ''))
            best_location = ai.get('location', '')
        else:
            # Rule-based fallback (kept from before)
            best_title = extract_title(text)
            best_date = extract_date(text)
            best_start, best_end = extract_time_range(text)
            best_location = extract_location(text)

        # If still missing, set defaults
        today = datetime.today().date()
        if best_date is None:
            best_date = today
        if best_start is None:
            best_start = time(9, 0)
        if best_end is None:
            best_end = time(10, 0)

        st.markdown("### 📝 Verify & Map Details")

        # --- ROW 1: EVENT NAME ---
        final_title = st.text_input("Event Name", value=best_title)

        # --- ROW 2: DATE ---
        final_date = st.date_input("Date", value=best_date)

        # --- ROW 3: TIME (COMPACT PICKER) ---
        st.markdown("**Event Time**")
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
            final_start = compact_time_picker("Start", best_start, "start")
        with time_col2:
            final_end = compact_time_picker("End", best_end, "end")

        # --- ROW 4: LOCATION ---
        final_location = st.text_input("Location", value=best_location)

        # --- ROW 5: NOTES (optional) ---
        final_desc = st.text_area("Event Notes (optional)", value=text, height=68)

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

# --- Rule-based fallback functions (copied from previous) ---
def extract_title(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines:
        lower = line.lower()
        if re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|mon|tue|wed|thu|fri|sat|sun)', lower):
            continue
        if re.search(r'\d{1,2}:\d{2}\s*(am|pm)', lower):
            continue
        if re.search(r'(location|venue|room|building|street|ave|blvd)', lower):
            continue
        if len(line.split()) > 12:
            continue
        return line
    return lines[0] if lines else ""

def extract_date(text):
    today = datetime.today().date()
    year = today.year
    patterns = [
        r'(?i)(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})?',
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*,?\s*(\d{4})?',
        r'(\d{1,2})/(\d{1,2})/(\d{2,4})',
        r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})',
        r'(?i)(tomorrow|next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday))'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                if groups[0].isalpha():
                    month_str = groups[0]
                    day = int(groups[1])
                    yr = int(groups[2]) if groups[2] else year
                    month = datetime.strptime(month_str[:3], "%b").month
                    try: return datetime(yr, month, day).date()
                    except: pass
                elif groups[1].isalpha():
                    day = int(groups[0])
                    month_str = groups[1]
                    yr = int(groups[2]) if groups[2] else year
                    month = datetime.strptime(month_str[:3], "%b").month
                    try: return datetime(yr, month, day).date()
                    except: pass
                else:
                    a, b, c = int(groups[0]), int(groups[1]), int(groups[2])
                    if c < 100: c += 2000 if c < 70 else 1900
                    if a <= 12 and b <= 31:
                        try: return datetime(c, a, b).date()
                        except: pass
                    if b <= 12 and a <= 31:
                        try: return datetime(c, b, a).date()
                        except: pass
            elif len(groups) == 1:
                keyword = groups[0].lower()
                if keyword == 'tomorrow':
                    return today + timedelta(days=1)
                if keyword.startswith('next '):
                    day_name = keyword.split()[1]
                    days = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
                    target = days.index(day_name)
                    today_weekday = today.weekday()
                    diff = target - today_weekday
                    if diff <= 0: diff += 7
                    return today + timedelta(days=diff)
    return None

def extract_time_range(text):
    match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))', text, re.IGNORECASE)
    if match:
        def parse(t_str):
            for fmt in ("%I:%M%p", "%I%p"):
                try:
                    return datetime.strptime(t_str.replace(" ", "").upper(), fmt).time()
                except: continue
            return None
        start = parse(match.group(1))
        end = parse(match.group(2))
        if start and end: return start, end
    match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))', text, re.IGNORECASE)
    if match:
        t = parse(match.group(1))
        if t:
            end = (datetime.combine(datetime.today(), t) + timedelta(hours=1)).time()
            return t, end
    return None, None

def extract_location(text):
    patterns = [
        r'(?i)(?:location|venue|room|address|where|place)\s*[:.]?\s*([^\n]+)',
        r'(?i)at\s+([^\n,]+(?:street|st|ave|avenue|blvd|road|rd|building|room|suite|floor|nyc|new york))',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            loc = match.group(1).strip()
            if len(loc) > 2: return loc
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines:
        lower = line.lower()
        if re.search(r'\b(in|at)\s+[a-z]', lower) and len(line.split()) < 15:
            return line
    return ""
