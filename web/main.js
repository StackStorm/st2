'use strict';

angular.module('main', ['ui.router', 'ngResource', 'angularMoment'])
  .config(function ($stateProvider, $urlRouterProvider) {
    $urlRouterProvider.otherwise('/react');

    $stateProvider
    .state('act', {
      url: '/act',
      controller: 'Sk0ActCtrl',
      templateUrl: 'apps/sk0-act/template.html',
      name: 'sk0-act',
      title: 'Act'
    })
    .state('react', {
      url: '/react',
      controller: 'Sk0ReactCtrl',
      templateUrl: 'apps/sk0-react/template.html',
      name: 'sk0-react',
      title: 'React'
    })
    .state('audit', {
      url: '/audit',
      controller: 'Sk0AuditCtrl',
      templateUrl: 'apps/sk0-audit/template.html',
      name: 'sk0-audit',
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
