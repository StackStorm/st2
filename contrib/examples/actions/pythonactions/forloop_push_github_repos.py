from st2actions.runners.pythonrunner import Action


class PushGithubRepos(Action):
    def run(self, data_to_push):
        try:
            for each_item in data_to_push:
                # Push data to a service here
                print str(each_item)
        except Exception as e:
            raise Exception("Process failed: {}".format(e.message))

        return (True, "Data pushed successfully")
