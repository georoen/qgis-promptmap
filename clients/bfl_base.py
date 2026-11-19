"""Shared HTTP client for Black Forest Labs image APIs."""

import math
import time
from urllib.parse import urlsplit


def is_bfl_url(url):
    """Only contact HTTPS URLs on BFL's documented domain."""
    if not isinstance(url, str) or "\\" in url or any(c.isspace() for c in url):
        return False
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        return (parsed.scheme == "https" and parsed.username is None and parsed.password is None
                and parsed.port in (None, 443) and host.endswith(".bfl.ai"))
    except ValueError:
        return False


def valid_cost(value):
    return type(value) in (int, float) and 0 <= value < math.inf


class BFLAPIClient:
    """Submit once, then poll the result URL returned by BFL."""

    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint

    def post_and_poll(self, payload, feedback):
        try:
            import requests
        except ImportError:
            return {"success": False, "error": "Python 'requests' library not found."}

        if feedback and feedback.isCanceled():
            return {"success": False, "error": "Canceled."}
        if feedback:
            feedback.pushInfo(f"Sending request to {self.endpoint.split('/')[-1]}...")
        headers = {"x-key": self.api_key, "accept": "application/json"}
        try:
            response = requests.post(self.endpoint, json=payload, headers=headers, timeout=60, allow_redirects=False)
        except requests.RequestException:
            return {"success": False, "error": "BFL submission failed; check the connection."}
        if not 200 <= response.status_code < 300:
            message = f"BFL submission failed (HTTP {response.status_code})."
            if response.status_code == 422:
                try:
                    body = response.json()
                except ValueError:
                    body = None
                detail = body.get("detail") if isinstance(body, dict) else None
                # The server may echo the prompt or base64 image in its validation report.
                fields = set()
                if isinstance(detail, list):
                    for item in detail:
                        location = item.get("loc") if isinstance(item, dict) else None
                        if isinstance(location, list):
                            fields.update(part for part in location if isinstance(part, str) and part in payload)
                if fields:
                    message += f" Rejected fields: {', '.join(sorted(fields))}."
                else:
                    message += " BFL rejected the request parameters without identifying a field."
            return {"success": False, "error": message}
        try:
            submitted = response.json()
        except ValueError:
            return {"success": False, "error": "BFL returned an unreadable submission response."}
        polling_url = submitted.get("polling_url") if isinstance(submitted, dict) else None
        if not is_bfl_url(polling_url):
            return {"success": False, "error": "BFL did not return a trusted polling URL."}
        submitted_cost = submitted.get("cost")

        if feedback:
            feedback.pushInfo("Waiting for BFL processing...")
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            if feedback and feedback.isCanceled():
                return {"success": False, "error": "Canceled."}
            try:
                response = requests.get(polling_url, headers=headers, timeout=30, allow_redirects=False)
            except requests.RequestException:
                time.sleep(2)
                continue
            try:
                body = response.json()
            except ValueError:
                body = None
            status = body.get("status") if isinstance(body, dict) else None
            if status in ("Error", "Failed", "Request Moderated", "Content Moderated", "Task not found", "No Card Generated"):
                return {"success": False, "error": f"BFL task stopped: {status}."}
            if response.status_code == 429 or response.status_code >= 500:
                time.sleep(2)
                continue
            if not 200 <= response.status_code < 300:
                return {"success": False, "error": f"BFL polling failed (HTTP {response.status_code})."}
            if status == "Ready":
                sample = body.get("result")
                if isinstance(sample, dict) and is_bfl_url(sample.get("sample")):
                    result = {"success": True, "url": sample["sample"]}
                elif isinstance(sample, str) and sample:
                    result = {"success": True, "data": sample}
                else:
                    return {"success": False, "error": "BFL returned no usable image result."}
                settled = body.get("cost")
                if valid_cost(settled):
                    result.update(cost_credits=settled, cost_basis="settled")
                elif valid_cost(submitted_cost):
                    result.update(cost_credits=submitted_cost, cost_basis="submission")
                return result
            if status not in ("Pending", "Reasoning", "Generating"):
                return {"success": False, "error": "BFL returned an unrecognized task status."}
            time.sleep(1)
        return {"success": False, "error": "Timed out waiting for BFL. The provider may still process or charge for the request."}
