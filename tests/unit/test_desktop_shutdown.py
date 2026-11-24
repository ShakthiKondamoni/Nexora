import unittest
from threading import Event
from unittest.mock import patch
from desktop import launcher
class Server:
 def __init__(self):self.should_exit=False;self.force_exit=False
class Sock:
 def __init__(self,events):self.events=events;self.closed=False
 def close(self):self.closed=True;self.events.append("socket.close")
class Thread:
 def __init__(self,name,events):self.name=name;self.events=events;self.alive=True
 def is_alive(self):return self.alive
 def join(self,timeout=None):self.events.append(self.name+".join");self.alive=False
class ShutdownTests(unittest.TestCase):
 def test_stop_requests_exit_without_closing_socket(self):
  events=[];stop=Event();server=Server();sock=Sock(events)
  with patch.object(launcher,"STOP",stop),patch.object(launcher,"SERVER",server),patch.object(launcher,"SOCK",sock):launcher._stop()
  self.assertTrue(stop.is_set());self.assertTrue(server.should_exit);self.assertFalse(sock.closed)
 def test_shutdown_joins_threads_before_closing_socket(self):
  events=[];boot=Thread("boot",events);backend=Thread("uvicorn",events);server=Server();sock=Sock(events)
  with patch.object(launcher,"STOP",Event()),patch.object(launcher,"SERVER",server),patch.object(launcher,"THREAD",backend),patch.object(launcher,"BOOT_THREAD",boot),patch.object(launcher,"SOCK",sock),patch.object(launcher,"_write_log"):
   launcher._shutdown(timeout=.1)
  self.assertTrue(server.should_exit);self.assertEqual(events,["boot.join","uvicorn.join","socket.close"]);self.assertTrue(sock.closed)
 def test_cleanup_is_idempotent_without_server(self):
  sock=Sock([])
  with patch.object(launcher,"STOP",Event()),patch.object(launcher,"SERVER",None),patch.object(launcher,"THREAD",None),patch.object(launcher,"BOOT_THREAD",None),patch.object(launcher,"SOCK",sock):
   launcher._shutdown(timeout=.1);launcher._shutdown(timeout=.1)
  self.assertTrue(sock.closed)
if __name__=="__main__":unittest.main()
