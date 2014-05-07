'use strict';
angular.module('main')
  .controller('sk0ReactCtrl', function ($scope) {
    // We need to define it here to allocate this variable in a prototype chain for other controllers.
    $scope.rule = {};
  })
  .controller('sk0ReactListCtrl', function ($scope, $resource) {
    var Rules = $resource('http://kandra.apiary-mock.com/rules?expand=true');

    $scope.rules = Rules.query();
  })
  .controller('sk0ReactPickerCtrl', function ($scope, $resource, $state) {
    var Services = $resource('http://kandra.apiary-mock.com/services');

    $scope.services = Services.get();

    $scope.type = $state.current.data.type;
    $scope.rule[$scope.type] = {};

    $scope.pick = function (entity) {
      $scope.rule[$scope.type] = entity;
      $state.go('.setup', { type: $scope.type });
    };
  })
  .controller('sk0ReactSetupCtrl', function ($scope, $state, $stateParams) {
    $scope.type = $stateParams.type;

    $scope.submit = function () {
      $state.go('^', { rule: JSON.stringify($scope.rule) });
    };
  });
