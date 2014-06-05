'use strict';

angular.module('main')
  .directive('sk0Menu', function () {

    return {
      restrict: 'C',
      scope: true,
      templateUrl: 'modules/sk0-menu/template.html',
      link: function postLink(scope) {
        scope.isMain = function (e) {
          return !!e.title;
        };
      }
    };

  });
