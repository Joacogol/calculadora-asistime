"""Prueba sin APIs: alfa del rótulo y montaje de un clip de muestra propio."""
from pathlib import Path
import subprocess,sys,json
sys.path.insert(0,'/app')
from app.reelero import rotulo,montar
from PIL import Image
out=Path('/revision/video');out.mkdir(exist_ok=True)
p=rotulo('ducart-disenos',{'id':'prueba-alta','titulo':'Soluciones para el agro','bajada':'Ducart Latin America'},out/'rotulo.png')
assert p
im=Image.open(p);assert im.mode=='RGBA'
a=im.getchannel('A');assert a.getextrema()[0]==0 and sum(a.histogram()[0:64])/(1080*1920)>.5
print('Alfa del rótulo: verificado')
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-i','/app/.claude/skills/ducart-disenos/assets/banco/campo-aereo.png','-vf','scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920','-t','3','-r','24','-c:v','libx264','-pix_fmt','yuv420p',str(out/'clip.mp4')],check=True)
montar(out/'clip.mp4',p,Path('/app/.claude/skills/ducart-disenos/musica/campo-calmo.mp3'),out/'reel-prueba.mp4',3)
info=json.loads(subprocess.check_output(['ffprobe','-v','quiet','-print_format','json','-show_streams',str(out/'reel-prueba.mp4')]))
assert any(s['codec_type']=='audio' for s in info['streams'])
v=next(s for s in info['streams'] if s['codec_type']=='video');assert (v['width'],v['height'])==(1080,1920)
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss','1.5','-i',str(out/'reel-prueba.mp4'),'-frames:v','1',str(out/'fotograma.png')],check=True)
print('Montaje MP4 1080x1920: verificado')
