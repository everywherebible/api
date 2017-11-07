import os


def mkdirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != 17:
            raise e
