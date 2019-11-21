import time


class PerfCounter:
    def __init__(self, tag=None):
        self.start = time.perf_counter()
        self.tag = tag

    def display(self, name):
        cur_ms = (time.perf_counter() - self.start) * 1000.0
        tag_str = '[%s] ' % self.tag if self.tag else ''
        print('%s%-4f ms: %s' % (tag_str, cur_ms, name))
