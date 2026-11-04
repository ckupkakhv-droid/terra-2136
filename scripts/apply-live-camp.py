"""Let the build ghost follow a finger while play/ui/camp-live.js holds the aim pad.

The inserted flag is false unless that module sets window.TERRA_CAMP_GHOST_AIM.
Without the flag the condition is the previous one. Re-running on an already
patched file does nothing.
"""
from pathlib import Path
import hashlib

root = Path(__file__).resolve().parents[1]
path = root / 'play/index.html'
raw = path.read_bytes()
expected = '0f1dcb3ea7056f9636088b778ea251aef59133604140f27aee67118f937fcec2'
old = 'this.mouse&&this.mouse.has&&!this.stR.on&&!this.touchSeen&&this.ray'
new = 'this.mouse&&this.mouse.has&&!this.stR.on&&(!this.touchSeen||window.TERRA_CAMP_GHOST_AIM)&&this.ray'
text = raw.decode('utf-8')
if new in text:
    if text.count(new) != 1 or old in text:
        raise SystemExit('Live-camp ghost hook is present but not unique.')
    raise SystemExit(0)
if hashlib.sha256(raw).hexdigest() != expected:
    raise SystemExit('Unsupported HTML baseline; review the upstream changes before applying.')
if text.count(old) != 1:
    raise SystemExit(f'Expected the build-ghost condition once, found {text.count(old)}.')
text = text.replace(old, new, 1)
if text.count(new) != 1:
    raise SystemExit('Ghost hook did not apply cleanly.')
path.write_text(text)
print(f'Applied live-camp ghost hook, {len(text.encode()) - len(raw):+d} bytes.')
