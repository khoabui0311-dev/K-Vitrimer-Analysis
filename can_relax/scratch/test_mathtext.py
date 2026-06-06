from matplotlib import mathtext

parser = mathtext.MathTextParser('path')

try:
    print("Testing Ea label:")
    parser.parse(r"$E_a = 80$")
    print("Success Ea")
except Exception as e:
    print("Error:", type(e).__name__, str(e))

try:
    print("Testing B label:")
    parser.parse(r"$B = 2000$")
    print("Success B")
except Exception as e:
    print("Error:", type(e).__name__, str(e))

try:
    print("Testing Tg label:")
    parser.parse(r"$T_g$")
    print("Success Tg")
except Exception as e:
    print("Error:", type(e).__name__, str(e))
