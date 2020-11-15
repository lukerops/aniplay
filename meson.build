project('aniplay',
          version: '0.1.0',
    meson_version: '>= 0.50.0',
          license: 'GPL3',
  default_options: [ 'warning_level=2',
                   ],
)

prettyname = 'Aniplay'
prettylicense = 'GPL-3.0+'

#i18n = import('i18n')

gio_dependency = dependency('gio-2.0', version: '>= 2.42.0')
glib_dependency = dependency('glib-2.0', version: '>= 2.42.0')
gtk_dependency = dependency('gtk+-3.0', version: '>= 3.24.0')
gst_dependency = dependency('gstreamer-1.0', version : '>= 1.14.1',
    fallback : ['gstreamer', 'gst_dep'])

pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'aniplay')

message(pkgdatadir)
message(moduledir)

install_subdir(meson.project_name(), install_dir : pkgdatadir)

subdir('data')
subdir('po')
subdir('bin')

meson.add_install_script('postinstall.py')
