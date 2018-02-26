from platform import Platform
import amigo_config


class X86Platform(Platform):
    def __init__(self, arch):
        super(X86Platform, self).__init__("native_x86", arch)
        cflags = " -fPIC -pipe -isysroot /"
        cxxflags = cflags
        #if amigo_config.CXX11:
        #    cxxflags += " -stdlib=libc++"
        self.append_default_flags('LDFLAGS',
                                  " -fpic -L/usr/lib")
        self.append_default_flags('CFLAGS', cflags)
        self.append_default_flags('CXXFLAGS', cxxflags)
