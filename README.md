# Solstice Events Check-In

This is a simple event check-in  built for Solstice Events.

The project started with a synchronous badge-printing flow, but after the Day 4 pivot it was changed to an asynchronous system using a simulated message queue and webhook confirmation.

## How It Works

When an attendee checks in:

1. The attendee ID is verified.
2. A badge print job is added to the queue.
3. The attendee is shown as `PENDING`.
4. The simulated printer completes the job.
5. A signed webhook is sent back to the application.
6. The webhook is verified.
7. The attendee becomes `CHECKED_IN`.

The system also prevents duplicate badge printing while an attendee is pending or already checked in.

## Test Attendees

- `ATT-001` - Maya Chen
- `ATT-002` - Daniel Okafor
- `ATT-003` - Sofia Laurent

The attendee IDs represent the values that would normally be read from the attendees' QR codes. QR scanning is simulated by manually entering the ID.

## QR Code

Each attendee has a QR code linked to their unique attendee ID.

For this prototype, the attendee ID is entered manually first. Once the attendee is found, their QR code is displayed on the screen.

For example:

- `ATT-001` → Maya Chen
- `ATT-002` → Daniel Okafor
- `ATT-003` → Sofia Laurent

The QR code contains the attendee's ID and represents the QR code that would be used for the attendee at the event.

## Run the Project

Install the requirements:

```powershell
pip install -r requirements.txt
```

Run the application:

```powershell
python app.py
```

Then open the local Flask address in your browser.

## Pivot Changes

The original flow was:

Check In → Call Printer → Wait → CHECKED_IN


After the pivot:

Check In → Queue → PENDING → Webhook → CHECKED_IN


The new version includes webhook verification, duplicate protection, unique print job IDs, and support for print jobs completing out of order.

## Note

The message queue and badge printer are simulated for this prototype. Attendee data is also stored in memory, so restarting the server resets the check-in statuses.