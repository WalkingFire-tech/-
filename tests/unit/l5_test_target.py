import os
def f():
    try: os.getsize(__file__)
    except Exception: pass
    return 42
