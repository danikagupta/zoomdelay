import streamlit as st
skip_meetings=st.secrets['skip_meetings']
skip_meetings_list = skip_meetings.strip().splitlines()

skip_users=st.secrets['skip_users']
skip_users_list = skip_users.strip().splitlines()