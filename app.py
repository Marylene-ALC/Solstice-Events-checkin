from flask import Flask, render_template, request, jsonify
import uuid
import hmac
import hashlib


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


    


    job_id = str(uuid.uuid4())


    print_job = {
        "jobId": job_id,
        "attendeeId": attendee_id,
        "name": attendee["name"]
    }


    print_queue.append(print_job)

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


    
    job = print_queue.pop(0)


    
    return jsonify({
        "message": "Printer processed job.",
        "job": job
    }), 200




@app.route("/attendees", methods=["GET"])
def get_attendees():

    return jsonify(attendees)




if __name__ == "__main__":
    app.run(debug=True)