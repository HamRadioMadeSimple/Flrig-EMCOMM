"""Talking to flrig over XML-RPC."""

import logging
import threading
import xmlrpc.client

log = logging.getLogger(__name__)


# ==========================================================================
# flrig XML-RPC client
# ==========================================================================
class TimeoutTransport(xmlrpc.client.Transport):
    def __init__(self, timeout=2.0):
        super().__init__()
        self.timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self.timeout
        return conn


class Flrig:
    def __init__(self, host, port):
        self.lock = threading.Lock()
        self.xcvr = None
        self.set_address(host, port)

    def set_address(self, host, port):
        with self.lock:
            self.url = f"http://{host}:{port}/RPC2"
            self.proxy = xmlrpc.client.ServerProxy(
                self.url, transport=TimeoutTransport(2.0), allow_none=True)
            self.xcvr = None

    def call(self, method, *args):
        with self.lock:
            return getattr(self.proxy, method)(*args)

    def tune(self, freq_hz, mode=None, bw=None):
        """Mode first (it can reset the filter), then bandwidth, then frequency."""
        warnings = []
        if mode:
            try:
                self.call("rig.set_mode", mode)
            except Exception as ex:
                warnings.append(f"mode {mode} not accepted ({ex})")
        if bw:
            try:
                self.call("rig.set_bandwidth", int(bw))
            except Exception as ex:
                warnings.append(f"bandwidth {bw} not accepted ({ex})")
        self.call("rig.set_vfo", float(freq_hz))
        return warnings

    def atu_tune(self):
        """Start the rig's antenna tuner, same as flrig's Tune button."""
        try:
            self.call("rig.tune")
            return
        except xmlrpc.client.Fault as ex:
            fault = ex
        # Explain clearly if this flrig build doesn't offer the command
        try:
            methods = [m for m in self.call("system.listMethods") if "tune" in m.lower()]
        except Exception:
            methods = []
        hint = f" flrig offers: {', '.join(methods)}" if methods else ""
        raise RuntimeError(f"flrig refused the tune command ({fault.faultString}).{hint}")

    def status(self):
        st = {"freq": int(float(self.call("rig.get_vfo")))}
        try:
            st["mode"] = str(self.call("rig.get_mode"))
        except Exception:
            st["mode"] = ""
        try:
            bw = self.call("rig.get_bw")
            st["bw"] = str(bw[0]) if isinstance(bw, (list, tuple)) and bw else str(bw)
        except Exception:
            st["bw"] = ""
        if self.xcvr is None:
            try:
                self.xcvr = str(self.call("rig.get_xcvr"))
            except Exception:
                self.xcvr = ""
            try:
                st["modes"] = [str(m) for m in self.call("rig.get_modes")]
            except Exception:
                log.debug("Optional step skipped", exc_info=True)
        st["xcvr"] = self.xcvr
        return st
