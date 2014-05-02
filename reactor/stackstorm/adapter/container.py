import eventlet
from threading import Thread

# Constants
SUCCESS_EXIT_CODE = 0

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=True,
    time=True
)


class AdapterContainer(object):

    def __init__(self, adapter_modules=[]):
        self.__adapter_modules = adapter_modules
        self.__adapters = []

    def load(self):
        self.__adapters = [m() for m in self.__adapter_modules]
        print "Created {} adapters.".format(len(self.__adapters))

    def run(self):
        worker_threads = []
        for m in self.__adapters:
            t = Thread(group=None, target=m.start)
            worker_threads.append((m.__class__.__name__, t))
            t.start()
        print "No of threads {}".format(len(worker_threads))
        for item in worker_threads:
            module_name = item[0]
            thread = item[1]
            thread.join()
            print "{} for module {} has exit.".format(thread.ident,
                                                      module_name)

    def main(self, argv=None):
        self.load()
        self.run()
        return SUCCESS_EXIT_CODE