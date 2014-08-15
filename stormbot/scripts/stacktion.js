// Description:
// Prototype stackstorm hubot integration
//
// Commands:
//   hubot some <command> [<argument>, ...] - calls out to run the shell staction.
'use strict';

var _ = require('lodash')
  , rsvp = require('rsvp');

var CONN_ERRORS = {
  'ECONNREFUSED': function(err) {
    return 'Connection has been refused. Check if other components are running as well. [' + err.code + ']';
  },
  'ECONNRESET': function(err) {
    return 'Remote server abruptly closed its end of the connection. Check if other components ' + ('throw an error too. [' + err.code + ']');
  },
  'default': function(err) {
    return 'Something gone terribly wrong. [' + err.code + ']';
  }
};

var PUBLISHERS = {
  'remote-exec-sysuser': function(actionExecution, msg, adapterName) {
    return publishMultiHostResult(actionExecution, msg, adapterName);
  },
  'internaldummy-builtin': function(actionExecution, msg, adapterName) {
    return publishLocalResult(actionExecution, msg, adapterName);
  },
  'internaldummy': function(actionExecution, msg, adapterName) {
    return publishLocalResult(actionExecution, msg, adapterName);
  },
  'shell': function(actionExecution, msg, adapterName) {
    return publishLocalResult(actionExecution, msg, adapterName);
  }
};

var getPublishHeader = function(actionExecution, adapterName) {
  var message;
  message = (adapterName !== null ? adapterName.toLowerCase() : void 0) === 'hipchat' ? '/code' : '';
  return '' + message + ' STATUS: ' + actionExecution.status + '\n';
};

var publishMultiHostResult = function(actionExecution, msg, adapterName) {
  var host, hostResult, message, result, _ref, _ref1;
  result = JSON.parse(actionExecution.result);
  message = getPublishHeader(actionExecution, adapterName);
  for (host in result) {
    hostResult = result[host];
    message = '' + message + 'Result for \'' + host + '\'\n';
    if ((_ref = hostResult.stdout) !== null ? _ref.length : void 0) {
      message = '' + message + '  STDOUT: ' + hostResult.stdout + '\n';
    }
    if ((_ref1 = hostResult.stderr) !== null ? _ref1.length : void 0) {
      message = '' + message + '  STDERR: ' + hostResult.stderr + '\n';
    }
    message = '' + message + '  EXIT_CODE: ' + hostResult.return_code + '\n';
  }
  return msg.send(message);
};

var publishLocalResult = function(action_execution, msg, adapterName) {
  var message, result, _ref, _ref1;
  result = JSON.parse(action_execution.result);
  message = getPublishHeader(action_execution, adapterName);
  if (((_ref = result.std_out) !== null ? _ref.length : void 0) > 0) {
    message = '' + message + ' STDOUT: ' + result.std_out + '\n';
  }
  if (((_ref1 = result.std_err) !== null ? _ref1.length : void 0) > 0) {
    message = '' + message + ' STDERR: ' + result.std_err + '\n';
  }
  message = '' + message + ' EXIT_CODE: ' + result.exit_code;
  return msg.send(message);
};

var parseArgs = function(scheme, argstr) {
  var arg, args, i, _i, _len, _ref;
  if (scheme === null) {
    scheme = [];
  }
  if (argstr === null) {
    argstr = '';
  }
  args = argstr.match(/([''])(?:(?!\1)[^\\]|\\.)*\1|(\S)+/g) || [];
  for (i = _i = 0, _len = args.length; _i < _len; i = ++_i) {
    arg = args[i];
    if ((_ref = arg[0]) === '\'' || _ref === '\'') {
      args[i] = arg.slice(1, -1).replace(/\\(.)/mg, '$1');
    }
  }
  return _.zipObject(scheme, args);
};

var formatCommand = function(command) {
  var arg, line, _i, _len, _ref;
  line = 'hubot run ' + command.name + ' ';
  _ref = _({}).assign(command.parameters).keys().value();
  for (_i = 0, _len = _ref.length; _i < _len; _i++) {
    arg = _ref[_i];
    line += '[' + arg + '] ';
  }
  return line += '- ' + command.description;
};

