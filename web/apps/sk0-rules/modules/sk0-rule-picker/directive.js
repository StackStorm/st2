'use strict';

angular.module('main')
  .directive('sk0RulePicker', function () {

    return {
      restrict: 'C',
      scope: {
        originalRule: '=rule',
        hidePopup: '='
      },
      templateUrl: 'apps/sk0-rules/modules/sk0-rule-picker/template.html',
      controller: function ($scope, sk0Api) {
        $scope.inventory = sk0Api;

        $scope.popup = $scope.hidePopup ? null : 'trigger';

        $scope.rule = {};

        if ($scope.originalRule && $scope.originalRule.$promise) {
          $scope.originalRule.$promise.then(function (rule) {
            $scope.rule = _.clone(rule);
          });
        }

        $scope.submit = function () {
          $scope.originalRule = _.clone($scope.rule);
        };
      }
    };

  });
