from st2common.runners.base_action import Action


class IncreaseIndexAndCheckCondition(Action):
    def run(self, index, pagesize, input):
        if pagesize and pagesize != '':
            if len(input) < int(pagesize):
                return (False, "Breaking out of the loop")
        else:
            pagesize = 0

        if not index or index == '':
            index = 1

        return(True, int(index) + 1)
