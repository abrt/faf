import os

def get_libname(path):
    libname = os.path.basename(path)
    idx = libname.rfind(".so")
    if idx > 0:
        libname = libname[0:idx + 3]
    return libname
