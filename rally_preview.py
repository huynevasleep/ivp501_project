"""Preview real standalone clips, never a seek into the full source video."""
from pathlib import Path
import hashlib
import json
from rally_export import export_individual


def preview_clip(source,segment,out,bundle=None):
    a,b=float(segment['start']),float(segment['end'])
    if not 0<=a<b or b-a>90:
        raise ValueError('Khoảng này dài hơn một pha thông thường. Hãy chỉnh mốc trước khi xem video riêng (tối đa 90 giây).')
    if bundle and 'files' in bundle:
        for saved,file in zip(bundle['segments'],bundle['files']):
            if abs(saved['start']-a)<1e-6 and abs(saved['end']-b)<1e-6 and Path(file).is_file():
                return Path(file)
    source=Path(source).resolve(); stat=source.stat()
    key=hashlib.sha256(f'{source}|{stat.st_size}|{stat.st_mtime_ns}|{a}|{b}'.encode()).hexdigest()[:24]
    dest=Path(out)/'previews'/key
    pointer=dest/'preview.json'
    if pointer.exists():
        file=Path(json.loads(pointer.read_text())['file'])
        if file.is_file(): return file
    bundle=export_individual(source,[segment],dest)
    file=bundle['files'][0].resolve()
    pointer.write_text(json.dumps({'file':str(file)}),encoding='utf-8')
    return file
