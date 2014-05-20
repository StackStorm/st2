'use strict';
angular.module('main')
  .directive('sk0AutoForm', function () {
    // TODO: figure out what other fields do we need.
    // TODO: create an interface to extend the list of fields.
    var fieldTypes = {
      'text': 'modules/sk0-auto-form/fields/input.partial.html',
      'password': 'modules/sk0-auto-form/fields/input.partial.html',
      'checkbox': 'modules/sk0-auto-form/fields/checkbox.partial.html',
      'textarea': 'modules/sk0-auto-form/fields/textarea.partial.html',
      'select': 'modules/sk0-auto-form/fields/select.partial.html'
    };

    return {
      restrict: 'C',
      scope: {
        'spec': '=',
        'result': '='
      },
      templateUrl: 'modules/sk0-auto-form/template.html',
      link: function postLink(scope) {
        scope.getFieldTemplate = function (type) {
          return fieldTypes[type];
        };

        scope.toMap = function (o) {
          return _.map(o, function (i) {
            return _.isObject(i) ? i : {
              key: i,
              value: i.charAt(0).toUpperCase() + i.slice(1)
            };
          });
        };

        _.each(scope.spec, function (e, index) {
          var id = e.key || index;
          if (!_.isUndefined(e.default) && _.isUndefined(scope.result[id])) {
            scope.result[id] = _.clone(e.default);
          }
        });
      }
    };

  });
