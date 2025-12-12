import mesa
print("Mesa version:", mesa.__version__)
print("Dir(mesa):", dir(mesa))
try:
    import mesa.time
    print("mesa.time imported successfully")
except ImportError as e:
    print("ImportError:", e)
