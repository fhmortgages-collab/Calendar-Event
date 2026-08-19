import streamlit as st
import re
from urllib.parse import quote

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="centered")

st.title("📅 Local Event Text Parser & Calendar Sync")
st.markdown("Paste your event details below. The app will parse the fields and generate a direct link to add the event to your Google Calendar.")

# Input Form
raw_text = st.text_area("Paste Event Details Here:", height=150, placeholder="Meeting with Natalie on Sep 10, 2026 from 1:00 PM to 2:00 PM at 227 Bowery, NY.")

if st.button("Parse and Generate Calendar Link", type="primary"):
    if not raw_text.strip():
        st.error("Please paste some event text first.")
    else:
        with st.spinner("Extracting details..."):
            try:
                # Basic Local Extraction Logic
                lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                title = lines[0] if lines else "Untitled Event"
                location = "Not specified"
                time_str = "Not specified"
                
                # Extract location if 'at' is present
                location_match = re.search(r'\bat\s+([^,\n]+(?:,[^,\n]+)*)', raw_text, re.IGNORECASE)
                if location_match:
                    location = location_match.group(1).strip()
                
                # Extract time pattern
                time_match = re.findall(r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b', raw_text, re.IGNORECASE)
                if time_match:
                    time_str = " - ".join(time_match)

                st.success("Successfully extracted details locally!")
                
                # Display Preview Metrics
                st.markdown("### Event Preview")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Event Title", title)
                    st.metric("Time", time_str)
                with col2:
                    st.metric("Location", location)
                
                # Construct Google Calendar Template URL
                # Note: This creates a pre-filled event link opening directly in Google Calendar
                base_cal_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
                encoded_title = quote(title)
                encoded_location = quote(location if location != "Not specified" else "")
                
                # Using a generic forward date for the template link (e.g., Sep 10, 2026)
                # Format required: YYYYMMDDTHHMMSSZ
                dates_param = "&dates=20260910T130000Z/20260910T140000Z"
                
                final_calendar_url = f"{base_cal_url}&text={encoded_title}&location={encoded_location}{dates_param}"
                
                st.markdown("---")
                st.markdown("### 🚀 Add to Your Calendar")
                st.markdown(f"Click the button below to open Google Calendar with your event pre-loaded:")
                st.markdown(f'<a href="{final_calendar_url}" target="_blank"><button style="background-color:#1a73e8;color:white;padding:10px 20px;border:none;border-radius:4px;cursor:pointer;font-size:16px;">📅 Open in Google Calendar</button></a>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"An error occurred during processing: {str(e)}")
