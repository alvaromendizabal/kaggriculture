"""Streaming execution helper called only by the user, from a notebook."""
from pathlib import Path
import os,queue,signal,subprocess,sys,threading,time

def run_screen(base,rid):
    base=Path(base);command=[sys.executable,str(base/'run_service.py'),'screen','--round',rid]
    child=subprocess.Popen(command,cwd=base,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,start_new_session=True)
    q=queue.Queue()
    def reader():
        for line in child.stdout:q.put(line)
        q.put(None)
    threading.Thread(target=reader,daemon=True).start();start=time.monotonic();ended=False
    logpath=base/'outputs'/f'notebook_round{rid}.log';logpath.parent.mkdir(exist_ok=True)
    def stop():
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=4)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
    try:
        with logpath.open('a') as log:
            while not ended or child.poll() is None:
                if time.monotonic()-start>195:raise TimeoutError('Notebook emergency deadline; preserve diagnostics')
                try:line=q.get(timeout=.2)
                except queue.Empty:continue
                if line is None:ended=True;continue
                print(line,end='',flush=True);log.write(line);log.flush()
        if child.wait()!=0:raise RuntimeError('Screen stopped. Bundle results; do not retry unchanged.')
    except BaseException:
        stop();raise
