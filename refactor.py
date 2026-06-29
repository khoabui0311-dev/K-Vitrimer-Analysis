import sys

with open('can_relax/gui/tabs/tab_comparison.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
for i, line in enumerate(lines):
    if 'Arrhenius Comparison Plot' in line and 'st.subheader' in line:
        start_idx = i
        break

if start_idx == -1:
    print('Could not find start index.')
    sys.exit(1)

orig_lines = lines[start_idx:]
indented_arr = ['    ' + l if l.strip() else '\n' for l in orig_lines]

new_block = [
    '            comp_tab_arr, comp_tab_vh = st.tabs(["Arrhenius Kinetics", "Van \'t Hoff"])\n',
    '            \n',
    '            with comp_tab_arr:\n',
] + indented_arr

lines = lines[:start_idx] + new_block

with open('can_relax/gui/tabs/tab_comparison.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Arrhenius block indented and tabs added.')
