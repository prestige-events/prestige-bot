import requests
import os

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
GRAPH_API_URL = "https://graph.facebook.com/v25.0"


def send_message(recipient_psid, message_text):
    """Send a text message to a user via Messenger."""
    url = f"{GRAPH_API_URL}/me/messages"
    payload = {
        "recipient": {"id": recipient_psid},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE",
    }
    headers = {"Content-Type": "application/json"}
    params = {"access_token": PAGE_ACCESS_TOKEN}

    response = requests.post(url, json=payload, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Errore invio messaggio: {response.status_code} - {response.text}")
    return response


def send_buttons(recipient_psid, text, buttons):
    """Send a message with buttons.

    buttons = [{"type": "postback", "title": "Testo", "payload": "PAYLOAD"}]
    """
    url = f"{GRAPH_API_URL}/me/messages"
    payload = {
        "recipient": {"id": recipient_psid},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": buttons[:3],  # Max 3 buttons
                },
            }
        },
        "messaging_type": "RESPONSE",
    }
    headers = {"Content-Type": "application/json"}
    params = {"access_token": PAGE_ACCESS_TOKEN}

    response = requests.post(url, json=payload, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Errore invio bottoni: {response.status_code} - {response.text}")
    return response


def get_user_profile(psid):
    """Get user profile info (first_name, last_name)."""
    url = f"{GRAPH_API_URL}/{psid}"
    params = {
        "fields": "first_name,last_name",
        "access_token": PAGE_ACCESS_TOKEN,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    print(f"Errore profilo utente: {response.status_code} - {response.text}")
    return {"first_name": "Amico", "last_name": ""}


def send_typing_on(recipient_psid):
    """Show typing indicator."""
    url = f"{GRAPH_API_URL}/me/messages"
    payload = {
        "recipient": {"id": recipient_psid},
        "sender_action": "typing_on",
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}
    requests.post(url, json=payload, params=params)
