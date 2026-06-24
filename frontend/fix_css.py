import re

css_path = '/home/da24/Desktop/creoAd/frontend/styles/landing.module.css'
with open(css_path, 'r') as f:
    css = f.read()

# Fix text color
css = css.replace('color: #71717a;', 'color: #a1a1aa;')

# Fix btnSecondary
css = css.replace('border: 1.5px solid rgba(10, 10, 10, 0.125);', 'border: 1.5px solid rgba(255, 255, 255, 0.2);')
css = css.replace('background: rgba(10, 10, 10, 0.05);', 'background: rgba(255, 255, 255, 0.05);')

# Fix btnDark (make it white for contrast against dark card)
css = css.replace('.btnDark {\n  background: #0a0a0a;\n  color: #fff;\n}', '.btnDark {\n  background: #fff;\n  color: #0a0a0a;\n}')

with open(css_path, 'w') as f:
    f.write(css)

print("Fixed CSS bugs")
