'use strict';

angular.module('main')
  .service('sk0Api', function($resource, $rootScope) {
    var HOST = '//172.168.50.50:9101';

    var scope = $rootScope.$new();

    function fetchInventory(type) {
      var Resource = $resource(HOST + '/' + type)
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

    scope.rules = $resource(HOST + '/rules', {}, {
      list: {
        method: 'GET',
        isArray: true
      },
      create: {
        method: 'POST'
      },
      get: {
        method: 'GET',
        url: HOST + '/rules/:id'
      },
      update: {
        method: 'PUT',
        url: HOST + '/rules/:id'
      },
      remove: {
        method: 'DELETE',
        url: HOST + '/rules/:id'
      },
      activate: {
        method: 'PUT',
        url: HOST + '/rules/:id/enable'
      },
      deactivate: {
        method: 'DELETE',
        url: HOST + '/rules/:id/enable'
      }
    });

    scope.triggers = fetchInventory('triggers');
    scope.actions = fetchInventory('actions');

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
  }).filter('toEntity', function (sk0Api, $filter) {
    return function (input, type) {
      var entity = $filter('unwrap')(sk0Api[type]);
      return entity && entity.index[input] || input;
    };
  });
