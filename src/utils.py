from urllib.parse import urlencode, urlparse, parse_qs
import jwt # type: ignore
from datetime import datetime, timedelta, timezone

def generate_jwt(client_id, client_secret):
    iat = datetime.now(timezone.utc)
    exp = iat + timedelta(hours=24)
    
    payload = {
        "iat": iat,
        "exp": exp,
        "appKey": client_id,
        "tokenExp": int(exp.timestamp())
    }
    
    token = jwt.encode(payload, client_secret, algorithm="HS256")
    return token


def extract_meeting_details(join_url):
    url = urlparse(join_url)
    if not url:
        print("Unable to parse join URL")
        return None, None
    
    # Extract path and split into parts
    path_parts = url.path.strip('/').split('/')
    meeting_id = None
    passcode = ""

    # Identify meeting ID
    for i, part in enumerate(path_parts):
        if part in ['j', 's', 'w'] and i + 1 < len(path_parts):
            meeting_id = path_parts[i + 1]
            break

    # Extract passcode from query parameters
    query_params = parse_qs(url.query)
    if 'pwd' in query_params:
        passcode = query_params['pwd'][0]

    return meeting_id, passcode