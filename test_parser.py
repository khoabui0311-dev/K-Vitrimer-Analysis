from matplotlib.mathtext import MathTextParser
p = MathTextParser('path')
tests = ['?', '-', 'a', r'\ ', r'\;', '']
for t in tests:
    try:
        p.parse(t)
        print('PASS:', repr(t))
    except Exception as e:
        print('FAIL:', repr(t))
