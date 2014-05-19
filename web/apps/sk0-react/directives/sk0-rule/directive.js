'use strict';

angular.module('main')
  .directive('sk0Rule', function () {

    return {
      restrict: 'C',
      scope: {
        rule: '='
      },
      replace: true,
      templateUrl: 'apps/sk0-react/directives/sk0-rule/template.html',
      controller: function ($scope, $state) {
        $scope.edit = function (rule) {
          $scope.$parent.setRule(rule);
          $state.go('^.test');
        };
      }
    };

  });
