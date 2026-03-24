from messenger import send_message, send_buttons, get_user_profile, send_typing_on
from database import (
    get_or_create_contact,
    get_contact_by_psid,
    add_tag,
    remove_tag,
    get_tags_for_contact,
    get_tournament_by_keyword,
    get_active_tournaments,
    register_contact_to_tournament,
    log_message,
)


def handle_message(sender_psid, message):
    """Handle incoming message from a user."""
    send_typing_on(sender_psid)

    # Get or create contact
    profile = get_user_profile(sender_psid)
    first_name = profile.get("first_name", "Amico")
    last_name = profile.get("last_name", "")
    contact_id = get_or_create_contact(sender_psid, first_name, last_name)

    # Log incoming message
    message_text = message.get("text", "")
    log_message(contact_id, "incoming", message_text)

    # Check if it's a keyword for a tournament
    keyword = message_text.strip().upper()
    tournament = get_tournament_by_keyword(keyword)

    if tournament:
        handle_tournament_keyword(sender_psid, contact_id, first_name, tournament)
        return

    # Check for common keywords
    tags = get_tags_for_contact(contact_id)

    if "nuovo_contatto" in tags and not any(
        t.startswith("interacted") for t in tags
    ):
        handle_welcome(sender_psid, contact_id, first_name)
    else:
        handle_default(sender_psid, first_name)


def handle_postback(sender_psid, postback):
    """Handle button clicks (postbacks)."""
    send_typing_on(sender_psid)

    profile = get_user_profile(sender_psid)
    first_name = profile.get("first_name", "Amico")
    last_name = profile.get("last_name", "")
    contact_id = get_or_create_contact(sender_psid, first_name, last_name)

    payload = postback.get("payload", "")
    log_message(contact_id, "postback", payload)

    if payload == "GET_STARTED":
        handle_welcome(sender_psid, contact_id, first_name)

    elif payload == "PROSSIMI_TORNEI":
        handle_next_tournaments(sender_psid, contact_id, first_name)

    elif payload == "PRIMO_TORNEO":
        handle_first_tournament(sender_psid, contact_id, first_name)

    elif payload == "DOVE_SIAMO":
        handle_location(sender_psid, contact_id)

    elif payload.startswith("ISCRIVI_"):
        tournament_id = int(payload.replace("ISCRIVI_", ""))
        handle_registration(sender_psid, contact_id, first_name, tournament_id)

    elif payload.startswith("INDECISO_"):
        tournament_id = int(payload.replace("INDECISO_", ""))
        handle_undecided(sender_psid, contact_id, first_name, tournament_id)

    elif payload == "NOTIFICA_TUTTI":
        add_tag(contact_id, "notifica_tutti_tornei")
        msg = "Perfetto! Ti avviseremo per ogni torneo in programma."
        send_message(sender_psid, msg)
        log_message(contact_id, "outgoing", msg)

    elif payload == "NOTIFICA_GRANDI":
        add_tag(contact_id, "notifica_eventi_speciali")
        msg = "OK! Ti avviseremo solo per gli eventi speciali."
        send_message(sender_psid, msg)
        log_message(contact_id, "outgoing", msg)

    elif payload == "DOMANDA":
        msg = (
            "Scrivi pure la tua domanda qui in chat.\n"
            "Un membro del nostro staff ti risponderà entro pochi minuti."
        )
        send_message(sender_psid, msg)
        log_message(contact_id, "outgoing", msg)


def handle_welcome(sender_psid, contact_id, first_name):
    """Welcome message for new contacts."""
    add_tag(contact_id, "interacted")

    text = (
        f"Benvenuto su Prestige Events, {first_name}!\n\n"
        "Da oltre 13 anni organizziamo tornei di poker "
        "nella provincia di Prato.\n"
        "900mq dedicati al gioco, strutture professionali, "
        "staff preparato.\n\n"
        "Cosa ti interessa?"
    )

    buttons = [
        {"type": "postback", "title": "Prossimi tornei", "payload": "PROSSIMI_TORNEI"},
        {"type": "postback", "title": "Il mio primo torneo", "payload": "PRIMO_TORNEO"},
        {"type": "postback", "title": "Dove siamo", "payload": "DOVE_SIAMO"},
    ]

    send_buttons(sender_psid, text, buttons)
    log_message(contact_id, "outgoing", text)


def handle_tournament_keyword(sender_psid, contact_id, first_name, tournament):
    """Handle when user sends a tournament keyword."""
    register_contact_to_tournament(contact_id, tournament["id"], "interested")
    add_tag(contact_id, f"interesse_torneo_{tournament['id']}")

    text = (
        f"Ciao {first_name}!\n\n"
        f"Ecco i dettagli del torneo:\n\n"
        f"🏆 {tournament['name']}\n"
        f"📅 {tournament['date']} alle {tournament['time']}\n"
        f"💰 Buy-in: {tournament['buyin']}"
    )

    if tournament["reentry"]:
        text += f" | Re-entry: {tournament['reentry']}"
    if tournament["guaranteed"]:
        text += f"\n👥 Garantito: {tournament['guaranteed']}"
    if tournament["blinds"]:
        text += f"\n⏱ Blinds: {tournament['blinds']} minuti"

    text += "\n📍 Prestige Events — Prato\n\nVuoi iscriverti?"

    buttons = [
        {
            "type": "postback",
            "title": "Si, mi iscrivo",
            "payload": f"ISCRIVI_{tournament['id']}",
        },
        {
            "type": "postback",
            "title": "Ho una domanda",
            "payload": "DOMANDA",
        },
        {
            "type": "postback",
            "title": "Ci penso",
            "payload": f"INDECISO_{tournament['id']}",
        },
    ]

    send_buttons(sender_psid, text, buttons)
    log_message(contact_id, "outgoing", text)


