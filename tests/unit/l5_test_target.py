import os
def f():
    try: os.getsize(__file__)
    except: pass
    return 42
