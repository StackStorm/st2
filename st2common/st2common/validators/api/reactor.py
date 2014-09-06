from st2common.exceptions.apivalidation import ValueValidationException
import st2common.operators as criteria_operators
import six

allowed_operators = criteria_operators.get_allowed_operators()


def validate_criteria(criteria):
    if not isinstance(criteria, dict):
        raise ValueValidationException('Criteria should be a dict.')

    for key, value in six.iteritems(criteria):
        operator = value.get('type', None)
        if operator is None:
            raise ValueValidationException('Operator not specified for field: ' + key)
        if operator not in allowed_operators:
            raise ValueValidationException('For field: ' + key + ', operator ' + operator +
                                           ' not in list of allowed operators: ' +
                                           str(allowed_operators.keys()))
        pattern = value.get('pattern', None)
        if pattern is None:
            raise ValueValidationException('For field: ' + key + ', no pattern specified ' +
                                           'for operator ' + operator)
