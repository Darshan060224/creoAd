import re

css_path = '/home/da24/Desktop/creoAd/frontend/styles/landing.module.css'
with open(css_path, 'r') as f:
    css = f.read()

# Replace background: #fff with dark glass
css = re.sub(r'background:\s*#fff(?:fff)?\s*;', 'background: rgba(24, 24, 27, 0.6);\n  backdrop-filter: blur(16px);\n  -webkit-backdrop-filter: blur(16px);', css)
css = re.sub(r'background:\s*rgba\(255,\s*255,\s*255,\s*0\.9[0-9]*\)\s*;', 'background: rgba(24, 24, 27, 0.8);\n  backdrop-filter: blur(16px);', css)

# Replace light backgrounds
css = re.sub(r'background:\s*#f5f5f[0-9a-f]\s*;', 'background: rgba(0, 0, 0, 0.3);', css)
css = re.sub(r'background:\s*#f0f0ee\s*;', 'background: #09090b;', css)

# Replace dark text/borders with light
css = re.sub(r'color:\s*#0a0a0a\s*;', 'color: #f4f4f5;', css)
css = re.sub(r'color:\s*#333\s*;', 'color: #e4e4e7;', css)
css = re.sub(r'color:\s*#555\s*;', 'color: #d4d4d8;', css)
css = re.sub(r'color:\s*#666\s*;', 'color: #a1a1aa;', css)
css = re.sub(r'color:\s*#888\s*;', 'color: #71717a;', css)

# Replace borders
css = re.sub(r'border([a-z-]*):\s*1\.5px solid #0a0a0a\s*;', r'border\1: 1px solid rgba(255, 255, 255, 0.1);', css)
css = re.sub(r'border([a-z-]*):\s*1px solid #0a0a0a\s*;', r'border\1: 1px solid rgba(255, 255, 255, 0.1);', css)
css = re.sub(r'border([a-z-]*):\s*1px solid #e0e0dc\s*;', r'border\1: 1px solid rgba(255, 255, 255, 0.08);', css)
css = re.sub(r'border([a-z-]*):\s*1\.5px solid #e0e0dc\s*;', r'border\1: 1px solid rgba(255, 255, 255, 0.08);', css)
css = re.sub(r'border([a-z-]*):\s*1px solid #e5e7eb\s*;', r'border\1: 1px solid rgba(255, 255, 255, 0.08);', css)

# Replace hardcoded box shadows
css = re.sub(r'box-shadow:\s*4px 4px 0 #0a0a0a\s*;', 'box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);', css)

# Add glowing radial backgrounds to gridBg
if '.gridBg {' in css:
    css = css.replace('.gridBg {\n  background-color: #f0f0ee;', '.gridBg {\n  background-color: #09090b;')

with open(css_path, 'w') as f:
    f.write(css)

print("Replaced CSS")
