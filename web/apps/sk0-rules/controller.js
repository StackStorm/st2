'use strict';
angular.module('main')

  // List rules
  .controller('sk0RulesCtrl', function ($scope, $resource) {
    var Rules = $resource('http://kandra.apiary-mock.com/rules');

    $scope.rules = Rules.query();
  })

  // Create new rule
  .controller('sk0RuleCreateCtrl', function ($scope) {
    $scope.rule = {};
  })

  // Edit existing rule
  .controller('sk0RuleEditCtrl', function ($scope, $state, $resource, $filter) {
    var Rule = $resource('http://kandra.apiary-mock.com/rules/:id');

    $scope.rule = $filter('unwrap')(Rule.get($state.params));
    $scope.hidePopup = true;

    $scope.button = {};
  });
