"""Nexora desktop entry point. Source run: python desktop/launcher.py"""
import json, logging, os, re, socket, sys, threading, time, traceback, webbrowser
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
ROOT=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parents[1])).resolve()
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
STOP=threading.Event(); _STATE_LOCK=threading.RLock(); SERVER=None; THREAD=None; BOOT_THREAD=None; SOCK=None; WINDOW=None; _LOG_HANDLER=None
_HEALTH_PATH="/api/health"; _STARTUP_TIMEOUT=25.0

def _data():return Path(os.environ.get("APPDATA") or (Path.home()/"AppData"/"Roaming"))/"Nexora"
def _log_path():return _data()/"logs"/"desktop.log"
def _redact(value):
 text=str(value)
 text=re.sub(r"(?i)(authorization|access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|password)(\s*[:=]\s*)([^\s,;]+)",r"\1\2<redacted>",text)
 text=re.sub(r"(?i)([?&](?:token|key|secret|code)=)[^&\s]+",r"\1<redacted>",text)
 return text[:12000]
def _write_log(phase,message):
 line=f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} [{phase}] {_redact(message)}\n"
 try:
  path=_log_path();path.parent.mkdir(parents=True,exist_ok=True)
  with path.open("a",encoding="utf-8") as stream:stream.write(line)
 except Exception as exc:
  try:print(line.rstrip()+f"\nCould not write Nexora diagnostic log: {_redact(exc)}",file=sys.stderr)
  except Exception:pass
def _record_startup_error(phase,error):
 detail="".join(traceback.format_exception(type(error),error,error.__traceback__)) or f"{type(error).__name__}: {error}"
 _write_log(phase,detail);return f"{type(error).__name__}: {_redact(error)}"
def _configure_runtime_logging():
 global _LOG_HANDLER
 if _LOG_HANDLER is not None:return
 path=_log_path();path.parent.mkdir(parents=True,exist_ok=True);handler=logging.FileHandler(path,encoding="utf-8")
 handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s"))
 class RedactingFilter(logging.Filter):
  def filter(self,record):record.msg=_redact(record.getMessage());record.args=();return True
 handler.addFilter(RedactingFilter())
 for name in ("uvicorn.error","backend"):
  logger=logging.getLogger(name);logger.setLevel(logging.INFO);logger.addHandler(handler)
 _LOG_HANDLER=handler
def _status(message,error=False):
 if WINDOW:
  try:WINDOW.evaluate_js(f"window.setStatus({json.dumps(str(message),ensure_ascii=True)},{str(bool(error)).lower()})")
  except Exception as exc:_write_log("loading-page status update",f"{type(exc).__name__}: {exc}")
def _user_data():
 if not getattr(sys,"frozen",False):return
 data=_data();data.mkdir(parents=True,exist_ok=True);db=data/"studio.db";files=data/"files";legacy=Path(sys.executable).resolve().parent
 import shutil
 if not db.exists() and (legacy/"studio.db").is_file():shutil.copy2(legacy/"studio.db",db)
 if not files.exists() and (legacy/"files").is_dir():shutil.copytree(legacy/"files",files,dirs_exist_ok=True)
 os.environ.setdefault("STUDIO_DB",str(db));os.environ.setdefault("STUDIO_FILES",str(files))
def _probe_health(base_url):
 try:
  with urlopen(base_url.rstrip("/")+_HEALTH_PATH,timeout=1) as response:
   status=getattr(response,"status",None)
   if status is None:status=response.getcode()
   body=response.read(8192)
  if status!=200:return False,f"HTTP {status} from {_HEALTH_PATH}"
  try:payload=json.loads(body.decode("utf-8"))
  except Exception as exc:return False,f"Invalid JSON from {_HEALTH_PATH}: {type(exc).__name__}"
  if not isinstance(payload,dict) or payload.get("status")!="Ready" or payload.get("service")!="Nexora":return False,f"Unexpected {_HEALTH_PATH} payload: {payload!r}"
  return True,""
 except HTTPError as exc:return False,f"HTTP {exc.code} from {_HEALTH_PATH}"
 except URLError as exc:return False,f"{type(exc.reason).__name__}: {exc.reason}"
 except (TimeoutError,socket.timeout) as exc:return False,f"TimeoutError: {exc or 'health request timed out'}"
 except Exception as exc:return False,f"{type(exc).__name__}: {exc}"
def _stop():
 STOP.set()
 with _STATE_LOCK:
  if SERVER is not None:SERVER.should_exit=True
def _join(thread,label,timeout,server=None):
 if thread is None or thread is threading.current_thread():return
 try:
  thread.join(timeout=timeout)
  if thread.is_alive() and server is not None:
   server.force_exit=True;thread.join(timeout=min(2.0,max(.1,timeout)))
  if thread.is_alive():_write_log("shutdown",f"{label} did not terminate within {timeout:g}s; forced exit requested where supported")
 except Exception as exc:_write_log("shutdown",f"Could not join {label}: {type(exc).__name__}: {exc}")
