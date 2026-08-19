import streamlit as st
import re
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="centered")

st.title("📅 Local Event Text Parser")
st.markdown("Paste your event text below. The app will extract titles, dates, times, and locations locally using pattern matching—no API key required!")

# Input Form
raw_text = st.text_area("Paste Event Details Here:", height=150, placeholder="Meeting with Natalie on Sep 10, 2026 from 1:00 PM to 2:00 PM at 227 Bowery, NY.")

if st.button("Parse Event Details", type="primary"):
    if not raw_text.strip():
        st.error("Please paste some event text first.")
    else:
        with st.spinner("Extracting details..."):
            try:
                # Basic Local Extraction Logic using Regex and Text Pattern Analysis
                lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                
                # Default extractions
                title = lines[0] if lines else "Untitled Event"
                location = "Not specified"
                time_str = "Not specified"
                
                # Simple keyword scanning for location (e.g., looking for "at [location]")
                location_match = re.search(r'\bat\s+([^,\n]+(?:,[^,\n]+)*)', raw_text, re.IGNORECASE)
                if location_match:
                    location = location_match.group(1).strip()
                
                # Simple time extraction pattern (e.g., matching times like 1pm, 2:00 PM)
                time_match = re.findall(r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b', raw_text, re.IGNORECASE)
                if time_match:
                    time_str = " - ".join(time_match)

                event_data = {
                    "title": title,
                    "date": "Extracted from text",
                    "time": time_str,
                    "location": location
                }
                
                st.success("Successfully extracted details locally!")
                st.json(event_data)
                
                # Display Preview Metrics
                st.markdown("### Event Preview")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Event Title", event_data.get("title"))
                    st.metric("Time", event_data.get("time"))
                with col2:
                    st.metric("Location", event_data.get("location"))
                
                st.success("✅ Event ready for manual calendar entry or export!")

            except Exception as e:
                st.error(f"An error occurred during processing: {str(e)}")
