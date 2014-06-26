# Description:
# Prototype stackstorm hubot integration
#
# Commands:
#   hubot execute <command> [<argument>, ...] - calls out to run the shell staction.


_ = require 'lodash'

CONN_ERRORS =
  'ECONNREFUSED': (err) -> "Connection has been refused. Check if other components are running as well."
  'default': (err) -> "Something gone terribly wrong. #{err}"

errorHandler = (robot) ->
  (err, res) ->
    if err
      robot.logger.error (CONN_ERRORS[err.code] || CONN_ERRORS['default']) err

parseArgs = (scheme=[], argstr="") ->
  # split string by space while preserving quoted literals
  args = argstr.match(/('.*?'|".*?"|\S+)/g) or []

  # trim quotes
  (args[i] = arg[1...-1]) for arg, i in args when arg[0] in ['\'', '\"']

  # build an object
  _.zipObject scheme, args

module.exports = (robot) ->

  # handle uncaught exceptions
  robot.error (err, msg) ->
    robot.logger.error 'Uncaught exception:', err

  # define basic clients
  httpclients =
    actiontypes: robot.http('http://localhost:9501').path('/actiontypes')
    actions: robot.http('http://localhost:9101').path('/actions')
    actionexecutions: robot.http('http://localhost:9101').path('/actionexecutions')

  # init for actions
  httpclients.actions
  .get(errorHandler robot) (err, res, body) ->
    actions = JSON.parse body
    robot.brain.set 'actions', _.zipObject _.map(actions, 'name'), actions

  httpclients.actiontypes
    .get(errorHandler robot) (err, res, body) ->
      actiontypes = JSON.parse body
      robot.brain.set 'actiontypes', _.zipObject _.map(actiontypes, 'name'), actiontypes

  # responder to run a staction
  robot.respond /execute (\w+)\s*(.*)?/i, (msg) ->
    [command, command_args] = msg.match[1..]

    actions = robot.brain.get 'actions'
    actiontypes = robot.brain.get 'actiontypes'

    unless action = actions[command]
      msg.send "No such action: '#{command}'"
      return

    expectedParams = actiontypes[action.runner_type].runner_parameter_names

    payload =
      action: action,
      runner_parameters: parseArgs(expectedParams, command_args)
      action_parameters: {}

    httpclients.actionexecutions
      .header('Content-Type', 'application/json')
      .post(JSON.stringify(payload), errorHandler robot) (err, res, body) ->
        staction_execution = JSON.parse(body)

        unless staction_execution.status is 'complete'
          msg.send "Action has failed to execute"
          return

        msg.send "Action has been completed sucessfully"
