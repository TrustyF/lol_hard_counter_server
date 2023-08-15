import time


class Profiler:
    def __init__(self, name):
        self.name = name

        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.end_time = time.time()

        time_passed = self.end_time - self.start_time
        print(f'{self.name} - {time_passed} seconds have passed')