def handle_registration(sender_psid, contact_id, first_name, tournament_id):
    """Handle tournament registration."""
    register_contact_to_tournament(contact_id, tournament_id, "registered")
    add_tag(contact_id, f"iscritto_torneo_{tournament_id}")
    remove_tag(contact_id, f"interesse_torneo_{tournament_id}")

    msg = (
        f"Perfetto {first_name}!\n\n"
        "Per confermare il tuo posto:\n"
        "📞 Chiama/WhatsApp il numero della room\n\n"
        "Ti invieremo un promemoria 24h prima del torneo.\n\n"
        "A presto! 🎯"
    )
    send_message(sender_psid, msg)
    log_message(contact_id, "outgoing", msg)


def handle_undecided(sender_psid, contact_id, first_name, tournament_id):
    """Handle undecided user."""
    register_contact_to_tournament(contact_id, tournament_id, "undecided")
    add_tag(contact_id, f"indeciso_torneo_{tournament_id}")

    msg = (
        f"Nessun problema {first_name}!\n"
        "Ti mandiamo un promemoria 48h prima "
        "nel caso cambiassi idea."
    )
    send_message(sender_psid, msg)
    log_message(contact_id, "outgoing", msg)


def handle_next_tournaments(sender_psid, contact_id, first_name):
    """Show next active tournaments."""
    tournaments = get_active_tournaments()

    if not tournaments:
        msg = (
            f"{first_name}, al momento non ci sono tornei in programma.\n"
            "Vuoi essere avvisato quando ne pubblichiamo uno?"
        )
        buttons = [
            {"type": "postback", "title": "Si, avvisami", "payload": "NOTIFICA_TUTTI"},
            {"type": "postback", "title": "Solo eventi grandi", "payload": "NOTIFICA_GRANDI"},
        ]
        send_buttons(sender_psid, msg, buttons)
    else:
        for t in tournaments[:3]:  # Max 3 tournaments
            text = (
                f"🏆 {t['name']}\n"
                f"📅 {t['date']} alle {t['time']}\n"
                f"💰 Buy-in: {t['buyin']}"
            )
            if t["guaranteed"]:
                text += f"\n👥 Garantito: {t['guaranteed']}"

            buttons = [
                {
                    "type": "postback",
                    "title": "Mi iscrivo",
                    "payload": f"ISCRIVI_{t['id']}",
                },
                {
                    "type": "postback",
                    "title": "Info",
                    "payload": "DOMANDA",
                },
            ]
            send_buttons(sender_psid, text, buttons)

    log_message(contact_id, "outgoing", "Lista tornei inviata")


def handle_first_tournament(sender_psid, contact_id, first_name):
    """Info for first-time players."""
    add_tag(contact_id, "nuovo_giocatore")

    msg = (
        f"Ottima scelta {first_name}!\n\n"
        "Da noi trovi:\n"
        "✅ Staff disponibile a spiegarti tutto\n"
        "✅ Tornei adatti a ogni livello\n"
        "✅ Un ambiente serio e accogliente\n\n"
        "Non serve esperienza. Il nostro staff ti guiderà "
        "in ogni fase del torneo.\n\n"
        "Vuoi vedere i prossimi tornei?"
    )

    buttons = [
        {"type": "postback", "title": "Prossimi tornei", "payload": "PROSSIMI_TORNEI"},
        {"type": "postback", "title": "Ho una domanda", "payload": "DOMANDA"},
    ]

    send_buttons(sender_psid, msg, buttons)
    log_message(contact_id, "outgoing", msg)


def handle_location(sender_psid, contact_id):
    """Send location info."""
    msg = (
        "📍 Prestige Events\n"
        "Provincia di Prato, Toscana\n\n"
        "Per indicazioni e orari, scrivici qui in chat "
        "o chiamaci al numero della room."
    )
    send_message(sender_psid, msg)
    log_message(contact_id, "outgoing", msg)


def handle_default(sender_psid, first_name):
    """Default response for unrecognized messages."""
    text = (
        f"Ciao {first_name}!\n"
        "Come posso aiutarti?"
    )
    buttons = [
        {"type": "postback", "title": "Prossimi tornei", "payload": "PROSSIMI_TORNEI"},
        {"type": "postback", "title": "Il mio primo torneo", "payload": "PRIMO_TORNEO"},
        {"type": "postback", "title": "Dove siamo", "payload": "DOVE_SIAMO"},
    ]
    send_buttons(sender_psid, text, buttons)
