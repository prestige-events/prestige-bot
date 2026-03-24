from apscheduler.schedulers.background import BackgroundScheduler
from database import (
    get_pending_scheduled_messages,
    get_contacts_by_tag,
    mark_scheduled_message_sent,
    log_message,
    get_contact_by_psid,
)
from messenger import send_message


def send_scheduled_messages():
    """Check and send any pending scheduled messages."""
    messages = get_pending_scheduled_messages()

    for msg in messages:
        contacts = get_contacts_by_tag(msg["tag"])

        for contact in contacts:
            text = msg["message_text"].replace("{first_name}", contact["first_name"] or "Amico")
            send_message(contact["psid"], text)
            log_message(contact["id"], "outgoing", f"[SCHEDULED] {text[:100]}")

        mark_scheduled_message_sent(msg["id"])
        print(f"Messaggio schedulato #{msg['id']} inviato a {len(contacts)} contatti")


def start_scheduler():
    """Start the background scheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_scheduled_messages, "interval", minutes=5)
    scheduler.start()
    print("Scheduler avviato - controlla messaggi ogni 5 minuti")
    return scheduler
