import os

VERBOSE = True


def log(source, message):
    if VERBOSE:
        print(f"[{os.path.basename(source)}] {message}", flush=True)
