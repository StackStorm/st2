from st2common.runners.base_action import Action


class MockCoreRemoteAction(Action):
    def run(self, cmd, hosts, hosts_dict):
        if hosts_dict:
            return hosts_dict

        if not hosts:
            return None

        host_list = hosts.split(",")
        results = {}
        for h in hosts:
            results[h] = {
                "failed": False,
                "return_code": 0,
                "stderr": "",
                "succeeded": True,
                "stdout": cmd,
            }
        return results
