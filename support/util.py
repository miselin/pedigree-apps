
import os


def expand(env, s):
    result = s
    for k, v in env.items():
        var = '$%s' % k
        result = result.replace(var, v)
    result = os.path.expandvars(result)

    return result
