import zipfile, sys, re, glob, os
import xml.etree.ElementTree as ET
def txt(e):
    out=[]
    def walk(n):
        tag=n.tag
        if tag=='BR': out.append('\n')
        if n.text: out.append(n.text)
        for c in n:
            walk(c)
            if c.tail: out.append(c.tail)
        if tag in('P','DT','DD','LA','row'): out.append('\n')
    walk(e)
    t=''.join(out)
    t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
    return t.strip()
def convert_zip(z, stamp='fetched'):
    name=os.path.basename(z)[:-4]
    zf=zipfile.ZipFile(z)
    x=[n for n in zf.namelist() if n.endswith('.xml')][0]
    root=ET.fromstring(zf.read(x))
    lines=[]
    first=True
    for norm in root.iter('norm'):
        m=norm.find('metadaten')
        if m is None: continue
        jur=m.findtext('jurabk') or ''
        if first:
            lines.append(f"# {m.findtext('langue') or jur} ({jur})\nSource: https://www.gesetze-im-internet.de/{name}/ (XML export, {stamp})\n")
            first=False
        enb=m.findtext('enbez') or ''
        tit=m.findtext('titel') or ''
        gl=m.find('gliederungseinheit')
        body=norm.find('textdaten/text/Content')
        b=txt(body) if body is not None else ''
        if gl is not None and not enb:
            lines.append(f"\n## {m.findtext('gliederungseinheit/gliederungsbez') or ''} {m.findtext('gliederungseinheit/gliederungstitel') or ''}\n")
            continue
        if not enb and not b: continue
        lines.append(f"\n### {enb} {tit}\n{b}\n")
    return name, '\n'.join(lines)

if __name__=='__main__':
    import datetime
    for z in sorted(glob.glob('_raw/*.zip')):
        n,t=convert_zip(z, 'fetched '+datetime.date.today().isoformat())
        open(n+'.md','w').write(t); print(n,len(t))
