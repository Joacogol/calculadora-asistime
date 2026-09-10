#!/usr/bin/env python3
"""Carga privada de la credencial de Supabase exclusiva de Clínica."""
import base64, getpass, json, os, tempfile
from pathlib import Path
p=Path('/opt/asistime-disenador/config/clinica.json')
os.umask(0o077)
d=json.loads(p.read_text()) if p.exists() else {}
s=getpass.getpass('Clave service_role de Supabase Clínica Preventiva (jejohzzxxnhktdxpdqpy): ').strip()
s=s or d.get('SUPABASE_KEY_CLINICA','')
try:
 part=s.split('.')[1]
 claims=json.loads(base64.urlsafe_b64decode(part+'='*(-len(part)%4)))
 assert claims.get('role')=='service_role' and claims.get('ref')=='jejohzzxxnhktdxpdqpy'
except Exception:
 raise SystemExit('Clave incorrecta: usar service_role del proyecto Clínica Preventiva. No se guardó.')
d['SUPABASE_KEY_CLINICA']=s
p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
fd,tmp=tempfile.mkstemp(dir=p.parent)
with os.fdopen(fd,'w') as f:
 json.dump(d,f); f.flush(); os.fsync(f.fileno())
os.replace(tmp,p)
print('Clave guardada de forma privada. Avisale a Codex que terminaste.')
