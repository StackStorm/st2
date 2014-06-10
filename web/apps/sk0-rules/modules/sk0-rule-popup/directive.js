'use strict';

angular.module('main')
  .directive('sk0RulePopup', function () {

    return {
      restrict: 'C',
      scope: {
        type: '@',
        rule: '='
      },
      templateUrl: 'apps/sk0-rules/modules/sk0-rule-popup/template.html',
      controller: function ($scope, sk0Api) {
        $scope.inventory = sk0Api;

        $scope.pick = function (entity) {
          if ($scope.type === 'trigger') {
            $scope.rule['trigger_type'] = { name: entity.name };
          } else {
            $scope.rule[$scope.type] = { type: entity.name };
          }

          if ($scope.rule['trigger_type'] && $scope.rule.action) {
            $scope.$parent.popup = null;
          } else {
            $scope.$parent.popup = $scope.type === 'trigger' ? 'action' : 'trigger';
          }
        };
      }
    };

  });
