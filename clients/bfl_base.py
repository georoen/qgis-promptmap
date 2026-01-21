"""
Base client for BFL (Black Forest Labs) API.
"""

import time
import logging
from typing import Dict, Any, Optional

class BFLAPIClient:
    """Base class for BFL API communication."""
    
    def __init__(self, api_key: str, endpoint: str, poll_endpoint: str = "https://api.eu.bfl.ai/v1/get_result"):
        self.api_key = api_key
        self.endpoint = endpoint
        self.poll_endpoint = poll_endpoint

    def post_and_poll(self, payload: Dict[str, Any], feedback) -> Dict[str, Any]:
        """Sends a request and polls for the result."""
        try: import requests
        except ImportError: return {"success": False, "error": "Python 'requests' library not found."}

        def log(msg):
            if feedback: feedback.pushInfo(msg)

        # 1. Send Request
        log(f"🚀 Sending request to {self.endpoint.split('/')[-1]}...")
        try:
            # BFL uses 'x-key' header
            headers = {
                'x-key': self.api_key,
                'accept': 'application/json',
                'Content-Type': 'application/json'
            }
            response = requests.post(
                self.endpoint, 
                json=payload, 
                headers=headers, 
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            task_id = result.get("id")
            polling_url = result.get("polling_url") or f"{self.poll_endpoint}?id={task_id}"
            log(f"✅ Request accepted. Task ID: {task_id}")
        except Exception as e:
            return {"success": False, "error": f"API Request failed: {e}"}

        # 2. Poll for Result
        log("⏳ Waiting for processing...")
        start_time = time.time()
        while time.time() - start_time < 600: # 10 minutes timeout
            if feedback and feedback.isCanceled(): 
                return {"success": False, "error": "Canceled."}
            
            try:
                poll_resp = requests.get(polling_url, headers={'x-key': self.api_key}, timeout=30)
                poll_data = poll_resp.json()
                status = poll_data.get("status")
                
                if status == "Ready":
                    log("✨ Processing complete!")
                    # Result structure might vary, but usually it's in result -> sample
                    if "result" in poll_data and "sample" in poll_data["result"]:
                        return {"success": True, "url": poll_data["result"]["sample"]}
                    else:
                        # Fallback or specific handling could be added here
                        return {"success": True, "data": poll_data["result"]} 
                        
                elif status == "Failed":
                    return {"success": False, "error": f"API Error: {poll_data.get('message')}"}
                elif status == "Request Moderated":
                     return {"success": False, "error": f"Request Moderated: {poll_data.get('message')}"}
                
                time.sleep(1)
            except Exception as e:
                # log(f"Polling error: {e}") # Optional: log polling errors
                time.sleep(2)
                
        return {"success": False, "error": "Timeout."}
