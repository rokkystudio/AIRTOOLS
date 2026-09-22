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

syscall_wrapper sys_read, 4003
syscall_wrapper sys_write, 4004
syscall_wrapper sys_open, 4005
syscall_wrapper sys_close, 4006
syscall_wrapper sys_lseek, 4019

.globl sys_exit
.ent sys_exit
sys_exit:
    li      $2, 4001
    syscall
1:
    b       1b
    nop
.end sys_exit
