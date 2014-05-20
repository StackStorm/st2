'use strict';

angular.module('main')
  .service('sk0EntityInventory', function($resource) {
    var Triggers = $resource('http://kandra.apiary-mock.com/triggers')
      , Actions = $resource('http://kandra.apiary-mock.com/actions')
      ;

    var methods = {};

    methods.triggers = Triggers.query();
    methods.actions = Actions.query();

    return methods;
  });
