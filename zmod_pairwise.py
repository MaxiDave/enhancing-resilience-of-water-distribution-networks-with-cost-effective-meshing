from itertools import tee

# This function simply returns a list (s0,s1,...,sn) in pairs such that [(s0,s1),(s1,s2),...,(sn-1,sn)]
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def reverse_pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    pairs = []
    for x, y in zip(b, a):
        pairs.append([x, y])
    return pairs