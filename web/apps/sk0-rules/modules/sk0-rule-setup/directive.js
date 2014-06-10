'use strict';

angular.module('main')
  .directive('sk0RuleSetup', function () {

    return {
      restrict: 'C',
      scope: {
        type: '@',
        rule: '='
      },
      templateUrl: 'apps/sk0-rules/modules/sk0-rule-setup/template.html',
      controller: function ($scope, sk0Api, $filter) {
        $scope.inventoryIndex = $filter('unwrap')(sk0Api[$scope.type+'s']).index;

        if ($scope.type === 'trigger') {
          $scope.name = $scope.rule['trigger_type'].name;
        } else {
          $scope.name = $scope.rule[$scope.type].type;
        }


        $scope.formResults = {};

        $scope.$watch($scope.type === 'trigger' ? 'rule.criteria' : 'rule.action.mapping', function (options) {
          $scope.formResults = {};
          if (options) {
            if ($scope.type === 'trigger') {
              $scope.formResults = _.mapValues(options, function (e) {
                return e.pattern;
              });
            } else {
              $scope.formResults = _.clone($scope.rule[$scope.type].mapping);
            }
          }
        });

        $scope.submit = function () {
          if ($scope.type === 'trigger') {
            $scope.rule.action.mapping = undefined;

            $scope.rule.criteria = _.mapValues($scope.formResults, function (e) {
              return {
                pattern: e,
                operator: 'matchregex'
              };
            });
          } else {
            $scope.rule[$scope.type].mapping = _.clone($scope.formResults);
          }
        };
      }
    };

  });
