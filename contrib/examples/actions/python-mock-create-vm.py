import eventlet
import random

from st2common.runners.base_action import Action


class MockCreateVMAction(Action):
    def run(self, cpu_cores, memory_mb, vm_name, ip):
        eventlet.sleep(5)

        data = {
            "vm_id": "vm" + str(random.randint(0, 10000)),
            ip: {"cpu_cores": cpu_cores, "memory_mb": memory_mb, "vm_name": vm_name},
        }

        return data
