# Сборка офлайн terra.html (всё встроено, работает с file://). Запуск: python3 scripts/build-offline.py -> terra.html в корне (не коммитить, загружать в GitHub Release)
import base64,re,glob,os,json
os.chdir(''+os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','play')+'')
h=open('index.html',encoding='utf-8').read()
b64=lambda p:base64.b64encode(open(p,'rb').read()).decode()
glbs={os.path.basename(p):b64(p) for p in glob.glob('assets/**/*.glb',recursive=True) if 'lab_kit' not in p}  # lab_kit.glb: not referenced by code yet
shim="<script>(function(){var G=%s;var of=window.fetch.bind(window);window.fetch=function(u,o){var s=String(u&&u.url||u);var n=s.split('?')[0].split('/').pop();if(G[n]){var b=Uint8Array.from(atob(G[n]),function(c){return c.charCodeAt(0)});return Promise.resolve(new Response(b,{status:200,headers:{'Content-Type':'model/gltf-binary'}}));}return of(u,o);};})();</script>"%json.dumps(glbs)
# modules -> importmap with data URLs, bare specifiers
mods={}
for p in glob.glob('ui/*.js'):
    s=open(p,encoding='utf-8').read()
    if re.search(r"^\s*(import|export)\s",s,re.M): mods[os.path.basename(p)]=s
def fix(s): return re.sub(r"(['\"])\./([\w-]+\.js)\1",lambda m:m.group(1)+'terra/'+m.group(2)+m.group(1),s)
imap={'imports':{'terra/'+k:'data:text/javascript;base64,'+base64.b64encode(fix(v).encode()).decode() for k,v in mods.items()}}
im='<script type="importmap">'+json.dumps(imap)+'</script>'
h=h.replace('<head>','<head>'+im+shim,1) if '<head>' in h else im+shim+h
def js(p):
    s=open(p,encoding='utf-8').read()
    if p=='ui/camp-navigation.js':
        s,c=re.subn(r"\{\s*(?:const base[^;]*;\s*)?const s = document\.createElement\('script'\).*?document\.head\.append\(l\); \}", "",s,flags=re.S)
        assert c==2,c
        for nm in ('camp-mobile','camp-dossier'):
            s+="\n;(function(){var st=document.createElement('style');st.textContent=%s;document.head.append(st);var sc=document.createElement('script');sc.textContent=%s;document.head.append(sc);})();"%(json.dumps(open('ui/%s.css'%nm,encoding='utf-8').read()),json.dumps(open('ui/%s.js'%nm,encoding='utf-8').read().replace('</script','<\\/script')))
    return s.replace('</script','<\\/script')
for m in re.finditer(r'<script([^>]*?)src="((?:ui|art)/[^"]+)"([^>]*)>\s*</script>',h):pass
def rs(m):
    a=m.group(1)+m.group(3); p=m.group(2)
    if 'module' in a: return '<script type="module">import "terra/%s";</script>'%os.path.basename(p)
    return '<script>'+js(p)+'</script>'
h,n=re.subn(r'<script([^>]*?)src="((?:ui|art)/[^"]+)"([^>]*)>\s*</script>',rs,h)
h,k=re.subn(r'<link rel="stylesheet" href="(ui/[^"]+)">',lambda m:'<style>'+open(m.group(1),encoding='utf-8').read()+'</style>',h)
print(n,k,len(mods),list(glbs))
open('../terra.html','w',encoding='utf-8').write(h)
