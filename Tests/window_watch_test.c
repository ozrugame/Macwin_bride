#include <assert.h>
#include "../native/steam_watch_state.h"
int main(void) {
    assert(steam_main_class(L"SDL_app"));
    assert(steam_main_class(L"vguiPopupWindow"));
    assert(!steam_main_class(L"Chrome_StatusTrayWindow"));
    WatchState s = {0};
    assert(!watch_update(&s, 0, 0)); /* startup is not a close */
    assert(!watch_update(&s, 1, 0));
    for (int i=0;i<10;i++) assert(!watch_update(&s, 0, 1)); /* minimized */
    assert(!watch_update(&s, 0, 0));
    assert(!watch_update(&s, 0, 0));
    assert(!watch_update(&s, 1, 0)); /* window recreated */
    assert(!watch_update(&s, 0, 0));
    assert(!watch_update(&s, 0, 0));
    assert(watch_update(&s, 0, 0));
    return 0;
}
