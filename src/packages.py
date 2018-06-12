from platform import Platform
from x86_platform import X86Platform
from android_platform import AndroidPlatform
from ios_platform import IOSPlatform
from external_cpackage import ExternalCPackage
from cpackage import CPackage
from subprocess import call
from multiprocessing import cpu_count
import os
import shutil


def _patch_libtool(module):
    os.chdir(module.local_path())
    shutil.move("libtool", "libtool~")
    call(['sed "s/library_names_spec=\".*\"/library_names_spec=\"~##~libname~##~{shared_ext}\"/" libtool~ > libtool~1'],
         shell=True)
    call(['sed "s/soname_spec=\".*\"/soname_spec=\"~##~{libname}~##~{shared_ext}\"/" libtool~1 > libtool~2'],
         shell=True)
    call(['sed "s/~##~/\\\\$/g" libtool~2 > libtool'], shell=True)
    call(['chmod', 'u+x', 'libtool'])


class Proj4(ExternalCPackage):
    def __init__(self, version, rootdir):
        super(Proj4, self).__init__(version, rootdir)
        self.set_zip_name("proj-" + version + ".tar.gz")
        self.set_url("http://download.osgeo.org/proj/" + self.zip_name())

    def _build(self, platform, env_vars=None, configure=""):
        configure = "./configure " + (platform.default_flags(platform.CONFIG_FLAGS) +
                                      " --without-jni")
        super(Proj4, self)._build(platform, env_vars, configure)

class Png(ExternalCPackage):
    def __init__(self, version, rootdir):
        super(Png, self).__init__(version, rootdir)
        self.set_zip_name("libpng-" + version + ".tar.gz")
        self.set_url("ftp://ftp.simplesystems.org/pub/libpng/png/src/libpng12/" + self.zip_name())

class GMock(ExternalCPackage):
    def __init__(self, version, rootdir, package_type=CPackage.STATIC_LIB):
        super(GMock, self).__init__(version, rootdir, package_type, 'gmock')
        self.set_zip_name("gmock-" + version + ".zip")
        self.set_url("https://googlemock.googlecode.com/files/" + self.zip_name())
        self.should_install_headers(True)
        self.__package_dir = os.path.join(rootdir, 'gmock-'+version)


    def _build(self, platform, env_vars=None, configure=""):
        self.exclude_sources(['gtest/', 'test/', 'fused-src/'])
        env_vars['CFLAGS'] = (platform.default_flags('CFLAGS') + ' -I' + self.__package_dir)
        env_vars['CXXFLAGS'] = (platform.default_flags('CXXFLAGS') + ' -I' + self.__package_dir)
        env_vars['CPPFLAGS'] = (platform.default_flags('CPPFLAGS') + ' -I' + self.__package_dir)
        self.set_package_dir(self.__package_dir)
        super(ExternalCPackage, self)._pre_build(platform, env_vars)
        super(ExternalCPackage, self)._build(platform, env_vars)
        super(ExternalCPackage, self)._post_build(platform, env_vars)

class Sqlite(ExternalCPackage):
    def __init__(self, version, rootdir, package_type=CPackage.STATIC_LIB):
        super(Sqlite, self).__init__(version, rootdir, package_type, 'sqlite3')
        self.set_zip_name("sqlite-amalgamation-" + version + ".zip")
        self.set_url("http://www.sqlite.org/2018/" + self.zip_name())
        self.should_install_headers(True)
        self.__package_dir = os.path.join(rootdir, 'sqlite-amalgamation-' + version)

    def _build(self, platform, env_vars=None, configure=""):
        self.set_package_dir(self.__package_dir)
        super(ExternalCPackage, self)._pre_build(platform, env_vars)
        super(ExternalCPackage, self)._build(platform, env_vars)
        super(ExternalCPackage, self)._post_build(platform, env_vars)

class Jpeg(ExternalCPackage):
    def __init__(self, version, rootdir):
        super(Jpeg, self).__init__(version, rootdir)
        self.set_zip_name("jpegsrc.v" + version + ".tar.gz")
        self.set_url("http://www.ijg.org/files/" + self.zip_name())


