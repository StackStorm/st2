'use strict';

angular.module('main')
  .directive('sk0RuleTest', function () {

    return {
      restrict: 'C',
      scope: {
        rule: '=',
        type: '@',
        status: '='
      },
      templateUrl: 'apps/sk0-react/modules/sk0-rule-test/template.html',
      replace: true,
      link: function (scope) {
        scope.isPassed = function (type) {
          return scope.status && scope.status[type].response && (scope.status[type].response.err ? false : true);
        };
      }
    };

  });
