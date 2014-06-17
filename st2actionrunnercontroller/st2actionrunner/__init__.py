import abc
import traceback


ACTION_NOT_SET_MSG = 'self._action not set.'

EXECUTION_ID = 'execution_id'
REPO_ID = 'repo_id'
STDOUT = 'stdout'
STDERR = 'stderr'
EXIT_CODE = 'exit_code'

ACTION_ID = 0
ACTION_NAME = 1
ACTION_DB = 2

class RunnerBase():
    __metaclass__ = abc.ABCMeta

    def __init__(self, action_id, action_name, runner_parameters, action_parameters):
        self._action = (action_id, action_name, None)
        self._runner_parameters(runner_parameters)
        self._action_parameters(action_parameters)

    """
        self._action_execution = None
        self._output = []
        self._action_result = {EXECUTION_ID: None,
                                 REPO_ID: None,
                                 STDOUT: [],
                                 STDERR: [],
                                 EXIT_CODE: None
                                 }
    """

    def get_action_id(self):
        return self._action[ACTION_ID]

    def get_action_name(self):
        return self._action[ACTION_NAME]

    def _set_runner_parameters(self, parameters):
        self._runner_parameters = parameters

    def get_runner_parameters(self):
        return self._runner_parameters

    def _set_action_parameters(self, parameters):
        self._action_parameters = parameters

    def get_action_parameters(self):
        return self._action_parameters

    def get_required_runner_parameter_names(self):
        if not self._action:
            raise ValueError(ACTION_NOT_SET_MSG)

    def get_required_action_parameter_names(self):
        if not self._action:
            raise ValueError(ACTION_NOT_SET_MSG)

        return self._action.param_names

    def get_run_type(self):
        if not self._action:
            raise ValueError(ACTION_NOT_SET_MSG)
        
    def report_stdout(self, message):
        self._action_result['stdout'].append(message)

    def report_stderr(self, message):
        self._action_result['stderr'].append(message)

    def report_exitcode(self, exitcode):
        if self._action_result[EXIT_CODE]:
            raise ValueError('Staction exit code already set')
        self._action_result[EXIT_CODE] = exitcode

    def _parse_args(self, args):
        parsed_args = {}

        name_values = args.split(',')
        for name_value in name_values:
            pair = name_value.split('=')
            parsed_args[pair[0]] = pair[1]

        return parsed_args

    def _set_repo_id(self, action):
        if self._action_result[REPO_ID]:
            raise ValueError('Staction repo id aleady set.')

        # TODO: Lookup from current repo path
#        self._action_result[REPO_ID] = "git:41977d22860bb73391695326d9c7477995c27e09"
        command = ['git', 'log', '-1', 'master', action.repo_path]
        # take first line
        # SHA is at
        # line.split(' ')[1]
        

    def _create_action_execution(self, action, args, target=None):
        action_execution = StactionExecution()
        action_execution.action = action
        action_execution.params = args
        action_execution.status = STEXEC_STARTING

        action_execution = action_execution.save()

        if self._action_result[EXECUTION_ID]:
            raise ValueError('Staction execution ID already set')
        self._action_result[EXECUTION_ID] = str(action_execution.id)

        return action_execution

    def _update_action_execution(self, action_execution, status):
        if not action_execution:
            raise ValueError('Staction execution object invalid')

        action_execution.status = status
        action_execution = action_execution.save()

    """
    def generate_dummy_data(self):
        self._action_result[EXECUTION_ID] = 'ABCDE12345'
        self._action_result[REPO_ID] = 'git:41977d22860bb73391695326d9c7477995c27e09'
        self._action_result[STDOUT].append('FreeBSD 9.0-RELEASE #0: Tue Jan 3 07:46:30 UTC 2012')
        self._action_result[STDERR].append('some error goes here')
        self._action_result[EXIT_CODE] = random.randrange(-1, 5, 1)
        return self._action_result
    """

    def do_run(self, action, target, args):
        #return self.generate_dummy_data()

        params = self._parse_args(args)


        # create execution action
        action_execution = self._create_action_execution(action, args)
        log.audit('Staction "%s" triggered for target "%s" with arguments "%s". Staction execution id "%s" ', action.name, target, params, action_execution.id)

        self._update_action_execution(action_execution, STEXEC_RUNNING)

        # report action start
#        self.report_action_control('Starting action name="%s",id="%s"' % (self._action_execution.action.name, self._action_execution.action.id))

        # report action repo ID
        self._set_repo_id(action)
        
        self.pre_run()
        self.run(target, params)
        self.post_run()
        if self._action_result[EXIT_CODE] is None:
            print 'error: action did not report exit code before returning from run()'
            print '       Assuming run error occured.'
            action_execution.status = STEXEC_ERROR
        else:
            pass

        self._update_action_execution(action_execution, STEXEC_FINISHED)

        print 'debug action result: %s' % self._action_result
        # TODO: destroy exec action (move exec station to historical table)

        log.audit('Staction execution id "%s" completed with result "%s"', action_execution.id, self._action_result)

        return self._action_result
