import base64
from typing import Tuple, Union

import requests
import streamlit as st

from typing import List, TypedDict, Union, Dict, Any
import json

from datetime import datetime, timedelta

from skip_lists import skip_users_list


ZOOM_TOKEN_ENDPOINT = "https://zoom.us/oauth/token"
ZOOM_API_V2_BASE_URL = "https://api.zoom.us/v2/"


def get_acceess_token(client_id: str, client_secret: str) -> Tuple[str, int]:
    data = {
        "grant_type": "account_credentials",
        "account_id": st.secrets['AID'],
    }

    encoded_auth_header = base64.b64encode(
        f"{client_id}:{client_secret}".encode("utf-8")
    ).decode("utf-8")

    headers = {"Host": "zoom.us", "Authorization": f"Basic {encoded_auth_header}"}

    response = requests.post(ZOOM_TOKEN_ENDPOINT, data=data, headers=headers)
    parsed_reponse = response.json()

    access_token = parsed_reponse["access_token"]
    expiry = parsed_reponse["expires_in"]

    return access_token, expiry


def create_authorized_header():
    access_token, _ = get_acceess_token(st.secrets['CID'], st.secrets['CSE'])
    headers = {"Authorization": f"Bearer {access_token}"}
    headers["Content-Type"] = "application/json"
    return headers

def get_meeting_details(meeting_id):
    """
    Fetches detailed meeting information, including the scheduled start time.
    
    Args:
        meeting_id (int): Zoom Meeting ID.
    
    Returns:
        Dict with scheduled start time, actual start time, and topic.
    """
    meeting_url = ZOOM_API_V2_BASE_URL + f"meetings/{meeting_id}"
    zoom_auth_header = create_authorized_header()
    response = requests.get(meeting_url, headers=zoom_auth_header)

    if response.status_code == 200:
        meeting = response.json()
        return {
            "id": meeting["id"],
            "topic": meeting["topic"],
            "scheduled_start_time": meeting.get("start_time", "N/A"),  # This is the scheduled start time
            "actual_start_time": None  # Will be updated from Reports API
        }
    else:
        st.sidebar.error(f"Error fetching scheduled start time for meeting {meeting_id}: {response.text}")
        return None

def get_meeting_ids_one_user(user_id,start_date, end_date):
    meetings_url = ZOOM_API_V2_BASE_URL+f"users/{user_id}/meetings?from={start_date}&to={end_date}"
    meetings_url = ZOOM_API_V2_BASE_URL+f"report/meetings?from={start_date}&to={end_date}&page_size=300"
    meetings_url = ZOOM_API_V2_BASE_URL+f"report/users/{user_id}/meetings?from={start_date}&to={end_date}&page_size=300"
    zoom_auth_header = create_authorized_header()
    response = requests.get(meetings_url, headers=zoom_auth_header)

    if response.status_code == 200:
        meetings = response.json().get("meetings", [])
        meeting_data = []

        for m in meetings:
            meeting_id = m["id"]
            actual_start_time = m["start_time"]  # Actual start time from Reports API

            # Fetch scheduled start time
            meeting_details = get_meeting_details(meeting_id)
            if meeting_details:
                meeting_details["actual_start_time"] = actual_start_time
                meeting_data.append(meeting_details)

        return meeting_data

        #return [{"id": m["id"], "topic": m["topic"], "start_time": m["start_time"]} for m in meetings]
    else:
        st.error(f"Error fetching meetings: {response.status_code} - {response.text} for {meetings_url=}")
        return []
    
def get_meeting_ids(start_date, end_date):
    user_ids= [
        '14FZQXqLRSODS33uQTVVaw',
        '5uBBBmxkRs2ULd5cfs8Adw',
        'atAAAIDOQYqcONrWd0oxxg',
        'dZ6K_rnJTOO5S-jOUpXf3w',
        'di6QjKDzTA-BsECJM-lqDA',
        'j4IclWA4ScOUmP_grnbflg',
    ]
    return_list=[]
    for u in user_ids:
        new_list=get_meeting_ids_one_user(u,start_date, end_date)
        return_list.extend(new_list)
    return return_list

