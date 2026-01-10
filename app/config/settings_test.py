from .settings import *

for handler_name in ["app_file", "access_file", "error_file"]:
    if handler_name in LOGGING["handlers"]:
        LOGGING["handlers"][handler_name] = {
            "class": "logging.NullHandler",
        }

# Reduce console noise during tests
LOGGING["handlers"]["console"]["level"] = "ERROR"