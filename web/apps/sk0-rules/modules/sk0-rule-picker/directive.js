'use strict';

angular.module('main')
  .directive('sk0RulePicker', function () {

    return {
      restrict: 'C',
      scope: {
        rule: '='
      },
      templateUrl: 'apps/sk0-rules/modules/sk0-rule-picker/template.html',
      controller: function ($scope, sk0EntityInventory) {
        $scope.inventory = sk0EntityInventory;
      }
    };

  });
