.text
.set noreorder
.set nomips16
.globl _start
.type _start, @function

# _start passes argc/argv from the Linux process stack to main(), then exits
# using the Linux MIPS O32 exit syscall.
_start:
    lw      $a0, 0($sp)
    addiu   $a1, $sp, 4
    jal     main
    nop

    move    $a0, $v0
    li      $v0, 4001
    syscall
    nop
