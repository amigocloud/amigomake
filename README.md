AmigoMake
=========

[Writing an AmigoMakefile](https://github.com/schernetsky/amigomake/wiki/Writing-an-AmigoMakefile)

Take a look at the sample [AmigoMakefile](https://github.com/schernetsky/amigomake/blob/master/SampleAmigoMakefile) which will build an executable out of all C/C++ files in its directory


##Install:
```bash
# Makes soft link to amigomake in /usr/bin
sudo ./install.sh
```

##Usage:
```bash
amigomake [flags] [action] {android,ios,x86} [platform-flags]
```

###Supported Platforms: 

android, ios, x86

###General Flags:
```
-h, --help         Show this help message and exit
-a, --arch         Specify the target architecture(s) (armv7 by default)
-f, --file         Specify AmigoMakefile path
-r, --root         Specify dir for external dependency soures
-d, --debug        Compile non-optimized with debug flags
--all              Apply action to everything including dependencies
                   (Needs to be supported in AmigoMakefile)
--gcc              Compile using gcc
--cxx11            Compile with c++11 support
-v, --verbose      Verbose mode
--version          Print version
```

###Actions:

Pass actions to be interpreted by the make file (clean, test, etc...)

The default action is: **build**  

###Platform Flags:
####X86:
None
####Android:
```
-n , --ndk           Specify path to the Android NDK(Required)
-v , --sdk-version   Specify Android SDK version to use(Required)
```
####iOS:
```
-v , --sdk-version   Specify iOS SDK version to use(Required)
```
##Examples:

###IOS:
```bash
# Clean non sim build and external dependencies:
amigomake --all -a armv7 -a arm64 clean ios -v 8.1

# Build IOS8 device without rebuilding external dependencies:
amigomake -a armv7 -a arm64 ios -v 8.1

# Build iOS8 simulator build and external dependencies:
amigomake --all -a i386 ios -v 8.1
```

###Android:
```bash
# Build Android without rebuilding external dependencies for SDK version 14:
amigomake android -n ~/android-ndk/ -v 14
```

###x86:
```bash
# Build x86 without rebuilding external dependencies:
amigomake x86
```

###External Libraries:
Some example external [packages](https://github.com/schernetsky/amigomake/blob/master/src/packages.py) are included:
 * proj4, libpng, libjpeg, gmock
 * sqlite, freetype, minizip, bzip
 * openssl, cURL, libicu, boost
