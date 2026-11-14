/* Runs inside one Wine prefix. Observes Steam's main window, never game windows. */
#include <windows.h>
#include <stdio.h>
#include <wchar.h>
#include "steam_watch_state.h"
typedef BOOL (WINAPI *QueryImageName)(HANDLE,DWORD,LPWSTR,PDWORD);
static QueryImageName queryImageName;
static int visible, minimized;
static BOOL CALLBACK inspect(HWND window, LPARAM unused) {
    WCHAR title[256], cls[128], path[2048];
    DWORD pid, size = 2048;
    HANDLE process;
    WCHAR *name;
    (void)unused;
    GetWindowThreadProcessId(window,&pid);
    process = OpenProcess(0x1000,FALSE,pid);
    if (!process) return TRUE;
    if (!queryImageName(process,0,path,&size)) { CloseHandle(process); return TRUE; }
    CloseHandle(process);
    name = wcsrchr(path,L'\\'); name = name ? name+1 : path;
    if (_wcsicmp(name,L"steam.exe") && _wcsicmp(name,L"steamwebhelper_real.exe") &&
        _wcsicmp(name,L"steamwebhelper.exe")) return TRUE;
    GetWindowTextW(window, title, 256);
    GetClassNameW(window,cls,128);
    if (wcscmp(title,L"Steam") && wcscmp(title,L"Sign in to Steam")) return TRUE;
    if (!steam_main_class(cls)) return TRUE;
    visible |= IsWindowVisible(window) != 0;
    minimized |= IsIconic(window) != 0;
    return TRUE;
}
int main(void) {
    WatchState state = {0}; int ticks, announced = 0;
    queryImageName = (QueryImageName)GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"QueryFullProcessImageNameW");
    if (!queryImageName) return 2;
    for (ticks=0;;++ticks) {
        visible = minimized = 0;
        if (!EnumWindows(inspect,0)) return 2;
        if (watch_update(&state,visible,minimized)) return 0;
        if (state.seen && !announced) { puts("watching"); fflush(stdout); announced=1; }
        if (!state.seen && ticks >= 180) return 3;
        Sleep(1000);
    }
}
