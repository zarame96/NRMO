import re,sys,glob,os
cats={
 'STATE':r'ACTIVE ?(のまま|を維持|で継続|継続)',
 'COST':r'(費用ゼロ|費用は?0|費用：0|費用なし|0円|無料|お金はかからない|コストゼロ|費用はかから)',
 'DATE':r'(21日から|21日時点|月21日|21日以降|21日前|21日に)',
 'HIST':r'(承認していない|しておらず|まだ[^。]{0,20}(していない|ない段階|前の段階))',
 'RECOV':r'(戻せない|取り消せない|撤回できない|元に戻らない)',
}
for d in sys.argv[1:]:
    for f in sorted(glob.glob(d+'/*.output.md')):
        rid=os.path.basename(f).replace('.output.md','')
        lines=open(f,encoding='utf-8').read().splitlines()
        for i,l in enumerate(lines):
            for c,p in cats.items():
                if re.search(p,l):
                    print(f"{d.split('/')[-3] if 'tests' in d else d}|{rid}|{c}|L{i+1}|{l.strip()[:260]}")
