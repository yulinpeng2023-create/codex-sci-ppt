#!/usr/bin/env python3
import importlib
import platform
import sys

MODULES = ['pptx', 'cv2', 'numpy', 'PIL']

print('Sci-PPT doctor')
print('OS:', platform.platform())
print('Python:', sys.version.split()[0])
failed = []
for name in MODULES:
    try:
        module = importlib.import_module(name)
        version = getattr(module, '__version__', 'ok')
        print(f'[OK] {name}: {version}')
    except Exception as exc:
        failed.append(name)
        print(f'[FAIL] {name}: {exc}')

if failed:
    print('Missing/broken dependencies:', ', '.join(failed))
    raise SystemExit(1)
print('Sci-PPT environment looks ready.')