module.exports = function(robot) {

  var actionsPromise, errorHandler, httpclient, httpclients;

  robot.router.post('/stormbot/st2', function(req, res) {
    var data, user;
    user = {};
    if (process.env.HUBOT_ADAPTER_ROOM) {
      user.room = process.env.HUBOT_ADAPTER_ROOM;
    }
    if (data = req.body.payload) {
      robot.send(user, '[' + req.body.type + ' ' + data.event + '] ' + data.msg);
      return res.end('{"status": "completed", "msg": "Message posted successfully"}');
    } else {
      return res.end('{"status": "failed", "msg": "An error occurred trying to post the message"}');
    }
  });

  robot.error(function(err) {
    return robot.logger.error('Uncaught exception:', err);
  });

  errorHandler = function(err) {
    if (err) {
      return robot.logger.error((CONN_ERRORS[err.code] || CONN_ERRORS['default'])(err));
    }
  };

  httpclient = robot.http('http://172.168.50.50:9101');

  httpclients = {
    actions: httpclient.scope('/actions'),
    actionexecutions: httpclient.scope('/actionexecutions')
  };

  actionsPromise = new rsvp.Promise(function(resolve, reject) {
    return httpclients.actions.get(errorHandler)(function(err, res, body) {
      var actions, obj;
      if (err) {
        return reject(err);
      }
      actions = JSON.parse(body);
      obj = _.zipObject(_.map(actions, 'name'), actions);
      robot.brain.set('actions', obj);
      return resolve(obj);
    });
  });

  rsvp.hash({
    actions: actionsPromise
  }).then(function(d) {
    var command, _name, _ref, _results;
    _ref = d.actions;
    _results = [];
    for (_name in _ref) {
      command = _ref[_name];
      _results.push(robot.commands.push(formatCommand(command)));
    }
    return _results;
  });

  return robot.respond(/run\s+(\S+)\s*(.*)?/i, function(msg) {

    var command, command_args, _ref;

    _ref = msg.match.slice(1), command = _ref[0], command_args = _ref[1];

    return rsvp.hash({
      actions: actionsPromise
    }).then(function(d) {

      var action, actions, actualParams, expectedParams, payload, pullResults;

      actions = d.actions;

      if (!(action = actions[command])) {
        msg.send('No such action: ' + command);
        return;
      }

      expectedParams = _({}).assign(action.parameters);
      actualParams = parseArgs(expectedParams.keys().value(), command_args);

      payload = {
        action: action,
        parameters: _({}).assign(expectedParams.value()).assign(actualParams).value()
      };

      httpclients.actionexecutions.header('Content-Type', 'application/json').post(JSON.stringify(payload), errorHandler)(function(err, res, body) {

        var action_execution;

        action_execution = JSON.parse(body);

        if (res.statusCode !== 201) {
          msg.send('Action has failed to run');
          return;
        }

        if (action_execution.status === 'scheduled') {
          setTimeout(function() {
            return pullResults(action_execution.id);
          }, 1000);
          return;
        }

        if (action_execution.status !== 'complete') {
          msg.send('Action has failed to execute');
          return;
        }

        action = actions[action_execution.action.name];

        return PUBLISHERS[action.runner_type](action_execution, msg, robot.adapterName);
      });

      return pullResults = function(id) {
        return httpclient.scope('/actionexecutions/' + id).get(errorHandler)(function(err, res, body) {

          var action_execution;

          action_execution = JSON.parse(body);

          if (action_execution.status === 'scheduled' || action_execution.status === 'running') {
            setTimeout(function() {
              return pullResults(action_execution.id);
            }, 1000);
            return;
          }

          if (action_execution.status !== 'complete') {
            msg.send('Action has failed to execute');
            return;
          }

          action = actions[action_execution.action.name];

          return PUBLISHERS[action.runner_type](action_execution, msg, robot.adapterName);
        });
      };
    });
  });
};