class Freetype(ExternalCPackage):
    def __init__(self, version, rootdir):
        super(Freetype, self).__init__(version, rootdir)
        self.set_zip_name("freetype-" + version + ".tar.gz")
        self.set_url("http://download.savannah.gnu.org/releases/freetype/" + self.zip_name())

    def _build(self, platform, env_vars=None, configure=""):
        if isinstance(platform, IOSPlatform) and platform.arch() == 'i386':
            configure = "./configure --build=x86 " + platform.default_flags(Platform.CONFIG_FLAGS)
        super(Freetype, self)._build(platform, env_vars, configure)

    def _post_build(self, platform, env_vars=None):
        install_dir = os.path.abspath(self.install_dir(platform))
        inc_dir = os.path.join(install_dir, 'include')
        inc_freetype = os.path.join(inc_dir, 'freetype2/freetype')
        if not os.path.exists(os.path.join(inc_dir, 'freetype')):
            shutil.move(inc_freetype, inc_dir)
        super(Freetype, self)._post_build(platform)


class Minizip(ExternalCPackage):
    def __init__(self, version, rootdir, package_type=CPackage.STATIC_LIB):
        super(Minizip, self).__init__(version, rootdir, package_type, 'minizip')
        self.set_zip_name("unzip" + version + ".zip")
        self.set_url("http://www.winimage.com/zLibDll/" + self.zip_name())
        self.set_source_list(['unzip.c', 'zip.c', 'ioapi.c'])
        self.should_install_headers(True)
        self.__package_dir = os.path.join(rootdir, 'unzip' + version)

    def _download_and_unzip(self, install_dir, unzip_path=None, retries=3):
        super(Minizip, self)._download_and_unzip(install_dir, self.__package_dir, retries)

    def _build(self, platform, env_vars=None, configure=""):
        env_vars['CFLAGS'] = platform.default_flags('CFLAGS') + " -DUSE_FILE32API"
        self.set_package_dir(self.__package_dir)
        super(ExternalCPackage, self)._pre_build(platform, env_vars)
        super(ExternalCPackage, self)._build(platform, env_vars)
        super(ExternalCPackage, self)._post_build(platform, env_vars)


class Bzip(ExternalCPackage):
    def __init__(self, version, rootdir):
        super(Bzip, self).__init__(version, rootdir)
        self.set_zip_name("bzip2-" + version + ".tar.gz")
        self.set_url("http://bzip.org/" + version + "/" + self.zip_name())

    def _build(self, platform, env_vars=None, configure=""):
        if not env_vars:
            env_vars = self._env_vars
        env_vars['CFLAGS'] = platform.default_flags('CFLAGS') + " -D_FILE_OFFSET_BITS=64"
        env_vars['CXXFLAGS'] = platform.default_flags('CXXFLAGS') + " -D_FILE_OFFSET_BITS=64"
        super(Bzip, self)._build(platform, env_vars, configure=None)

    def _make(self, platform, install_dir):
        cflags = "CFLAGS=" + platform.flags('CFLAGS')
        prefix = "PREFIX=" + install_dir
        if self._num_threads:
            mt = '-j' + str(self._num_threads)
        else:
            mt = '-j' + str(cpu_count())
        if isinstance(platform, AndroidPlatform):
            cc = "CC=" + platform.flags('CC')
            ar = "AR=" + platform.flags('AR')
            ranlib = "RANLIB=" + platform.flags('RANLIB')
            call(["make", mt, cc, ar, ranlib, cflags], env=platform.var_env())
        else:
            call(["make", mt, cflags], env=platform.var_env())
        call(["make", "install", prefix], env=platform.var_env())


