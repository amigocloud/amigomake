import os


class Package(object):
    # Creates a package from directory
    # Optional: list of source extensions to use when collecting files
    # Optional: custom package name (dir name by default)
    def __init__(self, directory, src_exts=None, package_name=None):
        self.__files = set()
        self.__deps = []
        self.__src_exts = src_exts
        self._package_dir = os.path.relpath(directory)
        self._install_dirs = {}
        self._cwd = os.getcwd()
        self._build_finished = False
        if package_name:
            self._package_name = package_name
        else:
            self._package_name = os.path.basename(self._package_dir)

            # Returns a set of files that matches the source extensions

    # Available after calling _collect_files()
    def files(self):
        return self.__files

    # Returns the package directory
    def package_dir(self):
        return self._package_dir

    # Sets the package directory
    def set_package_dir(self, package_dir):
        self._package_dir = package_dir

    # Sets the installation directory for the specified platform
    def set_install_dir(self, platform, install_dir):
        self._install_dirs[platform] = os.path.abspath(install_dir)

    # Returns the installation directory for the specified platform
    def install_dir(self, platform):
        if platform not in self._install_dirs:
            self.set_install_dir(platform, os.path.join(self._package_dir, 'build/'+platform.name()))
        return self._install_dirs[platform]

    # Collect files in the package dir that match the source extensions
    def _collect_files(self):
        if self._package_dir is not None:
            for (dirpath, dirnames, filenames) in os.walk(self._package_dir):
                for filename in filenames:
                    if check_extensions(filename, self.__src_exts):
                        self.__files.add(os.path.join(dirpath, filename))

    # Builds the package for a specified by calling:
    # _pre_build, _build, _post_build
    # Optional: additional environment variables
    def build(self, platform, env_vars=None):
        self._pre_build(platform, env_vars)
        self._build(platform, env_vars)
        self._post_build(platform, env_vars)

    # Adds a dependency on another package
    def add_dep(self, dep):
        self.__deps.append(dep)

    # Sets the list of dependencies
    def set_deps(self, deps):
        self.__deps = deps

    # Returns the dependecy list
    def deps(self):
        return self.__deps

    # Returns the package Name
    def name(self):
        return self._package_name

    # Cleans the package
    def clean(self, platform, clean_deps=False):
        self._build_finished = False

    # By default: Pre-build collects files and sets up environment vars
    def _pre_build(self, platform, env_vars=None):
        self._collect_files()
        platform.init_env_vars(env_vars)

    # Inherited classes should override _build
    def _build(self, platform, env_vars=None):
        pass

    # Inherited classes can override _post_build
    def _post_build(self, platform, env_vars=None):
        self._build_finished = True


# Checks the file extension against a provided list of extensions
def check_extensions(filename, extensions):
    for ext in extensions:
        if filename.lower().endswith(ext.lower()):
            return True
    return False


# Checks whether the file is older than the all files in the provided list 
def older(file_path, files_to_check):
    if not os.path.isfile(file_path):
        return True
    for file_to_check in files_to_check:
        if not os.path.isfile(file_to_check):
            return True
        if os.path.getmtime(file_path) <= os.path.getmtime(file_to_check):
            return True
    return False


def error_str(print_str):
    return '\033[91m' + print_str + '\033[0m'


def warn_str(print_str):
    return '\033[93m' + print_str + '\033[0m'


def ok_str(print_str):
    return '\033[92m' + print_str + '\033[0m'
    

        
    

