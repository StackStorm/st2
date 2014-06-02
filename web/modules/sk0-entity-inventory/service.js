'use strict';

angular.module('main')
  .service('sk0EntityInventory', function($resource, $rootScope) {
    var scope = $rootScope.$new();

    function fetch(type) {
      var Resource = $resource('http://kandra.apiary-mock.com/' + type)
        , r = scope.$new();

      r.index = {};
      r.tree = {};

      Resource.query().$promise.then(function (data) {
        _.each(data, function (e) {
          r.index[e.name] = e;
          _.each(e.tags, function (tag) {
            var current = r.tree[tag] = r.tree[tag] || {};
            current.title = tag;
            current.entities = (current.entities || []).concat([e]);
          });
        });

        r.$$phase || r.$apply();
      });

      return r;
    }

    scope.triggers = fetch('triggers');
    scope.actions = fetch('actions');

    return scope;
  }).filter('unwrap', function () {
    return function (v) {
      if (v && v.then) {
        var p = v;
        if (!('$$v' in v)) {
          p.$$v = undefined;
          p.then(function(val) { p.$$v = val; });
        }
        v = v.$$v;
      }
      return v;
    };
  }).filter('toEntity', function (sk0EntityInventory, $filter) {
    return function (input, type) {
      var entity = $filter('unwrap')(sk0EntityInventory[type]);
      return entity && entity.index[input] || input;
    };
  });
