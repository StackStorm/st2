class ServiceMissingError(Exception):
    """Error raised when a test uses a service but that service is missing."""
    # TODO add special platform handling to DRY instructions across services

    def __init__(self, service, instructions="", msg=None):
        if msg is None:
            msg = f"The {service} service does not seem to be running or is not accessible!"
            if instructions:
                msg += f"\n{instructions}"
        super().__init__(msg)
        self.service = service
        self.instructions = instructions
