from android_platform import AndroidPlatform
from ios_platform import IOSPlatform
from external_cpackage import ExternalCPackage
from subprocess import call
import os

boost_libs = ('date_time,random,' +
              'iostreams,regex,' +
              'signals,system,thread')


class Boost(ExternalCPackage):
    def __init__(self, version, rootdir):
        super(Boost, self).__init__(version, rootdir)
        self.set_zip_name("boost_" + version.replace(".", "_") + ".tar.bz2")
        self.set_url("http://surfnet.dl.sourceforge.net/project/boost/boost/" + version + "/" + self.zip_name())

    def _build_android(self, platform, install_dir, env_vars):
        os.chdir(self.local_path())
        platform.init_env_vars(env_vars)
        call(["./bootstrap.sh --with-libraries="+boost_libs], shell=True)
        self.apply_patches()
        self.__user_config_jam_android(platform, install_dir)
        self.__project_config_jam(install_dir)
        configure = (
            "./b2 link=static threading=multi --layout=unversioned target-os=linux toolset=android-arm -d+2 install")
        super(Boost, self)._build(platform, env_vars, configure)

    def _build_ios(self, platform, install_dir, env_vars):
        os.chdir(self.local_path())
        platform.init_env_vars(env_vars)
        call(["./bootstrap.sh --with-libraries="+boost_libs], shell=True)
        self.apply_patches()
        self.__user_config_jam_ios(platform)
        self.__project_config_jam(install_dir)
        target = 'iphone'
        toolset = 'darwin'
        arch = 'arm'
        if platform.arch() == 'i386':
            target += 'sim'
            toolset += '-' + platform.version() + '~iphonesim'
            arch = 'x86'
        cxxflags = "cxxflags='-I" + os.path.join(install_dir, "include")+"'"
        configure = ("./bjam toolset=" + toolset + " architecture=" + arch + 
                     " target-os=iphone macosx-version="+ target +"-" + platform.version() +
                     " define=_LITTLE_ENDIAN link=static install " + cxxflags)
        super(Boost, self)._build(platform, env_vars, configure)

    def _post_build(self, platform, env_vars=None):
        install_dir = os.path.abspath(self.install_dir(platform))
        obj_path = os.path.join(self.local_path(), 'tmp/obj')
        lib_path = os.path.join(install_dir, 'lib')

        if not os.path.exists(obj_path):
            os.makedirs(obj_path)
        os.chdir(obj_path)
        # Find lib files
        lib_files = set()
        for (dirpath, dirnames, filenames) in os.walk(lib_path):
            for filename in filenames:
                if filename.startswith('libboost_') and filename.endswith('.a'):
                    lib_files.add(os.path.join(dirpath, filename))
        # Extract objects
        ar = platform.flags('AR')
        for lib_file in lib_files:
            if isinstance(platform, IOSPlatform):
                lipo = platform.flags('LIPO')
                call([lipo + ' -thin ' + platform.arch() + ' ' + lib_file + ' -output ' + lib_file],
                     shell=True)
            call([ar + " -x " + lib_file], shell=True)
            os.remove(lib_file)
        # Find obj files
        obj_files = []
        for (dirpath, dirnames, filenames) in os.walk(obj_path):
            for filename in filenames:
                if filename.endswith('.o'):
                    obj_files.append(os.path.join(dirpath, filename))
        # Compile 1 output lib
        output = os.path.join(lib_path, 'libboost.a')
        ar_flag = 'rv'
        if isinstance(platform, IOSPlatform):
            ar_flag = 'crus'
        call_str = ar + ' ' + ar_flag + ' ' + output + " " + (' '.join(obj_files))
        call([call_str], shell=True)
        super(Boost, self)._post_build(platform)

    def _build(self, platform, env_vars=None, configure=""):
        install_dir = os.path.abspath(self.install_dir(platform))
        if isinstance(platform, AndroidPlatform):
            self._build_android(platform, install_dir, env_vars)
        elif isinstance(platform, IOSPlatform):
            self._build_ios(platform, install_dir, env_vars)
        else:
            os.chdir(self.local_path())
            platform.init_env_vars(env_vars)
            call(["./bootstrap.sh --with-libraries="+boost_libs], shell=True)
            self.__project_config_jam(install_dir)
            cxxflags = "cxxflags='-I" + os.path.join(install_dir, "include") + " -fPIC'"
            configure = './b2 toolset=clang link=static install ' + cxxflags

            super(Boost, self)._build(platform, env_vars, configure)

    def _make(self, platform, install_dir):
        return

    def __project_config_jam(self, install_dir):
        config_file = os.path.join(self.local_path(), 'project-config.jam')
        libs_str = ''
        for boost_lib in boost_libs.split(','):
            libs_str += ' --with-'+boost_lib
        to_write = """libraries ={LIBS} ;
option.set prefix : {ROOTDIR}/ ;
option.set exec-prefix : {ROOTDIR}/bin ;      
option.set libdir : {ROOTDIR}/lib ;           
option.set includedir : {ROOTDIR}/include ;"""
        context = {'ROOTDIR': install_dir, 'LIBS': libs_str}
        f = open(config_file, 'w')
        f.write(to_write.format(**context))
        f.close()

    def __user_config_jam_android(self, platform, install_dir):
        config_file = os.path.join(self.local_path(), 'tools/build/v2/user-config.jam')
        to_write = """using android : i686 : {CXX} :
<compileflags>-Os
<compileflags>-O2
<compileflags>-g
<compileflags>-std=gnu++0x
<compileflags>-Wno-variadic-macros
<compileflags>-fexceptions
<compileflags>-fpic
<compileflags>-ffunction-sections
<compileflags>-funwind-tables
<compileflags>-fomit-frame-pointer
<compileflags>-fno-strict-aliasing
<compileflags>-finline-limit=64
<compileflags>-DANDROID
<compileflags>-D__ANDROID__
<compileflags>-DNDEBUG
<compileflags>-I{SDK}/platforms/android-14/arch-x86/usr/include
<compileflags>-I{SDK}/sources/cxx-stl/gnu-libstdc++/include
<compileflags>-I{SDK}/sources/cxx-stl/gnu-libstdc++/libs/x86/include
<compileflags>-I{ROOTDIR}/include
<linkflags>-nostdlib
<linkflags>-lc
<linkflags>-Wl,-rpath-link=${SYSROOT}/usr/lib
<linkflags>-L{SYSROOT}/usr/lib
<linkflags>-L{SDK}/sources/cxx-stl/gnu-libstdc++/libs/x86
<linkflags>-L{ROOTDIR}/lib
# Flags above are for android
<architecture>x86
<compileflags>-fvisibility=hidden
<compileflags>-fvisibility-inlines-hidden
<compileflags>-fdata-sections
<cxxflags>-frtti
<cxxflags>-D_REENTRANT
<cxxflags>-D_GLIBCXX__PTHREADS
; 

using android : arm : {CXX} :
<compileflags>-Os
<compileflags>-O2
<compileflags>-g
<compileflags>-std=gnu++0x
<compileflags>-Wno-variadic-macros
<compileflags>-fexceptions
<compileflags>-fpic
<compileflags>-ffunction-sections
<compileflags>-funwind-tables
<compileflags>-march=armv5te
<compileflags>-mtune=xscale
<compileflags>-msoft-float
<compileflags>-mthumb
<compileflags>-fomit-frame-pointer
<compileflags>-fno-strict-aliasing
<compileflags>-finline-limit=64
<compileflags>-D__ARM_ARCH_5__
<compileflags>-D__ARM_ARCH_5T__
<compileflags>-D__ARM_ARCH_5E__
<compileflags>-D__ARM_ARCH_5TE__
<compileflags>-DANDROID
<compileflags>-D__ANDROID__
<compileflags>-DNDEBUG
<compileflags>-I{SDK}/platforms/android-14/arch-arm/usr/include
<compileflags>-I{SDK}/sources/cxx-stl/gnu-libstdc++/include
<compileflags>-I{SDK}/sources/cxx-stl/gnu-libstdc++/libs/armeabi-v7a/include
<compileflags>-I{ROOTDIR}/include
<linkflags>-nostdlib
<linkflags>-lc
<linkflags>-Wl,-rpath-link={SYSROOT}/usr/lib
<linkflags>-L{SYSROOT}/usr/lib
<linkflags>-L{SDK}/sources/cxx-stl/gnu-libstdc++/libs/armeabi-v7a
<linkflags>-L{ROOTDIR}/lib
# Flags above are for android
<architecture>arm
<compileflags>-fvisibility=hidden
<compileflags>-fvisibility-inlines-hidden
<compileflags>-fdata-sections
<cxxflags>-frtti
<cxxflags>-D__arm__
<cxxflags>-D_REENTRANT
<cxxflags>-D_GLIBCXX__PTHREADS
"""
        context = {
            'ROOTDIR': install_dir,
            'SYSROOT': platform.sysroot(),
            'SDK': platform.sdk_path(),
            'CXX': platform.flags('CXX')
        }
        f = open(config_file, 'w')
        f.write(to_write.format(**context))
        for dep in self.deps():
            dep_dir = dep.install_dir(self)
            if dep_dir is not None:
                f.write('<linkflags>-L' + os.path.join(dep_dir, "lib") + '\n')
                f.write('<compilerflags>-I' + os.path.join(dep_dir, "include") + '\n')
        f.write(';\n')
        f.close()

    def __user_config_jam_ios(self, platform):
        config_file = os.path.join(self.local_path(), 'tools/build/v2/user-config.jam')
        to_write = """using darwin : {SDK}~{BOOST_PLAT}
   : {CXX} -arch {ARCH} -mthumb -fvisibility=hidden -fvisibility-inlines-hidden {CFLAGS}
   : <striper> <root>{SDK_PATH}
   : <architecture>{BOOST_ARCH} <target-os>iphone
   ;
"""
        if platform.arch() == 'i386':
            arch = 'x86'
        else:
            arch = 'arm'
        context = {
            'ARCH': platform.arch(),
            'CFLAGS': '-Os -DBOOST_AC_USE_PTHREADS -DBOOST_SP_USE_PTHREADS',
            'SDK_PATH': platform.sdk_path(),
            'SDK': platform.version(),
            'BOOST_PLAT': 'iphone',
            'BOOST_ARCH': arch,
            'CXX': platform.flags('CXX')
        }
        f = open(config_file, 'w')
        f.write(to_write.format(**context))
        f.close()
