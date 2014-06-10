'use strict';

angular.module('main')
  .directive('sk0RuleActivate', function () {

    return {
      restrict: 'C',
      scope: {
        rule: '='
      },
      templateUrl: 'apps/sk0-rules/modules/sk0-rule-activate/template.html',
      controller: function ($scope, $state, sk0Api) {
        $scope.formSpec = [{
          key: 'name',
          type: 'text',
          label: 'Name',
          required: true
        }, {
          key: 'desc',
          type: 'textarea',
          label: 'Description'
        }];

        $scope.formResults = {};

        $scope.$watch('rule', function (options) {
          $scope.formResults = options ? _.clone(options) : {};
        });

        $scope.submit = function (enable) {
          $scope.rule.name = _.clone($scope.formResults.name);
          $scope.rule.description = _.clone($scope.formResults.desc);

          if (!_.isUndefined(enable)) {
            $scope.rule.enable = !!enable;
          }

          if ($scope.form.$valid) {
            if ($scope.rule.id) {
              sk0Api.rules.update({ id: $scope.rule.id }, $scope.rule);
            } else {
              sk0Api.rules.create($scope.rule);
            }

            $state.go('rules');
          }
        };
      }
    };

  });
