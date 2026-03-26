import os
import hashlib
import hmac
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from database import (
    init_db,
    get_all_contacts,
    get_active_tournaments,
    create_tournament,
    get_tournament_by_id,
    get_tournament_registrations,
    get_contacts_by_tag,
    create_scheduled_message,
    add_tag,
    update_tournament,
    delete_tournament,
)
from bot_logic import handle_message, handle_postback
from messenger import send_message
from scheduler import start_scheduler
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "prestige-secret-key")

# Initialize database and scheduler at import time (works with gunicorn)
init_db()
start_scheduler()

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "prestige_events_bot_2024")
APP_SECRET = os.environ.get("APP_SECRET", "")


# --- Webhook Facebook ---

@app.route("/webhook", methods=["GET"])
def webhook_verify():
    """Facebook webhook verification."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verificato!")
        return challenge, 200
    return "Token non valido", 403


@app.route("/webhook", methods=["POST"])
def webhook_handle():
    """Handle incoming webhook events from Facebook."""
    body = request.get_json()

    if body.get("object") != "page":
        return "Not a page event", 404

    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            sender_psid = event["sender"]["id"]

            if "message" in event and "text" in event["message"]:
                handle_message(sender_psid, event["message"])

            elif "postback" in event:
                handle_postback(sender_psid, event["postback"])

    return "EVENT_RECEIVED", 200


# --- Pannello Admin ---

@app.route("/")
def dashboard():
    """Admin dashboard."""
    contacts = get_all_contacts()
    tournaments = get_active_tournaments()
    return render_template(
        "dashboard.html",
        contacts=contacts,
        tournaments=tournaments,
        total_contacts=len(contacts),
        total_tournaments=len(tournaments),
    )


@app.route("/tournaments")
def tournaments_page():
    """Tournaments management page."""
    tournaments = get_active_tournaments()
    return render_template("tournaments.html", tournaments=tournaments)


@app.route("/tournaments/new", methods=["GET", "POST"])
def new_tournament():
    """Create a new tournament."""
    if request.method == "POST":
        tournament_id = create_tournament(
            name=request.form["name"],
            date=request.form["date"],
            time=request.form["time"],
            buyin=request.form.get("buyin", ""),
            reentry=request.form.get("reentry", ""),
            guaranteed=request.form.get("guaranteed", ""),
            blinds=request.form.get("blinds", ""),
            description=request.form.get("description", ""),
            keyword=request.form.get("keyword", ""),
        )

        # Auto-create reminders
        tournament_date = datetime.strptime(
            f"{request.form['date']} {request.form['time']}", "%Y-%m-%d %H:%M"
        )

        # Reminder 48h for undecided
        reminder_48h = tournament_date - timedelta(hours=48)
        create_scheduled_message(
            tournament_id,
            f"indeciso_torneo_{tournament_id}",
            (
                "Ehi {first_name},\n\n"
                f"tra 2 giorni si gioca il {request.form['name']}.\n\n"
                "I posti stanno finendo.\n"
                "Vuoi esserci?"
            ),
            reminder_48h.strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Reminder 24h for registered
        reminder_24h = tournament_date - timedelta(hours=24)
        create_scheduled_message(
            tournament_id,
            f"iscritto_torneo_{tournament_id}",
            (
                "Ciao {first_name},\n\n"
                f"domani si gioca il {request.form['name']}!\n\n"
                f"📍 Prestige Events — Prato\n"
                f"🕐 Registrazione dalle {request.form['time']}\n\n"
                "Ricorda di portare un documento d'identità.\n"
                "Buona fortuna al tavolo!"
            ),
            reminder_24h.strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Notify subscribers
        notify_tag = "notifica_tutti_tornei"
        subscribers = get_contacts_by_tag(notify_tag)
        for contact in subscribers:
            name = contact["first_name"] or "Amico"
            msg = (
                f"Ciao {name}!\n\n"
                f"Nuovo torneo in programma:\n\n"
                f"🏆 {request.form['name']}\n"
                f"📅 {request.form['date']} alle {request.form['time']}\n"
                f"💰 Buy-in: {request.form.get('buyin', 'TBD')}\n\n"
                f"Scrivi {request.form.get('keyword', '').upper()} per i dettagli!"
            )
            send_message(contact["psid"], msg)

        flash("Torneo creato con successo!", "success")
        return redirect(url_for("tournaments_page"))

    return render_template("new_tournament.html")


@app.route("/tournaments/<int:tournament_id>")
def tournament_detail(tournament_id):
    """Tournament detail with registrations."""
    tournament = get_tournament_by_id(tournament_id)
    registrations = get_tournament_registrations(tournament_id)
    return render_template(
        "tournament_detail.html",
        tournament=tournament,
        registrations=registrations,
    )


@app.route("/tournaments/<int:tournament_id>/edit", methods=["GET", "POST"])
def edit_tournament(tournament_id):
    """Edit an existing tournament."""
    tournament = get_tournament_by_id(tournament_id)
    if not tournament:
        flash("Torneo non trovato.", "error")
        return redirect(url_for("tournaments_page"))

    if request.method == "POST":
        update_tournament(
            tournament_id,
            name=request.form["name"],
            date=request.form["date"],
            time=request.form["time"],
            buyin=request.form.get("buyin", ""),
            reentry=request.form.get("reentry", ""),
            guaranteed=request.form.get("guaranteed", ""),
            blinds=request.form.get("blinds", ""),
            description=request.form.get("description", ""),
            keyword=request.form.get("keyword", ""),
        )
        flash("Torneo aggiornato con successo!", "success")
        return redirect(url_for("tournament_detail", tournament_id=tournament_id))

    return render_template("edit_tournament.html", tournament=tournament)


@app.route("/tournaments/<int:tournament_id>/delete", methods=["POST"])
def delete_tournament_route(tournament_id):
    """Delete a tournament."""
    delete_tournament(tournament_id)
    flash("Torneo eliminato.", "success")
    return redirect(url_for("tournaments_page"))


@app.route("/contacts")
def contacts_page():
    """Contacts list."""
    contacts = get_all_contacts()
    return render_template("contacts.html", contacts=contacts)


@app.route("/send-message", methods=["POST"])
def send_message_to_tag():
    """Send a message to all contacts with a specific tag."""
    tag = request.form["tag"]
    message_text = request.form["message"]

    contacts = get_contacts_by_tag(tag)
    sent_count = 0

    for contact in contacts:
        name = contact["first_name"] or "Amico"
        personalized = message_text.replace("{first_name}", name)
        send_message(contact["psid"], personalized)
        sent_count += 1

    flash(f"Messaggio inviato a {sent_count} contatti con tag '{tag}'", "success")
    return redirect(url_for("dashboard"))


# --- Health Check ---

@app.route("/health")
def health():
    return "OK", 200


# --- Startup ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
