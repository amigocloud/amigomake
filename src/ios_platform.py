from platform import Platform
import amigo_config
import os


class IOSPlatform(Platform):
    def __init__(self, version, arch, is_sim=False):
        if is_sim:
            name = 'iPhoneSimulator'
            arch = 'i386'
        else:
            name = 'iPhoneOS'
        min_version = "5.0"
        devroot = '/Applications/Xcode.app/Contents/Developer/'
        sdk_path = os.path.join(devroot, 'Platforms/' + name + '.platform/Developer')
        sdkroot = os.path.join(sdk_path, 'SDKs/' + name + version + '.sdk')

        super(IOSPlatform, self).__init__(name, arch, sdk_path)
        self.append_default_flags(Platform.CONFIG_FLAGS,
                                  "--host=" + arch + "-apple-darwin")
        cflags = (" -arch " + arch + " -pipe -no-cpp-precomp" +
                  " -isysroot " + sdkroot + " -miphoneos-version-min=" + min_version)
        cxxflags = cflags
        ldflags = " -arch " + arch + " -Wl,-dead_strip -miphoneos-version-min=" + min_version
        if amigo_config.CXX11:
            cxxflags += " -stdlib=libc++"
        self.append_default_flags('CFLAGS', cflags)
        self.append_default_flags('CPPFLAGS', cflags)
        self.append_default_flags('CXXFLAGS', cxxflags)
        self.append_default_flags('LDFLAGS', ldflags)

        toolchain_bin = os.path.join(devroot, 'Toolchains/XcodeDefault.xctoolchain/usr/bin/')
        self._set_default_flags('CC', toolchain_bin + self.default_flags('CC'))
        self._set_default_flags('CXX', toolchain_bin + self.default_flags('CXX'))
        self._set_default_flags('LD', toolchain_bin + "ld")
        self._set_default_flags('AR', toolchain_bin + "ar")
        self._set_default_flags('AS', toolchain_bin + "as")
        self._set_default_flags('NM', toolchain_bin + "nm")
        self._set_default_flags('STRIP', toolchain_bin + "strip")
        self._set_default_flags('RANLIB', toolchain_bin + "ranlib")
        self._set_default_flags('LIPO', toolchain_bin + "lipo")

        self.__is_sim = is_sim
        self.__version = version

    def version(self):
        return self.__version

    def is_sim(self):
        return self.__is_sim
