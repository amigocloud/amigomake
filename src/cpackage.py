from __future__ import print_function
from platform import crush_deps
from package import Package, older, check_extensions, error_str
from subprocess import call
import amigo_config
import multiprocessing
import os
import shutil
import re
import time
import sys

# Global vars needed to stop multi-threaded compilation on error
manager = multiprocessing.Manager()
failed_files = manager.list([])


class CPackage(Package):
    # Package output type
    SHARED_LIB = "shared_lib"
    STATIC_LIB = "static_lib"
    EXECUTABLE = "executable"
    EXTERNAL = "external"

    def __init__(self, directory, package_type, package_name=None, num_threads=None):
        self.__header_exts = ['.h', '.hpp']
        self.__src_exts = ['.c', '.cpp', '.cc', '.m', '.mm']
        super(CPackage, self).__init__(directory, self.__header_exts + self.__src_exts, package_name)
        self._num_threads = num_threads
        self._headers = set()
        self._sources = set()
        self._env_vars = {}
        self._appended_flags = {}
        self.__crush_ldflags = ''
        self.__outdated_sources = None
        self.__package_type = package_type
        self.__included_sources = []
        self.__excluded_sources = []
        self.__should_build_deps = True
        self.__should_install_headers = False
        self.__lib_prefix = 'lib'
        self.__deps_prefix = 'libdeps_' + self.name()
        self.__build_failed = False
        self.__is_clean = False
        self.__lib_path = None
        self.__obj_path = None
        self.__bin_path = None
        self.__inc_path = None
        self.__header_to_src_map = {}
        self.__src_to_header_map = {}
        self.__src_to_rel_header_map = {}
        self.__dep_libs = []
        self.__dep_lib_to_path_map = {}

    def __output_name(self, file_path):
        return self.name() + os.path.basename(os.path.splitext(file_path)[0] + '.o')

    def set_crush_ldflags(self, flags):
        self.__crush_ldflags = flags
        
    def add_ldflags(self, flags):
        if 'LDFLAGS' in self._appended_flags:
            self._appended_flags['LDFLAGS'] += ' ' + flags
        else:
            self._appended_flags['LDFLAGS'] = ' ' + flags

    def add_cflags(self, flags):
        if 'CFLAGS' in self._appended_flags:
            self._appended_flags['CFLAGS'] += ' ' + flags
        else:
            self._appended_flags['CFLAGS'] = ' ' + flags

    def add_cxxflags(self, flags):
        if 'CXXFLAGS' in self._appended_flags:
            self._appended_flags['CXXFLAGS'] += ' ' + flags
        else:
            self._appended_flags['CXXFLAGS'] = ' ' + flags

    def __add_dep_lib(self, lib, path, prepend=False):
        if prepend:
            self.__dep_libs.insert(0, lib)
        else:
            self.__dep_libs.append(lib)
        self.__dep_lib_to_path_map[lib] = path

    # Headers in the package
    # Available at beginning of the _build step
    def headers(self):
        return self._headers

    def set_header_exts(self, extensions):
        self.__header_exts = extensions
        
    def set_src_exts(self, extensions):
        self.__src_exts = extensions

    # Cleans the install directories
    def clean(self, platform, clean_deps=False):
        if self.__is_clean:
            return
        print (('\t%-15s\t' % (self.name() + ':')) + 'Cleaning')
        install_dir = self.install_dir(platform)
        if os.path.exists(install_dir):
            shutil.rmtree(install_dir)
        self.__is_clean = True
        if clean_deps:
            for dep in self.deps():
                dep.clean(platform, True)

    # Set sources to be compiled
    # The package by default compiles all source files in it's directory
    # This can be called to compile only a set of specific files
    def set_source_list(self, included_sources):
        self.__included_sources = included_sources

    # Sets source files that should be skipped during compilation
    def exclude_sources(self, excluded_sources):
        self.__excluded_sources = excluded_sources

    # Sets flag for whether dependencies should be built
    def should_build_deps(self, should_build):
        self.__should_build_deps = should_build

    # Sets flag for whether headers should be copies to the install dir
    def should_install_headers(self, should_install):
        self.__should_install_headers = should_install

    # Overrides default lib prefix of 'lib'
    def set_lib_prefix(self, prefix):
        self.__lib_prefix = prefix

    # Checks whether a filename is in the list of file names, if not it gets added
    def __check_duplicates(self, filename, files):
        if filename in files:
            print ((('\t%-15s\t' % (self.name() + ':')) +
                   error_str('ERROR') +
                   ': Duplicate source files found! (' + filename + ')\n\t' +
                   '\t\tPackage can only contain unique source filenames\n\t' +
                   '\t\tOtherwise object files will collide'))
            return True
        else:
            files.add(filename)
            return False

    # Builds the CPackage
    def _build(self, platform, env_vars=None):
        if not env_vars:
            env_vars = self._env_vars
        self.__is_clean = False
        if self._build_finished:
            return
        del failed_files[:]
        self.__build_failed = False
        # Create output directories
        self.__lib_path = os.path.join(self.install_dir(platform), 'lib')
        self.__obj_path = os.path.join(self.install_dir(platform), 'obj')
        self.__bin_path = os.path.join(self.install_dir(platform), 'bin')
        if not os.path.exists(self.__lib_path):
            os.makedirs(self.__lib_path)
        if not os.path.exists(self.__obj_path):
            os.makedirs(self.__obj_path)
        if not os.path.exists(self.__bin_path):
            os.makedirs(self.__bin_path)

        self.__outdated_sources = None

        # Collect all source files and headers to be compiled
        print (('\t%-15s\t' % (self.name() + ':')) + 'Checking Files')
        src_filenames = set()
        self.__collect_files_by_extension(src_filenames)
        print (('\t%-15s\t' % (self.name() + ':')) + 'Building Dependencies')
        dep_install_dirs = []
        for dep in self.deps():
            install_dir = dep.install_dir(platform)
            if self.__should_build_deps:
                dep.build(platform)
            for dep_header in dep.headers():
                self._headers.add(dep_header)
            if dep.__dep_libs:
                self.__dep_libs += dep.__dep_libs
                self.__dep_lib_to_path_map.update(dep.__dep_lib_to_path_map)
            elif not install_dir in dep_install_dirs:
                dep_install_dirs.insert(0, install_dir)
        dep_install_dirs = [x for x in dep_install_dirs
                            if os.path.join(x, 'lib') not in self.__dep_lib_to_path_map.values()]

        # Crush dependency libs into one static lib for IOS
        if self.__should_build_deps:
            print (('\t%-15s\t' % (self.name() + ':')) + 'Crushing Deps')
            index = 1
            for install_dir in dep_install_dirs:
                for (dirpath, dirnames, filenames) in os.walk(install_dir):
                    for filename in filenames:
                        if filename.startswith(self.__deps_prefix):
                            os.remove(os.path.join(dirpath, filename))
                if crush_deps(platform, install_dir, self.__deps_prefix + '_' + str(index), self.__crush_ldflags):
                    index += 1
        print (('\t%-15s\t' % (self.name() + ':')) + 'Initializing Source Maps')
        # Popuplate Source->Headers maps and Header->Sources maps
        self.__populate_src_maps()
        # Find Sources that require re-compilation
        self.__outdated_sources = self.__needs_recompile()
        if not self.__outdated_sources:
            print (('\t%-15s\t' % (self.name() + ':')) + 'No Changes Detected')
            return
        print (('\t%-15s\t' % (self.name() + ':')) + 'Configuring Platform')
        platform.configure(self.install_dir(platform), env_vars, None, self.deps())

        # Add linking flags
        print (('\t%-15s\t' % (self.name() + ':')) + 'Configuring Dependency Linking')
        for dep_lib in self.__dep_libs:
            if dep_lib in self.__dep_lib_to_path_map:
                platform.append_flags('LDFLAGS', " -L" + self.__dep_lib_to_path_map[dep_lib])
            platform.append_flags('LDFLAGS', " -l" + dep_lib)
        for install_dir in dep_install_dirs:
            lib_path = os.path.join(install_dir, "lib")
            dep_libs = set()
            match_found = False
            if os.path.exists(lib_path):
                for path in os.listdir(os.path.join(install_dir, "lib")):
                    match = re.match(r'(' + self.__deps_prefix + '.*)\.so', path)
                    if match:
                        lib = match.group(1).strip()[3:]
                        platform.append_flags('LDFLAGS', " -l" + lib)
                        self.__add_dep_lib(lib, lib_path)
                        match_found = True
                        break
                    else:
                        match = re.match(r'lib(.*)\.so.*', path)
                        if match:
                            dep_libs.add(match.group(1).strip())
            if not match_found:
                for dep_lib in dep_libs:
                    self.__add_dep_lib(dep_lib, lib_path)
                    platform.append_flags('LDFLAGS', " -l" + dep_lib)
        # Append custom flags
        try:
            app_flags = self._appended_flags.iteritems()
        except AttributeError:
            app_flags = self._appended_flags.items()
        for key, flags in app_flags:
            platform.append_flags(key, ' '+flags)

        self._compile(platform)
        if self.__build_failed:
            print (('\t%-15s\t' % (self.name() + ':')) + error_str('ERROR') + ': Compilation Failed!')
            sys.exit(1)
        else:
            self._link(platform)
            if self.__should_install_headers:
                self.__inc_path = os.path.join(self.install_dir(platform), 'include')
                if not os.path.exists(self.__inc_path):
                    os.makedirs(self.__inc_path)
                for header in self.headers():
                    shutil.copy(header, self.__inc_path)

    # Compilation step
    def _compile(self, platform):
        print (('\t%-15s\t' % (self.name() + ':')) + 'Compiling')
        start_time = time.time()
        compiler_pool = multiprocessing.Pool(self._num_threads)
        compiler_pool.map_async(CompilerFunc(self, platform), self._sources).get(9999999)
        print (('\t%-15s\t' % (self.name() + ':')) + 'Compiling took:\t' + str(time.time() - start_time) + 's')
        compiler_pool.close()
        compiler_pool.join()
        self.__build_failed = self.__build_failed or len(failed_files) > 0

    # Compiles a file for the specified platform with provided compiler and flags
    def compile_file(self, file_path, platform, cc, cflags):
        output_name = self.__output_name(file_path) 
        output = os.path.join(self.__obj_path, output_name)
        if (file_path not in self.__outdated_sources and
                not older(output, [file_path])):
            return
        if file_path in self.__src_to_header_map:
            self.__add_include_flags(file_path, cflags)
        call_str = cc + " -c " + file_path + " " + " -o " + output + " " + (' '.join(cflags))
        status = call([call_str], env=platform.var_env(), shell=True)
        if check_extensions(file_path, ['.cpp', '.cc', '.mm']):
            print ('\t  CXX\t' + file_path)
        else:
            print ('\t  CC\t' + file_path)
        if amigo_config.VERBOSE:
            print (call_str)
        if status != 0:
            failed_files.append(file_path)

    # Linking step
    def _link(self, platform):
        status = 0
        cc = platform.flags('CXX')
        ar = platform.flags('AR')
        ldflags = platform.flags('LDFLAGS').split()
        obj_files = []
        for (dirpath, dirnames, filenames) in os.walk(self.__obj_path):
            for filename in filenames:
                if(filename.startswith(self.name())):
                    obj_files.append(os.path.join(dirpath, filename))
        if self.__package_type == CPackage.STATIC_LIB:
            print (('\t%-15s\t' % (self.name() + ':')) + 'Preparing Static Library')
            output = os.path.join(self.__lib_path, self.__lib_prefix + self.name() + ".a")
            if not older(output, obj_files):
                return
            call_str = ar + " -r " + output + " " + (' '.join(obj_files))
            if amigo_config.VERBOSE:
                print (call_str)
            status = call([call_str], env=platform.var_env(), shell=True)
        elif self.__package_type == CPackage.SHARED_LIB:
            print (('\t%-15s\t' % (self.name() + ':')) + 'Preparing Shared Library')
            self.__add_dep_lib(self.name(), self.__lib_path, True)
            output = os.path.join(self.__lib_path, self.__lib_prefix + self.name() + ".so")
            if not older(output, obj_files):
                return
            call_str = (cc + " -shared -o " + output + " " +
                        (' '.join(obj_files)) + " " + (' '.join(ldflags)))
            if amigo_config.VERBOSE:
                print (call_str)
            status = call([call_str], env=platform.var_env(), shell=True)
        elif self.__package_type == CPackage.EXECUTABLE:
            print (('\t%-15s\t' % (self.name() + ':')) + 'Preparing Executable')
            output = os.path.join(self.__bin_path, self.name())
            if not older(output, obj_files):
                return
            call_str = (cc + " -o " + output + " " +
                        (' '.join(obj_files)) + " " + (' '.join(ldflags)))
            if amigo_config.VERBOSE:
                print (call_str)
            status = call([call_str], env=platform.var_env(), shell=True)
        if status != 0:
            print (('\t%-15s\t' % (self.name() + ':')) + error_str('ERROR') + ': Linking Failed!')
            sys.exit(1)

    # Appends required include flags to the passed cflags var 
    def __add_include_flags(self, file_path, cflags, files_added=set(), include_set=set()):
        def path_len(path):
            if os.path.normpath(self._package_dir) in path:
                return len(path) - len(self._package_dir)
            return len(path)
        headers = self.__src_to_rel_header_map[file_path]
        for header in headers:
            matched_headers = []
            for header_path in self._headers:
                if header_path.endswith(header):
                    matched_headers.append(header_path)
            if matched_headers:
                matched_headers = sorted(matched_headers, key=lambda x: path_len(x))
                header_path = matched_headers[0]
                if header_path in files_added:
                    continue
                files_added.add(header_path)
                include_path = header_path[:-len(header)]
                include_set.add(' -I' + include_path)

        for include_dir in include_set:
            cflags.append(include_dir)

    def __collect_files_by_extension(self, filenames=set()):
        for file_path in self.files():
            filename = os.path.basename(file_path)
            if check_extensions(file_path, self.__header_exts):
                self._headers.add(file_path)
            if check_extensions(file_path, self.__src_exts):
                file_excluded = False
                if self.__excluded_sources:
                    for exc_src in self.__excluded_sources:
                        if exc_src in file_path:
                            file_excluded = True
                            break
                if file_excluded:
                    continue
                if self.__included_sources:
                    for inc_src in self.__included_sources:
                        if os.path.basename(inc_src) == filename:
                            if self.__check_duplicates(filename, filenames):
                                sys.exit(1)
                            self._sources.add(file_path)
                            break
                else:
                    if self.__check_duplicates(filename, filenames):
                        return
                    self._sources.add(file_path)

    # Populates Source<-->Header maps
    def __populate_src_maps(self):
        for file_path in self._sources:
            self.__populate_src_maps_for_file(file_path)

    # Adds entry to Header->Sources map
    def __add_header_to_src_mapping(self, header_path, source_file):
        if header_path in self.__header_to_src_map:
            self.__header_to_src_map[header_path].add(source_file)
        else:
            self.__header_to_src_map[header_path] = {source_file}

    # Adds entry to Source->Headers map
    def __add_src_to_header_mapping(self, source_file, header_path):
        if source_file in self.__src_to_header_map:
            self.__src_to_header_map[source_file].add(header_path)
        else:
            self.__src_to_header_map[source_file] = {header_path}

    # Adds entry to Source->RelativeHeaders map
    # Relative header is the path in the actual #include statement
    def __add_src_to_rel_header_mapping(self, source_file, header_file):
        if source_file in self.__src_to_rel_header_map:
            self.__src_to_rel_header_map[source_file].add(header_file)
        else:
            self.__src_to_rel_header_map[source_file] = {header_file}

    # Recursively populate Source<-->Header maps for the given source file
    def __populate_src_maps_for_file(self, source_file):
        if not os.path.isfile(source_file):
            return
        files_checked = set()

        def include_loop(file_path):
            if file_path in files_checked:
                return
            files_checked.add(file_path)
            if file_path in self.__src_to_header_map:
                for header_rel_path in self.__src_to_rel_header_map[file_path]:
                    self.__add_src_to_rel_header_mapping(source_file, header_rel_path)
                for header_path in self.__src_to_header_map[file_path]:
                    self.__add_header_to_src_mapping(header_path, source_file)
                    self.__add_src_to_header_mapping(source_file, header_path)
                    include_loop(header_path)
                return
            for line in open(file_path):
                match = re.match(r'\s*#\s*include\s*("|<)\s*(.*)\s*("|>).*', line)
                if match:
                    header_file = match.group(2).strip()
                    header_file_name = os.path.basename(header_file)
                    for header_path in self._headers:
                        if os.path.basename(header_path) == header_file_name:
                            self.__add_header_to_src_mapping(header_path, source_file)
                            self.__add_src_to_header_mapping(source_file, header_path)
                            self.__add_src_to_rel_header_mapping(source_file, header_file)
                            if file_path is not source_file:
                                self.__add_src_to_header_mapping(file_path, header_path)
                                self.__add_src_to_rel_header_mapping(file_path, header_file)
                            include_loop(header_path)

        include_loop(source_file)

    # Returns a set of source files that require recompilation
    def __needs_recompile(self):
        sources_to_recompile = set()
        for source_file in self._sources:
            if not (source_file  in self.__src_to_header_map and self.__src_to_header_map[source_file]):
                obj_file = self.__output_name(source_file)
                obj_path = os.path.join(self.__obj_path, obj_file)
                if (not os.path.isfile(obj_path) or
                        older(obj_path, [source_file])):
                    sources_to_recompile.add(source_file)
        for header_file in self._headers:
            if header_file in self.__header_to_src_map:
                sources = self.__header_to_src_map[header_file]
                for source_file in sources:
                    obj_file = self.__output_name(source_file)
                    obj_path = os.path.join(self.__obj_path, obj_file)
                    if (not os.path.isfile(obj_path) or
                            older(obj_path, [header_file, source_file])):
                        sources_to_recompile.add(source_file)
        return sources_to_recompile

    def cmake(self, platform):
        print (('\t%-15s\t' % (self.name() + ':')) + 'Collecting Files')
        self._collect_files()
        print (('\t%-15s\t' % (self.name() + ':')) + 'Indexing Files')
        self.__collect_files_by_extension()
        self.__populate_src_maps()
        print (('\t%-15s\t' % (self.name() + ':')) + 'Collecting Header Dirs')
        include_dirs = []
        for file_path in self._sources:
            if file_path in self.__src_to_header_map:
                self.__add_include_flags(file_path, include_dirs)

        include_dirs = ' '.join(map(lambda x: "${PROJECT_SOURCE_DIR}/"+x[3:], list(set(include_dirs))))
        dep_include_dirs = set()
        for dep in self.deps():
            dep_dir = dep.install_dir(platform)
            if dep_dir is not None:
                dep_include_dirs.add(' ' + os.path.join(dep_dir, "include"))
        print (('\t%-15s\t' % (self.name() + ':')) + 'Creating CMakeLists.txt')
        cmake_file = open('CMakeLists.txt', 'w')
        print("cmake_minimum_required(VERSION 2.8)", file=cmake_file)
        print("project(%s)" % self.name(), file=cmake_file)
        print("include_directories(%s)" % (include_dirs + ' '.join(dep_include_dirs)), file=cmake_file)
        sources = []
        for ext in set(self.__header_exts + self.__src_exts):
            source_str = "SRC_FILES_" + str(ext[1:])
            sources.append("${%s}" % source_str)
            print("file(GLOB_RECURSE %s ${PROJECT_SOURCE_DIR}/*%s)" % (source_str, ext), file=cmake_file)
        if amigo_config.CXX11:
            print("set(CMAKE_CXX_FLAGS \"${CMAKE_CXX_FLAGS} -v -std=c++11 -stdlib=libc++\")", file=cmake_file)
        print("add_library(%s STATIC %s)" % (self.name(), ' '.join(sources)), file=cmake_file)


class CompilerFunc(object):
    def __init__(self, package, platform):
        self.__platform = platform
        self.__package = package

    def __call__(self, file_path):
        if failed_files:
            return
        self.__compile_file_path(self.__platform, file_path)

    def __compile_file_path(self, platform, file_path):
        if check_extensions(file_path, ['.c', '.m']):
            self.__c_build(file_path, platform)
        if check_extensions(file_path, ['.cpp', '.cc', '.mm']):
            self.__cpp_build(file_path, platform)

    # Compiles a c file for the specifies platform
    def __c_build(self, file_path, platform):
        cc = platform.flags('CC')
        cflags = platform.flags('CFLAGS').split()
        self.__package.compile_file(file_path, platform, cc, cflags)

    # Compiles a c file for the specifies platform
    def __cpp_build(self, file_path, platform):
        cc = platform.flags('CXX')
        cflags = platform.flags('CXXFLAGS').split()
        self.__package.compile_file(file_path, platform, cc, cflags)


