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
var tar = require('gulp-tar');
var gzip = require('gulp-gzip');

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

gulp.task('js-uglify', function() {
    //uglify raspiot sources
    gulp.src([
            source + '/js/**/*.js',
            '!' + source + '/js/libs/**/*.js'
        ])
        .pipe(uglify())
        .pipe(rename({ extname: '.min.js'}))
        .pipe(gulp.dest(destination + '/html/js/'));

    //and copy libs that should be already minified
    return gulp.src([
            source + '/js/libs/**/*.js'
        ])
        .pipe(gulp.dest(destination + '/html/js/libs/'));
});

gulp.task('deb-build', function(cb) {
    var cmd = spawn('/usr/bin/debuild', ['-us', '-uc'], {
        cwd: './',
        env: process.env
    });
    cmd.stdout.on('data', function(data) {
        //gutil.log(data.toString().trim());
        console.log(data.toString());
    });
    cmd.stderr.on('data', function(data) {
        //gutil.log(gutil.colors.red(data.toString().trim()));
        console.error(data.toString());
    });
    cmd.on('close', function(code) {
        //gutil.log(gutil.colors.green('Done ['+code.toString().trim()+']'));
        console.log('Done ['+code.toString()+']');
    });
});

gulp.task('deb-clean', function() {
    spawnSync('/usr/bin/debuild', ['clean'], {cwd: './', env:process.env});
    spawnSync('/bin/rm', ['-rf', 'raspiot.egg-info'], {cwd:'./', env:process.env});
    spawnSync('/bin/rm', ['-rf', 'pyraspiot.egg-info/'], {cwd:'./', env:process.env});
    del([
        '../raspiot_*.build',
        '../raspiot_*.changes',
        '../raspiot_*.deb',
        '../raspiot_*.dsc',
        '../raspiot_*.tar.gz'
    ], {force:true});
});

gulp.task('deb-move', function() {
    return gulp.src([
            '../raspiot_*.build',
            '../raspiot_*.changes',
            '../raspiot_*.deb',
            '../raspiot_*.dsc',
            '../raspiot_*.tar.gz'
        ])
        .pipe(gulp.dest(destination));
});

gulp.task('deb', ['deb-build', 'deb-move', 'deb-clean']);

gulp.task('docs-html', function() {
    spawnSync('make', ['html'], {cwd: './docs/', env:process.env});
});

gulp.task('docs-xml', function() {
    spawnSync('make', ['xml'], {cwd: './docs/', env:process.env});
});

gulp.task('docs-move', function() {
    gulp.src('./docs/_build/html/**/*')
        .pipe(tar('raspiot-docs.tar'))
        .pipe(gzip())
        .pipe(gulp.dest(destination));
});

gulp.task('docs-clean', function() {
    spawnSync('make', ['clean'], {cwd: './docs/', env:process.env});
});

gulp.task('docs', ['docs-html', 'docs-move', 'docs-clean']);
