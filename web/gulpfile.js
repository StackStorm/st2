/* jshint node: true */
'use strict';

var gulp = require('gulp')
  , jshint = require('gulp-jshint')
  , path = require('path')
  , es = require('event-stream')
  , less = require('gulp-less')
  , concat = require('gulp-concat')
  , serve = require('gulp-serve')
  ;

var settings = {
  dev: '.',
  js: ['apps/**/*.js', 'modules/**/*.js', 'main.js'],
  styles: {
    src: ['less/style.less', 'apps/**/*.less', 'modules/**/*.less'],
    includes: 'less/',
    dest: 'css'
  },
  html: 'index.html'
};


var debug = function () {
  return es.through(function write(data) {
    console.log('WRITE:', data ? data.path : '');
    console.log(data ? data.contents.toString() : '');
    this.emit('data', data);
  }, function end(data) {
    console.log('END:', data ? data.path : '');
    console.log(data ? data.contents.toString() : '');
    this.emit('end', data);
  });
};

debug();


gulp.task('gulphint', function () {
  return gulp.src('gulpfile.js')
    .pipe(jshint())
    .pipe(jshint.reporter('default'))
    ;
});

gulp.task('scripts', function () {
  return gulp.src(settings.js, { cwd: settings.dev })
    .pipe(jshint())
    .pipe(jshint.reporter('default'))
    ;
});

gulp.task('styles', function () {
  return gulp.src(settings.styles.src, { cwd: settings.dev })
    .pipe(less({ paths: path.join(settings.dev, settings.styles.includes) }))
    .on('error', function(err) {
      console.warn(err.message);
    })
    .pipe(concat('style.css'))
    .pipe(gulp.dest(path.join(settings.dev, settings.styles.dest)))
    ;
});

gulp.task('serve', serve(__dirname));


gulp.task('watch', function () {
  gulp.watch(settings.js, ['scripts']);
  gulp.watch(settings.styles.src.concat(settings.styles.includes), ['styles']);
});


gulp.task('default', ['gulphint', 'scripts', 'styles', 'watch', 'serve']);
