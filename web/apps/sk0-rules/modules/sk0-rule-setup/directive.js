'use strict';

angular.module('main')
  .directive('sk0RuleSetup', function () {

    return {
      restrict: 'C',
      scope: {
        type: '@'
      },
      templateUrl: 'apps/sk0-rules/modules/sk0-rule-setup/template.html',
      controller: function ($scope, sk0EntityInventory, $filter) {
        $scope.rule = $scope.$parent.rule;

        $scope.inventoryIndex = $filter('unwrap')(sk0EntityInventory[$scope.type+'s']).index;

        $scope.formResults = {};

        $scope.$watch('rule[type].options', function (options) {
          if (options) {
            $scope.formResults = _.clone(options);
          }
        });

        $scope.submit = function () {
          $scope.rule[$scope.type].options = $scope.formResults;
        };
      }
    };

  });
