# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.abspath('../'))

project = u''
copyright = u''
author = u''
version = u''
release = u''
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
]
source_suffix = '.rst'
master_doc = 'index'
language = None
exclude_patterns = [
    u'_build',
    'Thumbs.db',
    '.DS_Store',
    '**/*.pyc',
    'raspiot/tests/**',
    'raspiot/modules/**',
]
add_module_names = False
pygments_style = 'sphinx'
html_static_path = [
    '_static'
]
html_css_files = [
    '_static/cleep.css'
]
html_logo = '_static/cleep-logo-red.png'
html_favicon = '_static/favicon.ico'
todo_include_todos = True
autodoc_default_options = { 
    'undoc-members': True,
    'private-members': False,
}

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'prev_next_buttons_location': None,
    'style_external_links': True,
    'style_nav_header_background': '#607d8b',
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 6,
    'includehidden': False,
}

def setup(app):
    app.add_css_file('cleep.css')
    
