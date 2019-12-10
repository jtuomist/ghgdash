import threading
import time
import inspect


pc_data = threading.local()


class PerfCounter:
    def __init__(self, tag=None):
        self.start = time.perf_counter_ns()
        if tag is None:
            # If no tag given, default to the name of the calling func
            calling_frame = inspect.currentframe().f_back
            tag = calling_frame.f_code.co_name

        self.tag = tag
        if not hasattr(pc_data, 'depth'):
            pc_data.depth = 0
        pc_data.depth += 1

    def __del__(self):
        pc_data.depth -= 1

    def display(self, name):
        cur_ms = (time.perf_counter_ns() - self.start) / 1000000
        tag_str = '[%s] ' % self.tag if self.tag else ''
        print('%s%s%-4.3f ms: %s' % ((pc_data.depth - 1) * '  ', tag_str, cur_ms, name))
