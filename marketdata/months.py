"""Month arithmetic on 'YYYY-MM' strings."""
import datetime as _dt


def parse(month):
    y, m = month.split("-")
    return int(y), int(m)


def fmt(y, m):
    return f"{y:04d}-{m:02d}"


def add(month, n):
    y, m = parse(month)
    idx = y * 12 + (m - 1) + n
    return fmt(idx // 12, idx % 12 + 1)


def span(start, end):
    """Inclusive list of months from start to end."""
    out, cur = [], start
    while cur <= end:
        out.append(cur)
        cur = add(cur, 1)
    return out


def current(today=None):
    today = today or _dt.date.today()
    return fmt(today.year, today.month)


def last_n(n, end=None):
    end = end or add(current(), -1)
    return span(add(end, -(n - 1)), end)


def label(month):
    y, m = parse(month)
    names = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]
    return f"{names[m - 1]} {y}"
