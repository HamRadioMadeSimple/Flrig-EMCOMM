"""A pretend flrig for testing without a radio.

Run it by itself:  python tests/fake_flrig.py   then start the app; it connects to this
instead of a real radio. The tests also use it."""
import threading
from xmlrpc.server import SimpleXMLRPCServer

state = {"vfo": "7115000", "mode": "USB-D", "bw": "3000"}
calls = []


def start(port=12345):
    srv = SimpleXMLRPCServer(("127.0.0.1", port), logRequests=False, allow_none=True)

    def reg(name, fn):
        srv.register_function(lambda *a: (calls.append((name, a)), fn(*a))[1], name)
    reg("rig.get_vfo", lambda: state["vfo"])
    reg("rig.get_mode", lambda: state["mode"])
    reg("rig.get_bw", lambda: [state["bw"], ""])
    reg("rig.get_xcvr", lambda: "IC-7300")
    reg("rig.get_modes", lambda: ["LSB", "USB", "AM", "FM", "CW", "LSB-D", "USB-D"])
    reg("rig.set_vfo", lambda f: state.update(vfo=str(int(f))) or 0)
    reg("rig.set_mode", lambda m: state.update(mode=m) or 0)
    reg("rig.set_bandwidth", lambda b: state.update(bw=str(b)) or 0)
    reg("rig.tune", lambda *a: 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    start()
    input("Pretend flrig running on 127.0.0.1:12345. Press Enter to stop.\n")
