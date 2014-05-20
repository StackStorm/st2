'use strict';

angular.module('main')
  .directive('sk0Modal', function () {

    return {
      restrict: 'C',
      transclude: true,
      templateUrl: 'modules/sk0-modal/template.html'
    };

  });
