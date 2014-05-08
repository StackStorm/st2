'use strict';
angular.module('main')
  .directive('sk0AutoForm', function () {

    return {
      restrict: 'C',
      scope: {
        'spec': '=',
        'result': '='
      },
      templateUrl: 'directives/sk0-auto-form/template.html',
      link: function postLink(scope) {
        console.log('->', scope.result);
        _.each(scope.spec, function (e, index) {
          var id = e.key || index;
          if (!_.isUndefined(e.default) && _.isUndefined(scope.result[id])) {
            scope.result[id] = _.clone(e.default);
          }
        });
      }
    };

  });
