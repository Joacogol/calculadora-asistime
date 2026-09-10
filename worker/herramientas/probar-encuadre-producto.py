"""Regresión geométrica: alfa desplazado, proporciones extremas y foto opaca."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw
from motor.encuadre_producto import encuadrar
with tempfile.TemporaryDirectory() as tmp:
 for w,h,box in [(1200,900,(350,35,900,850)),(800,1800,(250,200,500,1700)),(1800,700,(25,210,1720,480)),(800,800,(150,150,650,650)),(800,600,(0,0,800,600))]:
  im=Image.new('RGBA',(w,h));ImageDraw.Draw(im).rectangle(box,fill=(80,90,100,255))
  path=Path(tmp)/'foto.png';im.save(path)
  for alto,top,bottom,ca,cb in [(1080,158,936,712.8,410.4),(1350,170,1196,712.8,410.4),(1920,202,1736,756,367.2)]:
   e=encuadrar(path,1080,alto,top,bottom,1042,ca,cb,29)
   l,t,r,b=e['visible'];assert t>=top and b<=bottom and r<=1042+1e-6
   assert l>=max(ca+(cb-ca)*t/alto,ca+(cb-ca)*b/alto)+29-1e-6
   assert abs(e['width']/e['height']-w/h)<1e-9
 # Mucho aire transparente no altera el tamaño visible ni el centrado.
 a=Image.new('RGBA',(100,200),'red');a.save(path)
 one=encuadrar(path,1080,1080,158,936,1042,713,410)
 padded=Image.new('RGBA',(900,900));padded.paste(a,(500,350));padded.save(path)
 two=encuadrar(path,1080,1080,158,936,1042,713,410)
 assert all(abs(x-y)<1e-6 for x,y in zip(one['visible'],two['visible']))
 Image.new('RGBA',(20,20)).save(path)
 try:encuadrar(path,1080,1080,158,936,1042,713,410)
 except ValueError:pass
 else:raise AssertionError('Una imagen vacía no debe entregarse.')
print('OK: proporciones, márgenes, diagonal, transparencia desplazada y fotos opacas.')
