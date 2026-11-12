#define QMK_KEYBOARD_H "qmk_stub.h"
#include "qmk_stub.h"
#include "nicola.h"
static char out[4096]; static bool layer1=false; static uint8_t mods=0; static uint16_t now=0;
void send_string(const char *s){ strcat(out,s); }
void layer_on(uint8_t l){ if(l==1) layer1=true; }
void layer_off(uint8_t l){ if(l==1) layer1=false; }
uint8_t get_mods(void){ return mods; }
uint8_t bitpop(uint8_t b){ uint8_t n=0; while(b){n+=b&1;b>>=1;} return n; }
uint16_t timer_read(void){ return now; }
#include "keymap_fragment.c"
static int fails=0;
/* resolve a physical "role" to keycode like the real keymap would (layer state) */
static void ev(uint16_t kc, bool pressed, uint16_t t){
  keyrecord_t r={{pressed,t}}; now=t;
  if(kc>=KC_LCTL && kc<=KC_RGUI){ uint8_t bit=1<<(kc-KC_LCTL); /* mods register after user returns true */
    bool cont=process_record_user(kc,&r); if(cont){ if(pressed) mods|=bit; else mods&=~bit; } return; }
  if(process_record_user(kc,&r) && kc<SAFE_RANGE && kc!=MO_FUNC){ strcat(out, pressed?"[d":"[u"); char b[8]; sprintf(b,"%02X]",kc); strcat(out,b);} }
static void expect(const char*name,const char*exp){ if(strcmp(out,exp)){ printf("FAIL %s\n  got: %s\n  exp: %s\n",name,out,exp); fails++;} else printf("ok   %s: %s\n",name,out); out[0]=0; }
static void reset(bool kana){ out[0]=0; mods=0; layer1=false; nicola_off(); out[0]=0; if(kana){ nicola_on(); out[0]=0; } }

int main(void){
  set_nicola(1);
  /* --- regressions of normal typing --- */
  reset(true); ev(NG_W,1,0); ev(NG_W,0,50); expect("single M","ka");
  reset(true); ev(NG_W,1,0); ev(NG_SHFTL,1,30); ev(NG_W,0,120); ev(NG_SHFTL,0,130); expect("M+O(left) combo","e");
  reset(true); ev(NG_W,1,0); ev(NG_SHFTR,1,200); ev(NG_SHFTR,0,250); ev(NG_W,0,260); expect("M then O after timeout","ka ");
  reset(true); ev(NG_W,1,0); ev(KC_ENT,1,10); ev(KC_ENT,0,20); ev(NG_W,0,30); expect("other key flushes first","ka[d28][u28]");
  reset(true); ev(NG_W,1,0); ev(KC_LCTL,1,10); expect("modifier press flushes before mod","ka"); if(layer1){puts("FAIL layer should be off");fails++;}
  /* --- F-C --- */
  reset(true); ev(MO_FUNC,1,0); ev(NG_W,1,10); ev(KC_EISU,1,20); ev(KC_EISU,0,40); ev(NG_W,0,50); ev(MO_FUNC,0,60);
  expect("F-C: Fn,W,EISU -> ka before host switch","ka<X_INT5><X_LNG2>"); if(nicola_state()||layer1){puts("FAIL still kana");fails++;}
  reset(true); ev(MO_FUNC,1,0); ev(NG_W,1,10); ev(KC_KANA2,1,20); ev(KC_KANA2,0,40); ev(NG_W,0,50); ev(MO_FUNC,0,60);
  expect("F-C: Fn,W,KANA2 in kana -> ka before host switch","ka<X_INT4><X_LNG1>"); if(!nicola_state()||!layer1){puts("FAIL not kana");fails++;}
  reset(false); ev(KC_KANA2,1,0); expect("ON from alnum, nothing pending","<X_INT4><X_LNG1>");
  /* --- F-B --- */
  reset(false); ev(KC_LSFT,1,0); ev(KC_KANA2,1,10); if(layer1){puts("FAIL F-B: layer on while shift held");fails++;}
  ev(KC_LSFT,0,20); if(!layer1){puts("FAIL F-B: layer not restored on release");fails++;}
  ev(KC_LCTL,1,30); if(layer1){puts("FAIL F-B: ctrl did not drop layer (underflow?)");fails++;} ev(KC_LCTL,0,40); if(!layer1){puts("FAIL");fails++;}
  expect("F-B: shift pressed in alnum, released in kana","<X_INT4><X_LNG1>");
  reset(true); ev(KC_LCTL,1,0); ev(KC_EISU,1,10); ev(KC_LCTL,0,20); ev(KC_KANA2,1,30); if(!layer1){puts("FAIL F-B: stale count kept layer off");fails++;}
  ev(KC_LCTL,1,40); if(layer1){puts("FAIL F-B: ctrl no longer drops layer");fails++;} ev(KC_LCTL,0,50); if(!layer1){puts("FAIL");fails++;}
  expect("F-B: ctrl across OFF/ON","<X_INT5><X_LNG2><X_INT4><X_LNG1>");
  /* lower-bound guard: release without counted press (two keys on one mod bit in a future keymap) */
  reset(true); ev(KC_LSFT,0,0); if(!layer1){puts("FAIL guard");fails++;} ev(KC_LSFT,1,10); if(layer1){puts("FAIL guard: underflowed");fails++;} ev(KC_LSFT,0,20);
  expect("guard: stray release does not underflow","");
  /* --- event time (LT replay) --- */
  reset(true); now=0; { keyrecord_t r={{1,0}}; now=300; process_record_user(NG_W,&r);} { keyrecord_t r={{1,170}}; now=301; process_record_user(NG_SHFTL,&r);} {keyrecord_t r={{0,180}}; now=302; process_record_user(NG_SHFTL,&r);} {keyrecord_t r={{0,190}}; now=303; process_record_user(NG_W,&r);}
  expect("replayed events judged by event.time (170ms apart = sequential)","ka ");
  printf("%s (%d failures)\n", fails?"FAILED":"ALL PASS", fails); return fails!=0;
}
