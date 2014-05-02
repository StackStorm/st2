'use strict';

angular.module('main')
  .directive('sk0Rule', function () {

    return {
      restrict: 'C',
      scope: {
        rule: '='
      },
      templateUrl: 'apps/sk0-react/directives/sk0-rule/template.html',
      link: function (scope, element) {
        var expanded = false;

        scope.toggleExpand = function () {
          expanded = !expanded;
          element.toggleClass('sk0-rule--expanded', expanded);
        };

        scope.isExpanded = function () {
          return expanded;
        };
      }
    };

  });
