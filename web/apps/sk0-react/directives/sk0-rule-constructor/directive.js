'use strict';

angular.module('main')
  .directive('sk0RuleConstructor', function () {

    return {
      restrict: 'C',
      scope: {
        rule: '='
      },
      templateUrl: 'apps/sk0-react/directives/sk0-rule-constructor/template.html',
      link: function () {}
    };

  });
