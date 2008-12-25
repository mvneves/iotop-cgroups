import ctypes
import fnmatch
import os
import time

# From http://git.kernel.org/?p=utils/util-linux-ng/util-linux-ng.git;a=blob;
#      f=configure.ac;h=770eb45ae85d32757fc3cff1d70a7808a627f9f7;hb=HEAD#l363
IOPRIO_GET_ARCH_SYSCALL = [
    ('alpha',    443),
    ('i*86',     290),
    ('ia64*',    1275),
    ('powerpc*', 274),
    ('s390*',    283),
    ('sparc*',   218),
    ('sh*',      289),
    ('x86_64*',  252),
]

def find_ioprio_get_syscall_number():
    arch = os.uname()[4]

    for candidate_arch, syscall_nr in IOPRIO_GET_ARCH_SYSCALL:
        if fnmatch.fnmatch(arch, candidate_arch):
            return syscall_nr


__NR_ioprio_get = find_ioprio_get_syscall_number()
ctypes_handle = ctypes.CDLL(None)
syscall = ctypes_handle.syscall

PRIORITY_CLASSES = (None, 'rt', 'be', 'idle')

WHO_PROCESS = 1
IOPRIO_CLASS_SHIFT = 13
IOPRIO_PRIO_MASK = (1 << IOPRIO_CLASS_SHIFT) - 1

def ioprio_class(ioprio):
    return PRIORITY_CLASSES[ioprio >> IOPRIO_CLASS_SHIFT]

def ioprio_data(ioprio):
    return ioprio & IOPRIO_PRIO_MASK

sched_getscheduler = ctypes_handle.sched_getscheduler
SCHED_OTHER, SCHED_FIFO, SCHED_RR, SCHED_BATCH, SCHED_ISO, SCHED_IDLE = range(6)

def get_ioprio_from_sched(pid):
    scheduler = sched_getscheduler(pid)
    nice = int(open('/proc/%d/stat' % pid).read().split()[18])
    ioprio_nice = (nice + 20) / 5

    if scheduler in (SCHED_FIFO, SCHED_RR):
        return 'rt/%d' % ioprio_nice
    elif scheduler == SCHED_IDLE:
        return 'idle'
    else:
        return 'be/%d' % ioprio_nice

def get(pid):
    if __NR_ioprio_get is None:
        return '?sys'

    ioprio = syscall(__NR_ioprio_get, WHO_PROCESS, pid)
    if ioprio < 0:
        return '?err'

    prio_class = ioprio_class(ioprio)
    if not prio_class:
        return get_ioprio_from_sched(pid)
    if prio_class == 'idle':
        return prio_class
    return '%s/%d' % (prio_class, ioprio_data(ioprio))

def sort_key(key):
    if key[0] == '?':
        return -ord(key[1])

    if '/' in key:
        if key.startswith('rt/'):
            shift = 0
        elif key.startswith('be/'):
            shift = 1
        prio = int(key.split('/')[1])
    elif key == 'idle':
        shift = 2
        prio = 0

    return (1 << (shift * IOPRIO_CLASS_SHIFT)) + prio

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        pid = int(sys.argv[1])
    else:
        pid = os.getpid()
    print 'pid:', pid
    print 'ioprio:', get(pid)

