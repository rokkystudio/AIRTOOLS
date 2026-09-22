/*
 * Reference source for a minimal AF_PACKET metadata probe.
 * Not compiled into this image because no MIPS cross-compiler is currently present in the project.
 * Intended future behavior: bind to ra0 and print only packet metadata / first header bytes to stdout.
 * No payload storage, no reconstruction, no flash writes.
 */
