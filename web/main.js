'use strict';

angular.module('main', ['ui.router', 'ngResource', 'angularMoment'])
  .config(function ($stateProvider, $urlRouterProvider) {
    $urlRouterProvider.otherwise('/react');

    $stateProvider
      .state('act', {
        url: '/act',
        controller: 'sk0ActCtrl',
        templateUrl: 'apps/sk0-act/template.html',
        title: 'Act'
      })

      .state('react', {
        url: '/react',
        templateUrl: 'apps/sk0-react/template.html',
        controller: 'sk0ReactCtrl',
        title: 'React',
        abstract: true
      })
      .state('react.list', {
        url: '',
        controller: 'sk0ReactListCtrl',
        templateUrl: 'apps/sk0-react/list.partial.html'
      })
      .state('react.triggers', {
        controller: 'sk0ReactPickCtrl',
        templateUrl: 'apps/sk0-react/pick.partial.html',
        data: {
          type: 'trigger'
        }
      })
      .state('react.triggers.setup', {
        controller: 'sk0ReactSetupCtrl',
        templateUrl: 'apps/sk0-react/setup.partial.html',
        params: ['type']
      })
      .state('react.actions', {
        controller: 'sk0ReactPickCtrl',
        templateUrl: 'apps/sk0-react/pick.partial.html',
        data: {
          type: 'action'
        }
      })
      .state('react.actions.setup', {
        controller: 'sk0ReactSetupCtrl',
        templateUrl: 'apps/sk0-react/setup.partial.html',
        params: ['type']
      })
      .state('react.test', {
        controller: 'sk0ReactTestCtrl',
        templateUrl: 'apps/sk0-react/test.partial.html'
      })

      .state('audit', {
        url: '/audit',
        controller: 'sk0AuditCtrl',
        templateUrl: 'apps/sk0-audit/template.html',
        title: 'Audit'
      });
  });

angular.module('main')
  .controller('MainCtrl', function ($scope, $state) {
    $scope.state = $state;

    // Don't forget to add a target for every href in menu
    // $scope.$on('$stateChangeStart', function (event, toState) {
    //   window.name = toState.name;
    // });
  });

angular.module('main')
  .filter('has', function () {
    return function (input, name) {
      return _.filter(input, function (e) {
        return !!e[name];
      });
    };
  });
