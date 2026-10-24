#include "lab.h"
static int equal(const char *a,const char *b) {
 while (*a && *a==*b) { a++; b++; }
 return *a==*b;
}
static void command(const char *s) {
 if (equal(s,"help")) text("COMMANDS help status memcheck exit\n");
 else if (equal(s,"status")) text("STATUS EL3 READY\n");
 else if (equal(s,"memcheck")) {
  volatile uint64_t buffer[32];
  for (unsigned i=0;i<32;i++) buffer[i]=0xfeed0000ULL+i;
  for (unsigned i=0;i<32;i++) if (buffer[i]!=0xfeed0000ULL+i) fail("UART_MEMCHECK");
  check(1,"UART_MEMCHECK");
 } else if (equal(s,"exit")) { check(1,"UART_SESSION"); lab_done(0); }
 else if (*s) text("ERROR unknown command\n");
}
int main(void) {
 lab_begin("uart");
 char line[32]; unsigned used=0; int overflow=0,previous_cr=0;
 text("lab> ");
 for (;;) {
  int c=getchar_uart();
  if (c<0) fail("UART input timeout");
  if (c=='\n' && previous_cr) { previous_cr=0; continue; }
  previous_cr=c=='\r';
  if (c=='\r' || c=='\n') {
   text("\n");
   if (overflow) text("ERROR line too long\n");
   else { line[used]=0; command(line); }
   used=0; overflow=0; text("lab> ");
  } else if (c==8 || c==127) {
   if (!overflow && used) { used--; text("\b \b"); }
  } else if (c>=32 && c<127 && !overflow) {
   if (used==sizeof(line)-1) overflow=1;
   else { line[used++]=(char)c; putchar_uart((char)c); }
  }
 }
}