def _close_socket(sock):
 if sock is not None:
  try:sock.close()
  except OSError as exc:_write_log("shutdown",f"Socket close: {type(exc).__name__}: {exc}")
def _shutdown(timeout=8.0):
 _stop()
 with _STATE_LOCK:boot=BOOT_THREAD
 _join(boot,"desktop boot thread",timeout)
 with _STATE_LOCK:server_thread=THREAD;server=SERVER;sock=SOCK
 _join(server_thread,"Uvicorn thread",timeout,server);_close_socket(sock)
def _boot():
 global SOCK,SERVER,THREAD
 phase="loopback listener setup"
 try:
  _status("Starting local services…")
  sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM);sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(("127.0.0.1",0));sock.listen(128)
  with _STATE_LOCK:SOCK=sock
  port=sock.getsockname()[1];base_url=f"http://127.0.0.1:{port}";os.environ["STUDIO_PUBLIC_ORIGIN"]=base_url
  phase="user data setup";_user_data()
  if STOP.is_set():return
  phase="backend imports";_configure_runtime_logging()
  import uvicorn
  from backend.main import app
  if STOP.is_set():return
  phase="Uvicorn startup"
  server=uvicorn.Server(uvicorn.Config(app,host="127.0.0.1",port=port,log_level="info",access_log=False,log_config=None))
  thread=threading.Thread(target=server.run,kwargs={"sockets":[sock]},daemon=True,name="nexora-uvicorn")
  with _STATE_LOCK:
   if STOP.is_set():return
   SERVER=server;THREAD=thread;thread.start()
  deadline=time.monotonic()+_STARTUP_TIMEOUT;last_check="Waiting for Uvicorn to start."
  while time.monotonic()<deadline and not STOP.is_set():
   if not thread.is_alive():
    message=f"Backend server thread exited before readiness. Last check: {last_check} See {_log_path()} for details."
    _write_log("Uvicorn startup",message);_status(message,True);return
   ready,detail=_probe_health(base_url)
   if ready:
    _write_log("startup",f"Backend ready at {base_url}{_HEALTH_PATH}");_status("Ready. Opening Nexora…");WINDOW.load_url(base_url);return
   if detail:last_check=detail
   time.sleep(.2)
  if not STOP.is_set():
   message=f"Timed out after {_STARTUP_TIMEOUT:g}s waiting for {base_url}{_HEALTH_PATH}. Last check: {last_check} See {_log_path()} for details."
   _write_log("readiness timeout",message);_status(message,True)
 except Exception as exc:
  detail=_record_startup_error(phase,exc);_status(f"Startup failed during {phase}: {detail}. See {_log_path()} for details.",True)
class Bridge:
 def select_project(self):
  try:
   import webview
   selected=webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG,title="Select a project folder");return str(selected[0]) if selected else ""
  except Exception as exc:_write_log("folder picker",f"{type(exc).__name__}: {exc}");return ""
 def open_external(self,url):
  from urllib.parse import urlsplit
  try:
   parsed=urlsplit(url)
   if parsed.scheme in ("http","https") and parsed.hostname and not parsed.username and not parsed.password:return bool(webbrowser.open(url,new=2))
  except Exception as exc:_write_log("external link",f"{type(exc).__name__}: {exc}")
  return False
def _show_error(title,message):
 try:
  import tkinter as tk
  from tkinter import messagebox
  window=tk.Tk();window.withdraw();messagebox.showerror(title,message);window.destroy()
 except Exception as exc:_write_log("desktop error dialog",f"{type(exc).__name__}: {exc}; original: {message}");print(message,file=sys.stderr)
def main():
 global WINDOW,BOOT_THREAD
 STOP.clear()
 try:_user_data()
 except Exception as exc:
  detail=_record_startup_error("user data setup",exc);_show_error("Nexora startup failed",f"{detail}\n\nSee {_log_path()} for details.");return 2
 try:import webview
 except Exception as exc:
  detail=_record_startup_error("pywebview import",exc);_show_error("Nexora desktop runtime",f"Install requirements-desktop.txt and Microsoft Edge WebView2 Runtime.\n\n{detail}\n\nSee {_log_path()} for details.");return 2
 page=ROOT/"desktop"/"loading.html"
 if not page.is_file():
  detail=_record_startup_error("loading page",FileNotFoundError(f"Loading page not found: {page}"));_show_error("Nexora startup failed",f"{detail}\n\nSee {_log_path()} for details.");return 2
 try:
  WINDOW=webview.create_window("Nexora",page.as_uri(),width=1440,height=920,min_size=(900,620),background_color="#101114",js_api=Bridge())
  WINDOW.events.closed+=lambda:_stop()
  with _STATE_LOCK:BOOT_THREAD=threading.Thread(target=_boot,daemon=True,name="nexora-desktop-boot");BOOT_THREAD.start()
  webview.start(debug=False)
 except Exception as exc:
  detail=_record_startup_error("pywebview window",exc);_show_error("Nexora desktop startup failed",f"{detail}\n\nSee {_log_path()} for details.");return 2
 finally:_shutdown();WINDOW=None
 return 0
if __name__=="__main__":raise SystemExit(main())
