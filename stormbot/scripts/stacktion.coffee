# Description:
# Prototype stackstorm hubot integration
#
# Commands:
#   hubot run <command> [<argument>, ...] - calls out to run the shell staction.


_ = require 'lodash'
rsvp = require 'rsvp'

CONN_ERRORS =
  'ECONNREFUSED': (err) ->
    "Connection has been refused. Check if other components are running as well. [#{err.code}]"
  'ECONNRESET': (err) ->
    "Remote server abruptly closed its end of the connection. Check if other components " +
      "throw an error too. [#{err.code}]"
  'default': (err) -> "Something gone terribly wrong. [#{err.code}]"

parseArgs = (scheme=[], argstr="") ->
  # split string by space while preserving quoted literals and escaped quotes
  args = argstr.match(/(["'])(?:(?!\1)[^\\]|\\.)*\1|(\S)+/g) or []

  # trim quotes and unescape strip slashes
  (args[i] = arg[1...-1].replace(/\\(.)/mg, "$1")) for arg, i in args when arg[0] in ['\'', '\"']

  # build an object
  _.zipObject scheme, args

formatCommand = (command) ->
  line = "hubot run #{command.name} "
  for arg in _.keys(command.parameters)
    line += "[#{arg}] "
  line += "- #{command.description}"

module.exports = (robot) ->

  # ST2 Listener
  robot.router.post '/stormbot/st2', (req, res) ->
    user = {}
    if process.env.HUBOT_ADAPTER_ROOM
      user.room = process.env.HUBOT_ADAPTER_ROOM

    if data = req.body.payload
      robot.send user, "[#{req.body.type} #{data.event}] #{data.msg}"
      res.end '{"status": "completed", "msg": "Message posted successfully"}'
    else
      res.end '{"status": "failed", "msg": "An error occurred trying to post the message")'

  # handle uncaught exceptions
  robot.error (err, msg) ->
    robot.logger.error 'Uncaught exception:', err

  errorHandler = (err, res) ->
    if err
      robot.logger.error (CONN_ERRORS[err.code] || CONN_ERRORS['default']) err

  # define basic clients
  httpclients =
    actions: robot.http('http://localhost:9101').path('/actions')
    actionexecutions: robot.http('http://localhost:9101').path('/actionexecutions')

  # init for actions
  actionsPromise = new rsvp.Promise (resolve, reject) ->
    httpclients.actions
      .get(errorHandler) (err, res, body) ->
        return reject err if err
        actions = JSON.parse body
        obj = _.zipObject _.map(actions, 'name'), actions
        robot.brain.set 'actions', obj
        resolve obj

  # Populate robot's command list for `help`
  rsvp.hash
    actions: actionsPromise
  .then (d) ->
    for _name, command of d.actions
      robot.commands.push formatCommand command

  # responder to run a staction
  robot.respond /run\s+(\S+)\s*(.*)?/i, (msg) ->
    [command, command_args] = msg.match[1..]

    rsvp.hash
      actions: actionsPromise
    .then (d) ->
      actions = d.actions

      unless action = actions[command]
        msg.send "No such action: '#{command}'"
        return

      expectedParams = _.keys(action.parameters)

      actualParams = parseArgs(expectedParams.keys().value(), command_args)

      payload =
        action: action,
        parameters: _({}).assign(expectedParams.value()).assign(actualParams).value()

      httpclients.actionexecutions
        .header('Content-Type', 'application/json')
        .post(JSON.stringify(payload), errorHandler) (err, res, body) ->
          action_execution = JSON.parse(body)

          unless res.statusCode is 201
            msg.send "Action has failed to run"
            return

          unless action_execution.status is 'complete'
            msg.send "Action has failed to execute"
            return

          result = JSON.parse(action_execution.result)

          msg.send "STATUS: #{action_execution.status}"
          msg.send "STDOUT: #{result.std_out}"
          msg.send "STDERR: #{result.std_err}"
          msg.send "EXIT_CODE: #{result.exit_code}"
