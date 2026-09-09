"""Historical developer script; never imported by the application."""

def main():
    raise RuntimeError('This historical migration targets obsolete code. Use the maintained modules; source history is retained below for review.')

    import re
    with open("can_relax/gui/tabs/tab_publication.py", "r", encoding="utf-8") as f:
        code = f.read()

    # Make a backup
    with open("can_relax/gui/tabs/tab_publication.bak.py", "w", encoding="utf-8") as f:
        f.write(code)



if __name__ == '__main__':
    main()
