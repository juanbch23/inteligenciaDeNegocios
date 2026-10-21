"""Copia el contenido de un .ispac a la carpeta de un proyecto SSIS de Visual Studio
y regenera el <Manifest> del .dtproj (resto del .dtproj se conserva)."""
import sys, os, re, shutil, zipfile, urllib.parse

ispac, projdir, projname = sys.argv[1], sys.argv[2], sys.argv[3]
root = os.path.dirname(projdir)
backup = os.path.join(root, '_respaldo_original', projname)
dtproj = os.path.join(projdir, projname + '.dtproj')

if not os.path.exists(backup):
    os.makedirs(backup)
    for f in os.listdir(projdir):
        if f.endswith(('.dtsx', '.conmgr', '.params', '.dtproj', '.user', '.database')):
            shutil.copy2(os.path.join(projdir, f), backup)

for f in os.listdir(projdir):
    if f.endswith(('.dtsx', '.conmgr')):
        os.remove(os.path.join(projdir, f))

manifest = None
with zipfile.ZipFile(ispac) as z:
    for n in z.namelist():
        name = urllib.parse.unquote(n)
        if name == '@Project.manifest':
            manifest = z.read(n).decode('utf-8-sig')
        elif name.endswith(('.dtsx', '.conmgr')) or name == 'Project.params':
            with open(os.path.join(projdir, name), 'wb') as o:
                o.write(z.read(n))

manifest = re.sub(r'<\?xml[^>]*\?>\s*', '', manifest).strip()
manifest = re.sub(r'\s*<SSIS:Property SSIS:Name="TargetServerVersion">\d+</SSIS:Property>', '', manifest)
manifest = '\n'.join('      ' + l for l in manifest.splitlines())

t = open(dtproj, encoding='utf-8-sig').read()
t = re.sub(r'<Manifest>.*?</Manifest>', lambda m: '<Manifest>\n' + manifest + '\n    </Manifest>', t, flags=re.S)
open(dtproj, 'w', encoding='utf-8-sig').write(t)
print(projname, 'OK:', sorted(f for f in os.listdir(projdir) if f.endswith(('.dtsx', '.conmgr', '.params'))))
