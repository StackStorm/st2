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

    $scope.formFields = [
      {
        key: 'username',
        default: 'uberuser',
        type: 'text',
        label: 'Username',
        placeholder: 'johndoe',
        disabled: true,
        description: 'Simple single line description'
      },
      {
        key: 'password',
        type: 'password',
        label: 'Password',
        required: true,
        description: 'Simple multiline description that unfolds when the field it related to is in focus'
      },
      {
        key: 'not-a-password',
        type: 'password',
        label: 'Not a password',
        default: 'thing',
        description:
          ['Complex multiline string',
           '========================',
           'Markdown-formatted. Not ready yet.'
          ].join('\n')
      }
    ];

    $scope.results = {
      password: 'some'
    };

    $scope.submit = function () {
      $state.go('^', { rule: JSON.stringify($scope.rule) });
    };
  });
