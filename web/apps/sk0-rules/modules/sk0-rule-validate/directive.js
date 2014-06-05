'use strict';

angular.module('main')
  .directive('sk0RuleValidate', function () {

    return {
      restrict: 'C',
      scope: true,
      templateUrl: 'apps/sk0-rules/modules/sk0-rule-validate/template.html',
      controller: function () {
        // Postponed, unreachable by the flow. For informational purposes only.
      }
    };

  });
