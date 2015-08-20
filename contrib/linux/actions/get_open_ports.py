import nmap

from st2actions.runners.pythonrunner import Action

"""
Note 1: This action requires nmap binary to be available.

Note 2: We only scan for open TCP ports since scanning for open UDP ports
                (-sU) requires root priveleges.
"""


class PortScanner(Action):
    def run(self, ip_address):
        result = []
        port_details = {}
        ps = nmap.PortScanner()
        ps.scan(ip_address, arguments='--min-parallelism 100 -sT')
        for target_host in ps.all_hosts():
            for comm in ps[target_host].all_protocols():
                if comm in ['tcp', 'udp', 'ip', 'sctp']:
                    ports = ps[target_host][comm].keys()
                    ports.sort()
                    for port in ports:
                        port_details = {
                            port: {
                                'state': ps[ip_address][comm][port]['state'],
                                'service': ps[ip_address][comm][port]['name'],
                                'protocol': comm
                            }
                        }
                        result.append(port_details)

        return result
