import multiprocessing
import platform
import subprocess
import sys

import os
from conans.model.version import Version
from conans.util.log import logger

_global_output = None


def args_to_string(args):
    if not args:
        return ""
    if sys.platform == 'win32':
        return subprocess.list2cmdline(args)
    else:
        return " ".join("'" + arg.replace("'", r"'\''") + "'" for arg in args)


def cpu_count():
    try:
        env_cpu_count = os.getenv("CONAN_CPU_COUNT", None)
        return int(env_cpu_count) if env_cpu_count else multiprocessing.cpu_count()
    except NotImplementedError:
        _global_output.warn("multiprocessing.cpu_count() not implemented. Defaulting to 1 cpu")
    return 1  # Safe guess


def detected_architecture():
    # FIXME: Very weak check but not very common to run conan in other architectures
    if "64" in platform.machine():
        return "x86_64"
    elif "86" in platform.machine():
        return "x86"
    return None

# DETECT OS, VERSION AND DISTRIBUTIONS


class OSInfo(object):
    """ Usage:
        (os_info.is_linux) # True/False
        (os_info.is_windows) # True/False
        (os_info.is_macos) # True/False
        (os_info.is_freebsd) # True/False
        (os_info.is_solaris) # True/False

        (os_info.linux_distro)  # debian, ubuntu, fedora, centos...

        (os_info.os_version) # 5.1
        (os_info.os_version_name) # Windows 7, El Capitan

        if os_info.os_version > "10.1":
            pass
        if os_info.os_version == "10.1.0":
            pass
    """

    def __init__(self):
        self.os_version = None
        self.os_version_name = None
        self.is_linux = platform.system() == "Linux"
        self.linux_distro = None
        self.is_windows = platform.system() == "Windows"
        self.is_macos = platform.system() == "Darwin"
        self.is_freebsd = platform.system() == "FreeBSD"
        self.is_solaris = platform.system() == "SunOS"

        if self.is_linux:
            import distro
            self.linux_distro = distro.id()
            self.os_version = Version(distro.version())
            version_name = distro.codename()
            self.os_version_name = version_name if version_name != "n/a" else ""
            if not self.os_version_name and self.linux_distro == "debian":
                self.os_version_name = self.get_debian_version_name(self.os_version)
        elif self.is_windows:
            self.os_version = self.get_win_os_version()
            self.os_version_name = self.get_win_version_name(self.os_version)
        elif self.is_macos:
            self.os_version = Version(platform.mac_ver()[0])
            self.os_version_name = self.get_osx_version_name(self.os_version)
        elif self.is_freebsd:
            self.os_version = self.get_freebsd_version()
            self.os_version_name = "FreeBSD %s" % self.os_version
        elif self.is_solaris:
            self.os_version = Version(platform.release())
            self.os_version_name = self.get_solaris_version_name(self.os_version)

    @property
    def with_apt(self):
        return self.is_linux and self.linux_distro in \
                                 ("debian", "ubuntu", "knoppix", "linuxmint", "raspbian")

    @property
    def with_yum(self):
        return self.is_linux and self.linux_distro in \
                                 ("centos", "redhat", "fedora", "pidora", "scientific",
                                  "xenserver", "amazon", "oracle", "rhel")

    @staticmethod
    def get_win_os_version():
        """
        Get's the OS major and minor versions.  Returns a tuple of
        (OS_MAJOR, OS_MINOR).
        """
        import ctypes

        class _OSVERSIONINFOEXW(ctypes.Structure):
            _fields_ = [('dwOSVersionInfoSize', ctypes.c_ulong),
                        ('dwMajorVersion', ctypes.c_ulong),
                        ('dwMinorVersion', ctypes.c_ulong),
                        ('dwBuildNumber', ctypes.c_ulong),
                        ('dwPlatformId', ctypes.c_ulong),
                        ('szCSDVersion', ctypes.c_wchar * 128),
                        ('wServicePackMajor', ctypes.c_ushort),
                        ('wServicePackMinor', ctypes.c_ushort),
                        ('wSuiteMask', ctypes.c_ushort),
                        ('wProductType', ctypes.c_byte),
                        ('wReserved', ctypes.c_byte)]

        os_version = _OSVERSIONINFOEXW()
        os_version.dwOSVersionInfoSize = ctypes.sizeof(os_version)
        retcode = ctypes.windll.Ntdll.RtlGetVersion(ctypes.byref(os_version))
        if retcode != 0:
            return None

        return Version("%d.%d" % (os_version.dwMajorVersion, os_version.dwMinorVersion))

    @staticmethod
    def get_debian_version_name(version):
        if not version:
            return None
        elif version.major() == "8.Y.Z":
            return "jessie"
        elif version.major() == "7.Y.Z":
            return "wheezy"
        elif version.major() == "6.Y.Z":
            return "squeeze"
        elif version.major() == "5.Y.Z":
            return "lenny"
        elif version.major() == "4.Y.Z":
            return "etch"
        elif version.minor() == "3.1.Z":
            return "sarge"
        elif version.minor() == "3.0.Z":
            return "woody"

    @staticmethod
    def get_win_version_name(version):
        if not version:
            return None
        elif version.major() == "5.Y.Z":
            return "Windows XP"
        elif version.minor() == "6.0.Z":
            return "Windows Vista"
        elif version.minor() == "6.1.Z":
            return "Windows 7"
        elif version.minor() == "6.2.Z":
            return "Windows 8"
        elif version.minor() == "6.3.Z":
            return "Windows 8.1"
        elif version.minor() == "10.0.Z":
            return "Windows 10"

    @staticmethod
    def get_osx_version_name(version):
        if not version:
            return None
        elif version.minor() == "10.12.Z":
            return "Sierra"
        elif version.minor() == "10.11.Z":
            return "El Capitan"
        elif version.minor() == "10.10.Z":
            return "Yosemite"
        elif version.minor() == "10.9.Z":
            return "Mavericks"
        elif version.minor() == "10.8.Z":
            return "Mountain Lion"
        elif version.minor() == "10.7.Z":
            return "Lion"
        elif version.minor() == "10.6.Z":
            return "Snow Leopard"
        elif version.minor() == "10.5.Z":
            return "Leopard"
        elif version.minor() == "10.4.Z":
            return "Tiger"
        elif version.minor() == "10.3.Z":
            return "Panther"
        elif version.minor() == "10.2.Z":
            return "Jaguar"
        elif version.minor() == "10.1.Z":
            return "Puma"
        elif version.minor() == "10.0.Z":
            return "Cheetha"

    @staticmethod
    def get_freebsd_version():
        return platform.release().split("-")[0]

    @staticmethod
    def get_solaris_version_name(version):
        if not version:
            return None
        elif version.minor() == "5.10":
            return "Solaris 10"
        elif version.minor() == "5.11":
            return "Solaris 11"


def cross_building(settings, self_os=None, self_arch=None):
    self_os = self_os or platform.system()
    self_arch = self_arch or detected_architecture()
    os_setting = settings.get_safe("os")
    arch_setting = settings.get_safe("arch")
    platform_os = {"Darwin": "Macos"}.get(self_os, self_os)

    if os_setting and platform_os != os_setting:
        return True
    if arch_setting and self_arch != arch_setting:
        return True

    return False

try:
    os_info = OSInfo()
except Exception as exc:
    logger.error(exc)
    _global_output.error("Error detecting os_info")