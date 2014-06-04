'use strict';

angular.module('main')
  .directive('sk0Rule', function () {

    return {
      restrict: 'C',
      scope: {
        rule: '='
      },
      replace: true,
      templateUrl: 'apps/sk0-react/modules/sk0-rule/template.html',
      controller: function ($scope, $state, sk0EntityInventory) {
        $scope.services = sk0EntityInventory;
        $scope.edit = function (rule) {
          $state.go('ruleEdit', rule);
        };
      }
    };

  });
