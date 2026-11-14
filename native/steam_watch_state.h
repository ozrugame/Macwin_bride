#ifndef STEAM_WATCH_STATE_H
#define STEAM_WATCH_STATE_H
#include <wchar.h>
static int steam_main_class(const wchar_t *name) {
    return !wcscmp(name,L"SDL_app") || !wcscmp(name,L"vguiPopupWindow") ||
           !wcscmp(name,L"Chrome_WidgetWin_0") || !wcscmp(name,L"Chrome_WidgetWin_1");
}
typedef struct { int seen, hidden; } WatchState;
/* Three consecutive one-second observations avoid closing on window recreation. */
static int watch_update(WatchState *s, int visible, int minimized) {
    if (visible || minimized) { s->seen = 1; s->hidden = 0; }
    else if (s->seen) ++s->hidden;
    return s->seen && s->hidden >= 3;
}
#endif
