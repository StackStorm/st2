'use strict';

angular.module('main')
  .directive('sk0RuleActivate', function () {

    return {
      restrict: 'C',
      scope: {
        rule: '='
      },
      templateUrl: 'apps/sk0-rules/modules/sk0-rule-activate/template.html',
      controller: function ($scope) {
        $scope.formSpec = [{
          key: 'name',
          type: 'text',
          label: 'Name'
        }, {
          key: 'desc',
          type: 'textarea',
          label: 'Description'
        }];

        $scope.formResults = {};

        $scope.submit = function () {
          $scope.rule.name = _.clone($scope.formResults.name);
          $scope.rule.description = _.clone($scope.formResults.desc);
          console.log($scope.rule);
        };
      }
    };

  });
