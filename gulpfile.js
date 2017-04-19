var gulp = require('gulp');
var clean = require('gulp-clean');
var uglify = require('gulp-uglify');
var concat = require('gulp-concat');
var rename = require('gulp-rename');
var jshint = require('gulp-jshint');
var gutil = require('gulp-util');
var spawn = require('child_process').spawn;
var spawnSync = require('child_process').spawnSync;
var del = require('del');

var source = './html';
var destination = './dist';

gulp.task('html-clean', function () {
    return gulp.src(destination + '**', {read: false})
        .pipe(clean());
});

gulp.task('js-checkcode', function() {
    return gulp.src([
            source + '/js/**/*.js',
            '!' + source + '/js/libs/**/*.js'
        ])
        .pipe(jshint())
        .pipe(jshint.reporter());
});

gulp.task('js-minify', function() {
    return gulp.src([
            source + '/js/**/*.js',
            '!' + source + '/js/libs/**/*.js'
        ])
        .pipe(concat('raspiot.js'))
        .pipe(rename('raspiot.min.js'))
        .pipe(uglify())
        .pipe(gulp.dest(destination + '/html/js/'));
});

gulp.task('deb-build', function(cb) {
    var cmd = spawn('/usr/bin/debuild', ['-us', '-uc'], {
        cwd: './',
        env: process.env
    });
    cmd.stdout.on('data', function(data) {
        gutil.log(data.toString().trim());
        //console.log(data.toString().trim());
    });
    cmd.stderr.on('data', function(data) {
        gutil.log(gutil.colors.red(data.toString().trim()));
        //console.error(data.toString().trim());
    });
    cmd.on('close', function(code) {
        gutil.log(gutil.colors.green('Done ['+code.toString().trim()+']'));
        //console.log('Done ['+code.toString().trim()+']');
    });
});

gulp.task('deb-clean', function() {
    var cmd = spawnSync('/usr/bin/debuild', ['clean'], {cwd: './', env:process.env});
    cmd = spawnSync('/bin/rm', ['-rf', 'raspiot.egg-info'], {cwd:'./', env:process.env});
    cmd = spawnSync('/bin/rm', ['-rf', 'pyraspiot.egg-info/'], {cwd:'./', env:process.env});
});

gulp.task('deb-move', function() {
    return gulp.src([
            '../raspiot_*.build',
            '../raspiot_*.changes',
            '../raspiot_*.deb',
            '../raspiot_*.dsc',
            '../raspiot_*.tar.gz'
        ])
        .pipe(gulp.dest(destination))
        .pipe(del([
            '../raspiot_*.build',
            '../raspiot_*.changes',
            '../raspiot_*.deb',
            '../raspiot_*.dsc',
            '../raspiot_*.tar.gz'
        ], {force:true}));
});

gulp.task('deb', ['deb-build', 'deb-clean', 'deb-move']);

