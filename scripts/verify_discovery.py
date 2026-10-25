"""Read-only Codex app-server skills/list check; no LLM turn, account edit or config edit."""
import argparse,json,queue,subprocess,threading,time,shutil,os
from pathlib import Path
from core import write
def verify(codex,out,cwd=None):
    binary=codex or shutil.which('codex.exe') or shutil.which('codex')
    if not binary:raise FileNotFoundError('Codex executable not found')
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    proc=subprocess.Popen([binary,'app-server','--listen','stdio://'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=flags)
    messages=queue.Queue()
    def reader():
        for line in proc.stdout:
            try:messages.put(json.loads(line))
            except json.JSONDecodeError:pass
    threading.Thread(target=reader,daemon=True).start()
    def send(msg):proc.stdin.write(json.dumps(msg)+'\n');proc.stdin.flush()
    def response(id):
        end=time.monotonic()+45
        while time.monotonic()<end:
            try:msg=messages.get(timeout=1)
            except queue.Empty:continue
            if msg.get('id')==id:
                if 'error' in msg:raise RuntimeError(str(msg['error']))
                return msg['result']
        raise TimeoutError('Codex app-server response timeout')
    try:
        send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'mechanism_skill_discovery_check','version':'1.0.0'}}});response(1)
        send({'method':'initialized','params':{}})
        send({'id':2,'method':'skills/list','params':{'cwds':[str(Path(cwd or Path.cwd()).resolve())],'forceReload':True}})
        result=response(2);found=[]
        def visit(value):
            if isinstance(value,dict):
                if value.get('name')=='mechanism-to-cad':found.append({k:value.get(k) for k in ('name','path','scope','enabled','description')})
                for v in value.values():visit(v)
            elif isinstance(value,list):
                for v in value:visit(v)
        visit(result)
        installed=Path.home()/'.agents/skills/mechanism-to-cad/SKILL.md'
        def same(p):return str(Path(p or '').resolve()).casefold()==str(installed.resolve()).casefold()
        success=any(same(x['path']) and x.get('enabled') is not False for x in found)
        report={'passed':success,'method':'Codex app-server initialize + skills/list forceReload; no agent turn','matches':found,'expected':str(installed)}
        write(out,report)
        if not success:raise RuntimeError('Installed skill not found/enabled in Codex skills/list; see report')
        return report
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--codex');p.add_argument('--out',required=True);p.add_argument('--cwd');a=p.parse_args();print(json.dumps(verify(a.codex,a.out,a.cwd),ensure_ascii=False,indent=2))
