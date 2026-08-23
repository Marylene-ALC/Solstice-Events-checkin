from flask import Flask, render_template, request, jsonify
import uuid
import hmac
import hashlib
import json
import urllib.request


app = Flask(__name__)


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



print_queue = []

jobs = {}

SECRET = b"my-webhook-secret"


@app.route("/")
def home():
    return render_template("index.html")



@app.route("/check-in", methods=["POST"])
def check_in():

    data = request.get_json()
    attendee_id = data.get("attendeeId")

    if attendee_id not in attendees:

        return jsonify({
            "success": False,
            "message": "Attendee not found."
        }), 404


    attendee = attendees[attendee_id]


    # Duplicate protection
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


    # Create a unique print job
    job_id = str(uuid.uuid4())


    print_job = {
        "jobId": job_id,
        "attendeeId": attendee_id,
        "name": attendee["name"]
    }


    # Publish to our simulated message queue
    print_queue.append(print_job)


    # Remember which attendee belongs to this job
    jobs[job_id] = attendee_id


    attendee["status"] = "PENDING"
    attendee["jobId"] = job_id


    return jsonify({
        "success": True,
        "name": attendee["name"],
        "status": "PENDING",
        "jobId": job_id,
        "message": "Badge print request queued."
    }), 202


@app.route("/process-next-job", methods=["POST"])
def process_next_job():

    if not print_queue:

        return jsonify({
            "message": "No print jobs waiting."
        }), 200


    # Take the first waiting job
    job = print_queue.pop(0)



    payload = {
        "jobId": job["jobId"],
        "status": "COMPLETED"
    }


    # Convert JSON to bytes
    body = json.dumps(payload).encode("utf-8")


    # Create HMAC signature
    signature = hmac.new(
        SECRET,
        body,
        hashlib.sha256
    ).hexdigest()


    # ----------------------------------------------
    # SEND WEBHOOK BACK TO OUR OWN APP
    # ----------------------------------------------

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


# --------------------------------------------------
# WEBHOOK CALLBACK
# --------------------------------------------------

@app.route("/webhook", methods=["POST"])
def webhook():

    # Get exact request body
    raw_body = request.get_data()


    # Read the signature sent by the printer
    received_signature = request.headers.get(
        "X-Signature"
    )


    # Calculate what the signature SHOULD be
    expected_signature = hmac.new(
        SECRET,
        raw_body,
        hashlib.sha256
    ).hexdigest()


    # Reject invalid webhook
    if received_signature != expected_signature:

        return jsonify({
            "error": "Invalid signature"
        }), 401


    # Signature is valid, now read the JSON
    data = request.get_json()


    job_id = data.get("jobId")
    status = data.get("status")


    # Make sure this job actually exists
    if job_id not in jobs:

        return jsonify({
            "error": "Unknown print job"
        }), 404


    attendee_id = jobs[job_id]

    attendee = attendees[attendee_id]


    # Only mark checked in after printer confirmation
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


@app.route("/attendees/<attendee_id>", methods=["GET"])
def get_attendee(attendee_id):

    if attendee_id not in attendees:

        return jsonify({
            "message": "Attendee not found."
        }), 404


    return jsonify(
        attendees[attendee_id]
    ), 200


@app.route("/attendees", methods=["GET"])
def get_attendees():

    return jsonify(attendees)


if __name__ == "__main__":
    app.run(debug=True)