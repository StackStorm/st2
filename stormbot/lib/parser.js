'use strict';

var _ = require('lodash')
  , cast = require('./cast.js')
  , splitargs = require('splitargs')
  ;

module.exports = function (argstr, spec) {
  var args = splitargs(argstr);

  // Prepare an object that consists of only the pairs that has default value
  var defaults = _.reduce(spec, function (result, value, key) {
    var defaults = value.default;

    if (defaults) {
      result[key] = defaults;
    }

    return result;
  }, {});


  // Iterate through the list of arguments to get an object of argument pairs
  var actual = {}
    , keys = _.keys(spec)
    ;

  _.each(args, function (arg) {

    var name;

    if (arg.match(/^\w+=/)) {

      var _ref = arg.split('=');

      name = _ref.shift();
      arg = _ref.join('=');

    } else {

      name = keys.shift();

    }

    if (_.isUndefined(name)) {
      // The question is should we or should we not skim through the rest of arguments if there is
      // no more positional one left? In other words, should we look for specific arguments to
      // overwrite positional one? Is it a feature we realy need or it's just a coincidence?
      //return false;
      return true;
    }

    actual[name] = cast(arg, spec[name]);

  });


  // Merge two objects together
  _.defaults(actual, defaults);


  return actual;
};