class OpenSSL(ExternalCPackage):
    def __init__(self, version, rootdir):
        super(OpenSSL, self).__init__(version, rootdir)
        self.set_zip_name("openssl-" + version + ".tar.gz")
        self.set_url("http://www.openssl.org/source/" + self.zip_name())

    def _build(self, platform, env_vars=None, configure=""):
        install_dir = os.path.abspath(self.install_dir(platform))
        if not env_vars:
            env_vars = self._env_vars
        if isinstance(platform, AndroidPlatform):
            env_vars['LDFLAGS'] = (platform.default_flags('LDFLAGS') +
                                   " -dynamiclib -nostdlib -lc -lgcc")
            env_vars['CFLAGS'] = (platform.default_flags('CFLAGS') +
                                  " -UOPENSSL_BN_ASM_PART_WORDS -DNO_WINDOWS_BRAINDEATH")
            configure = ("./Configure shared no-asm no-krb5 no-gost zlib-dynamic" +
                         " --openssldir=" + install_dir + " linux-generic32")
        elif isinstance(platform, IOSPlatform):
            env_vars['LDFLAGS'] = (platform.default_flags('LDFLAGS') +
                                   " -dynamiclib")
            env_vars['CFLAGS'] = (platform.default_flags('CFLAGS') +
                                  " -D_DARWIN_C_SOURCE -UOPENSSL_BN_ASM_PART_WORDS")
            configure = ("./config no-shared no-asm no-krb5 no-gost zlib" +
                         " --openssldir=" + install_dir)
        else:
            configure = ("./config no-asm no-krb5 no-gost zlib --openssldir=" + install_dir)
        super(OpenSSL, self)._build(platform, env_vars, configure)

    def _make(self, platform, install_dir):
        env_vars = platform.var_env()
        if self._num_threads:
            mt = '-j' + str(self._num_threads)
        else:
            mt = '-j' + str(cpu_count())
        if isinstance(platform, AndroidPlatform):
            shutil.move("Makefile", "Makefile~")
            call(['sed "s/\.so\.\$(SHLIB_MAJOR).\$(SHLIB_MINOR)/\.so/" Makefile~ > Makefile~1'],
                 shell=True)
            call(['sed "s/\$(SHLIB_MAJOR).\$(SHLIB_MINOR)//" Makefile~1 > Makefile'], shell=True)
        cc = "CC=" + env_vars['CC']
        cflags = "CFLAG=" + env_vars['CFLAGS']
        ldflags = "SHARED_LDFLAGS=" + env_vars['LDFLAGS']
        call(["make", mt, cc, cflags, ldflags], env=env_vars)
        call(["make", "install_sw"], env=env_vars)


class Curl(ExternalCPackage):
    def __init__(self, version, rootdir):
        super(Curl, self).__init__(version, rootdir)
        self.set_zip_name("curl-" + version + ".tar.gz")
        self.set_url("http://curl.haxx.se/download/" + self.zip_name())

    def _build(self, platform, env_vars=None, configure=""):
        configure = "./configure " + platform.default_flags(Platform.CONFIG_FLAGS)
        if not env_vars:
            env_vars = self._env_vars
        install_dir = os.path.abspath(self.install_dir(platform))
        env_vars['LDFLAGS'] = platform.default_flags('LDFLAGS')
        if isinstance(platform, AndroidPlatform):
            env_vars['LDFLAGS'] += " -lgcc -lc"
            configure += " --with-random=/dev/urandom"
        else:
            configure += " --target=" + platform.name()
        configure += (" --with-random=/dev/urandom --enable-ipv6 --enable-optimize --enable-nonblocking" +
                      " --disable-ares --disable-ftp --disable-ldap --disable-ldaps" +
                      " --disable-rtsp --disable-dict --disable-telnet --disable-tftp" +
                      " --disable-pop3 --disable-imap --disable-smtp --disable-gopher" +
                      " --disable-sspi --disable-soname-bump" +
                      " --without-polarssl --without-gnutls --without-cyassl" +
                      " --without-axtls --without-libssh2 --disable-manual --disable-verbose" +
                      " --with-zlib=" + install_dir)

        for dep in self.deps():
            dep_dir = dep.install_dir(platform)
            if dep_dir is not None:
                if isinstance(dep, OpenSSL):
                    configure += " --with-ssl=" + dep_dir

        super(Curl, self)._build(platform, env_vars, configure)

    def _make(self, platform, install_dir):
        self.__patch(platform)
        if self._num_threads:
            mt = '-j' + str(self._num_threads)
        else:
            mt = '-j' + str(cpu_count())
        cflags = "CFLAG=" + platform.flags('CFLAGSx')
        ldflags = "SHARED_LDFLAGS=" + platform.flags('LDFLAGS')
        os.chdir(os.path.join(self.local_path(), "lib"))
        call(["make", mt, cflags, ldflags], env=platform.var_env())
        call(["make", "install"], env=platform.var_env())
        os.chdir(os.path.join(self.local_path(), "include"))
        call(["make", mt, cflags, ldflags], env=platform.var_env())
        call(["make", "install"], env=platform.var_env())

    def __patch(self, platform):
        # Fix curl.h to compile on linux based systems
        if 'linux' in platform.env().system().lower():
            shutil.move("include/curl/curl.h", "include/curl/curl.h~")
            call(['sed "s/#include <sys\/types.h>/#include <sys\/select.h>\#include <sys\/types.h>/"'+
                  ' include/curl/curl.h~ > include/curl/curl.h'], shell=True)


