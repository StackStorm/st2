import unittest2
from st2reactor.adapter.container import AdapterContainer
from st2reactor.adapter import AdapterBase


class ContainerTest(unittest2.TestCase):

    def test_load(self):
        """
        Verify the correct no of adapters are created.
        """
        class LoadTestAdapter(AdapterBase):
            init_count = 0

            def __init__(self):
                LoadTestAdapter.init_count += 1

            def start(self):
                pass

            def stop(self):
                pass

        adapter_modules = [LoadTestAdapter, LoadTestAdapter]
        container = AdapterContainer(adapter_modules)
        container.load()
        self.assertEqual(LoadTestAdapter.init_count, len(adapter_modules),
                         'Insufficient adapters instantiated.')

    def test_adapter_start(self):
        """
        Verify start of adapters is called.
        """
        class RunTestAdapter(AdapterBase):
            start_call_count = 0

            def start(self):
                RunTestAdapter.start_call_count += 1

            def stop(self):
                pass

        adapter_modules = [RunTestAdapter, RunTestAdapter]
        container = AdapterContainer(adapter_modules)
        container.load()
        container.run()
        self.assertEqual(RunTestAdapter.start_call_count, len(adapter_modules),
                         'Not all AdapterBase.start called.')

    def test_adapter_start_no_load(self):
        """
        Verify start of adapters is not called without load.
        """
        class RunTestAdapter(AdapterBase):
            start_call_count = 0

            def start(self):
                RunTestAdapter.start_call_count += 1

            def stop(self):
                pass

        adapter_modules = [RunTestAdapter, RunTestAdapter]
        container = AdapterContainer(adapter_modules)
        container.run()
        self.assertEqual(RunTestAdapter.start_call_count, 0,
                         'AdapterBase.start should not be called.')
