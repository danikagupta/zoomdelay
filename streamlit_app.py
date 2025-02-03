import streamlit as st
import datetime
import pandas as pd

from zoom_integration import get_meeting_ids, get_attendee_details

if 'time_gap' not in st.session_state:
    st.session_state['time_gap']=1*60

if 'key' not in st.session_state:
    st.session_state['key']=1234


skip_meetings=[
    'Ops Team Sync up',
    'Amit/Naveen_Sync up',
    'Jewel/Amit_Sync up',
    'Meeting_Amit/Sindhu/David',
    'Technology News and Updates Meeting',
    'AIClub Research Symposium 2025',
    'Rajesh/Giri/Amit',
    'Weekly Marketing Sync-up',
    'Engineering Process Discussion',
    'Sync-up_Shilpa/Lachin/Veena/Shilpi/Vani/Nischay',
    'Sync-up_Sindhu/Shilpa/Lachin/Veena/Shilpi/Vani/Nischay',
    'Sindhu/Atul',
    'Weekly Company Meeting',
    'AIClub Leadership Team Weekly Meeting',
    '',
    '',

]

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

start_date_str, end_date_str = ui_get_dates()

if st.sidebar.button("Get Zoom Meetings & Attendees"):
    if st.session_state.get("key","")==st.secrets['key']:
        meetings = get_meeting_ids(start_date_str, end_date_str)
        with st.expander("Meetings"):
            st.dataframe(meetings)
    else:
        st.write("Sorry - your key{st.session_state.get('key','')} is not correct")

    if meetings:
        all_attendee_data = []
        for meeting in meetings:
            if meeting["topic"] in skip_meetings:
                st.sidebar.write(f"Skipping {meeting['topic']}")
                continue
            attendees = get_attendee_details(meeting["id"], meeting["topic"], meeting["start_time"],st.session_state['time_gap'])
            all_attendee_data.extend(attendees)

        if all_attendee_data:
            df = pd.DataFrame(all_attendee_data)
            st.sidebar.success(f"Retrieved {len(df)} attendee records!")
            st.dataframe(df)
        else:
            st.warning("No attendee data found.")
    else:
        st.warning("No meetings found in the selected date range.")
