from platform import Platform


class X86Platform(Platform):
    def __init__(self, arch):
        super(X86Platform, self).__init__("x86", arch)
        self.append_default_flags('LDFLAGS',
                                  " -fpic -Wl," +
                                  "-rpath-link=/usr/lib -L/usr/lib")
        self.append_default_flags('CFLAGS', " -fPIC -pipe -isysroot /")
        self.append_default_flags('CXXFLAGS', " -fPIC -pipe -isysroot /")