class Icu(ExternalCPackage):
    def __init__(self, version, rootdir):
        super(Icu, self).__init__(version, rootdir)
        self.set_zip_name("icu4c-" + version.replace(".", "_") + "-src.tgz")
        self.set_url("http://download.icu-project.org/files/icu4c/" + version + "/" + self.zip_name())

    def __cross_build(self, platform):
        rootdir = self.rootdir()
        hostbuild = rootdir + "/icu/hostbuild"
        if not os.path.exists(hostbuild):
            os.makedirs(hostbuild)
        os.chdir(hostbuild)
        if self._num_threads:
            mt = '-j' + str(self._num_threads)
        else:
            mt = '-j' + str(cpu_count())
        call(["../source/configure --prefix=" + hostbuild], shell=True)
        call(["make", mt])
        self.set_local_path(os.path.join(self.local_path(), "source"))
        os.chdir(self.local_path())
        self.apply_patches()
        self._post_build(platform)
        return hostbuild

    def _build_ios(self, platform, env_vars):
        hostbuild = self.__cross_build(platform)
        inc_common = os.path.join(self.local_path(), "common")
        inc_tzcode = os.path.join(self.local_path(), "tools/tzcode")
        env_vars['CFLAGS'] = (platform.default_flags('CFLAGS') +
                              " -I" + inc_common + " -I" + inc_tzcode )
        env_vars['CXXFLAGS'] = (platform.default_flags('CXXFLAGS') +
                                " -I" + inc_common + " -I" + inc_tzcode )
        env_vars['CPPFLAGS'] = (platform.default_flags('CPPFLAGS') +
                                " -I" + inc_common + " -I" + inc_tzcode )
        configure = ("./configure " + platform.default_flags(Platform.CONFIG_FLAGS) +
                     " --with-cross-build=" + hostbuild +
                     " --enable-static --disable-shared")
        super(Icu, self)._build(platform, env_vars, configure)

    def _build_android(self, platform, env_vars):
        hostbuild = self.__cross_build(platform)
        env_vars['LDFLAGS'] = (platform.default_flags('LDFLAGS') +
                               " -nostdlib -lc -lgcc -Wl,--entry=main")
        env_vars['CFLAGS'] = (platform.default_flags('CFLAGS') +
                              " -D__STDC_INT64__ -DU_HAVE_NAMESPACE=1")
        configure = ("./configure --host=arm-eabi-linux --with-cross-build=" + hostbuild +
                     " --enable-extras=no --enable-strict=no --enable-tests=no" +
                     " --enable-samples=no --enable-dyload=no" +
                     " --enable-tools=no --with-data-packaging=archive")
        super(Icu, self)._build(platform, env_vars, configure)

    def _build(self, platform, env_vars=None, configure=""):
        if not env_vars:
            env_vars = self._env_vars
        if isinstance(platform, AndroidPlatform):
            self._build_android(platform, env_vars)
        if isinstance(platform, IOSPlatform):
            self._build_ios(platform, env_vars)
        else:
            super(Icu, self)._build(platform, env_vars, configure)

