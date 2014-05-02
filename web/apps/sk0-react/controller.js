'use strict';
angular.module('main')
  .controller('Sk0ReactCtrl', function ($scope, $resource) {
    var Rules = $resource('http://kandra.apiary-mock.com/rules?expand=true');

    $scope.rules = Rules.query();
  });
