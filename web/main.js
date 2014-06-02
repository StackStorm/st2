'use strict';

angular.module('main', ['ui.router', 'ngResource', 'angularMoment'])
  .config(function ($stateProvider, $urlRouterProvider) {
    $urlRouterProvider.otherwise('/rules');

    $stateProvider
      .state('act', {
        url: '/act',
        controller: 'sk0ActCtrl',
        templateUrl: 'apps/sk0-act/template.html',
        title: 'Act'
      })

      .state('rules', {
        url: '/rules',
        templateUrl: 'apps/sk0-rules/template.html',
        controller: 'sk0RulesCtrl',
        title: 'Rules'
      })
      .state('ruleConstructor', {
        url: '/rules/create',
        templateUrl: 'apps/sk0-rules/edit.html',
        controller: 'sk0RulesCreateCtrl'
      })
      .state('ruleEdit', {
        url: '/rules/:id',
        templateUrl: 'apps/sk0-rules/edit.html',
        controller: 'sk0RuleEditCtrl'
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
