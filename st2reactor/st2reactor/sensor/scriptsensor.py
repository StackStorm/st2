class ScriptSensor(object):
    sensor_path = None

    def __init__(self, sensor_path):
        self.sensor_path = sensor_path

    def start(self):
        """
        XXX: Here's where we would subprocess this thing and consume output.
        """
        pass

    def stop(self):
        """
        XXX: Haven't thought through what should go in here.
        """
        pass
