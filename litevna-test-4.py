import sys 
sys.path.append('C:\\Users\\MYLab_Vostro\\NanoVNA\\python')

import time
from nanovna import NanoVNA

t = time.time()
x = NanoVNA('COM3')

try:
    x.open()
    x.set_sweep(1e6, 300e6)
    x.scan()
   # x.fetch_frequencies()
    
    
    s11 = nv.data(0)
    elapsed = time.time() - t
    print(elapsed)
    x.close()
except Exception as e:
    print(f"Error: {e}")
