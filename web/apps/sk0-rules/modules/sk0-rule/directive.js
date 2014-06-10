'use strict';

angular.module('main')
  .directive('sk0Rule', function () {

    return {
      restrict: 'C',
      scope: {
        rule: '='
      },
      replace: true,
      templateUrl: 'apps/sk0-rules/modules/sk0-rule/template.html',
      controller: function ($scope, $state, sk0Api) {
        $scope.services = sk0Api;

        $scope.edit = function (rule) {
          $state.go('ruleEdit', rule);
        };

        $scope.remove = function (rule) {
          sk0Api.rules.remove({ id: rule.id });
        };

        $scope.toggle = function (rule) {
          sk0Api.rules[rule.enable ? 'deactivate' : 'activate']({ id: rule.id });
        };
      }
    };

  });
