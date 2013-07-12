
from Products.Five import BrowserView

from ..service import service


class JsonView(BrowserView):
    def __call__(self):
        self.request.RESPONSE.setHeader('Content-Type', 'application/json')
        return service.render(
            self.context, recursive=self.request.get('recursive'))


class TestThreadingView(BrowserView):
    def __call__(self):
        import thread
        thread.start_new_thread(self._thread_func, ())
        print 'thread started'

        import multiprocessing
        proc = multiprocessing.Process(target=self._process_func)
        proc.start()
        print 'proc started'
        return 'thread and proc started'

    def _thread_func(self):
        import time
        time.sleep(10)
        print 'THREAD FUNC PRINT'

    def _process_func(self):
        import time
        time.sleep(10)
        print 'PROCESS FUNC PRINT'
