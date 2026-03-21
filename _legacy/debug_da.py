from aps_integration.aps_auth import get_aps_token
from aps_integration.da_manager import run_workitem
import traceback

print("--- INITIALIZING DEBUG SCENARIO ---")
token = get_aps_token()
print("Token acquired.")

try:
    # We just want to see if Autodesk accepts the ActivityID and payload structure
    run_workitem(token, "https://developer.api.autodesk.com/", "https://developer.api.autodesk.com/")
except Exception as e:
    print("Caught Exception!")
    traceback.print_exc()
