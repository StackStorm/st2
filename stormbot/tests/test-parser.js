/*jshint quotmark:false*/
/*global describe, it*/
'use strict';

var expect = require('chai').expect
  , parser = require('../lib/parser.js')
  ;

var basicShellSpec = {
  shell: {
    default: '/bin/bash'
  },
  cmd: {
    default: 'echo default'
  },
  irrelevant: {}
};

var typeSpec = {
  'command': {
    type: 'string'
  },
  'num': {
    type: 'integer'
  },
  'bool': {
    type: 'boolean'
  },
  'arr': {
    type: 'array'
  },
  'obj': {
    type: 'object'
  }
};

describe('Parser', function () {

  describe('specification', function () {

    it('should parse a string according to spec', function () {

      var o = parser('some', basicShellSpec);

      expect(o).to.be.an('object');
      expect(o).to.contain.key('shell');
      expect(o['shell']).to.be.equal('some');

    });

    it('should replace the keys that is not in argument string by their default values', function () {

      var o = parser('sh', basicShellSpec);

      expect(o).to.have.keys('shell', 'cmd');
      expect(o).to.be.deep.equal({
        shell: 'sh',
        cmd: 'echo default'
      });

    });

    it('should parse specific arguments', function () {

      var o = parser('cmd=/bin/true', basicShellSpec);

      expect(o).to.have.keys('shell', 'cmd');
      expect(o).to.be.deep.equal({
        shell: '/bin/bash',
        cmd: '/bin/true'
      });

    });

    it('should replace positional arguments with specific ones', function () {

      var o = parser('skipped_value "echo some" shell=/bin/zsh', basicShellSpec);

      expect(o).to.have.keys('shell', 'cmd');
      expect(o).to.be.deep.equal({
        shell: '/bin/zsh',
        cmd: 'echo some'
      });

    });

    it('should ignore positional arguments if there is no more specs for them', function () {

      var o = parser('/bin/zsh "echo some" thing else', basicShellSpec);

      expect(o).to.have.keys('shell', 'cmd', 'irrelevant');
      expect(o).to.be.deep.equal({
        shell: '/bin/zsh',
        cmd: 'echo some',
        irrelevant: 'thing'
      });

    });

    it('should not output arguments that has neither been defined through argstring nor has default value', function () {

      var o = parser('/bin/zsh "echo some"', basicShellSpec);

      expect(o).to.have.keys('shell', 'cmd');
      expect(o).to.be.deep.equal({
        shell: '/bin/zsh',
        cmd: 'echo some'
      });

    });

  });

  describe('type casting', function () {

    it('should cast argument to the type defined in spec', function () {

      var o = parser('count 10', typeSpec);

      expect(o).to.have.keys('command', 'num');
      expect(o['command']).to.be.a('string');
      expect(o['num']).to.be.a('number');
      expect(o).to.be.deep.equal({
        command: 'count',
        num: 10
      });

    });

    it('should cast argument type `integer` to integral number', function () {

      var o = parser('count 10.1', typeSpec);

      expect(o).to.have.keys('command', 'num');
      expect(o['command']).to.be.a('string');
      expect(o['num']).to.be.a('number');
      expect(o).to.be.deep.equal({
        command: 'count',
        num: 10
      });

    });

    it('should cast argument type `boolean` to bool', function () {

      var o1 = parser('bool=false', typeSpec);

      expect(o1).to.have.keys('bool');
      expect(o1['bool']).to.be.a('boolean');
      expect(o1).to.be.deep.equal({
        bool: false
      });

      var o2 = parser('bool=ok', typeSpec);

      expect(o2).to.have.keys('bool');
      expect(o2['bool']).to.be.a('boolean');
      expect(o2).to.be.deep.equal({
        bool: true
      });

    });

    it('should cast argument type `array` to array of strings by default', function () {

      var o1 = parser('arr=1,2,3,4', typeSpec);

      expect(o1).to.have.keys('arr');
      expect(o1['arr']).to.be.a('array');
      expect(o1).to.be.deep.equal({
        arr: ['1', '2', '3', '4']
      });

      var o2 = parser('arr="1, 2, 3, 4"', typeSpec);

      expect(o2).to.have.keys('arr');
      expect(o2['arr']).to.be.a('array');
      expect(o2).to.be.deep.equal({
        arr: ['1', '2', '3', '4']
      });

    });

    it('should cast argument type `array` to array of specific type', function () {

      var spec = {
        'arr': {
          type: 'array',
          items: {
            type: 'number'
          }
        }
      };

      var o1 = parser('arr=1,2,3,4', spec);

      expect(o1).to.have.keys('arr');
      expect(o1['arr']).to.be.a('array');
      expect(o1).to.be.deep.equal({
        arr: [1, 2, 3, 4]
      });

      var o2 = parser('arr="1, 2, 3, 4"', spec);

      expect(o2).to.have.keys('arr');
      expect(o2['arr']).to.be.a('array');
      expect(o2).to.be.deep.equal({
        arr: [1, 2, 3, 4]
      });

    });

    it('should cast argument type `array` to tuple-like structure of specific types', function () {

      var spec = {
        'arr': {
          type: 'array',
          items: [{
            type: 'number'
          }, {
            type: 'string'
          }]
        }
      };

      var o1 = parser('arr=1,2,3,4', spec);

      expect(o1).to.have.keys('arr');
      expect(o1['arr']).to.be.a('array');
      expect(o1).to.be.deep.equal({
        arr: [1, '2', '3', '4']
      });

      var o2 = parser('arr="1, 2, 3, 4"', spec);

      expect(o2).to.have.keys('arr');
      expect(o2['arr']).to.be.a('array');
      expect(o2).to.be.deep.equal({
        arr: [1, '2', '3', '4']
      });

    });

    it('should ignore additional arguments in tuple-like structures if option is set', function () {

      var spec = {
        'arr': {
          type: 'array',
          items: [{
            type: 'number'
          }, {
            type: 'string'
          }],
          additionalItems: false
        }
      };

      var o1 = parser('arr=1,2,3,4', spec);

      expect(o1).to.have.keys('arr');
      expect(o1['arr']).to.be.a('array');
      expect(o1).to.be.deep.equal({
        arr: [1, '2']
      });

      var o2 = parser('arr="1, 2, 3, 4"', spec);

      expect(o2).to.have.keys('arr');
      expect(o2['arr']).to.be.a('array');
      expect(o2).to.be.deep.equal({
        arr: [1, '2']
      });

    });

    it.skip('should cast argument type `object` to object', function () {

      var o1 = parser('obj=a:1,b:2,c:3,d:4', typeSpec);

      expect(o1).to.have.keys('obj');
      expect(o1['obj']).to.be.a('object');
      expect(o1).to.be.deep.equal({
        obj: {
          a: '1',
          b: '2',
          c: '3',
          d: '4'
        }
      });

      var o2 = parser('obj="a: 1, b: 2, c: 3, d: 4"', typeSpec);

      expect(o2).to.have.keys('obj');
      expect(o2['obj']).to.be.a('object');
      expect(o2).to.be.deep.equal({
        obj: {
          a: '1',
          b: '2',
          c: '3',
          d: '4'
        }
      });

    });

  });

  describe('quotes and literals', function () {

    it('should parse string by whitespaces', function () {

      var o = parser('sh /bin/true', basicShellSpec);

      expect(o).to.have.keys('shell', 'cmd');
      expect(o).to.be.deep.equal({
        shell: 'sh',
        cmd: '/bin/true'
      });

    });

    it('should respect quoted literals', function () {

      var o = parser('sh "echo some"', basicShellSpec);

      expect(o).to.have.keys('shell', 'cmd');
      expect(o).to.be.deep.equal({
        shell: 'sh',
        cmd: 'echo some'
      });

    });

    it('should preserve escaped quotes', function () {

      var o1 = parser('sh "echo \'some thing\'"', basicShellSpec);

      expect(o1).to.have.keys('shell', 'cmd');
      expect(o1).to.be.deep.equal({
        shell: 'sh',
        cmd: 'echo \'some thing\''
      });

      var o2 = parser("sh 'echo \"some thing\"'", basicShellSpec);

      expect(o2).to.have.keys('shell', 'cmd');
      expect(o2).to.be.deep.equal({
        shell: 'sh',
        cmd: 'echo \"some thing\"'
      });

    });

    it.skip('should preserve escaped characters inside quotes of the same type', function () {

      var o1 = parser('sh "echo \"some thing\""', basicShellSpec);

      expect(o1).to.have.keys('shell', 'cmd');
      expect(o1).to.be.deep.equal({
        shell: 'sh',
        cmd: 'echo \"some thing\"'
      });

      var o2 = parser("sh 'echo \'some thing\''", basicShellSpec);

      expect(o2).to.have.keys('shell', 'cmd');
      expect(o2).to.be.deep.equal({
        shell: 'sh',
        cmd: 'echo \'some thing\''
      });

    });

    it('should preserve other escaped characters', function () {

      var o1 = parser('sh "echo some\n"', basicShellSpec);

      expect(o1).to.have.keys('shell', 'cmd');
      expect(o1).to.be.deep.equal({
        shell: 'sh',
        cmd: 'echo some\n'
      });

      var o2 = parser("sh 'echo \tsome'", basicShellSpec);

      expect(o2).to.have.keys('shell', 'cmd');
      expect(o2).to.be.deep.equal({
        shell: 'sh',
        cmd: 'echo \tsome'
      });

    });

  });

});
