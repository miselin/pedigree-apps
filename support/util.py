
import os


def expand(env, s):
    result = s
    for k, v in env.items():
        var = '$%s' % k
        result = result.replace(var, v)
    result = os.path.expandvars(result)

    return result


def path_in_colon_list(path, thelist):
    """Is the given path in the ':'-separated list?"""
    thelist = thelist.split(':')
    return path in thelist
