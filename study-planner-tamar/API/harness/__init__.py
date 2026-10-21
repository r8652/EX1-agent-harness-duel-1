import os

VERBOSE = True


# Prints a runtime action tagged with the harness file that performed it
def log(source, message):
    if VERBOSE:
        print(f"[{os.path.basename(source)}] {message}", flush=True)
