from flask import Flask, render_template, request, jsonify
import time

app = Flask(__name__)


# Our three test attendees
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


def print_badge_sync(attendee_id, attendee_name):
    """
    Simulates the OLD synchronous printer REST API.

    The application waits here until printing finishes.
    """

    print(f"Sending badge for {attendee_name} to printer...")

    # Simulate the printer taking 2 seconds
    time.sleep(2)

    print(f"Badge printed for {attendee_name}")

    return True


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/check-in", methods=["POST"])
def check_in():

    data = request.get_json()

    attendee_id = data.get("attendeeId")

    # Does this attendee exist?
    if attendee_id not in attendees:
        return jsonify({
            "success": False,
            "message": "Attendee not found."
        }), 404

    attendee = attendees[attendee_id]

    # Duplicate protection
    if attendee["status"] == "CHECKED_IN":
        return jsonify({
            "success": False,
            "message": f'{attendee["name"]} is already checked in.',
            "status": attendee["status"]
        }), 409

    # OLD synchronous behaviour:
    # wait until printing succeeds
    print_success = print_badge_sync(
        attendee_id,
        attendee["name"]
    )

    if print_success:
        attendee["status"] = "CHECKED_IN"

        return jsonify({
            "success": True,
            "name": attendee["name"],
            "status": attendee["status"],
            "message": "Badge printed successfully."
        }), 200

    return jsonify({
        "success": False,
        "message": "Badge printing failed."
    }), 500


@app.route("/attendees", methods=["GET"])
def get_attendees():
    return jsonify(attendees)


if __name__ == "__main__":
    app.run(debug=True)

    