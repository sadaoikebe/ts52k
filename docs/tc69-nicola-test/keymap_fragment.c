enum custom_keycodes { KC_EISU = NG_SAFE_RANGE, KC_KANA2 };
bool process_record_user(uint16_t keycode, keyrecord_t *record) {

  switch (keycode) {
    case KC_EISU:
      if (record->event.pressed) {
        // NICOLA親指シフト
        nicola_off(); // 保留中の打鍵を確定してから切り替える
        send_string(SS_TAP(X_INT5)); // Win (Muhenkan key)
        send_string(SS_TAP(X_LNG2)); // Mac
        // NICOLA親指シフト
      }
      return false;
      break;
    case KC_KANA2:
      if (record->event.pressed) {
        // NICOLA親指シフト
        nicola_on(); // 保留中の打鍵を確定してから切り替える
        send_string(SS_TAP(X_INT4)); // Win (Henkan key)
        send_string(SS_TAP(X_LNG1)); // Mac
        // NICOLA親指シフト
      }
      return false;
      break;
  }

  // NICOLA親指シフト
  bool a = true;
  if (nicola_state()) {
    nicola_mode(keycode, record);
    a = process_nicola(keycode, record);
  }
  if (a == false) return false;
  // NICOLA親指シフト

// as kbd101 layer driver on windows recognizes the IME on/off key, we no longer need to disguise as 106 keyboard
//   bool continue_process = process_jtu(keycode, record);
//   if (continue_process == false) {
//     return false;
//   }

  return true;
}
