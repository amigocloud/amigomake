from platform import Platform, Toolchain
from subprocess import call
import amigo_config
import os


class AndroidPlatform(Platform):
    def __init__(self, name, arch, ndk_path, sdk_version, toolchain_version, toolchain_install_path):
        super(AndroidPlatform, self).__init__(name, arch, ndk_path)
        self.__sdk_version = sdk_version
        self.__toolchain_version = toolchain_version
        self.__toolchain_install_path = toolchain_install_path
        self.__toolchain_generated = False
        self.__arch = arch

        bin_prefix = name
        target = name
        if arch == 'x86_64':
            bin_prefix = arch+'-linux-android'
        elif arch == 'x86':
            bin_prefix = 'i686-linux-android'
        elif 'armv8' in arch:
            bin_prefix = 'aarch64-linux-android'
            target = arch+'-android-linux'
        elif 'arm' not in arch:
            bin_prefix = arch+'-linux-androideabi'

        toolchain_bin = os.path.join(toolchain_install_path, "bin/" + bin_prefix)
        self._set_default_flags('CC', toolchain_bin + "-" + self.default_flags('CC'))
        self._set_default_flags('CXX', toolchain_bin + "-" + self.default_flags('CXX'))
        self._set_default_flags('LD', toolchain_bin + "-ld")
        self._set_default_flags('CPP', toolchain_bin + "-cpp")
        self._set_default_flags('AR', toolchain_bin + "-ar")
        self._set_default_flags('AS', toolchain_bin + "-as")
        self._set_default_flags('NM', toolchain_bin + "-nm")
        self._set_default_flags('STRIP', toolchain_bin + "-strip")
        self._set_default_flags('CXXCPP', toolchain_bin + "-cpp")
        self._set_default_flags('RANLIB', toolchain_bin + "-ranlib")

        self.append_default_flags(Platform.CONFIG_FLAGS,
                                  " --host=" + arch + "-android-linux" +
                                  " --target=" + target)

        ldflags = ''
        if 'armv7' in arch:
            ldflags = ' -march=armv7-a -Wl,--fix-cortex-a8'
        # elif arch == 'armv8a':
        #     ldflags = ' -march=armv8-a -Wl,--fix-cortex-a8'

        self.append_default_flags('LDFLAGS', ldflags +
                                  " -fPIC -Wl," +
                                  "-rpath-link=" + self.sysroot() + "/usr/lib" +
                                  " -L" + self.sysroot() + "/usr/lib -L" + self.gcc_libs())
        cflags = ''
        if 'armv7' in arch:
            cflags = ' -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16'
        # elif arch == 'armv8a':
        #     cflags = ' -march=armv8-a'

        self.append_default_flags('CFLAGS', cflags + " -pipe -isysroot " + self.sysroot())
        self.append_default_flags('CXXFLAGS', cflags + " -pipe -isysroot " + self.sysroot())

    def unique_name(self):
        if 'armv8' in self.arch():
            return 'android_'+self.arch()+'-linux-android'
        return 'android_' + super(AndroidPlatform, self).unique_name()

    def configure(self, install_dir, env_vars=None, configure="", deps=None):
        if not self.__toolchain_generated:
            self.__generate_toolchain()
        super(AndroidPlatform, self).configure(install_dir, env_vars, configure, deps)

    def sdk_version(self):
        return self.__sdk_version

    def toolchain_version(self):
        return self.__toolchain_version

    def sysroot(self):
        return os.path.join(self.__toolchain_install_path, "sysroot")

    def gcc_libs(self):
        return os.path.join(self.__toolchain_install_path, "lib/gcc/" + self.name() + "/" + self.__toolchain_version)

    def __generate_toolchain(self):
        arch_arg = ''
        if 'armv7' in self.__arch:
            arch_arg = '--arch arm'
        elif 'armv8' in self.__arch:
            arch_arg = '--arch arm64'
        elif 'x86_64' in self.__arch:
            arch_arg = '--arch x86_64'
        elif 'x86' == self.__arch:
            arch_arg = '--arch x86'

        builder = os.path.join(self.sdk_path(), "build/tools/make_standalone_toolchain.py --force")
        api = '--api ' + self.sdk_version()
        install_dir = "--install-dir=" + self.__toolchain_install_path
        cxx11 = ''
        if amigo_config.CXX11:
            cxx11 = '--stl=libc++'
        call_str = builder + " " + arch_arg + " " + api + " " + install_dir + " " + cxx11
        if amigo_config.VERBOSE:
            print (call_str)
        call([call_str], shell=True)
        self.__toolchain_generated = True
