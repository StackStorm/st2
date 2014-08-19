'use strict';

var _ = require('lodash');


var types = {};

types.integer = function (val) {
  return parseInt(val, 10);
};

types.boolean = function (val) {
  var variations = ['true', 'yes', 'yeah', 'sure', 'ok', '1'];
  return variations.indexOf((val + '').toLowerCase()) !== -1;
};

types.array = function (val, spec) {
  var additional = spec.additionalItems !== false;

  return _.reduce(val.split(','), function (result, e, i) {
    var type = _.isArray(spec.items) ? spec.items[i] : spec.items;

    if (type || additional) {
      result.push(cast(e.trim(), type));
    }

    return result;
  }, []);
};

types.string = function (val) {
  return val + '';
};

types.number = function (val) {
  var num = Number(val, 10);
  return (isNaN(num) ? 0 : num);
};

types.object = function (val) {
  return new Object(val);
};

types.null = function () {
  return null;
};


var cast = module.exports = function (val, spec) {
  if (!spec) {
    spec = {};
  }

  return (types[spec.type] || types.string)(val, spec);
};
