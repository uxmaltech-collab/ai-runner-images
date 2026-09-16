#!/usr/bin/env python3
"""Restore the existing canonical CLOEXEC RPC binary from standard input."""
import sys,os,hashlib,json,datetime
from pathlib import Path
assert os.getuid()==0
p=Path('/opt/macos-tart-guest-agent/bin/tart-guest-agent')
expected='a1c66855a250108ea05fc4f672f1099dfd1c315a012dee343c282aab83933952'
old=hashlib.sha256(p.read_bytes()).hexdigest()
stage=p.with_name('tart-guest-agent.incoming-flutter-base')
with stage.open('xb') as f:
 while data:=sys.stdin.buffer.read(1048576): f.write(data)
assert stage.stat().st_size==12835808
assert hashlib.sha256(stage.read_bytes()).hexdigest()==expected
stage.chmod(0o755)
os.replace(stage,p)
result={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'previous_sha256':old,'installed_sha256':expected,'source':'canonical-rpc-cloexec-v2','loaded_on_next_boot':True}
Path('/opt/ai-runner-images/rpc-installation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
