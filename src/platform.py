from subprocess import call
import amigo_config
import shutil
import os


def crush_deps(platform, install_dir, output_name, ldflags=''):
    cwd = os.getcwd()
    ar = platform.flags('AR')
    lipo = platform.flags('LIPO')
    cc = platform.flags('CXX')
    tmp_path = os.path.join(install_dir, 'tmp')
    lib_path = os.path.join(install_dir, 'lib')
    output = os.path.join(lib_path, output_name)
    if os.path.exists(tmp_path):
        shutil.rmtree(tmp_path)
    os.makedirs(tmp_path)
    # Find lib files
    lib_files = []
    for (dirpath, dirnames, filenames) in os.walk(lib_path):
        for filename in filenames:
            if filename.endswith('.a'):
                path = os.path.join(dirpath, filename)
                if not os.path.islink(path):
                    lib_files.append((path, filename[:-2]))
    for lib_file, lib_name in lib_files:
        extract_path = os.path.join(tmp_path, lib_name)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        os.makedirs(extract_path)
        os.chdir(extract_path)
        call_str = ar + " -x " + lib_file
        if amigo_config.VERBOSE:
            print (call_str)
        call([call_str], shell=True)
        files = os.listdir(extract_path)
        i = 0
        for file in files:
            if file.endswith('.o'):
                os.rename (file, lib_name+"_" + str(i) +".o")
                i += 1
        if lipo:
            call_str = lipo + ' -create -arch ' + platform.arch() + ' ' + lib_file + ' -output ' + lib_file
            if amigo_config.VERBOSE:
                print (call_str)
            call([call_str], shell=True)
    status = False
    os.chdir(tmp_path)
    if lib_files:
        ar_flag = 'crus'
        call_str = ar + ' ' + ar_flag + ' ' + output + '.a' + " " +tmp_path+"/*/*.o"
        if amigo_config.VERBOSE:
            print (call_str)
        call([call_str], shell=True)
        if lipo:
            call_str = lipo + ' -create -arch ' + platform.arch() + ' ' + output + '.a' + ' -output ' + output + '.a'
            if amigo_config.VERBOSE:
                print (call_str)
            call([call_str], shell=True)
        call_str = (cc + " -shared -o " + output + '.so' +
            " -Wl,--whole-archive " + output + '.a' + " -Wl,--no-whole-archive " + ldflags)
        if amigo_config.VERBOSE:
            print (call_str)
        call([call_str], shell=True)
        status = True
    os.chdir(cwd)
    return status


class Platform(object):
    CONFIG_FLAGS = 'configure_flags'

    def __init__(self, name, arch, sdk_path=None):
        self.__name = name
        self.__arch = arch
        self.__sdk_path = sdk_path
        self.__env = Environment()
        self._toolchain = None
        self.__var_env = os.environ.copy()
        self.__default_flags = {}
        self._set_default_flags('AR', "ar")
        cxx_modifiers = ''
        if amigo_config.CXX11:
            cxx_modifiers += ' -std=c++11'
        if amigo_config.GCC:
            self._set_default_flags('CC', "gcc")
            self._set_default_flags('CXX', "g++" + cxx_modifiers)
        else:
            self._set_default_flags('CC', "clang")
            self._set_default_flags('CXX', "clang++" + cxx_modifiers)

    # Platform Name (eg. iPhoneOS)
    def name(self):
        return self.__name

    def unique_name(self):
        return self.__name

    # Target Architecture (eg. armv7)
    def arch(self):
        return self.__arch

    # Path to SDK (if available)
    def sdk_path(self):
        return self.__sdk_path

    # Platform's Environment
    def env(self):
        return self.__env

    # Toolchain (if available)
    def toolchain(self):
        return self._toolchain

    # Initializes default environment variable
    # Should be called vefore building or configuring
    # Optional: takes additional environment variable to initialize
    def init_env_vars(self, env_vars=None):
        self.__var_env = os.environ.copy()
        for flag_key in self.__default_flags:
            self.__var_env[flag_key] = self.default_flags(flag_key)
        if env_vars:
            for flag_key in env_vars:
                self.__var_env[flag_key] = env_vars[flag_key]

    # Environment Variables
    def var_env(self):
        return self.__var_env

    # Calls configure with the provided installation dir
    # Optional: takes additional environment variables
    # Optional: override the configure call string, or None to skip the call
    # Optional: package dependencies
    def configure(self, install_dir, env_vars=None, configure="", deps=None):
        self.init_env_vars(env_vars)

        dep_dirs = {install_dir}

        if deps:
            for dep in deps:
                dep_dir = dep.install_dir(self)
                if dep_dir is not None:
                    dep_dirs.add(dep_dir)
                else:
                    print ('No install dir in package ' + dep.name() + ' for ' + self.name())

        for dep_dir in dep_dirs:
            lib_path = os.path.join(dep_dir, "lib")
            inc_path = os.path.join(dep_dir, "include")
            if not " -L" + lib_path in self.flags('LDFLAGS'):
                self.append_flags('LDFLAGS', " -L" + lib_path)
            if not lib_path in self.flags('LD_LIBRARY_PATH'):
                self.append_flags('LD_LIBRARY_PATH', ":" + lib_path)
            if not " -I" + lib_path in self.flags('CFLAGS'):
                self.append_flags('CFLAGS', " -I" + inc_path)
            if not " -I" + lib_path in self.flags('CXXFLAGS'):
                self.append_flags('CXXFLAGS', " -I" + inc_path)

        if configure is not None:
            if configure == "":
                configure = "./configure " + self.default_flags(Platform.CONFIG_FLAGS)
            if configure.startswith('cmake'):
                configure += " -DCMAKE_INSTALL_PREFIX:PATH=" + install_dir
            else:
                configure += " --prefix=" + install_dir
            if amigo_config.VERBOSE:
                print (configure)
            call([configure], shell=True, env=self.var_env())

    def _set_default_flags(self, key, flags):
        self.__default_flags[key] = flags

    # Retrieve default flags for the provided key
    def default_flags(self, key):
        if key in self.__default_flags:
            return self.__default_flags[key]
        else:
            return ""

    # Appends default environment vars
    # (To be set by inherited platforms)
    def append_default_flags(self, key, flags):
        if key in self.__default_flags:
            self.__default_flags[key] += ' ' + flags
        else:
            self.__default_flags[key] = flags

    # Retrieve all set flags for the provided key should
    def flags(self, key):
        if key in self.__var_env:
            return self.__var_env[key]
        else:
            return ""

    # Append additional flags to the provided environment var
    def append_flags(self, key, flags):
        if key in self.__var_env:
            self.__var_env[key] += ' ' + flags
        else:
            self.__var_env[key] = flags

    # Sets flags for provided environment var
    def set_flags(self, key, flags):
        self.__var_env[key] = flags


class Environment(object):
    # Autodetects environment system using uname
    def __init__(self):
        self.__system = "windows"
        try:
            (sysname, nodename, release, version, machine) = os.uname()
            self.__system = sysname.lower() + '-' + machine.lower()
        except:
            pass

    def system(self):
        return self.__system


class Toolchain(object):
    def __init__(self, version, platform, install_path):
        self.__version = version
        self.__platform = platform
        self.__install_path = install_path

    def path(self):
        return self.__install_path

    def platform(self):
        return self.__platform

    def version(self):
        return self.__version

