'use strict';
angular.module('main')
  .controller('sk0ReactCtrl', function ($scope) {
    // We need to define it here to allocate this variable in a prototype chain for other controllers.
    $scope.rule = {};

    $scope.setRule = function (rule) {
      $scope.rule = rule || {};
    };
  })
  .controller('sk0ReactListCtrl', function ($scope, $resource) {
    var Rules = $resource('http://kandra.apiary-mock.com/rules');

    $scope.rules = Rules.query();
  })
  .controller('sk0ReactPickCtrl', function ($scope, sk0EntityInventory, $state) {
    $scope.type = $state.params.type;

    $scope.services = sk0EntityInventory[$scope.type + 's'];

    $scope.pick = function (entity) {
      $scope.rule[$scope.type] = { type: entity };
      if ($scope.rule.trigger && $scope.rule.action) {
        $state.go('^.setup', { type: 'trigger' });
      } else {
        $state.go('.', { type: $scope.type === 'trigger' ? 'action' : 'trigger' });
      }
    };
  })
  .controller('sk0ReactSetupCtrl', function ($scope, $state, $stateParams) {
    $scope.type = $stateParams.type;
    $scope.formResults = _.clone($scope.rule[$scope.type].options) || {};

    $scope.submit = function () {
      $scope.rule[$scope.type].options = $scope.formResults;
      if ($scope.rule.trigger.options && $scope.rule.action.options) {
        $state.go('^.validate');
      } else {
        $state.go('.', { type: $scope.type === 'trigger' ? 'action' : 'trigger' });
      }
    };
  })
  .controller('sk0ReactTestCtrl', function ($scope, $resource, $state) {
    var Rules = $resource('http://:baseURL/rules', {
      baseURL: 'kandra.apiary-mock.com'
    }, {
      confirm: { url: 'http://:baseURL/rules/:id/activate', method: 'PUT' },
      log: { url: 'http://:baseURL/rules/:id/log', isArray: true }
    });

    $scope.result = Rules.save({
      trigger: {
        type: $scope.rule.trigger.type.name,
        options: $scope.rule.trigger.options
      },
      action: {
        type: $scope.rule.action.type.name,
        options: $scope.rule.action.options
      }
    });

    $scope.result.$promise.then(function (rule) {
      var timer = setInterval(function () {

        Rules.log({ id: rule.id }, function (logs) {
          $scope.logs = logs[logs.length - 1];

          if ($scope.isPassed('trigger') !== undefined && $scope.isPassed('action') !== undefined) {
            clearInterval(timer);
          }
        });
      }, 3000);
    });

    $scope.isPassed = function (type) {
      return $scope.logs && $scope.logs[type].response && ($scope.logs[type].response.err ? false : true);
    };

    $scope.cancel = function () {
      $scope.setRule();
      $state.go('^.list');
    };

    $scope.save = function () {
      $scope.result.$promise.then(function (rule) {
        console.log(rule);
        rule.$confirm({ id: rule.id }, function () {
          $scope.setRule();
          $state.go('^.list');
        });
      });
    };

    console.log(Rules);
  });
