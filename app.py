from flask import Flask, render_template, request, jsonify

import uuid
import hmac
import hashlib
import json
import urllib.request


app = Flask(__name__)


# --------------------------------------------------
# ATTENDEES
# --------------------------------------------------

attendees = {
    "ATT-001": {
        "name": "Maya Chen",
        "status": "NOT_CHECKED_IN"
    },

    "ATT-002": {
        "name": "Daniel Okafor",
        "status": "NOT_CHECKED_IN"
    },

    "ATT-003": {
        "name": "Sofia Laurent",
        "status": "NOT_CHECKED_IN"
    }
}


# --------------------------------------------------
# QUEUE AND JOB STORAGE
# --------------------------------------------------

# Simulated message queue
print_queue = []

# Connects a job ID to an attendee ID
jobs = {}

# Secret used to sign and verify webhooks
SECRET = b"my-webhook-secret"


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# CHECK IN
# --------------------------------------------------

@app.route("/check-in", methods=["POST"])
def check_in():

    data = request.get_json()

    attendee_id = data.get("attendeeId")


    # Check that attendee exists
    if attendee_id not in attendees:

        return jsonify({
            "success": False,
            "message": "Attendee not found."
        }), 404


    attendee = attendees[attendee_id]


    # --------------------------------------------------
    # DUPLICATE PROTECTION
    # --------------------------------------------------

    # Do not create another badge if:
    #
    # 1. A print job is already pending
    # OR
    # 2. The attendee is already checked in

    if attendee["status"] in ["PENDING", "CHECKED_IN"]:

        return jsonify({
            "success": False,
            "name": attendee["name"],
            "status": attendee["status"],
            "message": (
                f'{attendee["name"]} already has a '
                'check-in in progress or completed.'
            )
        }), 409


    # --------------------------------------------------
    # CREATE PRINT JOB
    # --------------------------------------------------

    job_id = str(uuid.uuid4())


    print_job = {
        "jobId": job_id,
        "attendeeId": attendee_id,
        "name": attendee["name"]
    }


    # --------------------------------------------------
    # ADD JOB TO MESSAGE QUEUE
    # --------------------------------------------------

    print_queue.append(print_job)


    # Remember who owns this job
    jobs[job_id] = attendee_id


    # Attendee is NOT checked in yet.
    #
    # We are waiting for printer confirmation.

    attendee["status"] = "PENDING"
    attendee["jobId"] = job_id


    return jsonify({
        "success": True,
        "name": attendee["name"],
        "status": "PENDING",
        "jobId": job_id,
        "message": "Badge print request queued."
    }), 202


# --------------------------------------------------
# PROCESS NEXT PRINT JOB
# --------------------------------------------------

@app.route("/process-next-job", methods=["POST"])
def process_next_job():

    if not print_queue:

        return jsonify({
            "message": "No print jobs waiting."
        }), 200


    # Take the FIRST waiting job
    job = print_queue.pop(0)


    # Create printer completion message
    payload = {
        "jobId": job["jobId"],
        "status": "COMPLETED"
    }


    # Convert JSON to bytes
    body = json.dumps(payload).encode("utf-8")


    # --------------------------------------------------
    # SIGN THE WEBHOOK
    # --------------------------------------------------

    signature = hmac.new(
        SECRET,
        body,
        hashlib.sha256
    ).hexdigest()


    # --------------------------------------------------
    # SEND WEBHOOK
    # --------------------------------------------------

    webhook_request = urllib.request.Request(
        "http://127.0.0.1:5000/webhook",
        data=body,
        method="POST"
    )


    webhook_request.add_header(
        "Content-Type",
        "application/json"
    )


    webhook_request.add_header(
        "X-Signature",
        signature
    )


    try:

        with urllib.request.urlopen(
            webhook_request
        ) as response:

            webhook_response = (
                response
                .read()
                .decode()
            )


        return jsonify({
            "message": "Printer completed job and sent webhook.",
            "job": job,
            "webhookResponse": webhook_response
        }), 200


    except Exception as error:

        return jsonify({
            "message": "Printer finished, but webhook delivery failed.",
            "error": str(error)
        }), 500


# ==================================================
# NEW: PROCESS A SPECIFIC JOB
# ==================================================
#
# This route allows us to demonstrate that
# confirmations can arrive OUT OF ORDER.
#
# Example:
#
# Maya scans first
# Daniel scans second
#
# But we can process Daniel's job FIRST.
#
# ==================================================

