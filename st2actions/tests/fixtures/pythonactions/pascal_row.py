import math


class PascalRowAction(object):

    def run(self, **kwargs):
        return PascalRowAction._compute_pascal_row(**kwargs)

    @staticmethod
    def _compute_pascal_row(row_index=0):
        return [math.factorial(row_index)/(math.factorial(i)*math.factorial(row_index-i))
                for i in range(row_index+1)]
