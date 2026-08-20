import streamlit as st
import re
from datetime import datetime, time, timedelta
from urllib.parse import quote
import json

# --- Try to import Gemini, but don't crash if not installed ---
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# --- Load API key securely ---
API_KEY = None
try:
    # For Streamlit Cloud (secrets)
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    # For local dev with .streamlit/secrets.toml
    try:
        import os
        API_KEY = os.getenv("GEMINI_API_KEY")
    except:
        pass

# --- Configure AI if key exists ---
model = None
if API_KEY and genai:
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        st.sidebar.success("✅ AI model ready")
    except Exception as e:
        st.sidebar.error(f"AI config error: {e}")

# --- Rule‑based fallback functions (same as before) ---
# ... (copy the functions: extract_title, extract_date, etc. from previous version) ...
# For brevity, I'll assume they are defined – in the full code they are.

# --- AI extraction function ---
def parse_with_ai(text):
    if not model:
        return None
    prompt = f"""
You are an expert calendar assistant. Extract event details from the following text.
Return ONLY a valid JSON object with these exact keys:
- "title" (string)
- "organization" (string, e.g., company name or host)
- "date" (string in YYYY-MM-DD format)
- "start_time" (string in HH:MM AM/PM format, e.g. "02:30 PM")
- "end_time" (string in HH:MM AM/PM format)
- "location" (string, full address or room)

If a piece of information is missing, use an empty string "".

Text:
{text}
"""
    try:
        response = model.generate_content(prompt)
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return json.loads(json_str)
    except Exception as e:
        st.error(f"AI error: {e}")
        return None

# --- Parsing helpers ---
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

def parse_date_from_ai(d_str):
    if not d_str:
        return None
    try:
        return datetime.strptime(d_str, "%Y-%m-%d").date()
    except:
        return None

# --- Page config ---
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="wide")

# --- Session state ---
if 'show_mapping' not in st.session_state:
    st.session_state.show_mapping = False
if 'event_text' not in st.session_state:
    st.session_state.event_text = ""
if 'ai_parsed' not in st.session_state:
    st.session_state.ai_parsed = None
if 'final_title' not in st.session_state:
    st.session_state.final_title = ""
if 'final_org' not in st.session_state:
    st.session_state.final_org = ""
if 'final_date' not in st.session_state:
    st.session_state.final_date = datetime.today().date()
if 'final_start' not in st.session_state:
    st.session_state.final_start = time(9, 0)
if 'final_end' not in st.session_state:
    st.session_state.final_end = time(10, 0)
if 'final_location' not in st.session_state:
    st.session_state.final_location = ""

def clear_all():
    for key in ['show_mapping', 'event_text', 'ai_parsed', 
                'final_title', 'final_org', 'final_date', 
                'final_start', 'final_end', 'final_location']:
        st.session_state[key] = None if key != 'show_mapping' else False
    st.session_state.event_text = ""
    st.session_state.show_mapping = False
    st.rerun()

# --- UI Layout ---
st.title("📅 Smart Event Parser (AI‑Powered)")

col_input, col_form = st.columns([1, 1.3], gap="small")

with col_input:
    st.markdown("### 📝 Enter Event Details")
    raw_text = st.text_area(
        "Paste your event text here",
        value=st.session_state.event_text,
        height=180,
        placeholder="e.g. Acme Corp Quarterly Meeting on Aug 27 at 2pm in Room 101"
    )
    if raw_text != st.session_state.event_text:
        st.session_state.event_text = raw_text
        st.session_state.ai_parsed = None
        if raw_text.strip():
            st.session_state.show_mapping = True

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Extract with AI", use_container_width=True, type="primary"):
            if st.session_state.event_text.strip():
                if model:
                    with st.spinner("🧠 AI thinking..."):
                        parsed = parse_with_ai(st.session_state.event_text)
                        if parsed:
                            st.session_state.ai_parsed = parsed
                            st.session_state.show_mapping = True
                        else:
                            st.warning("AI failed, using rule‑based fallback.")
                            st.session_state.ai_parsed = None
                            st.session_state.show_mapping = True
                else:
                    st.warning("No API key. Using rule‑based fallback.")
                    st.session_state.ai_parsed = None
                    st.session_state.show_mapping = True
            else:
                st.warning("Please paste some text.")
    with c2:
        if st.button("🗑️ Clear / Reset", use_container_width=True):
            clear_all()

    if st.session_state.event_text.strip() and not st.session_state.show_mapping:
        st.session_state.show_mapping = True

with col_form:
    if st.session_state.show_mapping and st.session_state.event_text.strip():
        text = st.session_state.event_text

        # --- Get best guesses ---
        if st.session_state.ai_parsed:
            ai = st.session_state.ai_parsed
            best_title = ai.get('title', '')
            best_org = ai.get('organization', '')
            best_date = parse_date_from_ai(ai.get('date', ''))
            best_start = parse_time_from_ai(ai.get('start_time', ''))
            best_end = parse_time_from_ai(ai.get('end_time', ''))
            best_location = ai.get('location', '')
        else:
            # rule‑based fallback
            # (you can reuse the functions from the previous version)
            best_title = extract_title(text)
            best_org = extract_organization(text)  # add if you have it
            best_date = extract_date(text)
            best_start, best_end = extract_time_range(text)
            best_location = extract_location(text)

        # Defaults
        today = datetime.today().date()
        if best_date is None:
            best_date = today
        if best_start is None:
            best_start = time(9, 0)
        if best_end is None:
            best_end = time(10, 0)

        # Update session state with bests if empty
        if best_title and not st.session_state.final_title:
            st.session_state.final_title = best_title
        if best_org and not st.session_state.final_org:
            st.session_state.final_org = best_org
        if best_location and not st.session_state.final_location:
            st.session_state.final_location = best_location

        st.markdown("### 📝 Verify & Map Details")
        manual_opt = "Other (Manual Entry)"

        # --- TITLE ---
        title_options = [best_title] if best_title else [""]
        if best_title and st.session_state.final_title != best_title:
            title_options.append(st.session_state.final_title)
        title_options.append(manual_opt)
        # Simplify: just show a text input with the best guess
        final_title = st.text_input("Event Name", value=st.session_state.final_title)
        st.session_state.final_title = final_title

        # --- ORGANIZATION ---
        org_options = [best_org] if best_org else [""]
        if best_org and st.session_state.final_org != best_org:
            org_options.append(st.session_state.final_org)
        org_options.append(manual_opt)
        final_org = st.text_input("Organization / Host", value=st.session_state.final_org)
        st.session_state.final_org = final_org

        # --- DATE ---
        final_date = st.date_input("Date", value=st.session_state.final_date)
        st.session_state.final_date = final_date

        # --- TIME (compact picker) ---
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
            final_start = compact_time_picker("Start", st.session_state.final_start, "start")
        with time_col2:
            final_end = compact_time_picker("End", st.session_state.final_end, "end")
        st.session_state.final_start = final_start
        st.session_state.final_end = final_end

        # --- LOCATION ---
        final_location = st.text_input("Location", value=st.session_state.final_location)
        st.session_state.final_location = final_location

        # --- NOTES ---
        final_desc = st.text_area("Event Notes (optional)", value=text, height=68)

        # --- Generate Link ---
        if st.button("✅ Generate Link", use_container_width=True):
            calendar_title = final_title
            if final_org and final_org not in final_title:
                calendar_title = f"{final_title} ({final_org})"
            
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
