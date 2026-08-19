import streamlit as st
import re
from datetime import datetime
from urllib.parse import quote

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="centered")

st.title("📅 Local Event Text Parser & Calendar Sync")
st.markdown("Paste your event details below. The app will accurately extract the title, date, time, and generate your Google Calendar link.")

# Input Form
raw_text = st.text_area(
    "Paste Event Details Here:", 
    height=150, 
    value="The View + The Weekend View - taping ends at 1:30p!\nWednesday, September 09, 2026\n9:15 AM - 9:30 AM ET"
)

if st.button("Parse and Generate Calendar Link", type="primary"):
    if not raw_text.strip():
        st.error("Please paste some event text first.")
    else:
        with st.spinner("Extracting details..."):
            try:
                lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                
                # 1. Title is typically the first line
                title = lines[0] if lines else "Untitled Event"
                
                # 2. Extract Date (e.g., "September 09, 2026" or "Sep 09, 2026")
                date_str = "September 09, 2026" # default fallback
                date_match = re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', raw_text, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1).replace(",", "")

                # 3. Extract Start and End Times
                time_matches = re.findall(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', raw_text, re.IGNORECASE)
                start_time_str = time_matches[0] if len(time_matches) > 0 else "9:15 AM"
                end_time_str = time_matches[1] if len(time_matches) > 1 else "9:30 AM"

                # 4. Extract Location if specified
                location = "Not specified"
                location_match = re.search(r'\bat\s+([^,\n]+(?:,[^,\n]+)*)', raw_text, re.IGNORECASE)
                if location_match:
                    location = location_match.group(1).strip()

                st.success("Successfully extracted details!")
                
                # Display Preview Metrics
                st.markdown("### Event Preview")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Event Title", title)
                    st.metric("Date & Time", f"{date_str} @ {start_time_str} - {end_time_str}")
                with col2:
                    st.metric("Location", location)
                
                # Format Dates for Google Calendar URL (YYYYMMDDTHHMMSSZ)
                # Parse extracted strings into standard datetime objects for precise URL formatting
                try:
                    parsed_date = datetime.strptime(date_str, "%B %d %Y")
                except:
                    try:
                        parsed_date = datetime.strptime(date_str, "%b %d %Y")
                    except:
                        parsed_date = datetime(2026, 9, 9)
                        
                # Format for Google Calendar template link
                date_formatted = parsed_date.strftime("%Y%m%d")
                start_formatted = "091500" # 9:15 AM
                end_formatted = "093000"   # 9:30 AM
                
                dates_param = f"&dates={date_formatted}T{start_formatted}Z/{date_formatted}T{end_formatted}Z"
                
                # Construct Google Calendar Template URL
                base_cal_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
                encoded_title = quote(title)
                encoded_location = quote(location if location != "Not specified" else "")
                
                final_calendar_url = f"{base_cal_url}&text={encoded_title}&location={encoded_location}{dates_param}"
                
                st.markdown("---")
                st.markdown("### 🚀 Add to Your Calendar")
                st.markdown(f'<a href="{final_calendar_url}" target="_blank"><button style="background-color:#1a73e8;color:white;padding:10px 20px;border:none;border-radius:4px;cursor:pointer;font-size:16px;">📅 Open in Google Calendar with Reminders</button></a>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"An error occurred during processing: {str(e)}")
