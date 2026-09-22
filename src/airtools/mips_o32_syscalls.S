.set noreorder
.text

.macro syscall_wrapper name, number
.globl \name
.ent \name
\name:
    li      $2, \number
    syscall
    beqz    $7, 1f
    nop
    subu    $2, $0, $2
1:
    jr      $31
    nop
.end \name
.endm

syscall_wrapper sys_fork, 4002
syscall_wrapper sys_waitpid, 4007
syscall_wrapper sys_execve, 4011
syscall_wrapper sys_kill, 4037
syscall_wrapper sys_dup2, 4063
syscall_wrapper sys_nanosleep, 4166
syscall_wrapper sys_read, 4003
syscall_wrapper sys_write, 4004
syscall_wrapper sys_open, 4005
syscall_wrapper sys_close, 4006
syscall_wrapper sys_mkdir, 4039
syscall_wrapper sys_unlink, 4010
syscall_wrapper sys_gettimeofday, 4078
syscall_wrapper sys_ioctl, 4054
syscall_wrapper sys_accept, 4168
syscall_wrapper sys_listen, 4174
syscall_wrapper sys_bind, 4169
syscall_wrapper sys_recv, 4175
syscall_wrapper sys_send, 4178
syscall_wrapper sys_setsockopt, 4181
syscall_wrapper sys_recvfrom, 4176
syscall_wrapper sys_sendto, 4180
syscall_wrapper sys_socket, 4183

.globl sys_exit
.ent sys_exit
sys_exit:
    li      $2, 4001
    syscall
1:
    b       1b
    nop
.end sys_exit
