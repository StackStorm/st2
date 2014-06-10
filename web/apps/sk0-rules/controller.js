'use strict';
angular.module('main')

  // List rules
  .controller('sk0RulesCtrl', function ($scope, sk0Api) {
    $scope.rules = sk0Api.rules.list();
  })

  // Create new rule
  .controller('sk0RuleCreateCtrl', function ($scope) {
    $scope.rule = {};
  })

  // Edit existing rule
  .controller('sk0RuleEditCtrl', function ($scope, $state, sk0Api, $filter) {
    $scope.rule = $filter('unwrap')(sk0Api.rules.get($state.params));
    $scope.hidePopup = true;

    $scope.button = {};
  });
