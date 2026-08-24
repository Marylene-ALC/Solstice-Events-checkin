from flask import Flask, render_template, request, jsonify

import uuid
import hmac
import hashlib
import json
import urllib.request
import threading
import time


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
    if attendee["status"] == "PENDING":

        return jsonify({
            "success": False,
            "name": attendee["name"],
            "status": "PENDING",
            "message": (
                f'{attendee["name"]} already has a badge print in progress.'
            )
        }), 409


    if attendee["status"] == "CHECKED_IN":

        return jsonify({
            "success": False,
            "name": attendee["name"],
            "status": "CHECKED_IN",
            "message": (
                f'{attendee["name"]} is already checked in.'
            )
        }), 409


    # Create unique print job
    job_id = str(uuid.uuid4())


    print_job = {
        "jobId": job_id,
        "attendeeId": attendee_id,
        "name": attendee["name"]
    }


    # Add job to simulated queue
    print_queue.append(print_job)


    # Remember which attendee belongs to the job
    jobs[job_id] = attendee_id


    # Important: not checked in yet
    attendee["status"] = "PENDING"
    attendee["jobId"] = job_id



    
    printer_thread = threading.Thread(
        target=simulate_printer,
        args=(job_id,)
    )

    printer_thread.daemon = True

    printer_thread.start()


    return jsonify({
        "success": True,
        "name": attendee["name"],
        "status": "PENDING",
        "jobId": job_id,
        "message": "Badge print request queued."
    }), 202



def simulate_printer(job_id):

    # Pretend the printer takes 3 seconds
    time.sleep(3)


    # Find this exact job in the queue
    job = None

    for queued_job in print_queue:

        if queued_job["jobId"] == job_id:

            job = queued_job
            break


    # It may already have been manually processed
    if job is None:
        return


    print_queue.remove(job)


    # Create completion webhook payload
    payload = {
        "jobId": job["jobId"],
        "status": "COMPLETED"
    }


    body = json.dumps(payload).encode("utf-8")


    # Create valid HMAC signature
    signature = hmac.new(
        SECRET,
        body,
        hashlib.sha256
    ).hexdigest()


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

            print(
                "Automatic printer webhook:",
                response.status
            )


    except Exception as error:

        print(
            "Automatic printer webhook failed:",
            error
        )


@app.route("/process-next-job", methods=["POST"])
def process_next_job():

    if not print_queue:

        return jsonify({
            "message": "No print jobs waiting."
        }), 200


    job = print_queue.pop(0)


    payload = {
        "jobId": job["jobId"],
        "status": "COMPLETED"
    }


    body = json.dumps(payload).encode("utf-8")


    signature = hmac.new(
        SECRET,
        body,
        hashlib.sha256
    ).hexdigest()


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
                response.read().decode()
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


@app.route("/process-job/<job_id>", methods=["POST"])
def process_specific_job(job_id):

    job = None


    for queued_job in print_queue:

        if queued_job["jobId"] == job_id:

            job = queued_job
            break


    if job is None:

        return jsonify({
            "message": "Print job not found in queue."
        }), 404


    print_queue.remove(job)


    payload = {
        "jobId": job["jobId"],
        "status": "COMPLETED"
    }


    body = json.dumps(payload).encode("utf-8")


    signature = hmac.new(
        SECRET,
        body,
        hashlib.sha256
    ).hexdigest()


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
                response.read().decode()
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


@app.route("/queue", methods=["GET"])
def get_queue():

    return jsonify(print_queue), 200


@app.route("/webhook", methods=["POST"])
def webhook():

    raw_body = request.get_data()


    received_signature = request.headers.get(
        "X-Signature"
    )


    expected_signature = hmac.new(
        SECRET,
        raw_body,
        hashlib.sha256
    ).hexdigest()


    if received_signature != expected_signature:

        return jsonify({
            "error": "Invalid signature"
        }), 401


    data = request.get_json()


    job_id = data.get("jobId")

    status = data.get("status")


    if job_id not in jobs:

        return jsonify({
            "error": "Unknown print job"
        }), 404


    attendee_id = jobs[job_id]

    attendee = attendees[attendee_id]


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

    app.run(debug=True, threaded=True)