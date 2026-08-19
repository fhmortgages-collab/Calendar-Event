import streamlit as st
import re
from datetime import datetime
from urllib.parse import quote

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="centered")

st.title("📅 Local Event Text Parser & Calendar Sync")
st.markdown("Paste your event details below to accurately extract the title, date, and exact time window.")

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
                
                # 1. Title is the first line
                title = lines[0] if lines else "Untitled Event"
                
                # 2. Extract Date (e.g., "September 09, 2026")
                date_str = ""
                date_match = re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', raw_text, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1).replace(",", "")

                # 3. Target the exact start and end time range (e.g., 9:15 AM - 9:30 AM)
                start_time_str, end_time_str = "", ""
                time_range_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\s*-\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', raw_text, re.IGNORECASE)
                if time_range_match:
                    start_time_str = time_range_match.group(1)
                    end_time_str = time_range_match.group(2)

                # 4. Extract Location ONLY if explicitly preceded by "at"
                location = ""
                location_match = re.search(r'\bat\s+([^,\n]+(?:,[^,\n]+)*)', raw_text, re.IGNORECASE)
                if location_match:
                    location = location_match.group(1).strip()

                st.success("Successfully extracted details!")
                
                # Display Preview Metrics
                st.markdown("### Event Preview")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Event Title", title)
                    st.metric("Time", f"{start_time_str} - {end_time_str}" if start_time_str else "Not specified")
                with col2:
                    st.metric("Date", date_str if date_str else "Not specified")
                    st.metric("Location", location if location else "None provided")
                
                # Build Google Calendar URL
                base_cal_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
                encoded_title = quote(title)
                encoded_location = quote(location) if location else ""
                
                # Format dates and times into local GCal format (YYYYMMDDTHHMMSS) without 'Z'
                dates_param = ""
                if date_str and start_time_str and end_time_str:
                    try:
                        parsed_date = datetime.strptime(date_str, "%B %d %Y")
                    except:
                        try:
                            parsed_date = datetime.strptime(date_str, "%b %d %Y")
                        except:
                            parsed_date = None
                            
                    if parsed_date:
                        date_formatted = parsed_date.strftime("%Y%m%d")
                        
                        start_dt = datetime.strptime(start_time_str.upper(), "%I:%M %p")
                        end_dt = datetime.strptime(end_time_str.upper(), "%I:%M %p")
                        
                        start_formatted = start_dt.strftime("%H%M%S")
                        end_formatted = end_dt.strftime("%H%M%S")
                        
                        # Local time formatting (omitting 'Z' so GCal keeps local time)
                        dates_param = f"&dates={date_formatted}T{start_formatted}/{date_formatted}T{end_formatted}"

                final_calendar_url = f"{base_cal_url}&text={encoded_title}"
                if encoded_location:
                    final_calendar_url += f"&location={encoded_location}"
                if dates_param:
                    final_calendar_url += dates_param
                
                st.markdown("---")
                st.markdown("### 🚀 Add to Your Calendar")
                st.markdown(f'<a href="{final_calendar_url}" target="_blank"><button style="background-color:#1a73e8;color:white;padding:10px 20px;border:none;border-radius:4px;cursor:pointer;font-size:16px;">📅 Open in Google Calendar</button></a>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"An error occurred during processing: {str(e)}")
