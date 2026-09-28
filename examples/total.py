def total(n):
    xs = [3, -1, 4]
    s = 0
    i = 0
    while i < n:
        if 0 <= xs[i]:
            s = s + xs[i]
        i = i + 1
    return s