def round_to_nearest_30_min(dt):
    minutes = dt.minute
    if minutes < 15:
        rounded_dt = dt.replace(minute=0, second=0, microsecond=0)
    elif minutes < 45:
        rounded_dt = dt.replace(minute=30, second=0, microsecond=0)
    else:
        rounded_dt = (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return rounded_dt
    

def get_attendee_details(meeting_id, topic, start_time,time_gap,space2):
    """
    Fetches attendee details for a given meeting ID.

    Args:
        meeting_id (int): The Zoom meeting ID.
        topic (str): The meeting topic.
        start_time (str): The meeting start time.

    Returns:
        List of dictionaries with attendee details.
    """
    participants_url = ZOOM_API_V2_BASE_URL+f"report/meetings/{meeting_id}/participants?page_size=300"
    zoom_auth_header = create_authorized_header()
    response = requests.get(participants_url, headers=zoom_auth_header)

    if response.status_code == 200:
        participants = response.json().get("participants", [])
        try:
            start_time_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            st.error(f"Invalid start_time format for meeting {meeting_id}: {start_time}")
            return []

        filtered_participants = []

        for p in participants:
            if p.get("name","Unknown") in skip_users_list:
                space2.write(f"Skipping User: {p['name']}")
                continue
            join_time_str = p.get("join_time", None)
            if join_time_str:
                try:
                    join_time_dt = datetime.strptime(join_time_str, "%Y-%m-%dT%H:%M:%SZ")
                    rounded_start_time_dt = round_to_nearest_30_min(start_time_dt) 
                    time_difference = (join_time_dt - rounded_start_time_dt).total_seconds()
                    
                    if time_difference > time_gap:
                        filtered_participants.append({
                            "Meeting ID": meeting_id,
                            "Meeting Topic": topic,
                            "Meeting Start Time": start_time,
                            "Participant Name": p.get("name", "N/A"),
                            "Participant Email": p.get("user_email", "N/A"),
                            "Join Time": join_time_str,
                            "Leave Time": p.get("leave_time", "N/A"),
                            "Late": time_difference,
                            "Duration": p.get("duration", 0)
                        })
                except ValueError:
                    st.warning(f"Skipping participant with invalid join_time format: {join_time_str}")

        return filtered_participants
    else:
        st.error(f"Failed to get participants for meeting {meeting_id}: {response.text}")
        return []



def list_meetings(
    user_id: str,
    meeting_type: str,
    next_page_token: Union[str, None] = None,
    from_date: Union[str, None] = None,
    to_date: Union[str, None] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    list_meetings_url = ZOOM_API_V2_BASE_URL + f"users/{user_id}/meetings"

    zoom_auth_header = create_authorized_header()

    params = {
        "type": meeting_type,
        "next_page_token": next_page_token,
        "page_size": page_size,
        "from": from_date,
        "to": to_date,
    }

    response = requests.get(list_meetings_url, params=params, headers=zoom_auth_header)
    meetings = response.json()

    return meetings

def get_next_page_token(
    user_id: str,
    meeting_type: str,
    next_page_tokens: Union[None, Dict[str, Dict[str, str]]],
) -> Union[str, None]:
    next_page_token = None

    if user_id and meeting_type and next_page_tokens:
        # next_page_tokens = json.load(next_page_tokens)
        next_page_token = next_page_tokens[user_id][meeting_type]

    return next_page_token

def get_schedules():
    next_page_tokens=None
    meeting_types = ["upcoming"]
    user_ids= [
        '14FZQXqLRSODS33uQTVVaw',
        '5uBBBmxkRs2ULd5cfs8Adw',
        'atAAAIDOQYqcONrWd0oxxg',
        'dZ6K_rnJTOO5S-jOUpXf3w',
        'di6QjKDzTA-BsECJM-lqDA',
        'j4IclWA4ScOUmP_grnbflg',
    ]

    limit = 300
    page_size=250

    try:
        all_meetings = {}
        new_next_page_tokens = {}
        for user_id in user_ids:
            all_meetings[user_id] = {}
            new_next_page_tokens[user_id] = {}

            for meeting_type in meeting_types:
                next_page_token = get_next_page_token(
                    user_id, meeting_type, next_page_tokens
                )

                # Fetch a chunk of meetings
                response = list_meetings(
                    user_id,
                    meeting_type,
                    next_page_token=next_page_token,
                    from_date=None,
                    to_date=None,
                    page_size=page_size,
                )
                #print(response)

                if "meetings" not in response:
                    message = (
                        "Cannot fetch the zoom meetings! Error: " + response["message"]
                    )
                    print(message)
                    st.write(f"Error: {message}")
                    return 

                if not next_page_tokens or (next_page_tokens and next_page_token):
                    meetings = response["meetings"]
                    new_next_page_token = response["next_page_token"]

                else:
                    meetings = []
                    new_next_page_token = ""

                total_records = response["total_records"]

                all_meetings[user_id][meeting_type] = {}
                all_meetings[user_id][meeting_type]["sessions"] = meetings
                all_meetings[user_id][meeting_type]["total_sessions"] = total_records
                new_next_page_tokens[user_id][meeting_type] = new_next_page_token

        data = {"meetings": all_meetings, "nextPageTokens": new_next_page_tokens}
        #st.sidebar.dataframe(data)
        return data

    except Exception as e:
        message = "Cannot fetch the zoom meetings!"
        print(message, " Error: ", str(e))
        st.write(message, " Error: ", str(e))