@app.route("/process-job/<job_id>", methods=["POST"])
def process_specific_job(job_id):

    # Look for the requested job
    job = None


    for queued_job in print_queue:

        if queued_job["jobId"] == job_id:

            job = queued_job
            break


    # --------------------------------------------------
    # JOB NOT FOUND
    # --------------------------------------------------

    if job is None:

        return jsonify({
            "message": "Print job not found in queue."
        }), 404


    # Remove ONLY this particular job
    # from the queue.

    print_queue.remove(job)


    # --------------------------------------------------
    # CREATE COMPLETION MESSAGE
    # --------------------------------------------------

    payload = {
        "jobId": job["jobId"],
        "status": "COMPLETED"
    }


    body = json.dumps(payload).encode("utf-8")


    # --------------------------------------------------
    # SIGN THE WEBHOOK
    # --------------------------------------------------

    signature = hmac.new(
        SECRET,
        body,
        hashlib.sha256
    ).hexdigest()


    # --------------------------------------------------
    # CREATE WEBHOOK REQUEST
    # --------------------------------------------------

    webhook_request = urllib.request.Request(
        "http://127.0.0.1:5000/webhook",
        data=body,
        method="POST"
    )


    webhook_request.add_header(
        "Content-Type",
        "application/json"
    )


    webhook_request.add_header(
        "X-Signature",
        signature
    )


    # --------------------------------------------------
    # SEND WEBHOOK
    # --------------------------------------------------

    try:

        with urllib.request.urlopen(
            webhook_request
        ) as response:

            webhook_response = (
                response
                .read()
                .decode()
            )


        return jsonify({
            "message": "Specific print job completed.",
            "job": job,
            "webhookResponse": webhook_response
        }), 200


    except Exception as error:

        return jsonify({
            "message": "Webhook delivery failed.",
            "error": str(error)
        }), 500


# ==================================================
# NEW: VIEW CURRENT PRINT QUEUE
# ==================================================

@app.route("/queue", methods=["GET"])
def get_queue():

    return jsonify(print_queue), 200


# --------------------------------------------------
# WEBHOOK
# --------------------------------------------------

@app.route("/webhook", methods=["POST"])
def webhook():

    # Get the EXACT request body.
    #
    # This is important because the signature
    # was calculated using these exact bytes.

    raw_body = request.get_data()


    # Get signature sent by printer

    received_signature = request.headers.get(
        "X-Signature"
    )


    # Calculate the signature ourselves

    expected_signature = hmac.new(
        SECRET,
        raw_body,
        hashlib.sha256
    ).hexdigest()


    # --------------------------------------------------
    # VERIFY SIGNATURE
    # --------------------------------------------------

    if received_signature != expected_signature:

        return jsonify({
            "error": "Invalid signature"
        }), 401


    # --------------------------------------------------
    # READ WEBHOOK DATA
    # --------------------------------------------------

    data = request.get_json()


    job_id = data.get("jobId")

    status = data.get("status")


    # --------------------------------------------------
    # CHECK THAT JOB EXISTS
    # --------------------------------------------------

    if job_id not in jobs:

        return jsonify({
            "error": "Unknown print job"
        }), 404


    # Find attendee belonging to this job

    attendee_id = jobs[job_id]

    attendee = attendees[attendee_id]


    # --------------------------------------------------
    # PRINTER CONFIRMED COMPLETION
    # --------------------------------------------------

    if status == "COMPLETED":

        attendee["status"] = "CHECKED_IN"


        return jsonify({
            "message": "Webhook verified.",
            "attendeeId": attendee_id,
            "name": attendee["name"],
            "status": attendee["status"]
        }), 200


    return jsonify({
        "message": "Webhook received, but job is not completed."
    }), 200


# --------------------------------------------------
# GET ONE ATTENDEE
# --------------------------------------------------

@app.route("/attendees/<attendee_id>", methods=["GET"])
def get_attendee(attendee_id):

    if attendee_id not in attendees:

        return jsonify({
            "message": "Attendee not found."
        }), 404


    return jsonify(
        attendees[attendee_id]
    ), 200


# --------------------------------------------------
# GET ALL ATTENDEES
# --------------------------------------------------

@app.route("/attendees", methods=["GET"])
def get_attendees():

    return jsonify(attendees)


# --------------------------------------------------
# START APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    app.run(debug=True)