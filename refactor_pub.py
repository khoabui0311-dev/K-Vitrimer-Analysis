
import re
with open("can_relax/gui/tabs/tab_publication.py", "r", encoding="utf-8") as f:
    code = f.read()

# Make a backup
with open("can_relax/gui/tabs/tab_publication.bak.py", "w", encoding="utf-8") as f:
    f.write(code)

