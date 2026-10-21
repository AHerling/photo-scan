#!/usr/bin/env python3
import os, tarfile, gzip, time, struct, subprocess

debdir = '/home/cain/opencode/printer-gui/deb'
out = '/home/cain/opencode/printer-gui/photo-scan_0.1.0-1_all.deb'
# control
control = open(os.path.join(debdir,'DEBIAN/control')).read()
os.makedirs(os.path.join(debdir,'DEBIAN'), exist_ok=True)
with open(os.path.join(debdir,'DEBIAN/control'),'wb') as f:
    f.write(control.encode())
# make control.tar.gz
import io
def tar_gz(files):
    bio = io.BytesIO()
    with tarfile.open(fileobj=bio, mode='w:gz') as tar:
        for path, arcname in files:
            tar.add(path, arcname=arcname)
    return bio.getvalue()

files = []
for root, dirs, filenames in os.walk(os.path.join(debdir,'DEBIAN')):
    for fn in filenames:
        p = os.path.join(root,fn)
        files.append((p, os.path.relpath(p, debdir)))
control_tgz = tar_gz(files)
# data.tar.xz
files = []
for root, dirs, filenames in os.walk(debdir):
    for fn in filenames:
        p = os.path.join(root,fn)
        if p.startswith(os.path.join(debdir,'DEBIAN')):
            continue
        files.append((p, os.path.relpath(p, debdir)))
# try gzip
bio = io.BytesIO()
with tarfile.open(fileobj=bio, mode='w:gz') as tar:
    for path, arcname in files:
        tar.add(path, arcname=arcname)
data_tgz = bio.getvalue()

with open(out,'wb') as f:
    f.write(b'!<arch>\n')
    # debian-binary
    def ar_entry(name, data):
        name = name.encode()
        if len(name) < 16:
            name = name + b' '*(16-len(name))
        else:
            name = name[:15]+b'/'
        hdr = name + b'%d' % int(time.time()) + b' '*(12-len(str(int(time.time())))) if False else name
        # simpler
        hdr = (name + b'0       ' + b'0       ' + b'0     ' + b'%d' % (0o100644) + b' '*(8-len('%d'%(0o100644))) if False else None)
    # easier way
    pass

# use subprocess
subprocess.call(['ar','rc',out,'/dev/null'])
