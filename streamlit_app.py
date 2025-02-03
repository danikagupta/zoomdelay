import streamlit as st
import datetime
import pandas as pd

from zoom_integration import get_meeting_ids, get_attendee_details
from skip_lists import skip_meetings_list, skip_users_list

if 'time_gap' not in st.session_state:
    st.session_state['time_gap']=1*60

if 'key' not in st.session_state:
    st.session_state['key']=1234


def ui_get_dates():
    """
    Creates the UI for selecting start and end dates.

    Returns:
        Tuple of start_date_str and end_date_str in YYYY-MM-DD format.
    """
    today = datetime.date.today()
    one_week_ago = today - datetime.timedelta(days=7)

    start_date = st.sidebar.date_input("Start Date", value=one_week_ago)
    end_date = st.sidebar.date_input("End Date", value=today)
    if time_gap:=st.sidebar.text_input("Allowed time gap in seconds",value=st.session_state.get("time_gap","")):
        st.session_state["time_gap"]=int(time_gap)
    if key:=st.sidebar.text_input("Enter the key",value=st.session_state.get("key","")):
        st.session_state["key"]=key
    
    #st.write(f"Time gap is {st.session_state['time_gap']}")
    #st.write(f"Key is {st.session_state['key']}")
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

# Streamlit UI
st.title("Zoom Meeting & Attendee Report")
progress_bar = st.progress(0)
status_text = st.empty()

start_date_str, end_date_str = ui_get_dates()

if st.sidebar.button("Get Zoom Meetings & Attendees"):
    space1, space2 = st.sidebar.empty(), st.sidebar.empty()
    if st.session_state.get("key","")==st.secrets['key']:
        meetings = get_meeting_ids(start_date_str, end_date_str)
        with st.expander("Meetings"):
            st.dataframe(meetings)
    else:
        st.write(f"Sorry - your key {st.session_state.get('key','')} is not correct")
        meetings=None

    if meetings:
        all_attendee_data = []
        total_count = len(meetings)+1
        for idx,meeting in enumerate(meetings):
            progress_bar.progress(idx/total_count)
            status_text.text(f"Progress: {round(100*idx/total_count)}%")
            if meeting["topic"] in skip_meetings_list:
                space1.write(f"Skipping Topic: {meeting['topic']}")
                continue
            attendees = get_attendee_details(meeting["id"], meeting["topic"], meeting["actual_start_time"],st.session_state['time_gap'],space2)
            all_attendee_data.extend(attendees)

        progress_bar.progress(100)
        status_text.text(f"Completed!")
        
        if all_attendee_data:
            df = pd.DataFrame(all_attendee_data)
            st.sidebar.success(f"Retrieved {len(df)} attendee records!")
            st.dataframe(df)
        else:
            st.warning("No attendee data found.")
    else:
        st.warning("No meetings found in the selected date range.")
