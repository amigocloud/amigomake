from subprocess import call
from multiprocessing import cpu_count
from cpackage import CPackage
from package import error_str, warn_str
import amigo_config
import zipfile
import tarfile
import os
import sys
import shutil


class ExternalCPackage(CPackage):
    def __init__(self, version, rootdir, package_type=CPackage.EXTERNAL, package_name=None, num_threads=1):
        if not package_name:
            package_name = self.__class__.__name__
        super(ExternalCPackage, self).__init__(rootdir, package_type, package_name, num_threads)
        self._package_dir = os.path.abspath(rootdir)
        self.__version = version
        self.__zipname = None
        self.__local_path = None
        self.__url = None
        self.__patches = []
        self.__files_to_copy = []
        self.__cwd = os.getcwd()

    # Returns the root directory for the package
    def rootdir(self):
        return self._package_dir

    # Returns package version
    def version(self):
        return self.__version

    # Sets the path where the source resides
    def set_local_path(self, local_path):
        self.__local_path = os.path.abspath(local_path)

    # Returns the path where the source resides
    def local_path(self):
        return self.__local_path

    # Sets URL from which the package may be downloaded
    def set_url(self, url):
        self.__url = url

    # Returns URL from which the package may be downloaded
    def url(self):
        return self.__url

    # Sets the name of the downloaded compressed file
    def set_zip_name(self, zipname):
        self.__zipname = zipname

    # Returns the name of the downloaded compressed file
    def zip_name(self):
        return self.__zipname

    # Downloads and unzips the package(to '.' by default)
    # Tar and Zip formats are supported
    # Optional: unzip path
    # Optional: number of retries
    def _download_and_unzip(self, install_dir, unzip_path=None, retries=3):
        if not unzip_path:
            unzip_path = self.rootdir()
        try:
            if not os.path.exists(self.__zipname):
                curl_call = ["curl", "-L", "-o", self.__zipname, self.__url] 
                if amigo_config.VERBOSE:
                    print ' '.join(curl_call)
                call(curl_call)
                if self.__zipname.endswith('.zip'):
                    archive = zipfile.ZipFile(self.__zipname, "r")
                else:
                    archive = tarfile.open(self.__zipname)
            else:
                if self.__zipname.endswith('.zip'):
                    archive = zipfile.ZipFile(self.__zipname, "r")
                else:
                    archive = tarfile.open(self.__zipname)

            if self.__zipname.endswith('.zip'):
                namelist = archive.namelist()
            else:
                namelist = archive.getnames()
            if len(namelist) > 0:
                path = namelist[0]
                if path.startswith('./'):
                    path = path[2:]
                index = path.find("/")
                if index > 0:
                    path = path[:index]
                path = os.path.join(unzip_path, path)
                if unzip_path == self.rootdir():
                    self.set_local_path(path)
                else:
                    self.set_local_path(unzip_path)
                if os.path.exists(self.local_path()):
                    shutil.rmtree(self.local_path())
                archive.extractall(unzip_path)
            if amigo_config.VERBOSE:
                print "Project Path: " + self.local_path()                
            archive.close()
        except:
            if os.path.exists(self.__zipname):
                os.remove(self.__zipname)
            if retries > 0:
                print (('\t%-15s\t' % (self.name() + ':')) + warn_str('WARNING') +
                       ': Could not download/unzip source. Retrying!')
                self._download_and_unzip(install_dir, unzip_path, retries - 1)
            else:
                print (('\t%-15s\t' % (self.name() + ':')) + error_str('ERROR') +
                       ': Could not download/unzip source')
                sys.exit(1)

    # Pre Build step: download, unzip, build deps
    def _pre_build(self, platform, env_vars=None):
        self.__cwd = os.getcwd()
        if not os.path.exists(self.rootdir()):
            os.makedirs(self.rootdir())
        os.chdir(self.rootdir())

        if self.__local_path is None:
            install_dir = os.path.abspath(self.install_dir(platform))
            self._download_and_unzip(install_dir)

        if self.__local_path is None:
            return False

        for to_copy in self.__files_to_copy:
            dst = os.path.join(self.__local_path, to_copy[1])
            src = to_copy[0]
            print ('\t%-15s\t' % (self.name() + ':')) + "Copying file " + src + " to " + dst
            shutil.copy(src, dst)

        for dep in self.deps():
            dep.build(platform)

        return True

    # Build step: configure, make
    def _build(self, platform, env_vars=None, configure=""):
        install_dir = os.path.abspath(self.install_dir(platform))
        if not env_vars:
            env_vars = self._env_vars
        for key, flags in self._appended_flags.iteritems():
            if key in env_vars:
                env_vars[key] += ' '+flags
            else:
                env_vars[key] = platform.default_flags(key)+' '+flags
        os.chdir(self.__local_path)
        platform.configure(install_dir, env_vars, configure, self.deps())
        self._make(platform, install_dir)

    # Post Build step: restore cwd, and collect installed headers
    def _post_build(self, platform, env_vars=None):
        os.chdir(self.__cwd)
        self._build_finished = True

    # Builds the package
    def build(self, platform, env_vars=None, configure=""):
        if self._build_finished:
            return
        if not env_vars:
            env_vars = self._env_vars

        if self._pre_build(platform):
            self._build(platform, env_vars, configure)
        self._post_build(platform)

    # Make step
    def _make(self, platform, install_dir):
        if self._num_threads:
            mt = '-j' + str(self._num_threads)
        else:
            mt = '-j' + str(cpu_count())
        call(["make", mt], env=platform.var_env())
        call(["make", "install"], env=platform.var_env())

    # Adds a file to copy to a path relative to the source dir
    def copy_to_src(self, copy_from, copy_to):
        self.__files_to_copy.append([os.path.abspath(copy_from), copy_to])

    # Adds a patch file (.patch or tar file)
    # Inherited packages should call apply_patch if needed
    def add_patch_file(self, patch_path):
        patch_path = os.path.abspath(patch_path)
        self.__patches.append(patch_path)

    # Clears the patches
    def remove_patches(self):
        self.__patches = []

    # Applies the set patches
    def apply_patches(self):
        for patch_file in self.__patches:
            if patch_file.endswith(".patch"):
                self.__patch_file(patch_file)
            else:
                self.__patch_zip(patch_file)

    # Applies a patch
    @staticmethod
    def __patch_file(patchpath):
        call_str = "patch -p1 < " + patchpath
        if amigo_config.VERBOSE:
            print call_str
        call([call_str], shell=True)

    # Applies a archive of patches (tar format supported)
    def __patch_zip(self, patchpath):
        tar = tarfile.open(patchpath)
        tar.extractall()
        for patch_file in tar.getnames():
            if patch_file.endswith(".patch"):
                self.__patch_file(patch_file)
        tar.close()
