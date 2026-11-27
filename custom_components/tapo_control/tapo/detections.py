"""Detections of a camera connected to a Tapo hub, read from the hub's detection list.

A hub keeps a list of detections for each camera connected to it
(searchDetectionList). An entry appears when its recording ends, so a
detection is seen after it happened, not while it happens.

No Home Assistant imports, so this can be tested and reused on its own.
"""

# alarm_type values seen on an H200 with a D230 doorbell
DETECTION_TYPES = {
    2: "motion",
    6: "person",
    10: "ring",
    16: "package",
}

# look back far enough to cover a long recording plus a missed poll
LOOK_BACK_SECONDS = 15 * 60
LOOK_AHEAD_SECONDS = 60


def detection_list_request(now: int) -> dict:
    """searchDetectionList request for the last LOOK_BACK_SECONDS."""
    return {
        "playback": {
            "search_detection_list": {
                "start_index": 0,
                "end_index": 99,
                "channel": 0,
                "start_time": now - LOOK_BACK_SECONDS,
                "end_time": now + LOOK_AHEAD_SECONDS,
            }
        }
    }


def detection_list(response: dict) -> list:
    """The detections in a searchDetectionList response."""
    return response["playback"]["search_detection_list"]


class DetectionTracker:
    """Remembers which detections were already reported.

    The first list only records what is there, so detections from before a
    restart are not reported again.
    """

    def __init__(self):
        self._seen = set()
        self._seeded = False

    def new_detections(self, detections: list) -> list:
        """Detections not seen before, oldest first, as dicts with
        type ("motion", "person", ... or "other"), alarm_type, start_time, end_time.
        """
        new = []
        for item in detections:
            key = (item.get("start_time"), item.get("alarm_type"))
            if key in self._seen:
                continue
            self._seen.add(key)
            if self._seeded:
                new.append(
                    {
                        "type": DETECTION_TYPES.get(item.get("alarm_type"), "other"),
                        "alarm_type": item.get("alarm_type"),
                        "start_time": item.get("start_time"),
                        "end_time": item.get("end_time"),
                    }
                )
        self._seeded = True
        self._forget_old(detections)
        new.sort(key=lambda d: d["start_time"] or 0)
        return new

    def _forget_old(self, detections: list):
        # keep only what the hub still lists, so memory stays small
        current = {(d.get("start_time"), d.get("alarm_type")) for d in detections}
        self._seen &= current
