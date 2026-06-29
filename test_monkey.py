import matplotlib.pyplot as plt
import matplotlib.mathtext as mathtext

_original_parse = mathtext.MathTextParser.parse

def _safe_parse(self, s, *args, **kwargs):
    try:
        return _original_parse(self, s, *args, **kwargs)
    except Exception as e:
        print('CAUGHT EXCEPTION:', e)
        return _original_parse(self, r'~', *args, **kwargs)

mathtext.MathTextParser.parse = _safe_parse

fig, ax = plt.subplots()
ax.plot([1,2], [1,2], label='Test $\\Delta')
plt.legend()
try:
    plt.tight_layout()
    print('Success!')
except Exception as e:
    print('TIGHT LAYOUT FAILED:', e)
