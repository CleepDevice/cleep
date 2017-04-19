var gulp = require('gulp');
var clean = require('gulp-clean');
var uglify = require('gulp-uglify');
var concat = require('gulp-concat');
var rename = require('gulp-rename');
var jshint = require('gulp-jshint');

var source = './html';
var destination = './dist';


gulp.task('clean', function () {
    return gulp.src(destination + '**', {read: false})
        .pipe(clean());
});

gulp.task('checkcode', function() {
    return gulp.src([
            source + '/js/**/*.js',
            '!' + source + '/js/libs/**/*.js'
        ])
        .pipe(jshint())
        .pipe(jshint.reporter());
});

gulp.task('minifyjs', function() {
    return gulp.src([
            source + '/js/**/*.js',
            '!' + source + '/js/libs/**/*.js'
        ])
        .pipe(concat('raspiot.js'))
        .pipe(rename('raspiot.min.js'))
        .pipe(uglify())
        .pipe(gulp.dest(destination + '/html/js/'));
});

gulp.task('dist', ['clean', 'checkcode', 'minifyjs']);

